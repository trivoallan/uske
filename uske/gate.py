"""knock's gate (D-30, form b; knock ADR 0051): knock plans, uske judges, knock applies.

uske also holds the conditional of remediation: a source refused on rules its playbook tags
`curable` is handed back with a remediation order, and knock repairs that one digest; the repaired image is held in the transit and judged before it is promoted.

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
from uske.results import ResultLine, attempts, last_states, last_verdicts

MAX_ATTEMPTS = 3  # held images left without a verdict for one source, after which it is no longer remediated
REBUILD_REFUSED = (
    "uske/rebuild-refused"  # legacy: closing lines written before remediation orders
)
REMEDIATION_REFUSED = "uske/remediation-refused"
REMEDIATION_UNDECLARED = "uske/remediation-undeclared"
NO_TRANSIT = "uske/no-transit"


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


def _decide(
    op: dict, last: dict[str, dict], lines: list[dict], transit: str | None
) -> str | None:
    """`order` when the operation is handed back with a remediation order, None when it is handed
    back as is, else why it is withheld.

    A sound source is placed as knock plans it: copied, or rebuilt through its transform, which is
    not judged again. A source refused on repairable rules only is remediated, once: after the
    repaired image is refused, the closing line is not repairable any more. The same holds when
    knock replans a remediated tag (its transform changed): the order is renewed, the source is
    not judged again, and the new image is.

    A sound source on a tag knock marks `remediated: true` (the destination tag it replaces
    carries a remediation) is remediated too (D11): placed as is, the next upstream patch would
    undo the repair. uske never infers the mark from the destination; no key means unmarked.
    Refused and exhausted sources stay withheld, mark or not.
    """
    line = last.get(op["sourceDigest"]) or {}
    state = line.get("state")
    if state == Outcome.DIRECT_PLACEMENT and op.get("remediated") is not True:
        return None
    if state != Outcome.DIRECT_PLACEMENT and (
        state != Outcome.TRANSFORMATION_REQUIRED or not line.get("repairable")
    ):
        return "refused"
    if attempts(lines, op["sourceDigest"]) >= MAX_ATTEMPTS:
        return "attempts-exhausted"
    if not transit:
        return "no-transit"  # without a second gate, the repaired image would be placed unjudged
    return "order"


def approve(
    plan: dict,
    policy: Policy,
    lines: list[dict],
    transit: str | None = None,
    *,
    epoch: str = "",
    ts: str = "",
    run: str | None = None,
) -> tuple[dict, dict, list[dict]]:
    """(the plan minus every withheld operation, how many were withheld per cause, the journal
    lines this decision writes).

    An operation on a source to remediate carries `remediate: {epoch}`, the screening's epoch.
    Without a transit, it is withheld and its source is recorded inconclusive (`uske/no-transit`)
    so the next screening judges it again; copies and transform-only rebuilds still go through.
    `transit` is trusted, not checked: naming it is the workflow's promise that remediated images
    are held and judged before they are placed.
    """
    last = last_verdicts(lines)
    kept, discarded, written = [], {}, {}
    for op in operations(plan, policy):
        cause = _decide(op, last, lines, transit)
        if cause is None:
            kept.append(op)
        elif cause == "order":
            kept.append({**op, "remediate": {"epoch": epoch}})
            discarded.setdefault(
                "ordered", 0
            )  # reported apart: an order is not a withholding
        else:
            discarded[cause] = discarded.get(cause, 0) + 1
            if cause == "no-transit":
                source = last[op["sourceDigest"]]
                written.setdefault(
                    op["sourceDigest"],
                    ResultLine(
                        ts=ts,
                        ref=source.get("ref") or f"{op['source']}:{op['sourceTag']}",
                        digest=op["sourceDigest"],
                        state=Outcome.INCONCLUSIVE.value,
                        ruleset=source.get("ruleset") or "none",
                        reason=NO_TRANSIT,
                        run=run,
                    ).to_dict(),
                )
    discarded.pop("ordered", None)
    return {**plan, "operations": kept}, discarded, list(written.values())


def ordered(plan: dict) -> int:
    """How many operations of an approved plan carry a remediation order."""
    return sum(1 for op in plan.get("operations") or [] if op.get("remediate"))


def from_applied(
    applied: dict, policy: Policy, lines: list[dict], *, ts: str, run: str | None
) -> list[dict]:
    """The journal lines knock's AppliedOperations call for: a placement line linking each source
    to the digest knock wrote, and a decision on the source of an order knock could not honour."""
    last = last_verdicts(lines)
    out: list[dict] = []
    for op in applied.get("operations") or []:
        if op.get("policy") != policy.name:
            continue
        source = last.get(op["sourceDigest"]) or {}
        base = {
            "ts": ts,
            "ref": source.get("ref") or f"{op['destination']}:{op['tag']}",
            "digest": op["sourceDigest"],
            "ruleset": source.get("ruleset") or "none",
            "run": run,
        }
        reason = op.get("reason")
        if op.get("kind") == "withheld" and reason == "remediation-undeclared":
            out.append(
                ResultLine(
                    **base,
                    state=Outcome.QUARANTINE.value,
                    reason=REMEDIATION_UNDECLARED,
                ).to_dict()
            )
        elif op.get("kind") == "withheld" and reason == "remediation-unstaged":
            out.append(
                ResultLine(
                    **base, state=Outcome.INCONCLUSIVE.value, reason=NO_TRANSIT
                ).to_dict()
            )
        elif op.get("kind") in ("imported", "updated") and op.get("writtenDigest"):
            out.append(
                ResultLine(
                    **base,
                    state=source.get("state") or Outcome.DIRECT_PLACEMENT.value,
                    placed=op["writtenDigest"],
                ).to_dict()
            )
    return out


def from_promoted(
    promoted: dict, policy: Policy, lines: list[dict], *, ts: str, run: str | None
) -> list[dict]:
    """A placement line per image `knock promote` placed: the source, and the held digest, which
    promote copies by digest, so it is the digest placed. Read only once promote has succeeded.

    ponytail: all or nothing — a promote that fails on one entry records none; the failed
    entries are planned and judged again next screening, the placed ones get their line then.
    """
    last = last_verdicts(lines)
    out: list[dict] = []
    for e in entries(promoted, policy):
        source = last.get(e["sourceDigest"]) or {}
        out.append(
            ResultLine(
                ts=ts,
                ref=source.get("ref") or f"{e['source']}:{e['sourceTag']}",
                digest=e["sourceDigest"],
                state=source.get("state") or Outcome.DIRECT_PLACEMENT.value,
                ruleset=source.get("ruleset") or "none",
                run=run,
                placed=e["stagedDigest"],
            ).to_dict()
        )
    return out


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
                "epoch": e.get("epoch") or "",
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
