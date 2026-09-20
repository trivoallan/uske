"""knock's gate (D-30, form b; knock ADR 0051): knock plans, the orchestrator judges, knock applies.

`knock reconcile --plan-out` writes a ReconcilePlan: one operation per import, update or rebuild,
each with the source digest it would copy. The orchestrator has those digests judged and returns
the plan minus the refused operations; `knock reconcile --apply-plan` applies an operation only if
(policy, destination, tag, kind, source digest) is still in it. A tag republished upstream changes
digest and is withheld.
"""

from __future__ import annotations

import copy

from uske.outcomes import Outcome
from uske.policies import Policy
from uske.results import last_states


def prepare(policy: Policy) -> dict:
    """The policy handed to knock: under --apply-plan, admit signs only approved operations (D-33).

    Only this working copy is marked; a signature is never removed, so never the source policy.
    """
    doc = copy.deepcopy(policy.document)
    doc.setdefault("spec", {})["admit"] = True
    return doc


def operations(plan: dict, policy: Policy) -> list[dict]:
    return [op for op in plan.get("operations") or [] if op.get("policy") == policy.name]


def candidates(plan: dict, policy: Policy) -> list[dict]:
    """One candidate per source digest: a decision is per digest (D-24)."""
    seen: dict[str, dict] = {}
    for op in operations(plan, policy):
        seen.setdefault(op["sourceDigest"], {"ref": f"{op['source']}:{op['sourceTag']}", "digest": op["sourceDigest"]})
    return list(seen.values())


def approve(plan: dict, policy: Policy, lines: list[dict]) -> dict:
    """The plan minus every operation whose source digest is not direct-placement."""
    states = last_states(lines)
    kept = [op for op in operations(plan, policy) if states.get(op["sourceDigest"]) == Outcome.DIRECT_PLACEMENT]
    return {**plan, "operations": kept}
