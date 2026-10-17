"""The regime picks the rule set (D-21), by file name: `<playbooks>/<regime>.yaml`.

uske knows no regime: a repository adds one by adding its file. What uske reads in a playbook is
the `id` of its tiers and the rules tagged `curable`; the schema stays `regis`'s to check.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from uske.outcomes import TIERS

# a label value becomes a file name: never a path (`../x`)
REGIME = re.compile(r"[a-z0-9][a-z0-9-]*")
TIER_IDS = frozenset(TIERS)
CURABLE = "curable"


class PlaybookError(Exception):
    """A playbooks directory uske cannot route to: a technical failure."""


def resolve(track: str | None, playbooks_dir: str | Path) -> Path | None:
    """The playbook for `track`, or None: a regime without its file is never evaluated."""
    if not track or not REGIME.fullmatch(track):
        return None
    root = Path(playbooks_dir).resolve()
    path = (root / f"{track}.yaml").resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


def curable(playbook: dict) -> frozenset[str]:
    """Slugs of the rules a remediation can fix: those the playbook tags `curable`."""
    rules = (playbook.get("spec") or {}).get("rules") or []
    return frozenset(
        r["slug"]
        for r in rules
        if isinstance(r, dict) and "slug" in r and CURABLE in (r.get("tags") or [])
    )


def check(playbooks_dir: str | Path) -> None:
    """Refuse, before anything is judged, a directory whose playbooks uske could not classify."""
    root = Path(playbooks_dir)
    if not root.is_dir():
        raise PlaybookError(f"{root}: not a directory")
    for path in sorted(root.glob("*.yaml")):
        try:
            doc = yaml.safe_load(path.read_text())
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            raise PlaybookError(f"{path.name}: {exc}") from exc
        if not isinstance(doc, dict) or doc.get("kind") != "Playbook":
            raise PlaybookError(f"{path.name}: not a Playbook")
        for tier in (doc.get("spec") or {}).get("tiers") or []:
            if not isinstance(tier, dict) or tier.get("id") not in TIER_IDS:
                name = tier.get("name") if isinstance(tier, dict) else tier
                raise PlaybookError(
                    f"{path.name}: tier {name!r} has no id among {', '.join(sorted(TIER_IDS))}"
                )
