# Plan — screen-and-policy-fan-out

> Pour un agent : chaque tâche cite le scénario du delta qu'elle rend vert. Test d'abord, puis le
> code, puis `uv run python -m pytest --no-cov <fichier>`. La suite complète (`make test`) et
> `make lint` passent à chaque point de commit. Branche : `feat/screen-and-policy-fan-out`,
> depuis `main` à jour.

## Plan de documentation

| Chemin | Quadrant | Destinataire | Geste |
| --- | --- | --- | --- |
| `README.md` | — | l'opératrice qui lance un screening hors du cluster, ou qui écrit un overlay | modifiée : la règle « ne lance jamais » réduite aux sous-commandes ; une section *Screen locally* (verbe, trois variables, montage au même chemin, crochet) ; les deux plafonds et le stockage `ReadWriteMany` ; un seul namespace par volume `uske-results` ; la forme nouvelle des chemins de rapport |
| `docs/architecture/arc42.md` | explication | la mainteneuse et l'agent qui lit l'architecture | modifiée : *Solution Strategy* (lignes « Enchaînement » et « Intégration ») ; *Building Block View*, bloc *Workflow* en parent et enfant, plus un bloc *Screen* ; *Deployment View* (deux templates, le `Role`, le stockage) ; *Architecture Decisions* (SDR-0021) ; *Risks* (`RISK-05` révisé, un `RISK-07` sur la charge du contrôleur) |
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

- [ ] 3.1 Dans `tests/test_orchestrator.py`, les quatre scénarios de
  `specs/rebuild-gate/spec.md` (*Un correctif amont sur un tag réparé*, *Un tag réparé, sans
  transit*, *Un tag jamais réparé*, *Un tag réparé dont la nouvelle source est refusée*), sur des
  plans en fixture qui portent ou non `"remediated": true`. Puis, dans `_decide` de
  `uske/gate.py`, la branche D11 avant le `return None` de `direct-placement`. Attendu :
  `uv run python -m pytest --no-cov tests/test_orchestrator.py -k remediated` rend `4 passed`.
- [ ] 3.2 Commit : `feat(gate): renouveler la réparation d'un tag qui en porte une`.

## 4. Le workflow réparti

- [ ] 4.1 `deploy/base/workflowtemplate.yaml` : renommer le template de politique en un second
  `WorkflowTemplate` `uske-policy`, avec les paramètres `repository`, `commit`, `name`, `path`,
  `playbooks`, `transit`, `epoch` et `run`, son propre `checkout` au commit (D7), `{{workflow.name}}`
  remplacé par le paramètre `run`, le mutex `policy-{{workflow.parameters.name}}` et
  `parallelism: 1`. Chaque occurrence de `--run "{{workflow.name}}"` et de
  `{{workflow.name}}.html` passe par `run`.
- [ ] 4.2 Le parent `uske-screening` : `checkout` qui sort `git rev-parse HEAD`, `list`, l'étape
  `policy` en template `resource` (D7 : `setOwnerReference`, label `uske.io/policy`, conditions,
  `continueOn: failed`), puis `summary`, qui échoue en nommant les politiques en échec ;
  `parallelism: 1`. Sur l'enfant, `ttlStrategy.secondsAfterCompletion: 86400` et
  `podGC.strategy: OnPodSuccess`.
- [ ] 4.3 `deploy/base/storage-and-access.yaml` : un `Role` `uske-children` (`workflows`, verbes
  `create`, `get`, `list`, `watch`, `patch`) et son `RoleBinding` au compte `uske`.
- [ ] 4.4 `deploy/check-storage.py` (D9), plus `tests/test_check_storage.py` sur deux rendus en
  fixture : un rendu sain, et un rendu `parallelism: 20` avec `uske-results` en `ReadWriteOnce`
  (scénario *Un plafond relevé sans stockage partagé*). Attendu sur le second : code 1, et la sortie
  d'erreur nomme `uske-results`.
- [ ] 4.5 `Makefile`, cible `lint` : après `argo lint`, `uv run python deploy/check-storage.py
  "$$d/uske.yaml"`. Attendu : `make lint` passe sur `deploy/kind`.
- [ ] 4.6 `deploy/kind/kustomization.yaml` : réécrire les patches par indice pour les deux
  templates (le `checkout` du parent et de l'enfant par copie `hostPath`, le CA et la clé de
  `knock` sur `knock`, `knock-once` et `regis-analyze` de l'enfant). Attendu :
  `kubectl kustomize deploy/kind > /tmp/uske.yaml && argo lint --offline /tmp/uske.yaml` imprime
  `no linting errors found!`.
- [ ] 4.7 Sur le banc : `deploy/kind/up.sh`, puis `kubectl -n uske create -f
  deploy/kind/screening.yaml`, puis `argo -n uske wait @latest`. Attendu : un Workflow enfant par
  fichier de `deploy/kind/policies/` (`kubectl -n uske get wf -l uske.io/policy`), et des lignes
  qui portent toutes le `run` du parent (scénarios *Trois politiques* et *Les lignes d'un
  screening se reconnaissent*).
- [ ] 4.8 Commit : `feat(deploy): un Workflow enfant par politique, deux plafonds posés par l'overlay`.

## 5. Documentation et clôture

- [ ] 5.1 Écrire les pages du plan de documentation. Lancer la vérification des ADR et l'aligner
  sur `docs/adr/SDR-0021-screen-et-repartition.md` une fois son verdict reçu.
- [ ] 5.2 Relire `review.md` : chaque finding de sévérité haute a sa tâche cochée.
- [ ] 5.3 `openspec validate screen-and-policy-fan-out --type change --strict`. Attendu :
  `Change 'screen-and-policy-fan-out' is valid`.
- [ ] 5.4 Commit : `docs: dire le verbe screen et la répartition par politique`.
