# Review

## Grilles retenues

Trois grilles, choisies selon ce que le livrable fait à la personne qui l'utilise.

- **DevEx** — le livrable se consomme : un workflow que d'autres dépôts appellent, avec ses entrées,
  son étiquette mobile et la page how-to qui l'accompagne.
- **Ingénierie** — deux décisions coûtent cher : le nom de fichier `extra-screen.yml` et ses
  entrées deviennent une interface publique (D1), et le suivi des images touche un fichier du socle
  (finding 11). La surface d'attaque est elle aussi touchée : un jeton en écriture et un conteneur
  privilégié.
- **Contrôle** — le livrable porte des refus et des placements : une ligne perdue rend une décision
  invérifiable.

La grille Design ne s'applique pas : rien ici ne se regarde.

**Conduite.** Revue faite le 2026-10-17 sur `proposal.md`, `design.md` et le delta
`github-screening-workflow`. Un relecteur à contexte neuf a lu les trois fichiers et les a
confrontés au code d'`uske`, de `knock` et de `regis`. L'auteur a ensuite revérifié dans le code
les findings 1, 2, 5 et 6. Les skills `plan-eng-review` et `plan-devex-review` n'ont pas été
lancées : elles demandent l'aval de la personne, qui n'a pas été sollicité pour cet artefact.

**Ce que la revue a vérifié et ce qu'elle déduit.** Sont confirmés par le code : les options
d'`uske screen` (`--policy`, `--results`, `--run`, `--work`, `--playbooks`, `--transit`) ;
l'arrivée de `run` sur les lignes de verdict et de placement ; l'appel de `USKE_AFTER_RECORD`
seulement quand des lignes ont été écrites, son environnement, et l'arrêt qu'impose son échec ;
les codes de sortie ; le nom du journal ; le calcul de ce qui reste dû ; l'absence de verrou et de
`.pending-merge` dans `results/` ; `buildctl` lancé sans `--addr` ; l'inutilité de
`registry.insecure` pour GHCR ; l'exclusion des `extra-*` par `socle-drift`.
Sont **déduits, sans exécution** : l'absence de `command` pour un service GitHub, le refus de `:`
par `upload-artifact`, le rechargement des scanners de `regis` slim, la prise en compte de
`BUILDKIT_HOST` par `buildctl`, et le comportement du verrou de GitHub au-delà d'un run en attente.

## Findings et traitement

| # | Grille · dimension | Finding | Sévérité | Traitement |
| --- | --- | --- | --- | --- |
| 1 | Ingénierie · exactitude | Sans `--work`, `uske` travaille sous `/tmp/uske-…` (cli.py:351). Il passe pourtant à `knock` et à `regis` des chemins pris dans ce répertoire (plan, politique préparée, `-D`), alors que les conteneurs ne montent que `$PWD`. | Bloquante | D2 : `--work "$RUNNER_TEMP/uske-work"`, monté dans les deux conteneurs, hors de `results/`. |
| 2 | Ingénierie · exactitude | `USKE_*_CMD` est découpé par `shlex.split`, sans shell (screen.py:47-50), et `env:` ne développe rien : `$PWD` et `~` arrivent tels quels à `docker`. | Bloquante | D2 : une étape `run:` compose les préfixes en chemins absolus et les écrit dans `$GITHUB_ENV`. |
| 3 | Ingénierie · exactitude | Un service GitHub n'a pas de clé `command` : on ne peut pas lui passer `--addr tcp://0.0.0.0:1234`. L'argument « seul un workflow déclare `services:` » de D1 tombe ; D1 tient encore par `concurrency` et `permissions`. | Bloquante | D2 : BuildKit est lancé par une étape `docker run -d --privileged -p 127.0.0.1:1234:1234 … --addr tcp://0.0.0.0:1234`. Corriger la justification de D1 et l'alternative « action composite » dans `proposal.md`. |
| 4 | Contrôle · traçabilité | Les rapports sont rangés sous `reports/<nom>/sha256:…/`, et `upload-artifact` refuse `:`. De plus, la racine du motif `results/reports/**` retire le préfixe `reports/`. L'affirmation de D5, « le chemin vaut dans l'artefact », est donc fausse. | Bloquante | D5 : `tar -C results -cf reports.tar reports`, puis téléverser l'archive. Corriger D5 et le scénario « Un refus ». |
| 5 | Ingénierie · exactitude | `knock` exige `KNOCK_REGISTRIES` (knock/config.py:394-396), et `docker run` ne transmet pas l'environnement de l'hôte. | Bloquante | Nouvelle entrée `registries` (JSON non secret), passée par `-e KNOCK_REGISTRIES` ; les identifiants restent dans `config.json`. Spec et D1. |
| 6 | Ingénierie · exactitude | `knock` tourne en `65532` avec `HOME=/tmp` (knock/Dockerfile:45-46) : il ne peut pas écrire dans les répertoires que crée `uske` sous l'uid du runner. | Bloquante | `--user "$(id -u):$(id -g)"` sur les deux préfixes, composé dans l'étape du finding 2. |
| 7 | Ingénierie · exactitude | `/home/nonroot/.docker/config.json` n'est le bon chemin pour aucune des deux images : `regis` lit `/home/regis/.docker`, `knock` lit `/tmp/.docker`. | Majeure | D2 : un montage par image, au bon chemin. La question ouverte 2 est close. |
| 8 | Contrôle · intégrité du journal | Le verrou porte sur le chemin (`inputs.policy`), alors que le journal porte sur `metadata.name`. Deux chemins pour une même politique écrivent dans un seul fichier, et « le rebase ne conflit jamais » est faux. Un `/` est en outre interdit dans un nom d'artefact. | Majeure | Deux jobs : le premier sort `metadata.name`, le second prend `concurrency: uske-screen-<nom>` au niveau du job et nomme l'artefact. D4 et spec. |
| 9 | Contrôle · durabilité | Le crochet passe aussi après `record-applied`, c'est-à-dire après le placement (screen.py:259). Si ce push échoue, la ligne `placed` ne vit plus que sur un runner éphémère. Le crochet passe jusqu'à 5 fois par politique. | Majeure | Une étape finale `if: always()` recommit et repousse le journal. D4 et une exigence de la spec. |
| 10 | DevEx · entrées | Rien ne fournit les playbooks : `--playbooks` vaut `playbooks` par défaut (playbooks.py:8-18). Sans `--transit`, une source à réparer finit `inconclusive` (`uske/no-transit`), ce qui contredit le scénario « Une source à réparer ». | Majeure | Entrées `playbooks` (défaut `playbooks`) et `transit`. Le scénario exige un transit. |
| 11 | Ingénierie · socle | `renovate.json5` est un fichier du socle, ce qui contredit « Socle : rien ». Le preset actif ne suit pas un digest dans une chaîne `docker run`. | Majeure | Choisir entre deux voies : des variables `*_VERSION` avec `# renovate:` (par étiquette, ce qui amende D3), ou un changement de `renovate.json5` mené dans les trois dépôts. Corriger l'Impact. |
| 12 | DevEx · temps | `regis` slim recharge ses scanners et la base grype à chaque `docker run --rm`, donc à chaque empreinte. | Majeure | Épingler la variante `-full`, monter un cache de la base grype, et pré-tirer les images dans une étape. Mesurer avant de choisir. |
| 13 | DevEx · verrou | Avec `cancel-in-progress: false`, GitHub ne garde qu'un seul run en attente : un troisième run annule le deuxième. | Mineure | Le dire dans la spec (le plus récent l'emporte), et placer `concurrency` au niveau du job. |
| 14 | DevEx · branche du journal | `checkout` échoue sur une branche absente. Le crochet n'a ni `user.name` ni `user.email`, il doit utiliser `git -C "$USKE_RESULTS"`, et `USKE_STEP` n'est pas cité. Deux premiers runs simultanés créent deux racines orphelines. | Mineure | Une étape qui fait naître la branche. Le crochet écrit en fichier, avec identité et `-C`. Un test du double premier run sur l'exemple. |
| 15 | Ingénierie · surface d'attaque | `persist-credentials` laisse le jeton dans un `.git/config` monté dans `regis` et `knock`. `buildkitd` est publié sur `0.0.0.0`. Dans le scénario « Un chemin piégé », `uske` ne refuse rien : il échoue à charger la politique. | Mineure | `persist-credentials: false`, et un push authentifié dans le crochet seulement. Publier sur `127.0.0.1`. Récrire le scénario (« le job échoue, rien n'est placé »). |
| 16 | DevEx · versionnage | Question ouverte 4 : une version écrite par Release Please (`extra-files`, `x-release-please-version`) évite `id-token: write`. | Mineure | Retenir cette voie dans D2. Le banc D7 installe depuis `github.sha`. |
| 17 | DevEx · banc | Sur une PR venue d'un fork, `GITHUB_TOKEN` est en lecture seule, et le banc D7 échoue. | Mineure | Ne déclencher `pull_request` que pour les PR du même dépôt. |

## Critère d'achèvement

La revue est close quand :

- les findings 1 à 6 ont modifié `design.md` (D1, D2, D5), le delta `github-screening-workflow` et,
  pour le 3, `proposal.md` ;
- les findings 7, 8, 9 et 10 ont modifié D2, D4 et le delta, et le 9 y est une exigence avec son
  scénario ;
- le finding 11 est tranché par la personne, puis l'Impact de `proposal.md` est corrigé ;
- le finding 12 est une tâche de mesure en tête du plan, avant le choix de la variante de `regis` ;
- les findings 13 à 17 sont corrigés dans le delta ou inscrits dans `tasks.md`.

## État du traitement (2026-10-17)

- **Appliqués aux artefacts** : findings 1 à 10 et 13 à 16. Ils ont modifié `design.md` (D1, D2,
  D4 à D7), le delta `github-screening-workflow` (entrées, exigence du push final, verrou par
  `metadata.name`, archive des rapports, jeton hors des conteneurs) et `proposal.md`.
- **Finding 11** : tranché par la personne le 2026-10-17 (versions dans des variables `*_VERSION`,
  sans toucher au socle). D3 et l'Impact sont amendés.
- **Restent pour `tasks.md`** : la mesure de la variante de `regis` (finding 12), en tête du plan ;
  l'épreuve du double premier run sur le banc (finding 14) ; le déclencheur du banc réservé aux PR
  du même dépôt (finding 17).
