# Conception — workflow réutilisable de screening sur GitHub Actions

Sections arc42 touchées : **7 — Deployment View** (un second environnement d'exécution, le runner
GitHub, à côté du cluster Argo) ; **11 — Risks and Technical Debts** (`RISK-01` et `DEBT-08`
gagnent une ligne : la branche git comme support éprouvé à petite échelle). Les skills
`arc42-section-07`, `arc42-section-11` et `arc42-review` seront proposées au moment de
l'implémentation ; sans accord de la personne, les sections se rempliront à la main à partir du
gabarit.

## Context

`uske screen` (SDR-0021) conduit un screening entier hors du cluster. Il lance `regis` et `knock`
par leur nom, ou par le préfixe de `USKE_REGIS_CMD` / `USKE_KNOCK_CMD` : le préfixe est découpé par
`shlex.split`, sans shell (screen.py:47-50). `uske` ne connaît pas git. Quand une étape a écrit des
lignes au journal (`record`, `record-approve`, `record-applied`, `record-held`,
`record-promoted`), il lance `USKE_AFTER_RECORD` par `sh -c`, avec `USKE_POLICY` (le
`metadata.name`), `USKE_STEP` et `USKE_RESULTS` ; un échec du crochet arrête la politique avant le
placement qui suit. `--run` atteint les lignes de verdict et de placement (SDR-0018). Sans
`--work`, le travail se fait sous `/tmp/uske-…` (cli.py:351). Les rapports sont copiés sous
`reports/<nom>/<empreinte>/`, avant la ligne qui les cite (D5 d'origine). Le journal est
`<results>/<metadata.name>.jsonl`.

`regis` est publié sur `ghcr.io/trivoallan/regis` en deux variantes : `<version>` (slim, scanners
chargés au premier usage) et `<version>-full`. L'image tourne en uid 1001, avec
`HOME=/home/regis`, et lit `~/.docker/config.json`. `knock` est publié sur
`ghcr.io/trivoallan/knock` : uid 65532, `HOME=/tmp`. Il exige `KNOCK_REGISTRIES` et lance
`buildctl` sans `--addr`, qui suit donc `BUILDKIT_HOST`. `uske` est en 0.9.x.

ADR en vigueur qui contraignent : SDR-0016 (journal en ajout seul), SDR-0017 (socle commun ; un
workflow propre s'appelle `extra-*.yml`, et `renovate.json5` fait partie du socle), SDR-0018
(`run`), SDR-0021 (`screen`, trois versions séparées), SDR-0022 (pages de `docs/` en anglais,
artefacts OpenSpec en français). Aucun n'est à réviser.

## Goals / Non-Goals

**Goals:**

- Un dépôt de politiques crible une politique en un job d'une dizaine de lignes.
- La reconstruction marche sur un runner hébergé, sans secret pour la démonstration GHCR.
- Le journal vit dans le dépôt appelant, sur une branche qui ne fait que croître.
- Le verbe est le même qu'en local, `uske screen` : aucune étape n'est recopiée.

**Non-Goals:**

- Planifier 10 000 politiques : `DEBT-07` reste ouvert, et Argo reste le candidat.
- Le contrôle de demande de fusion (`judge_only`), laissé au change suivant.
- Le runner auto-hébergé et le Harbor interne : la page how-to les documente comme un écart, sans
  les éprouver ici.
- Toute modification du code d'`uske`, ou d'un fichier du socle.

## Decisions

### D1 — Un workflow réutilisable, pas une action

Le workflow s'appelle `.github/workflows/extra-screen.yml` et se déclenche par `workflow_call`.
Seul un workflow déclare `concurrency:` et `permissions:` au niveau d'un job, et seul un workflow
enchaîne deux jobs dont le second attend le premier (D4). Une action composite laisserait ces trois
points à l'appelant. Le démon BuildKit, lui, n'est pas un argument : il est lancé par une étape
(D2), ce qu'une action ferait aussi. Alternatives écartées : l'action composite, et l'action
enveloppée dans le workflow (voir `proposal.md`). Une fois publié, le nom du fichier est une
interface : le renommer casse les appelants.

Entrées :

| Entrée | Défaut | Rôle |
| --- | --- | --- |
| `policy` | — (requise) | chemin de la politique dans le dépôt appelant |
| `registries` | — (requise) | `KNOCK_REGISTRIES` : JSON non secret, sans identifiants |
| `transit` | vide | nom, dans `registries`, du registre de transit ; sans lui, une source à réparer finit `inconclusive` (`uske/no-transit`) |
| `playbooks` | `playbooks` | répertoire des playbooks dans le dépôt appelant |
| `journal-branch` | `uske-journal` | branche où vit le journal |
| `report-retention-days` | `90` | durée de vie de l'artefact des rapports |
| `registry-username` | vide (l'acteur du run) | utilisateur du registre, avec le secret ci-dessous |
| secret `registry-token` | absent (`GITHUB_TOKEN`) | jeton du registre ; seul à atteindre le juge et le placeur |

Aucune entrée ne remplace une image : le trio est épinglé (D3). Les identifiants de registre ne
passent pas par les entrées : `docker login` les écrit dans `config.json` (D2).

### D2 — Deux conteneurs lancés par des préfixes composés, BuildKit lancé par une étape

```
job name     (ubuntu-latest)  -> output name = metadata.name de la politique
job screen   needs: name ; concurrency: uske-screen-<name>, cancel-in-progress: false
  steps:
    checkout politiques -> $GITHUB_WORKSPACE   (persist-credentials: false)
    journal             -> $GITHUB_WORKSPACE/results  (D4)
    uv tool install git+https://github.com/trivoallan/uske@v<version>  (D6)
    docker login ghcr.io (GITHUB_TOKEN) ; docker pull regis, knock, buildkit
    docker run -d --privileged -p 127.0.0.1:1234:1234 moby/buildkit:<BUILDKIT_VERSION>
               --addr tcp://0.0.0.0:1234
    étape "préfixes" (run:) écrit dans $GITHUB_ENV, chemins absolus déjà développés :
      W=$GITHUB_WORKSPACE  T=$RUNNER_TEMP/uske-work  U=$(id -u):$(id -g)  C=$HOME/.docker/config.json
      USKE_REGIS_CMD = docker run --rm --network host --user U -v W:W -v T:T -w W
                         -v C:/home/regis/.docker/config.json:ro  ghcr.io/trivoallan/regis:<REGIS_VERSION>-full
      USKE_KNOCK_CMD = docker run --rm --network host --user U -v W:W -v T:T -w W
                         -v C:/tmp/.docker/config.json:ro
                         -e KNOCK_REGISTRIES -e BUILDKIT_HOST=tcp://127.0.0.1:1234
                         ghcr.io/trivoallan/knock:<KNOCK_VERSION>
      USKE_AFTER_RECORD = $RUNNER_TEMP/after-record.sh   (D4)
    uske screen --policy "$POLICY" --results "$W/results" --work "$T"
                --playbooks "$PLAYBOOKS" [--transit "$TRANSIT"] --run "$RUN_URL"
    étape finale "journal" (if: always())                (D4)
    étape finale "rapports" (if: always())               (D5)
```

- **Le répertoire de travail est monté** (finding 1) : `--work` sous `$RUNNER_TEMP`, hors de
  `results/`, monté au même chemin dans les deux conteneurs. `knock` y écrit son plan, et `uske` l'y
  retrouve.
- **Les chemins sont développés avant `uske`** (finding 2) : une étape `run:` compose les deux
  préfixes et les écrit dans `$GITHUB_ENV`. Ni `env:` ni `shlex` ne développent `$PWD` ou `~`.
- **Les conteneurs tournent sous l'uid du runner** (finding 6), par `--user`. Ils écrivent alors
  dans les répertoires que crée `uske`, et le runner peut lire ce qu'ils écrivent.
- **`config.json` est monté au bon chemin pour chaque image** (finding 7). `knock` reçoit
  `KNOCK_REGISTRIES` par son nom seul (`-e KNOCK_REGISTRIES`) : la valeur reste dans
  l'environnement et ne passe jamais par la ligne de commande.
- **BuildKit est lancé par une étape** (finding 3) : un service GitHub n'accepte pas d'arguments.
  Le port est publié sur `127.0.0.1` seulement (finding 15).
- **`regis` tourne en variante `-full`** (finding 12). En slim, chaque `docker run --rm` recharge
  les scanners et la base grype, et l'on paie ce coût à chaque empreinte. Les trois images sont
  tirées une fois, avant le screening. La mesure de la tâche 1 confirme ce choix, ou ajoute un cache
  de la base grype monté depuis l'hôte.
  Mesure (regis 0.41.0, `docker run --rm`, linux/arm64 sous Docker Desktop, images déjà tirées,
  `alpine:3.22`, playbook `version`) : slim 167 s puis 217 s, `-full` 195 s puis 213 s.
  `-full` n'est pas plus lent que slim au second run : le choix `-full` est retenu.
  L'écart entre les deux variantes est dans le bruit : dans les deux, grype télécharge sa base à
  chaque run (de 160 à 210 s), car aucune image ne l'embarque. `-full` reste retenu, parce que slim
  charge aussi ses scanners au premier usage.
- **Une base grype par jour, partagée par les jugements du run** (mesure de la tâche 1). Le motif
  est celui de `docs/how-to/operate.md` (*Screen locally*) : un répertoire de l'hôte,
  `$RUNNER_TEMP/grype-db`, est gardé par `actions/cache` sous la clé `grype-db-<jour UTC>`. S'il
  est vide, une étape le remplit une fois par `grype db update` (le binaire de l'image de `regis`,
  `/usr/local/bin/grype`). Le préfixe de `regis` le monte sur `/grype-db`, avec
  `GRYPE_DB_CACHE_DIR=/grype-db`, `GRYPE_DB_AUTO_UPDATE=false`,
  `GRYPE_DB_MAX_ALLOWED_BUILT_AGE=48h` et `GRYPE_CHECK_FOR_APP_UPDATE=false`, comme dans le
  cluster. On télécharge ainsi au plus une fois par jour et par dépôt, au lieu d'une fois par
  empreinte.

### D3 — Un trio épinglé par version d'`uske`, suivi par Renovate sans toucher au socle

`extra-screen.yml` déclare en `env:` trois variables, chacune précédée d'un commentaire
`# renovate:` : `REGIS_VERSION`, `KNOCK_VERSION` et `BUILDKIT_VERSION`. Exemple :
`# renovate: datasource=docker depName=ghcr.io/trivoallan/regis`. C'est le motif que suit déjà
`RENOVATE_VERSION` (renovate.yml:17), par le preset actif `customManagers:githubActionsVersions` :
`renovate.json5` ne change pas, et le socle non plus. Les images sont désignées **par étiquette de
version, pas par digest** : le preset suit une version, et un digest dans une chaîne `docker run`
échappe au gestionnaire `github-actions` (finding 11). La variante `-full` est ajoutée au moment de
l'usage, si bien que la variable reste une version nue que Renovate sait comparer. Une étiquette
d'`uske` désigne ainsi trois versions éprouvées ensemble, sans lier les trois paquets (SDR-0021).

Ce que l'on perd : une étiquette d'image republiée sous le même numéro changerait le trio sans
bruit. `regis` et `knock` ne republient pas une version, et `config:best-practices` épingle déjà
par digest ce qu'il sait épingler. Le risque est accepté.

### D4 — Le journal sur une branche dédiée, poussé après chaque écriture et à la fin

- **Naissance de la branche** (finding 14). Une étape teste `git ls-remote --heads origin
  <journal-branch>`. Si la branche est absente, l'étape crée sous `results/` un dépôt sur une
  branche orpheline, qui ne contient qu'un `.gitignore` (`reports/`), et le pousse. Si elle existe,
  l'étape l'extrait sous `results/`. `uske` y lit le journal pour savoir ce qui reste dû.
- **Le crochet**, `after-record.sh`, est écrit dans un fichier par une étape. Il travaille par
  `git -C "$USKE_RESULTS"`, avec une identité posée (`user.name`, `user.email`). Il commite
  `"$USKE_POLICY.jsonl"` avec un message qui nomme le run et `USKE_STEP`, puis il pousse. Si le
  push est refusé, il fait `pull --rebase` et repousse, trois fois au plus ; au-delà, il échoue, et
  `uske` ne place rien de plus. Le push s'authentifie dans le crochet seul, par
  `http.extraheader`, depuis `GITHUB_TOKEN` : aucun jeton n'est écrit dans un `.git/config` monté
  dans les conteneurs (finding 15).
- **L'étape finale « journal »** (`if: always()`, finding 9) recommit et repousse le journal de la
  politique. Le crochet passe aussi après `record-applied`, c'est-à-dire après le placement. Si ce
  push-là échoue, la ligne `placed` ne vivrait plus que sur un runner éphémère : l'étape finale
  rattrape ce cas, et le job échoue si elle échoue à son tour.
- **Le verrou porte sur `metadata.name`, pas sur le chemin** (finding 8). Le job `name` lit la
  politique et sort son nom. Le job `screen` prend `concurrency: uske-screen-<name>` au niveau du
  job, ce qui évite aussi de bloquer un groupe du même nom chez l'appelant. Deux chemins qui
  désignent la même politique s'attendent donc. GitHub ne garde qu'un seul run en attente par
  groupe : un troisième run annule le deuxième, et le plus récent l'emporte (finding 13). Un run
  annulé avant de commencer ne place rien. Deux politiques de noms différents écrivent deux fichiers
  différents, si bien que leur rebase ne conflit pas.
- **Deux premiers runs simultanés** créent chacun une racine orpheline. Le push de naissance du
  second est refusé (ce n'est pas une avance rapide), et l'étape de naissance ne rejoue pas : le run
  échoue avant le screening, donc avant tout placement. Le relancer suffit, puisqu'il trouve alors
  la branche.

Un push fait avec `GITHUB_TOKEN` ne déclenche pas d'autre workflow : il n'y a donc pas de boucle.
Alternatives écartées : la branche par défaut (protégée), et un dépôt séparé (il faudrait un jeton
de plus).

### D5 — Les rapports dans une archive, attachée au run

Les rapports restent écrits par `uske` à l'endroit où il les écrit (le D5 d'origine ne change pas),
mais ils ne sont pas commités. L'étape finale « rapports » (`if: always()`) archive
`tar -C results -cf reports.tar reports`, puis téléverse l'archive comme artefact
`uske-reports-<name>`. Deux raisons à l'archive (finding 4) : les chemins contiennent
`sha256:…`, et `upload-artifact` refuse `:` ; un motif `results/reports/**` retirerait en plus le
préfixe `reports/`. Dans l'archive, chaque rapport garde exactement le chemin que cite sa ligne,
relatif à `results/`. La ligne porte aussi `run`, l'URL du run, qui mène à l'artefact.
Alternatives écartées : tout commiter dans git (le dépôt grossit à chaque jugement), et ne garder
que le Markdown (le comportement d'`uske` changerait).

### D6 — Étiquette mobile à la mineure tant qu'`uske` est en 0.x, et version écrite par Release Please

- Le workflow `extra-major-tag.yml`, déclenché sur `release: published`, déplace une étiquette
  mobile vers le commit de la version. En 0.x, une mineure peut casser (SemVer), donc l'étiquette
  mobile est `v0.9`, `v0.10`… ; à partir de 1.0, ce sera `v1`. `release.yml`, qui fait partie du
  socle, ne change pas.
- Le workflow appelé doit installer son propre `uske`. Or le contexte `github` d'un workflow
  réutilisable est celui de l'appelant. La version est donc **écrite dans `extra-screen.yml` par
  Release Please** (`extra-files`, marqueur `x-release-please-version`, dans
  `release-please-config.json`, qui n'est pas un fichier du socle), et le workflow installe
  `git+…@v<version>`. Cette voie évite `id-token: write` (finding 16).

### D7 — L'exemple appelant éprouve le workflow

Le workflow `extra-screen-example.yml` de ce dépôt appelle `extra-screen.yml` par son chemin local,
sur une politique d'exemple : source `docker.io/library/alpine`, cible
`ghcr.io/trivoallan/uske-example/…`, et un transit sur le même GHCR pour la reconstruction. Il se
lance à la demande (`workflow_dispatch`), et sur les PR du même dépôt qui touchent
`extra-screen.yml` : les PR venues d'un fork sont exclues, car leur `GITHUB_TOKEN` est en lecture
seule (finding 17). Par chemin local, `extra-screen.yml` installerait la dernière version publiée
d'`uske`, pas le code de la PR. Une entrée cachée, `uske-ref`, réservée au banc, fait donc
installer `uske` depuis `github.sha`. Il n'y a pas de test unitaire pour un workflow : le banc en
tient lieu.

## Risks / Trade-offs

- [Les artefacts expirent, au plus 90 jours sur un dépôt public] → La ligne du journal garde
  l'état, le playbook et la raison : le scénario de Contestabilité (« trois semaines, une minute »)
  tient sur la ligne seule. Au-delà, le rapport complet est perdu (question ouverte 1).
- [Le conteneur `buildkitd` est privilégié] → Ce n'est le cas que sur un runner hébergé et
  éphémère, avec un port publié sur `127.0.0.1`. La page how-to dit qu'un runner auto-hébergé
  partagé demande BuildKit sans root.
- [Le jeton écrit sur tout le dépôt appelant et sur ses paquets] → Le job déclare ses permissions au
  plus juste. `persist-credentials: false`, l'authentification git passe par le seul crochet, et
  aucune entrée n'est interpolée dans un script : les entrées passent par l'environnement.
- [Le jeton du registre atteint le juge et le placeur par `config.json`] → C'est voulu : le placeur
  pousse, et le juge lit l'image retenue dans le transit, privée sur GHCR. Mais sans le secret
  `registry-token`, ce jeton est `GITHUB_TOKEN`, qui porte aussi `contents: write` : un outil
  compromis pourrait écrire dans le dépôt appelant. Accepté pour la démonstration ; le guide
  demande un jeton de registre dédié, limité aux paquets, pour tout autre usage (revue de tâche des
  groupes 2-3, tranché par Tristan le 2026-10-17).
- [Une étiquette d'image est republiée sous le même numéro] → Le risque est accepté (D3).
- [Le nom `extra-screen.yml` et ses entrées deviennent une interface] → Retirer ou renommer une
  entrée est un changement cassant, noté dans le CHANGELOG.
- [La variante `-full` de `regis` est lourde à tirer] → Elle est tirée une fois par run. La mesure
  de la tâche 1 compare avec la variante slim plus un cache.
- [Deux premiers runs simultanés] → Le second échoue avant de placer quoi que ce soit, et une
  relance suffit (D4).

## Migration Plan

Il n'y a rien à migrer : ce sont des fichiers nouveaux, que personne n'appelle encore. Pour retirer
le workflow, le déprécier d'abord pendant une mineure, puisque supprimer `extra-screen.yml` casse
les appelants.

## Open Questions

1. Au-delà de la rétention des artefacts, faut-il garder une copie durable des rapports, au moins
   ceux des refus ? Les pistes sont une release GitHub, une branche `uske-reports`, ou rien.

Questions closes par la revue : l'utilisateur et le `HOME` des images (finding 7, D2), le besoin de
`registry.insecure` pour GHCR (non, il ne sert qu'avec `tls_verify: false`), et le commit d'`uske`
à installer (finding 16, D6).
