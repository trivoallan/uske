# Proposition — la documentation que lit le public de `uske` passe en anglais

## Why

`uske` part sous l'organisation `sncfdevelopers` ([`SDR-0019`](../../../docs/adr/SDR-0019-documentation-publique.md)
a fixé `docs.audience: public`), et des talks sur le produit sont soumis à une conférence
internationale. `SDR-0020` (*Le README en anglais*, sur `main`) n'a passé en anglais que le README.
Il a écarté `documentation: anglais` parce que c'était « bien plus que ce que la question
demande ». La question a changé depuis : le participant au talk lit le README, puis l'architecture,
la page des raisons et la sortie de `uske decisions` montrée en démo. Sur `origin/main`, l'arc42 a
370 lignes de prose française, la page des raisons 20, `docs/explanation/how-it-works.md` 8, et le
CLI affiche deux marques françaises.

**Objectif qualité :** Contestabilité `#secure` (rang 2) : un refus se retrouve et s'explique en une
minute. Ce change élargit le « s'explique » au lecteur qui ne lit pas le français.

## What Changes

- **Nouvel ADR `SDR-0022`** (`SDR-0021` est pris par la branche `feat/screen-and-policy-fan-out`).
  Il dépasse `SDR-0020` et fixe `localization.language.documentation: anglais`. Les ADR, la
  discovery (`openspec/discovery.md`, `.nanopm/`), les artefacts OpenSpec et les messages de commit
  restent en français, et le texte de l'ADR les nomme. Les corps gelés des ADR ne se traduisent pas.
- **Glossaire FR→EN** : le glossaire de `docs/architecture/arc42.md` reçoit le terme anglais de
  chaque terme métier (screening, transit, quarantine, inconclusive, placeur, juge…). Il est fixé
  **avant** toute traduction, et toutes les pages, la sortie du CLI et la page des raisons
  l'emploient. Quand `regis` ou `knock` emploient déjà un terme anglais, c'est celui-là qu'on
  retient.
- **`docs/architecture/arc42.md`** : traduit en entier, glossaire compris.
- **`docs/explanation/how-it-works.md`** : la section « Décisions » passe en anglais.
- **`docs/reference/raisons.md` → `docs/reference/reasons.md`** : la table des raisons de
  `uske/outcomes.py` passe en anglais, puis la page est régénérée et renommée.
  `tests/test_reasons.py` et le lien du README suivent. Les codes de raison (`regis/*`, `uske/*`)
  sont déjà en anglais et **ne changent pas**, donc le journal n'est pas touché.
- **`uske decisions`** : dans les formats `text` et `md`, les marques « antidatée » et
  « arbitrage absent » deviennent `backdated` et `no arbitration`. Les tests et golden tests
  suivent.

## Alternatives écartées

- **Ne rien faire, ou s'en tenir à `SDR-0020`** : un participant qui suit le lien du talk lit un
  README anglais, puis tombe sur une architecture et une page de raisons qu'il ne peut pas lire. Sur
  la démo, la sortie anglaise affiche des marques en français.
- **Tout traduire, ADR et discovery compris** : les corps d'ADR sont gelés (`SDR-0001`), donc les
  traduire reviendrait à les réécrire. Le talk porte sur le produit, pas sur la méthode, et son
  public ne lit pas ces documents.
- **Deux changes, l'arc42 après la soumission du CFP** : proposé, puis écarté par le mainteneur au
  profit d'une seule merge request (cadrage, passe 1).
- **Une table de termes dans le dossier `docs/`, partagée par les trois dépôts** : elle donnerait
  une source unique, mais demande un change dans un autre dépôt pour un vocabulaire que seul `uske`
  n'a pas encore en anglais. `regis` et `knock` s'alignent par relecture.
- **Bilingue (pages FR et EN côte à côte)** : deux textes à tenir en phase, et rien pour vérifier
  qu'ils le restent.
- **Traduire aussi les noms de tiers des playbooks** (`Placement direct`, `Quarantaine`…) : ce sont
  des données que `uske` lit dans les playbooks, pas de la documentation. Les changer casserait le
  contrat avec `docs/playbooks/`. Hors périmètre.

## Conception

Conception : aucune condition, pas de `design.md`. Les choix de périmètre, d'emplacement du
glossaire et de ce qui reste en français sont tranchés ici.

## Revue

Revue : due, pour un livrable face à un tiers : la sortie de la CLI `uske decisions` et les pages
publiques changent.

## Capabilities

### New Capabilities

- aucune

### Modified Capabilities

- `decision-lookup` : les marques des formats `text` et `md` sont en anglais (`backdated`,
  `no arbitration`).

## Impact

- Code : `uske/outcomes.py` (textes de la table des raisons), `uske/decisions.py` (deux marques).
- Tests : `tests/test_reasons.py` (chemin de la page), `tests/test_decisions.py` (marques), golden
  tests `tests/golden/decisions-redis-728.{txt,md}` et `decisions-escape.md` s'ils portent une
  marque.
- Docs : `docs/architecture/arc42.md`, `docs/explanation/how-it-works.md`,
  `docs/reference/raisons.md` renommée `reasons.md`, lien du `README.md`, nouvel
  `docs/adr/SDR-0022-*.md`.
- Travaux parallèles : `feat/screen-and-policy-fan-out` ajoute `SDR-0021` et touche la doc. Le
  change qui fusionne en second traduit ce que l'autre a ajouté.
- Le journal, ses codes de raison et les playbooks ne changent pas.

## Cadrage

- Détection : `.nanopm/wiki/docs/product.md` est présent. Le seul ADR `proposed` vu est
  `SDR-0020-screen-et-repartition.md`, non suivi dans ce checkout ; il appartient au change
  `screen-and-policy-fan-out` (il y devient `SDR-0021`). `docs/architecture/arc42.md` est présent.
- Cadrage, passe 1 sur 5 (2026-10-17) : marques du CLI incluses ; arc42 dans ce change ; glossaire
  dans l'arc42 de `uske` ; verdict de l'ADR de screen laissé à son change.
- Ce checkout (branche `docs/audience-public`) est en retard sur `origin/main`. Le change se pose sur
  une branche tirée de `origin/main` (tâche 1.1).

Proposition refusée : verdicts (2026-10-17)
