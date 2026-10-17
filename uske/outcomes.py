"""Turn a `regis` report into one of four outcomes, failing closed (D-23)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Outcome(StrEnum):
    DIRECT_PLACEMENT = "direct-placement"
    TRANSFORMATION_REQUIRED = "transformation-required"
    QUARANTINE = "quarantine"
    INCONCLUSIVE = "inconclusive"


# Tier `id` -> outcome: the playbook's own names are labels for humans, in any language.
# inconclusive is no tier: it says an evaluation did not finish (D-23).
TIERS = {
    o.value: o
    for o in (
        Outcome.DIRECT_PLACEMENT,
        Outcome.TRANSFORMATION_REQUIRED,
        Outcome.QUARANTINE,
    )
}


def criteria(playbook: dict) -> dict[str, str]:
    """slug -> `provider/criterion`: the report carries the slug, not the provider."""
    rules = (playbook.get("spec") or {}).get("rules") or []
    return {
        r["slug"]: f"{r.get('provider')}/{r.get('criterion')}"
        for r in rules
        if "slug" in r
    }


def classify(
    report: dict | None, playbook: dict, regis_exit: int = 0
) -> tuple[Outcome, str | None]:
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

    outcome = TIERS.get(result.get("tier_id"))
    if outcome is None:
        return Outcome.INCONCLUSIVE, "regis/unknown-tier"
    if outcome is Outcome.DIRECT_PLACEMENT:
        return outcome, None
    failed = next((r for r in critical if not r.get("passed")), None)
    if failed is None:
        # nothing critical failed: if a rule did not finish, the better tier was missed on it,
        # and an evaluation that did not conclude decides nothing (D-23)
        unfinished = next((r for r in rules if r.get("status") == "incomplete"), None)
        if unfinished:
            # its own reason: the same slug under inconclusive also means a critical rule did
            # not finish, and the reader must tell the two apart
            return Outcome.INCONCLUSIVE, BETTER_TIER_MISSED + reason(unfinished)
    return outcome, reason(failed) if failed else None


def repairable(report: dict | None, slugs: frozenset[str]) -> bool:
    """Whether a refusal can be remediated: the tier is `transformation-required` (never
    `quarantine`: the playbook said nothing repairs it), at least one failed rule is curable,
    and every failed critical rule is. An unfinished rule is not a failure here; classify has
    already made an incomplete critical rule inconclusive (D-23)."""
    if not slugs or not isinstance(report, dict):
        return False
    results = report.get("playbooks") or []
    if not results or not isinstance(results[0], dict):
        return False
    result = results[0]
    if TIERS.get(result.get("tier_id")) is not Outcome.TRANSFORMATION_REQUIRED:
        return False
    failed = [
        r
        for r in result.get("rules") or []
        if isinstance(r, dict)
        and not r.get("passed")
        and r.get("status") != "incomplete"
    ]
    critical = {
        r.get("slug") for r in failed if str(r.get("level", "")).lower() == "critical"
    }
    return any(r.get("slug") in slugs for r in failed) and critical <= slugs


@dataclass(frozen=True)
class Reason:
    """One reason as the journal writes it; `<...>` marks a part filled in when written."""

    code: str
    states: tuple[Outcome, ...]
    meaning: str  # documentation, so English (SDR-0022): docs/reference/reasons.md is built from it
    action: str


BETTER_TIER_MISSED = "uske/better-tier-missed:"
HOW = "[`docs/explanation/how-it-works.md`](../explanation/how-it-works.md#rebuilds-and-repairs)"  # where reopening a source is shown

# Every reason uske writes. tests/test_reasons.py fails on a reason literal missing here.
REASONS = (
    Reason(
        "<provider>/<criterion>",
        (Outcome.QUARANTINE, Outcome.TRANSFORMATION_REQUIRED),
        "The first critical rule of the playbook that failed. It is the first cause, not the "
        "only one: the report lists them all.",
        "Read the rule in the report, and its definition in the `regis` rules reference "
        "(`docs/reference/rules`).",
    ),
    Reason(
        "<provider>/<criterion>",
        (Outcome.INCONCLUSIVE,),
        "A critical rule did not finish: a tool failed, or some data was missing. Nothing is "
        "decided about the image (D-23).",
        "Read in the report why the rule is `incomplete`. The next screening judges it again.",
    ),
    Reason(
        BETTER_TIER_MISSED + "<provider>/<criterion>",
        (Outcome.INCONCLUSIVE,),
        "No critical rule failed, but this non-critical rule did not finish: the image may "
        "have missed a better tier. An evaluation that does not conclude decides nothing "
        "(D-23).",
        "Read in the report why the rule is `incomplete`. The image may be sound; the next "
        "screening judges it again.",
    ),
    Reason(
        "regis/exit-1",
        (Outcome.INCONCLUSIVE,),
        "`regis` failed technically, after Argo's retries. This is not a verdict on the image.",
        "Read the logs of the workflow's `regis` step.",
    ),
    Reason(
        "regis/exit-3",
        (Outcome.INCONCLUSIVE,),
        "The call to `regis` was malformed: the metadata does not satisfy a schema the "
        "playbook declares. This is not a verdict on the image.",
        "Fix the playbook or the metadata; the report lists the failing fields.",
    ),
    Reason(
        "regis/exit-<N>",
        (Outcome.INCONCLUSIVE,),
        "`regis` stopped on another code (2: command line rejected).",
        "Read the logs of the workflow's `regis` step.",
    ),
    Reason(
        "regis/no-report",
        (Outcome.INCONCLUSIVE,),
        "`regis` left no readable report.",
        "Read the logs of the `regis` step, then check the work volume.",
    ),
    Reason(
        "regis/no-verdict",
        (Outcome.INCONCLUSIVE,),
        "The report holds no playbook result.",
        "Check that the workflow passes a playbook to `regis`.",
    ),
    Reason(
        "regis/unknown-tier",
        (Outcome.INCONCLUSIVE,),
        "The tier returned carries no `id`, or one `uske` does not know: "
        + ", ".join(f"`{tier_id}`" for tier_id in TIERS)
        + ". The tier's `name` is a label and is never read.",
        "Give the playbook's tier this `id`, and check that `regis` writes `tier_id` in its "
        "report.",
    ),
    Reason(
        "uske/unknown-track",
        (Outcome.INCONCLUSIVE,),
        "The policy names a track with no known playbook: the image was not evaluated (D-21).",
        "Add the playbook for this track, or fix the policy's track.",
    ),
    Reason(
        "uske/remediation-refused",
        (Outcome.QUARANTINE,),
        "Closing line on the source: its remediated image was judged and refused. One attempt "
        "per source; this is not a new verdict on the source (SDR-0016).",
        "The line's `rebuilt` key is the digest of the refused image: `uske decisions` on the "
        "source shows that image's line and report. To try again, reopen the source: append "
        "a `uske/reopened` line by hand, as " + HOW + " shows.",
    ),
    Reason(
        "uske/rebuild-refused",
        (Outcome.QUARANTINE,),
        "Older closing line, written before remediation on order: the source's rebuilt image "
        "was judged and refused (SDR-0016). New lines say `uske/remediation-refused`.",
        "The line's `rebuilt` key is the digest of the refused image: `uske decisions` on the "
        "source shows that image's line and report. To try again, reopen the source, as "
        + HOW
        + " shows.",
    ),
    Reason(
        "uske/remediation-undeclared",
        (Outcome.QUARANTINE,),
        "The track made the source repairable, but the policy's import declares no "
        "`remediate:` step: `knock` held the operation back.",
        "Declare `remediate:` in the policy, then reopen the source ("
        + HOW
        + "); or remove "
        "the rule from the track's repairable list.",
    ),
    Reason(
        "uske/no-transit",
        (Outcome.INCONCLUSIVE,),
        "The source needed remediation, but no transit was configured to hold the remediated "
        "image until its verdict: the operation was withdrawn. The screening's copies were "
        "placed.",
        "Name the workflow's transit. The next screening judges the source again.",
    ),
    Reason(
        "uske/reopened",
        (Outcome.INCONCLUSIVE,),
        "Line written by hand: someone reopened the source (SDR-0016), as "
        + HOW
        + " shows.",
        "Nothing: the next screening judges it again.",
    ),
    Reason(
        "",
        (Outcome.DIRECT_PLACEMENT, Outcome.TRANSFORMATION_REQUIRED),
        "No reason. Under `transformation-required`, the tier comes from a playbook condition "
        "that names no failed critical rule.",
        "Nothing for a direct placement; otherwise, read the report.",
    ),
)


def reference() -> str:
    """docs/reference/reasons.md, generated: the page cannot drift from the code."""
    out = [
        "# Journal reasons",
        "",
        "<!-- Generated by `uv run python -m uske.outcomes`. Do not edit by hand. -->",
        "",
        "Every journal line carries a state and, often, a reason. A state is one of the four",
        "outcomes `uske` writes (`direct-placement`, `transformation-required`, `quarantine`,",
        "`inconclusive`), or a state a person writes by hand to record a decision `uske` did",
        "not take (`placed-by-exception`, `abandoned`). A reopening is also written by hand,",
        "under `inconclusive` (reason `uske/reopened`).",
        "",
        "Under `inconclusive`, nothing is placed, as for a refusal, but nothing is decided",
        "either: the image is not refused, and the next screening judges it again.",
        "",
        "**Read the state and the reason as a pair**: the same reason does not say the same",
        "thing under two states. `<...>` marks a part filled in when the line is written;",
        "`<provider>/<criterion>` is a playbook rule.",
        "",
        "| Reason | State | What it says | What to do |",
        "| --- | --- | --- | --- |",
    ]
    for r in REASONS:
        code = f"`{r.code}`" if r.code else "*(none)*"
        states = ", ".join(f"`{s.value}`" for s in r.states)
        out.append(f"| {code} | {states} | {r.meaning} | {r.action} |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":  # pragma: no cover
    print(reference(), end="")
