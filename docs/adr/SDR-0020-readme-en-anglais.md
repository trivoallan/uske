---
adr: SDR-0020
slug: readme-en-anglais
title: Le README en anglais, comme ceux de regis et knock
status: accepted
date: 2026-10-17
authors: [Tristan Rivoallan]
supersedes: [SDR-0002]
traits:
  localization:
    language:
      default: français
      code: anglais
      comments: anglais
---

# Le README en anglais, comme ceux de regis et knock

> **Qu'est-ce que ce fichier ?** Un ADR (*Architecture Decision Record*) : une décision
> consignée, avec son contexte, les options pesées, ce qui a été retenu et ce que ça coûte.
> Celui-ci est propre à `uske`. Il dépasse [`SDR-0002`](SDR-0002-localization.md), qui reste au
> répertoire : son corps est gelé, et c'est le `supersedes:` ci-dessus qui dit qu'il n'est plus
> en vigueur ([`SDR-0001`](SDR-0001-record-architecture-decisions.md)).

## Context and Problem Statement

[`SDR-0002`](SDR-0002-localization.md) écrit la prose de ce dépôt en français, et notait déjà que
`README.md`, bilingue et anglais d'abord, s'en écartait « tant qu'un change ne l'a pas réécrit ou
qu'un nouvel ADR n'a pas surchargé `documentation` ».

Les README de `regis`, `knock` et `uske` sont réécrits sur un même squelette, pour un lecteur
open source qui découvre les trois dépôts. Ils partagent un bloc copié à l'octet. Ceux de `regis`
et `knock` sont en anglais.

## Considered Options

* **README en français.** Conforme à `SDR-0002`, mais le bloc commun ne peut plus être identique
  dans les trois dépôts, et le lecteur visé change de langue d'un dépôt à l'autre.
* **`documentation: anglais`.** Toute la prose passe en anglais, ADR et arc42 compris : bien plus
  que ce que la question demande.
* **Une exception nommée : `README.md` en anglais.** Le reste ne bouge pas.

## Decision Outcome

**`README.md` s'écrit en anglais. Le reste de la prose reste en français.** Les clés de
localisation sont celles de `SDR-0002`, reprises ici parce que le bloc `traits:` en vigueur est
celui de cet ADR. Le schéma n'a pas de clé pour un seul fichier : l'exception vit dans ce texte.

Les sections que l'ancien `README.md` portait en anglais ont été déplacées telles quelles dans
`docs/how-to/operate.md` et `docs/explanation/how-it-works.md`. Elles sont en anglais et
s'écartent de la règle jusqu'à ce qu'un change les traduise.

- `localization.language.default` : reprise de `SDR-0002` — 2026-10-17
- `localization.language.code` : reprise de `SDR-0002` — 2026-10-17
- `localization.language.comments` : reprise de `SDR-0002` — 2026-10-17

### Consequences

Un lecteur non francophone comprend ce que fait `uske` sans quitter la page d'accueil, et le
bloc commun reste identique dans les trois dépôts. Le coût : deux langues dans un même dépôt, et
un agent qui écrit le README doit lire cet ADR, pas seulement les clés.
