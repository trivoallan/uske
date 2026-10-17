# Conception — `uske screen` et la répartition par politique

Sections d'arc42 touchées : *Solution Strategy* (le choix « Enchaînement » et « Intégration »),
*Deployment View* (deux `WorkflowTemplate`, un `Role`, le stockage `ReadWriteMany`),
*Architecture Decisions* (SDR-0021), *Risks and Technical Debts* (`RISK-05`, un risque nouveau sur
la charge du contrôleur, `DEBT-07`). Les skills `arc42-section-NN` et `devops-engineer` n'ont pas
été lancées : ce change a été ouvert par une autre session, sans personne pour donner son aval ;
les sections se rédigent à la main en `apply`.

## Context

Un screening n'existe que dans ses enchaîneurs : le `WorkflowTemplate` `uske-screening`
(`deploy/base/workflowtemplate.yaml`) et `base-images/screen.sh`, qui en recopie les étapes en
Bash, chacune dans le conteneur publié de son outil. Les deux divergent déjà : `screen.sh` ne
lance pas `record --promoted` après `knock promote`.

Le template répartit déjà le travail : `withParam` par politique, puis par empreinte. Ce qui le
sérialise, c'est `parallelism: 1`, imposé parce que le volume de travail `work` et le journal
`uske-results` sont `ReadWriteOnce`. Un seul Workflow porte toutes les politiques : une trace,
un échec, un rejeu pour tout le monde.

L'ordre de grandeur annoncé est de plus de 10 000 politiques. Un spike de volumétrie, prévu le
2026-10-19, mesurera le temps d'un plan et d'un jugement ; aucun nombre n'existe encore.

Contraintes en vigueur : le journal en ajout seul, qui n'avance que vers l'avant, avec son
vocabulaire (SDR-0016) et sa clé `run` (SDR-0018) ; le cœur sans entrée-sortie (SDR-0003, non tenu,
`DEBT-01`) ; les objectifs qualité de la section 1 d'arc42, dans leur ordre.

## Goals / Non-Goals

**Goals:**

- Un screening entier en une commande, hors du cluster, qui décide exactement comme le workflow.
- Une politique par Workflow enfant, que l'on rejoue seule ; un nombre de politiques et de
  jugements simultanés réglable par l'overlay.
- Le parent fixe ce qui doit être commun au screening : le commit du dépôt, l'epoch, le `run`.

**Non-Goals:**

- Fixer les plafonds : le spike les donnera.
- Décider le support du journal (`DEBT-08`) ou statuer sur le planificateur (`DEBT-07`) ;
  ce change s'appuie sur Argo sans clore la dette.
- Découper en plusieurs `CronWorkflow` : le paramètre `policies` le permet déjà.
- Modifier `base-images/screen.sh` : son passage à `uske screen` est un change de ce dépôt-là.
- Paralléliser les jugements de `uske screen` : il sert le poste et la CI.

## Decisions

### D1 — `uske screen` enchaîne les fonctions des sous-commandes, pas leur ligne de commande

Un module `uske/screen.py` appelle, dans l'ordre de l'enfant `uske-policy`, les mêmes fonctions de
`gate`, `results`, `outcomes` et `playbooks` que les `cmd_*` de `cli.py`. Là où un `cmd_*` mêle
lecture d'arguments et décision (`cmd_classify`, `cmd_record`, `cmd_approve`), la décision passe
dans une fonction sans `argparse`, que le `cmd_*` et `screen` appellent tous deux.

*Écartée :* rappeler `uske.cli.main([...])` pour chaque étape. C'est plus court, mais chaque étape
relirait le journal et repasserait par du JSON sur la sortie standard, et une `Failure` au milieu
se confondrait avec la fin.

La garantie « mêmes lignes que les étapes » se tient par un test de parité (scénario *Les mêmes
lignes que les étapes*) : de faux `regis` et `knock`, en scripts Python, écrivent des fichiers
figés ; le test conduit le screening une fois par `screen`, une fois par les sous-commandes, et
compare les journaux sans `ts`.

### D2 — Les outils sont des commandes, un préfixe les déplace

`regis` et `knock` se lancent par `subprocess.run(prefix + args)`, sans shell. `prefix` vaut
`shlex.split(os.environ["USKE_REGIS_CMD"])` si la variable est posée, `["regis"]` sinon ; idem
pour `knock`. `shutil.which(prefix[0])` est vérifié pour les deux avant toute étape.

`uske` passe aux outils les chemins qu'il voit. Avec un préfixe `docker run`, l'opérateur monte
le répertoire de travail et le journal au même chemin dans le conteneur (`-v "$W:$W"`) ; le README
le dit. *Écartée :* traduire les chemins par une table hôte → conteneur. `uske` saurait alors
comment un outil est lancé.

*Écartée :* mettre `regis` et `knock` en dépendances Python. Cela lierait trois versions et
contredirait la règle « par leur ligne de commande ».

### D3 — Un répertoire de travail, jetable mais montrable

`--work` désigne le répertoire où vivent la politique préparée, les plans, les rapports, les
lignes et les listes d'images retenues, avec la même arborescence que `/work` dans le workflow.
Par défaut, un `tempfile.mkdtemp()`, dont le chemin est écrit sur la sortie d'erreur et qui n'est
pas supprimé. Un screening en échec se diagnostique en lisant ce répertoire.

### D4 — Le crochet après écriture, plutôt que git dans `uske`

`screen.sh` commite le journal avant chaque placement, pour qu'aucune image ne soit placée sans
sa décision écrite. `uske screen` lance `USKE_AFTER_RECORD` par `sh -c`, avec `USKE_POLICY` et
`USKE_RESULTS` dans l'environnement, après chaque étape qui a ajouté au moins une ligne. Un code
non nul arrête la politique. `base-images` y met son `compose_reports` et son `commit_journal`.

Le crochet est une commande de l'opérateur, au même titre que le préfixe des outils : il n'élargit
pas la confiance.

### D5 — Les rapports, par un chemin relatif

`screen` copie `report.html` et `report.md` sous `<results>/reports/<politique>/<empreinte>/<run>.<ext>`,
où `<run>` vaut `--run` ou l'epoch, et la ligne cite le Markdown par un chemin relatif à `--results`.
La spec `decision-lookup` lit déjà un chemin relatif comme « rangé à côté du journal ». Le workflow,
lui, garde son chemin absolu sur le volume. *Écartée :* le chemin absolu partout. Hors du cluster,
le journal voyage dans un dépôt git, et un chemin absolu du poste n'y désigne rien.

### D6 — Codes de retour et sortie

0 si chaque politique est allée au bout, verdicts quelconques. 1 si une politique a échoué : un
outil introuvable, une écriture au journal ou un crochet en échec, un `--apply-plan` ou un `promote`
en échec. Les politiques suivantes sont conduites quand même, sauf pour un outil introuvable,
vérifié avant tout. 2 pour une erreur d'usage. Sur la sortie standard, une ligne JSON par
politique : `{"policy", "judged", "approved", "ordered", "promoted", "outcome"}`. Avec
`--judge-only`, les lignes de verdict.

### D7 — Un parent qui crée des Workflows, un enfant par politique

`uske-screening` devient le parent :

1. `checkout` extrait le dépôt et sort son commit (`git rev-parse HEAD`).
2. `list` liste les politiques.
3. `policy`, en `withParam`, est un template `resource` : `action: create` d'un `Workflow` dont
   `workflowTemplateRef` vaut `uske-policy`, avec `setOwnerReference: true`, le label
   `uske.io/policy`, `successCondition: status.phase == Succeeded` et
   `failureCondition: status.phase in (Failed,Error)`. `continueOn: failed` pour que les autres
   politiques continuent.
4. `summary` écrit les politiques en échec et fait échouer le parent s'il y en a une.

Le `spec.parallelism` du parent est le plafond de politiques ; celui de `uske-policy` est le
plafond de jugements. Ces champs sont des entiers, pas des paramètres Argo : l'overlay les pose par
un patch kustomize.

L'enfant reçoit `repository`, `commit`, `name`, `path`, `playbooks`, `transit`, `epoch` et `run`. Son
`checkout` fait `git init`, `git fetch --depth 1 origin <commit>`, puis `git checkout FETCH_HEAD`.
Il garde un `volumeClaimTemplate` `work` à lui, le mutex `policy-<name>`, et les étapes
d'aujourd'hui, à ceci près que `{{workflow.name}}` devient le paramètre `run` et que l'epoch vient
du parent. Le parent passe `run = {{workflow.name}}` : toutes les lignes d'un screening portent le
même `run` (SDR-0018).

*Écartée :* `templateRef` vers `uske-policy` dans le même Workflow. Les étapes partageraient le
volume du parent et la trace unique, ce qu'il s'agit de quitter.

*Écartée :* un Workflow par politique soumis par un `CronWorkflow` par politique. 10 000
`CronWorkflow` à tenir, et plus de commit commun.

### D8 — Le droit de créer des Workflows

Le compte `uske` reçoit, dans son `Role`, `create`, `get`, `list`, `watch` et `patch` sur
`workflows.argoproj.io`, ce que demande un template `resource`. Rien d'autre n'est élargi.

### D9 — Le stockage partagé se vérifie au rendu

Un script `deploy/check-storage.py`, en bibliothèque standard plus `pyyaml`, lit un rendu
kustomize. Si le `parallelism` de l'un des deux templates dépasse 1, il exige `ReadWriteMany` sur le
`PersistentVolumeClaim` `uske-results` et sur le `volumeClaimTemplate` `work` de `uske-policy`. Sinon,
il sort en 1 en nommant le volume. `make lint` le lance sur chaque overlay du dépôt, aujourd'hui
`deploy/kind`. Un test le lance sur un rendu fautif en fixture.

### D10 — Le banc garde 1 et 1, et ses patches suivent

`deploy/kind` remplace le `checkout` du parent et de l'enfant par sa copie depuis `hostPath`, et
monte le CA et la clé de `knock` dans les templates de l'enfant. Ses patches visent aujourd'hui des
indices (`/spec/templates/3`) que la scission déplace. Ils sont réécrits, et le README du banc dit
de lancer `deploy/kind/screening.yaml` comme avant.

### D11 — Renouveler l'ordre sur un tag réparé

Le plan de `knock` (`ReconcilePlan`, `knock/domain/gate.py` sur `origin/main`) marque
`remediated: true` une opération dont le tag de destination porte une réparation. `_decide` de
`uske/gate.py` renvoie aujourd'hui `None` (rendue telle quelle) pour une source en
`direct-placement` ; il renvoie désormais `order` quand l'opération est marquée et qu'un transit est
nommé, et `no-transit` sans transit. Les causes `refused` et `attempts-exhausted` passent avant la
marque. La règle vit dans `gate.py`, donc le workflow et `uske screen` la tiennent tous deux sans
autre geste. L'image réparée est jugée à la seconde porte comme toute autre.

*Écartée :* que `knock` renouvelle seul l'ordre quand il voit la marque. `knock` reste un exécutant
(son ADR 0051) : décider d'une remédiation revient à l'orchestrateur, qui en écrit la trace.

*Écartée :* que `uske` lise la destination pour savoir si un tag est réparé. Il ne connaît pas la
forme d'une réparation, et la marque du plan est déjà là.

## Risks / Trade-offs

- [Un `knock` qui n'écrit pas `remediated` laisse un correctif amont défaire une réparation] →
  l'overlay épingle `knock` par empreinte ; le README dit la version minimale.
- [Un tag réparé sans transit est retiré et sa source repasse `inconclusive` : elle est rejugée à
  chaque screening tant qu'aucun transit n'est nommé] → c'est la conduite de `uske/no-transit`
  aujourd'hui ; la fraîcheur cède à la Sûreté.

- [10 000 objets `Workflow` par screening, toutes les 5 minutes, chargent le contrôleur Argo et
  etcd] → `ttlStrategy.secondsAfterCompletion` et `podGC: OnPodSuccess` sur l'enfant ; le
  propriétaire supprime les enfants avec le parent ; le spike mesure. Si cela ne tient pas, il
  reste à découper en plusieurs `CronWorkflow` sur des sous-répertoires de `policies`.
- [Chaque `resource` qui attend son enfant occupe un pod] → borné par le plafond de politiques,
  pas par leur nombre.
- [Le stockage `ReadWriteMany` manque là où `uske` sera déployé] → les plafonds restent à 1, et le
  passage de fichiers par artefacts Argo est l'alternative consignée dans `proposal.md`.
- [`concurrencyPolicy: Forbid` saute un screening quand le précédent dure plus de 5 minutes] →
  c'est la conduite voulue : une politique n'a qu'un écrivain. Le spike dira si la cadence tient.
- [Le verrou `policy-<name>` est une ressource du namespace : deux namespaces qui partagent un
  volume de journal le contourneraient] → un seul namespace par volume `uske-results`, dit au README.
- [`uske screen` fond les étapes que l'Opérabilité veut séparées] → hors du cluster seulement. Le
  répertoire `--work` gardé et la sortie par politique rendent le diagnostic ; une politique se
  rejoue par `--policy`.
- [Des chemins qui diffèrent entre `uske` et un outil en conteneur] → l'outil échoue à lire ou à
  écrire. La panne remonte en code 1 (`knock`) ou en `inconclusive` (`regis`), jamais en
  placement. Le README impose le montage au même chemin.
- [`uske` grossit (Minceur)] → un module qui n'ajoute aucune règle de jugement ni aucun geste de
  placement ; il ne fait que lancer et lire.

## Migration Plan

1. Livrer `uske screen` seul, avec son test de parité : rien ne change pour le cluster.
2. Livrer la scission du template et le `Role`, plafonds à 1. Le parent garde le nom
   `uske-screening` : le `CronWorkflow` ne change pas. Un screening en cours finit sur la
   définition qu'il a déjà lue.
3. Lancer le banc : `deploy/kind/up.sh`, puis un screening ; vérifier un enfant par politique et
   des journaux identiques à ceux d'avant la scission.
4. Après le spike, un overlay de production pose ses plafonds et son stockage `ReadWriteMany`.

Retour arrière : réappliquer les manifestes de la version précédente. Le journal ne change pas de
forme, et un enfant interrompu laisse sa politique due au screening suivant, comme aujourd'hui.

## Open Questions

- Les deux plafonds, et si un parent tient 10 000 enfants : le spike du 2026-10-19.
- SDR-0021 (ci-dessous, `tasks.md`) attend son verdict : il lève la règle « `uske` ne lance
  jamais ses voisins » pour le seul verbe `screen`. Aucun ADR en vigueur ne porte cette règle (elle
  vit dans le README et dans *Solution Strategy*), et aucun n'est donc dépassé.
- `DEBT-07` reste ouvert : ce change approfondit le choix d'Argo sans peser les options écartées
  (GitLab CI reste une hypothèse de cible).
