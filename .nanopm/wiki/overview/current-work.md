---
type: overview
section: plan
generated: 2026-09-20
sources: [wiki/docs/objectives.md, wiki/docs/strategy.md, wiki/docs/roadmap.md]
---
# Plan Brief
Generated 2026-09-20 · Project: uske · Sources: objectives.md, strategy.md, roadmap.md

## What we're betting on
Le squelette marchant tel qu'il est — placement direct seul, échec fermé — tient sur le vrai Harbor et le vrai Argo de l'employeur avec une surcouche de déploiement et des correctifs mineurs, et il y fait un travail utile : sur le catalogue réel, au moins 70 % des empreintes jugées obtiennent *placement direct* et un screening dure moins que son intervalle de planification. Si ce pari tient, un premier screening planifié va au bout d'ici le 2026-10-31 et dix d'affilée sans l'auteur d'ici le 2026-12-15 — sans reconcevoir ni le journal, ni la barrière, ni le couplage à `regis` et `knock`. Le risque déclaré : le réel casse le squelette là où les fixtures n'ont jamais regardé, ou pire, ne casse rien mais ne sert à rien (des screenings verts qui ne placent presque rien).
_More detail: `.nanopm/wiki/docs/strategy.md`_

## What we're aiming for
Période 2026-09-21 → 2026-12-31, deux objectifs. **Objectif 1 — faire tourner un screening réel chez l'employeur, sans l'auteur** : KR1 catalogue réel jugé à blanc avec ≥70 % en placement direct avant le 2026-10-04 ; KR2 un premier screening planifié va au bout sur le vrai Harbor avant le 2026-10-31 ; KR3 dix screenings planifiés consécutifs sans intervention de l'auteur avant le 2026-12-15. **Objectif 2 — faire qu'un refus s'explique sans l'auteur** : KR1 le premier refus réel est observé et consigné ; KR2 une sous-commande lit le journal pour un humain avant le 2026-11-30 ; KR3 un collègue explique un refus réel en moins d'une minute avant le 2026-12-15.
_More detail: `.nanopm/wiki/docs/objectives.md`_

## What we're building now
**NOW** : (1) un passage à blanc sur le catalogue réel — sans `--apply-plan` — pour savoir quelle part du catalogue est plaçable, au plus tard le 2026-09-27 (test le moins cher de la stratégie) ; (2) `premier-screening-deploye` — livrer la surcouche `deploy/<cible>` (politique, projet Harbor, namespace Argo, compte robot) pour qu'un screening planifié tourne seul sur le vrai Harbor, au plus tard le 2026-10-31. Capacité dépassée d'environ 0,5 semaine ; les deux items sont séquentiels, le passage à blanc conditionne la suite. **NEXT** (aperçu) : dix screenings consécutifs sans l'auteur, observation du premier refus réel, la sous-commande `retrouver-un-refus`, et un collègue qui explique un refus seul.
_More detail: `.nanopm/wiki/docs/roadmap.md`_

## What we're saying no to
- L'issue quarantaine qui agit — `approve` retient déjà tout ce qui n'est pas placement direct ; revisit si le passage à blanc montre plus de 30 % hors placement direct, ou qu'un pair place à la main une image refusée.
- Ouvrir le dépôt et chercher des adopteurs — rien n'a encore tourné en réel ; revisit après dix screenings consécutifs sans l'auteur.
- Les issues « transformation requise » et « non concluante » — revisit quand le journal réel montrera laquelle revient le plus souvent.
- Le travail de méthode hors change en cours (sections d'arc42 restantes, nouveaux ADR) — revisit seulement si un change en cours déplace ce qu'une section décrit.
- Une console ou un tableau de bord — c'est l'anti-persona ; revisit si un second registre, tenu par quelqu'un d'autre, tourne en production.
- Une colle générique pour d'autres juges ou placeurs — `uske` ne connaît que `regis` et `knock` ; revisit si l'employeur impose un autre juge ou placeur.
- **Pas de suppression des scripts maison** avant dix screenings allés au bout et un collègue ayant rejoué seul un screening échoué — ils restent le seul retour en arrière (`.nanopm/wiki/docs/strategy.md`).

## Not yet planned
Aucune base d'opportunités n'existe encore (`.nanopm/wiki/entities/opportunities/INDEX.md` est absent) : pas de signal utilisateur classé pour nourrir le prochain cycle de planification au-delà de ce que `strategy.md` et `roadmap.md` mentionnent déjà eux-mêmes (aucun retour utilisateur à ce jour, les deux items NOW sont précisément ce qui en produira).
