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
- **WHEN** la responsable plateforme le resoumet avec les mêmes paramètres, `merge` à `true`
- **THEN** seule cette politique est rejouée, ses lignes rejoignent son journal, et le journal des
  autres est inchangé

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

### Requirement: Aucun volume partagé entre les pods d'un screening

Aucun pod d'un Workflow enfant MUST NOT monter le volume `uske-results` ni un volume que monte un
autre pod. Ce qui passe d'une étape de l'enfant à la suivante SHALL passer par les artefacts Argo,
dans le dépôt d'artefacts que l'overlay déclare. Seules deux étapes du parent montent
`uske-results` : l'instantané, en lecture, et la fusion, la seule à l'écrire ; toutes deux sous le
verrou `uske-journal`. Le
stockage peut donc rester `ReadWriteOnce` quels que soient les plafonds.

#### Scenario: Le rendu des manifestes

- **WHEN** `deploy/base` est rendu par kustomize
- **THEN** seuls les templates d'instantané (en lecture) et de fusion montent `uske-results`, et
  aucun template de `uske-policy` ne déclare de volume persistant, hors sa fusion

### Requirement: Un enfant juge sur un instantané du journal de sa politique

Avant de créer les enfants, le parent SHALL publier en artefact un instantané des journaux
(`*.jsonl` de `uske-results`, sans les rapports). Chaque enfant SHALL travailler sur une copie du
journal de sa seule politique, tirée de cet instantané : il y ajoute ses lignes à mesure, et ses
étapes lisent cette copie comme elles lisent le journal aujourd'hui (`pending`, `approve`,
`record`). Les lignes qu'un enfant ajoute SHALL former un artefact à part, les seules lignes
nouvelles, avec les rapports qu'elles citent.

#### Scenario: Une décision de la première porte pèse sur l'approbation

- **GIVEN** une source due, jugée saine dans l'enfant
- **WHEN** l'étape `approve` de l'enfant lit sa copie du journal
- **THEN** elle voit le verdict que `record` vient d'y ajouter, et rend l'opération au placeur

### Requirement: Une décision est durable avant le placement qu'elle permet

Le placeur MUST NOT recevoir `--apply-plan` ni `promote` avant que l'artefact qui porte les lignes
de verdict approuvant cette opération soit écrit dans le dépôt d'artefacts. Un dépôt d'artefacts
injoignable MUST faire échouer l'enfant avant tout placement.

#### Scenario: Le dépôt d'artefacts refuse l'écriture

- **GIVEN** un enfant dont l'étape `record` ne peut pas téléverser son artefact de lignes
- **WHEN** l'enfant se poursuit
- **THEN** l'étape `place` ne démarre pas, et l'enfant finit en échec

### Requirement: Une fusion verse les lignes au journal, une politique à la fois

Le parent SHALL finir, après tous ses enfants, en échec ou non, par une étape de fusion : pour
chaque enfant qui a produit un artefact de lignes, elle ajoute ces lignes au journal de sa
politique sur `uske-results`, par la même règle d'ajout que `uske record` — en ajout seul, une
ligne qui répète le dernier état d'une empreinte ou qui précède sa dernière ligne n'est pas écrite —,
et copie les rapports à côté. Elle SHALL tenir le verrou `uske-journal`, que prend aussi la fusion
d'un enfant relancé seul : deux fusions n'écrivent jamais en même temps. La fusion MUST être
rejouable : la rejouer sur les mêmes artefacts n'ajoute aucune ligne. Un enfant relancé seul SHALL
fusionner ses propres lignes quand son paramètre `merge` vaut `true` ; le parent le passe à
`false`.

#### Scenario: Deux politiques, une fusion

- **GIVEN** un screening de deux politiques, dont chaque enfant a ajouté deux lignes
- **WHEN** la fusion tourne
- **THEN** chaque journal gagne ses deux lignes, dans l'ordre où l'enfant les a écrites

#### Scenario: Rejouer la fusion

- **GIVEN** une fusion qui a déjà versé les lignes d'un screening
- **WHEN** l'étape de fusion est rejouée par `argo retry`
- **THEN** aucune ligne n'est ajoutée

#### Scenario: Une ligne écrite à la main pendant le screening

- **GIVEN** une ligne de réouverture ajoutée au journal d'une politique après l'instantané, et plus
  récente qu'une ligne de l'enfant sur la même empreinte
- **WHEN** la fusion tourne
- **THEN** la ligne de l'enfant n'est pas écrite, et la fusion la signale comme périmée sur sa
  sortie d'erreur

#### Scenario: Un enfant en échec a placé une partie

- **GIVEN** un enfant dont l'application a échoué après avoir placé une copie
- **WHEN** la fusion tourne
- **THEN** la ligne de placement de cette copie rejoint le journal

### Requirement: Un journal n'a qu'un écrivain à la fois

Deux Workflows MUST NOT travailler en même temps sur une même politique : le verrou par politique
de l'enfant SHALL s'appliquer à travers tous les screenings du namespace, et le `CronWorkflow`
SHALL interdire deux screenings simultanés. Seule la fusion écrit au journal, sous le verrou
`uske-journal`.

#### Scenario: Une politique rejouée à la main pendant un screening

- **GIVEN** un enfant de la politique P en cours dans un screening
- **WHEN** la responsable plateforme resoumet un enfant de P
- **THEN** le second attend la fin du premier avant sa première étape

### Requirement: Deux plafonds, posés par l'overlay

Le nombre d'enfants actifs à la fois et le nombre de jugements à la fois dans un enfant SHALL être
deux réglages distincts, posés par l'overlay. La base MUST les poser à 1 et à 1, et l'overlay
`kind` aussi.

#### Scenario: La base et le banc

- **WHEN** `deploy/base` et `deploy/kind` sont rendus par kustomize
- **THEN** les deux plafonds valent 1

### Requirement: Une panne reste dans sa politique, et se voit

L'échec d'un enfant MUST NOT empêcher le parent de créer ni d'attendre les autres enfants, ni de
fusionner les lignes qu'ils ont produites. Le parent SHALL finir en échec si au moins un enfant a
fini en échec ou en erreur, ou si la fusion a échoué, et SHALL nommer ces politiques dans sa sortie.
Un enfant SHALL garder la conduite d'aujourd'hui : un verdict non concluant est une issue métier,
une application qui échoue laisse juger et promouvoir ce qui a été retenu, puis fait échouer
l'enfant.

#### Scenario: Une politique sur trois échoue

- **GIVEN** trois politiques, dont l'application de la deuxième échoue
- **WHEN** le screening tourne
- **THEN** la première et la troisième sont conduites jusqu'à leur placement, et leurs lignes
  fusionnées
- **AND** le parent finit en échec et sa sortie nomme la deuxième politique
