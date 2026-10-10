# Plan — issue-transformation

> **Pour un agent exécutant** : ce plan s'exécute tâche par tâche. Les cases `- [ ]` suivent
> l'avancement. Chaque groupe finit par un point de commit.

**But** : qu'une source à réparer soit reconstruite dans un transit, que sa sortie soit jugée par
empreinte, et que `knock` ne promeuve que ce qui ressort en placement direct.

**Architecture** : trois demandes de fusion. Une dans `knock`, qui dit dans son plan ce qu'il
reconstruit. Ici, le Python et ses tests d'abord (groupes 3 à 7), sans effet tant que le workflow
ne nomme pas de transit. Puis le workflow, le banc et les écrits (groupes 8 à 10), après le
renommage de `deploy/` et après le premier screening réel.

**Outils** : Python 3.12, `unittest`, `uv`, Argo Workflows, `kustomize`, `argo lint`, `kind`,
BuildKit, `regis`, `knock`.

**Commande de test**, partout dans ce plan :

```bash
uv run --with pyyaml python -m unittest discover tests -t .
```

## Plan de documentation

| Chemin | Quadrant | Destinataire | Geste |
| --- | --- | --- | --- |
| `README.md` | — | Un visiteur du dépôt, et qui monte le banc | Modifiée — les étapes d'un screening, « seul le placement direct agit », la version minimale de `knock`, le geste qui rouvre une source |
| `docs/consommer-la-base.md` | Guide | Qui écrit une surcouche de déploiement dans un autre dépôt | Modifiée si elle existe à ce moment (elle naît dans `demenagement-gitlab-et-livraison`) — le paramètre `transit`, l'entrée de liste, les identités, l'adresse de BuildKit, les miroirs |
| `docs/architecture/arc42.md` | Explication | L'auteur, et les agents qui écrivent les changes | Modifiée — *Essential Features*, journal des décisions |
| `docs/adr/SDR-0016-journal-et-transit.md` | Référence | Qui doit savoir ce qui est décidé sans lire le code | Créée |
| `openspec/discovery.md` | — | Les agents qui proposent la prochaine story | Modifiée — story 4 cochée, note à la story 3 |

Hors périmètre, et nommé pour qu'il ne s'oublie pas : le dossier `docs` (D-32, DEBT-21, §5.2), qui
décrit encore un transit proposé. Il appartient à un autre dépôt.

## ADR

- **Relus au frontmatter** : les douze fichiers de `docs/adr/`, le 2026-10-10. Tous les
  `supersedes:` sont vides : aucun ADR n'en dépasse un autre. `SDR-0014` et `SDR-0015` sont
  réservés par le change `demenagement-gitlab-et-livraison`.
- **Relus au corps** : `SDR-0001` (un ADR `accepted` est gelé) ; `SDR-0002` (prose en français,
  code et commentaires en anglais — il décide de la langue de l'ADR à écrire et du code de ce
  plan) ; `SDR-0003` (hexagonal — ce plan ajoute aux modules plats existants, `DEBT-01` ne se
  referme pas ici) ; `SDR-0005` (validation aux frontières — le fichier des images retenues est lu
  à la main, comme le plan, `DEBT-02` ne se referme pas ici) ; `SDR-0007` (couverture — non
  mesurée, `DEBT-04`) ; `SDR-0009` (github-flow, `squash`, préfixe `feat`).
- **À créer** : `SDR-0016`, à la tâche 10.4. Deux décisions durables qui contraignent les changes
  suivants : le vocabulaire du journal (la clé `source`, la clé `rebuilt`, les raisons
  `uske/rebuild-refused` et `uske/reopened`), irréversible à la première ligne réelle ; et le
  transit obligatoire dès que le workflow nomme une seconde porte.

## 1. Établir les faits avant d'écrire

Aucune de ces tâches n'écrit de code. Chacune note son résultat dans la description de la demande
de fusion du groupe 9.

- [ ] 1.1 Mesurer les candidates du banc avec le playbook complet. Pour chacune de
  `alpine:3.18.0`, `redis:7.2.0`, `redis:7.4-bookworm`, `debian:bookworm-20230904-slim` :

  ```bash
  regis analyze docker.io/library/<image> \
    --playbook tests/fixtures/repo/playbooks/version/playbook.yaml -D /tmp/mesure/<image> -o "report.{format}"
  jq -r '.playbooks[0] | .tier, (.rules[] | select(.passed == false) | .slug)' /tmp/mesure/<image>/report.json
  ```

  Attendu : un tier et la liste des règles en échec par image. Il faut **une** image en
  « Transformation requise puis placement » dont les seules règles en échec sont `cve-critical`
  ou `freshness`, et **une** dont `no-root` échoue. La liste de licences n'a plus la famille GPL
  depuis `trivoallan/uske#8` : vérifier que cette PR est fusionnée avant de mesurer.
- [ ] 1.2 Si aucune image ne satisfait le premier cas : arrêter et revenir à la personne. Le
  repli écrit dans `review.md` (finding 7) est une image faite exprès, non `root`, trop ancienne,
  poussée par `up.sh` ; il change ce que le banc prouve, et ce n'est pas à ce plan de le décider.
- [ ] 1.3 Relever la version de `knock` qui contient sa PR #310 et le champ `transformed`, et son
  empreinte :

  ```bash
  gh release list --repo trivoallan/knock --limit 3
  crane digest ghcr.io/trivoallan/knock:<version>
  ```

  Attendu : une version postérieure à `0.12.0` et une empreinte `sha256:…`. Si elle n'existe
  pas, les groupes 8 et 9 attendent ; les groupes 3 à 7 non.
- [ ] 1.4 Confirmer comment `knock` trouve BuildKit :

  ```bash
  grep -rn "BUILDKIT_HOST\|--addr" ../knock/knock/adapters/buildkit_cli.py ../knock/deploy/base
  ```

  Attendu : soit `BUILDKIT_HOST` lu par `buildctl`, soit une option. La tâche 9.2 emploie ce qui
  est trouvé.
- [ ] 1.5 Confirmer que la branche de renommage de `demenagement-gitlab-et-livraison` est
  fusionnée : `grep -rn "orchestrator" deploy/ uske/ | wc -l` doit rendre `0`. Sinon, les groupes
  8 et 9 attendent, et la raison `uske/unknown-track` citée en 6.1 s'écrit encore
  `orchestrator/unknown-track` : ne pas la toucher.

## 2. Dans `knock` : dire ce qu'il reconstruit — première demande de fusion, autre dépôt

Ce groupe vit dans le dépôt `knock`, avec son propre change OpenSpec et ses propres règles
(couverture par fichier, `ruff`, `mypy`). Il est listé ici parce que tout le reste en dépend.

- [ ] 2.1 Ouvrir dans `knock` un change `plan-says-transformed` : `PlannedOperation`
  (`knock/domain/gate.py`) gagne `transformed: bool = False`, **hors** de `key()`.
- [ ] 2.2 `reconcile_registry.py` le renseigne à l'écriture du plan, avec la même expression que
  `_held` : `bool(w.vplan.transform)`.
- [ ] 2.3 Régénérer le schéma publié et l'exemple : `make reference`. Attendu :
  `docs/reference/schemas/reconcile-plan.schema.json` et `docs/examples/gate/plan.json` portent
  `transformed`.
- [ ] 2.4 Vérifier : `uv run pytest && uv run ruff check . && uv run mypy knock`. Attendu : tout
  passe, couverture tenue.
- [ ] 2.5 Fusionner, puis publier une version. Reprendre la tâche 1.3.

## 3. Le journal : deux clés et un compte

**Fichiers** : `uske/results.py`, `tests/test_orchestrator.py`.

- [x] 3.1 Écrire le test qui échoue. Dans `tests/test_orchestrator.py`, ajouter l'import
  `from uske import cli, outcomes, results` (remplace `from uske import cli, outcomes`), les
  constantes après `D3` :

  ```python
  S1 = "sha256:" + "a" * 64  # held-image digests
  S2 = "sha256:" + "b" * 64
  S3 = "sha256:" + "c" * 64
  ```

  et la classe, avant `class NothingHardcoded` :

  ```python
  class Attempts(unittest.TestCase):
      def test_counts_held_images_since_the_last_line_on_the_source(self):
          held = lambda digest: {"digest": digest, "state": "inconclusive", "source": D1}
          own = {"digest": D1, "state": "transformation-required"}
          self.assertEqual(results.attempts([own, held(S1), held(S2)], D1), 2)
          self.assertEqual(results.attempts([own, held(S1), own, held(S2)], D1), 1)
          self.assertEqual(results.attempts([own, held(S1)], D2), 0)

      def test_a_line_carries_its_source_and_its_rebuild(self):
          line = results.ResultLine(ts="t", ref="r", digest=D1, state="quarantine", ruleset="x",
                                    source=D2, rebuilt=S1)
          self.assertEqual((line.to_dict()["source"], line.to_dict()["rebuilt"]), (D2, S1))
  ```
- [x] 3.2 Lancer la commande de test. Attendu : `AttributeError: module 'uske.results' has no
  attribute 'attempts'` et `TypeError: ... unexpected keyword argument 'source'`.
- [x] 3.3 Dans `uske/results.py`, ajouter deux champs à `ResultLine`, après `report` :

  ```python
      source: str | None = None  # on a held image's line: the source digest it was built from
      rebuilt: str | None = None  # on a closing line: the held image that was refused
  ```

  et la fonction, après `pending` :

  ```python
  def attempts(lines: list[dict], source: str) -> int:
      """Held images judged for `source` since the last line written on `source` itself."""
      count = 0
      for line in lines:
          if line["digest"] == source:
              count = 0
          elif line.get("source") == source:
              count += 1
      return count
  ```
- [x] 3.4 Lancer la commande de test. Attendu : `OK`.
- [x] 3.5 Commit : `git add uske/results.py tests/test_orchestrator.py && git commit -m "feat: le journal porte la source d'une image retenue et compte ses essais"`.

## 4. `approve` : une source à réparer, sous deux conditions

**Fichiers** : `uske/gate.py`, `uske/cli.py`, `tests/test_orchestrator.py`.

- [x] 4.1 Dans `tests/test_orchestrator.py`, donner au constructeur de plan un champ de plus.
  Remplacer la fonction `plan` par :

  ```python
  def plan(policy: str, ops: list[tuple[str, str]], kind: str = "import",
           transformed: bool | None = None) -> dict:
      """A ReconcilePlan as `knock reconcile --plan-out` writes it: (tag, source digest) per op."""
      extra = {} if transformed is None else {"transformed": transformed}
      return {"apiVersion": "knock.io/v1alpha1", "kind": "ReconcilePlan", "operations": [
          {"policy": policy, "kind": kind, "destination": "harbor.example/shared-test/app", "tag": tag,
           "source": "harbor.example/producer/app", "sourceTag": tag, "sourceDigest": digest, **extra}
          for tag, digest in ops]}
  ```
- [x] 4.2 `approve` va rendre une clé de plus. Dans `Screening.screening`, remplacer la dernière
  ligne `return calls, approved, applied` par :

  ```python
          return calls, {"approved": approved["approved"]}, applied
  ```
- [x] 4.3 Écrire le test qui échoue, avant `class NothingHardcoded` :

  ```python
  class Rebuild(Workdir):
      """The second gate: a source to repair is rebuilt, its output judged, then promoted or closed."""

      POLICY = str(FIXTURES / "standard.yaml")
      NAME = "fixture-standard"
      SOURCE = "harbor.example/producer/app:1.0"
      HELD = "harbor.example/transit/shared-test/app:1.0"
      REPAIR = report("Transformation requise puis placement")

      def record(self, name: str, lines) -> int:
          return run("record", "--policy", self.POLICY, "--results", str(self.results),
                     "--lines", self.write(name, lines))[1]["written"]

      def judge_source(self, digest: str, value) -> None:
          self.record(f"src-{digest[-4:]}.json", self.classify(FULL, self.SOURCE, digest, value))

      def approve(self, value: dict, *extra: str) -> tuple[dict, list[str]]:
          out = self.tmp / "approved.json"
          _, result = run("approve", "--policy", self.POLICY, "--plan", self.write("plan.json", value),
                          "--results", str(self.results), "--out", str(out), *extra)
          return result, [op["tag"] for op in json.loads(out.read_text())["operations"]]

      def journal(self) -> list[dict]:
          path = self.results / f"{self.NAME}.jsonl"
          return [json.loads(l) for l in path.read_text().splitlines()]

      def test_a_source_to_repair_needs_a_rebuild_and_a_transit(self):
          self.judge_source(D1, self.REPAIR)
          rebuilt = plan(self.NAME, [("1.0", D1)], transformed=True)
          self.assertEqual(self.approve(rebuilt, "--transit", "transit")[1], ["1.0"])
          self.assertEqual(self.approve(rebuilt), ({"approved": 0, "discarded": {"no-transit": 1}}, []))
          copied = plan(self.NAME, [("1.0", D1)], transformed=False)
          self.assertEqual(self.approve(copied, "--transit", "transit")[0]["discarded"], {"not-rebuilt": 1})
          silent = plan(self.NAME, [("1.0", D1)])
          self.assertEqual(self.approve(silent, "--transit", "transit")[0]["discarded"], {"not-rebuilt": 1})

      def test_a_sound_source_is_approved_rebuilt_or_not(self):
          self.judge_source(D1, report("Placement direct"))
          for transformed in (True, False, None):
              with self.subTest(transformed=transformed):
                  value = plan(self.NAME, [("1.0", D1)], transformed=transformed)
                  self.assertEqual(self.approve(value)[1], ["1.0"])
  ```
- [x] 4.4 Lancer la commande de test. Attendu : `error: unrecognized arguments: --transit` puis
  des échecs sur `discarded`.
- [x] 4.5 Dans `uske/gate.py`, remplacer l'import `from uske.results import last_states` par
  `from uske.results import attempts, last_states`, ajouter après les imports :

  ```python
  MAX_ATTEMPTS = 3  # held images judged for one source before the orchestrator stops rebuilding it
  REBUILD_REFUSED = "uske/rebuild-refused"
  ```

  et remplacer la fonction `approve` par :

  ```python
  def _discarded(op: dict, states: dict[str, str], lines: list[dict], transit: str | None) -> str | None:
      """Why an operation is withheld, or None when it is handed back to knock."""
      rebuilt = op.get("transformed") is True  # absent means a copy: knock did not say it rebuilds
      state = states.get(op["sourceDigest"])
      if state == Outcome.TRANSFORMATION_REQUIRED:
          if not transit:
              return "no-transit"  # without a second gate, the rebuilt output would be placed unjudged
          if not rebuilt:
              return "not-rebuilt"
      elif state != Outcome.DIRECT_PLACEMENT:
          return "refused"
      if rebuilt and attempts(lines, op["sourceDigest"]) >= MAX_ATTEMPTS:
          return "attempts-exhausted"
      return None


  def approve(plan: dict, policy: Policy, lines: list[dict], transit: str | None = None) -> tuple[dict, dict]:
      """(the plan minus every withheld operation, how many were withheld per cause)."""
      states = last_states(lines)
      kept, discarded = [], {}
      for op in operations(plan, policy):
          cause = _discarded(op, states, lines, transit)
          if cause is None:
              kept.append(op)
          else:
              discarded[cause] = discarded.get(cause, 0) + 1
      return {**plan, "operations": kept}, discarded
  ```
- [x] 4.6 Dans `uske/cli.py`, remplacer le corps de `cmd_approve` par :

  ```python
  def cmd_approve(args) -> None:
      policy = _policy(args.policy)
      lines = results.read(results.path_for(args.results, policy.name))
      approved, discarded = gate.approve(_read_json(args.plan), policy, lines, args.transit)
      out = Path(args.out)
      out.parent.mkdir(parents=True, exist_ok=True)
      out.write_text(json.dumps(approved, indent=2))
      _json({"approved": len(approved["operations"]), "discarded": discarded})
  ```

  et, dans `parser()`, sous le sous-analyseur `approve`, ajouter après la ligne `--out` :

  ```python
      s.add_argument("--transit", help="the registry rebuilds are held in; without it, no source to repair is approved")
  ```
- [x] 4.7 Lancer la commande de test. Attendu : `OK`.
- [x] 4.8 Commit : `git add uske/gate.py uske/cli.py tests/test_orchestrator.py && git commit -m "feat: approve rend une source à réparer quand knock la reconstruit et qu'un transit est nommé"`.

## 5. Les images retenues : dues, puis filtrées

**Fichiers** : `uske/gate.py`, `uske/cli.py`, `tests/test_orchestrator.py`.

- [x] 5.1 Dans `tests/test_orchestrator.py`, ajouter après la fonction `plan` :

  ```python
  def staged(policy: str, items: list[tuple[str, str, str]]) -> dict:
      """A StagedRebuilds as `knock reconcile --staged-out` writes it: (tag, source digest, held digest)."""
      return {"apiVersion": "knock.io/v1alpha1", "kind": "StagedRebuilds", "entries": [
          {"policy": policy, "import": "v1", "variant": "default", "kind": "import",
           "destination": "harbor.example/shared-test/app", "tag": tag,
           "source": "harbor.example/producer/app", "sourceTag": tag, "sourceDigest": source,
           "staged": "harbor.example/transit/shared-test/app", "stagedDigest": held, "aliases": []}
          for tag, source, held in items]}
  ```
- [x] 5.2 Écrire le test qui échoue, dans `class Rebuild` :

  ```python
      def pending_held(self, value: dict | None) -> list[dict]:
          path = self.write("staged.json", value) if value is not None else str(self.tmp / "absent.json")
          return run("pending", "--policy", self.POLICY, "--staged", path, "--results", str(self.results))[1]

      def approve_held(self, value: dict | None) -> tuple[dict, list[dict]]:
          path = self.write("staged.json", value) if value is not None else str(self.tmp / "absent.json")
          out = self.tmp / "staged.approved.json"
          _, result = run("approve", "--policy", self.POLICY, "--staged", path,
                          "--results", str(self.results), "--out", str(out))
          return result, json.loads(out.read_text())["entries"]

      def test_one_candidate_per_held_digest(self):
          value = staged(self.NAME, [("1.0", D1, S1), ("latest", D1, S1), ("1.1", D2, S2)])
          value["entries"].append({**value["entries"][0], "policy": "another-policy", "stagedDigest": S3})
          todo = self.pending_held(value)
          self.assertEqual([c["digest"] for c in todo], [S1, S2])
          self.assertEqual(todo[0]["target"], f"harbor.example/transit/shared-test/app@{S1}")
          self.assertEqual((todo[0]["source"], todo[0]["sourceRef"]), (D1, self.SOURCE))

      def test_no_staged_file_means_nothing_held(self):
          self.assertEqual(self.pending_held(None), [])
          self.assertEqual(self.approve_held(None), ({"approved": 0}, []))
  ```
- [x] 5.3 Lancer la commande de test. Attendu : `error: unrecognized arguments: --staged`.
- [x] 5.4 Dans `uske/gate.py`, ajouter à la fin :

  ```python
  def entries(staged: dict, policy: Policy) -> list[dict]:
      return [e for e in staged.get("entries") or [] if e.get("policy") == policy.name]


  def staged_candidates(staged: dict, policy: Policy) -> list[dict]:
      """One candidate per held digest: what knock built is judged where it is held."""
      seen: dict[str, dict] = {}
      for e in entries(staged, policy):
          seen.setdefault(e["stagedDigest"], {
              "ref": f"{e['staged']}:{e['tag']}", "digest": e["stagedDigest"],
              "source": e["sourceDigest"], "sourceRef": f"{e['source']}:{e['sourceTag']}"})
      return list(seen.values())


  def approve_staged(staged: dict, policy: Policy, lines: list[dict]) -> dict:
      """The held images minus every one that is not direct-placement. Kept entries are untouched."""
      states = last_states(lines)
      kept = [e for e in entries(staged, policy) if states.get(e["stagedDigest"]) == Outcome.DIRECT_PLACEMENT]
      return {**staged, "entries": kept}
  ```
- [x] 5.5 Dans `uske/cli.py`, ajouter après `_read_json` :

  ```python
  def _read_staged(path: str) -> dict:
      """knock's StagedRebuilds. No file: knock held nothing, or did not get that far."""
      return _read_json(path) if Path(path).exists() else {"entries": []}
  ```

  Remplacer le corps de `cmd_pending` par :

  ```python
  def cmd_pending(args) -> None:
      policy = _policy(args.policy)
      lines = results.read(results.path_for(args.results, policy.name))
      if args.staged:
          found = gate.staged_candidates(_read_staged(args.staged), policy)
      else:
          found = gate.candidates(_read_json(args.plan), policy)
      _json([_target(c) for c in results.pending(found, lines)])
  ```

  Remplacer le corps de `cmd_approve` par :

  ```python
  def cmd_approve(args) -> None:
      policy = _policy(args.policy)
      lines = results.read(results.path_for(args.results, policy.name))
      if args.staged:
          approved = gate.approve_staged(_read_staged(args.staged), policy, lines)
          count = {"approved": len(approved["entries"])}
      else:
          approved, discarded = gate.approve(_read_json(args.plan), policy, lines, args.transit)
          count = {"approved": len(approved["operations"]), "discarded": discarded}
      out = Path(args.out)
      out.parent.mkdir(parents=True, exist_ok=True)
      out.write_text(json.dumps(approved, indent=2))
      _json(count)
  ```

  Dans `parser()`, sous `pending`, remplacer la ligne `s.add_argument("--plan", required=True, …)`
  par :

  ```python
      source = s.add_mutually_exclusive_group(required=True)
      source.add_argument("--plan", help="knock's ReconcilePlan (reconcile --plan-out)")
      source.add_argument("--staged", help="knock's StagedRebuilds (reconcile --staged-out)")
  ```

  et sous `approve`, remplacer la ligne `s.add_argument("--plan", required=True)` par les trois
  mêmes lignes.
- [x] 5.6 Lancer la commande de test. Attendu : `OK`.
- [x] 5.7 Commit : `git add uske/gate.py uske/cli.py tests/test_orchestrator.py && git commit -m "feat: pending et approve lisent le fichier des images retenues"`.

## 6. `classify` : la ligne d'une image retenue, et la clôture de sa source

**Fichiers** : `uske/cli.py`, `tests/test_orchestrator.py`.

- [x] 6.1 Écrire le test qui échoue, dans `class Rebuild` :

  ```python
      def judge_held(self, source: str, held: str, value) -> list[dict]:
          path = self.write(f"held-{held[-4:]}.json", value)
          code, lines = run("classify", "--playbook", str(FULL), "--ref", self.HELD, "--digest", held,
                            "--report", path, "--source-ref", self.SOURCE, "--source-digest", source)
          self.assertEqual(code, 0)
          return lines

      def test_a_repaired_image_is_promoted_and_closes_nothing(self):
          self.judge_source(D1, self.REPAIR)
          lines = self.judge_held(D1, S1, report("Placement direct"))
          self.assertEqual([(l["digest"], l["state"], l["source"]) for l in lines],
                           [(S1, "direct-placement", D1)])
          self.record("held.json", lines)
          value = staged(self.NAME, [("1.0", D1, S1), ("1.1", D2, S2)])
          result, kept = self.approve_held(value)
          self.assertEqual(result, {"approved": 1})
          self.assertEqual(kept, [value["entries"][0]])  # handed back exactly as knock wrote it

      def test_a_refused_rebuild_closes_its_source(self):
          self.judge_source(D1, self.REPAIR)
          lines = self.judge_held(D1, S1, self.REPAIR)
          held, closing = lines
          self.assertEqual((held["digest"], held["state"], held["source"]), (S1, "transformation-required", D1))
          self.assertEqual((closing["digest"], closing["ref"], closing["state"], closing["reason"]),
                           (D1, self.SOURCE, "quarantine", "uske/rebuild-refused"))
          self.assertEqual((closing["rebuilt"], closing["ruleset"], closing["report"]),
                           (S1, held["ruleset"], held["report"]))
          self.assertEqual(self.record("held.json", lines), 2)
          self.assertEqual(self.record("held-again.json", lines), 0)  # replaying the second gate adds nothing
          rebuilt = plan(self.NAME, [("1.0", D1)], transformed=True)
          self.assertEqual(self.approve(rebuilt, "--transit", "transit"),
                           ({"approved": 0, "discarded": {"refused": 1}}, []))
          todo = run("pending", "--policy", self.POLICY, "--plan", self.write("plan.json", rebuilt),
                     "--results", str(self.results))[1]
          self.assertEqual(todo, [])  # a closed source is not judged again

      def test_a_first_gate_line_is_untouched(self):
          line = self.classify(FULL, self.SOURCE, D1, self.REPAIR)
          self.assertIsInstance(line, dict)
          self.assertNotIn("source", line)
  ```
- [x] 6.2 Lancer la commande de test. Attendu : `error: unrecognized arguments: --source-ref`.
- [x] 6.3 Dans `uske/cli.py`, ajouter `import dataclasses` avec les imports de la bibliothèque
  standard, et remplacer la dernière ligne de `cmd_classify`, `_json(line.to_dict())`, par :

  ```python
      if not args.source_digest:  # first gate; Argo passes an empty string
          _json(line.to_dict())
          return
      lines = [dataclasses.replace(line, source=args.source_digest).to_dict()]
      if outcome in (outcomes.Outcome.TRANSFORMATION_REQUIRED, outcomes.Outcome.QUARANTINE):
          # the rebuild was judged and refused: close the source, one attempt only
          lines.append(results.ResultLine(
              ts=line.ts, ref=args.source_ref, digest=args.source_digest,
              state=outcomes.Outcome.QUARANTINE.value, ruleset=ruleset,
              reason=gate.REBUILD_REFUSED, report=line.report, rebuilt=args.digest,
          ).to_dict())
      _json(lines)
  ```

  Dans `parser()`, sous `classify`, ajouter après la ligne `--regis-exit` :

  ```python
      s.add_argument("--source-ref", default="", help="for a held image: the source it was built from")
      s.add_argument("--source-digest", default="", help="for a held image: that source's digest")
  ```
- [x] 6.4 Lancer la commande de test. Attendu : `OK`.
- [x] 6.5 Commit : `git add uske/cli.py tests/test_orchestrator.py && git commit -m "feat: classify consigne une image retenue et clôt la source d'une reconstruction refusée"`.

## 7. Les essais bornés, la réouverture, et ce que la clôture ne dit pas

**Fichiers** : `tests/test_orchestrator.py`. Aucun code de produit : les groupes 3 à 6 suffisent,
et ces tests le montrent.

- [x] 7.1 Écrire les tests, dans `class Rebuild` :

  ```python
      def test_a_silent_judge_is_retried_three_times_then_a_line_reopens(self):
          self.judge_source(D1, self.REPAIR)
          rebuilt = plan(self.NAME, [("1.0", D1)], transformed=True)
          for held in (S1, S2):
              lines = self.judge_held(D1, held, report(None))
              self.assertEqual([l["state"] for l in lines], ["inconclusive"])  # nothing closes
              self.record(f"held-{held[-4:]}.json", lines)
              self.assertEqual(self.approve(rebuilt, "--transit", "transit")[1], ["1.0"])
          self.record("held-third.json", self.judge_held(D1, S3, report(None)))
          self.assertEqual(self.approve(rebuilt, "--transit", "transit"),
                           ({"approved": 0, "discarded": {"attempts-exhausted": 1}}, []))
          self.assertEqual(self.journal()[-1]["digest"], S3)  # nothing was written on the source

          reopen = {"ts": "2026-10-10T00:00:00Z", "ref": self.SOURCE, "digest": D1,
                    "state": "inconclusive", "ruleset": "none", "reason": "uske/reopened"}
          self.assertEqual(self.record("reopen.json", reopen), 1)
          todo = run("pending", "--policy", self.POLICY, "--plan", self.write("plan.json", rebuilt),
                     "--results", str(self.results))[1]
          self.assertEqual([c["digest"] for c in todo], [D1])
          self.judge_source(D1, self.REPAIR)
          self.assertEqual(self.approve(rebuilt, "--transit", "transit")[1], ["1.0"])

      def test_a_closed_source_reopens_by_the_same_line(self):
          self.judge_source(D1, self.REPAIR)
          self.record("held.json", self.judge_held(D1, S1, self.REPAIR))
          self.record("reopen.json", {"ts": "2026-10-10T00:00:00Z", "ref": self.SOURCE, "digest": D1,
                                      "state": "inconclusive", "ruleset": "none", "reason": "uske/reopened"})
          self.judge_source(D1, self.REPAIR)
          rebuilt = plan(self.NAME, [("1.0", D1)], transformed=True)
          self.assertEqual(self.approve(rebuilt, "--transit", "transit")[1], ["1.0"])

      def test_a_sound_source_whose_rebuild_is_refused_is_closed_too(self):
          self.judge_source(D1, report("Placement direct"))
          self.record("held.json", self.judge_held(D1, S1, self.REPAIR))
          closing = self.journal()[-1]
          self.assertEqual((closing["digest"], closing["reason"]), (D1, "uske/rebuild-refused"))
          # not a verdict of the judge on the source: the reason says so, and story 3 must read it
          self.assertNotEqual(closing["reason"], "secrets/verified-secrets")
  ```
- [x] 7.2 Lancer la commande de test. Attendu : `OK`, sans toucher au produit. Si un test
  échoue, le défaut est dans les groupes 3 à 6 : le corriger là.
- [x] 7.3 Vérifier qu'aucun identifiant de test n'est entré dans le produit :
  `uv run --with pyyaml python -m unittest tests.test_orchestrator.NothingHardcoded`. Attendu :
  `OK`.
- [x] 7.4 Commit : `git add tests/test_orchestrator.py && git commit -m "test: les essais sans verdict sont bornés, et une ligne rouvre une source"`.
- [ ] 7.5 Ouvrir la demande de fusion du Python : titre `feat: une source à réparer passe par le
  transit, sa sortie est jugée avant d'être promue`. Sa description dit que rien ne change tant que
  le workflow ne passe pas `--transit`, et renvoie à ce change.

## 8. Le workflow : la seconde porte — troisième demande de fusion

**Fichiers** : `deploy/base/workflowtemplate.yaml`, `deploy/kind/kustomization.yaml`. Après les
tâches 1.3 et 1.5. Les noms ci-dessous sont ceux d'après le renommage (`uske`) ; si le fichier
porte encore `orchestrator`, ce groupe attend.

- [ ] 8.1 Ajouter le paramètre, **en dernier** dans `spec.arguments.parameters` (le banc patche
  les trois premiers par index) :

  ```yaml
        - name: transit  # a name of KNOCK_REGISTRIES: where rebuilt images are held until judged
          value: transit
  ```
- [ ] 8.2 Dans le gabarit `policy`, à l'étape `approve`, ajouter `--transit` aux arguments :

  ```yaml
                    approve --policy {{inputs.parameters.path}} --results /results
                    --plan /work/plans/{{inputs.parameters.name}}.json
                    --out /work/plans/{{inputs.parameters.name}}.approved.json
                    --transit {{workflow.parameters.transit}}
  ```
- [ ] 8.3 Remplacer l'étape `place` par ces trois étapes :

  ```yaml
        - - name: place  # knock's gate, step 2: copies are placed, rebuilds are held in the transit
            template: knock-once
            when: "{{=jsonpath(steps.approve.outputs.result, '$.approved') > 0}}"
            continueOn:  # one failed build must not withhold the images that were held
              failed: true
              error: true
            arguments:
              parameters:
                - name: args
                  value: >-
                    reconcile /work/policies/{{inputs.parameters.name}}
                    --apply-plan /work/plans/{{inputs.parameters.name}}.approved.json
                    --stage-to {{workflow.parameters.transit}}
                    --staged-out /work/staged/{{inputs.parameters.name}}.json
        - - name: second-gate
            template: staged
            when: "{{=jsonpath(steps.approve.outputs.result, '$.approved') > 0}}"
            arguments:
              parameters:
                - {name: name, value: "{{inputs.parameters.name}}"}
                - {name: path, value: "{{inputs.parameters.path}}"}
                - {name: playbook, value: "{{=jsonpath(steps.resolve.outputs.result, '$.playbook')}}"}
        - - name: place-failed  # the failure stays visible once everything held has been handled
            template: fail
            when: "{{steps.place.status}} == Failed || {{steps.place.status}} == Error"
  ```
- [ ] 8.4 Dans le gabarit `evaluate`, remplacer la ligne `parameters: [...]` de ses entrées et
  l'étape `classify` par :

  ```yaml
        parameters:
          - {name: policy}
          - {name: playbook}
          - {name: ref}
          - {name: digest}
          - {name: target}
          - {name: key}
          # A held image names its source and writes its lines apart: read with the first
          # gate's, the source's own line would reopen it after its closure.
          - {name: source-ref, value: ""}
          - {name: source-digest, value: ""}
          - {name: lines, value: lines}
  ```

  ```yaml
        - - name: classify
            template: classify
            arguments:
              parameters:
                - name: args
                  value: >-
                    classify --playbook {{inputs.parameters.playbook}}
                    --ref {{inputs.parameters.ref}} --digest {{inputs.parameters.digest}}
                    --report /work/reports/{{inputs.parameters.key}}/report.json
                    --report-link /results/reports/{{inputs.parameters.policy}}/{{inputs.parameters.digest}}.html
                    --regis-exit {{steps.regis.exitCode}}
                    --source-ref "{{inputs.parameters.source-ref}}"
                    --source-digest "{{inputs.parameters.source-digest}}"
                - {name: out, value: "/work/{{inputs.parameters.lines}}/{{inputs.parameters.policy}}/{{inputs.parameters.key}}.json"}
                - {name: html, value: "/work/reports/{{inputs.parameters.key}}/report.html"}
                - {name: link, value: "/results/reports/{{inputs.parameters.policy}}/{{inputs.parameters.digest}}.html"}
  ```

  Les guillemets autour des deux paramètres de source sont nécessaires : vides, ils
  disparaîtraient de la ligne de commande et `argparse` sortirait en erreur d'usage.
- [ ] 8.5 Dans le gabarit `knock`, créer aussi le répertoire des images retenues :
  `args: ["mkdir -p /work/plans /work/staged && knock {{inputs.parameters.args}}"]`.
- [ ] 8.6 Ajouter **à la fin** de `spec.templates` (le banc patche les gabarits 3, 6 et 7 par
  index) :

  ```yaml
      - name: staged  # the second gate: judge what knock built, then promote what is sound
        inputs:
          parameters: [{name: name}, {name: path}, {name: playbook}]
        steps:
          - - name: pending
              template: uske
              arguments:
                parameters:
                  - name: args
                    value: >-
                      pending --policy {{inputs.parameters.path}}
                      --staged /work/staged/{{inputs.parameters.name}}.json --results /results
          - - name: evaluate
              template: evaluate
              withParam: "{{steps.pending.outputs.result}}"
              arguments:
                parameters:
                  - {name: policy, value: "{{inputs.parameters.name}}"}
                  - {name: playbook, value: "{{inputs.parameters.playbook}}"}
                  - {name: ref, value: "{{item.ref}}"}
                  - {name: digest, value: "{{item.digest}}"}
                  - {name: target, value: "{{item.target}}"}
                  - {name: key, value: "{{item.key}}"}
                  - {name: source-ref, value: "{{item.sourceRef}}"}
                  - {name: source-digest, value: "{{item.source}}"}
                  - {name: lines, value: staged-lines}
          - - name: record
              template: uske
              arguments:
                parameters:
                  - name: args
                    value: >-
                      record --policy {{inputs.parameters.path}} --results /results
                      --lines /work/staged-lines/{{inputs.parameters.name}}
          - - name: approve
              template: uske
              arguments:
                parameters:
                  - name: args
                    value: >-
                      approve --policy {{inputs.parameters.path}} --results /results
                      --staged /work/staged/{{inputs.parameters.name}}.json
                      --out /work/staged/{{inputs.parameters.name}}.approved.json
          - - name: promote  # the prepared policy, with admit: promote signs what it places
              template: knock
              when: "{{=jsonpath(steps.approve.outputs.result, '$.approved') > 0}}"
              arguments:
                parameters:
                  - name: args
                    value: >-
                      promote /work/policies/{{inputs.parameters.name}}
                      --staged /work/staged/{{inputs.parameters.name}}.approved.json

      - name: knock-once  # no retry: a retried apply rebuilds every held image under a new digest
        inputs:
          parameters:
            - name: args
        container:
          image: knock
          command: [sh, -c]
          args: ["mkdir -p /work/plans /work/staged && knock {{inputs.parameters.args}}"]
          envFrom:
            - secretRef: {name: uske-knock}
          volumeMounts:
            - {name: work, mountPath: /work}

      - name: fail  # no retry either
        container:
          image: uske
          command: [sh, -c]
          args: ["echo 'knock reconcile --apply-plan failed for this policy' >&2; exit 1"]
  ```

  Reprendre du gabarit `knock` le nom exact du secret et du gabarit `uske` ; ne pas les deviner.
- [ ] 8.7 Dans `deploy/kind/kustomization.yaml`, donner au gabarit `knock-once` (index 9) les
  mêmes montages que `knock` (index 7), à la suite des patches existants :

  ```yaml
        - op: add
          path: /spec/templates/9/container/volumeMounts/-
          value: {name: registry-ca, mountPath: /etc/registry-ca, readOnly: true}
        - op: add
          path: /spec/templates/9/container/volumeMounts/-
          value: {name: knock-key, mountPath: /keys, readOnly: true}
  ```
- [ ] 8.8 Vérifier les manifestes :

  ```bash
  kubectl kustomize deploy/kind > /tmp/uske.yaml && argo lint --offline /tmp/uske.yaml
  ```

  Attendu : `no linting errors found!`. Si `deploy/example` existe, le rendre et le linter de la
  même façon, après lui avoir ajouté `transit` dans son bloc de paramètres.
- [ ] 8.9 Vérifier que le montage a suivi : `grep -c "registry-ca" /tmp/uske.yaml`. Attendu : un
  de plus qu'avant ce groupe.
- [ ] 8.10 Commit : `git add deploy/ && git commit -m "feat: le screening retient ce que knock reconstruit, le fait juger, puis promouvoir"`.

## 9. Le banc : une réparation qui réussit, une qui est refusée

**Fichiers** : `deploy/kind/up.sh`, `deploy/kind/kustomization.yaml`, `deploy/kind/buildkitd.yaml`
(créé), deux fichiers sous `deploy/kind/policies/` (créés). Après la tâche 1.1 : les deux images
sont celles qu'elle a retenues, notées `<réparable>` et `<en-root>` ci-dessous.

- [ ] 9.1 Dans `deploy/kind/up.sh` et `deploy/kind/kustomization.yaml`, remplacer l'empreinte de
  `knock` par celle de la tâche 1.3, avec son numéro de version en commentaire.
- [ ] 9.2 Créer `deploy/kind/buildkitd.yaml` : un `Deployment` et un `Service` `buildkitd`, port
  1234, image `moby/buildkit:v0.30.0-rootless`, repris de
  `../knock/deploy/components/buildkitd/deployment.yaml`. Deux écarts : pas de port de métriques,
  et un `buildkitd.toml` qui fait confiance à l'autorité du banc :

  ```toml
  [registry."registry.uske.svc.cluster.local:5000"]
    ca = ["/etc/registry-ca/bundle.pem"]
  ```

  avec le secret `registry-ca` monté sur `/etc/registry-ca`. L'ajouter à `resources:` dans
  `deploy/kind/kustomization.yaml`.
- [ ] 9.3 Dans `deploy/kind/up.sh`, à la création du secret de `knock`, donner à la liste une
  entrée de transit, un miroir et l'adresse de BuildKit :

  ```bash
    --from-literal=KNOCK_REGISTRIES="{\"local\": {\"host\": \"$REGISTRY\"}, \"transit\": {\"host\": \"$REGISTRY/transit\"}}" \
    --from-literal=KNOCK_TRANSFORM_PACKAGE_MIRRORS='{"bench": {"apt": "https://deb.debian.org/debian", "apk": "https://dl-cdn.alpinelinux.org/alpine"}}' \
    --from-literal=BUILDKIT_HOST=tcp://buildkitd:1234 \
  ```

  La dernière ligne emploie ce que la tâche 1.4 a trouvé. Ajouter après le déploiement du
  registre : `kubectl -n "$NS" rollout status deploy/buildkitd --timeout=180s`.
- [ ] 9.4 Créer `deploy/kind/policies/hub-reparable.yaml` et `deploy/kind/policies/hub-en-root.yaml`,
  sur le modèle de `deploy/kind/policies/hub-redis-7.yaml`, label `admission-track: standard`,
  une seule étiquette sélectionnée chacune, et :

  ```yaml
        transform:
          - rewritePackageSources: { mirror: bench }
          - upgradePackages: { epoch: "2026-10-10" }
  ```

  En tête de chaque fichier, un commentaire dit ce que le banc attend d'elle et la date de la
  mesure de la tâche 1.1.
- [ ] 9.5 Monter le banc et lancer un screening : `deploy/kind/up.sh`. Noter la durée, et celle
  du même montage sur `main` : c'est la mesure du finding 19. Si elle double, arrêter et proposer
  à la personne de faire de la réparation une variante `up.sh repair`.
- [ ] 9.6 Vérifier la réparation réussie :

  ```bash
  kubectl -n uske exec deploy/registry -- ls /var/lib/registry/hub/<réparable>
  kubectl -n uske run journal --rm -i --restart=Never --image=uske:dev \
    --overrides='{"spec":{"containers":[{"name":"j","image":"uske:dev","command":["cat","/results/hub-reparable.jsonl"],"volumeMounts":[{"name":"r","mountPath":"/results"}]}],"volumes":[{"name":"r","persistentVolumeClaim":{"claimName":"uske-results"}}]}}'
  ```

  Attendu : le dépôt existe dans la destination ; le journal porte une ligne
  `transformation-required` sur la source, puis une ligne `direct-placement` avec une clé
  `source`. `deploy/kind/attestations.sh` sur l'image placée rend sa signature.
- [ ] 9.7 Vérifier la réparation refusée : le même `cat` sur `/results/hub-en-root.jsonl`.
  Attendu : trois lignes — la source en `transformation-required`, l'image retenue avec `source`,
  puis la source en `quarantine`, raison `uske/rebuild-refused`, avec `rebuilt`. Le dépôt existe
  sous `/var/lib/registry/transit/hub/` et pas sous `/var/lib/registry/hub/`.
- [ ] 9.8 Lancer un second screening : `argo -n uske submit deploy/kind/screening.yaml --wait`.
  Attendu : le journal de `hub-en-root` n'a pas de ligne de plus, et l'étape `second-gate` de
  cette politique est `Skipped`.
- [ ] 9.9 Éprouver les pannes à la main (finding 9), chacune sur un banc remonté :
  - retirer `transit` de `KNOCK_REGISTRIES`, lancer un screening : l'étape `place` échoue, rien
    n'est placé, `place-failed` fait échouer la politique ;
  - arrêter `buildkitd` (`kubectl -n uske scale deploy/buildkitd --replicas=0`), lancer un
    screening : `place` échoue, `second-gate` tourne et ne promeut rien, la politique finit en
    échec, les politiques en voie copie sont placées.

  Noter les deux résultats. Si `{{steps.place.status}}` ne se résout pas quand `place` est
  `Skipped`, le dire : c'est le point d'Argo que la revue n'a pas pu vérifier (finding 16).
- [ ] 9.10 Commit : `git add deploy/kind && git commit -m "feat: le banc local montre une réparation réussie et une refusée"`.

## 10. Écrire, décider, auditer

- [ ] 10.1 `README.md` : la liste des étapes d'un screening gagne le transit et la seconde porte ;
  l'encadré *Status* ne dit plus que seul le placement direct agit, mais que deux issues sur
  quatre agissent ; une section « Rebuilds » dit la version minimale de `knock`, que sans le champ
  `transformed` rien n'est réparé, et le geste qui rouvre une source : la ligne à ajouter, ses
  cinq clés, et qu'il faut un pod jetable pour écrire sur le volume.
- [ ] 10.2 Ce qu'une surcouche doit fournir (findings 6 et 13), dans `docs/consommer-la-base.md`
  si elle existe, sinon dans la même section du `README.md` : le paramètre `transit` ; l'entrée
  de liste, **sur l'hôte de la destination** ; une seule identité `knock` avec l'écriture sur les
  deux projets ; la lecture du transit pour `regis` ; l'adresse de BuildKit ; les miroirs.
- [ ] 10.3 `docs/architecture/arc42.md`, *Essential Features* : remplacer « Rendre au placeur le
  plan, moins les opérations refusées ; il n'applique que cela » par deux lignes — le plan
  filtré, où une source à réparer n'est rendue que si le placeur la reconstruit ; puis ce que le
  placeur a construit, retenu, jugé par empreinte, et promu seulement en placement direct.
- [ ] 10.4 Créer `docs/adr/SDR-0016-journal-et-transit.md`, en français, avec le frontmatter des
  autres ADR (`adr`, `slug`, `title`, `status: accepted`, `date`, `authors`, `supersedes: []`,
  sans bloc `traits:`) et les sections du gabarit. Il consigne les deux décisions de la section
  ADR de ce plan, et renvoie à `design.md` D3, D5, D6 et D7 sans les recopier. L'ajouter au
  journal des décisions de `docs/architecture/arc42.md`. Si `SDR-0014` et `SDR-0015` n'existent
  pas encore à ce moment, garder `0016` : ces deux numéros sont réservés.
- [ ] 10.5 `openspec/discovery.md` : cocher la story 4 et y nommer ce change ; à la story 3,
  ajouter une ligne — une clôture `uske/rebuild-refused` n'est pas une quarantaine du juge, et
  une copie de la même source peut être en service (finding 8) ; à l'étape 4 du parcours,
  remplacer « seule `direct-placement` agit ».
- [ ] 10.6 Auditer la surface d'attaque (finding 18) : lancer `/cso` sur la branche. Sans la
  commande, parcourir à la main l'OWASP Top 10 et STRIDE sur trois points — l'écriture de
  `knock` sur le transit, la signature à la promotion sur la foi d'un fichier filtré, le port de
  `buildkitd` sur le banc — et ouvrir un fil sur la demande de fusion pour chaque point non
  vérifié.
- [ ] 10.7 Relire le plan de documentation de ce fichier contre ce qui a été écrit : chaque ligne
  du tableau a son fichier modifié dans `git diff --stat main`.
- [ ] 10.8 Valider le change : `openspec validate issue-transformation --type change --strict`.
  Attendu : `Change 'issue-transformation' is valid`.
- [ ] 10.9 Commit : `git add README.md docs/ openspec/discovery.md && git commit -m "docs: le screening en deux portes, et les décisions qui le tiennent"`.
- [ ] 10.10 Ouvrir la demande de fusion du workflow, du banc et des écrits : titre `feat: le
  screening fait juger ce que knock reconstruit avant de le promouvoir`. Sa description porte les
  résultats des tâches 1.1, 9.5 et 9.9.
