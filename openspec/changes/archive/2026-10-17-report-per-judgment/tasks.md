# Plan — report-per-judgment

> **Pour l'agent qui applique ce plan :** `/opsx:apply report-per-judgment`, tâche par tâche, test
> d'abord. Les cases `- [ ]` suivent l'avancement.

**But :** un rapport copié par `uske screen` n'est jamais réécrit, et le crochet reçoit l'étape qui
l'appelle (`USKE_STEP`).

**Approche :** `keep_report` nomme le rapport d'après l'epoch, avec un nom libre, et le copie par
création exclusive. `record()` reçoit le nom de l'étape et le passe à `hook()`. Les spécifications
sont dans `specs/screen-command/spec.md` (MODIFIED) ; il n'y a pas de `design.md` (voir
`proposal.md`, Conception).

**Outils :** Python 3.12, `unittest` lancé par `pytest` (`make test` : couverture de branches,
bloquante sous 90 %).

## Plan de documentation

| Chemin | Quadrant | Destinataire | Geste |
| --- | --- | --- | --- |
| `docs/how-to/operate.md` (section *Screen locally*) | guide | l'opérateur qui lance `uske screen` hors d'Argo, et l'auteur d'un crochet | modifiée |
| `uske/cli.py` (`SCREEN_EPILOG`, l'aide de `uske screen --help`) | — | l'utilisateur de la CLI | modifiée |
| `CHANGELOG.md` | — | qui lit la release | modifiée par Release Please, au merge |

## ADR

- Revue des ADR faite pour ce change. Frontmatter relu pour SDR-0001 à SDR-0011 et SDR-0016 à
  SDR-0022, tous `accepted`, sans aucun `supersedes`.
- Relus en entier :
  - SDR-0018 (« Une ligne du journal nomme le screening qui l'a écrite ») : la ligne garde `run`.
    Seul le nom du fichier de rapport cesse d'en dépendre, et SDR-0018 n'impose rien sur ce nom ;
  - SDR-0021 (« Un verbe qui lance les deux outils, et un Workflow par politique ») : il pose le
    crochet `USKE_AFTER_RECORD`, que `USKE_STEP` complète sans en changer le contrat ;
  - SDR-0007 (tests) : le seuil de couverture, que les tests ci-dessous tiennent ;
  - SDR-0022 (documentation en anglais) : la langue de `operate.md` et de l'aide.
- Créés : aucun. Aucune décision durable et transverse n'est introduite : le nom d'un rapport et
  une variable du crochet sont des détails de la commande, que décrit `screen-command`.

## 1. Le rapport d'un jugement n'est jamais réécrit

**Fichiers :** `uske/screen.py` (`_Screening.keep_report`, et une fonction `_free_stem` à ajouter
après `_file_name`), `tests/test_screen.py` (classe `Reports`).

- [x] 1.1 Dans `tests/test_screen.py`, classe `Reports`, remplacer les quatre premiers tests par
  ceux-ci. Ils couvrent le scénario « Un rapport cité par un chemin relatif », et le run ne nomme
  plus le rapport :

  ```python
  def test_the_report_is_copied_and_cited_relative_to_the_results(self):
      """*Un rapport cité par un chemin relatif*."""
      code, _, _ = self.screen("--policy", str(REDISTRIBUTION), "--run", "41")
      self.assertEqual(code, 0)
      relative = f"reports/fixture-redistribution/{D4}/{EPOCH}.md"
      self.assertTrue((self.results / relative).is_file())
      self.assertTrue((self.results / relative).with_suffix(".html").is_file())
      self.assertEqual(self.journal("fixture-redistribution")[0]["report"], relative)

  def test_the_run_never_names_the_report(self):
      self.screen(
          "--policy", str(REDISTRIBUTION), "--run", "https://ci.example/runs/77/"
      )
      line = self.journal("fixture-redistribution")[0]
      self.assertEqual(
          line["report"], f"reports/fixture-redistribution/{D4}/{EPOCH}.md"
      )
      self.assertEqual(line["run"], "https://ci.example/runs/77/")
  ```

  Supprimer `test_without_a_run_the_epoch_names_the_report` et
  `test_a_run_of_dots_falls_back_to_the_epoch` : le run ne sert plus au nom.
- [x] 1.2 Ajouter le test du scénario « Une empreinte rejugée sous le même epoch » :

  ```python
  def test_a_judgment_never_rewrites_an_earlier_report(self):
      """*Une empreinte rejugée sous le même epoch*."""
      folder = self.results / "reports" / "fixture-redistribution" / D4
      folder.mkdir(parents=True)
      (folder / f"{EPOCH}.md").write_text("earlier")
      code, _, _ = self.screen("--policy", str(REDISTRIBUTION))
      self.assertEqual(code, 0)
      self.assertEqual((folder / f"{EPOCH}.md").read_text(), "earlier")
      self.assertFalse((folder / f"{EPOCH}.html").exists())
      self.assertTrue((folder / f"{EPOCH}-2.html").is_file())
      self.assertEqual(
          self.journal("fixture-redistribution")[0]["report"],
          f"reports/fixture-redistribution/{D4}/{EPOCH}-2.md",
      )
  ```

- [x] 1.3 Lancer `uv run python -m pytest --no-cov -q tests/test_screen.py -k Reports`. Résultat
  attendu : échecs sur `test_the_report_is_copied_and_cited_relative_to_the_results` (le rapport
  est cité en `41.md`), sur `test_the_run_never_names_the_report` (`https_ci.example_runs_77.md`)
  et sur `test_a_judgment_never_rewrites_an_earlier_report` (le fichier contient le rapport du
  juge, et non `earlier`).
- [x] 1.4 Dans `uske/screen.py`, ajouter sous `_file_name` :

  ```python
  REPORT_EXTS = ("md", "html", "json")


  def _free_stem(folder: Path, base: str) -> str:
      """The first name no report carries yet in `folder`: `base`, then `base-2`, `base-3`…"""
      stem, n = base, 1
      while any((folder / f"{stem}.{ext}").exists() for ext in REPORT_EXTS):
          n += 1
          stem = f"{base}-{n}"
      return stem
  ```

  Puis, dans `keep_report`, remplacer le bloc qui va de `# a run may be a URL (SDR-0018)` jusqu'au
  `return` par :

  ```python
  # the epoch names the report, never the run: one judgment, one file, never rewritten
  relative = Path("reports") / self.policy.name / digest
  folder = inside(self.results / relative, self.results / "reports")
  folder.mkdir(parents=True, exist_ok=True)
  stem = _free_stem(folder, _file_name(self.epoch) or "report")
  for ext in written:
      with (out / f"report.{ext}").open("rb") as src, (
          folder / f"{stem}.{ext}"
      ).open("xb") as dst:  # exclusive: fails rather than rewrite a cited report
          shutil.copyfileobj(src, dst)
  return str(relative / f"{stem}.{written[0]}")
  ```

  Mettre à jour la docstring de `keep_report` : le nom est l'epoch, ou le premier nom libre.
- [x] 1.5 Relancer `uv run python -m pytest --no-cov -q tests/test_screen.py`. Résultat attendu :
  tout passe, `0 failed`.
- [x] 1.6 Point de commit : `fix: un rapport rejugé par uske screen n'écrase plus celui d'une décision antérieure`.

## 2. Le crochet reçoit l'étape qui l'appelle

**Fichiers :** `uske/screen.py` (`_Screening.record`, `_Screening.hook`, les cinq appels à
`self.record`), `tests/test_screen.py` (la classe des tests du crochet, celle de
`test_the_journal_is_committed_before_the_placement`).

- [x] 2.1 Ajouter les tests des deux scénarios, dans la classe de
  `test_the_journal_is_committed_before_the_placement` :

  ```python
  def steps(self) -> list[str]:
      return (self.tmp / "steps").read_text().split()

  def test_the_hook_knows_the_step_that_wrote(self):
      """*Le crochet sait quelle étape l'appelle*."""
      only_a_source_to_repair(self.tmp)
      self.verdicts(**{D2: "repairable", held(D2): "direct"})
      os.environ["USKE_AFTER_RECORD"] = f'echo "$USKE_STEP" >> "{self.tmp}/steps"'
      code, _, _ = self.screen("--policy", str(STANDARD), "--transit", "transit")
      self.assertEqual(code, 0)
      self.assertEqual(self.steps(), ["record", "record-held", "record-promoted"])

  def test_the_hook_after_a_source_left_without_transit(self):
      """*Une source à réparer sans transit*."""
      self.verdicts(**{D2: "repairable"})
      os.environ["USKE_AFTER_RECORD"] = f'echo "$USKE_STEP" >> "{self.tmp}/steps"'
      self.screen("--policy", str(STANDARD))
      self.assertEqual(self.steps()[:2], ["record", "record-approve"])

  def test_the_hook_after_a_placement(self):
      os.environ["USKE_AFTER_RECORD"] = f'echo "$USKE_STEP" >> "{self.tmp}/steps"'
      self.screen("--policy", str(REDISTRIBUTION))
      self.assertEqual(self.steps(), ["record", "record-applied"])
  ```

- [x] 2.2 Lancer `uv run python -m pytest --no-cov -q tests/test_screen.py -k hook`. Résultat
  attendu : les trois nouveaux tests échouent, parce que `steps` ne contient que des lignes vides
  (`['']` ou une liste vide).
- [x] 2.3 Dans `uske/screen.py` :
  - ajouter `step: str` comme premier paramètre de `record` (`def record(self, step: str, *, lines=…)`) ;
  - remplacer `self.hook()` par `self.hook(step)` ;
  - définir `def hook(self, step: str) -> None:` et ajouter `"USKE_STEP": step,` dans `env`, à
    côté de `USKE_POLICY` ;
  - nommer chacun des cinq appels :

  | Ligne actuelle | Devient |
  | --- | --- |
  | `self.record(lines=p.lines)` (dans `steps`) | `self.record("record", lines=p.lines)` |
  | `self.record(lines=p.approve_lines)` | `self.record("record-approve", lines=p.approve_lines)` |
  | `self.record(applied=p.applied)` | `self.record("record-applied", applied=p.applied)` |
  | `self.record(lines=p.staged_lines)` | `self.record("record-held", lines=p.staged_lines)` |
  | `self.record(promoted=p.staged_approved)` | `self.record("record-promoted", promoted=p.staged_approved)` |

- [x] 2.4 Relancer `uv run python -m pytest --no-cov -q tests/test_screen.py`. Résultat attendu :
  tout passe, `0 failed`. Si `test_the_hook_after_a_source_left_without_transit` ne voit pas
  `record-approve`, c'est que l'approbation n'a pas écrit de ligne `uske/no-transit` : vérifier
  d'abord que `test_without_a_transit_nothing_is_ordered` passe, plutôt que de modifier le test.
- [x] 2.5 Point de commit : `feat: le crochet de uske screen sait quelle étape l'appelle`.

## 3. Documentation

- [x] 3.1 Dans `docs/how-to/operate.md`, section *Screen locally* :
  - remplacer le paragraphe « Reports are copied to `reports/<policy>/<digest>/<run>.<ext>` … » par
    `reports/<policy>/<digest>/<epoch>.<ext>`, avec le premier nom libre (`<epoch>-2`, …) quand
    l'empreinte a déjà un rapport sous cet epoch : un rapport cité n'est jamais réécrit, et la
    ligne garde le run en `run` ;
  - dans le bloc qui présente `USKE_AFTER_RECORD`, ajouter `USKE_STEP` et ses cinq valeurs, avec
    un exemple de message de commit `journal($USKE_POLICY): $USKE_STEP`. Préciser que le crochet
    n'est appelé qu'après une étape qui a écrit au moins une ligne : un screening ne passe donc pas
    toujours par les cinq étapes (review, finding 4).

  Vérification : `grep -n "<run>.<ext>" docs/how-to/operate.md` ne renvoie rien, et
  `grep -c USKE_STEP docs/how-to/operate.md` renvoie au moins 2.
- [x] 3.2 Dans `uske/cli.py`, `SCREEN_EPILOG` : sur la ligne de `USKE_AFTER_RECORD`, écrire
  « with USKE_POLICY, USKE_RESULTS and USKE_STEP set ». Vérification :
  `uv run uske screen --help | grep USKE_STEP` affiche la ligne.
- [x] 3.3 Point de commit : `docs: dire comment uske screen nomme ses rapports, et USKE_STEP`.

## 4. Vérification d'ensemble

- [x] 4.1 `make lint`, puis `make test`. Résultat attendu : `ruff` sans erreur, et pytest qui
  termine avec une couverture d'au moins 90 %, sans `FAIL Required test coverage`.
- [x] 4.2 `openspec validate report-per-judgment --type change --strict`. Résultat attendu :
  `Change 'report-per-judgment' is valid`.
- [x] 4.3 Ouvrir la PR. Après la release suivante, retirer de la release 0.9.0 d'uske le problème
  connu « Report names from `uske screen` », et ajuster `base-images` si son crochet existe déjà :
  `openspec/changes/uske-screen`, D4, et sa tâche 1.2.
