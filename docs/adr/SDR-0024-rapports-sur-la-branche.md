---
adr: SDR-0024
slug: rapports-sur-la-branche
title: Hors du cluster, les rapports cités vivent sur la branche du journal
status: accepted
date: 2026-10-17
authors: [Tristan Rivoallan]
supersedes: []
---

# Hors du cluster, les rapports cités vivent sur la branche du journal

> Verdict `accepted` reçu de Tristan Rivoallan le 2026-10-17 (option A). Cet ADR amende un point
> de [`SDR-0023`](SDR-0023-workflow-github.md), « Les rapports partent dans une archive du run »,
> qui reste en vigueur pour tout le reste. Options pesées : `openspec/changes/reports-survive-rerun/proposal.md`.

## Context and Problem Statement

Rejouer le job `screen` supprime l'archive des rapports de la tentative précédente, quel que soit
son nom (sondes du 2026-10-17). Les lignes que cette tentative a poussées citent pourtant ces
rapports (`RISK-13`). L'archive expire aussi au bout de 90 jours au plus sur un dépôt public.

## Considered Options

* **Commiter les rapports sur la branche du journal**, avec la ligne qui les cite.
* Une branche dédiée aux rapports : deux pushes, une ligne peut arriver sans son rapport.
* Un paquet OCI ou un asset de release : supprimables sans trace dans le dépôt.
* Refuser le rejeu : un run échoué ne se rejoue plus depuis l'interface.
* Accepter le risque.

## Decision Outcome

**Le crochet du journal commite les rapports de la politique avec son journal.** `uske` copie un
rapport avant d'écrire la ligne qui le cite : le commit de la ligne porte son rapport. L'archive du
run reste, comme copie, et `report-retention-days` avec elle : les retirer casserait les appelants
de `v0.11.0`.

### Consequences

* Bon : un rapport cité vit aussi longtemps que sa ligne, et l'historique de la branche montre
  toute suppression ; rejouer un job redevient sûr ; la limite de 90 jours tombe.
* Coût : la branche grossit à chaque empreinte nouvelle jugée (pas à chaque run), ce qui avait fait
  écarter cette option dans `github-action` (D5).
* Coût : un rapport commité ne s'efface plus sans réécrire la branche. `regis` ne garde d'un secret
  trouvé que sa forme masquée.
