"""A screening spread over pods that share no volume: each child exports its new lines, one pod merges.

A child works on a copy of its policy's journal, taken from the parent's snapshot. `export` packs
what the child added beyond that snapshot, with the reports those lines cite; `merge` appends each
archive to the real journal by `results.append`, the same forward-only rule as `uske record` (D9,
D12). An archive is checked whole before anything is written: a member or a policy name never
leads outside the results directory.
"""

from __future__ import annotations

import io
import json
import os
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path, PurePosixPath

from uske import policies, results

LINES = "lines.jsonl"
REPORTS = "reports"
SUFFIX = ".tgz"
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


def export(
    policy: str, results_dir: Path, snapshot_lines: int, out: Path
) -> tuple[int, list[str]]:
    """Write the archive of the lines past the snapshot and their reports: (lines, warnings)."""
    if snapshot_lines < 0:
        raise ArchiveError(f"--snapshot-lines must be 0 or more, got {snapshot_lines}")
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
    with tarfile.open(out, "w:gz", dereference=True) as tar:
        data = body.encode()
        info = tarfile.TarInfo(LINES)
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
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


def _read(archive: Path, policy: str) -> tuple[list[dict], dict[str, bytes]]:
    """The archive's lines and reports (member name -> content), every member checked first."""
    lines: list[dict] = []
    reports: dict[str, bytes] = {}
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
                elif name.is_relative_to(PurePosixPath(REPORTS, policy)):
                    reports[name.as_posix()] = tar.extractfile(info).read()  # type: ignore[union-attr]
                else:
                    raise ArchiveError(f"refused member {info.name!r}")
    except (OSError, tarfile.TarError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArchiveError(str(exc)) from exc
    return lines, reports


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


def merge_one(archive: Path, results_dir: Path) -> tuple[str, int, list[str]]:
    """Merge one `<policy>.tgz`: (policy, lines written, stale messages)."""
    policy = archive.name.removesuffix(SUFFIX)
    if len(policy) > policies.NAME_MAX or not policies.NAME.fullmatch(policy):
        raise ArchiveError(f"{policy!r} is not a policy name (DNS-1123)")
    lines, reports = _read(archive, policy)
    root = results_dir.resolve()
    try:
        # reports first: a line is never in the journal before the report it cites
        for member, content in sorted(reports.items()):
            dest = results_dir / member
            if not dest.resolve().is_relative_to(root / REPORTS):
                raise ArchiveError(f"refused member {member!r}: outside {REPORTS}/")
            _keep(content, dest)
        written, stale = results.append(results.path_for(results_dir, policy), lines)
    except OSError as exc:
        raise ArchiveError(str(exc)) from exc
    return policy, written, stale


def archives(source: Path) -> list[Path]:
    """The `<policy>.tgz` files of `source`, by name; none when it does not exist."""
    if not source.exists():
        return []
    if not source.is_dir():
        raise ArchiveError(f"{source}: not a directory")
    return sorted(p for p in source.iterdir() if p.name.endswith(SUFFIX))
