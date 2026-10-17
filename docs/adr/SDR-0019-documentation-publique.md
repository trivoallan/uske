---
adr: SDR-0019
slug: documentation-publique
title: Une documentation lue hors de l'organisation
status: accepted
date: 2026-10-17
authors: [Tristan Rivoallan]
supersedes: [SDR-0008]
traits:
  docs:
    tool: aucun
    root: docs/
    audience: public
---

# Une documentation lue hors de l'organisation

> **Qu'est-ce que ce fichier ?** Un ADR (*Architecture Decision Record*) : une décision
> consignée, avec son contexte, les options pesées, ce qui a été retenu et ce que ça coûte.
> Celui-ci est propre à `uske`, comme [`SDR-0017`](SDR-0017-socle-commun.md). Il dépasse
> [`SDR-0008`](SDR-0008-documentation.md), qui reste au répertoire : son corps est gelé, et c'est
> le `supersedes:` ci-dessus qui dit qu'il n'est plus en vigueur
> ([`SDR-0001`](SDR-0001-record-architecture-decisions.md)).

## Context and Problem Statement

[`SDR-0008`](SDR-0008-documentation.md) fixait `docs.audience: mono-utilisateur`, au motif que
le dépôt était privé. Ce motif ne tient plus : `uske` est public, sous licence Apache-2.0, et
part sous l'organisation `sncfdevelopers` avec `regis` et `knock`
([`SDR-0017`](SDR-0017-socle-commun.md)). Ses pages se lisent déjà hors de l'organisation.

Une audience déclarée plus étroite que celle qui lit est le seul écart que l'on ne rattrape pas :
`SDR-0008` le disait lui-même, et prévoyait qu'un nouvel ADR élargirait l'audience le jour où le
dépôt s'ouvrirait, après relecture de **toutes** les pages écrites sous `mono-utilisateur`.

## Considered Options

* **Garder `mono-utilisateur`.** La valeur ment sur ce qui est lu, et elle autorise un agent à
  écrire dans une page ce que le monde lira.
* **Un cran du milieu (`équipe`, `LS`, `groupe`).** Plus étroit que le lectorat réel, donc faux
  de la même façon.
* **`public`.** L'audience déclarée est celle qui lit.

## Decision Outcome

**`docs.audience: public`.** Aucune page de ce dépôt ne porte d'URL interne, de nom de client, de
détail d'infrastructure de l'organisation, ni d'adresse de personne. Une note brute n'y a plus sa
place : elle va dans un dépôt privé.

`docs.tool` et `docs.root` ne changent pas : le dépôt n'a toujours pas de site, et ses pages
vivent sous `docs/`. Elles sont reprises ici parce que le bloc `traits:` en vigueur est celui de
cet ADR.

Les pages de `docs/` et le `README.md` ont été relues le 2026-10-17 avant d'écrire cette valeur ;
la liste des passages relus est dans la demande de fusion qui porte cet ADR.

- `docs.tool` : reprise de `SDR-0008` — 2026-10-17
- `docs.root` : reprise de `SDR-0008` — 2026-10-17
- `docs.audience` : répondue — 2026-10-17

### Consequences

Un agent sait ce qu'il n'a pas le droit d'écrire dans une page. Le document d'architecture
définit désormais les termes du métier dans son glossaire, puisqu'un lecteur extérieur ne les
connaît pas.

Le coût : rien ne vérifie la règle, seule la relecture la tient. Les ADR gelés écrits sous
`mono-utilisateur` ne se corrigent pas ; ce qui y passe mal en `public` est signalé dans la
demande de fusion, et se retire, le cas échéant, comme `SDR-0013` l'a été avant l'ouverture.

## More Information

```bash
( cd docs/adr && npx @jackchuka/mdschema@0.15.1 check '*.md' )
```
