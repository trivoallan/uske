## RENAMED Requirements

- FROM: `### Requirement: Les rapports partent en archive attachée au run`
- TO: `### Requirement: Les rapports cités sont commités avec la ligne qui les cite`

## MODIFIED Requirements

### Requirement: Le journal vit sur une branche dédiée du dépôt appelant

Le workflow SHALL lire et écrire le journal sur la branche `journal-branch` du dépôt appelant,
extraite comme répertoire de résultats d'`uske` avant le screening, hors de l'espace de travail du
dépôt appelant. Si la branche est absente, le workflow SHALL la faire naître orpheline, par un
commit vide. Le workflow MUST NOT écrire sur aucune autre branche.

#### Scenario: Premier run

- **GIVEN** un dépôt sans branche `uske-journal`
- **WHEN** le workflow crible une politique dont une empreinte est due
- **THEN** la branche `uske-journal` existe, sans ancêtre commun avec la branche par défaut
- **AND** elle porte le journal de la politique et les rapports que citent ses lignes

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

#### Scenario: Un dépôt appelant qui suit `results/`

- **GIVEN** un dépôt appelant qui suit un répertoire `results/` sur sa branche par défaut
- **WHEN** le workflow crible une politique
- **THEN** la branche du journal est extraite sans heurter ce répertoire, et le screening a lieu

### Requirement: Le journal est poussé avant le placement qui suit, et encore à la fin

Après chaque écriture au journal, le workflow SHALL commiter le journal de la politique et les
rapports de la politique, puis les pousser sur `journal-branch`. Si le push est refusé, il SHALL
rejouer sur rebase, trois fois au plus. Un échec au-delà MUST arrêter la politique, sans rien
placer de plus, et faire échouer le job. À la fin du job, que le screening ait réussi ou non, le
workflow SHALL commiter et pousser de nouveau le journal et les rapports de la politique, et MUST
faire échouer le job si ce dernier push échoue.

#### Scenario: Un push concurrent

- **GIVEN** un autre run qui a poussé le journal d'une autre politique entre deux écritures
- **WHEN** le workflow pousse son journal
- **THEN** le push réussit après un rebase, et les deux journaux sont sur la branche

#### Scenario: Le push échoue avant un placement

- **GIVEN** une branche `journal-branch` sur laquelle le jeton ne peut pas pousser
- **WHEN** le screening écrit sa première ligne de verdict
- **THEN** le job échoue, et le placeur n'a reçu aucun `--apply-plan`

#### Scenario: Le push échoue après un placement

- **GIVEN** un placement fait, et un push de la ligne `placed` refusé par le crochet
- **WHEN** le job se termine
- **THEN** l'étape finale repousse le journal, et la ligne `placed` est sur la branche
- **AND** si ce dernier push échoue aussi, le job échoue

### Requirement: Les rapports cités sont commités avec la ligne qui les cite

Le workflow SHALL commiter les rapports qu'`uske` a gardés pour la politique sous
`reports/<metadata.name>/`, sur `journal-branch`, dans le commit qui porte la première ligne qui
les cite, au chemin exact qu'elle cite. Il MUST NOT commiter les rapports d'une autre politique.
Il SHALL aussi publier ceux que le run a écrits, et eux seuls, sous la forme d'une archive
attachée au run, nommée d'après le `metadata.name` de la politique, même quand le job échoue, avec la rétention de l'entrée
`report-retention-days`.

#### Scenario: Un refus

- **GIVEN** une politique dont une empreinte est refusée
- **WHEN** le run se termine
- **THEN** la branche `journal-branch` porte le rapport que cite la ligne de refus, au chemin exact
  qu'elle cite, `sha256:` compris, dans le commit qui porte cette ligne
- **AND** l'archive du run le contient au même chemin

#### Scenario: Un job rejoué

- **GIVEN** une première tentative qui a poussé une ligne de refus et son rapport
- **WHEN** le job est rejoué, et que GitHub supprime l'archive de la première tentative
- **THEN** le rapport que cite la ligne reste sur la branche

#### Scenario: L'archive ne reprend pas la branche

- **GIVEN** une branche `journal-branch` qui porte déjà les rapports d'un run précédent
- **WHEN** le run juge une empreinte nouvelle
- **THEN** l'archive du run ne contient que le rapport de cette empreinte

#### Scenario: Une branche née avant ce change

- **GIVEN** une branche `journal-branch` dont le `.gitignore` écarte `reports/`
- **WHEN** le workflow pousse une ligne qui cite un rapport
- **THEN** le rapport est commité quand même

#### Scenario: Une panne après un jugement

- **GIVEN** un juge qui a rendu son rapport, puis un placeur qui échoue
- **WHEN** le job échoue
- **THEN** l'étape finale commite et pousse le rapport, et l'archive est publiée quand même
