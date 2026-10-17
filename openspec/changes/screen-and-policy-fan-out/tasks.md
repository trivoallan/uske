# Plan — screen-and-policy-fan-out

> Pour un agent : chaque tâche cite le scénario du delta qu'elle rend vert. Test d'abord, puis le
> code, puis `uv run python -m pytest --no-cov <fichier>`. La suite complète (`make test`) et
> `make lint` passent à chaque point de commit. Branche : `feat/screen-and-policy-fan-out`,
> depuis `main` à jour.

## Plan de documentation

| Chemin | Quadrant | Destinataire | Geste |
| --- | --- | --- | --- |
| `README.md` | — | l'opératrice qui lance un screening hors du cluster, ou qui écrit un overlay | modifiée : la règle « ne lance jamais » réduite aux sous-commandes ; une section *Screen locally* (verbe, trois variables, montage au même chemin, crochet) ; les deux plafonds, le dépôt d'artefacts et `uske merge` (rejouer une fusion, relancer un enfant seul) ; un seul namespace par volume `uske-results` ; la forme nouvelle des chemins de rapport |
| `docs/architecture/arc42.md` | explication | la mainteneuse et l'agent qui lit l'architecture | modifiée : *Solution Strategy* (lignes « Enchaînement » et « Intégration ») ; *Building Block View*, bloc *Workflow* en parent et enfant, plus un bloc *Screen* ; *Deployment View* (deux templates, le `Role`, le dépôt d'artefacts, la fusion) ; *Architecture Decisions* (SDR-0021) ; *Risks* (`RISK-05` révisé, un `RISK-07` sur la charge du contrôleur) |
| `docs/adr/SDR-0021-screen-et-repartition.md` | référence | qui conteste le choix plus tard | créée (écrite avec ce plan, `proposed`) |
| `deploy/base/workflowtemplate.yaml` (commentaire d'en-tête) | — | qui lit le manifeste | modifiée : parent et enfant, les deux plafonds |

`CLAUDE.md` n'est pas touché : ses commandes ne changent pas.

## ADR

- Relus au frontmatter : SDR-0001 à SDR-0011, SDR-0016 à SDR-0019. Tous `accepted`, aucun
  `supersedes` : tous sont en vigueur.
- Relus au corps : SDR-0016 (le journal en ajout seul et le transit obligatoire, que `screen`
  doit tenir à l'identique) ; SDR-0018 (la clé `run`, que le parent fixe pour tous ses enfants) ;
  SDR-0003 (le cœur sans entrée-sortie : les lancements de processus restent dans `screen.py`, à la
  frontière).
- Créés : [`SDR-0021`](../../../docs/adr/SDR-0021-screen-et-repartition.md), `proposed`, qui
  attend son verdict avant l'archivage. Aucun ADR n'est dépassé.

## 1. Extraire les décisions des sous-commandes

- [x] 1.1 Dans `uske/cli.py`, déplacer le corps de décision de `cmd_classify` dans une fonction
  `classify_lines(playbook: Path | None, ref: str, digest: str, report: Path | None, report_link:
  str | None, regis_exit: int, source_ref: str, source_digest: str, track: str, epoch: str, run:
  str) -> list[dict]`, que `cmd_classify` appelle. La sortie JSON de `cmd_classify` reste
  identique : `uv run python -m pytest --no-cov tests/test_orchestrator.py` passe sans retouche.
- [x] 1.2 Même geste pour `cmd_record` (`record_lines(policy, results, lines, applied, promoted,
  run) -> tuple[int, list[str]]`) et `cmd_approve` (`approve_plan(...)` et
  `approve_staged(...)`, qui rendent le document approuvé et le décompte). Même vérification.
- [x] 1.3 Commit : `refactor(cli): séparer les décisions des sous-commandes de leurs arguments`.

## 2. Le verbe `uske screen`

- [x] 2.1 Créer `tests/fakes/regis` et `tests/fakes/knock`, deux scripts Python exécutables qui
  écrivent des fichiers figés tirés de `tests/fixtures/` selon leurs arguments (`analyze`,
  `reconcile --plan-out`, `reconcile --apply-plan … --staged-out --applied-out`, `promote`), et
  qui consignent chaque appel dans `$FAKE_CALLS`. Un `FAKE_FAIL=apply` fait sortir l'application en 1.
- [x] 2.2 Test de parité dans `tests/test_screen.py` (scénario *Les mêmes lignes que les étapes*),
  puis `uske/screen.py` : une fonction `screen_policy(policy, work, results, playbooks, transit,
  epoch, run, tools, after_record, judge_only) -> dict` qui suit l'ordre de `uske-policy`. Chaque
  bloc porte en commentaire le nom de l'étape du template qu'il suit (`# prepare`, `# plan`, …).
  Attendu : `uv run python -m pytest --no-cov tests/test_screen.py -k parity` rend `1 passed`.
- [x] 2.3 `Tools` dans `uske/screen.py` : un préfixe par outil (`shlex.split` de `USKE_REGIS_CMD`
  et `USKE_KNOCK_CMD`, ou le nom seul), vérifié par `shutil.which` avant toute étape. Un outil qui
  sort en erreur écrit sur la sortie d'erreur la commande complète et son code. Tests : *Un préfixe
  docker*, *Le placeur manque*.
- [x] 2.4 Le crochet `USKE_AFTER_RECORD` (`sh -c`, avec `USKE_POLICY` et `USKE_RESULTS` dans
  l'environnement), lancé après toute écriture d'au moins une ligne. Tests : *Commiter le journal
  avant de placer*, *Le crochet échoue*, et une politique nommée `a;touch pwned` dont le crochet
  `true` ne crée aucun fichier `pwned`.
- [x] 2.5 Copie des rapports et chemin relatif (scénario *Un rapport cité par un chemin relatif*),
  `--judge-only` (*Une demande de fusion*), régime inconnu (*Un régime inconnu*), source à réparer
  (*Une source à réparer*), journal en lecture seule (*Le journal ne peut pas être écrit*).
- [x] 2.6 Le verbe dans `parser()` de `uske/cli.py` : `screen` avec `--policies` ou `--policy`
  (exclusifs, l'un requis), `--playbooks`, `--results`, `--work`, `--transit`, `--epoch`, `--run`
  et `--judge-only`. Une ligne JSON par politique, et le code de retour de D6. L'épilogue de
  `--help` nomme les trois variables, avec un exemple chacune. Tests : *Une quarantaine*, *Une
  politique casse, la suivante passe*, *Une copie saine*.
- [x] 2.7 `make test` : la couverture de branches reste ≥ 90 %, `uske/screen.py` compris.
- [x] 2.8 Commit : `feat(cli): conduire un screening entier en une commande locale`.

## 3. Renouveler l'ordre sur un tag réparé

- [x] 3.1 Dans `tests/test_orchestrator.py`, les quatre scénarios de
  `specs/rebuild-gate/spec.md` (*Un correctif amont sur un tag réparé*, *Un tag réparé, sans
  transit*, *Un tag jamais réparé*, *Un tag réparé dont la nouvelle source est refusée*), sur des
  plans en fixture qui portent ou non `"remediated": true`. Puis, dans `_decide` de
  `uske/gate.py`, la branche D11 avant le `return None` de `direct-placement`. Attendu :
  `uv run python -m pytest --no-cov tests/test_orchestrator.py -k remediated` rend `4 passed`.
- [x] 3.2 Commit : `feat(gate): renouveler la réparation d'un tag qui en porte une`.

## 4. Le workflow réparti

- [x] 4.1 `uske merge` (D12) : dans `uske/cli.py`, le verbe `merge --results <dir> --from <dir>`.
  Pour chaque `<politique>.tgz` de `--from` (trié par nom) : nom vérifié DNS-1123, membres de
  l'archive refusés s'ils sortent de leur répertoire, lignes de `lines.jsonl` ajoutées par
  `results.append` au journal de la politique, rapports de `reports/` copiés sous
  `<results>/reports/` sans écraser. Sortie `{"<politique>": <écrites>}` ; un artefact illisible
  fait sortir en 1 après les autres. Un verbe `uske export --policy <f> --results <dir>
  --snapshot-lines <n> --out <f.tgz>` écrit l'archive (lignes au-delà des `n` premières, rapports
  qu'elles citent sous `<dir>/reports/`). Tests dans `tests/test_merge.py`, scénarios *Deux
  politiques, une fusion*, *Rejouer la fusion*, *Une ligne écrite à la main pendant le screening*,
  plus un nom `../x` et un membre d'archive `../../x` refusés.
- [x] 4.2 Commit : `feat(cli): verser au journal les lignes d'un screening réparti`.
- [x] 4.3 `deploy/base/workflowtemplate.yaml` : un second `WorkflowTemplate` `uske-policy`, avec
  les paramètres `repository`, `commit`, `name`, `path`, `playbooks`, `transit`, `epoch`, `run`,
  `snapshot-lines` et `merge` (défaut `true`), son propre `checkout` au commit (D7), `{{workflow.name}}`
  remplacé par `run`, le mutex `policy-{{workflow.parameters.name}}`, `parallelism: 1`,
  `ttlStrategy.secondsAfterCompletion: 86400`, `podGC.strategy: OnPodSuccess`, et aucun volume
  persistant : chaque template reçoit et rend l'artefact `work` (`/work`), les sous-commandes
  lisent `--results /work/results`, `evaluate` rend sa ligne et son rapport à clé fixe sous
  `runs/{{run}}/{{name}}/`, `record` reçoit le préfixe `lines/` comme répertoire, et chaque étape
  qui écrit des lignes rend l'artefact `lines` par `uske export` (D9). Une dernière étape `merge`,
  `when: merge == true`, mutex `uske-journal`, seule à monter `uske-results`.
- [x] 4.4 Le parent `uske-screening` : `checkout` qui sort `git rev-parse HEAD`, `list`,
  `snapshot` (archive des `*.jsonl` de `uske-results`, un compte de lignes par politique), l'étape
  `policy` en template `resource` (D7 : `setOwnerReference`, label `uske.io/policy`, conditions,
  `continueOn: failed`, `merge: "false"`), `merge` (D12, préfixe `runs/{{workflow.name}}/out/`,
  mutex `uske-journal`, après tous les enfants), puis `summary`, qui échoue en nommant les
  politiques en échec ou une fusion échouée ; `parallelism: 1`.
- [x] 4.5 `deploy/base/storage-and-access.yaml` : un `Role` `uske-children` (`workflows`, verbes
  `create`, `get`, `list`, `watch`, `patch`) et son `RoleBinding` au compte `uske`. Un test lit le
  rendu de `deploy/base` (scénario *Le rendu des manifestes*) : seul le template de fusion monte
  `uske-results`, aucun template de `uske-policy` ne déclare de volume persistant, les deux
  `parallelism` valent 1. Il est lancé par `make lint` après `argo lint`.
- [x] 4.6 `deploy/kind` : `up.sh` installe MinIO et le configmap `artifact-repositories` (D10) ;
  `kustomization.yaml` réécrit les patches par indice pour les deux templates (le `checkout` par
  copie `hostPath`, le CA et la clé de `knock` sur `knock`, `knock-once` et `regis-analyze` de
  l'enfant). Attendu : `kubectl kustomize deploy/kind > /tmp/uske.yaml && argo lint --offline
  /tmp/uske.yaml` réussit.
- [ ] 4.7 Sur le banc : `deploy/kind/up.sh`, puis `kubectl -n uske create -f
  deploy/kind/screening.yaml`, puis `argo -n uske wait @latest`. Attendu : un Workflow enfant par
  fichier de `deploy/kind/policies/` (`kubectl -n uske get wf -l uske.io/policy`), une fusion, et
  des lignes qui portent toutes le `run` du parent (scénarios *Trois politiques*, *Les lignes d'un
  screening se reconnaissent*, *Deux politiques, une fusion*).
- [x] 4.8 Commit : `feat(deploy): un Workflow enfant par politique, sans volume partagé`.

## 5. Documentation et clôture

- [x] 5.1 Écrire les pages du plan de documentation. Lancer la vérification des ADR et l'aligner
  sur `docs/adr/SDR-0021-screen-et-repartition.md` une fois son verdict reçu.
- [ ] 5.2 Relire `review.md` : chaque finding de sévérité haute a sa tâche cochée.
- [ ] 5.3 `openspec validate screen-and-policy-fan-out --type change --strict`. Attendu :
  `Change 'screen-and-policy-fan-out' is valid`.
- [ ] 5.4 Commit : `docs: dire le verbe screen et la répartition par politique`.
