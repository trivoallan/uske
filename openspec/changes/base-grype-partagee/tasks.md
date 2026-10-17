# Plan — base-grype-partagee

> Pour un agent : chaque tâche cite le scénario du delta `shared-vulnerability-db` qu'elle rend
> vert. Test d'abord, puis le manifeste, puis `make test`. `make lint` (ruff, kustomize, puis
> `argo lint --offline`) passe à chaque point de commit. Branche : `feat/base-grype-partagee`,
> depuis `main` à jour. Le groupe 1 (spike) passe avant tout manifeste : ses réponses peuvent
> changer les scripts des tâches 2.2 et 3.2. Les choix de la revue d'ingénierie du 2026-10-17 sont
> cités par leur numéro (D3 à D10) ; la distribution par le dépôt d'artefacts suit SDR-0021.

## Plan de documentation

La documentation d'uske est en anglais (SDR-0022) ; les artefacts du change restent en français.

| Chemin | Quadrant | Destinataire | Geste |
| --- | --- | --- | --- |
| `docs/how-to/operate.md` | guide | l'opératrice qui déploie, exploite le banc ou lance un screening en CI | modifiée : refreshing the vulnerability database (the `grype-db` CronWorkflow every 6 h, the two artifact keys, a manual refresh after a regis upgrade, `grype-db` as the first thing to check when the full regime goes *inconclusive* on `cve-critical`, the 48 h bound and its effect per regime) ; the bench (cron suspended, refill after a pause of more than 48 h) ; *Screen locally* (what the caller gives the regis container: a mounted grype cache, the four variables, a daily cache key in CI) |
| `docs/architecture/arc42.md` | explication | la mainteneuse et l'agent qui lit l'architecture | modifiée : *Deployment View*, *Infrastructure Level 1* (the `grype-db` WorkflowTemplate and CronWorkflow, the two keys in the artifact repository, in the diagram and the text) |
| `deploy/base/grype-db.yaml` (commentaire d'en-tête) | — | qui lit le manifeste | créée : what is distributed and why the imported database, why the regis image, the two keys |
| `TODOS.md` | — | la mainteneuse | modifiée pendant la revue (D10) : l'alerte avant 48 h |

`README.md` et `CLAUDE.md` ne sont pas touchés : le README renvoie déjà à `docs/how-to/operate.md`
pour *Screen locally*, et les commandes ne changent pas.

## ADR

- Relus au frontmatter : SDR-0001 à SDR-0011 et SDR-0016 à SDR-0022. SDR-0017 dépasse SDR-0006 et
  SDR-0010 ; SDR-0019 dépasse SDR-0008.
- Relus au corps : SDR-0021 (aucun volume partagé, pas de `ReadWriteMany` : il fait passer la base
  par le dépôt d'artefacts) ; SDR-0022 (la documentation en anglais) ; SDR-0003 (le change ne
  touche que `deploy/` et la doc, pas le code de `uske`) ; SDR-0017 (`make lint` et `make test`
  sont le contrat de CI que les tâches appellent).
- Créés : aucun. Distribuer une donnée par le dépôt d'artefacts applique SDR-0021 ; la règle « une
  base vérifiée toutes les 6 h, sans résultat au-delà de 48 h » est un comportement, tenu par la
  spec `shared-vulnerability-db`.

## 1. Spike : la base importée, emballée puis déballée, dans l'image regis

Dans l'image regis épinglée par `deploy/kind/kustomization.yaml`
(`ghcr.io/trivoallan/regis@sha256:7c09…`, 0.41.0-full, grype 0.112.0), notée `<image>`.

- [x] 1.1 Vérifier la liste publiée :
  `docker run --rm --entrypoint grype <image> db list -o json | jq '.[0] | {status, built, checksum}'`.
  Attendu : un objet `active` avec `built` et `checksum`. Le script de 2.2 s'appuie sur ces champs.
- [x] 1.2 Télécharger, valider et emballer, en chronométrant :
  `docker run --rm -v gdbs:/out -e GRYPE_DB_CACHE_DIR=/tmp/db -e GRYPE_CHECK_FOR_APP_UPDATE=false --entrypoint sh <image> -c 'grype db update && grype db status && cd /tmp/db && time python3 -c "import tarfile; t=tarfile.open(\"/out/current.tar.zst\", \"w:zst\"); t.add(\"6\"); t.close()"'`.
  Attendu : `Status: valid`, et une archive de l'ordre de 500 Mo dans le volume `gdbs`. Noter la
  durée et la taille.
- [x] 1.3 Déballer dans un conteneur neuf, puis scanner, en chronométrant :
  `docker run --rm -v gdbs:/in:ro -e GRYPE_DB_CACHE_DIR=/tmp/grype-db -e GRYPE_DB_AUTO_UPDATE=false -e GRYPE_DB_MAX_ALLOWED_BUILT_AGE=48h -e GRYPE_CHECK_FOR_APP_UPDATE=false --entrypoint sh <image> -c 'time python3 -c "import tarfile; tarfile.open(\"/in/current.tar.zst\", \"r:zst\").extractall(\"/tmp/grype-db\", filter=\"data\")" && time grype alpine:3.20 -o json | jq -c .descriptor.db.status'`.
  Attendu : `valid: true`, et `from` qui porte l'URL d'Anchore avec `checksum=sha256…` (finding 5).
  Sinon, appliquer le repli du finding 5 et le noter ici. Noter les deux durées.
- [x] 1.4 Vérifier le refus d'une base trop vieille et d'une base absente : relancer le scan de 1.3
  avec `GRYPE_DB_MAX_ALLOWED_BUILT_AGE=1s`, puis sans déballer. Attendu dans les deux cas : code
  de sortie non nul, et un message qui nomme la base. Noter ici le nom exact de chaque variable
  s'il diffère sur 0.112.0.
- [x] 1.5 Consigner les réponses de 1.1 à 1.4 dans *Open Questions* de `design.md`, et y trancher
  le finding 5 de `review.md`. Commit : `docs: consigner le spike de la base grype distribuée`.

## 2. Le rafraîchissement : WorkflowTemplate et CronWorkflow

- [x] 2.1 Test d'abord, dans `tests/test_grype_db.py` (`unittest`, même style que
  `tests/test_orchestrator.py`). Il charge `deploy/base/grype-db.yaml` avec `yaml.safe_load_all`
  et vérifie :
  - un `CronWorkflow` `grype-db` avec `concurrencyPolicy: Forbid`, `schedules: ["17 */6 * * *"]`
    (D6) et `workflowTemplateRef: grype-db` ;
  - un `WorkflowTemplate` `grype-db` avec `serviceAccountName: uske`, dont le conteneur a l'image
    `regis` ;
  - un artefact d'entrée `pointer` facultatif à la clé `grype-db/current.json`, et deux sorties
    facultatives, `grype-db/current.tar.zst` et `grype-db/current.json`, sans archivage Argo
    (`archive: {none: {}}`) ;
  - dans le script : `grype db list` avant tout téléchargement ; `grype db status` avant
    l'emballage ; l'emballage en `w:zst`.
  Scénarios : *Le rafraîchissement planifié distribue une nouvelle base*, *Aucune base nouvelle
  n'est publiée*, *Un téléchargement interrompu*. `make test` attendu : échec,
  `FileNotFoundError` sur `deploy/base/grype-db.yaml`.
- [x] 2.2 Créer `deploy/base/grype-db.yaml` avec le `WorkflowTemplate` `grype-db`
  (`serviceAccountName: uske`, la `retryStrategy` des étapes du screening) et le `CronWorkflow`
  `grype-db` (`schedules: ["17 */6 * * *"]`, `concurrencyPolicy: Forbid`,
  `workflowTemplateRef: grype-db`). Le conteneur, image `regis`, `command: [sh, -c]`, reçoit le
  pointeur en `/tmp/in/current.json` et écrit ses sorties sous `/tmp/out/`. Il exécute (champs de
  `grype db list` ajustés selon le spike 1.1) :
  ```sh
  set -eu
  export GRYPE_CHECK_FOR_APP_UPDATE=false GRYPE_DB_CACHE_DIR=/tmp/db
  mkdir -p /tmp/out
  grype db list -o json > /tmp/list.json
  rc=0
  python3 - <<'PY' || rc=$?
  import json, pathlib, sys
  latest = next(d for d in json.load(open("/tmp/list.json")) if d["status"] == "active")
  current = pathlib.Path("/tmp/in/current.json")
  if current.exists() and json.loads(current.read_text())["checksum"] == latest["checksum"]:
      print("no newer database"); sys.exit(10)
  pathlib.Path("/tmp/latest.json").write_text(json.dumps({k: latest[k] for k in ("built", "checksum")}))
  PY
  [ "$rc" -ne 10 ] || exit 0
  [ "$rc" -eq 0 ] || exit "$rc"
  grype db update
  grype db status
  cd /tmp/db
  python3 -c "import tarfile; t = tarfile.open('/tmp/out/current.tar.zst', 'w:zst'); t.add('6'); t.close()"
  mv /tmp/latest.json /tmp/out/current.json
  ```
  Le code 10 dit « rien de nouveau » et fait sortir en succès sans sortie. Un échec de `grype db update` ou de
  `grype db status` arrête le script avant toute sortie : Argo ne téverse rien, et les clés en
  place ne changent pas. Scénarios : *Le rafraîchissement planifié distribue une nouvelle base*,
  *Aucune base nouvelle n'est publiée*, *Un téléchargement interrompu*.
- [x] 2.3 Ajouter `- grype-db.yaml` aux `resources` de `deploy/base/kustomization.yaml`.
  `make test` attendu : `tests/test_grype_db.py` vert. `make lint` attendu : sortie 0.
- [x] 2.4 Commit : `feat: rafraîchir toutes les 6 h une base grype distribuée par les artefacts`.

## 3. Les évaluations jugent avec la base distribuée

- [x] 3.1 Test d'abord, dans `tests/test_grype_db.py` : le template `regis-analyze` de
  `deploy/base/workflowtemplate.yaml` reçoit un artefact d'entrée `grype-db` facultatif à la clé
  `grype-db/current.tar.zst`, en `/grype/current.tar.zst (un `emptyDir` monté en /grype)`, sans archivage Argo ; son script
  déballe l'archive (`r:zst`, `filter="data"`) et la supprime avant `regis analyze` ; il ne monte
  aucun volume de plus (SDR-0021) ; son environnement contient `GRYPE_DB_CACHE_DIR=/grype/db`,
  `GRYPE_DB_AUTO_UPDATE=false`, `GRYPE_DB_MAX_ALLOWED_BUILT_AGE=48h` et
  `GRYPE_CHECK_FOR_APP_UPDATE=false` (D8). Scénarios : *Une évaluation ne télécharge pas de base*,
  *Deux évaluations entre deux rafraîchissements jugent avec la même base*, *Aucune base
  distribuée*. `make test` attendu : échec sur l'absence de l'artefact.
- [x] 3.2 Dans `deploy/base/workflowtemplate.yaml`, template `regis-analyze` : ajouter l'artefact
  d'entrée, faire précéder `regis analyze` du déballage de D4 (`design.md`), et ajouter un `env`
  avec les quatre variables, à côté de son `envFrom`.
- [x] 3.3 `make test` attendu : vert. `make lint` attendu : sortie 0.
- [x] 3.4 Commit : `feat: juger avec la base grype distribuée, sans appel à Anchore`.

## 4. Le banc kind et la documentation

- [ ] 4.1 Créer `deploy/kind/grype-db.yaml`, un `Workflow` (`generateName: grype-db-`,
  `workflowTemplateRef: grype-db`) sur le modèle de `deploy/kind/screening.yaml`. Dans
  `deploy/kind/kustomization.yaml`, suspendre le `CronWorkflow` `grype-db` par le même patch que
  le `CronWorkflow` `uske` (D9). Dans `deploy/kind/up.sh`, avant `echo "Ready. Start a screening:"`,
  lancer le remplissage et attendre ce Workflow-là, nommé :
  `wf=$(kubectl -n $NS create -f $HERE/grype-db.yaml -o name)` puis
  `kubectl -n $NS wait --for=jsonpath='{.status.phase}'=Succeeded "$wf" --timeout=15m`.
  Attendu sur un banc neuf : `condition met`. Un ancien Workflow en échec ne bloque pas l'attente.
- [ ] 4.2 Sur le banc, lancer un screening (`kubectl -n uske create -f deploy/kind/screening.yaml`),
  puis vérifier qu'un rapport porte la base distribuée :
  `jq '.results.cve.source.checksum' <rapport json d'une évaluation>`. Attendu : la somme de
  `grype-db/current.json`. Vérifier ensuite, dans le journal du pod `regis-analyze`, que le
  déballage et l'analyseur `cve` prennent ensemble bien moins que ~140 s. Scénario : *Deux
  évaluations entre deux rafraîchissements jugent avec la même base*.
- [ ] 4.3 Preuve de la chaîne du refus sur le banc (D3) : poser, le temps du test,
  `GRYPE_DB_MAX_ALLOWED_BUILT_AGE=1s` sur `regis-analyze`, puis lancer un screening avec une
  politique au régime complet et une au régime allégé (`deploy/kind/policies`). Attendu dans le
  journal : `inconclusive` avec la raison `cve-critical` pour la première ; pour la seconde, la
  décision donnée par les règles de secrets et de licences ; dans les deux rapports, une erreur
  dans `results.cve`. Retirer le réglage. Scénarios : *Une base de 50 h, régime complet*, *Une base
  de 50 h, régime allégé*.
- [ ] 4.4 Rédiger, en anglais, les lignes du *Plan de documentation* : `docs/how-to/operate.md`
  (rafraîchissement, rafraîchissement manuel après une montée de version de regis, `grype-db`
  comme première piste d'un *inconclusive* sur `cve-critical`, banc) et
  `docs/architecture/arc42.md` (*Deployment View*). Commit : `docs: décrire la base grype distribuée`.
- [ ] 4.5 Rédiger, en anglais, le contrat de l'appelant dans *Screen locally* de
  `docs/how-to/operate.md`. Exemple de `USKE_REGIS_CMD` qui monte `~/.cache/grype:/grype-db` et
  pose les quatre variables avec `GRYPE_DB_CACHE_DIR=/grype-db`, et clé de cache CI
  `grype-db-$(date -u +%F)`. Scénario : *La documentation décrit le contrat de l'appelant*.
  Commit : `docs: dire ce que uske screen attend de la base grype`.

## 5. Validation

- [ ] 5.1 `openspec validate base-grype-partagee --type change --strict`. Attendu :
  `Change 'base-grype-partagee' is valid`.
- [ ] 5.2 Vérifier le critère d'achèvement de `review.md` : le finding 5 est tranché (1.5), et
  les findings 3, 4 et 6 sont traités (4.4, `design.md` *Risks*, 4.5).
