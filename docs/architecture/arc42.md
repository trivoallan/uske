---
date: 2026-09-20
title: uske — document d'architecture
---

**About arc42**

arc42, the template for documentation of software and system
architecture.

Template Version 9.0-EN. (based upon AsciiDoc version), July 2025

Created, maintained and © by Dr. Peter Hruschka, Dr. Gernot Starke and
contributors. See <https://arc42.org>.

# Introduction and Goals

> État de ce document au 2026-10-17 : les sections *Introduction and Goals*, *Architecture
> Constraints*, *Context and Scope*, *Solution Strategy*, *Building Block View* et *Architecture
> Decisions* sont rédigées. Les six autres portent encore le texte du gabarit : elles s'écrivent
> quand un change déplace ce qu'elles décrivent.

## Requirements Overview

`uske` joue ensemble un outil qui **juge** une image de conteneur et un outil qui la **place**
dans un registre. Sur planification, pour chaque politique active, il conduit un *screening* et
consigne chaque décision. Il ne juge rien et ne place rien : il appelle, il attend, il écrit.

### Essential Features

- Lister les politiques actives, tenues dans un dépôt à part, extrait à chaque screening.
- Faire écrire au placeur son plan : chaque import, mise à jour ou reconstruction qu'il s'apprête
  à faire, avec l'empreinte de la source.
- Faire juger chaque empreinte encore due d'une décision, avec le jeu de règles que le régime de
  la politique appelle.
- Classer chaque verdict en l'une de quatre issues : placement direct, transformation requise,
  quarantaine, non concluant.
- Rendre au placeur le plan, moins les opérations refusées ; il n'applique que cela. Une source
  à réparer n'y reste que si le placeur dit qu'il la reconstruira.
- Faire retenir dans un transit ce que le placeur construit, le faire juger par sa propre
  empreinte, et ne lui rendre pour promotion que ce qui ressort en placement direct.
- Ajouter une ligne par décision à un fichier de résultats. Les lignes s'ajoutent, ne se
  réécrivent jamais.
- Recenser le registre : ce qui y est, moins ce qui a été admis, donne le contournement.
- Envoyer au suivi des vulnérabilités les inventaires signés par le placeur, et en retirer ce
  qui a quitté le registre.

### Business Context

Aujourd'hui, les images entrent dans un registre par des scripts et des chaînes d'intégration
maison, écrits équipe par équipe : jugement et placement y sont mêlés, rien n'est planifié de
façon uniforme, et rien n'est contestable après coup. **Le mal est d'abord l'absence
d'automatisation ; la contestabilité vient ensuite.** `uske` sert la personne qui tient le
registre — les images entrent seules, selon des règles déclarées —, puis celles qui subissent
ou vérifient une décision : l'équipe dont l'image est refusée, l'auditeur qui doit prouver ce
qui a été admis.

**Hors périmètre** : devenir une colle générique pour d'autres juges ou d'autres placeurs ;
toute interface graphique.

### References

- [`openspec/discovery.md`](../../openspec/discovery.md) — personas, parcours annoté contre le
  code, priorités, stories. Ce document en reprend le périmètre et les objectifs, sans les
  recopier au-delà.
- [`README.md`](../../README.md) — ce que fait un screening, pas à pas.

## Quality Goals

> Quatre objectifs, **ordonnés** : en cas de conflit, le rang le plus haut l'emporte. Chacun dit
> ce à quoi il fait renoncer — un objectif qui ne coûte rien n'en est pas un. Toute décision
> d'architecture les sert, dans cet ordre. Source et ordre : `openspec/discovery.md`, réponses
> reçues le 2026-09-20.

| Rang | Objectif | Scénario vérifiable | Renonce à |
|:----:|----------|---------------------|-----------|
| 1 | **Sûreté** `#safe` — dans le doute, ne rien placer | Un verdict absent, illisible ou non concluant vaut refus : sur un screening où le juge ne répond pas, **zéro** opération est rendue au placeur pour les empreintes concernées. | La fraîcheur : une image saine peut attendre un screening de plus. |
| 2 | **Contestabilité** `#secure` (non-répudiation) — toute décision est consignée, jamais réécrite, retrouvable | Un refus vieux de trois semaines se retrouve et s'explique **en une minute** — date, état, jeu de règles, raison ; et l'historique du fichier de résultats ne montre **aucune** ligne modifiée ou supprimée. | La compacité du journal, et toute correction en place d'une ligne fausse : on ajoute, on ne rature pas. |
| 3 | **Opérabilité** `#operable` — un screening qui échoue se diagnostique et se rejoue sans dégât | **Une seule** personne rejoue un screening interrompu à n'importe quelle étape ; le rejeu ne place rien deux fois et ne perd aucune ligne de résultat. | La vitesse d'exécution : les étapes restent séparées, lisibles et rejouables plutôt que fondues. |
| 4 | **Minceur** `#flexible` — `uske` ne juge ni ne place, et ne grossit pas | `uske` ne contient **aucune** règle de jugement et **aucun** geste de placement : retirer le juge ou le placeur le laisse sans rien à décider. | La commodité d'un outil qui ferait tout. Dernière du rang : quand la sûreté exige que `uske` vérifie lui-même quelque chose, il grossit. |

Les scénarios détaillés iront dans *Quality Requirements*, quand cette section sera rédigée.

## Stakeholders

| Role/Name | Contact | Expectations |
|-----------|---------|--------------|
| **Responsable plateforme** — tient le registre ; persona principale | persona ; à défaut de personne réelle, répond : le mainteneur | Qu'un screening tourne sur planification sans elle, que rien de douteux n'entre, et qu'elle comprenne assez l'enchaînement des étapes pour rejouer seule un screening échoué. |
| **Équipe applicative** — attend une image pour livrer | persona ; répond : le mainteneur | Savoir pourquoi son image n'est pas arrivée : la raison du refus et la règle appliquée, sans archéologie. |
| **Auditeur sécurité / conformité** | persona ; répond : le mainteneur | Un journal qui fait foi : pour une image et une date, la décision, le jeu de règles et la raison ; et la preuve qu'aucune ligne n'a été réécrite. |
| **Auteur et mainteneur** — Tristan Rivoallan | dépôt `trivoallan/uske` | Savoir où poser du code et ce qui a le droit de dépendre de quoi ; retrouver pourquoi une décision a été prise. Premier utilisateur réel, sur un seul registre. |
| **Agents qui écrivent les changes** | contexte d'agent du dépôt | Lire les objectifs et les décisions en un lieu, sans les déduire du code. |

**Ces cinq rôles sont les parties prenantes du système, pas le lectorat de ce document.** Trois
d'entre eux sont des personas : aucune personne réelle ne les tient aujourd'hui, et c'est le
mainteneur qui répond à leur place. Le lectorat de la documentation, lui, est fixé par
[`SDR-0008`](../adr/SDR-0008-documentation.md) à `mono-utilisateur` — ce qui explique qu'aucun
terme du métier ne soit défini en *Glossary* : `screening`, `régime`, `contournement`, `juge`,
`placeur` s'emploient ici sans glose. Le jour où l'audience s'élargit, un nouvel ADR le dit, et
`SDR-0008` prévient lui-même que **toutes** les pages écrites sous `mono-utilisateur` se
relisent avant — cette section et le glossaire les premiers.

**Validation des objectifs qualité** : Tristan Rivoallan, qui en a fixé l'ordre le 2026-09-20.

# Architecture Constraints

> Ce qu'un développeur ne peut pas défaire seul. Le test appliqué à chaque ligne : *en sortir
> demande-t-il une décision d'organisation ?* Si un change suffit à s'en affranchir, ce n'est pas
> une contrainte, c'est une décision — et sa place est en *Architecture Decisions*.

| Contrainte | Nature | Ce qu'elle impose | Comment en sortir |
|------------|--------|-------------------|-------------------|
| **La méthode `surdesrails`** — posée en dépendance de développement du dépôt | organisationnelle | Le format des décisions (MADR), leur numérotation `SDR-nnnn`, le schéma qui refuse une décision non statuée, et le jeu de questions auxquelles tout dépôt qui l'adopte doit répondre. | Retirer la dépendance et répondre à chaque question à la main. Ce n'est pas un change : c'est renoncer à la méthode. |
| **Un ADR `accepted` est gelé** — [`SDR-0001`](../adr/SDR-0001-record-architecture-decisions.md) | organisationnelle | Le corps d'une décision statuée ne se corrige pas. Tout ce qui en découle — le français par défaut, le langage, le modèle de branches, le seuil de couverture — n'est pas rouvrable par un change. | Un nouvel ADR qui nomme l'ancien dans son `supersedes:`. L'ancien reste au répertoire. |
| **`regis` et `knock` sont des dépôts tiers** | technique | `uske` ne les connaît que par leur ligne de commande et leur code de sortie ; il ne partage avec eux ni code ni modèle de données. Leurs cycles de version ne sont pas les siens. | Rien ici : c'est la séparation que sert l'objectif de **Minceur**, et l'abandonner viderait `uske` de sa raison d'être. |

**La méthode est une contrainte, pas une décision, et c'est ce qui explique la forme de
*Architecture Decisions*.** Les onze ADR hérités de la méthode n'ont pas été choisis : ils ont
été posés, avec leurs numéros et leurs questions. Ce que ce dépôt décide, c'est la **réponse** à
chacun — pas l'existence de la question. Un lecteur qui prendrait le journal des décisions pour une
délibération libre se tromperait sur ce qui a réellement été arbitré ici.

**La voie de recours est nommée, et elle est asymétrique.** Une question qui ne se pose pas dans
ce dépôt reçoit le verdict `rejected` avec son motif, ce qui la fait taire entièrement ; une
règle particulière se déroge par un ADR local qui écrit son motif. Mais certaines clés n'admettent
qu'une valeur, et celles-là ne se dérogent pas — elles se rejettent en bloc.

# Context and Scope

> Niveau LEAN : une table par contexte, sans diagramme. La frontière tient en une phrase —
> `uske` et son journal sont dedans, tout ce qu'il appelle est dehors — et une table la dit sans
> outil de rendu, ce que [`SDR-0008`](../adr/SDR-0008-documentation.md) (`tool: aucun`) demande.
> Les `IF-nn` sont ceux de ce document : un `IF-nn` cité dans le code vient du dossier de
> référence, et ne désigne pas la même interface.

## Business Context

`uske` est **au milieu et ne tient rien** : chaque partenaire ci-dessous juge, place, recense
ou suit, et `uske` ne fait que leur passer ce que l'autre a produit. La seule chose qu'il
possède est le **journal des résultats** — c'est pourquoi il est dedans, et non un partenaire.

| ID | Partenaire | Ce qui entre dans `uske` | Ce qui sort de `uske` |
|----|------------|--------------------------|-----------------------|
| IF-01 | **Planificateur** | Le déclenchement d'un screening | Une issue : réussi (refus et non-concluants compris) ou échec technique, à rejouer |
| IF-02 | **Dépôt des politiques et des jeux de règles** | Les politiques actives et leur régime ; les jeux de règles | rien — lu, jamais écrit |
| IF-03 | **Placeur** (`knock`) | Son plan ; ce qu'il a retenu en transit ; ce qu'il a placé | Le plan moins les opérations refusées ; la liste à promouvoir |
| IF-04 | **Juge** (`regis`) | Un verdict et son rapport, par empreinte | Une empreinte et le jeu de règles que le régime appelle |
| IF-05 | **Registre** | Ce qui y est | rien — lu, jamais écrit ; `uske` n'y place ni n'en retire rien |
| IF-06 | **Suivi des vulnérabilités** | Ce qu'il suit déjà | Les inventaires signés par le placeur ; le retrait de ce qui a quitté le registre |
| IF-07 | **Responsable plateforme** | Le rejeu d'un screening ; une ligne de réouverture ajoutée au journal | La chronologie des décisions d'une image |
| IF-08 | **Équipe applicative, auditeur** | Une image, ou un état et une période | Les décisions, le jeu de règles et la raison de chacune — en lecture seule |
| IF-09 | **Oracle d'usage** — la commande que la rétention de la maison lance déjà | La dernière fois qu'une image a servi, ou rien | Les seules images suspectes de contournement, une par une |

**Hors frontière, même si on les croit dedans :**

- **Le transit.** `uske` le nomme au placeur, mais n'y lit ni n'y écrit : le placeur y retient,
  le juge y lit. Le fermer aux consommateurs est le travail du registre.
- **La signature et l'attestation** : c'est le placeur qui signe ; `uske` vérifie une signature
  avant d'envoyer un inventaire (IF-06), il n'en produit aucune.
- **Les règles de jugement** : elles sont dans les jeux de règles (IF-02) et chez le juge. La
  seule table que `uske` tient est celle qui associe un régime à un jeu de règles.

Le reste du hors-périmètre — colle générique, interface graphique — est fixé en *Business
Context* de la première section.

## Technical Context

Chaque interface métier a un seul canal. **`uske` n'appelle ni `regis` ni `knock`** : chacun
tourne dans sa propre image, à sa propre étape du workflow, et les étapes se passent des fichiers
sur le volume `/work` du screening (*Architecture Constraints*). `uske` ne parle HTTP qu'aux deux
API qu'il connaît par leur nom.

| ID | Canal | Format | Authentification |
|----|-------|--------|------------------|
| IF-01 | Argo Workflows : un `CronWorkflow` enchaîne les sous-commandes de `uske` ([`deploy/base`](../../deploy/base)) | Arguments en ligne de commande, JSON sur la sortie standard ; code de sortie 0 (issue métier) ou 1 (échec technique, qu'Argo rejoue) | Le compte de service du `CronWorkflow` |
| IF-02 | `git` : le dépôt est extrait à chaque screening, à l'étape `checkout` | YAML (politiques, jeux de règles) | Celle du dépôt ; nommé par le paramètre `repository` de l'overlay |
| IF-03 | Étapes Argo à part, image `knock` : `reconcile --plan-out`, `--apply-plan`, `--stage-to`, `promote` ; fichiers sur `/work` | JSON (plan, audit) | Les identifiants de registre de `knock` (`KNOCK_REGISTRIES`) |
| IF-04 | Étape Argo à part, image `regis` : `regis analyze` ; son code de sortie est passé à `uske classify` (`--regis-exit`) | JSON (rapport), sur `/work` | Les identifiants de registre de `regis`, sur l'hôte de la destination |
| IF-05 | HTTP, API Harbor `/api/v2.0` (`uske census`) | JSON | Basique : `HARBOR_URL`, `HARBOR_USER`, `HARBOR_PASSWORD` |
| IF-06 | HTTP, API Dependency-Track `/api` (`uske dt-plan`, `dt-publish`, `dt-retire`) | JSON ; inventaires CycloneDX | Clé d'API : `DT_URL`, `DT_API_KEY` |
| IF-07 | `kubectl` : un pod jetable qui monte le volume `uske-results` (README, *Why was an image not placed?*) | Une ligne JSON ajoutée au fichier de résultats ; Markdown en sortie de `uske decisions` | Les droits Kubernetes de la personne sur le namespace |
| IF-08 | Le même pod, volume monté en lecture seule | Markdown (chronologie Mermaid et tableau) | Idem |
| IF-09 | Processus enfant de `uske census` : la commande nommée par `KNOCK_USAGE_ORACLE_CMD` | JSON sur l'entrée standard ; `{"last_seen": …}` en sortie, code 0 pour répondre | Celle de la commande |

# Solution Strategy

> Niveau LEAN : ce qui a été choisi et le motif en une ligne. Le pourquoi complet est dans
> l'ADR nommé ; une ligne sans ADR est une décision qui n'en a pas encore.

**Un enchaîneur de commandes qui échoue fermé.** Chaque étape d'un screening est une
sous-commande courte de `uske` — elle lit des fichiers, appelle un outil, écrit du JSON — et
c'est le planificateur qui les enchaîne. `uske` ne garde aucun état en mémoire d'une étape à
l'autre : ce qui passe d'une étape à la suivante est un fichier, et ce qui reste après le
screening est une ligne du journal. Tout ce qui n'est pas un verdict lisible de placement direct
se lit comme un refus.

## Choix techniques

| Sujet | Choix | Motif | Où |
|-------|-------|-------|----|
| Langage | Python ≥ 3.12 | L'un des trois que la méthode recommande ; celui de `regis` et `knock`, donc un seul outillage pour les trois dépôts | [`SDR-0004`](../adr/SDR-0004-languages.md) |
| Enchaînement | Argo Workflows : un `CronWorkflow`, une sous-commande par étape | Le rejeu, les reprises et la trace de chaque étape viennent de l'outil, pas de `uske` | **aucun ADR** — `DEBT-07` |
| Intégration | `regis` et `knock` à leurs propres étapes du workflow, par fichiers ; Harbor et Dependency-Track par HTTP, en bibliothèque standard | Ne partager ni code ni image avec les outils enchaînés ; une seule dépendance d'exécution (`pyyaml`) | *Architecture Constraints* |
| Persistance | Un fichier JSON Lines par politique, en ajout seul, sur un volume | Un fichier se lit, se copie et se conteste sans serveur ; l'ajout seul se vérifie dans son historique | [`SDR-0016`](../adr/SDR-0016-journal-et-transit.md), [`SDR-0018`](../adr/SDR-0018-journal-run.md) ; le support lui-même : **aucun ADR** — `DEBT-08` |
| Structure du code | Hexagonale : le domaine sans entrée-sortie | Un agent modifie et teste une règle sans environnement qui tourne | [`SDR-0003`](../adr/SDR-0003-architecture.md) — non tenu, `DEBT-01` |
| Validation | `pydantic` aux frontières, JSON Schema pour les fichiers | Un champ absent devient une erreur nommée, pas un défaut silencieux | [`SDR-0005`](../adr/SDR-0005-validation.md) — non tenu, `DEBT-02` |

## Approche par objectif qualité

| Objectif | Mécanisme principal | Où |
|----------|---------------------|----|
| 1. **Sûreté** `#safe` | **Échec fermé** : un rapport absent ou illisible devient `inconclusive` (`outcomes.py`, D-23 du dossier de référence). N'est rendu au placeur que le placement direct, et la transformation requise quand le placeur dit qu'il reconstruira. Le placeur n'applique une opération que si son empreinte source n'a pas changé depuis le plan (`gate.py`, D-30). Ce qu'il reconstruit passe une **seconde porte**, depuis un transit obligatoire. | `SDR-0016` ; *Runtime View*, à écrire |
| 2. **Contestabilité** `#secure` | **Journal en ajout seul, qui n'avance que vers l'avant** : une ligne plus ancienne que la dernière du même digest n'est pas écrite. Chaque ligne porte son état, son jeu de règles, sa raison et son screening (`run`) ; `uske decisions` les rend lisibles. | `SDR-0016`, `SDR-0018` |
| 3. **Opérabilité** `#operable` | **Des étapes séparées et rejouables** : JSON sur la sortie, code de sortie 0 pour toute issue métier et 1 pour un échec technique, qu'Argo rejoue. Le journal à sens unique rend un rejeu sans effet sur ce qui est déjà écrit ; une image retenue sans verdict est retentée trois fois au plus. | *Runtime View*, *Deployment View*, à écrire |
| 4. **Minceur** `#flexible` | **Rien à juger, rien à placer** : la seule table métier est celle qui associe un régime à un jeu de règles (`playbooks.py`). Les autres outils ne sont connus que par leur ligne de commande ou leur API. | *Architecture Constraints* |

**La Sûreté coûte déjà de la Minceur, et c'est voulu** : `gate.py` compte lui-même les
tentatives et clôt une source dont la reconstruction a été refusée, ce qu'un `uske` réduit à un
simple enchaînement ne ferait pas. Le rang des objectifs le permet ; la ligne 4 de *Quality Goals* l'avait annoncé.

# Building Block View

> Niveau LEAN : le niveau 1 seul, en table. Un bloc est un groupe de modules de `uske/`, ou le
> workflow de `deploy/base` ; aucun ne descend au fichier près plus qu'il ne le faut — le paquet
> compte dix modules à plat, et quatre blocs n'en ont qu'un.

## Whitebox Overall System

**Deux blocs au centre, sans entrée-sortie, et des adaptateurs autour.** *Issues* et *Porte*
décident ; tout le reste lit, écrit ou parle à un partenaire. C'est la forme que vise
[`SDR-0003`](../adr/SDR-0003-architecture.md), à moitié atteinte : les deux sont déjà purs, mais
rien dans l'arborescence ne sépare le domaine des adaptateurs (`DEBT-01`).

| Bloc | Responsabilité | Source | Dépend de | Interfaces | Entrées-sorties |
|------|----------------|--------|-----------|------------|-----------------|
| **Workflow** | Enchaîner les étapes d'un screening : extraire le dépôt, lancer `knock`, `regis` et les sous-commandes de `uske`, chacun dans son image, et leur passer des fichiers sur `/work` | `deploy/base/` | toutes les sous-commandes, par leur ligne de commande | IF-01, IF-02, IF-03, IF-04 | oui — c'est sa raison d'être |
| **Sous-commandes** | Une sous-commande par étape : lire les fichiers et l'environnement, appeler le bloc qui décide, écrire du JSON, et traduire l'issue en code de sortie (0 métier, 1 technique) | `uske/cli.py` | tous les blocs ci-dessous | IF-01, IF-07, IF-08 | oui |
| **Issues** | Ramener un rapport du juge à l'une des quatre issues, en échouant fermé | `uske/outcomes.py` | — | IF-04, par le rapport que lui passent les sous-commandes | **non** |
| **Porte** | Rendre le plan moins les refus ; compter les tentatives d'une reconstruction et clore une source refusée | `uske/gate.py` | Issues, Politiques, Journal (les derniers états, déjà lus) | IF-03, par le plan que lui passent les sous-commandes | **non** |
| **Politiques** | Lire les politiques ; associer un régime à un jeu de règles — la seule table métier de `uske` | `uske/policies.py`, `uske/playbooks.py` | — | IF-02 | lecture seule |
| **Journal** | Écrire une ligne par décision, en ajout seul et vers l'avant ; relire le journal pour une personne | `uske/results.py`, `uske/decisions.py` | Issues | IF-07, IF-08 | oui |
| **Recensement** | Compter le contournement : ce qui est au registre, moins ce qui est passé par la porte, puis demander l'usage des seuls suspects | `uske/census.py` | — | IF-05, IF-09 | oui |
| **Synchronisation du suivi** | Envoyer au suivi des vulnérabilités les inventaires signés, après en avoir vérifié la signature ; retirer ce qui a quitté le registre | `uske/dtsync.py` | Politiques | IF-06 | oui |

**Aucune dépendance circulaire.** *Issues*, *Politiques* et *Recensement* n'importent rien de
`uske` ; le *Journal* ne dépend que d'*Issues*, et la *Porte* de trois blocs qui ne dépendent pas
d'elle. *Issues* est un bloc à part pour cette raison : rangé avec la *Porte*,
il faisait un cycle — la *Porte* lit le *Journal*, et le *Journal* écrit des issues.

**Le Journal appartient à `uske`, et c'est le seul bloc à garder un état** d'un screening à
l'autre. Tout le reste se recalcule : *Issues* et la *Porte* d'un rapport et d'un plan, le Recensement et la
Synchronisation du registre lui-même.

**Ce que la table dit de `DEBT-01`.** La colonne *Entrées-sorties* trace la frontière que
l'hexagone demande : seules *Issues*, la *Porte* et la table des régimes en sont déjà du bon côté. Le
Journal et les Politiques mêlent une règle (n'écrire que vers l'avant, lire un régime) et la
lecture d'un fichier ; le Recensement et la Synchronisation mêlent une règle (soustraire, planifier)
et un appel HTTP. Rapprocher le code, c'est séparer ces deux moitiés dans chacun des quatre.

# Runtime View

## \<Runtime Scenario 1\>

- *\<insert runtime diagram or textual description of the scenario\>*

- *\<insert description of the notable aspects of the interactions
  between the building block instances depicted in this diagram.\>*

## \<Runtime Scenario 2\>

## …​

## \<Runtime Scenario n\>

# Deployment View

## Infrastructure Level 1

***\<Overview Diagram\>***

Motivation  
*\<explanation in text form\>*

Quality and/or Performance Features  
*\<explanation in text form\>*

Mapping of Building Blocks to Infrastructure  
*\<description of the mapping\>*

## Infrastructure Level 2

### *\<Infrastructure Element 1\>*

*\<diagram + explanation\>*

### *\<Infrastructure Element 2\>*

*\<diagram + explanation\>*

…​

### *\<Infrastructure Element n\>*

*\<diagram + explanation\>*

# Cross-cutting Concepts

## *\<Concept 1\>*

*\<explanation\>*

## *\<Concept 2\>*

*\<explanation\>*

…​

## *\<Concept n\>*

*\<explanation\>*

# Architecture Decisions

## Overview

Les décisions d'architecture de ce dépôt vivent dans [`docs/adr/`](../adr/), une par fichier, au
format MADR. Cette section est leur **journal** : elle y renvoie, et ne recopie ni leur contexte,
ni leurs options, ni leurs valeurs — chaque ADR dit que ses valeurs s'écrivent chez lui « et
nulle part ailleurs », et c'est ce qui les empêche d'être contredites ici.

Quatorze ADR à ce jour, tous statués, dont deux dépassés par `SDR-0017` ; douze sont donc en
vigueur. Onze sont hérités de la méthode — voir *Architecture Constraints* : dix questions
qu'elle pose à tout dépôt qui l'adopte, et la règle qui dit comment on y répond. Trois sont
propres à `uske` : `SDR-0016`, `SDR-0017` et `SDR-0018`. Une nouvelle décision s'écrit
quand un choix est cher à défaire, touche plusieurs blocs, arbitre entre deux objectifs qualité
ou contraint les changes suivants.

**La numérotation est celle de la méthode, trous compris.** Elle saute de `SDR-0011` à
`SDR-0016`. **`SDR-0012` n'existe pas en amont non plus** — vérifié le 2026-09-20 dans les
ressources du paquet, où ce numéro ne sert que de nom d'ADR orphelin dans un test de l'outil.
**`SDR-0013` a été retiré le 2026-10-16, avant l'ouverture du dépôt** : il résumait des
prescriptions internes de l'employeur, et la question qu'il posait (le front) ne se pose pas
ici, puisque `uske` ne sert aucune interface. `SDR-0014` et `SDR-0015` n'ont jamais été écrits
dans ce dépôt. Un trou dans la suite ne signale donc **aucune décision perdue**, et ce dépôt ne
renumérote pas : il porterait alors des numéros que la méthode ne reconnaîtrait plus.

**Ce journal liste aussi les questions encore ouvertes.** Un ADR `proposed` est une question
posée et non tranchée : il ne contraint rien, et le dépôt ne s'y conforme ni ne s'en écarte. Il
figure quand même au journal — savoir ce qui reste à décider vaut autant que savoir ce qui l'a
été.

**Un ADR `accepted` ne se corrige pas** : son corps est gelé
([`SDR-0001`](../adr/SDR-0001-record-architecture-decisions.md)). Pour revenir sur une décision,
un nouvel ADR la nomme dans son `supersedes:` ; l'ancien reste au répertoire, qui est un journal
et non la liste de ce qui est en vigueur. À ce jour, un seul en dépasse d'autres : `SDR-0017`
dépasse `SDR-0006` et `SDR-0010`.

## Decision Log

| ID | Décision | Statut | Date | Objectif qualité servi | Le dépôt s'y conforme ? |
|----|----------|--------|------|------------------------|-------------------------|
| [SDR-0001](../adr/SDR-0001-record-architecture-decisions.md) | Comment les décisions se consignent | accepted | 2026-08-29 | Contestabilité | oui |
| [SDR-0002](../adr/SDR-0002-localization.md) | Langue de chaque support | accepted | 2026-09-20 | Opérabilité | en partie — `README.md` précède la décision |
| [SDR-0003](../adr/SDR-0003-architecture.md) | Pattern d'architecture, et où vit ce document | accepted | 2026-09-20 | Sûreté, Opérabilité | **non** — le code est à rapprocher |
| [SDR-0004](../adr/SDR-0004-languages.md) | Langage principal | accepted | 2026-09-20 | Opérabilité | oui |
| [SDR-0005](../adr/SDR-0005-validation.md) | Validation aux frontières et des fichiers de données | accepted | 2026-09-20 | Sûreté, contre Minceur | **non** — validation à la main aujourd'hui |
| [SDR-0006](../adr/SDR-0006-commits.md) | Portées des commits, et ce qui tient le format | accepted — dépassé par SDR-0017 | 2026-09-20 | Contestabilité | sans objet — dépassé |
| [SDR-0007](../adr/SDR-0007-tests.md) | Seuil de couverture | accepted | 2026-09-20 | Sûreté | oui — 91 % mesuré le 2026-10-16 |
| [SDR-0008](../adr/SDR-0008-documentation.md) | Outil, racine et audience de la documentation | accepted | 2026-09-20 | Minceur | oui |
| [SDR-0009](../adr/SDR-0009-branching.md) | Modèle de branches et de fusion | accepted | 2026-09-20 | Contestabilité, Opérabilité | oui |
| [SDR-0010](../adr/SDR-0010-forge-and-ci.md) | Forge, chaîne d'intégration, et ce qu'un rouge empêche | accepted — dépassé par SDR-0017 | 2026-09-20 | Opérabilité | sans objet — dépassé |
| [SDR-0011](../adr/SDR-0011-delivery.md) | Environnements servis, et ce qui fabrique une version | accepted | 2026-09-20 | Contestabilité | oui — release-please branché le 2026-10-16 |
| [SDR-0016](../adr/SDR-0016-journal-et-transit.md) | Vocabulaire du journal pour une reconstruction, et transit obligatoire | accepted | 2026-10-10 | Sûreté, Contestabilité | oui — première décision propre à `uske` |
| [SDR-0017](../adr/SDR-0017-socle-commun.md) | Socle commun : format des titres tenu par la CI, CI bloquante | accepted | 2026-10-16 | Contestabilité, Opérabilité | oui |
| [SDR-0018](../adr/SDR-0018-journal-run.md) | Une ligne du journal nomme le criblage qui l'a écrite (clé `run`) | accepted | 2026-10-16 | Contestabilité, Opérabilité | oui — `classify --run` reçoit `{{workflow.name}}` du `WorkflowTemplate` |

## Écarts ouverts

Cinq décisions disaient où le dépôt allait, pas où il était ; chacune écrit son écart sous son
titre *Consequences*, et aucun n'a été réglé par le change qui a statué. `SDR-0017` en a refermé
trois le 2026-10-16 (`DEBT-03`, `DEBT-04` et `DEBT-05`) ; `DEBT-01` et `DEBT-02` restent ouverts.
Un sixième ne vient d'aucune décision — il a été relevé en revue, et reste ouvert. Deux autres,
relevés en rédigeant *Solution Strategy*, sont l'inverse : des décisions prises dans le code et
le déploiement, que rien n'a statuées. Cinq écarts sont donc ouverts à ce jour. **Tous portent un identifiant dès maintenant, avant que
*Risks and Technical Debts* existe** : un écart sans nom ne se referme pas, il s'oublie. Ces
identifiants sont stables — un écart réglé se marque *Closed* et garde son numéro, il ne
disparaît pas de la table.

| ID | Écart | Décision qui l'ouvre | Ce qui le referme |
|----|-------|----------------------|-------------------|
| DEBT-01 | L'arborescence du code contredit le pattern décidé ; un agent lit une structure que l'ADR dément, et suit l'ADR pour le code nouveau | [`SDR-0003`](../adr/SDR-0003-architecture.md) | Le rapprochement du code existant, change après change |
| DEBT-02 | La validation aux frontières se fait à la main ; un champ absent reste un défaut silencieux au lieu d'une erreur nommée | [`SDR-0005`](../adr/SDR-0005-validation.md) | Les frontières existantes portées sur l'outil décidé |
| DEBT-03 | Le format des messages de commit n'est tenu par rien ; un message hors format passe | [`SDR-0006`](../adr/SDR-0006-commits.md) | *Closed* 2026-10-16 par [`SDR-0017`](../adr/SDR-0017-socle-commun.md) : le workflow `pr-title` vérifie le titre par une expression régulière ; `commitlint` n'a pas été installé. (Critère d'origine : `commitlint` installé et branché sur le titre de la demande de fusion.) |
| DEBT-04 | La couverture de tests n'est pas mesurée : le seuil décidé n'est ni tenu ni démenti | [`SDR-0007`](../adr/SDR-0007-tests.md) | *Closed* 2026-10-16. Un instrument branché, et une première mesure prise |
| DEBT-05 | Rien ne fabrique une version : les livraisons ne se déduisent d'aucun commit | [`SDR-0011`](../adr/SDR-0011-delivery.md) | *Closed* 2026-10-16. L'outil de release installé — il dépend de DEBT-03 |
| DEBT-06 | Le schéma des ADR n'est lancé par personne : une décision laissée vide ou non statuée passe sans que rien ne le dise | aucune — relevé en revue le 2026-09-20 | Le contrôle ajouté à la cible `lint` du `Makefile`, ou dit manuel dans un ADR qui dépasse [`SDR-0017`](../adr/SDR-0017-socle-commun.md) |
| DEBT-07 | Argo Workflows enchaîne les étapes, et rien ne dit pourquoi : c'est lui qui rend un rejeu possible (objectif d'Opérabilité), et le quitter réécrirait tout `deploy/` | aucune — relevé le 2026-10-17 en écrivant *Solution Strategy* | Un ADR qui statue le planificateur, options écartées comprises |
| DEBT-08 | Le journal est un fichier JSON Lines par politique sur un volume, et rien ne dit pourquoi : `SDR-0016` fixe son vocabulaire, pas son support ; l'objectif de Contestabilité repose sur ce support | aucune — relevé le 2026-10-17 en écrivant *Solution Strategy* | Un ADR qui statue le support du journal, options écartées comprises |

**`DEBT-06` n'a pas la même provenance que les cinq autres, et c'est le plus intéressant.** Les
cinq premiers sont déclarés par la décision qui les crée : quelqu'un a statué, et a écrit ce que
sa décision coûtait. Le sixième n'est déclaré nulle part — il a fallu une revue pour le voir.
Vérifié le 2026-09-20 : `mdschema` n'est nommé que dans son propre fichier de configuration ; ni
la chaîne, ni un script, ni un crochet ne le lance. La méthode livre l'instrument, le dépôt ne le
branche pas.

**Il partageait ce motif avec `DEBT-03`**, refermé depuis : deux vérifications décidées, aucune
des deux automatisée. C'est le seul motif qui s'est répété dans cette table, et c'est donc lui
qu'il faut surveiller — un dépôt qui décide des contrôles sans les brancher finit par croire ses décisions
tenues.

**`DEBT-07` et `DEBT-08` sont le cas inverse de `DEBT-06`** : là, une vérification décidée
sans être branchée ; ici, une décision branchée sans être décidée. Les deux trompent de la même
façon — le journal des décisions ne dit pas ce que le dépôt fait.

**Ces huit lignes sont la matière de *Risks and Technical Debts***, qui les reprendra telles
quelles avec leur probabilité et leur impact quand un change l'écrira. D'ici là, elles vivent
ici : c'est le seul endroit du dépôt où les huit se lisent ensemble.

**La colonne « Le dépôt s'y conforme ? » du journal ci-dessus dit la même chose en prose.** Le
jour où *Risks and Technical Debts* existe, c'est vers ces `DEBT-nn` qu'elle renverra, au lieu
de redire l'état — deux endroits pour le même fait se contredisent tôt ou tard.

**Un arbitrage entre objectifs est déjà écrit** : `SDR-0005` ajoute une dépendance, contre la
Minceur, au nom de la Sûreté. Le rang des objectifs tranche — c'est à cela qu'il sert.

# Quality Requirements

## Quality Requirements Overview

## Quality Scenarios

# Risks and Technical Debts

# Glossary

| Term         | Definition         |
|--------------|--------------------|
| *\<Term-1\>* | *\<definition-1\>* |
| *\<Term-2\>* | *\<definition-2\>* |
