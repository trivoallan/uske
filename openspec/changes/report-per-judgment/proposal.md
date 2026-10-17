# Proposition — un rapport par jugement, jamais réécrit, et l'étape nommée au crochet

Cadrage, passe 1 sur 5 (2026-10-17). Les options A, B et C ont été posées en exploration, et C a
été retenue (« ok »). Découverte : rien à proposer, `.nanopm/wiki/docs/product.md` existe.
Verdicts : refusés le 2026-10-17. Document d'architecture : présent.

Objectif qualité : **Contestability** (rang 2), « every decision is recorded, never rewritten, and
can be found again ».

## Why

`uske screen` copie les rapports à `reports/<politique>/<empreinte>/<run>.<ext>` en écrasant le
fichier s'il existe. Or une empreinte `inconclusive` est rejugée, et une deuxième tentative du même
run porte le même `--run` : sur GitHub Actions, c'est le même `GITHUB_RUN_ID`. Le nouveau rapport
remplace alors celui que cite une ligne déjà écrite, ce qui est exactement le défaut que fe956bb
avait corrigé pour `classify`. Depuis la 0.9.0, c'est le premier problème connu de la release.

Un crochet `USKE_AFTER_RECORD` ne sait pas non plus à quelle étape il est appelé : `base-images`
perd un message de commit par porte (D4 de son change `uske-screen`).

## What Changes

- Un rapport copié par `uske screen` se nomme d'après l'**epoch** du screening, et plus d'après
  `--run`. Si ce nom est déjà pris, `uske screen` prend le premier libre parmi `<epoch>-2`,
  `<epoch>-3`, et ainsi de suite. Le nom est réservé par création exclusive, et un fichier existant
  n'est jamais réécrit. Le Markdown et le HTML d'un même jugement portent le même nom.
- La ligne cite le rapport de son propre jugement. Le run reste dans la ligne, en `run`.
- `uske screen` passe `USKE_STEP` au crochet, avec l'étape qui vient d'écrire le journal :
  `record`, `record-approve`, `record-applied`, `record-held` (les verdicts de la seconde porte) ou
  `record-promoted`.
- Le nom des rapports écrits par Argo, `<run>.html` dans le `WorkflowTemplate`, ne change pas.

## Alternatives écartées

- **Ne rien faire, et documenter le problème** : une ligne de journal renverrait au rapport d'une
  autre décision. Ça contredit l'objectif de rang 2, et ce n'est pas un simple défaut de confort.
- **A. Un flag `--report-name`** : le nom devient court, mais c'est l'appelant qui doit garantir
  qu'il est unique. Un appelant qui se trompe réécrit un rapport cité, sans que rien le signale.
- **B. L'epoch seule, sans chercher de nom libre** : le nom est neuf à chaque invocation, mais un
  `--epoch` imposé, le même d'une tentative à l'autre, fait revenir la collision.
- **Garder `<run>` et n'y ajouter qu'un suffixe libre** : ça règle le bug, mais le nom reste une URL
  aplatie de plus de 60 caractères. L'epoch est courte, triable, et la ligne porte déjà le run.
- **Réutiliser `_keep` de `uske merge`, qui garde le fichier existant** : c'est correct pour
  `merge`, où rejouer une archive redonne le même contenu. Pour `screen`, un nouveau jugement a un
  contenu nouveau, et la nouvelle ligne citerait l'ancien rapport.

## Conception

Conception : aucune condition, pas de `design.md`. Le changement tient dans `keep_report` et
`hook()`, sans dépendance nouvelle ni migration : les rapports déjà écrits gardent leur nom, et les
lignes qui les citent ne changent pas.

## Revue

Revue : due. Le change touche un livrable face à un tiers, la CLI `uske screen` : `USKE_STEP` est
une interface nouvelle pour les auteurs de crochets, et le nom des rapports change pour
`base-images`.

## Capabilities

### New Capabilities

### Modified Capabilities

- `screen-command` :
  - « Le rapport survit à la commande » : le nom vient de l'epoch, avec un nom libre, sans jamais
    réécrire ;
  - « Un crochet après chaque écriture au journal » : `USKE_STEP` est passé au crochet.

## Impact

- Code : `uske/screen.py` (`keep_report`, `record`, `hook`), `tests/`.
- Documentation : `docs/how-to/operate.md` (les noms des rapports, `USKE_STEP`), l'épilogue de
  `uske screen --help` dans `uske/cli.py`.
- `base-images` : les rapports passent de `<run_id>-<tentative>` (avec `screen.sh`) à `<epoch>`.
  Son crochet peut nommer la porte dans ses commits. Les notes de la release 0.9.0 peuvent retirer
  ce problème connu une fois la version suivante publiée.
