# Proposition — le banc local sait monter un vrai Harbor, sans cesser d'être léger par défaut

## Why

Harbor est le registre cible de l'employeur, et le banc local monte **Zot** à sa place. Zot sert le
protocole de registre, ce qui suffit à `regis` et à `knock` ; il n'implémente pas l'API v2.0 de
Harbor, à laquelle `census` est le seul à parler. Cette sous-commande n'a donc jamais tourné contre
autre chose qu'un `FakeHarbor`. C'est le seul endroit où le banc ment sur ce qu'il éprouve.

**Objectif qualité.** Ce change sert l'**opérabilité** (rang 3 de `docs/architecture/arc42.md`,
§1) : un banc qui éprouve ce qui tournera, plutôt qu'une approximation. Il ne sert pas la sûreté —
rien de ce qui juge ou place ne change — et il n'arbitre aucun conflit.

## Détection

- `.nanopm/wiki/docs/product.md` est présent : rien à proposer.
- `docs/adr/SDR-0013-frontend.md` est en `status: proposed`. Son verdict est **déjà pris en charge**
  par le change `demenagement-gitlab-et-livraison`, dont la tâche 6.1 le statue `rejected`. Le
  proposer ici le ferait rendre deux fois ; la branche des verdicts n'est donc pas ouverte dans ce
  change, et ce n'est pas un refus.
- `docs/architecture/arc42.md` existe : rien à proposer.

## Passes de cadrage

Cadrage conduit par `superpowers:brainstorming` le 2026-09-20, en prose et à une question par
envoi, comme pour le change précédent — la borne du schéma n'est pas tenue telle qu'elle est
écrite. Compte réel : trois envois de question (ce que le banc doit prouver, jusqu'où va la
variante, où elle vit), puis trois envois de section de conception. La découverte n'a consommé
aucune passe.

## What Changes

- **Une variante du banc**, choisie par un argument positionnel comme les autres modes du script :
  `deploy/kind/up.sh harbor`, à côté de `up.sh dt` et `up.sh down`.
- **Harbor prend l'adresse de Zot.** Le chart expose un service dont le nom et le port se
  paramètrent : `expose.clusterIP.name: registry` et `httpsPort: 5000` font répondre Harbor là où
  Zot répondait. Les neuf politiques du banc, le certificat TLS et son SAN, `KNOCK_REGISTRIES`,
  `HARBOR_HOST`, l'amorçage par `crane`, `screening.yaml` et `attestations.sh` ne changent pas.
- **Sept projets créés par l'API**, dérivés des politiques du banc : `mirror` pour les sources,
  puis `hub`, `a-4711`, `a-5203`, `a-6100`, `a-7300`, `shared-test`. Créés **publics**, pour que
  `attestations.sh` continue de tirer l'image sans identifiants.
- **Trois identités** : `admin`, qui ne sort pas du script de montage ; `robot$uske-read`, en
  lecture, pour `census` et `regis` ; `robot$uske-knock`, en écriture sur les six projets de
  destination, pour `knock`. C'est la forme des trois secrets du staging, en plus petit.
- **Le secret `uske-harbor` gagne `HARBOR_URL`, `HARBOR_USER` et `HARBOR_PASSWORD`.** Sans eux,
  `census` échoue avant d'atteindre un registre (`uske/cli.py:195`) — c'est un défaut du banc
  actuel, indépendant de Harbor.
- **Le geste de confiance cosign propre à Zot est sauté** en mode Harbor : l'extension
  `/v2/_zot/ext/cosign` n'a pas d'équivalent.
- **Zot reste le défaut** : `deploy/kind/up.sh` sans argument ne change pas de comportement.

## Alternatives écartées

- **Remplacer Zot par Harbor** — écartée : le banc passerait d'un pod à six et de quelques secondes
  à quelques minutes, pour tout le monde et à chaque montage, alors qu'une seule sous-commande a
  besoin de l'API Harbor.
- **Une seconde surcouche complète `deploy/kind-harbor/`** — écartée : les deux bancs ne diffèrent
  que sur trois points, et tout le reste existerait en double, puis divergerait.
- **Un script d'appoint qui ajoute Harbor à un banc déjà debout** — écartée : le banc cesserait
  d'être reproductible d'une seule commande, et un état intermédiaire existerait.
- **Donner à Harbor sa propre adresse** (`harbor`, port 443) — écartée : il faudrait alors une
  seconde série de politiques, un second certificat et des secrets différents, pour ne gagner qu'un
  nom de service plus juste.
- **Créer les projets privés**, comme sur un Harbor réel — écartée : `attestations.sh` tire sans
  identifiants, et le banc sert à regarder. La séparation qui compte, le droit d'écrire, reste
  entière.
- **Aller jusqu'au proxy-cache** — écartée : le staging l'éprouvera pour de vrai, et le simuler ici
  coûterait une configuration de plus à tenir sans lecteur.
- **Ne rien faire** — écartée : `census` resterait la seule sous-commande jamais exercée hors des
  fixtures, et l'écart sur `HARBOR_URL` resterait invisible jusqu'au premier essai réel.

## Conception

`design` est dû : dépendance externe nouvelle — un chart Helm et six composants — et ambiguïté que
des décisions techniques lèvent avant le code (l'adresse du service, la portée des robots, le
caractère public des projets).

## Revue

Revue : aucune, pas de `review.md`. Aucune décision ne porte le cran coûteux ou irréversible ; la
surface d'attaque touchée est celle d'un banc jetable, sur un cluster `kind` local, dont les mots
de passe sont fixes et écrits en clair dans le script comme l'est déjà celui de Dependency-Track ;
et rien ici n'est distribué à un tiers.

## Capabilities

### New Capabilities

- `local-bench`: ce que le banc local doit garantir — qu'il éprouve l'API du registre cible et non
  une approximation, qu'il reste léger et inchangé par défaut, que les droits d'écriture y soient
  séparés des droits de lecture, et qu'il reste jetable et reproductible d'une seule commande.

### Modified Capabilities

Aucune. Ni `repository-method` ni `versioned-delivery` ne décrivent le banc.

## Impact

- **Fichiers** : `deploy/kind/up.sh` (la variante et les secrets), `deploy/kind/kustomization.yaml`
  (retirer Zot du rendu en mode Harbor), `README.md` (la commande), et une valeur de chart épinglée
  — `harbor/harbor` 1.19.2, Harbor 2.15.2.
- **Code** : aucun changement dans `uske/*.py`. `census` est employé tel qu'il est ; c'est le secret
  du banc qui lui donnait tort.
- **Tests** : aucun test unitaire ajouté. `FakeHarbor` garde son rôle, qui est d'éprouver la
  logique sans réseau ; le banc est l'épreuve.
- **Dépendances** : le chart Harbor et son dépôt Helm, tirés au montage de la variante seulement.
- **Ordre** : ce change vient **après** `demenagement-gitlab-et-livraison`, qui renomme
  `orchestrator` en `uske` dans tout `deploy/`, `up.sh` compris. Les artefacts emploient déjà les
  noms d'après.
- **Feuille de route** : ce chantier n'y figure pas. Il se place après le passage à blanc (dû le
  2026-09-27) et le déménagement, ou à la place de quelque chose que quelqu'un décide de repousser.

## Questions ouvertes

- **Un robot Harbor de portée système peut-il énumérer les projets ?** `census` commence par
  `GET /projects`. Non vérifié contre un Harbor réel ; c'est la première tâche, et son repli est
  écrit d'avance : `admin` pour `census` dans le banc, dit en commentaire.
- **Faut-il, plus tard, un projet proxy-cache dans le banc ?** Écarté aujourd'hui ; à rouvrir si le
  staging montre que le motif casse quelque chose que le banc aurait pu révéler.
- **Branche** : ces artefacts sont rédigés sur `docs/wiki-produit`, pas sur `main`. Ils devront
  atteindre `main` avant toute implémentation.
