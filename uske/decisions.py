"""Read the decision journal for a person (story 2): which decisions, on which image, and why.

Read-only. Lines keep the file's order: the journal only grows, so the file is what happened,
in the order it was written down (SDR-0016).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from uske.outcomes import Outcome

TS = "%Y-%m-%dT%H:%M:%SZ"
REQUIRED = ("ts", "digest", "state")
# the keys uske writes (results.ResultLine); any other key is rendered as found
WRITTEN = (
    "ts",
    "ref",
    "digest",
    "state",
    "reason",
    "ruleset",
    "report",
    "source",
    "rebuilt",
)
ADDED = ("policy", "backdated")  # what this module adds to a line
STATES = {o.value for o in Outcome}


class JournalError(Exception):
    """A journal that cannot be read in full: nothing is rendered."""


def read_journal(path: Path) -> list[dict]:
    lines = []
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        if not raw.strip():
            continue
        where = f"{path}:{number}"
        try:
            line = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise JournalError(f"{where}: {exc.msg}") from exc
        if not isinstance(line, dict):
            raise JournalError(f"{where}: not a JSON object")
        missing = [k for k in REQUIRED if k not in line]
        if missing:
            raise JournalError(f"{where}: missing {', '.join(missing)}")
        for key in WRITTEN:  # what is rendered as text must be text (eng review, D16)
            if key in line and not isinstance(line[key], str):
                raise JournalError(f"{where}: {key} must be a string")
        try:
            datetime.strptime(line["ts"], TS)
        except (TypeError, ValueError) as exc:
            raise JournalError(f"{where}: ts must be {TS}, got {line['ts']!r}") from exc
        if "policy" in line:
            raise JournalError(f"{where}: the key 'policy' is reserved")
        lines.append(line)
    return lines


def load(results_dir: Path, policy: str | None = None) -> tuple[list[dict], list[str]]:
    """Every line of the journals, tagged with its policy, in file order; and what was read."""
    names = sorted(p.stem for p in results_dir.glob("*.jsonl") if p.is_file())
    if not names:
        raise JournalError(
            f"{results_dir}: no journal (*.jsonl) here;"
            " --results is the directory where the uske-results volume is mounted"
        )
    if policy is not None and policy not in names:
        raise JournalError(
            f"no journal for policy {policy!r}; present: {', '.join(names)}"
        )
    files = [results_dir / f"{n}.jsonl" for n in ([policy] if policy else names)]
    lines, read = [], []
    for path in files:
        found = read_journal(path)
        read.append(f"{path}: {len(found)} lines")
        lines.extend({"policy": path.stem, **line} for line in found)
    return annotate(lines), read


def annotate(lines: list[dict]) -> list[dict]:
    """Mark a line dated before an earlier line of its (policy, digest): written later, backdated."""
    newest: dict[tuple[str, str], str] = {}
    out = []
    for line in lines:
        key = (line["policy"], line["digest"])
        if line["ts"] < newest.get(key, ""):
            line = {**line, "backdated": True}
        newest[key] = max(line["ts"], newest.get(key, ""))
        out.append(line)
    return out


def digest_of(image: str) -> str | None:
    """The digest an argument names, if it names one: `sha256:…` or `<repository>@sha256:…`."""
    if "@" in image:
        return image.split("@", 1)[1]
    return image if image.startswith("sha256:") else None


def select(
    lines: list[dict],
    image: str | None = None,
    states: set[str] | None = None,
    since: date | None = None,
) -> list[dict]:
    """The lines on an image (and on what was rebuilt from it), in a state, from a UTC day on."""
    if image is not None:
        digest = digest_of(image)
        # ponytail: exact match only; a short reference could name another repository
        wanted = (
            {digest}
            if digest
            else {l["digest"] for l in lines if l.get("ref") == image}
        )
        lines = [
            l
            for l in lines
            if wanted & {l["digest"], l.get("source"), l.get("rebuilt")}
        ]
    if states is not None:
        lines = [l for l in lines if l["state"] in states]
    if since is not None:
        day = since.isoformat()
        lines = [l for l in lines if l["ts"][:10] >= day]
    return lines


def suggest(lines: list[dict], image: str) -> list[str]:
    """Full references in the journal that end with `/<image>`: a hint, never a match."""
    return sorted({l["ref"] for l in lines if l.get("ref", "").endswith("/" + image)})
