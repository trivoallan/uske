# Verdicts des ADR hérités

Journal de la conduite des verdicts du change `onboarding` : le tri, le récapitulatif des
réponses, le tableau final. Les valeurs elles-mêmes vivent dans les ADR, et nulle part ailleurs.

## Tri

Preuves relevées le 2026-09-20. Un ADR n'est **constaté** que si toutes ses clés ont une preuve.

| ADR | Clé | Valeurs admises | Preuve dans le dépôt | Valeur proposée | Tas |
| --- | --- | --- | --- | --- | --- |
| SDR-0004 | `languages.main.name` | chaîne | `pyproject.toml` : `requires-python = ">=3.12"`, paquet `uske` | `Python` | **constaté** |
| SDR-0009 | `branching.model` | `github-flow`, `trunk-based`, `gitflow` | `git branch -a` : `main` seule, plus une branche `dependabot/…` ; quatre commits poussés droit sur `main` | `github-flow` (méthode) | à choisir |
| SDR-0009 | `branching.merge` | `squash`, `merge-commit`, `rebase` | aucune fusion dans l'historique | `squash` (méthode) | à choisir |
| SDR-0009 | `branching.prefixes` | liste prise parmi les onze types | aucune branche de travail à ce jour | `[feat, fix, docs]` (méthode) | à choisir |
| SDR-0002 | `localization.language.default` | `français`, `anglais` | artefacts `openspec/` et ADR en français ; `README.md` bilingue, anglais d'abord | `français` (méthode) | à choisir |
| SDR-0002 | `…language.code` | idem | `uske/*.py` : symboles en anglais | `anglais` — constatée | à choisir |
| SDR-0002 | `…language.comments` | idem | `uske/*.py` : commentaires et docstrings en anglais | `anglais` — constatée | à choisir |
| SDR-0002 | `…language.commits` | idem | `git log` : trois messages en français, un en anglais | vide — comme `default` | à choisir |
| SDR-0002 | `…language.documentation` | idem | `README.md` anglais d'abord ; `docs/adr/` en français | vide — comme `default` | à choisir |
| SDR-0003 | `architecture.pattern` | `event-driven`, `hexagonal`, `layered`, `microservices`, `monolithic`, `soa` | `uske/` : 1 010 lignes, dix modules à plat, un seul déployable (`Dockerfile`) | `monolithic` — l'ADR le dit honnête pour un petit dépôt | à choisir |
| SDR-0003 | `architecture.document` | `arc42`, `ailleurs`, `aucun` | accord reçu le 2026-09-20 pour créer `docs/architecture/arc42.md` | `arc42` — répondue | à choisir |
| SDR-0005 | `validation.boundary` | nom de bibliothèque, ou `aucun` | `pyproject.toml` : seule dépendance `pyyaml` ; aucune bibliothèque de validation ; `uske` lit des politiques, des plans, des arguments | `pydantic` (méthode, pour Python) — le code ne s'y conforme pas encore | à choisir |
| SDR-0005 | `validation.data_files` | `json-schema`, autre, `aucun` | aucun `$schema` ni schéma dans le dépôt | `json-schema` (méthode) | à choisir |
| SDR-0006 | `commits.scopes` | liste de mots, ou `[]` | `git log` : aucune portée dans les quatre messages | `[]` — constatée | à choisir |
| SDR-0006 | `commits.tool` | `commitlint`, `hook`, `aucun` | ni `commitlint.config.*`, ni `.husky`, ni `.pre-commit-config.yaml` ; aucune version engendrée depuis les messages | `aucun` — constatée | à choisir |
| SDR-0007 | `tests.coverage_target` | un nombre, ou `aucun` | `.github/workflows/test.yaml` lance `unittest`, sans instrument de couverture | `90` (méthode) | à choisir |
| SDR-0008 | `docs.tool` | `docusaurus`, `mkdocs`, `aucun` | ni `mkdocs.yml` ni `docusaurus.config.*` | `aucun` — constatée | à choisir |
| SDR-0008 | `docs.root` | un chemin | `docs/adr/` existe | `docs/` — constatée | à choisir |
| SDR-0008 | `docs.audience` | `mono-utilisateur`, `équipe`, `LS`, `groupe`, `public` | licence Apache-2.0, but « open source / recherche » (répondu le 2026-09-20) ; mais le dépôt est aujourd'hui privé | `public` | à choisir |
| SDR-0010 | `forge.host` | `gitlab`, `github`, autre | `git remote get-url origin` : `https://github.com/trivoallan/uske` | `github` — constatée | à choisir |
| SDR-0010 | `ci.tool` | dépend de la forge, ou `aucun` | `.github/workflows/test.yaml` | `github-actions` — constatée | à choisir |
| SDR-0010 | `ci.gate` | `bloquante`, `informative`, `aucune` | l'API de protection de `main` répond 403 : indisponible pour un dépôt privé sur ce plan — rien ne bloque aujourd'hui | `informative` — ce qui est vrai ; `bloquante` est la proposition de la méthode | à choisir |
| SDR-0011 | `deploy.environments` | liste de paires, déclencheurs `tag`, `merge`, `manuel` | `README.md` : « Not deployed anywhere yet » ; aucun flux de publication d'image | `[]` — constatée | à choisir |
| SDR-0011 | `release.tool` | `release-please`, autre, `manuel`, `aucun` | version `0.0.0`, aucun tag, aucun `CHANGELOG.md` | `aucun` — ce qui est vrai ; `release-please` est la proposition de la méthode sur GitHub | à choisir |

**Résultat du tri** : un ADR constaté (`SDR-0004`), neuf à choisir. `SDR-0006` a ses deux clés
prouvées, mais ce que le dépôt *fait* n'est pas ce qu'il *veut* faire : le doute va au tas « à
choisir » (`design.md`, D2).

**Note de schéma** : une surcharge de `SDR-0002` laissée vide se **retire** du frontmatter —
la vérification refuse une clé présente à valeur nulle.

## Récapitulatif

Réponses reçues le 2026-09-20, en une passe de trois appels, sans écriture entre eux. Dix
verdicts `accepted`, aucun `rejected`, aucun *sans réponse*.

| ADR | Verdict | Clé | Valeur | Provenance |
| --- | --- | --- | --- | --- |
| SDR-0009 | accepted | `branching.model` | `github-flow` | répondue — 2026-09-20 |
| SDR-0009 | accepted | `branching.merge` | `squash` | répondue — 2026-09-20 |
| SDR-0009 | accepted | `branching.prefixes` | `[feat, fix, docs]` | répondue — 2026-09-20 |
| SDR-0002 | accepted | `localization.language.default` | `français` | répondue — 2026-09-20 |
| SDR-0002 | accepted | `localization.language.code` | `anglais` | constatée — `uske/*.py` ; confirmée le 2026-09-20 |
| SDR-0002 | accepted | `localization.language.comments` | `anglais` | constatée — `uske/*.py` ; confirmée le 2026-09-20 |
| SDR-0002 | accepted | `…documentation`, `…commits` | clés retirées — comme `default` | répondue — 2026-09-20 |
| SDR-0003 | accepted | `architecture.pattern` | `hexagonal` | répondue — 2026-09-20 |
| SDR-0003 | accepted | `architecture.document` | `arc42` | répondue — 2026-09-20 |
| SDR-0004 | accepted | `languages.main.name` | `Python` | constatée — `pyproject.toml` ; confirmée le 2026-09-20 |
| SDR-0005 | accepted | `validation.boundary` | `pydantic` | répondue — 2026-09-20 |
| SDR-0005 | accepted | `validation.data_files` | `json-schema` | répondue — 2026-09-20 |
| SDR-0006 | accepted | `commits.scopes` | `[]` | constatée — `git log` ; confirmée le 2026-09-20 |
| SDR-0006 | accepted | `commits.tool` | `commitlint` | répondue — 2026-09-20, à la confirmation du récapitulatif |
| SDR-0007 | accepted | `tests.coverage_target` | `90` | répondue — 2026-09-20 |
| SDR-0008 | accepted | `docs.tool` | `aucun` | constatée — ni `mkdocs.yml` ni `docusaurus.config.*` ; confirmée le 2026-09-20 |
| SDR-0008 | accepted | `docs.root` | `docs/` | constatée — `docs/adr/` ; confirmée le 2026-09-20 |
| SDR-0008 | accepted | `docs.audience` | `mono-utilisateur` | répondue — 2026-09-20 |
| SDR-0010 | accepted | `forge.host` | `github` | constatée — `git remote get-url origin` ; confirmée le 2026-09-20 |
| SDR-0010 | accepted | `ci.tool` | `github-actions` | constatée — `.github/workflows/test.yaml` ; confirmée le 2026-09-20 |
| SDR-0010 | accepted | `ci.gate` | `informative` | répondue — 2026-09-20 |
| SDR-0011 | accepted | `deploy.environments` | `[]` | constatée — `README.md` ; confirmée le 2026-09-20 |
| SDR-0011 | accepted | `release.tool` | `release-please` | répondue — 2026-09-20 |

**Écarts que ces verdicts ouvrent entre ce qui est décidé et ce que le dépôt fait.** Aucun
n'est réglé par ce change ; chacun s'écrit sous *Consequences* de son ADR.

| ADR | Décidé | Ce que le dépôt fait | Qui le règle |
| --- | --- | --- | --- |
| SDR-0003 | `hexagonal` | dix modules à plat, entrées-sorties mêlées au domaine | changes suivants |
| SDR-0005 | `pydantic`, `json-schema` | vérifications à la main, aucun schéma | changes suivants |
| SDR-0006 | `commitlint` | aucun outil ne tient le format | changes suivants |
| SDR-0007 | `90` | aucun instrument de couverture | changes suivants |
| SDR-0011 | `release-please` | version `0.0.0`, aucun tag, outil non installé | changes suivants |

**Tension tranchée à la confirmation.** La première réponse sur `SDR-0006` était
`commits.tool: aucun`. `SDR-0011` retenant `release-please`, qui engendre les versions depuis
les messages, le présupposé de `commitlint` tient : la personne a retenu `commitlint` en
confirmant le récapitulatif, le 2026-09-20.

**Confirmation reçue le 2026-09-20** : « Oui, avec `commits.tool = commitlint` ». L'écriture
dans `docs/adr/` commence après cette ligne.

**Cache `npx`** : la personne le purge elle-même ; en attendant, la vérification passe par le
binaire du cache lancé avec `node`.
