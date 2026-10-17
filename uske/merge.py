"""A screening spread over pods that share no volume: each child exports its new lines, one pod merges.

The parent's `snapshot` copies the journals for its children and leaves a mark, `.pending-merge/<run>`,
beside them; a screening that finds another run's mark refuses to start. A child works on a copy of
its policy's journal, taken from that snapshot. `export` packs what the child added beyond the
snapshot, with the reports those lines cite; `merge` appends each archive to the real journal by
`results.append`, the same forward-only rule as `uske record` (D9, D12), then clears the mark. An
archive is checked whole before anything is written: a member or a policy name never leads outside
the results directory.

A line written to the real journal after the snapshot, by hand or by another screening, wins: the
child's lines on that digest are refused, named, and the merge fails (D12). The child never saw that
line, and its own lines, newer by `ts`, would otherwise silently revert it. The placement may have
happened already: the merge makes the conflict visible, it cannot undo it.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from uske import policies, results

LINES = "lines.jsonl"
# the snapshot's line count and the screening's run, written by `export`, read by `merge`
META = "meta.json"
REPORTS = "reports"
SUFFIX = ".tgz"
# beside the journals, never a `*.jsonl`: snapshot, merge and `decisions` read only those
PENDING = ".pending-merge"
RUN_MAX = 253  # a Workflow's name: a DNS-1123 subdomain
# where the lines say a report lives once merged: the journal volume's mount point (D9)
MOUNT = PurePosixPath("/results")


class ArchiveError(Exception):
    """An archive that cannot be merged: unreadable, or one that would write out of place."""


def _report_member(cited: str, results_dir: Path, policy: str) -> tuple[Path, str]:
    """The file a line's `report` names in the child, and its member name in the archive."""
    path = PurePosixPath(cited)
    if path.is_absolute():
        if not path.is_relative_to(MOUNT):
            raise ArchiveError(f"{cited}: not under {MOUNT}")
        path = path.relative_to(MOUNT)
    member = PurePosixPath(os.path.normpath(path.as_posix()))
    if (
        not member.is_relative_to(PurePosixPath(REPORTS, policy))
        or ".." in member.parts
    ):
        raise ArchiveError(f"{cited}: not under {REPORTS}/{policy}/")
    return results_dir / member, member.as_posix()


def _member(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))


def export(
    policy: str, results_dir: Path, snapshot_lines: int, out: Path, run: str
) -> tuple[int, list[str]]:
    """Write the archive of the lines past the snapshot and their reports: (lines, warnings)."""
    if snapshot_lines < 0:
        raise ArchiveError(f"--snapshot-lines must be 0 or more, got {snapshot_lines}")
    if not run:
        raise ArchiveError("--run must name the screening")
    lines = results.read(results.path_for(results_dir, policy))
    if len(lines) < snapshot_lines:
        raise ArchiveError(
            f"{policy}: the journal has {len(lines)} lines, fewer than the snapshot's "
            f"{snapshot_lines}: the snapshot is not its prefix"
        )
    new = lines[snapshot_lines:]
    warnings: list[str] = []
    reports: dict[str, Path] = {}
    for line in new:
        if not line.get("report"):
            continue
        try:
            source, member = _report_member(line["report"], results_dir, policy)
        except ArchiveError as exc:
            warnings.append(f"skipped: {exc}")
            continue
        if source.is_file():
            reports[member] = source
        else:
            warnings.append(f"skipped: {line['report']}: no such report")
    body = "".join(json.dumps(line, ensure_ascii=False) + "\n" for line in new)
    out.parent.mkdir(parents=True, exist_ok=True)
    meta = {"snapshot_lines": snapshot_lines, "run": run}
    with tarfile.open(out, "w:gz", dereference=True) as tar:
        _member(tar, META, (json.dumps(meta) + "\n").encode())
        _member(tar, LINES, body.encode())
        for member, source in sorted(reports.items()):
            tar.add(source, arcname=member, recursive=False)
    return len(new), warnings


def _checked_line(value: object) -> dict:
    if not isinstance(value, dict) or not all(
        isinstance(value.get(k), str) for k in ("ts", "digest", "state")
    ):
        raise ArchiveError(f"{LINES}: a line needs ts, digest and state")
    try:
        datetime.strptime(value["ts"], "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ArchiveError(f"{value['digest']}: ts {value['ts']!r}: {exc}") from exc
    return value


def _checked_meta(value: object) -> dict:
    if (
        not isinstance(value, dict)
        or type(value.get("snapshot_lines")) is not int
        or value["snapshot_lines"] < 0
        or not isinstance(value.get("run"), str)
        or not value["run"]
    ):
        raise ArchiveError(f"{META}: needs snapshot_lines (0 or more) and run")
    return value


def _read(archive: Path, policy: str) -> tuple[list[dict], dict[str, bytes], dict]:
    """The archive's lines, reports (member name -> content) and meta, every member checked first."""
    lines: list[dict] = []
    reports: dict[str, bytes] = {}
    meta: dict | None = None
    try:
        with tarfile.open(archive, "r:gz") as tar:
            for info in tar.getmembers():
                name = PurePosixPath(info.name)
                if (
                    name.is_absolute()
                    or ".." in name.parts
                    or not (info.isfile() or info.isdir())
                ):
                    raise ArchiveError(f"refused member {info.name!r}")
                if info.isdir():
                    continue
                if name.as_posix() == LINES:
                    text = tar.extractfile(info).read().decode()  # type: ignore[union-attr]
                    rows = [r.removesuffix("\r") for r in text.split("\n")]
                    lines = [_checked_line(json.loads(r)) for r in rows if r.strip()]
                elif name.as_posix() == META:
                    data = tar.extractfile(info).read()  # type: ignore[union-attr]
                    meta = _checked_meta(json.loads(data))
                elif name.is_relative_to(PurePosixPath(REPORTS, policy)):
                    reports[name.as_posix()] = tar.extractfile(info).read()  # type: ignore[union-attr]
                else:
                    raise ArchiveError(f"refused member {info.name!r}")
    except (OSError, tarfile.TarError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArchiveError(str(exc)) from exc
    if meta is None:
        raise ArchiveError(
            f"no {META}: written by an older `uske export`, it does not say which journal lines "
            "came after the snapshot; re-run the child to export it again"
        )
    return lines, reports, meta


def _since_snapshot(journal: list[dict], meta: dict) -> dict[str, dict]:
    """digest -> the last journal line past the snapshot that this screening did not write."""
    count = meta["snapshot_lines"]
    if len(journal) < count:
        raise ArchiveError(
            f"the journal has {len(journal)} lines, fewer than the snapshot's {count}: "
            "the snapshot is not its prefix"
        )
    return {
        line["digest"]: line
        for line in journal[count:]
        if line.get("run") != meta["run"]
    }


def _conflict(line: dict, theirs: dict) -> str:
    reason = f" ({theirs['reason']})" if theirs.get("reason") else ""
    who = f"run {theirs['run']}" if theirs.get("run") else "hand"
    return (
        f"conflict: {line['digest']}: the child's {line['state']} line of {line['ts']} is not "
        f"merged: the journal has {theirs['state']}{reason} of {theirs['ts']}, written by "
        f"{who} after the snapshot"
    )


def _keep(content: bytes, dest: Path) -> None:
    """Write `dest` unless it exists: a report already merged is never overwritten."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as tmp:
        tmp.write(content)
    try:
        os.link(tmp.name, dest)  # fails if dest exists; never a half-written report
    except FileExistsError:
        pass
    finally:
        os.unlink(tmp.name)


def _check_policy(policy: str) -> None:
    if len(policy) > policies.NAME_MAX or not policies.NAME.fullmatch(policy):
        raise ArchiveError(
            f"{policy!r} is not a policy name (a DNS-1123 subdomain, at most 63 characters)"
        )


def merge_one(
    policy: str, archive: Path, results_dir: Path
) -> tuple[int, list[str], list[str]]:
    """Merge one archive of `policy`: (lines written, stale messages, conflict messages).

    A child's line on a digest that the journal gained a line on since the snapshot, not written by
    this screening, is refused: that line stays the digest's last state.
    """
    _check_policy(policy)
    lines, reports, meta = _read(archive, policy)
    journal = results.path_for(results_dir, policy)
    root = results_dir.resolve()
    try:
        theirs = _since_snapshot(results.read(journal), meta)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError) as exc:
        raise ArchiveError(f"{journal.name}: {exc}") from exc
    kept = [line for line in lines if line["digest"] not in theirs]
    conflicts = [
        _conflict(line, theirs[line["digest"]])
        for line in lines
        if line["digest"] in theirs
    ]
    try:
        # reports first: a line is never in the journal before the report it cites
        for member, content in sorted(reports.items()):
            dest = results_dir / member
            if not dest.resolve().is_relative_to(root / REPORTS):
                raise ArchiveError(f"refused member {member!r}: outside {REPORTS}/")
            _keep(content, dest)
        written, stale = results.append(journal, kept)
    except OSError as exc:
        raise ArchiveError(str(exc)) from exc
    return written, stale, conflicts


def archives(source: Path) -> list[tuple[str, list[Path]]]:
    """`source/<policy>/*.tgz`: each policy's archives, by name, so in its children's creation order.

    A child names its archive `<creation time>-<child>.tgz`: a child re-created by `argo retry`, or
    resubmitted, adds an archive and never overwrites one not yet merged. Only regular files count:
    a missing optional input can show up as an empty directory. None when `source` does not exist.
    """
    if not source.exists():
        return []
    if not source.is_dir():
        raise ArchiveError(f"{source}: not a directory")
    found = []
    for directory in sorted(p for p in source.iterdir() if p.is_dir()):
        files = sorted(
            p for p in directory.iterdir() if p.is_file() and p.name.endswith(SUFFIX)
        )
        if files:
            found.append((directory.name, files))
    return found


def check_run(run: str) -> None:
    if len(run) > RUN_MAX or not policies.NAME.fullmatch(run):
        raise ArchiveError(f"{run!r} is not a Workflow name (a DNS-1123 subdomain)")


def pending(results_dir: Path) -> list[str]:
    """The screenings whose merge has not succeeded yet: their marks, by name."""
    marks = results_dir / PENDING
    if not marks.is_dir():
        return []
    return sorted(p.name for p in marks.iterdir() if p.is_file())


def snapshot(listed: list[dict], results_dir: Path, out: Path, run: str) -> list[dict]:
    """Copy the journals to `out`, mark `run` pending, and return `listed` with each line count.

    Refuses while another screening's merge is pending: its children may have placed images
    whose lines are not in the journal yet, and a snapshot without them would judge them again.
    """
    check_run(run)
    others = [name for name in pending(results_dir) if name != run]
    if others:
        raise ArchiveError(
            f"the merge of {', '.join(others)} is pending: its lines are not in the journal "
            f"yet. Replay it with `argo retry {others[0]}`; once it has merged, the next "
            f"screening starts (to give its lines up, remove {results_dir / PENDING}/<run>)"
        )
    out.mkdir(parents=True, exist_ok=True)
    for journal in sorted(results_dir.glob("*.jsonl")):
        if journal.is_file():
            shutil.copyfile(journal, out / journal.name)
    fanned = []
    for policy in listed:
        _check_policy(policy["name"])
        copy = results.path_for(out, policy["name"])
        # Non-blank lines, as results.read counts them: what the child's export skips.
        text = copy.read_text("utf-8") if copy.exists() else ""
        lines = sum(1 for line in text.split("\n") if line.strip())
        fanned.append({**policy, "lines": lines})
    mark = results_dir / PENDING / run
    mark.parent.mkdir(exist_ok=True)
    mark.write_text(datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") + "\n")
    return fanned


def merged(results_dir: Path, run: str) -> None:
    """Clear `run`'s mark: its lines are all in the journal."""
    check_run(run)
    (results_dir / PENDING / run).unlink(missing_ok=True)
