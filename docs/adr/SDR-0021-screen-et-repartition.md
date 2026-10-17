---
adr: SDR-0021
slug: screen-et-repartition
title: Un verbe qui lance les deux outils, et un Workflow par politique
status: proposed
date: 2026-10-17
authors: [Tristan Rivoallan]
supersedes: []
---

# Un verbe qui lance les deux outils, et un Workflow par politique

> `proposed` : écrit par le change `screen-and-policy-fan-out`, il attend son verdict. Le
> raisonnement complet, les alternatives et les risques vivent dans
> `openspec/changes/screen-and-policy-fan-out/design.md`, décisions D1, D2, D4 et D7. Cet ADR
> n'en retient que ce qui engage les changes suivants.

## Context and Problem Statement

Jusqu'ici, `uske` ne lançait jamais `regis` ni `knock` : le workflow les lançait, chacun dans son
image, et `uske` lisait leurs fichiers. Un screening hors du cluster se recopiait donc à la main,
en Bash (`base-images/screen.sh`). Dans le cluster, toutes les politiques passaient par un seul
Workflow, tenu à `parallelism: 1` par des volumes `ReadWriteOnce`. L'ordre de grandeur annoncé est
de plus de 10 000 politiques.

## Considered Options

* **Garder la règle, et laisser chaque dépôt recopier les étapes** : écartée, les copies dérivent
  déjà.
* **`uske screen` lance les deux outils par leur ligne de commande, et un préfixe les déplace** :
  retenue.
* **`regis` et `knock` en bibliothèques de `uske`** : écartée, car elle lierait trois versions.
* **Un seul Workflow, rendu parallèle sur un stockage partagé** : écartée, car il garde une trace
  et un rejeu pour toutes les politiques.
* **Un Workflow enfant par politique, créé par un parent qui fixe commit, epoch et `run`** :
  retenue.

## Decision Outcome

* `uske screen` est le seul verbe qui lance `regis` et `knock`. Il les lance par leur nom sur le
  `PATH`, ou par le préfixe de `USKE_REGIS_CMD` et `USKE_KNOCK_CMD`. Il ne lit d'eux que leurs
  fichiers et leur code de retour. Les sous-commandes d'étape restent sans outil.
* `uske` ne connaît pas git : ce qui doit suivre une écriture au journal passe par
  `USKE_AFTER_RECORD`.
* Dans le cluster, l'unité de travail est la politique : un `Workflow` enfant `uske-policy` par
  politique, chaque outil dans son image, et deux plafonds posés par l'overlay. Au-delà de 1, le
  stockage est `ReadWriteMany`.

### Consequences

* Bon : un seul enchaînement décide hors du cluster, et un test de parité le tient aligné sur les
  étapes.
* Bon : une politique se rejoue seule, et sa trace est à elle.
* Coût : `uske` grossit d'un module qui lance des processus (objectif Minceur).
* Coût : un droit de plus pour le compte `uske`, créer des `Workflow`, et un stockage
  `ReadWriteMany` à fournir pour dépasser 1.
* Ne décide ni le planificateur (`DEBT-07`) ni le support du journal (`DEBT-08`).
