## MODIFIED Requirements

### Requirement: Le journal vit sur une branche dédiée du dépôt appelant

Le workflow SHALL lire et écrire le journal sur la branche `journal-branch` du dépôt appelant,
extraite comme répertoire de résultats d'`uske` avant le screening, hors de l'espace de travail du
dépôt appelant. Si la branche est absente, le workflow SHALL la faire naître orpheline, sans autre
fichier qu'un `.gitignore` qui écarte `reports/`. Le workflow MUST NOT écrire sur aucune autre
branche.

#### Scenario: Premier run

- **GIVEN** un dépôt sans branche `uske-journal`
- **WHEN** le workflow crible une politique dont une empreinte est due
- **THEN** la branche `uske-journal` existe, sans ancêtre commun avec la branche par défaut
- **AND** elle porte le journal de la politique, et aucun rapport

#### Scenario: Deux premiers runs simultanés

- **GIVEN** un dépôt sans branche `uske-journal`, et deux runs qui la font naître en même temps
- **WHEN** le push de naissance du second est refusé parce que la branche existe désormais
- **THEN** le second jette sa racine locale, clone la branche du premier, et poursuit son screening
- **AND** si la branche n'existe toujours pas, il échoue avant de rien placer

#### Scenario: Une empreinte déjà décidée

- **GIVEN** une branche `uske-journal` dont le journal porte déjà une décision pour une empreinte
- **WHEN** le workflow crible la même politique, et que le plan porte la même empreinte
- **THEN** le juge n'est pas appelé pour cette empreinte

#### Scenario: La branche par défaut reste intacte

- **GIVEN** un dépôt dont `main` est protégée
- **WHEN** le workflow crible une politique
- **THEN** `main` ne reçoit aucun commit, et le run réussit

#### Scenario: Un dépôt appelant qui suit un répertoire `results/`

- **GIVEN** un dépôt appelant dont la branche par défaut porte un répertoire `results/`
- **WHEN** le workflow crible une politique
- **THEN** la branche du journal est extraite ou naît, et le screening a lieu

### Requirement: Les rapports partent en archive attachée au run

Le workflow SHALL publier, sous la forme d'une archive attachée au run, les rapports qu'`uske` a
gardés. L'archive est nommée d'après le `metadata.name` de la politique et le numéro de tentative
du run, et conserve le chemin de chaque rapport relatif aux résultats. Le workflow SHALL la publier
même quand le job échoue, avec la rétention de l'entrée `report-retention-days`. Il MUST NOT
commiter les rapports, ni remplacer l'archive d'une tentative précédente.

#### Scenario: Un refus

- **GIVEN** une politique dont une empreinte est refusée
- **WHEN** le run se termine
- **THEN** l'archive du run contient le rapport que cite la ligne de refus, au chemin exact
  qu'elle cite, `sha256:` compris
- **AND** la branche `journal-branch` ne contient aucun rapport

#### Scenario: Une panne après un jugement

- **GIVEN** un juge qui a rendu son rapport, puis un placeur qui échoue
- **WHEN** le job échoue
- **THEN** l'archive des rapports est publiée quand même

#### Scenario: Un job rejoué

- **GIVEN** un run dont le job `screen` a publié son archive
- **WHEN** le job est rejoué
- **THEN** la nouvelle tentative publie sa propre archive, et celle de la première reste

## ADDED Requirements

### Requirement: La base grype est partagée d'un run à l'autre, même après un échec

Le workflow SHALL garder la base grype dans le cache d'Actions, une par jour UTC. Quand le cache du
jour manque, il SHALL la télécharger une fois et la sauver avant le screening, de sorte qu'un
screening qui échoue ne perde pas la base téléchargée.

#### Scenario: Un screening qui échoue

- **GIVEN** un run sans cache du jour, dont le screening échoue
- **WHEN** un second run du même jour commence
- **THEN** il restaure la base du cache, sans la télécharger
