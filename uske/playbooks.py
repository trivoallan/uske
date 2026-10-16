"""The regime picks the rule set (D-21). The only place that knows the regimes."""

from __future__ import annotations

from pathlib import Path

# D-05, D-19: derogation and redistribution share the lightweight tier.
TABLE = {
    "standard": "version/playbook.yaml",
    "derogation": "version/playbook-allege.yaml",
    "redistribution": "version/playbook-allege.yaml",
}


def resolve(track: str | None, playbooks_dir: str | Path) -> Path | None:
    """The playbook for `track`, or None: an unknown regime is never evaluated."""
    relative = TABLE.get(track) if track else None
    return Path(playbooks_dir) / relative if relative else None


# The rules a remediation can fix, by regime: slugs of that regime's playbook. A refusal whose
# failed rules all sit here (and at least one does) becomes a remediation order; a regime absent
# from this table has nothing repairable. Slugs, not `provider/criterion`: `cve-critical` and
# `cve-high` share `cve/cve-count`.
REPAIRABLE: dict[str, frozenset[str]] = {
    "standard": frozenset({"cve-critical"}),
}


def repairable(track: str | None) -> frozenset[str]:
    """The repairable rules of `track`; none for an unknown or absent regime."""
    return REPAIRABLE.get(track or "", frozenset())
