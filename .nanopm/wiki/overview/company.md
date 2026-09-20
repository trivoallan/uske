---
type: overview
section: define
generated: 2026-09-20
sources: [vision-mission.md, business-model.md, org.md, product.md, personas.md]
---

# PM Context Brief
Generated 2026-09-20 · Project: uske · Sources: vision-mission.md, business-model.md, org.md, product.md, personas.md

## What we do
`uske` est une CLI Python à onze sous-commandes, orchestrée par un `CronWorkflow` Argo, qui bat la mesure entre deux outils voisins : elle fait écrire son plan à `knock` (qui place les images dans un registre interne), fait juger chaque empreinte encore due par `regis` (qui dit si une image est saine), puis renvoie à `knock` le plan moins les refus et ajoute une ligne à un journal append-only par décision. `uske` ne juge rien et ne place rien elle-même — elle orchestre et consigne. Le problème qu'elle résout : aujourd'hui, les images entrent dans les registres internes via des scripts et pipelines maison où jugement et placement sont mêlés, sans planification uniforme ni contestabilité après coup.
_More detail: `.nanopm/wiki/docs/product.md`_

## Who it's for
La persona principale est la responsable plateforme qui tient le registre d'images internes — aujourd'hui, l'auteur lui-même, au sein de l'équipe plateforme de son employeur. Son job-to-be-done : que les images entrent seules, selon des règles déclarées, sans qu'elle y passe ses journées, et pouvoir dormir (dans le doute, rien n'entre). Deux personas secondaires : l'équipe applicative qui attend son image (veut savoir pourquoi un refus, sans archéologie) et l'auditeur sécurité/conformité (veut un journal qui fait foi). Anti-persona : l'organisation qui veut une console — tableau de bord ou interface graphique ; `uske` reste volontairement mince et ne s'adresse qu'à des lecteurs de texte.
_More detail: `.nanopm/wiki/docs/personas.md`_

## How we make money
Aucun revenu : `uske` est un projet open source (Apache-2.0) porté par un employeur, pas vendu. Ce qui le fait durer est le temps que l'employeur laisse à l'auteur tant que l'outil lui sert — pas une disposition à payer d'un tiers. Le premier terrain est interne (déployé chez l'employeur), la publication ouverte suit ; le dépôt est aujourd'hui privé, sans canal de découverte public. Aucune tarification, aucun packaging, aucune donnée d'économie unitaire (et il n'y en aura pas au sens monétaire).
_More detail: `.nanopm/wiki/docs/business-model.md`_

## Why we exist
Mission : faire entrer seules les images de conteneur dans un registre interne, selon des règles déclarées, en jouant ensemble un outil qui juge et un outil qui place, en consignant chaque décision. Vision à 3-5 ans : le trio `regis`/`knock`/`uske` devient un catalogue open source adopté par d'autres responsables plateforme, sans que ceux-ci connaissent l'auteur — jalon d'arrivée (assumed) : au moins un registre non tenu par l'auteur alimenté par des screenings planifiés. Valeurs, par rang décroissant : sûreté (dans le doute, refuser), contestabilité (on ajoute, on ne rature jamais), opérabilité (étapes séparées, rejouables), minceur (`uske` refuse de devenir une colle générique). Stade : Idea — projet à un seul auteur, pas encore déployé.
_More detail: `.nanopm/wiki/docs/vision-mission.md`_

## Who decides
Tristan Rivoallan est seul auteur, mainteneur et unique committer : il tranche toute décision produit, d'architecture et l'ordre des objectifs qualité, consignée en ADR. Des agents de code proposent des changes OpenSpec sous sa relecture, sans pouvoir de décision. L'équipe plateforme de l'employeur (dont l'auteur fait partie) décide, entre pairs, du déploiement sur son registre — seule décision réellement partagée, et celle qui compte pour la première preuve d'usage. Aucun second mainteneur : le projet s'arrête si l'auteur s'arrête.
_More detail: `.nanopm/wiki/docs/org.md`_

## What's NOT known yet
- Cible réelle du premier screening : l'employeur est nommé, mais ni le cluster ni le registre précis ne le sont.
- Ce que signifie « mettre à l'écart » une image déjà placée par un screening antérieur.
- Aucune donnée d'usage réel : pas de conversation utilisateur consignée, pas d'issue, dépôt privé sans canal de retour ; les deux personas secondaires (équipe applicative, auditeur) n'ont encore été rencontrées par personne.
- L'ouverture du dépôt (vision « adopté par d'autres » vs dépôt privé aujourd'hui) n'est pas encore planifiée comme jalon.
- Le pari central de la vision — qu'une responsable plateforme tierce reconnaîtra son problème et acceptera de tenir un dépôt de politiques et trois outils — n'est étayé par aucun échange réel.
