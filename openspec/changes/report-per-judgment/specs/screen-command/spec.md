## MODIFIED Requirements

### Requirement: Un crochet après chaque écriture au journal

Quand `USKE_AFTER_RECORD` est posée, `uske screen` SHALL lancer cette commande, par le shell,
après chaque étape qui a ajouté au moins une ligne au journal, et avant l'étape suivante. Elle lui
SHALL passer dans son environnement :

- `USKE_POLICY`, le nom de la politique ;
- `USKE_RESULTS`, le répertoire du journal ;
- `USKE_STEP`, l'étape qui vient d'écrire. Ses valeurs sont `record` pour les verdicts de la
  première porte, `record-approve` pour les lignes de l'approbation, `record-applied` après
  l'application, `record-held` pour les verdicts de la seconde porte et `record-promoted` après la
  promotion.

Un code de retour non nul MUST arrêter la politique sans aucun placement de plus, et faire sortir
`uske screen` avec le code 1 une fois les autres politiques traitées.

#### Scenario: Commiter le journal avant de placer

- **GIVEN** `USKE_AFTER_RECORD` qui écrit l'heure et `USKE_POLICY` dans un fichier témoin
- **WHEN** `uske screen` consigne les verdicts d'une politique, puis la fait appliquer
- **THEN** le fichier témoin porte le nom de la politique avant que le placeur reçoive
  `--apply-plan`

#### Scenario: Le crochet sait quelle étape l'appelle

- **GIVEN** `USKE_AFTER_RECORD` qui ajoute `USKE_STEP` à un fichier témoin
- **AND** une politique dont une source est réparée, jugée saine en seconde porte, puis promue
- **WHEN** `uske screen` traite cette politique
- **THEN** le fichier témoin porte, dans cet ordre, `record`, `record-held` et `record-promoted`
- **AND** aucune autre étape, puisque ni l'approbation ni l'application n'ont écrit de ligne

#### Scenario: Une source à réparer sans transit

- **GIVEN** `USKE_AFTER_RECORD` qui ajoute `USKE_STEP` à un fichier témoin
- **AND** une source refusée sur des règles réparables, et pas de `--transit`
- **WHEN** `uske screen` traite cette politique
- **THEN** le fichier témoin porte `record`, puis `record-approve`, l'étape qui consigne la source
  `inconclusive` (`uske/no-transit`)

#### Scenario: Le crochet échoue

- **GIVEN** `USKE_AFTER_RECORD=false`
- **WHEN** `uske screen` consigne les verdicts d'une politique
- **THEN** le placeur ne reçoit aucun `--apply-plan` pour cette politique
- **AND** la commande sort avec le code 1

### Requirement: Le rapport survit à la commande

Pour chaque empreinte jugée, `uske screen` SHALL copier les rapports HTML et Markdown que le juge a
écrits sous `--results`, à `reports/<politique>/<empreinte>/<nom>.<ext>`, avant d'écrire la ligne
qui les cite.

`<nom>` SHALL être l'epoch du screening, ou, si un rapport de ce nom existe déjà pour cette
empreinte, le premier nom libre parmi `<epoch>-2`, `<epoch>-3`, et ainsi de suite. Un fichier qui
existe déjà sous `reports/` MUST NOT être réécrit. Le Markdown et le HTML d'un même jugement
SHALL porter le même `<nom>`.

La ligne SHALL citer le Markdown s'il existe, le HTML sinon, par un chemin relatif à `--results`.

#### Scenario: Un rapport cité par un chemin relatif

- **GIVEN** un juge qui écrit `report.html` et `report.md`, et `--epoch 20261017T050000Z`
- **WHEN** `uske screen` consigne le verdict de l'empreinte `sha256:abc…` de la politique `p`
- **THEN** `reports/p/sha256:abc…/20261017T050000Z.md` existe sous `--results`, et la ligne porte
  ce chemin en `report`

#### Scenario: Une empreinte rejugée sous le même epoch

- **GIVEN** une ligne `inconclusive` qui cite `reports/p/sha256:abc…/20261017T050000Z.md`
- **WHEN** `uske screen` rejuge `sha256:abc…` avec le même `--epoch` et le même `--run`
- **THEN** le fichier cité par la première ligne garde son contenu
- **AND** la nouvelle ligne cite `reports/p/sha256:abc…/20261017T050000Z-2.md`, le rapport de son
  propre jugement
