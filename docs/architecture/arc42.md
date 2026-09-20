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

> État de ce document au 2026-09-20 : les sections *Introduction and Goals* et *Architecture
> Decisions* sont rédigées. Les dix autres portent encore le texte du gabarit : elles s'écrivent
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
- Rendre au placeur le plan, moins les opérations refusées ; il n'applique que cela.
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
| 2 | **Contestabilité** `#secure` — toute décision est consignée, jamais réécrite, retrouvable | Un refus vieux de trois semaines se retrouve et s'explique **en une minute** — date, état, jeu de règles, raison ; et l'historique du fichier de résultats ne montre **aucune** ligne modifiée ou supprimée. | La compacité du journal, et toute correction en place d'une ligne fausse : on ajoute, on ne rature pas. |
| 3 | **Opérabilité** `#operable` — un screening qui échoue se diagnostique et se rejoue sans dégât | **Une seule** personne rejoue un screening interrompu à n'importe quelle étape ; le rejeu ne place rien deux fois et ne perd aucune ligne de résultat. | La vitesse d'exécution : les étapes restent séparées, lisibles et rejouables plutôt que fondues. |
| 4 | **Minceur** `#flexible` — `uske` ne juge ni ne place, et ne grossit pas | `uske` ne contient **aucune** règle de jugement et **aucun** geste de placement : retirer le juge ou le placeur le laisse sans rien à décider. | La commodité d'un outil qui ferait tout. Dernière du rang : quand la sûreté exige que `uske` vérifie lui-même quelque chose, il grossit. |

Les scénarios détaillés iront dans *Quality Requirements*, quand cette section sera rédigée.

## Stakeholders

| Role/Name | Contact | Expectations |
|-----------|---------|--------------|
| **Responsable plateforme** — tient le registre ; persona principale | — persona, personne non nommée | Qu'un screening tourne sur planification sans elle, que rien de douteux n'entre, et qu'elle comprenne assez l'enchaînement des étapes pour rejouer seule un screening échoué. |
| **Équipe applicative** — attend une image pour livrer | — persona | Savoir pourquoi son image n'est pas arrivée : la raison du refus et la règle appliquée, sans archéologie. |
| **Auditeur sécurité / conformité** | — persona | Un journal qui fait foi : pour une image et une date, la décision, le jeu de règles et la raison ; et la preuve qu'aucune ligne n'a été réécrite. |
| **Auteur et mainteneur** — Tristan Rivoallan | dépôt `trivoallan/uske` | Savoir où poser du code et ce qui a le droit de dépendre de quoi ; retrouver pourquoi une décision a été prise. Premier utilisateur réel, sur un seul registre. |
| **Agents qui écrivent les changes** | — | Lire les objectifs et les décisions en un lieu, sans les déduire du code. |

**Validation des objectifs qualité** : Tristan Rivoallan, qui en a fixé l'ordre le 2026-09-20.

# Architecture Constraints

# Context and Scope

## Business Context

**\<Diagram or Table\>**

**\<optionally: Explanation of external domain interfaces\>**

## Technical Context

**\<Diagram or Table\>**

**\<optionally: Explanation of technical interfaces\>**

**\<Mapping Input/Output to Channels\>**

# Solution Strategy

# Building Block View

## Whitebox Overall System

***\<Overview Diagram\>***

Motivation  
*\<text explanation\>*

Contained Building Blocks  
*\<Description of contained building block (black boxes)\>*

Important Interfaces  
*\<Description of important interfaces\>*

### \<Name black box 1\>

*\<Purpose/Responsibility\>*

*\<Interface(s)\>*

*\<(Optional) Quality/Performance Characteristics\>*

*\<(Optional) Directory/File Location\>*

*\<(Optional) Fulfilled Requirements\>*

*\<(optional) Open Issues/Problems/Risks\>*

### \<Name black box 2\>

*\<black box template\>*

### \<Name black box n\>

*\<black box template\>*

### \<Name interface 1\>

…​

### \<Name interface m\>

## Level 2

### White Box *\<building block 1\>*

*\<white box template\>*

### White Box *\<building block 2\>*

*\<white box template\>*

…​

### White Box *\<building block m\>*

*\<white box template\>*

## Level 3

### White Box \<\_building block x.1\_\>

*\<white box template\>*

### White Box \<\_building block x.2\_\>

*\<white box template\>*

### White Box \<\_building block y.1\_\>

*\<white box template\>*

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

Onze décisions à ce jour, toutes héritées de la méthode : dix questions qu'elle pose à tout dépôt
qui l'adopte, et la règle qui dit comment on y répond. Aucune n'est encore propre à `uske`. Une
nouvelle décision s'écrit quand un choix est cher à défaire, touche plusieurs blocs, arbitre
entre deux objectifs qualité ou contraint les changes suivants.

**Un ADR `accepted` ne se corrige pas** : son corps est gelé
([`SDR-0001`](../adr/SDR-0001-record-architecture-decisions.md)). Pour revenir sur une décision,
un nouvel ADR la nomme dans son `supersedes:` ; l'ancien reste au répertoire, qui est un journal
et non la liste de ce qui est en vigueur. À ce jour, aucun ADR n'en dépasse un autre.

## Decision Log

| ID | Décision | Statut | Date | Objectif qualité servi | Le dépôt s'y conforme ? |
|----|----------|--------|------|------------------------|-------------------------|
| [SDR-0001](../adr/SDR-0001-record-architecture-decisions.md) | Comment les décisions se consignent | accepted | 2026-08-29 | Contestabilité | oui |
| [SDR-0002](../adr/SDR-0002-localization.md) | Langue de chaque support | accepted | 2026-09-20 | Opérabilité | en partie — `README.md` précède la décision |
| [SDR-0003](../adr/SDR-0003-architecture.md) | Pattern d'architecture, et où vit ce document | accepted | 2026-09-20 | Sûreté, Opérabilité | **non** — le code est à rapprocher |
| [SDR-0004](../adr/SDR-0004-languages.md) | Langage principal | accepted | 2026-09-20 | Opérabilité | oui |
| [SDR-0005](../adr/SDR-0005-validation.md) | Validation aux frontières et des fichiers de données | accepted | 2026-09-20 | Sûreté, contre Minceur | **non** — validation à la main aujourd'hui |
| [SDR-0006](../adr/SDR-0006-commits.md) | Portées des commits, et ce qui tient le format | accepted | 2026-09-20 | Contestabilité | **non** — l'outil reste à installer |
| [SDR-0007](../adr/SDR-0007-tests.md) | Seuil de couverture | accepted | 2026-09-20 | Sûreté | **non mesuré** — aucun instrument |
| [SDR-0008](../adr/SDR-0008-documentation.md) | Outil, racine et audience de la documentation | accepted | 2026-09-20 | Minceur | oui |
| [SDR-0009](../adr/SDR-0009-branching.md) | Modèle de branches et de fusion | accepted | 2026-09-20 | Contestabilité, Opérabilité | en partie — une branche `ci/…` antérieure porte un préfixe hors liste |
| [SDR-0010](../adr/SDR-0010-forge-and-ci.md) | Forge, chaîne d'intégration, et ce qu'un rouge empêche | accepted | 2026-09-20 | Opérabilité | oui |
| [SDR-0011](../adr/SDR-0011-delivery.md) | Environnements servis, et ce qui fabrique une version | accepted | 2026-09-20 | Contestabilité | **non** — l'outil reste à installer |

## Écarts ouverts

Cinq décisions disent où le dépôt va, pas où il est : `SDR-0003`, `SDR-0005`, `SDR-0006`,
`SDR-0007`, `SDR-0011`. Chacune écrit l'écart sous son titre *Consequences*. Aucun n'est réglé
par le change qui a statué ; ils reviennent aux changes suivants, et iront dans *Risks and
Technical Debts* quand cette section sera rédigée.

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
