# Proposition — les rapports cités survivent au rejeu d'un job

Suite du change `screen-workflow-followups` (trivoallan/uske#64), qui a consigné `RISK-13` sans le
corriger. Objectif qualité : **Contestability** (rang 2).

## Why

Sur GitHub Actions, rejouer le job `screen` d'`extra-screen.yml` supprime l'archive
`uske-reports-<nom>` de la tentative précédente, quel que soit son nom (sondes du 2026-10-17, runs
39026356045 et 39026418538). Les lignes que cette tentative a poussées sur la branche du journal
citent pourtant ces rapports : elles gardent état, playbook et raison, mais plus le rapport. Le
guide dit pour l'instant de lancer un nouveau run plutôt que de rejouer. Le workflow est publié
depuis `v0.11.0` : son interface ne change pas ici.

## Options

Faits mesurés : un jugement ne rejuge pas une empreinte déjà décidée, donc les rapports croissent
avec les empreintes nouvelles, pas avec les runs. Sur le banc, l'archive d'un run pèse de 8 à
131 Ko compressée. `uske` copie le rapport sous `reports/<nom>/<empreinte>/` **avant** d'écrire la
ligne qui le cite (D5 d'origine), et ne réécrit jamais un rapport (`open("xb")`).

| Option | Contestability (rang 2) | Coût | Verdict |
|---|---|---|---|
| **A. Commiter les rapports sur la branche du journal**, dans le commit de la ligne qui les cite | Le rapport vit aussi longtemps que la ligne, dans le même commit ; l'historique montre toute suppression (même garde que `RISK-01`). Ferme aussi la limite de 90 jours (question ouverte 1 de `github-action`). | Rouvre D5 de `github-action` (« le dépôt grossit à chaque jugement ») ; la croissance suit les empreintes nouvelles. Un rapport commité ne s'efface plus sans réécrire la branche. L'archive du run n'est plus la seule copie. | Ferme `RISK-13` |
| B. Branche dédiée `uske-reports` | Même durée que A | Deux pushes par étape : une ligne peut arriver sans son rapport. Logique de rebase doublée. | Dominée par A |
| C. Paquet OCI (GHCR, `oras`) | Survit au rejeu ; supprimable par un administrateur du paquet sans trace dans le dépôt | Un outil de plus ; la ligne cite un chemin, pas une référence OCI | Écartée |
| D. Asset de release par run | Survit au rejeu ; supprimable sans trace | Une release par run encombre les releases | Écartée |
| E. Refuser le rejeu : le job `screen` échoue d'emblée si `github.run_attempt > 1` | Aucun rapport cité n'est perdu ; la durée reste de 90 jours au plus | Une ligne, mais un run échoué ne se rejoue plus depuis l'interface (arc42 le compte pour l'Operability) : il faut lancer un nouveau run | Ferme `RISK-13`, au prix de l'Operability |
| F. Accepter le risque | Le scénario « trois semaines, une minute » tient sur la ligne seule ; le rapport est perdu | Rien | Laisse `RISK-13` ouvert |

## Décision

**Option A**, tranchée par Tristan le 2026-10-17. Elle rouvre D5 de `github-action` : la
croissance de la branche, qui l'avait fait écarter, suit les empreintes nouvelles et non les runs,
et la Contestability (rang 2) passe avant la sobriété du dépôt. Les rapports de `regis` ne gardent
d'un secret trouvé que sa forme masquée (`Redacted`) : l'historique n'en grave aucun en clair.

`v0.11.0` étant publiée, l'archive du run et l'entrée `report-retention-days` restent : les
retirer casserait les appelants. L'archive n'est plus qu'une commodité de téléchargement.

## What Changes

- **Le crochet commite les rapports de la politique** avec son journal : `git add -f` sur
  `<nom>.jsonl` et `reports/<nom>/`. `uske` copie le rapport avant d'écrire la ligne qui le cite
  (D5 d'origine), donc le commit qui porte la ligne porte aussi son rapport. L'étape finale passe
  par le même crochet.
- **La branche naît sans `.gitignore`** : un commit vide. Une branche née en `v0.11.0` garde son
  `.gitignore`, que `-f` contourne.
- **Docs** : le guide dit où trouver un rapport sur la branche et retire « lancer un nouveau run
  plutôt que rejouer » ; la référence et arc42 (section 7, `RISK-13` clos) suivent.

## Capabilities

### Modified Capabilities

- `github-screening-workflow` : « Le journal vit sur une branche dédiée du dépôt appelant »
  (naissance sans `.gitignore`), « Le journal est poussé avant le placement qui suit, et encore à
  la fin » (avec ses rapports), et « Les rapports partent en archive attachée au run », renommée
  « Les rapports cités sont commités avec la ligne qui les cite ».

## Impact

`.github/workflows/extra-screen.yml`, `tests/test_screen_workflow.py`,
`docs/how-to/screen-from-github.md`, `docs/reference/screen-workflow.md`,
`docs/architecture/arc42.md` (section 7 et `RISK-13`). Aucun changement d'`uske` lui-même.
