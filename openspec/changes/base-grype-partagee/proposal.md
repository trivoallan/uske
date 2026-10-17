# Proposition — une base de vulnérabilités grype rafraîchie hors des screenings, distribuée par le dépôt d'artefacts

## Why

Chaque pod `regis-analyze` démarre sans cache. À chaque évaluation, grype télécharge et décompresse
donc sa base de vulnérabilités : 141,7 s mesurées à froid (`grype db update`, 2026-10-17), soit
autant que toute la durée de l'analyseur `cve` relevée sur la même image (141 s). Une fois la base
en place, un scan prend 3 à 4 s (mesuré le 2026-10-17 sur `alpine:3.20`).
Le moment est venu parce que `screen-and-policy-fan-out` (#53) répartit désormais le screening en
un Workflow enfant par politique, pour plus de 10 000 politiques : chaque enfant paierait ces
~140 s par évaluation. Ce change en est une condition, pas la livraison de la fenêtre de 5 minutes.

## What Changes

- **Nouveau `CronWorkflow` `grype-db`**, toutes les 6 h, dans l'image regis. Il compare la base
  publiée par Anchore (`grype db list`) à celle déjà distribuée, et ne fait rien si elles sont
  identiques. Sinon, il la télécharge (`grype db update`), la valide (`grype db status`), l'emballe
  telle qu'importée en une archive tar zstd, et la dépose dans le dépôt d'artefacts du namespace
  sous une clé fixe, `grype-db/current.tar.zst`, avec un pointeur `grype-db/current.json`. Vérifier
  toutes les 6 h garde la base fraîche quelle que soit l'heure de publication d'Anchore (vers
  06:29 UTC le 2026-10-16).
- **Aucun volume partagé** (SDR-0021) : `regis-analyze` reçoit l'archive en artefact d'entrée
  facultatif, la décompresse dans son propre système de fichiers (13 s mesurées, 3,25 Go), puis
  lance regis avec `GRYPE_DB_CACHE_DIR` sur ce dossier, `GRYPE_DB_AUTO_UPDATE=false`,
  `GRYPE_DB_MAX_ALLOWED_BUILT_AGE=48h` et `GRYPE_CHECK_FOR_APP_UPDATE=false`. Les évaluations ne
  téléchargent plus rien depuis Anchore, et toute la flotte juge avec la même base entre deux
  rafraîchissements.
- **Une base de plus de 48 h ne fournit plus aucun résultat de vulnérabilités.** grype refuse de
  scanner. regis sort quand même en succès, avec une erreur dans le résultat `cve`, et la règle
  `cve-critical` reste *incomplete*. Dans le régime complet, où elle est critique, la décision est
  *inconclusive* (D-23), ce qui vaut refus (Sûreté). Dans le régime allégé, la CVE est informative
  (D-05), et la décision ne change pas. Il en va de même tant qu'aucune base n'a été distribuée.
- **Chemin local et CI** (`uske screen`, avec `USKE_REGIS_CMD`) : c'est l'appelant qui fournit la
  base. `uske` ne lance pas grype. La documentation de `uske screen` décrit ce que l'appelant
  fournit : un cache grype monté dans le conteneur regis, les quatre mêmes variables, et une clé de
  cache qui change chaque jour en CI.
- **regis ne change pas.** Son image porte Python 3.14, dont `tarfile` lit et écrit le zstd, et son
  rapport consigne déjà la base utilisée (`results.cve.source` : `built_at`, `checksum`). **Le
  journal ne change pas non plus.**

## Alternatives écartées

- **Ne rien faire** : ~140 s par évaluation, multipliées par la répartition en enfants.
- **Un volume `grype-db` partagé, monté en lecture seule par chaque `regis-analyze`** : première
  conception de ce change, écartée après #53. SDR-0021 (accepted) pose qu'aucun volume n'est
  partagé entre enfants et qu'il n'y aura pas de stockage `ReadWriteMany` ; un volume
  `ReadWriteOnce` épinglerait tous les enfants sur un nœud.
- **Distribuer l'archive d'Anchore telle quelle**, importée par chaque pod (`grype db import`) :
  écarté, l'import prend 65 s mesurées (hydratation de la base), contre 13 s pour décompresser la
  base déjà importée. La base importée pèse 531 Mo en zstd, contre 191 Mo pour l'archive d'Anchore.
- **Un cache par nœud, tenu par un DaemonSet et monté en `hostPath`** : écarté. C'est une pièce
  d'infrastructure de plus, et `hostPath` touche à la sécurité des pods.
- **Une base par screening**, téléchargée au début de chaque screening : écartée sur décision de
  fraîcheur ; la flotte veut une base commune entre deux rafraîchissements.
- **La base embarquée dans l'image regis**, reconstruite chaque nuit : demande un pipeline de build
  quotidien dans un dépôt tiers, et fixe la base par la version de regis.
- **Un miroir pour réseau fermé** : la prod a un accès sortant vers `grype.anchore.io`.
- **uske rafraîchit la base lui-même au début de `uske screen`** : c'est à l'appelant de fournir
  la base ; lancer grype ferait grossir `uske` (Minceur).
- **Consigner la base dans la ligne du journal** : le rapport la porte déjà.
- **Garder le seuil de grype (5 jours) ou n'en mettre aucun** : on veut 48 h.
- **Faire refuser par `uske` toute erreur `cve`, quel que soit le régime** (revue, D3) : contredit
  D-05 et ferait juger `uske`.
- **Un rafraîchissement par jour à 03:17 UTC** (revue, D6) : la base aurait déjà ~21 h, et un seul
  passage raté la ferait franchir les 48 h environ 3 h plus tard.
- **Couper la vérification par hachage au démarrage** (revue, D5) : mesurée sans coût visible
  (scan de 3 à 4 s avec ou sans), elle reste activée.
- **Laisser tourner le cron `grype-db` sur le banc kind** (revue, D9) : suspendu, sur le modèle du
  cron des screenings.

## Conception

`design` est dû : le change introduit un motif nouveau (une donnée distribuée par le dépôt
d'artefacts à tous les enfants), et la forme de cette distribution (quoi emballer, sous quelle clé,
comment la remplacer) se décide avant le code.

## Revue

`review` est due : le change touche une surface d'attaque. La base distribuée décide si une image
est saine. Le job qui l'écrit et les pods qui la lisent ont donc une frontière d'intégrité, et une
base altérée produirait de faux verdicts sains sur toute la flotte.

## Capabilities

### New Capabilities

- `shared-vulnerability-db` : la base de vulnérabilités que les évaluations lisent. Elle est
  rafraîchie hors des screenings (vérifiée toutes les 6 h, téléchargée une fois par base publiée),
  distribuée par le dépôt d'artefacts, jamais téléchargée depuis Anchore par une évaluation, et
  sans résultat au-delà de 48 h. Un rafraîchissement ne livre jamais une base partielle et, s'il
  rate, laisse la précédente en place.

### Modified Capabilities

- aucune.

## Impact

- `deploy/base` : un `WorkflowTemplate` et un `CronWorkflow` `grype-db` nouveaux ; `regis-analyze`
  dans `workflowtemplate.yaml` (artefact d'entrée, décompression, environnement) ;
  `kustomization.yaml`.
- `deploy/kind` : le cron `grype-db` y est suspendu, comme celui des screenings. `up.sh` fait un
  premier remplissage, qui se relance à la main après une pause du banc de plus de 48 h.
- Dépôt d'artefacts : deux clés de plus, `grype-db/current.tar.zst` (~531 Mo) et
  `grype-db/current.json`, remplacées à chaque nouvelle base.
- Stockage éphémère de chaque pod `regis-analyze` : ~3,8 Go (archive puis base décompressée).
- Dépendance externe : `grype.anchore.io` n'est plus sollicité que par le rafraîchissement.
- Documentation, en anglais (SDR-0022) : `docs/how-to/operate.md`, `docs/architecture/arc42.md`.
- Aucun changement dans regis ni dans knock.

Objectif qualité : le change arbitre entre **Sûreté** (rang 1) et une vitesse que l'**Opérabilité**
(rang 3) accepte de sacrifier. Il sert la Sûreté : dans le régime complet, une base périmée ou
absente fait refuser au lieu de laisser juger ; entre deux rafraîchissements, toutes les décisions
portent sur une même base connue. Le régime allégé reste ce que D-05 en fait.

## Cadrage

- Cadrage, passe 1 sur 5 (en exploration, avant la création du change) : la prod a un accès
  sortant vers `grype.anchore.io` ; une base commune à la flotte ; change rangé dans
  `uske/openspec`.
- Cadrage, passe 2 sur 5 : mode d'accès du stockage de prod, *je ne sais pas* ; les deux chemins,
  Argo et `uske screen`, sont dans le périmètre ; un seuil d'âge plus court que celui de grype ;
  le journal ne change pas.
- Cadrage, passe 3 sur 5 : seuil de 48 h ; sur le chemin local et CI, c'est l'appelant qui fournit
  la base.
- Revue d'ingénierie du 2026-10-17 (`/plan-eng-review`, D3 à D10) : chaîne réelle du refus (D3) ;
  mesure du hachage au démarrage (D5) ; vérification toutes les 6 h (D6) ; vérification de version
  de grype coupée (D8) ; cron suspendu sur le banc (D9) ; alerte notée dans `TODOS.md` (D10).
  D4 (générations sur le volume) et D7 (taille du volume) tombent avec le volume.
- À l'application, le 2026-10-17 : #53, mergé entre-temps, rend le volume partagé contraire à
  SDR-0021 ; réponse reçue : distribuer la base par le dépôt d'artefacts. Mesures du jour :
  import de l'archive d'Anchore 65 s, décompression de la base importée 13 s, scan 3 à 4 s avec ou
  sans hachage au démarrage.

## Questions ouvertes

- **Les noms exacts des variables grype et le format de `grype db list -o json`** sont vérifiés
  sur grype 0.114.0. Ils restent à confirmer contre la version embarquée dans l'image regis
  (0.112.0) : c'est la tâche 1.
- **La somme de contrôle survit-elle à l'emballage ?** `grype db update` écrit la source et sa
  somme dans `import.json` ; la tâche 1 vérifie qu'un pod qui décompresse la base la retrouve dans
  `descriptor.db.status.from`.
