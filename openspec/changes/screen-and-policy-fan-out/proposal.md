# Proposition — un screening en une commande locale, et un workflow qui répartit les politiques

## Why

Un screening n'existe aujourd'hui que dans deux enchaînements écrits à la main : le
`WorkflowTemplate` `uske-screening` et `base-images/screen.sh`, qui recopie ses étapes en Bash et
dérive déjà (il ne consigne pas les placements promus). Le premier traite toutes les politiques
dans un seul Workflow, avec `parallelism: 1`, parce que ses deux volumes sont `ReadWriteOnce`.
L'ordre de grandeur annoncé est de plus de 10 000 politiques : à ce rythme, un screening ne finit
jamais dans sa fenêtre de 5 minutes. Le moment est venu parce que la remédiation sur ordre
(`remediate:`, `--stage-to`, `knock promote`) a rendu le chaînage assez long pour qu'une troisième
copie à la main coûte plus cher qu'une commande.

## What Changes

- **Nouveau verbe `uske screen`** : un screening entier, en local, en une commande. Pour chaque
  politique (toutes celles d'un répertoire, ou une seule par `--policy`) : préparer, faire planifier
  `knock`, faire juger par `regis` chaque empreinte encore due, consigner, approuver, faire appliquer
  le plan moins les refus, juger les images retenues dans le transit, faire promouvoir les saines,
  consigner. Il réemploie les fonctions des sous-commandes existantes, dans le même ordre que le
  workflow.
- `uske screen` lance `regis` et `knock` comme des commandes : celles du `PATH` par défaut, ou un
  préfixe donné par `USKE_REGIS_CMD` et `USKE_KNOCK_CMD` (par exemple `docker run --rm … <image>`).
  **Cela met fin à la règle « `uske` ne lance jamais `regis` ni `knock` lui-même »**, pour ce seul
  verbe ; les sous-commandes d'étape ne changent pas.
- `--judge-only` : planifier et juger, ne rien consigner ni placer (le `SCREEN_MODE=judge` des
  demandes de fusion de `base-images`).
- Une commande nommée par `USKE_AFTER_RECORD` est lancée après chaque écriture au journal et
  avant le placement qui suit ; son échec arrête la politique, sans rien placer. C'est là que
  `base-images` commite son journal et recompose ses rapports : `uske` ne connaît pas git.
- **Le workflow se scinde en deux** : un `WorkflowTemplate` parent extrait le dépôt une fois, fixe
  son commit, l'epoch et l'identifiant du screening, liste les politiques, puis crée un Workflow
  enfant par politique. L'enfant, `uske-policy`, porte les étapes d'aujourd'hui, chacune dans
  l'image de son outil, et garde la répartition des jugements par empreinte.
- Deux plafonds, posés par l'overlay : le nombre de politiques traitées à la fois, et le nombre de
  jugements à la fois dans une politique. La base garde 1 et 1 ; le banc `kind` aussi, sur du
  stockage `ReadWriteOnce`.
- Au-delà de 1, l'overlay doit fournir un stockage `ReadWriteMany` pour `uske-results` et pour le
  volume de travail de chaque enfant. Le verrou par politique et le journal à un fichier par
  politique restent ce qui empêche deux écritures concurrentes sur un même journal.
- La panne d'une politique n'arrête pas les autres ; le screening finit en échec si l'une a échoué.
- **Le renouvellement d'une réparation** (décision D11 de la revue des étapes de durcissement de
  `knock`) : une opération que le plan de `knock` marque `remediated: true` repart avec un ordre de
  remédiation, même sur une source saine. Sans cela, le correctif amont suivant d'un tag réparé
  serait placé sans réparation, et une image réparée pour tourner sans root redeviendrait root sans
  bruit. `knock` reste un exécutant : c'est à l'orchestrateur de renouveler.

## Alternatives écartées

- **Ne rien faire** : `parallelism: 1` sur 10 000 politiques ne tient pas la fenêtre de 5 minutes,
  et `screen.sh` continue de dériver du workflow à chaque change.
- **Un seul pod par politique qui lance `uske screen`** : il faudrait une image qui embarque
  `regis`, `knock` et `uske`, et l'on perdrait la reprise par étape d'Argo et l'isolement de chaque
  outil dans son image. Le verbe sert le poste et la CI ; le cluster garde ses étapes.
- **Répartir par empreinte seulement, dans un seul Workflow** : c'est déjà ce que fait `withParam` ;
  un seul Workflow de 10 000 politiques reste un seul objet, une seule trace, un seul échec à
  rejouer en entier.
- **Partager le travail entre les pods par des artefacts Argo (S3) plutôt que par un volume
  `ReadWriteMany`** : il faudrait un dépôt d'artefacts et réécrire le passage de fichiers de toutes
  les étapes ; le volume garde le modèle actuel. À reprendre si le stockage `ReadWriteMany` manque
  là où `uske` sera déployé.
- **Découper en plusieurs `CronWorkflow`, chacun sur un sous-répertoire de politiques** : c'est
  déjà possible avec le paramètre `policies`, sans rien construire. Ce change ne le fait pas ; il
  le documente comme le levier suivant si un seul parent ne suffit pas.
- **Lancer `regis` et `knock` en bibliothèque Python** : `uske` les connaît par leur ligne de
  commande, et partager leur code lierait les trois versions.
- **Mettre git dans `uske screen`** : le support du journal n'est pas décidé (`DEBT-08`) ; un crochet
  après écriture laisse ce choix à qui lance la commande.
- **Fixer les plafonds dans la base** : aucune mesure n'existe encore ; le spike de volumétrie
  donnera les nombres.

## Conception

`design` est dû : changement transverse et motif d'architecture nouveau (`uske` lance ses
voisins ; un Workflow parent crée des Workflows enfants), et dépendance d'infrastructure nouvelle
(stockage `ReadWriteMany` hors du banc).

## Revue

`review` est due : un livrable face à un tiers, le verbe CLI `uske screen` et ses variables
d'environnement, qui exécutent des commandes nommées par l'opérateur.

## Objectif qualité

Le change sert **Opérabilité** (rang 3, section 1 de `docs/architecture/arc42.md`) : une politique
se rejoue seule, par son Workflow enfant, et un screening entier se lance d'un geste sur un poste.
Il arbitre contre **Minceur** (rang 4) : `uske` grossit d'un verbe qui lance ses voisins. Il ne
touche pas à **Sûreté** ni à **Contestabilité** : les mêmes décisions, dans le même ordre, avec le
journal écrit avant chaque placement. `uske screen` fond les étapes en un processus, ce que
l'Opérabilité *renonce à* : le cluster les garde séparées, et le verbe ne sert que hors du cluster.

## Capabilities

### New Capabilities

- `screen-command` : ce que garantit `uske screen` — un screening entier en une commande, dans
  l'ordre du workflow, le journal écrit avant tout placement, les outils appelés par leur ligne de
  commande, une sortie et des codes de retour qui distinguent l'issue métier de la panne.
- `screening-fan-out` : ce que garantit le workflow réparti — une politique par Workflow enfant,
  toutes jugées sur le même commit du dépôt et sous le même epoch, des plafonds posés par
  l'overlay, une panne isolée à sa politique et visible sur le screening.

### Modified Capabilities

- `rebuild-gate` : une exigence ajoutée, le renouvellement de l'ordre sur une opération marquée
  `remediated: true`. Les autres exigences, et celles de `decision-lookup`, ne changent pas ; ce
  change les fait tenir par deux enchaîneurs au lieu d'un.

## Impact

- Code : `uske/cli.py` (verbe `screen`), un module `uske/screen.py` qui enchaîne les fonctions
  existantes et lance les deux outils ; `uske/gate.py` (le renouvellement) ; tests sous `tests/`.
- Dépendance : un `knock` qui écrit `remediated` dans son plan (sa branche `main` actuelle) ; un
  `knock` plus ancien n'écrit pas la clé, et rien n'est renouvelé.
- Déploiement : `deploy/base/workflowtemplate.yaml` se scinde en un parent et un enfant
  (`uske-policy`) ; `deploy/base/cronworkflow.yaml` vise le parent ; un `Role` qui permet au compte
  `uske` de créer et lire des Workflows ; `deploy/kind` garde 1 et 1.
- Documentation : `README.md` (la règle « ne lance jamais », le verbe, les deux plafonds et le
  stockage), `docs/architecture/arc42.md` (*Solution Strategy*, *Deployment View*, `RISK-05`,
  `DEBT-07`), un ADR.
- Hors dépôt : `base-images/screen.sh` peut se réduire à des variables et à son crochet git ;
  ce change ne le modifie pas.

## Questions ouvertes

- Les nombres : combien de politiques et de jugements à la fois, et si un seul Workflow parent
  tient 10 000 enfants par screening sans saturer le contrôleur Argo. Le spike de volumétrie
  prévu le 2026-10-19 doit répondre ; le change livre les plafonds réglables, pas leurs valeurs.

---

Cadrage, passe 1 sur 5 (budget du cadrage), le 2026-10-17 : trois questions — comment
`uske screen` lance les outils, l'unité de répartition, le stockage —, posées en prose à la
session qui a ouvert ce change (`AskUserQuestion` n'atteignait pas la personne depuis ici).
Réponse reçue : les trois propositions par défaut, et le schéma `surdesrails`.

Ajout reçu le 2026-10-17 de la même session, hors passe : le renouvellement sur `remediated: true`
(D11 de la revue de `knock`), à porter comme exigence avec scénario.
