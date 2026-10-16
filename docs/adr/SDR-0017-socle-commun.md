---
adr: SDR-0017
slug: socle-commun
title: Socle commun à regis, knock et uske
status: accepted
date: 2026-10-16
authors: [Tristan Rivoallan]
supersedes: [SDR-0006, SDR-0010]
traits:
  commits:
    scopes: []
    tool: commitlint
  forge:
    host: github
  ci:
    tool: github-actions
    gate: bloquante
---

# Socle commun à regis, knock et uske

> **Qu'est-ce que ce fichier ?** Un ADR (*Architecture Decision Record*) : une décision
> consignée, avec son contexte, les options pesées, ce qui a été retenu et ce que ça coûte.
> Celui-ci est propre à `uske`, comme [`SDR-0016`](SDR-0016-journal-et-transit.md). Il dépasse
> deux ADR hérités de la méthode, [`SDR-0006`](SDR-0006-commits.md) et
> [`SDR-0010`](SDR-0010-forge-and-ci.md), qui restent au répertoire : leur corps est gelé, et
> c'est le `supersedes:` ci-dessus qui dit qu'ils ne sont plus en vigueur
> ([`SDR-0001`](SDR-0001-record-architecture-decisions.md)).
>
> **`commits.tool: commitlint` ne veut pas dire que `commitlint` est installé.** C'est la valeur
> la plus proche que le schéma de la méthode admette ; `commitlint` n'est pas installé, et c'est
> l'expression régulière du workflow `pr-title` qui tient le format.

## Context and Problem Statement

`regis`, `knock` et `uske` s'ouvrent sous l'organisation `sncfdevelopers`. Leur CI doit être
identique : les fichiers de workflow sont les mêmes octet pour octet dans les trois dépôts, et ce
qui est propre à un dépôt vit dans son `Makefile` ou dans un fichier de données
(`.github/settings.json`, `.github/images.json`). Cela a été décidé lors de la préparation de
l'ouverture des trois dépôts. Le socle est écrit dans `regis` puis copié ici ;
le workflow `socle-drift` compare chaque semaine les trois copies.

Ce socle contredit deux réponses que ce dépôt avait données :

- [`SDR-0006`](SDR-0006-commits.md) confiait le format des commits à `commitlint`, branché sur le
  titre de la demande de fusion. Il n'a jamais été installé (`DEBT-03`).
- [`SDR-0010`](SDR-0010-forge-and-ci.md) déclarait la chaîne `informative`, parce qu'un dépôt
  privé sur ce plan n'avait pas de protection de branche (l'API répondait 403 le 2026-09-20).
  Un dépôt public y a droit, et le socle en dépend.

## Considered Options

* **`commitlint` sur le titre de la PR.** C'est ce que prévoyait `SDR-0006`. Il demande Node dans
  le socle, donc dans trois dépôts Python, pour une seule vérification.
* **Une expression régulière dans le socle.** Une ligne de `grep -E` sur le titre de la PR, dans
  un workflow du socle. Elle ne dépend de rien et s'exécute partout de la même façon.
* **Laisser la CI informative.** Rien ne change, et un rouge continue de ne rien empêcher alors
  que la forge sait maintenant le bloquer.

## Decision Outcome

**L'expression régulière, et une chaîne bloquante.**

Le titre de la PR est vérifié par le workflow `pr-title` du socle
([`.github/workflows/pr-title.yml`](../../.github/workflows/pr-title.yml)) : les onze types de
Conventional Commits, une portée facultative et la syntaxe de rupture. Sous `squash`
([`SDR-0009`](SDR-0009-branching.md)), ce titre devient le message du commit sur `main`, et c'est
lui que lit release-please ([`SDR-0011`](SDR-0011-delivery.md)). `commits.scopes` reste `[]`,
comme dans `SDR-0006`. L'expression régulière accepte une portée facultative, quelle qu'elle
soit : `commits.scopes: []` n'est donc tenu que par la relecture.

La chaîne est `bloquante` : le ruleset versionné dans
[`.github/settings.json`](../../.github/settings.json) exige cinq checks de statut, `lint`,
`test`, `security`, `image` et `pr-title`, avant toute fusion sur `main`. Les quatre premiers
viennent de [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml), qui n'appelle que les
cibles du `Makefile`. Le même ruleset porte une règle `code_scanning` : une alerte CodeQL bloque
la fusion à partir de `critical`. `forge.host` et `ci.tool` ne changent pas.

**Sur `commits.tool`, le schéma est plus étroit que la décision.** Le `.mdschema.yml` de ce
répertoire n'admet que `commitlint`, `hook` ou `aucun`, et refuse `titre-de-pr` (vérifié le
2026-10-16 avec `mdschema` 0.15.1). Ce fichier écrit donc `commitlint`, la valeur que la méthode
décrit comme « en CI » : elle dit **où** le format est tenu, sur le titre de la PR et avant la
fusion. **`commitlint` n'est pas installé** ; ce qui tient le format est l'expression régulière
de `pr-title`. `hook` dirait un contrôle local, et `aucun` dirait que rien ne le tient : les deux
seraient faux.

- `commits.scopes` : reprise de `SDR-0006` — 2026-10-16
- `commits.tool` : répondue — 2026-10-16
- `forge.host`, `ci.tool` : reprises de `SDR-0010` — 2026-10-16
- `ci.gate` : répondue — 2026-10-16

### Consequences

`DEBT-03`, `DEBT-04` et `DEBT-05` sont refermés. Le titre de chaque PR est vérifié avant la
fusion. La couverture est mesurée par `make test` et bloque sous 90 %
([`SDR-0007`](SDR-0007-tests.md)) : 91 % le 2026-10-16. release-please fabrique les versions et
publie une image signée sur GHCR.

`DEBT-06` reste ouvert : le socle ne lance pas `mdschema`, parce qu'il est identique dans trois
dépôts et que seul `uske` porte ce schéma. Sa place serait la cible `lint` du `Makefile`, qui est
propre à ce dépôt ; ce fichier ne la tranche pas.

Le coût : `uske` ne choisit plus seul sa CI. Un changement dans un fichier du socle se fait dans
`regis`, puis se recopie dans `knock` et `uske`. Un besoin propre à ce dépôt va dans son
`Makefile`, ou dans un workflow `extra-*.yml`, que `socle-drift` ne compare pas.

## More Information

Les fichiers du socle sont listés dans
[`.github/workflows/socle-drift.yml`](../../.github/workflows/socle-drift.yml).

```bash
( cd docs/adr && npx @jackchuka/mdschema@0.15.1 check '*.md' )
```
