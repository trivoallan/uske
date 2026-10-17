---
adr: SDR-0022
slug: documentation-en-anglais
title: La documentation en anglais, les décisions en français
status: accepted
date: 2026-10-17
authors: [Tristan Rivoallan]
supersedes: [SDR-0020]
traits:
  localization:
    language:
      default: français
      documentation: anglais
      code: anglais
      comments: anglais
---

# La documentation en anglais, les décisions en français

> **Qu'est-ce que ce fichier ?** Un ADR (*Architecture Decision Record*) : une décision
> consignée, avec son contexte, les options pesées, ce qui a été retenu et ce que ça coûte.
> Celui-ci est propre à `uske`. Il dépasse [`SDR-0020`](SDR-0020-readme-en-anglais.md), qui reste
> au répertoire : son corps est gelé, et c'est le `supersedes:` ci-dessus qui dit qu'il n'est plus
> en vigueur ([`SDR-0001`](SDR-0001-record-architecture-decisions.md)).

## Context and Problem Statement

[`SDR-0020`](SDR-0020-readme-en-anglais.md) a passé le seul `README.md` en anglais, pour le lecteur
open source qui découvre `regis`, `knock` et `uske`. Il a écarté `documentation: anglais` parce que
c'était « bien plus que ce que la question demande ».

La question a changé depuis. Des talks sur `uske` sont soumis à une conférence internationale. Le
participant qui suit le lien de la dernière slide ne s'arrête pas au README : il lit le document
d'architecture pour savoir si `uske` tourne chez lui, la page des raisons pour comprendre un refus
montré en démo, et la sortie de `uske decisions`. Avec `SDR-0020`, ces trois-là restent en
français. Le talk porte sur le produit, pas sur la méthode : ce lecteur ne lit pas les ADR.

## Considered Options

* **S'en tenir à `SDR-0020`.** Le README est en anglais, mais le lecteur bute ensuite sur
  l'architecture, les raisons et la démo.
* **Tout en anglais, ADR et discovery compris.** Les corps des ADR sont gelés : les traduire
  revient à les réécrire. Et le public du talk ne les lit pas.
* **`documentation: anglais`, avec des exceptions nommées.** La documentation que lit
  l'utilisateur passe en anglais. Les supports de décision restent dans la langue de qui décide.

## Decision Outcome

**`documentation: anglais`.** Sont en anglais `README.md`, toutes les pages de `docs/` hors
`docs/adr/`, et les textes que le code rend à un lecteur : la page des raisons engendrée par
`uske/outcomes.py` et les marques de `uske decisions`.

**Restent en français, suivant `default` :** les ADR (`docs/adr/`), la découverte
(`openspec/discovery.md`, `.nanopm/`), les artefacts OpenSpec (`openspec/`) et les messages de
commit. Le schéma n'a pas de clé pour ces exceptions : elles vivent dans ce texte.

Les termes du métier ont un seul nom anglais, fixé dans le glossaire de
`docs/architecture/arc42.md`. Toute page et tout texte rendu par le code l'emploient.

- `localization.language.default` : reprise de `SDR-0020` — 2026-10-17
- `localization.language.documentation` : répondue — 2026-10-17
- `localization.language.code` : reprise de `SDR-0020` — 2026-10-17
- `localization.language.comments` : reprise de `SDR-0020` — 2026-10-17

### Consequences

Un lecteur non francophone suit `uske` du README jusqu'à la raison d'un refus sans changer de
langue. Le coût : deux langues dans un même dépôt, frontière tracée par le type de document, et un
agent qui écrit une page doit lire cet ADR, pas seulement les clés. Le glossaire devient un point
de passage : un terme nouveau y entre avec son nom anglais avant d'apparaître dans une page.

## More Information

```bash
( cd docs/adr && npx @jackchuka/mdschema@0.15.1 check '*.md' )
```
