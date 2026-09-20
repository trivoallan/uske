## ADDED Requirements

### Requirement: La vérification des ADR est lancée par la chaîne d'intégration

La vérification du répertoire `docs/adr/` contre son schéma MUST être exécutée par la chaîne
d'intégration à chaque demande de fusion. Un instrument que personne ne lance ne prouve rien : la
capacité de vérifier mécaniquement existe déjà, c'est son déclenchement qui manque (`DEBT-06`).

#### Scenario: Une demande de fusion laisse une décision vide

- **GIVEN** une demande de fusion qui ajoute un ADR dont une clé est restée vide
- **WHEN** la chaîne d'intégration s'exécute
- **THEN** la vérification nomme ce fichier
- **AND** son résultat est porté par la demande de fusion, sans qu'une personne ait eu à y penser

#### Scenario: Toutes les décisions sont statuées

- **GIVEN** une demande de fusion où chaque ADR porte un verdict et des clés remplies
- **WHEN** la chaîne d'intégration s'exécute
- **THEN** la vérification ne nomme aucun fichier

### Requirement: Le format dont la version se déduit est tenu là où la fusion l'écrit

Le format des messages dont se déduit une version MUST être vérifié là où le modèle de fusion du
dépôt l'inscrit dans l'historique. Sous une fusion par écrasement, c'est le titre de la demande de
fusion qui devient le message : vérifier les commits de la branche laisserait passer le seul texte
qui compte (`DEBT-03`).

#### Scenario: Un titre de demande de fusion hors format

- **GIVEN** une demande de fusion dont le titre ne suit pas le format décidé
- **WHEN** la chaîne d'intégration s'exécute
- **THEN** le titre est signalé avant la fusion

#### Scenario: Des commits de branche hors format, et un titre conforme

- **GIVEN** une branche dont les commits intermédiaires ne suivent pas le format
- **AND** une demande de fusion dont le titre le suit
- **WHEN** la chaîne d'intégration s'exécute
- **THEN** rien n'est signalé : seul le texte qui entrera dans l'historique est vérifié
