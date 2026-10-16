"""Turn a `regis` report into one of four outcomes, failing closed (D-23)."""

from __future__ import annotations

from dataclasses import dataclass
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

    outcome = TIERS.get(result.get("tier"))
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
    """Whether a refusal can be remediated: the tier is "Transformation requise" (never
    Quarantaine: the playbook said nothing repairs it), at least one failed rule is repairable,
    and every failed critical rule is. An unfinished rule is not a failure here; classify has
    already made an incomplete critical rule inconclusive (D-23)."""
    if not slugs or not isinstance(report, dict):
        return False
    results = report.get("playbooks") or []
    if not results or not isinstance(results[0], dict):
        return False
    result = results[0]
    if TIERS.get(result.get("tier")) is not Outcome.TRANSFORMATION_REQUIRED:
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
    meaning: str  # prose, so French (SDR-0002): docs/reference/raisons.md is generated from it
    action: str


BETTER_TIER_MISSED = "uske/better-tier-missed:"

# Every reason uske writes. tests/test_reasons.py fails on a reason literal missing here.
REASONS = (
    Reason(
        "<provider>/<criterion>",
        (Outcome.QUARANTINE, Outcome.TRANSFORMATION_REQUIRED),
        "La première règle critique du playbook qui a échoué. C'est la première, pas la seule "
        "cause : le report les donne toutes.",
        "Lire la règle dans le report, et sa définition dans la référence des règles de "
        "`regis` (`docs/reference/rules`).",
    ),
    Reason(
        "<provider>/<criterion>",
        (Outcome.INCONCLUSIVE,),
        "Une règle critique n'a pas abouti : un outil a échoué, ou une donnée manquait. "
        "Rien n'est décidé sur l'image (D-23).",
        "Lire dans le report pourquoi la règle est `incomplete`. Le prochain criblage la rejuge.",
    ),
    Reason(
        BETTER_TIER_MISSED + "<provider>/<criterion>",
        (Outcome.INCONCLUSIVE,),
        "Aucune règle critique n'a échoué, mais cette règle non critique n'a pas abouti : "
        "l'image a peut-être manqué un meilleur tier. Une évaluation qui ne conclut pas ne "
        "décide rien (D-23).",
        "Lire dans le report pourquoi la règle est `incomplete`. L'image est peut-être saine ; "
        "le prochain criblage la rejuge.",
    ),
    Reason(
        "regis/exit-1",
        (Outcome.INCONCLUSIVE,),
        "`regis` a échoué techniquement, après les nouvelles tentatives d'Argo. Ce n'est pas "
        "un verdict sur l'image.",
        "Lire les journaux de l'étape `regis` du workflow.",
    ),
    Reason(
        "regis/exit-3",
        (Outcome.INCONCLUSIVE,),
        "L'appel à `regis` était mal formé : les métadonnées ne satisfont pas un schéma "
        "déclaré par le playbook. Ce n'est pas un verdict sur l'image.",
        "Corriger le playbook ou les métadonnées ; le report liste les champs en défaut.",
    ),
    Reason(
        "regis/exit-<N>",
        (Outcome.INCONCLUSIVE,),
        "`regis` s'est arrêté sur un autre code (2 : ligne de commande refusée).",
        "Lire les journaux de l'étape `regis` du workflow.",
    ),
    Reason(
        "regis/no-report",
        (Outcome.INCONCLUSIVE,),
        "`regis` n'a laissé aucun report lisible.",
        "Lire les journaux de l'étape `regis`, puis vérifier le volume de travail.",
    ),
    Reason(
        "regis/no-verdict",
        (Outcome.INCONCLUSIVE,),
        "Le report ne contient aucun résultat de playbook.",
        "Vérifier que le workflow passe bien un playbook à `regis`.",
    ),
    Reason(
        "regis/unknown-tier",
        (Outcome.INCONCLUSIVE,),
        "Le tier rendu n'est aucun de ceux que `uske` connaît : "
        + ", ".join(f"`{name}`" for name in TIERS)
        + ".",
        "Aligner le nom des tiers du playbook sur cette liste.",
    ),
    Reason(
        "uske/unknown-track",
        (Outcome.INCONCLUSIVE,),
        "La politique désigne un régime sans playbook connu : l'image n'a pas été évaluée "
        "(D-21).",
        "Ajouter le playbook de ce régime, ou corriger le régime de la politique.",
    ),
    Reason(
        "uske/remediation-refused",
        (Outcome.QUARANTINE,),
        "Ligne de clôture sur la source : son image réparée a été jugée et refusée. Une seule "
        "tentative par source ; ce n'est pas un nouveau verdict sur la source (SDR-0016).",
        "Lire le report de l'image réparée (clé `rebuilt`). Pour réessayer, rouvrir la source.",
    ),
    Reason(
        "uske/rebuild-refused",
        (Outcome.QUARANTINE,),
        "Ancienne ligne de clôture, écrite avant la réparation sur ordre : l'image reconstruite "
        "de la source a été jugée et refusée (SDR-0016). Les nouvelles lignes disent "
        "`uske/remediation-refused`.",
        "Lire le report de l'image reconstruite (clé `rebuilt`). Pour réessayer, rouvrir la "
        "source.",
    ),
    Reason(
        "uske/remediation-undeclared",
        (Outcome.QUARANTINE,),
        "La source était réparable selon le régime, mais l'import de la politique ne déclare "
        "aucune étape `remediate:` : `knock` a retenu l'opération.",
        "Déclarer `remediate:` dans la politique, puis rouvrir la source ; ou retirer la règle "
        "de la liste réparable du régime.",
    ),
    Reason(
        "uske/no-transit",
        (Outcome.INCONCLUSIVE,),
        "La source était à réparer, mais aucun transit n'était configuré pour tenir l'image "
        "réparée avant son verdict : l'opération a été retirée. Les copies du criblage ont été "
        "placées.",
        "Nommer le transit du workflow. Le prochain criblage rejuge la source.",
    ),
    Reason(
        "uske/reopened",
        (Outcome.INCONCLUSIVE,),
        "Ligne écrite à la main : une personne a rouvert la source (SDR-0016).",
        "Rien : le prochain criblage la rejuge.",
    ),
    Reason(
        "",
        (Outcome.DIRECT_PLACEMENT, Outcome.TRANSFORMATION_REQUIRED),
        "Aucune raison. En `transformation-required`, le tier vient d'une condition du "
        "playbook qui ne nomme aucune règle critique échouée.",
        "Rien pour un placement direct ; sinon, lire le report.",
    ),
)


def reference() -> str:
    """docs/reference/raisons.md, generated: the page cannot drift from the code."""
    out = [
        "# Raisons du journal",
        "",
        "<!-- Engendré par `uv run python -m uske.outcomes`. Ne pas modifier à la main. -->",
        "",
        "Chaque ligne du journal porte un état et, souvent, une raison. **Lisez le couple** :",
        "une même raison ne dit pas la même chose sous deux états. `<...>` marque une partie",
        "remplie à l'écriture ; `<provider>/<criterion>` est une règle du playbook.",
        "",
        "| Raison | État | Ce qu'elle dit | Que faire |",
        "| --- | --- | --- | --- |",
    ]
    for r in REASONS:
        code = f"`{r.code}`" if r.code else "*(aucune)*"
        states = ", ".join(f"`{s.value}`" for s in r.states)
        out.append(f"| {code} | {states} | {r.meaning} | {r.action} |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":  # pragma: no cover
    print(reference(), end="")
