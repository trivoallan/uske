# Proposition — Un workflow réutilisable qui crible une politique depuis GitHub Actions

## Why

`uske screen` a été écrit pour qu'« un poste ou une CI juge sans recopier les étapes » (SDR-0021),
et la clé `run` attend déjà « l'URL du run GitHub Actions » (SDR-0018). Mais rien ne livre ce
screening hors du cluster : chaque dépôt de politiques qui veut cribler depuis GitHub doit
recomposer lui-même l'installation de `uske`, les images de `regis` et `knock`, un démon BuildKit,
le verrou par politique et l'écriture du journal dans git. C'est la dérive que SDR-0021 a fermée
pour `screen.sh`, rouverte d'un dépôt à l'autre. Maintenant, parce que le verbe et ses deux
crochets (`USKE_*_CMD`, `USKE_AFTER_RECORD`) existent : il ne manque que l'emballage.

## What Changes

- **Un workflow réutilisable** (`workflow_call`), `.github/workflows/extra-screen.yml`, publié par
  ce dépôt. Un dépôt de politiques l'appelle en un job :
  `uses: trivoallan/uske/.github/workflows/extra-screen.yml@<version>`, avec le chemin d'une
  politique et la liste de ses registres (`KNOCK_REGISTRIES`, sans identifiants). Le transit et le
  répertoire des playbooks sont des entrées facultatives. Il crible cette politique par
  `uske screen --policy`, reconstruction comprise.
- Le workflow porte ce qu'une action composite laisserait à l'appelant : le verrou `concurrency`
  par politique, au niveau du job, les permissions (`contents: write`, `packages: write`), et
  l'enchaînement de deux jobs (lire le nom de la politique, puis cribler).
- `regis` et `knock` tournent dans leurs images, **épinglées par version de `uske`** : une étiquette
  d'`uske` désigne un trio éprouvé ensemble. Les versions sont écrites dans des variables
  `*_VERSION` que suit le preset Renovate déjà actif, sans toucher au socle.
- **Le journal s'écrit dans git, sur une branche dédiée** (`uske-journal` par défaut), dans le dépôt
  des politiques, par `USKE_AFTER_RECORD` : un commit et un push après chaque écriture, rejoués sur
  rebase. L'historique de cette branche ne fait que croître.
- **Les rapports partent dans une archive attachée au run**, pas dans git. La ligne du journal porte `run`, l'URL
  du run, qui mène à l'artefact.
- Cible première : runner hébergé par GitHub, registre public. **Démonstration sans secret** :
  source Docker Hub, cible GHCR, `GITHUB_TOKEN` seul.
- **Versionnage** : les étiquettes de Release Please, plus une étiquette mobile que déplace un
  workflow `extra-*` à chaque version (voir `design.md`, D6).
- Aucun changement du code d'`uske`.

## Alternatives écartées

- **Ne rien faire, documenter un exemple à recopier** : chaque copie dérive, comme `screen.sh` a
  dérivé ; c'est le motif que SDR-0021 a écarté.
- **Action composite (`action.yml`)** : souple, mais l'appelant devrait déclarer lui-même le service
  le verrou par politique, les permissions et l'enchaînement des deux jobs — les choses qu'on se
  trompe à écrire. Réponse reçue en passe 3. (Le démon BuildKit n'est pas un argument : il se lance
  par une étape, dans un workflow comme dans une action ; revue, finding 3.)
- **Action composite enveloppée par le workflow** : deux fichiers à tenir pour une souplesse que
  personne n'a demandée.
- **GitHub Actions comme planificateur de production** (cron et matrice sur toutes les
  politiques) : la matrice plafonne à 256 jobs, les runners hébergés n'atteignent pas un Harbor
  interne, et N pushes concurrents rouvrent `DEBT-08`. Argo reste le candidat pour 10 000+
  politiques ; ce change ne tranche pas `DEBT-07`.
- **Contrôle de demande de fusion (juger sans placer)** : utile, et `judge_only` existe déjà dans
  `screen.py` ; écarté de ce change, il viendra après (passe 1).
- **Import seul, sans BuildKit** : une politique qui demande une reconstruction échouerait ; réponse
  reçue en passe 2, la reconstruction est dans le périmètre.
- **Journal sur la branche par défaut** : bloqué dès que `main` est protégée.
- **Rapports dans git** (tous, ou Markdown seul) : le dépôt grossit à chaque jugement, et le
  Markdown seul changerait le comportement d'`uske` (D5). Réponse reçue en passe 3.
- **Étiquettes exactes seules** : écarté au profit d'une étiquette mobile, convention des Actions.
- **Images épinglées par digest** : le gestionnaire `github-actions` de Renovate ne voit pas un
  digest dans une chaîne `docker run`, et le suivre demanderait de changer `renovate.json5`, fichier
  du socle, dans les trois dépôts. Réponse reçue le 2026-10-17 (revue, finding 11) : versions,
  sans toucher au socle.

## Conception

`design.md` est dû : dépendance externe nouvelle (GitHub Actions comme environnement d'exécution,
BuildKit en service, GHCR) et ambiguïtés techniques à lever avant le code (branche du journal,
réseau entre conteneurs, étiquette mobile en 0.x).

## Revue

`review.md` est due : livrable face à un tiers (un workflow que d'autres dépôts appellent, dont le
nom de fichier et les entrées deviennent une interface), et surface d'attaque touchée (un jeton en
écriture sur le dépôt et les paquets, un conteneur privilégié).

## Objectif qualité

Sert **Opérabilité** (rang 3) : un screening échoué se rejoue depuis l'interface de GitHub, une
politique seule. Sert **Contestabilité** (rang 2) : l'historique git de la branche du journal rend
vérifiable « aucune ligne modifiée » (`RISK-01`, à cette échelle). L'arbitre contre elle sur un
point : les rapports en artefact expirent (voir `design.md`, risques). Tient **Minceur** (rang 4) :
aucun code d'`uske` ne change.

## Capabilities

### New Capabilities

- `github-screening-workflow` : ce que garantit le workflow réutilisable à un dépôt de politiques —
  ses entrées, l'ordre journal puis push avant tout placement suivant, le verrou par politique, la
  branche du journal, les rapports en artefact, le trio d'images épinglé.

### Modified Capabilities

<!-- aucune : `uske screen` et ses crochets sont utilisés tels quels -->

## Impact

- Nouveaux fichiers : `.github/workflows/extra-screen.yml` (réutilisable),
  `.github/workflows/extra-major-tag.yml` (étiquette mobile),
  `.github/workflows/extra-screen-example.yml` et sa politique d'exemple (le banc), et une page
  `docs/how-to/` en anglais (SDR-0022).
- `release-please-config.json` : `extra-files` qui écrit la version d'`uske` dans
  `extra-screen.yml` (pas un fichier du socle).
- Renovate : rien à changer ; le preset `customManagers:githubActionsVersions` suit les variables
  `*_VERSION` du workflow.
- `docs/architecture/arc42.md` : vue de déploiement (section 7), un second environnement
  d'exécution ; `DEBT-08` mentionne la branche git comme support éprouvé à petite échelle.
- Socle : rien ; les workflows sont des `extra-*`, et ni `release.yml` ni `renovate.json5` ne
  changent.
- Dépôts appelants : un job, les permissions `contents: write`, `packages: write`, et une liste de
  registres ; des playbooks sous `playbooks/` ou l'entrée qui les désigne.

## Passes

Détection : `.nanopm/wiki/docs/product.md` présent, aucun SDR `proposed`, `arc42.md` présent —
rien à proposer.

- Cadrage, passe 1 sur 5 (exploration) : quel usage — action réutilisable, retenue.
- Cadrage, passe 2 sur 5 (exploration) : reconstruction incluse ; journal dans le dépôt des
  politiques ; runner hébergé et registre public d'abord.
- Cadrage, passe 3 sur 5 (`superpowers:brainstorming`) : workflow réutilisable ; branche dédiée ;
  rapports en artefact ; étiquettes de Release Please plus étiquette mobile.
- Cadrage, passe 4 sur 5 (après la revue) : suivi des images par version, sans toucher au socle
  (finding 11).

## Questions ouvertes

- Durée de rétention des artefacts : 90 jours au plus sur un dépôt public. Faut-il, au-delà, une
  copie durable des rapports refusés (voir `design.md`) ?
