"""knock's gate (D-30, form b; knock ADR 0051): knock plans, uske judges, knock applies.

`knock reconcile --plan-out` writes a ReconcilePlan: one operation per import, update or rebuild,
each with the source digest it would copy. uske has those digests judged and returns
the plan minus the refused operations; `knock reconcile --apply-plan` applies an operation only if
(policy, destination, tag, kind, source digest) is still in it. A tag republished upstream changes
digest and is withheld.
"""

from __future__ import annotations

import copy

from uske.outcomes import Outcome
from uske.policies import Policy
from uske.results import attempts, last_states

MAX_ATTEMPTS = 3  # held images left without a verdict for one source, after which it is no longer rebuilt
REBUILD_REFUSED = "uske/rebuild-refused"


def prepare(policy: Policy) -> dict:
    """The policy handed to knock: under --apply-plan, admit signs only approved operations (D-33).

    Only this working copy is marked; a signature is never removed, so never the source policy.
    """
    doc = copy.deepcopy(policy.document)
    doc.setdefault("spec", {})["admit"] = True
    return doc


def operations(plan: dict, policy: Policy) -> list[dict]:
    return [
        op for op in plan.get("operations") or [] if op.get("policy") == policy.name
    ]


def candidates(plan: dict, policy: Policy) -> list[dict]:
    """One candidate per source digest: a decision is per digest (D-24)."""
    seen: dict[str, dict] = {}
    for op in operations(plan, policy):
        seen.setdefault(
            op["sourceDigest"],
            {"ref": f"{op['source']}:{op['sourceTag']}", "digest": op["sourceDigest"]},
        )
    return list(seen.values())


def _discarded(
    op: dict, states: dict[str, str], lines: list[dict], transit: str | None
) -> str | None:
    """Why an operation is withheld, or None when it is handed back to knock."""
    rebuilt = (
        op.get("transformed") is True
    )  # absent means a copy: knock did not say it rebuilds
    state = states.get(op["sourceDigest"])
    if state == Outcome.TRANSFORMATION_REQUIRED:
        if not transit:
            return "no-transit"  # without a second gate, the rebuilt output would be placed unjudged
        if not rebuilt:
            return "not-rebuilt"
    elif state != Outcome.DIRECT_PLACEMENT:
        return "refused"
    if rebuilt and attempts(lines, op["sourceDigest"]) >= MAX_ATTEMPTS:
        return "attempts-exhausted"
    return None


def approve(
    plan: dict, policy: Policy, lines: list[dict], transit: str | None = None
) -> tuple[dict, dict]:
    """(the plan minus every withheld operation, how many were withheld per cause).

    `transit` is trusted, not checked: naming it is the workflow's promise that rebuilt images
    are held and judged before they are placed.
    """
    states = last_states(lines)
    kept, discarded = [], {}
    for op in operations(plan, policy):
        cause = _discarded(op, states, lines, transit)
        if cause is None:
            kept.append(op)
        else:
            discarded[cause] = discarded.get(cause, 0) + 1
    return {**plan, "operations": kept}, discarded


def entries(staged: dict, policy: Policy) -> list[dict]:
    return [e for e in staged.get("entries") or [] if e.get("policy") == policy.name]


def staged_candidates(staged: dict, policy: Policy) -> list[dict]:
    """One candidate per held digest: what knock built is judged where it is held."""
    seen: dict[str, dict] = {}
    for e in entries(staged, policy):
        seen.setdefault(
            e["stagedDigest"],
            {
                "ref": f"{e['staged']}:{e['tag']}",
                "digest": e["stagedDigest"],
                "source": e["sourceDigest"],
                "sourceRef": f"{e['source']}:{e['sourceTag']}",
            },
        )
    return list(seen.values())


def approve_staged(staged: dict, policy: Policy, lines: list[dict]) -> dict:
    """The held images minus every one that is not direct-placement. Kept entries are untouched."""
    states = last_states(lines)
    kept = [
        e
        for e in entries(staged, policy)
        if states.get(e["stagedDigest"]) == Outcome.DIRECT_PLACEMENT
    ]
    return {**staged, "entries": kept}
