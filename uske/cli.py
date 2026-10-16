"""One subcommand per workflow step, plus `decisions`, which reads the journal for a person.

JSON on stdout unless asked otherwise. A business outcome is never an exit code: quarantine and
inconclusive exit 0. Exit 1 is a technical failure (Argo retries it), exit 2 a usage error
(argparse).
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import yaml

from uske import census, decisions, dtsync, gate, outcomes, playbooks, policies, results


class Failure(Exception):
    """A technical failure: exit 1."""


def _json(value) -> None:
    print(json.dumps(value, ensure_ascii=False))


def _read_json(path: str):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise Failure(f"{path}: {exc}") from exc


def _read_staged(path: str) -> dict:
    """knock's StagedRebuilds. No file: knock held nothing, or did not get that far."""
    return _read_json(path) if Path(path).exists() else {"entries": []}


def _policy(path: str) -> policies.Policy:
    try:
        return policies.load(path)
    except policies.PolicyError as exc:
        raise Failure(str(exc)) from exc


def cmd_list(args) -> None:
    found, errors = policies.load_dir(args.policies)
    for error in errors:
        print(f"skipped: {error}", file=sys.stderr)
    _json([{"name": p.name, "path": str(p.path)} for p in found])


def _target(candidate: dict) -> dict:
    """What the workflow needs per digest: `regis` evaluates by digest, never by tag (D-24)."""
    repository = candidate["ref"]
    if ":" in repository.rsplit("/", 1)[-1]:
        repository = repository.rsplit(":", 1)[0]
    digest = candidate["digest"]
    return {
        **candidate,
        "target": f"{repository}@{digest}",
        "key": digest.split(":")[-1][:16],
    }


def cmd_pending(args) -> None:
    policy = _policy(args.policy)
    lines = results.read(results.path_for(args.results, policy.name))
    if args.staged:
        found = gate.staged_candidates(_read_staged(args.staged), policy)
    else:
        found = gate.candidates(_read_json(args.plan), policy)
    _json([_target(c) for c in results.pending(found, lines)])


def cmd_prepare(args) -> None:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        yaml.safe_dump(
            gate.prepare(_policy(args.policy)), sort_keys=False, allow_unicode=True
        )
    )
    _json({"prepared": str(out)})


def cmd_resolve(args) -> None:
    policy = _policy(args.policy)
    playbook = playbooks.resolve(policy.track, args.playbooks)
    _json({"track": policy.track, "playbook": str(playbook) if playbook else None})


def cmd_classify(args) -> None:
    """The report is read where the screening wrote it, and recorded where it will still be."""
    if bool(args.source_ref) != bool(args.source_digest):
        # half a pair would write an anonymous closing line, or silently skip the second gate
        raise Failure("--source-ref and --source-digest go together")
    if args.playbook is None:
        # unknown regime: never evaluated, recorded as such (D-21, D-23)
        ruleset, report_path, report = "none", None, None
        outcome, reason = outcomes.Outcome.INCONCLUSIVE, "uske/unknown-track"
    else:
        try:
            raw = Path(args.playbook).read_bytes()
            playbook = yaml.safe_load(raw) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise Failure(f"{args.playbook}: {exc}") from exc
        ruleset = "sha256:" + hashlib.sha256(raw).hexdigest()
        report_path = Path(args.report) if args.report else None
        try:
            report = json.loads(report_path.read_text()) if report_path else None
        except (OSError, json.JSONDecodeError):
            report = None  # unreadable is inconclusive, not a failure
        outcome, reason = outcomes.classify(report, playbook, args.regis_exit)
    repairable = (
        outcome is outcomes.Outcome.TRANSFORMATION_REQUIRED
        and not args.source_digest  # a repaired image is judged, never repaired again
        and outcomes.repairable(report, playbooks.repairable(args.track or None))
    )
    line = results.ResultLine(
        ts=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ref=args.ref,
        digest=args.digest,
        state=outcome.value,
        ruleset=ruleset,
        reason=reason,
        # what a human opens, when the workflow kept it; else what was read, for a local run
        report=(args.report_link or str(report_path)) if report is not None else None,
        run=args.run_id or None,  # Argo passes an empty string when it has none
        repairable=True if repairable else None,
    )
    if not args.source_digest:  # first gate; Argo passes an empty string
        _json(line.to_dict())
        return
    lines = [
        dataclasses.replace(
            line, source=args.source_digest, epoch=args.epoch or None
        ).to_dict()
    ]
    if outcome in (
        outcomes.Outcome.TRANSFORMATION_REQUIRED,
        outcomes.Outcome.QUARANTINE,
    ):
        # the repaired image was judged and refused: close the source, one attempt only
        lines.append(
            results.ResultLine(
                ts=line.ts,
                ref=args.source_ref,
                digest=args.source_digest,
                state=outcomes.Outcome.QUARANTINE.value,
                ruleset=ruleset,
                reason=gate.REMEDIATION_REFUSED,
                report=line.report,
                run=line.run,
                rebuilt=args.digest,
            ).to_dict()
        )
    _json(lines)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def cmd_record(args) -> None:
    policy = _policy(args.policy)
    if not (args.lines or args.applied or args.promoted):
        raise Failure("record needs --lines, --applied or --promoted")
    files: list[Path] = []
    if args.lines:
        source = Path(args.lines)
        # a directory holds one line per digest, written by each `classify` of the fan-out
        if source.is_dir():
            files = sorted(source.glob("*.json"))
        else:  # no directory: no candidate this screening
            files = [source] if source.exists() or source.suffix else []
    lines = []
    for f in files:
        value = _read_json(str(f))
        lines.extend(value if isinstance(value, list) else [value])
    if args.applied and Path(args.applied).exists():
        journal = results.read(results.path_for(args.results, policy.name))
        lines.extend(
            gate.from_applied(
                _read_json(args.applied),
                policy,
                journal,
                ts=_now(),
                run=args.run_id or None,
            )
        )
    if args.promoted:
        journal = results.read(results.path_for(args.results, policy.name))
        lines.extend(
            gate.from_promoted(
                _read_staged(args.promoted),
                policy,
                journal,
                ts=_now(),
                run=args.run_id or None,
            )
        )
    for line in lines:
        try:
            datetime.strptime(line["ts"], "%Y-%m-%dT%H:%M:%SZ")
        except (KeyError, TypeError, ValueError) as exc:
            raise Failure(
                f"{line.get('digest')}: ts must be %Y-%m-%dT%H:%M:%SZ, got {line.get('ts')!r}"
            ) from exc
    written, stale = results.append(results.path_for(args.results, policy.name), lines)
    for message in stale:
        print(message, file=sys.stderr)
    _json({"written": written, **({"stale": len(stale)} if stale else {})})


def cmd_approve(args) -> None:
    policy = _policy(args.policy)
    lines = results.read(results.path_for(args.results, policy.name))
    if args.staged:
        approved = gate.approve_staged(_read_staged(args.staged), policy, lines)
        count = {"approved": len(approved["entries"])}
    else:
        approved, discarded, written = gate.approve(
            _read_json(args.plan),
            policy,
            lines,
            args.transit,
            epoch=args.epoch or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
            ts=_now(),
            run=args.run_id or None,
        )
        count = {
            "approved": len(approved["operations"]),
            "ordered": gate.ordered(approved),
            "discarded": discarded,
        }
        if args.lines_out:
            Path(args.lines_out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.lines_out).write_text(json.dumps(written, ensure_ascii=False))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(approved, indent=2))
    _json(count)


def _dependency_track() -> dtsync.DependencyTrack:
    url, key = os.environ.get("DT_URL"), os.environ.get("DT_API_KEY")
    if not url or not key:
        raise Failure("DT_URL and DT_API_KEY are required")
    return dtsync.DependencyTrack(url, key)


def _sync(step):
    """Run a dt-sync step; its failures are technical (exit 1)."""
    try:
        step()
    except dtsync.SyncError as exc:
        raise Failure(str(exc)) from exc


def cmd_dt_plan(args) -> None:
    def step():
        fleet = dtsync.placed(_read_json(args.audit))
        found, errors = policies.load_dir(args.policies)
        for error in errors:
            print(f"skipped: {error}", file=sys.stderr)
        result = dtsync.plan(
            fleet, {p.name: p for p in found}, _dependency_track().tracked()
        )
        for line in result["report"]:
            print(
                f"report: {line['ref']}: {line['reason']} {line.get('policy', '')}",
                file=sys.stderr,
            )
        _json(result)

    _sync(step)


def _registry_flags() -> list[str]:
    user, password = os.environ.get("HARBOR_USER"), os.environ.get("HARBOR_PASSWORD")
    return (
        ["--registry-username", user, "--registry-password", password] if user else []
    )


def _tags(value: str) -> list[str]:
    """A JSON array (what Argo renders for `{{item.tags}}`) or a comma-separated list."""
    if value.startswith("["):
        try:
            return [str(t) for t in json.loads(value)]
        except json.JSONDecodeError as exc:
            raise Failure(f"--tags: {exc}") from exc
    return [t for t in value.split(",") if t]


def cmd_dt_publish(args) -> None:
    def step():
        ref = f"{args.ref}@{args.digest}"  # what is verified is what is sent
        bom = dtsync.verified_bom(ref, args.key, _registry_flags())
        item = {
            "project": args.project,
            "version": args.version,
            "digest": args.digest,
            "tags": _tags(args.tags),
            "uuid": args.uuid if args.uuid not in (None, "", "null") else None,
        }
        uuid = _dependency_track().publish(item, bom)
        _json({"ref": ref, "sent": f"{args.project} {args.version}", "uuid": uuid})

    _sync(step)


def cmd_census(args) -> None:
    """Count the bypass (objective 2, KR2). Without --oracle-cmd, only the stored bypass."""
    url, user = os.environ.get("HARBOR_URL"), os.environ.get("HARBOR_USER")
    password = os.environ.get("HARBOR_PASSWORD")
    if not url or not user or not password:
        raise Failure("HARBOR_URL, HARBOR_USER and HARBOR_PASSWORD are required")
    known = None
    if args.known_repositories:
        try:
            lines = Path(args.known_repositories).read_text().splitlines()
        except OSError as exc:
            raise Failure(f"{args.known_repositories}: {exc}") from exc
        known = {
            line.strip() for line in lines if line.strip() and not line.startswith("#")
        }
    try:
        fleet = census.walk(census.Harbor(url, user, password), args.project or None)
        suspect = census.suspects(fleet, known)
        split = None
        if args.oracle_cmd:
            ask = census.command_oracle(args.oracle_cmd, args.oracle_timeout)
            split = census.in_service(suspect, ask, idle_days=args.idle_days)
        result = census.report(
            fleet, suspect, split, idle_days=args.idle_days, known_repositories=known
        )
    except census.CensusError as exc:
        raise Failure(str(exc)) from exc
    for caveat in result["caveats"]:
        print(f"caveat: {caveat}", file=sys.stderr)
    if args.suspects_out:
        Path(args.suspects_out).write_text(
            json.dumps(suspect, ensure_ascii=False, indent=2)
        )
    _json(result)


def cmd_dt_retire(args) -> None:
    _sync(lambda: _dependency_track().retire(args.uuid))
    _json({"retired": args.uuid})


def _day(text: str) -> date:
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"expected YYYY-MM-DD (a UTC day), got {text!r}"
        ) from exc


def cmd_decisions(args) -> None:
    try:
        lines, read = decisions.load(Path(args.results), args.policy_name)
    except decisions.JournalError as exc:
        raise Failure(str(exc)) from exc
    for entry in read:
        print(entry, file=sys.stderr)
    # "a, b" means a and b; an empty --state filters nothing
    states = {s.strip() for s in (args.state or "").split(",") if s.strip()} or None
    found = decisions.select(lines, args.image, states, args.since)
    if args.image and not found:
        close = decisions.suggest(lines, args.image)
        hint = (
            f"did you mean: {', '.join(close)}"
            if close
            else "the journal holds full references (docker.io/library/…) or digests"
        )
        print(f"no decision on {args.image}; {hint}", file=sys.stderr)
    if args.format == "json":
        _json(found)
    elif found:
        render = decisions.render_text if args.format == "text" else decisions.render_md
        print(render(found))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="uske", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("list", help="policies to process this screening")
    s.add_argument("--policies", required=True)
    s.set_defaults(run=cmd_list)

    s = sub.add_parser("prepare", help="the policy handed to knock, with admit: true")
    s.add_argument("--policy", required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(run=cmd_prepare)

    s = sub.add_parser("pending", help="the plan's digests still owed a decision")
    s.add_argument("--policy", required=True)
    source = s.add_mutually_exclusive_group(required=True)
    source.add_argument("--plan", help="knock's ReconcilePlan (reconcile --plan-out)")
    source.add_argument(
        "--staged",
        help="knock's StagedRebuilds (reconcile --staged-out); a missing file means nothing was held",
    )
    s.add_argument("--results", required=True)
    s.set_defaults(run=cmd_pending)

    s = sub.add_parser("resolve", help="the playbook for the policy's regime")
    s.add_argument("--policy", required=True)
    s.add_argument("--playbooks", default="playbooks")
    s.set_defaults(run=cmd_resolve)

    s = sub.add_parser("classify", help="one regis report -> one result line")
    s.add_argument("--playbook", help="absent when the regime is unknown")
    s.add_argument("--ref", required=True)
    s.add_argument("--digest", required=True)
    s.add_argument("--report", help="the regis report read to judge")
    s.add_argument(
        "--report-link",
        help="where that report survives the screening; recorded instead of --report",
    )
    s.add_argument("--regis-exit", type=int, default=0)
    s.add_argument(
        "--source-ref",
        default="",
        help="for a held image: the source it was built from",
    )
    s.add_argument(
        "--source-digest", default="", help="for a held image: that source's digest"
    )
    s.add_argument(
        "--track",
        default="",
        help="the policy's regime: its repairable rules mark a refusal `repairable`",
    )
    s.add_argument(
        "--epoch",
        default="",
        help="for a held image: the remediation order it was built under",
    )
    s.add_argument(
        "--run",
        dest="run_id",  # `run` is the subcommand's handler
        default="",
        help="the screening that judged: an id, or its URL (SDR-0018)",
    )
    s.set_defaults(run=cmd_classify)

    s = sub.add_parser("record", help="append this screening's lines")
    s.add_argument("--policy", required=True)
    s.add_argument("--results", required=True)
    s.add_argument(
        "--lines",
        default="",
        help="JSON file (a line or a list), or a directory of them",
    )
    s.add_argument(
        "--applied",
        default="",
        help="knock's AppliedOperations (reconcile --applied-out): placements, and the orders "
        "knock withheld; a missing file means knock applied nothing",
    )
    s.add_argument(
        "--promoted",
        default="",
        help="the StagedRebuilds `knock promote` placed, once it succeeded: a placement line "
        "per source, naming the promoted digest",
    )
    s.add_argument("--run", dest="run_id", default="", help="the screening that writes")
    s.set_defaults(run=cmd_record)

    s = sub.add_parser(
        "approve", help="the plan minus refused operations, for knock --apply-plan"
    )
    s.add_argument("--policy", required=True)
    source = s.add_mutually_exclusive_group(required=True)
    source.add_argument("--plan", help="knock's ReconcilePlan (reconcile --plan-out)")
    source.add_argument(
        "--staged",
        help="knock's StagedRebuilds (reconcile --staged-out); a missing file means nothing was held",
    )
    s.add_argument("--results", required=True)
    s.add_argument("--out", required=True)
    s.add_argument(
        "--transit",
        help="name of the registry remediated images are held in; trusted, not checked. Without "
        "it, no source to repair is approved: each is recorded inconclusive (uske/no-transit)",
    )
    s.add_argument(
        "--epoch",
        default="",
        help="the remediation orders' epoch: the screening's start, UTC, YYYYMMDDTHHMMSSZ "
        "(default: now)",
    )
    s.add_argument(
        "--lines-out",
        default="",
        help="where to write the journal lines this decision calls for (uske/no-transit)",
    )
    s.add_argument(
        "--run", dest="run_id", default="", help="the screening that decides"
    )
    s.set_defaults(run=cmd_approve)

    s = sub.add_parser(
        "dt-plan",
        help="the placed fleet vs Dependency-Track: what to send, what to retire",
    )
    s.add_argument("--audit", required=True, help="knock audit --signed --sbom, JSON")
    s.add_argument("--policies", required=True)
    s.set_defaults(run=cmd_dt_plan)

    s = sub.add_parser(
        "dt-publish", help="verify an image's CycloneDX attestation, then send it"
    )
    s.add_argument("--ref", required=True, help="host/repository, without tag")
    s.add_argument("--digest", required=True)
    s.add_argument("--project", required=True)
    s.add_argument("--version", required=True)
    s.add_argument("--tags", default="", help="a JSON array or comma-separated")
    s.add_argument("--uuid", help="the version already in Dependency-Track, if any")
    s.add_argument("--key", default="/keys/cosign.pub", help="knock's public key")
    s.set_defaults(run=cmd_dt_publish)

    s = sub.add_parser(
        "dt-retire", help="make a version whose image left the registry inactive"
    )
    s.add_argument("--uuid", required=True)
    s.set_defaults(run=cmd_dt_retire)

    s = sub.add_parser(
        "census",
        help="count the bypass: enumerate Harbor, subtract the admitted, ask the oracle",
    )
    s.add_argument(
        "--project",
        action="append",
        help="restrict to these Harbor projects (repeatable)",
    )
    s.add_argument(
        "--known-repositories",
        help="file of project/repo the existing chain owns, one per line (D-26, IF-08)",
    )
    s.add_argument(
        "--oracle-cmd",
        help="the usage-oracle command; without it, only the stored bypass is reported",
    )
    s.add_argument("--oracle-timeout", type=int, default=30)
    s.add_argument(
        "--idle-days",
        type=int,
        default=census.HOUSE_IDLE_DAYS,
        help="the in-service window, in days (the house retention uses 15)",
    )
    s.add_argument(
        "--suspects-out", help="write the suspect artifacts here, to name the teams"
    )
    s.set_defaults(run=cmd_census)
    s = sub.add_parser(
        "decisions",
        help="read the journal for a person: which decisions, on which image, why",
    )
    s.add_argument(
        "image", nargs="?", help="a full reference, a digest, or <repository>@sha256:…"
    )
    s.add_argument(
        "--results", required=True, help="where the uske-results volume is mounted"
    )
    s.add_argument(
        "--policy-name", help="a policy's metadata.name: read its journal only"
    )
    s.add_argument(
        "--state",
        help="comma-separated, any state (e.g. placed-by-exception,abandoned)",
    )
    s.add_argument("--since", type=_day, help="YYYY-MM-DD, a UTC day, inclusive")
    s.add_argument("--format", choices=("json", "text", "md"), default="json")
    s.set_defaults(run=cmd_decisions)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        args.run(args)
    except Failure as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
