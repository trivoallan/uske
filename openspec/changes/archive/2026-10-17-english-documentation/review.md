# Review

## Grilles retenues

- **DevEx** : le livrable se consomme. Le lecteur extérieur lit le README, l'architecture et la page
  des raisons, et la personne qui exploite lit la sortie de `uske decisions`.
- La revue d'ingénierie n'est pas retenue : aucune décision `irréversible`, et le plan tient en une
  merge request.

`/plan-devex-review` n'a pas été lancée. La grille a été appliquée à la main, sur `proposal.md` et
le delta `decision-lookup`.

## Findings et traitement

| # | Grille · dimension | Finding | Sévérité | Traitement |
| --- | --- | --- | --- | --- |
| 1 | DevEx · cohérence du vocabulaire | Traduire page par page laisse chaque page choisir son mot (« screening », « vetting », « scan »). Le lecteur croit alors à trois concepts différents. | Haute | Le glossaire FR→EN est la première tâche. Une tâche de relecture finale vérifie chaque terme du glossaire dans toutes les pages traduites et dans la sortie du CLI. |
| 2 | DevEx · liens | Le renommage `raisons.md` → `reasons.md` casse les liens du README, de `uske/outcomes.py` et de `tests/test_reasons.py`. Aucun ADR gelé ne cite la page. | Moyenne | Mettre à jour les trois références dans le même commit que le renommage. |
| 3 | DevEx · travaux parallèles | Deux worktrees en cours (`screen-fan-out`, `placed-on-promote`) modifient `uske/outcomes.py`. `screen-fan-out` ajoute aussi `docs/how-to/operate.md`, en français. Le change qui fusionne en second hérite d'un conflit, ou réintroduit du français. | Haute | Tâche dédiée : au rebase sur `main`, traduire toute page ou entrée de la table des raisons arrivée entre-temps. Signaler dans la merge request l'ordre de fusion avec ces deux branches. |
| 4 | DevEx · stabilité de la sortie | Un script qui lirait la sortie `text` pour y chercher « antidatée » casserait. Le contrat machine reste le format `json`, qui porte `"backdated": true` et ne change pas. | Basse | La note de version signale le changement des deux marques. Aucun autre traitement. |
| 5 | DevEx · lisibilité de la démo | Les noms de tiers (`Placement direct`, `Quarantaine`) restent en français et apparaissent dans la page des raisons (`regis/unknown-tier`). | Basse | Hors périmètre, c'est un contrat avec les playbooks. La page anglaise dit explicitement que ces noms sont ceux écrits par les playbooks. |

## Critère d'achèvement

- `git grep -nP '[àâçéèêëîïôûùüœ]'` ne trouve plus de prose française dans `README.md`,
  `docs/architecture/`, `docs/reference/`, `uske/*.py` (hors noms de tiers des playbooks) ni
  `tests/golden/`.
- Chaque terme du glossaire a un équivalent anglais, et c'est le seul employé dans les pages
  traduites.
- Les tests passent, golden tests régénérés compris, et `docs/reference/reasons.md` est identique à
  la sortie de `uv run python -m uske.outcomes`.
- `SDR-0022` est `accepted`, et ses valeurs portent leur provenance.
