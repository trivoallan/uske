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
    source: str | None = (
        None  # on a held image's line: the source digest it was built from
    )
    rebuilt: str | None = None  # on a closing line: the held image that was refused

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


def path_for(results_dir: str | Path, policy_name: str) -> Path:
    return Path(results_dir) / f"{policy_name}.jsonl"


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def last_states(lines: list[dict]) -> dict[str, str]:
    """digest -> its last recorded state."""
    return {line["digest"]: line["state"] for line in lines}


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
    dropped (D-27), and so is a line older than that digest's newest line: the journal only moves
    forward, so replaying a step never reopens a decision. `stale` describes the lines dropped for age."""
    last: dict[
        str, tuple[str, str]
    ] = {}  # digest -> (newest ts, state of the last line)
    for line in read(path):
        ts = max(line.get("ts") or "", last.get(line["digest"], ("", ""))[0])
        last[line["digest"]] = (ts, line["state"])
    kept, stale = [], []
    for line in new_lines:
        newest, state = last.get(line["digest"], ("", None))
        # ponytail: second resolution — a replay inside the same second as the newer line is not caught; the workflow never does that
        if line["ts"] < newest:
            stale.append(f"stale: {line['digest']} {line['ts']} is older than {newest}")
        elif line["state"] != state:
            kept.append(line)
            last[line["digest"]] = (line["ts"], line["state"])
    if kept:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as out:
            out.write(
                "".join(json.dumps(line, ensure_ascii=False) + "\n" for line in kept)
            )
    return len(kept), stale
