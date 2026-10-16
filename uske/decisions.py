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
    "run",
    "source",
    "rebuilt",
)
ADDED = ("policy", "backdated")  # what this module adds to a line
STATES = {o.value for o in Outcome}
# one pass, so an entity's own `#` and `;` are never escaped again
MERMAID = str.maketrans(
    {"#": "#35;", "%": "#37;", ":": "#58;", ";": "#59;", "\r": " ", "\n": " "}
)


class JournalError(Exception):
    """A journal that cannot be read in full: nothing is rendered."""


def _no_constant(name: str):
    raise ValueError(f"{name} is not valid JSON")


def read_journal(path: Path) -> list[dict]:
    """Parse one journal strictly; any unreadable file or line raises JournalError."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise JournalError(f"{path}: {exc}") from exc
    lines = []
    # split on "\n" only: splitlines() would also cut on U+2028 and friends
    for number, raw in enumerate(text.split("\n"), 1):
        raw = raw.removesuffix("\r")
        if not raw.strip():
            continue
        where = f"{path}:{number}"
        try:
            line = json.loads(raw, parse_constant=_no_constant)
        except json.JSONDecodeError as exc:
            raise JournalError(f"{where}: {exc.msg}") from exc
        except ValueError as exc:
            raise JournalError(f"{where}: {exc}") from exc
        if not isinstance(line, dict):
            raise JournalError(f"{where}: not a JSON object")
        missing = [k for k in REQUIRED if k not in line]
        if missing:
            raise JournalError(f"{where}: missing {', '.join(missing)}")
        for key in WRITTEN:  # what is rendered as text must be text (eng review, D16)
            if key in line and not isinstance(line[key], str):
                raise JournalError(f"{where}: {key} must be a string")
        try:
            # the round trip rejects what strptime forgives, such as "2026-1-1T0:0:0Z"
            if datetime.strptime(line["ts"], TS).strftime(TS) != line["ts"]:
                raise ValueError(line["ts"])
        except ValueError as exc:
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


def _family(lines: list[dict], wanted: set[str]) -> set[str]:
    """The digests linked to `wanted` by `source` or `rebuilt`, both ways, until nothing is added:
    a rebuild brings its source (the first gate) and its siblings, a source its rebuilds."""
    family = set(wanted)
    while True:
        grown = set(family)
        for l in lines:
            links = {l.get("source"), l.get("rebuilt")} - {None}
            if l["digest"] in family:
                grown |= links
            elif links & family:
                grown.add(l["digest"])
        if grown == family:
            return family
        family = grown


def select(
    lines: list[dict],
    image: str | None = None,
    states: set[str] | None = None,
    since: date | None = None,
) -> list[dict]:
    """The lines on an image and its rebuild family, in a state, from a UTC day on."""
    if image is not None:
        digest = digest_of(image)
        # ponytail: exact match only; a short reference could name another repository
        wanted = (
            {digest}
            if digest
            else {l["digest"] for l in lines if l.get("ref") == image}
        )
        family = _family(lines, wanted)
        lines = [l for l in lines if l["digest"] in family]
    if states is not None:
        lines = [l for l in lines if l["state"] in states]
    if since is not None:
        day = since.isoformat()
        lines = [l for l in lines if l["ts"][:10] >= day]
    return lines


def suggest(lines: list[dict], image: str) -> list[str]:
    """Full references in the journal that end with `/<image>`: a hint, never a match."""
    return sorted({l["ref"] for l in lines if l.get("ref", "").endswith("/" + image)})


def groups(lines: list[dict]) -> dict[tuple[str, str], list[dict]]:
    """(policy, digest) -> its lines, groups in the order of their first line."""
    out: dict[tuple[str, str], list[dict]] = {}
    for line in lines:
        out.setdefault((line["policy"], line["digest"]), []).append(line)
    return out


def unsigned(line: dict) -> bool:
    """A decision uske did not take (another state, or a reopening), with nobody named for it."""
    by_hand = line["state"] not in STATES or line.get("reason") == "uske/reopened"
    return by_hand and "arbitration" not in line


def marks(line: dict) -> list[str]:
    """The labels a line carries in the renderings: backdated, unsigned."""
    return [
        mark
        for mark, on in (
            ("antidatée", line.get("backdated")),
            ("arbitrage absent", unsigned(line)),
        )
        if on
    ]


def extras(line: dict) -> list[str]:
    """`source`, `rebuilt` and every key uske does not write, as `key: value`, in file order."""
    return [
        f"{k}: {v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)}"
        for k, v in line.items()
        if k in ("source", "rebuilt") or (k not in WRITTEN and k not in ADDED)
    ]


def _flat(text: str) -> str:
    return text.replace("\r", " ").replace("\n", " ")


def render_text(lines: list[dict]) -> str:
    """Render the lines as plain text, one block per (policy, digest), one value per line."""
    blocks = []
    for (policy, digest), group in groups(lines).items():
        out = [f"== {policy} · {_flat(group[0].get('ref', '—'))} · {_flat(digest)}"]
        for line in group:
            head = f"{line['ts']}  {_flat(line['state'])}  {_flat(line.get('reason') or '—')}"
            out.append(head + "".join(f"  [{m}]" for m in marks(line)))
            out.extend(
                f"    {k}: {_flat(line[k])}"
                for k in ("run", "ruleset", "report")
                if k in line
            )
            out.extend(f"    {_flat(e)}" for e in extras(line))
        blocks.append("\n".join(out))
    return "\n\n".join(blocks)


def _cell(text: str) -> str:
    return text.replace("\r", " ").replace("\n", " ").replace("|", "\\|")


def _report(path: str | None) -> str:
    """The report cell: a path on the volume is named as such, since the ticket's reader cannot
    open it; a relative path is a file next to the journal (a repository of results)."""
    if path is None:
        return ""
    return f"`{path}` (volume uske-results)" if path.startswith("/") else f"`{path}`"


def _run_label(run: str) -> str:
    """A run is an id, or the URL of its page: the label is the id, the URL's last segment."""
    if run.startswith(("http://", "https://")):
        return run.rstrip("/").rsplit("/", 1)[-1]
    return run


def _period(line: dict) -> str:
    """The timeline period of a line: its screening, else its UTC minute."""
    if "run" in line:
        return f"run {_run_label(line['run'])}"
    return f"{line['ts'][:10]} {line['ts'][11:16]}"


def _run_cell(run: str | None) -> str:
    if run is None:
        return ""
    label = _run_label(run)
    return f"[{label}]({run})" if label != run else run


def render_md(lines: list[dict]) -> str:
    """Render the lines as Markdown: a Mermaid timeline and a table per (policy, digest)."""
    blocks = []
    for (policy, digest), group in groups(lines).items():
        ref = group[0].get("ref", "—")
        out = [
            f"## {policy} · {_flat(ref)}",
            "",
            f"`{digest}`",
            "",
            "```mermaid",
            "timeline",
        ]
        out.append(f"    title {ref.translate(MERMAID)}")
        # one period per screening (SDR-0018); a line written before the run was recorded, or
        # by hand, gets its UTC minute. Periods follow the file: a backdated event keeps its mark
        periods: dict[str, list[str]] = {}
        for line in group:
            event = f"{line['state']} — {line.get('reason') or '—'}"
            event += "".join(f" ({m})" for m in marks(line))
            periods.setdefault(_period(line), []).append(event.translate(MERMAID))
        out.extend(
            f"    {period.translate(MERMAID)} : " + " : ".join(events)
            for period, events in periods.items()
        )
        out += ["```", "", "| ts | run | state | reason | ruleset | report | details |"]
        out.append("| --- | --- | --- | --- | --- | --- | --- |")
        for line in group:
            cells = [
                line["ts"],
                _run_cell(line.get("run")),
                line["state"],
                line.get("reason") or "—",
                line.get("ruleset", ""),
                _report(line.get("report")),
                "; ".join(extras(line) + marks(line)),
            ]
            out.append("| " + " | ".join(_cell(str(c)) for c in cells) + " |")
        blocks.append("\n".join(out))
    return "\n\n".join(blocks)
