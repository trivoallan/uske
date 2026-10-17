## ADDED Requirements

### Requirement: Un screening entier en une commande, dans l'ordre du workflow

`uske screen` SHALL conduire, pour chaque politique de `--policies` (ou la seule politique de
`--policy`), dans cet ordre : préparer la politique, faire écrire son plan au placeur, faire juger
chaque empreinte encore due, consigner ces verdicts, approuver le plan moins les refus, consigner
les lignes de l'approbation, faire appliquer le plan approuvé (avec le transit quand le plan porte
un ordre de remédiation), consigner les placements, puis, s'il y a des images retenues : les faire
juger, consigner, approuver, faire promouvoir les saines et consigner les promotions. Chaque étape
MUST produire les mêmes lignes de journal que la sous-commande d'étape du même nom, à `ts` près.
Les politiques SHALL être traitées l'une après l'autre, dans l'ordre de `uske list`.

#### Scenario: Une copie saine

- **GIVEN** une politique dont le plan porte une copie, et un juge qui rend `direct-placement`
- **WHEN** `uske screen --policy <fichier>` est lancée
- **THEN** le journal gagne la ligne de verdict de l'empreinte, puis sa ligne de placement
- **AND** le placeur a reçu `reconcile --apply-plan` avec un plan qui contient l'opération

#### Scenario: Les mêmes lignes que les étapes

- **GIVEN** les mêmes plans, rapports et listes d'images retenues, écrits par de faux outils
- **WHEN** un screening est conduit une fois par `uske screen`, une fois par les sous-commandes
  d'étape dans l'ordre du workflow, chacun sur un journal vide
- **THEN** les deux journaux portent les mêmes lignes, dans le même ordre, clés `ts` exceptées

#### Scenario: Une source à réparer

- **GIVEN** une source refusée sur une règle réparable, un plan qui déclare l'opération
  reconstruite, et `--transit transit`
- **WHEN** `uske screen` est lancée
- **THEN** le placeur reçoit `--stage-to transit`, l'image retenue est jugée par sa propre
  empreinte, et elle n'est promue que sur `direct-placement`

#### Scenario: Un régime inconnu

- **GIVEN** une politique dont le régime n'a pas de jeu de règles
- **WHEN** `uske screen` est lancée
- **THEN** le juge n'est pas appelé, et chaque empreinte due est consignée `inconclusive`, raison
  `uske/unknown-track`

### Requirement: Le journal est écrit avant tout placement qui en dépend

`uske screen` MUST NOT demander au placeur d'appliquer ni de promouvoir une opération avant que les
verdicts qui l'approuvent soient écrits au journal. Une écriture au journal qui échoue MUST arrêter
la politique avant son placement.

#### Scenario: Le journal ne peut pas être écrit

- **GIVEN** un répertoire `--results` en lecture seule
- **WHEN** `uske screen` est lancée sur une politique dont une empreinte est saine
- **THEN** le placeur ne reçoit aucun `--apply-plan`, et la commande sort avec le code 1

### Requirement: Les deux outils sont appelés par leur ligne de commande

`uske screen` SHALL lancer le juge par la commande `regis` et le placeur par la commande `knock`,
cherchées sur le `PATH`. `USKE_REGIS_CMD` et `USKE_KNOCK_CMD`, quand elles sont posées, SHALL
remplacer chacune le nom de sa commande par un préfixe, découpé comme le ferait un shell POSIX et
lancé sans shell, auquel les arguments s'ajoutent. Les chemins passés aux outils sont ceux que voit
`uske`. Une commande introuvable MUST faire échouer `uske screen` avec `error:`, le nom de la
commande et le code 1, avant toute écriture au journal et tout placement. `uske` ne lit rien
d'autre de l'outil que ses fichiers de sortie et son code de retour.

#### Scenario: Un préfixe docker

- **GIVEN** `USKE_REGIS_CMD="docker run --rm -v /w:/w regis:1"`
- **WHEN** `uske screen` fait juger une empreinte
- **THEN** le processus lancé est `docker` avec les arguments `run --rm -v /w:/w regis:1 analyze …`

#### Scenario: Le placeur manque

- **GIVEN** un `PATH` sans `knock` et `USKE_KNOCK_CMD` non posée
- **WHEN** `uske screen` est lancée
- **THEN** la sortie d'erreur porte `error:` et `knock`, la commande sort avec le code 1
- **AND** le journal n'est pas modifié

### Requirement: Juger sans consigner ni placer

Avec `--judge-only`, `uske screen` SHALL faire planifier et juger chaque empreinte due, et écrire
sur la sortie standard les lignes de verdict qu'elle aurait consignées. Elle MUST NOT écrire au
journal, ni appeler le placeur autrement que pour `--plan-out`, ni lancer le crochet après
écriture.

#### Scenario: Une demande de fusion

- **GIVEN** une politique dont une empreinte est due
- **WHEN** `uske screen --judge-only` est lancée
- **THEN** la sortie standard porte la ligne de verdict de cette empreinte
- **AND** le journal est inchangé, et le placeur n'a reçu que `reconcile --plan-out`

### Requirement: Un crochet après chaque écriture au journal

Quand `USKE_AFTER_RECORD` est posée, `uske screen` SHALL lancer cette commande, par le shell,
après chaque étape qui a ajouté au moins une ligne au journal, et avant l'étape suivante. Elle lui
SHALL passer `USKE_POLICY` (le nom de la politique) et `USKE_RESULTS` (le répertoire du journal)
dans son environnement. Un code de retour non nul MUST arrêter la politique sans aucun placement de
plus, et faire sortir `uske screen` avec le code 1 une fois les autres politiques traitées.

#### Scenario: Commiter le journal avant de placer

- **GIVEN** `USKE_AFTER_RECORD` qui écrit l'heure et `USKE_POLICY` dans un fichier témoin
- **WHEN** `uske screen` consigne les verdicts d'une politique, puis la fait appliquer
- **THEN** le fichier témoin porte le nom de la politique avant que le placeur reçoive
  `--apply-plan`

#### Scenario: Le crochet échoue

- **GIVEN** `USKE_AFTER_RECORD=false`
- **WHEN** `uske screen` consigne les verdicts d'une politique
- **THEN** le placeur ne reçoit aucun `--apply-plan` pour cette politique
- **AND** la commande sort avec le code 1

### Requirement: Une issue métier n'est pas une panne

`uske screen` SHALL sortir avec le code 0 quand chaque politique a été conduite jusqu'au bout,
quels que soient ses verdicts, `quarantine` et `inconclusive` compris. Un juge qui échoue SHALL
donner un verdict `inconclusive`, pas une panne. Une application ou une promotion qui échoue MUST
NOT empêcher de juger ni de promouvoir ce que le placeur a retenu malgré elle, ni de conduire les
politiques suivantes ; `uske screen` SHALL alors sortir avec le code 1. La commande SHALL écrire
sur la sortie standard un objet JSON par politique : son nom, le nombre d'empreintes jugées,
approuvées, ordonnées, promues, et son issue, `ok` ou `failed`.

#### Scenario: Une quarantaine

- **GIVEN** une politique dont la seule empreinte due est refusée sur une règle critique non
  réparable
- **WHEN** `uske screen` est lancée
- **THEN** la commande sort avec le code 0 et le journal porte une ligne `quarantine`

#### Scenario: Une politique casse, la suivante passe

- **GIVEN** deux politiques, dont l'application de la première échoue
- **WHEN** `uske screen --policies <répertoire>` est lancée
- **THEN** la seconde est conduite jusqu'à son placement
- **AND** la commande sort avec le code 1, et l'objet de la première porte `failed`

### Requirement: Le rapport survit à la commande

Pour chaque empreinte jugée, `uske screen` SHALL copier les rapports HTML et Markdown que le juge a
écrits sous `--results`, à `reports/<politique>/<empreinte>/<run>.<ext>`, où `<run>` est `--run`,
ou l'epoch du screening à défaut, avant d'écrire la ligne qui les cite. La ligne SHALL citer le
Markdown s'il existe, le HTML sinon, par un chemin relatif à `--results`.

#### Scenario: Un rapport cité par un chemin relatif

- **GIVEN** un juge qui écrit `report.html` et `report.md`, et `--run 41`
- **WHEN** `uske screen` consigne le verdict de l'empreinte `sha256:abc…` de la politique `p`
- **THEN** `reports/p/sha256:abc…/41.md` existe sous `--results`, et la ligne porte ce chemin en
  `report`

### Requirement: Un nom de politique ne désigne jamais un chemin

Le `metadata.name` d'une politique nomme des fichiers (journal, rapports, travail) et le label de
son Workflow enfant : il MUST être un sous-domaine DNS-1123 de 63 caractères au plus —
minuscules, chiffres, `-` et `.`, commençant et finissant par un alphanumérique. Une politique dont le nom
ne l'est pas MUST être refusée à la lecture : signalée `skipped:` par `--policies`, en `error:`
et code 1 par `--policy`. Aucun chemin construit à partir d'un nom ou d'une empreinte MUST NOT
sortir de `--work` ni de `--results`.

#### Scenario: Un nom qui remonte l'arborescence

- **GIVEN** une politique nommée `../x`, et un répertoire témoin à côté de `--work`
- **WHEN** `uske screen --policy <fichier>` est lancée
- **THEN** la commande sort avec le code 1, le répertoire témoin est intact, et aucun outil n'est
  appelé
