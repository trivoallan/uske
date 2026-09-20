"""Turn a `regis` report into one of four outcomes, failing closed (D-23)."""

from __future__ import annotations

from enum import StrEnum


class Outcome(StrEnum):
    DIRECT_PLACEMENT = "direct-placement"
    TRANSFORMATION_REQUIRED = "transformation-required"
    QUARANTINE = "quarantine"
    INCONCLUSIVE = "inconclusive"


# Tier names as the playbooks in playbooks/version/ write them.
TIERS = {
    "Placement direct": Outcome.DIRECT_PLACEMENT,
    "Transformation requise puis placement": Outcome.TRANSFORMATION_REQUIRED,
    "Quarantaine": Outcome.QUARANTINE,
}


def criteria(playbook: dict) -> dict[str, str]:
    """slug -> `provider/criterion`: the report carries the slug, not the provider."""
    rules = (playbook.get("spec") or {}).get("rules") or []
    return {r["slug"]: f"{r.get('provider')}/{r.get('criterion')}" for r in rules if "slug" in r}


def classify(report: dict | None, playbook: dict, regis_exit: int = 0) -> tuple[Outcome, str | None]:
    """(outcome, reason). Anything short of a known tier on a complete evaluation is inconclusive."""
    if regis_exit != 0:
        return Outcome.INCONCLUSIVE, f"regis/exit-{regis_exit}"
    if not isinstance(report, dict):
        return Outcome.INCONCLUSIVE, "regis/no-report"
    results = report.get("playbooks") or []
    if not results or not isinstance(results[0], dict):
        return Outcome.INCONCLUSIVE, "regis/no-verdict"
    result = results[0]
    rules = [r for r in result.get("rules") or [] if isinstance(r, dict)]
    names = criteria(playbook)

    def reason(rule: dict) -> str:
        return names.get(rule.get("slug"), rule.get("slug") or "unknown")

    critical = [r for r in rules if str(r.get("level", "")).lower() == "critical"]
    incomplete = next((r for r in critical if r.get("status") == "incomplete"), None)
    if incomplete:
        return Outcome.INCONCLUSIVE, reason(incomplete)

    outcome = TIERS.get(result.get("tier"))
    if outcome is None:
        return Outcome.INCONCLUSIVE, "regis/unknown-tier"
    if outcome is Outcome.DIRECT_PLACEMENT:
        return outcome, None
    failed = next((r for r in critical if not r.get("passed")), None)
    return outcome, reason(failed) if failed else None
