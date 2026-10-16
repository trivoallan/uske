"""One append-only results file per policy; its refusal lines are journal lines (D-22)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from uske.outcomes import Outcome


@dataclass(frozen=True)
class ResultLine:
    ts: str
    ref: str
    digest: str
    state: str
    ruleset: str
    reason: str | None = None
    report: str | None = None
    run: str | None = None  # the screening that wrote the line: an id or its URL
    source: str | None = (
        None  # on a held image's line: the source digest it was built from
    )
    rebuilt: str | None = None  # on a closing line: the held image that was refused
    # on a first-gate refusal: the playbook's failed rules are all repairable under the regime
    repairable: bool | None = None
    epoch: str | None = (
        None  # on a held image's line: the remediation order it was built under
    )
    placed: str | None = (
        None  # on a placement line: the digest knock wrote at the destination
    )

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


def path_for(results_dir: str | Path, policy_name: str) -> Path:
    return Path(results_dir) / f"{policy_name}.jsonl"


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    # Split on "\n" only: splitlines() also breaks on U+2028, U+2029, \x0b, \x0c and
    # \x1c, which JSON allows raw inside a string (a hand-written arbitration line).
    lines = (line.removesuffix("\r") for line in path.read_text("utf-8").split("\n"))
    return [json.loads(line) for line in lines if line.strip()]


def last_states(lines: list[dict]) -> dict[str, str]:
    """digest -> its last recorded state."""
    return {line["digest"]: line["state"] for line in lines}


def last_verdicts(lines: list[dict]) -> dict[str, dict]:
    """digest -> its last line that is a decision, not a placement record."""
    return {line["digest"]: line for line in lines if not line.get("placed")}


def pending(candidates: list[dict], lines: list[dict]) -> list[dict]:
    """Candidates never decided, plus those whose last outcome was inconclusive (retried)."""
    states = last_states(lines)
    return [
        c
        for c in candidates
        if states.get(c["digest"], Outcome.INCONCLUSIVE) == Outcome.INCONCLUSIVE
    ]


def attempts(lines: list[dict], source: str) -> int:
    """Held images left without a verdict for `source` since the last line written on `source` itself."""
    count = 0
    for line in lines:
        if line["digest"] == source:
            count = 0
        elif line.get("source") == source and line["state"] == Outcome.INCONCLUSIVE:
            count += 1
    return count


def append(path: Path, new_lines: list[dict]) -> tuple[int, list[str]]:
    """Append in a single write; returns (written, stale). A line that repeats a digest's last state is
    dropped (D-27), unless it records a placed digest not yet recorded for that digest; so is a
    line older than that digest's newest line: the journal only moves forward, so replaying a
    step never reopens a decision. `stale` describes the lines dropped for age."""
    last: dict[
        str, tuple[str, str]
    ] = {}  # digest -> (newest ts, state of the last line)
    placed: dict[
        str, set[str]
    ] = {}  # digest -> the placed digests already recorded for it
    for line in read(path):
        ts = max(line.get("ts") or "", last.get(line["digest"], ("", ""))[0])
        last[line["digest"]] = (ts, line["state"])
        if line.get("placed"):
            placed.setdefault(line["digest"], set()).add(line["placed"])
    kept, stale = [], []
    for line in new_lines:
        newest, state = last.get(line["digest"], ("", None))
        # a placement repeats its source's state on purpose: what it adds is the placed digest
        new_placement = bool(line.get("placed")) and line["placed"] not in placed.get(
            line["digest"], set()
        )
        # ponytail: second resolution — a replay inside the same second as the newer line is not caught; the workflow never does that
        if line["ts"] < newest:
            stale.append(f"stale: {line['digest']} {line['ts']} is older than {newest}")
        elif line["state"] != state or new_placement:
            kept.append(line)
            last[line["digest"]] = (line["ts"], line["state"])
            if new_placement:
                placed.setdefault(line["digest"], set()).add(line["placed"])
    if kept:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as out:
            out.write(
                "".join(json.dumps(line, ensure_ascii=False) + "\n" for line in kept)
            )
    return len(kept), stale
