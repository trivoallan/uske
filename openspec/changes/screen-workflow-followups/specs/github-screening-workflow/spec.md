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

## ADDED Requirements

### Requirement: La base grype est partagée d'un run à l'autre, même après un échec

Le workflow SHALL garder la base grype dans le cache d'Actions, une par jour UTC. Quand le cache du
jour manque, il SHALL la télécharger une fois et la sauver avant le screening, de sorte qu'un
screening qui échoue ne perde pas la base téléchargée.

#### Scenario: Un screening qui échoue

- **GIVEN** un run sans cache du jour, dont le screening échoue
- **WHEN** un second run du même jour commence
- **THEN** il restaure la base du cache, sans la télécharger
