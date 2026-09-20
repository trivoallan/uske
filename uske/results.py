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
    return [c for c in candidates if states.get(c["digest"], Outcome.INCONCLUSIVE) == Outcome.INCONCLUSIVE]


def append(path: Path, new_lines: list[dict]) -> int:
    """Append in a single write; a line that repeats a digest's last state is dropped (D-27)."""
    states = last_states(read(path))
    kept = []
    for line in new_lines:
        if states.get(line["digest"]) != line["state"]:
            kept.append(line)
            states[line["digest"]] = line["state"]
    if kept:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as out:
            out.write("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in kept))
    return len(kept)
