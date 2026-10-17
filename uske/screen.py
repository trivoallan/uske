"""`uske screen`: one policy's screening, the steps of the workflow's `policy` template, in order.

The decisions are the subcommands' own (`classify_lines`, `record_lines`, `approve_plan`,
`approve_staged`); this module only launches `regis` and `knock` by their command lines, reads
the files they write and their exit codes, and keeps the journal ahead of every placement: an
operation is applied or promoted only once the verdicts that approve it are written, and the
`USKE_AFTER_RECORD` hook has succeeded (change `screen-and-policy-fan-out`, D1 to D6).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

from uske import gate, playbooks, policies, results
from uske.cli import (
    Failure,
    approve_plan,
    approve_staged,
    classify_lines,
    read_json,
    read_staged,
    record_lines,
    target,
)


@dataclass(frozen=True)
class Tools:
    """The command prefix of each tool; the arguments are appended, no shell runs them (D2)."""

    regis: list[str]
    knock: list[str]

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Tools:
        def prefix(variable: str, name: str) -> list[str]:
            value = env.get(variable, "").strip()
            return shlex.split(value) if value else [name]

        return cls(prefix("USKE_REGIS_CMD", "regis"), prefix("USKE_KNOCK_CMD", "knock"))

    def check(self) -> None:
        """Both commands are found before any step: a missing one fails before the journal."""
        for name, prefix in (("regis", self.regis), ("knock", self.knock)):
            if shutil.which(prefix[0]) is None:
                raise Failure(
                    f"{name}: command not found: {prefix[0]} "
                    f"(put it on PATH, or set USKE_{name.upper()}_CMD)"
                )


def launch(command: list[str], env: Mapping[str, str] | None = None) -> int:
    """Run `command`, its output streamed to stderr (fd 2): stdout is uske's. Its exit code, 127
    if it could not start. A failure names the whole command line, the first clue when a prefix
    mounts a path elsewhere (review, finding 2)."""
    line = shlex.join(command)
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        done = subprocess.run(
            command,
            stdout=2,
            env=dict(env) if env is not None else None,
            check=False,
        )
    except OSError as exc:
        print(f"failed to start: {line}: {exc}", file=sys.stderr)
        return 127
    if done.returncode:
        print(f"exit {done.returncode}: {line}", file=sys.stderr)
    return done.returncode


def inside(path: Path, root: Path) -> Path:
    """`path`, once checked to stay under `root`: a name or a digest is never a way out."""
    if not path.resolve().is_relative_to(root.resolve()):
        raise Failure(f"{path}: outside {root}")
    return path


class _Paths:
    """The policy's files under the work directory, laid out as `/work` in the workflow (D3)."""

    def __init__(self, work: Path, name: str) -> None:
        self.work = work
        self.policy = work / "policies" / name
        self.plan = work / "plans" / f"{name}.json"
        self.approved = work / "plans" / f"{name}.approved.json"
        self.approve_lines = work / "approve-lines" / f"{name}.json"
        self.lines = work / "lines" / name
        self.staged_lines = work / "staged-lines" / name
        self.staged = work / "staged" / f"{name}.json"
        self.staged_approved = work / "staged" / f"{name}.approved.json"
        self.applied = work / "applied" / f"{name}.json"
        for path in vars(self).values():
            inside(path, work)

    def clear(self) -> None:
        """A reused work directory must not replay an earlier screening's files."""
        for directory in (self.lines, self.staged_lines):
            shutil.rmtree(directory, ignore_errors=True)
        for path in (
            self.plan,
            self.approved,
            self.approve_lines,
            self.staged,
            self.staged_approved,
            self.applied,
        ):
            path.unlink(missing_ok=True)
        # knock's --plan-out, --staged-out and --applied-out do not create their directory
        for directory in ("plans", "staged", "applied"):
            (self.work / directory).mkdir(parents=True, exist_ok=True)

    def report(self, key: str) -> Path:
        return inside(self.work / "reports" / key, self.work / "reports")


class _Screening:
    def __init__(
        self,
        policy: policies.Policy,
        work: Path,
        results_dir: Path,
        playbooks_dir: Path,
        transit: str | None,
        epoch: str,
        run: str,
        tools: Tools,
        after_record: str | None,
        judge_only: bool,
    ) -> None:
        self.policy = policy
        self.work = work
        self.paths: _Paths  # set by steps(): its checks are failures of this policy
        self.results = results_dir
        self.playbooks = playbooks_dir
        self.transit = transit
        self.epoch = epoch
        self.run = run
        self.tools = tools
        self.after_record = after_record
        self.judge_only = judge_only
        self.summary: dict = {
            "policy": policy.name,
            "judged": 0,
            "approved": 0,
            "ordered": 0,
            "promoted": 0,
            "outcome": "ok",
        }
        self.verdicts: list[dict] = []

    def screen(self) -> dict:
        try:
            self.steps()
        except (Failure, OSError) as exc:
            print(f"error: {self.policy.name}: {exc}", file=sys.stderr)
            self.summary["outcome"] = "failed"
        except (KeyError, TypeError, ValueError) as exc:
            # a file a tool wrote, not in the shape uske reads: this policy fails, not the others
            print(
                f"error: {self.policy.name}: unexpected input: "
                f"{type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            self.summary["outcome"] = "failed"
        if self.judge_only:
            return {
                "policy": self.policy.name,
                "lines": self.verdicts,
                "outcome": self.summary["outcome"],
            }
        return self.summary

    def steps(self) -> None:
        name = self.policy.name
        self.paths = p = _Paths(self.work, name)
        inside(results.path_for(self.results, name), self.results)
        p.clear()
        # prepare
        p.policy.mkdir(parents=True, exist_ok=True)
        (p.policy / "policy.yaml").write_text(
            yaml.safe_dump(
                gate.prepare(self.policy), sort_keys=False, allow_unicode=True
            )
        )
        # plan
        if launch(
            [*self.tools.knock, "reconcile", str(p.policy), "--plan-out", str(p.plan)]
        ):
            raise Failure("knock reconcile --plan-out failed")
        # pending, resolve
        found = gate.candidates(read_json(str(p.plan)), self.policy)
        todo = [target(c) for c in results.pending(found, self.journal())]
        playbook = playbooks.resolve(self.policy.track, self.playbooks)
        # evaluate, unevaluated
        for item in todo:
            self.evaluate(item, playbook, p.lines, self.policy.track or "")
        if self.judge_only:  # judged, never recorded nor placed
            return
        # record
        self.record("record", lines=p.lines)
        # approve
        approved, count = approve_plan(
            self.policy,
            self.results,
            p.plan,
            self.transit or "",
            self.epoch,
            self.run,
            p.approve_lines,
        )
        p.approved.write_text(json.dumps(approved, indent=2))
        self.summary["approved"], self.summary["ordered"] = (
            count["approved"],
            count["ordered"],
        )
        if not self.transit and count["discarded"].get("no-transit"):
            print(
                f"warning: {name}: {count['discarded']['no-transit']} source(s) to repair "
                "recorded inconclusive (uske/no-transit): pass --transit to have them repaired",
                file=sys.stderr,
            )
        # record-approve
        self.record("record-approve", lines=p.approve_lines)
        if not count["approved"]:
            return
        # place, place-staged: the transit only when the plan carries an order
        stage = (
            ["--stage-to", str(self.transit), "--staged-out", str(p.staged)]
            if count["ordered"]
            else []
        )
        placed = not launch(
            [
                *self.tools.knock,
                "reconcile",
                str(p.policy),
                "--apply-plan",
                str(p.approved),
                *stage,
                "--applied-out",
                str(p.applied),
            ]
        )
        # record-applied: what was placed is recorded, even when the apply failed
        self.record("record-applied", applied=p.applied)
        # second-gate
        if count["ordered"]:
            self.second_gate(playbook)
        # place-failed: once everything held has been handled
        if not placed:
            raise Failure(f"knock reconcile --apply-plan failed for {name}")

    def second_gate(self, playbook: Path | None) -> None:
        p = self.paths
        # pending
        found = gate.staged_candidates(read_staged(str(p.staged)), self.policy)
        held = [target(c) for c in results.pending(found, self.journal())]
        # evaluate: a held image by its own digest
        for item in held:
            self.evaluate(item, playbook, p.staged_lines, "")
        # record
        self.record("record-held", lines=p.staged_lines)
        # approve
        approved, count = approve_staged(self.policy, self.results, p.staged)
        p.staged_approved.write_text(json.dumps(approved, indent=2))
        if not count["approved"]:
            return
        # promote
        if launch(
            [
                *self.tools.knock,
                "promote",
                str(p.policy),
                "--staged",
                str(p.staged_approved),
            ]
        ):
            raise Failure(f"knock promote failed for {self.policy.name}")
        # record-promoted
        self.record("record-promoted", promoted=p.staged_approved)
        self.summary["promoted"] = count["approved"]

    def journal(self) -> list[dict]:
        return results.read(results.path_for(self.results, self.policy.name))

    def evaluate(
        self, item: dict, playbook: Path | None, lines_dir: Path, track: str
    ) -> None:
        """One digest judged; its lines written where `record` reads them."""
        digest, source_digest = item["digest"], item.get("source", "")
        if playbook is None:
            # unknown track: never sent to regis (D-21)
            lines = classify_lines(
                None, item["ref"], digest, None, None, 0, "", "", "", "", self.run
            )
        else:
            out = self.paths.report(item["key"])
            shutil.rmtree(out, ignore_errors=True)  # never read an earlier report
            out.mkdir(parents=True)
            code = launch(
                [
                    *self.tools.regis,
                    "analyze",
                    item["target"],
                    "--playbook",
                    str(playbook),
                    "-D",
                    str(out),
                    "-o",
                    "report.{format}",
                    "--html",
                    "--markdown",
                ]
            )
            # a failed evaluation is recorded inconclusive, not lost (D-23)
            lines = classify_lines(
                playbook,
                item["ref"],
                digest,
                out / "report.json",
                self.keep_report(out, digest),
                code,
                item.get("sourceRef", ""),
                source_digest,
                track,
                item.get("epoch", ""),
                self.run,
            )
        lines_dir.mkdir(parents=True, exist_ok=True)
        (lines_dir / f"{item['key']}.json").write_text(
            json.dumps(lines if source_digest else lines[0], ensure_ascii=False)
        )
        self.summary["judged"] += 1
        self.verdicts.extend(lines)

    def keep_report(self, out: Path, digest: str) -> str | None:
        """Copy the reports next to the journal, before the line that cites them is written (D5).

        The line cites the Markdown, else the HTML, else the JSON, relative to the results
        directory. The report is named after the epoch, or the first free name after it
        (`<epoch>-2`, `<epoch>-3`…): a report already there is never rewritten. A judged-only
        screening writes nothing there: its line cites the report in the work directory.
        """
        written = [ext for ext in ("md", "html") if (out / f"report.{ext}").is_file()]
        if not written and (out / "report.json").is_file():
            written = ["json"]
        if not written:
            return None
        if self.judge_only:
            return str(out / f"report.{written[0]}")
        # the epoch names the report, never the run: one judgment, one file, never rewritten
        relative = Path("reports") / self.policy.name / digest
        folder = inside(self.results / relative, self.results / "reports")
        folder.mkdir(parents=True, exist_ok=True)
        stem = _free_stem(folder, _file_name(self.epoch) or "report")
        for ext in written:
            with (
                (out / f"report.{ext}").open("rb") as src,
                (folder / f"{stem}.{ext}").open("xb") as dst,
            ):  # exclusive: fails rather than rewrite a cited report
                shutil.copyfileobj(src, dst)
        return str(relative / f"{stem}.{written[0]}")

    def record(
        self,
        step: str,
        *,
        lines: Path | None = None,
        applied: Path | None = None,
        promoted: Path | None = None,
    ) -> None:
        written, stale = record_lines(
            self.policy, self.results, lines, applied, promoted, self.run
        )
        for message in stale:
            print(message, file=sys.stderr)
        if written:
            self.hook(step)

    def hook(self, step: str) -> None:
        """`USKE_AFTER_RECORD`, by the shell. The policy's name reaches it through the
        environment only: never interpolated into the command (review, finding 5)."""
        if not self.after_record:
            return
        env = {
            **os.environ,
            "USKE_POLICY": self.policy.name,
            "USKE_STEP": step,
            "USKE_RESULTS": str(self.results),
        }
        if launch(["sh", "-c", self.after_record], env):
            raise Failure("USKE_AFTER_RECORD failed: nothing more is placed")


def _file_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("._")


REPORT_EXTS = ("md", "html", "json")


def _free_stem(folder: Path, base: str) -> str:
    """The first name no report carries yet in `folder`: `base`, then `base-2`, `base-3`…"""
    stem, n = base, 1
    while any((folder / f"{stem}.{ext}").exists() for ext in REPORT_EXTS):
        n += 1
        stem = f"{base}-{n}"
    return stem


def screen_policy(
    policy: policies.Policy,
    work: Path,
    results_dir: Path,
    playbooks_dir: Path,
    transit: str | None,
    epoch: str,
    run: str,
    tools: Tools,
    after_record: str | None,
    judge_only: bool,
) -> dict:
    """Screen one policy; never raises for the policy's own failure.

    Returns `{"policy", "judged", "approved", "ordered", "promoted", "outcome"}`, outcome `ok` or
    `failed`. `judged` counts every digest given a verdict line at either gate, the digests of an
    unknown track too, which are recorded without being sent to regis; with `judge_only`, `{"policy", "lines", "outcome"}`, the verdict lines it would have
    recorded.
    """
    return _Screening(
        policy,
        work,
        results_dir,
        playbooks_dir,
        transit,
        epoch,
        run,
        tools,
        after_record,
        judge_only,
    ).screen()
