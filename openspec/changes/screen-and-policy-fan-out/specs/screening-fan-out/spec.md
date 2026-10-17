## ADDED Requirements

### Requirement: Une politique, un Workflow enfant

Le Workflow d'un screening SHALL lister les politiques, puis créer, pour chacune, un Workflow
enfant tiré du `WorkflowTemplate` `uske-policy`, qui porte les étapes d'une politique telles
qu'avant ce change, chacune dans l'image de son outil, avec la répartition des jugements par
empreinte. L'enfant SHALL porter le nom de sa politique dans un label et le parent comme
propriétaire : supprimer le parent supprime ses enfants. Un enfant SHALL pouvoir être relancé seul,
avec les paramètres que le parent lui a passés.

#### Scenario: Trois politiques

- **GIVEN** un dépôt de trois politiques actives
- **WHEN** un screening tourne
- **THEN** trois Workflows enfants existent, chacun avec le label de sa politique et le parent pour
  propriétaire

#### Scenario: Rejouer une politique

- **GIVEN** un enfant en échec
- **WHEN** la responsable plateforme le resoumet avec les mêmes paramètres
- **THEN** seule cette politique est rejouée, et le journal des autres est inchangé

### Requirement: Un screening, un commit, un epoch, un nom

Le parent SHALL fixer, une fois par screening, le commit du dépôt des politiques, l'epoch des
ordres de remédiation et l'identifiant `run` écrit sur les lignes du journal ; il SHALL passer ces
trois valeurs à chaque enfant. Chaque enfant MUST extraire le dépôt à ce commit, pas à la tête de
sa branche.

#### Scenario: Le dépôt avance pendant le screening

- **GIVEN** un screening dont le parent a fixé le commit C
- **WHEN** un commit D est poussé avant que le dernier enfant extraie le dépôt
- **THEN** cet enfant juge avec les politiques et les jeux de règles de C

#### Scenario: Les lignes d'un screening se reconnaissent

- **GIVEN** un screening de deux politiques
- **WHEN** leurs journaux sont lus
- **THEN** toutes les lignes écrites par ce screening portent le même `run`, le nom du parent

### Requirement: Deux plafonds, posés par l'overlay

Le nombre d'enfants actifs à la fois et le nombre de jugements à la fois dans un enfant SHALL être
deux réglages distincts, posés par l'overlay. La base MUST les poser à 1 et à 1, et l'overlay
`kind` aussi. Un overlay qui porte l'un des deux au-delà de 1 MUST déclarer `ReadWriteMany` pour le
volume `uske-results` et pour le volume de travail de l'enfant ; la vérification des manifestes
(`make lint`) MUST refuser un overlay qui ne le fait pas.

#### Scenario: La base et le banc

- **WHEN** `deploy/base` et `deploy/kind` sont rendus par kustomize
- **THEN** les deux plafonds valent 1, et les volumes restent `ReadWriteOnce`

#### Scenario: Un plafond relevé sans stockage partagé

- **GIVEN** un overlay qui porte à 20 le nombre d'enfants actifs, et garde `uske-results` en
  `ReadWriteOnce`
- **WHEN** `make lint` est lancée
- **THEN** elle échoue en nommant l'overlay et le volume

### Requirement: Un journal n'a qu'un écrivain à la fois

Deux Workflows MUST NOT écrire en même temps le journal d'une même politique : le verrou par
politique de l'enfant SHALL s'appliquer à travers tous les screenings du namespace, et le
`CronWorkflow` SHALL interdire deux screenings simultanés. Deux enfants de politiques différentes
écrivent dans deux fichiers différents.

#### Scenario: Une politique rejouée à la main pendant un screening

- **GIVEN** un enfant de la politique P en cours dans un screening
- **WHEN** la responsable plateforme resoumet un enfant de P
- **THEN** le second attend la fin du premier avant sa première étape

### Requirement: Une panne reste dans sa politique, et se voit

L'échec d'un enfant MUST NOT empêcher le parent de créer ni d'attendre les autres enfants. Le parent
SHALL finir en échec si au moins un enfant a fini en échec ou en erreur, et SHALL nommer ces
politiques dans sa sortie. Un enfant SHALL garder la conduite d'aujourd'hui : un verdict non
concluant est une issue métier, une application qui échoue laisse juger et promouvoir ce qui a été
retenu, puis fait échouer l'enfant.

#### Scenario: Une politique sur trois échoue

- **GIVEN** trois politiques, dont l'application de la deuxième échoue
- **WHEN** le screening tourne
- **THEN** la première et la troisième sont conduites jusqu'à leur placement
- **AND** le parent finit en échec et sa sortie nomme la deuxième politique
