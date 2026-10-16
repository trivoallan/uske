# Plan — decisions

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** une sous-commande `uske decisions`, en lecture seule, qui rend le journal lisible pour
l'équipe applicative et l'auditeur, en JSON, en texte ou en Markdown avec une `timeline` Mermaid.

**Architecture:** un module `uske/decisions.py` qui lit, annote, filtre et rend ; `uske/cli.py`
n'ajoute qu'un parseur et une fonction `cmd_decisions`. Le module ne dépend que de
`uske.outcomes`. Aucune écriture, aucune dépendance nouvelle.

**Tech Stack:** Python 3 (stdlib : `json`, `datetime`, `pathlib`), `argparse`, `unittest` lancé par
`pytest` avec `pytest-cov` (seuil 90 %).

**Fichiers :**

- Create : `uske/decisions.py` — lecture, annotation, sélection, rendus `text` et `md`.
- Create : `tests/test_decisions.py` — tests du module et de la sous-commande.
- Create : `tests/golden/decisions-redis-728.txt`, `tests/golden/decisions-redis-728.md`,
  `tests/golden/decisions-escape.md` — sorties attendues.
- Modify : `uske/cli.py` — import, docstring, `cmd_decisions`, parseur.
- Modify : `tests/fixtures/repo/policies/projets/a-4711/redis-7.journal.jsonl` — ligne 5.
- Modify : `README.md` — section *Use*.
- Modify : `openspec/discovery.md` — story 2, champ *Change*.

Chaque commande se lance depuis la racine du dépôt `uske`.

## Plan de documentation

| Chemin | Quadrant | Destinataire | Geste |
| --- | --- | --- | --- |
| `README.md` (section *Use*) | — | la responsable plateforme, l'équipe applicative et l'auditeur qui lancent `uske` | modifiée : `decisions` ajoutée, et la phrase « une sous-commande par étape » corrigée |
| `uske/cli.py` (docstring du module) | — | l'auteur et les agents qui lisent le code | modifiée : `decisions` n'est pas une étape du workflow |
| `openspec/discovery.md` (story 2) | — | l'auteur et les agents qui planifient | modifiée : `Change : decisions` |

Hors du dépôt, et donc hors de cette demande de fusion : O2-KR2 du wiki nanopm
(`.nanopm/wiki/docs/objectives.md`, dépôt privé `oci-pm`) nomme encore `retrouver-un-refus`.

## ADR

- Revue des ADR conduite pour ce change. Frontmatter relu pour les quatorze fichiers de
  `docs/adr/` (`SDR-0001` à `SDR-0011`, `SDR-0016`, `SDR-0017`) ; tous `accepted`, aucun
  `supersedes` en vigueur qui touche le journal.
- Relu au corps : `SDR-0016` — il fixe le vocabulaire que `decisions` lit (`source`, `rebuilt`,
  `uske/rebuild-refused`, `uske/reopened`) et pose que tout lecteur doit rendre la raison avec
  l'état. Le delta s'y conforme.
- Relu au frontmatter pour ce qu'il impose ici : `SDR-0002` — prose en français, code et
  commentaires en anglais.
- Créés : aucun — `decisions` ne fait que lire ; « l'ordre du fichier fait foi » découle de
  l'ajout seul que SDR-0016 a déjà fixé, et le vocabulaire de l'arbitrage reste hors de ce change.

## 1. Une fixture cohérente

- [x] 1.1 Remplacer la ligne 5 de `tests/fixtures/repo/policies/projets/a-4711/redis-7.journal.jsonl`
  (l'exception sur `redis:7.2.8`) par exactement cette ligne. L'exception lève désormais la raison
  de sa quarantaine, et son motif parle de licence :

  ~~~json
  {"ts":"2026-10-09T09:00:00Z","ref":"docker.io/library/redis:7.2.8","digest":"sha256:5b3e8f1c07a4d296e8b1f5c3a907d24e6b8f1a03c5d79e2b4f6a8c1d3e5079b2","state":"placed-by-exception","reason":"sbom/license-blocklist","ruleset":"sha256:9e2b7c1a4d0f6835b2e9c7a1d4f60b83e5c2a9d7f1b46e0c3a8d5f2b9e6c1a40","arbitration":{"by":"cao-data","date":"2026-10-09","reason":"Licence acceptée par le service juridique pour un usage interne."}}
  ~~~

- [x] 1.2 Lancer `uv run python -m pytest tests/test_orchestrator.py --no-cov -q`. Attendu : la
  dernière ligne finit par `passed`, sans `failed`. `test_refusal_line_has_the_journal_keys` lit
  la première `quarantine` (ligne 1), que rien ne touche.
- [x] 1.3 Commit :

  ~~~bash
  git add tests/fixtures/repo/policies/projets/a-4711/redis-7.journal.jsonl
  git commit -m "test: l'exception de la fixture lève la raison de sa quarantaine

  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  ~~~

## 2. Lire le journal, ou échouer en le disant

- [x] 2.1 Créer `tests/test_decisions.py` avec ces tests, qui échouent tant que le module manque :

  ~~~python
  """`uske decisions`: the journal read for a person, read-only."""

  from __future__ import annotations

  import contextlib
  import io
  import json
  import shutil
  import tempfile
  import unittest
  from datetime import date
  from pathlib import Path

  from uske import cli, decisions

  HERE = Path(__file__).parent
  GOLDEN = HERE / "golden"
  POLICY = HERE / "fixtures" / "repo" / "policies" / "projets" / "a-4711" / "redis-7.yaml"
  JOURNAL = POLICY.with_name("redis-7.journal.jsonl")
  R728 = "docker.io/library/redis:7.2.8"
  D726 = "sha256:1a4f0c9d2b7e5a83c6d1f9e0b4a72c58d3e6f1b09a4c7d2e5f8b1a0c3d6e9f2b"
  D1 = "sha256:" + "1" * 64
  S = "sha256:" + "a" * 64  # a source
  H = "sha256:" + "b" * 64  # the held image rebuilt from it


  def line(**fields) -> str:
      base = {"ts": "2026-10-01T00:00:00Z", "digest": D1, "state": "quarantine"}
      return json.dumps({**base, **fields})


  class Journal(unittest.TestCase):
      """A results directory holding the redis-7 fixture under the name the workflow gives it."""

      def setUp(self):
          self.dir = Path(tempfile.mkdtemp())
          self.addCleanup(shutil.rmtree, self.dir)
          shutil.copy(JOURNAL, self.dir / "a-4711-redis-7.jsonl")

      def write(self, name: str, *lines: str) -> Path:
          path = self.dir / name
          path.write_text("\n".join(lines) + "\n")
          return path

      def call(self, *argv: str) -> tuple[int, str, str]:
          out, err = io.StringIO(), io.StringIO()
          with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
              code = cli.main(["decisions", "--results", str(self.dir), *argv])
          return code, out.getvalue(), err.getvalue()


  class Read(Journal):
      def test_every_journal_tagged_with_its_policy_in_file_order(self):
          self.write("other.jsonl", line())
          lines, read = decisions.load(self.dir)
          self.assertEqual([l["policy"] for l in lines], ["a-4711-redis-7"] * 5 + ["other"])
          self.assertEqual(lines[0]["ts"], "2026-09-14T04:12:33Z")
          self.assertEqual(
              read,
              [f"{self.dir / 'a-4711-redis-7.jsonl'}: 5 lines", f"{self.dir / 'other.jsonl'}: 1 lines"],
          )

      def test_reports_and_other_files_are_not_read(self):
          (self.dir / "reports").mkdir()
          (self.dir / "reports" / "x.jsonl").write_text("not json\n")
          (self.dir / "a-4711-redis-7.jsonl~").write_text("not json\n")
          lines, _ = decisions.load(self.dir)
          self.assertEqual(len(lines), 5)

      def test_one_policy(self):
          self.write("other.jsonl", line())
          lines, _ = decisions.load(self.dir, "other")
          self.assertEqual([l["policy"] for l in lines], ["other"])

      def test_nothing_to_read_is_an_error(self):
          with self.assertRaisesRegex(decisions.JournalError, "uske-results volume"):
              decisions.load(self.dir / "missing")
          with self.assertRaisesRegex(decisions.JournalError, "present: a-4711-redis-7$"):
              decisions.load(self.dir, "redis-7")

      def test_an_unreadable_line_names_its_file_and_line(self):
          bad = {
              "not json": "{",
              "not an object": "[]",
              "missing state": json.dumps({"ts": "2026-10-01T00:00:00Z", "digest": D1}),
              "ts with an offset": line(ts="2026-10-09T09:00:00+02:00"),
              "reserved key": line(policy="x"),
              "ref not a string": line(ref=None),
              "state not a string": line(state=1),
          }
          for case, text in bad.items():
              with self.subTest(case):
                  path = self.write("bad.jsonl", line(), "", text)
                  with self.assertRaisesRegex(decisions.JournalError, f"^{path}:3: "):
                      decisions.read_journal(path)
  ~~~

- [x] 2.2 Lancer `uv run python -m pytest tests/test_decisions.py --no-cov -q`. Attendu : échec à la
  collecte, `ImportError: cannot import name 'decisions' from 'uske'`.
- [x] 2.3 Créer `uske/decisions.py` :

  ~~~python
  """Read the decision journal for a person (story 2): which decisions, on which image, and why.

  Read-only. Lines keep the file's order: the journal only grows, so the file is what happened,
  in the order it was written down (SDR-0016).
  """

  from __future__ import annotations

  import json
  from datetime import date, datetime
  from pathlib import Path

  from uske.outcomes import Outcome

  TS = "%Y-%m-%dT%H:%M:%SZ"
  REQUIRED = ("ts", "digest", "state")
  # the keys uske writes (results.ResultLine); any other key is rendered as found
  WRITTEN = ("ts", "ref", "digest", "state", "reason", "ruleset", "report", "source", "rebuilt")
  ADDED = ("policy", "backdated")  # what this module adds to a line
  STATES = {o.value for o in Outcome}


  class JournalError(Exception):
      """A journal that cannot be read in full: nothing is rendered."""


  def read_journal(path: Path) -> list[dict]:
      lines = []
      for number, raw in enumerate(path.read_text().splitlines(), 1):
          if not raw.strip():
              continue
          where = f"{path}:{number}"
          try:
              line = json.loads(raw)
          except json.JSONDecodeError as exc:
              raise JournalError(f"{where}: {exc.msg}") from exc
          if not isinstance(line, dict):
              raise JournalError(f"{where}: not a JSON object")
          missing = [k for k in REQUIRED if k not in line]
          if missing:
              raise JournalError(f"{where}: missing {', '.join(missing)}")
          for key in WRITTEN:  # what is rendered as text must be text (eng review, D16)
              if key in line and not isinstance(line[key], str):
                  raise JournalError(f"{where}: {key} must be a string")
          try:
              datetime.strptime(line["ts"], TS)
          except (TypeError, ValueError) as exc:
              raise JournalError(f"{where}: ts must be {TS}, got {line['ts']!r}") from exc
          if "policy" in line:
              raise JournalError(f"{where}: the key 'policy' is reserved")
          lines.append(line)
      return lines


  def load(results_dir: Path, policy: str | None = None) -> tuple[list[dict], list[str]]:
      """Every line of the journals, tagged with its policy, in file order; and what was read."""
      names = sorted(p.stem for p in results_dir.glob("*.jsonl") if p.is_file())
      if not names:
          raise JournalError(
              f"{results_dir}: no journal (*.jsonl) here;"
              " --results is the directory where the uske-results volume is mounted"
          )
      if policy is not None and policy not in names:
          raise JournalError(
              f"no journal for policy {policy!r}; present: {', '.join(names)}"
          )
      files = [results_dir / f"{n}.jsonl" for n in ([policy] if policy else names)]
      lines, read = [], []
      for path in files:
          found = read_journal(path)
          read.append(f"{path}: {len(found)} lines")
          lines.extend({"policy": path.stem, **line} for line in found)
      return annotate(lines), read


  def annotate(lines: list[dict]) -> list[dict]:
      """Mark a line dated before an earlier line of its (policy, digest): written later, backdated."""
      newest: dict[tuple[str, str], str] = {}
      out = []
      for line in lines:
          key = (line["policy"], line["digest"])
          if line["ts"] < newest.get(key, ""):
              line = {**line, "backdated": True}
          newest[key] = max(line["ts"], newest.get(key, ""))
          out.append(line)
      return out
  ~~~

- [x] 2.4 Lancer `uv run python -m pytest tests/test_decisions.py --no-cov -q`. Attendu :
  `5 passed`.
- [x] 2.5 Commit :

  ~~~bash
  git add uske/decisions.py tests/test_decisions.py
  git commit -m "feat: lire le journal en entier, ou dire où il est illisible

  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  ~~~

## 3. Choisir les décisions : image, état, date

- [x] 3.1 Ajouter à `tests/test_decisions.py`, avant toute autre classe de rendu :

  ~~~python
  class Select(Journal):
      def lines(self, **filters) -> list[dict]:
          return decisions.select(decisions.load(self.dir)[0], **filters)

      def test_by_reference(self):
          found = self.lines(image=R728)
          self.assertEqual([l["state"] for l in found], ["quarantine", "placed-by-exception"])

      def test_by_digest_with_or_without_repository(self):
          for image in (D726, f"docker.io/library/redis@{D726}"):
              with self.subTest(image):
                  found = self.lines(image=image)
                  self.assertEqual([l["state"] for l in found], ["quarantine", "abandoned"])

      def test_a_short_reference_matches_nothing(self):
          self.assertEqual(self.lines(image="redis:7.2.8"), [])

      def test_a_short_reference_gets_suggestions_never_matches(self):
          lines = decisions.load(self.dir)[0]
          self.assertEqual(decisions.suggest(lines, "redis:7.2.8"), [R728])
          self.assertEqual(decisions.suggest(lines, "nginx:1.27"), [])

      def test_a_source_by_its_reference_shows_its_rebuilds(self):
          self.write(
              "repair.jsonl",
              line(ref="hub/app:1", digest=S, state="transformation-required"),
              line(ref="transit/app:1-r", digest=H, source=S, report="r.html"),
              line(ref="hub/app:1", digest=S, rebuilt=H, reason="uske/rebuild-refused"),
          )
          found = self.lines(image="hub/app:1")
          self.assertEqual([l["digest"] for l in found], [S, H, S])
          self.assertEqual(found[1]["report"], "r.html")

      def test_state_and_since_add_up(self):
          found = self.lines(states={"placed-by-exception", "abandoned"}, since=date(2026, 9, 21))
          self.assertEqual(
              [(l["ts"], l["state"]) for l in found],
              [("2026-09-21T14:03:07Z", "abandoned"), ("2026-10-09T09:00:00Z", "placed-by-exception")],
          )

      def test_since_is_inclusive_on_the_utc_day(self):
          found = self.lines(since=date(2026, 10, 9))
          self.assertEqual([l["ts"] for l in found], ["2026-10-09T09:00:00Z"])

      def test_a_backdated_line_keeps_its_place_and_is_marked(self):
          self.write("late.jsonl", line(ts="2026-10-05T00:00:00Z"), line(ts="2026-10-02T00:00:00Z"))
          lines = decisions.load(self.dir, "late")[0]
          self.assertEqual([l.get("backdated") for l in lines], [None, True])
  ~~~

- [x] 3.2 Lancer `uv run python -m pytest tests/test_decisions.py --no-cov -q`. Attendu : les tests
  de `Select` échouent sur `AttributeError: module 'uske.decisions' has no attribute …`
  (`select` ou `suggest`), sauf `test_a_backdated_line_keeps_its_place_and_is_marked`, qui passe
  déjà.
- [x] 3.3 Ajouter à la fin de `uske/decisions.py` :

  ~~~python
  def digest_of(image: str) -> str | None:
      """The digest an argument names, if it names one: `sha256:…` or `<repository>@sha256:…`."""
      if "@" in image:
          return image.split("@", 1)[1]
      return image if image.startswith("sha256:") else None


  def select(
      lines: list[dict],
      image: str | None = None,
      states: set[str] | None = None,
      since: date | None = None,
  ) -> list[dict]:
      """The lines on an image (and on what was rebuilt from it), in a state, from a UTC day on."""
      if image is not None:
          digest = digest_of(image)
          # ponytail: exact match only; a short reference could name another repository
          wanted = {digest} if digest else {l["digest"] for l in lines if l.get("ref") == image}
          lines = [l for l in lines if wanted & {l["digest"], l.get("source"), l.get("rebuilt")}]
      if states is not None:
          lines = [l for l in lines if l["state"] in states]
      if since is not None:
          day = since.isoformat()
          lines = [l for l in lines if l["ts"][:10] >= day]
      return lines


  def suggest(lines: list[dict], image: str) -> list[str]:
      """Full references in the journal that end with `/<image>`: a hint, never a match."""
      return sorted({l["ref"] for l in lines if l.get("ref", "").endswith("/" + image)})
  ~~~

- [x] 3.4 Lancer `uv run python -m pytest tests/test_decisions.py --no-cov -q`. Attendu :
  `13 passed`.
- [x] 3.5 Commit :

  ~~~bash
  git add uske/decisions.py tests/test_decisions.py
  git commit -m "feat: retrouver les décisions sur une image, ses reconstructions, un état, une date

  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  ~~~

## 4. Le rendu texte

- [x] 4.1 Créer `tests/golden/decisions-redis-728.txt`, sans saut de ligne final :

  ~~~text
  == a-4711-redis-7 · docker.io/library/redis:7.2.8 · sha256:5b3e8f1c07a4d296e8b1f5c3a907d24e6b8f1a03c5d79e2b4f6a8c1d3e5079b2
  2026-10-06T04:10:00Z  quarantine  sbom/license-blocklist
      ruleset: sha256:9e2b7c1a4d0f6835b2e9c7a1d4f60b83e5c2a9d7f1b46e0c3a8d5f2b9e6c1a40
      report: regis/2026-10-06/redis-7.2.8.html
  2026-10-09T09:00:00Z  placed-by-exception  sbom/license-blocklist
      ruleset: sha256:9e2b7c1a4d0f6835b2e9c7a1d4f60b83e5c2a9d7f1b46e0c3a8d5f2b9e6c1a40
      arbitration: {"by": "cao-data", "date": "2026-10-09", "reason": "Licence acceptée par le service juridique pour un usage interne."}
  ~~~

- [x] 4.2 Ajouter à `tests/test_decisions.py` :

  ~~~python
  class Text(Journal):
      def test_golden(self):
          found = decisions.select(decisions.load(self.dir)[0], image=R728)
          expected = (GOLDEN / "decisions-redis-728.txt").read_text().rstrip("\n")
          self.assertEqual(decisions.render_text(found), expected)

      def test_one_group_per_policy_and_digest(self):
          self.write("b.jsonl", line(ref="r:1", state="placed-by-exception", arbitration={"by": "x"}))
          self.write("a.jsonl", line(ref="r:1"))
          text = decisions.render_text(decisions.load(self.dir)[0])
          self.assertIn(f"== a · r:1 · {D1}", text)
          self.assertIn(f"== b · r:1 · {D1}", text)

      def test_marks_and_missing_reason(self):
          self.write(
              "m.jsonl",
              line(ts="2026-10-05T00:00:00Z", state="direct-placement"),
              line(ts="2026-10-02T00:00:00Z", state="inconclusive", reason="uske/reopened"),
          )
          text = decisions.render_text(decisions.load(self.dir, "m")[0])
          self.assertIn("2026-10-05T00:00:00Z  direct-placement  —\n", text)
          self.assertIn("inconclusive  uske/reopened  [antidatée]  [arbitrage absent]", text)

      def test_source_and_rebuilt_are_shown(self):
          self.write("s.jsonl", line(source=S, rebuilt=H))
          text = decisions.render_text(decisions.load(self.dir, "s")[0])
          self.assertIn(f"    source: {S}\n    rebuilt: {H}", text)
  ~~~

- [x] 4.3 Lancer `uv run python -m pytest tests/test_decisions.py --no-cov -q`. Attendu : les quatre
  tests de `Text` échouent sur `AttributeError: … has no attribute 'render_text'`.
- [x] 4.4 Ajouter à la fin de `uske/decisions.py` :

  ~~~python
  def groups(lines: list[dict]) -> dict[tuple[str, str], list[dict]]:
      """(policy, digest) -> its lines, groups in the order of their first line."""
      out: dict[tuple[str, str], list[dict]] = {}
      for line in lines:
          out.setdefault((line["policy"], line["digest"]), []).append(line)
      return out


  def unsigned(line: dict) -> bool:
      """A decision uske did not take (another state, or a reopening), with nobody named for it."""
      by_hand = line["state"] not in STATES or line.get("reason") == "uske/reopened"
      return by_hand and "arbitration" not in line


  def marks(line: dict) -> list[str]:
      return [
          mark
          for mark, on in (("antidatée", line.get("backdated")), ("arbitrage absent", unsigned(line)))
          if on
      ]


  def extras(line: dict) -> list[str]:
      """`source`, `rebuilt` and every key uske does not write, as `key: value`, in file order."""
      return [
          f"{k}: {v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)}"
          for k, v in line.items()
          if k in ("source", "rebuilt") or (k not in WRITTEN and k not in ADDED)
      ]


  def render_text(lines: list[dict]) -> str:
      blocks = []
      for (policy, digest), group in groups(lines).items():
          out = [f"== {policy} · {group[0].get('ref', '—')} · {digest}"]
          for line in group:
              head = f"{line['ts']}  {line['state']}  {line.get('reason') or '—'}"
              out.append(head + "".join(f"  [{m}]" for m in marks(line)))
              out.extend(f"    {k}: {line[k]}" for k in ("ruleset", "report") if k in line)
              out.extend(f"    {e}" for e in extras(line))
          blocks.append("\n".join(out))
      return "\n\n".join(blocks)
  ~~~

- [x] 4.5 Lancer `uv run python -m pytest tests/test_decisions.py --no-cov -q`. Attendu :
  `17 passed`.
- [x] 4.6 Commit :

  ~~~bash
  git add uske/decisions.py tests/test_decisions.py tests/golden/decisions-redis-728.txt
  git commit -m "feat: rendre les décisions en texte, par politique et par empreinte

  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  ~~~

## 5. Le rendu Markdown, avec sa chronologie Mermaid

- [x] 5.1 Créer `tests/golden/decisions-redis-728.md`, sans saut de ligne final :

  ~~~~markdown
  ## a-4711-redis-7 · docker.io/library/redis:7.2.8

  `sha256:5b3e8f1c07a4d296e8b1f5c3a907d24e6b8f1a03c5d79e2b4f6a8c1d3e5079b2`

  ```mermaid
  timeline
      title docker.io/library/redis#58;7.2.8
      2026-10-06 : quarantine — sbom/license-blocklist
      2026-10-09 : placed-by-exception — sbom/license-blocklist
  ```

  | ts | state | reason | ruleset | report | details |
  | --- | --- | --- | --- | --- | --- |
  | 2026-10-06T04:10:00Z | quarantine | sbom/license-blocklist | sha256:9e2b7c1a4d0f6835b2e9c7a1d4f60b83e5c2a9d7f1b46e0c3a8d5f2b9e6c1a40 | `regis/2026-10-06/redis-7.2.8.html` (volume uske-results) |  |
  | 2026-10-09T09:00:00Z | placed-by-exception | sbom/license-blocklist | sha256:9e2b7c1a4d0f6835b2e9c7a1d4f60b83e5c2a9d7f1b46e0c3a8d5f2b9e6c1a40 |  | arbitration: {"by": "cao-data", "date": "2026-10-09", "reason": "Licence acceptée par le service juridique pour un usage interne."} |
  ~~~~

- [x] 5.2 Créer `tests/golden/decisions-escape.md`, sans saut de ligne final :

  ~~~~markdown
  ## p · r.example/a:1

  `sha256:1111111111111111111111111111111111111111111111111111111111111111`

  ```mermaid
  timeline
      title r.example/a#58;1
      2026-10-01 : placed-by-exception — r#58;1 #35;2#59; 3#37;#37; 4|5 6 : quarantine — —
  ```

  | ts | state | reason | ruleset | report | details |
  | --- | --- | --- | --- | --- | --- |
  | 2026-10-01T00:00:00Z | placed-by-exception | r:1 #2; 3%% 4\|5 6 | none |  | arbitration: {"by": "b", "reason": "x\|y\r\nz"} |
  | 2026-10-01T00:00:00Z | quarantine | — |  |  |  |
  ~~~~

- [x] 5.3 Ajouter à `tests/test_decisions.py` :

  ~~~python
  class Markdown(Journal):
      def test_golden(self):
          found = decisions.select(decisions.load(self.dir)[0], image=R728)
          expected = (GOLDEN / "decisions-redis-728.md").read_text().rstrip("\n")
          self.assertEqual(decisions.render_md(found), expected)

      def test_escapes_what_breaks_mermaid_and_tables(self):
          lines = [
              {
                  "policy": "p",
                  "ts": "2026-10-01T00:00:00Z",
                  "ref": "r.example/a:1",
                  "digest": D1,
                  "state": "placed-by-exception",
                  "reason": "r:1 #2; 3%% 4|5\n6",
                  "ruleset": "none",
                  "arbitration": {"by": "b", "reason": "x|y\r\nz"},
              },
              {"policy": "p", "ts": "2026-10-01T00:00:00Z", "digest": D1, "state": "quarantine"},
          ]
          expected = (GOLDEN / "decisions-escape.md").read_text().rstrip("\n")
          self.assertEqual(decisions.render_md(lines), expected)

      def test_marks_appear_in_the_timeline_and_the_table(self):
          self.write(
              "m.jsonl",
              line(ts="2026-10-05T00:00:00Z", state="direct-placement"),
              line(ts="2026-10-02T00:00:00Z", state="inconclusive", reason="uske/reopened"),
          )
          md = decisions.render_md(decisions.load(self.dir, "m")[0])
          self.assertIn("inconclusive — uske/reopened (antidatée) (arbitrage absent)", md)
          self.assertIn("|  | antidatée; arbitrage absent |", md)
  ~~~

  Dans la cellule `details`, `\r\n` est écrit tel quel, en deux séquences d'échappement JSON :
  `json.dumps` n'y laisse aucun vrai saut de ligne, et seul `|` reste à échapper.

- [x] 5.4 Lancer `uv run python -m pytest tests/test_decisions.py --no-cov -q`. Attendu : les trois
  tests de `Markdown` échouent sur `AttributeError: … has no attribute 'render_md'`.
- [x] 5.5 Ajouter, sous `STATES` dans `uske/decisions.py` :

  ~~~python
  # one pass, so an entity's own `#` and `;` are never escaped again
  MERMAID = str.maketrans(
      {"#": "#35;", "%": "#37;", ":": "#58;", ";": "#59;", "\r": " ", "\n": " "}
  )
  ~~~

  puis, à la fin du fichier :

  ~~~python
  def _cell(text: str) -> str:
      return text.replace("\r", " ").replace("\n", " ").replace("|", "\\|")


  def render_md(lines: list[dict]) -> str:
      blocks = []
      for (policy, digest), group in groups(lines).items():
          ref = group[0].get("ref", "—")
          out = [f"## {policy} · {ref}", "", f"`{digest}`", "", "```mermaid", "timeline"]
          out.append(f"    title {ref.translate(MERMAID)}")
          days: dict[str, list[str]] = {}
          for line in group:
              event = f"{line['state']} — {line.get('reason') or '—'}"
              event += "".join(f" ({m})" for m in marks(line))
              days.setdefault(line["ts"][:10], []).append(event.translate(MERMAID))
          out.extend(f"    {day} : " + " : ".join(events) for day, events in days.items())
          out += ["```", "", "| ts | state | reason | ruleset | report | details |"]
          out.append("| --- | --- | --- | --- | --- | --- |")
          for line in group:
              cells = [
                  line["ts"],
                  line["state"],
                  line.get("reason") or "—",
                  line.get("ruleset", ""),
                  # the ticket's reader cannot open it: say where it is
                  f"`{line['report']}` (volume uske-results)" if "report" in line else "",
                  "; ".join(extras(line) + marks(line)),
              ]
              out.append("| " + " | ".join(_cell(str(c)) for c in cells) + " |")
          blocks.append("\n".join(out))
      return "\n\n".join(blocks)
  ~~~

- [x] 5.6 Lancer `uv run python -m pytest tests/test_decisions.py --no-cov -q`. Attendu :
  `20 passed`.
- [ ] 5.7 Ouvrir `tests/golden/decisions-redis-728.md` dans l'aperçu Markdown de GitHub ou de
  l'éditeur (Mermaid activé). Attendu : une frise à deux dates, sans erreur de syntaxe Mermaid,
  puis le tableau à deux lignes.
- [x] 5.8 Commit :

  ~~~bash
  git add uske/decisions.py tests/test_decisions.py tests/golden/decisions-redis-728.md tests/golden/decisions-escape.md
  git commit -m "feat: rendre les décisions en Markdown, avec une chronologie Mermaid

  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  ~~~

## 6. La sous-commande

- [ ] 6.1 Ajouter à `tests/test_decisions.py` :

  ~~~python
  class Command(Journal):
      def test_json_by_default_with_the_policy(self):
          code, out, err = self.call(R728)
          found = json.loads(out)
          self.assertEqual(code, 0)
          self.assertEqual([l["state"] for l in found], ["quarantine", "placed-by-exception"])
          self.assertEqual({l["policy"] for l in found}, {"a-4711-redis-7"})
          self.assertIn("a-4711-redis-7.jsonl: 5 lines", err)

      def test_text_and_md(self):
          for fmt, golden in (("text", "decisions-redis-728.txt"), ("md", "decisions-redis-728.md")):
              with self.subTest(fmt):
                  code, out, _ = self.call(R728, "--format", fmt)
                  self.assertEqual((code, out), (0, (GOLDEN / golden).read_text().rstrip("\n") + "\n"))

      def test_one_policy_by_its_name(self):
          self.write("other.jsonl", line())
          code, out, _ = self.call("--policy-name", "a-4711-redis-7")
          self.assertEqual({l["policy"] for l in json.loads(out)}, {"a-4711-redis-7"})

      def test_an_unknown_policy_name_lists_the_present_ones(self):
          code, out, err = self.call("--policy-name", "redis-7")
          self.assertEqual((code, out), (1, ""))
          self.assertIn("present: a-4711-redis-7", err)

      def test_the_exceptions_of_a_period(self):
          code, out, _ = self.call("--state", "placed-by-exception,abandoned", "--since", "2026-09-21")
          self.assertEqual([l["state"] for l in json.loads(out)], ["abandoned", "placed-by-exception"])

      def test_nothing_matches(self):
          self.assertEqual(self.call("--state", "direct-placement")[:2], (0, "[]\n"))
          code, out, _ = self.call("--state", "direct-placement", "--format", "text")
          self.assertEqual((code, out), (0, ""))

      def test_a_short_reference_gets_the_full_one_on_stderr(self):
          code, out, err = self.call("redis:7.2.8")
          self.assertEqual((code, out), (0, "[]\n"))
          self.assertIn(f"did you mean: {R728}", err)

      def test_a_reference_nothing_extends_is_reminded(self):
          code, out, err = self.call("nginx:1.27")
          self.assertEqual((code, out), (0, "[]\n"))
          self.assertIn("full references", err)

      def test_a_bad_date_is_a_usage_error_that_says_the_form(self):
          err = io.StringIO()
          with self.assertRaises(SystemExit) as caught, contextlib.redirect_stderr(err):
              cli.main(["decisions", "--results", str(self.dir), "--since", "21/09/2026"])
          self.assertEqual(caught.exception.code, 2)
          self.assertIn("expected YYYY-MM-DD", err.getvalue())

      def test_unreadable_or_empty_is_a_technical_failure_with_nothing_on_stdout(self):
          self.write("bad.jsonl", line(), line(), "{")
          code, out, err = self.call()
          self.assertEqual((code, out), (1, ""))
          self.assertIn("bad.jsonl:3: ", err)
          empty = Path(tempfile.mkdtemp())
          self.addCleanup(shutil.rmtree, empty)
          self.dir = empty
          self.assertEqual(self.call()[0], 1)

      def test_the_journal_is_left_untouched(self):
          path = self.dir / "a-4711-redis-7.jsonl"
          before = (path.read_bytes(), path.stat().st_mtime_ns)
          self.call("--format", "md")
          self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)
  ~~~

- [ ] 6.2 Lancer `uv run python -m pytest tests/test_decisions.py --no-cov -q`. Attendu : les onze
  tests de `Command` échouent (`invalid choice: 'decisions'`, levé comme `SystemExit: 2`).
- [ ] 6.3 Dans `uske/cli.py`, remplacer la docstring du module par :

  ~~~python
  """One subcommand per workflow step, plus `decisions`, which reads the journal for a person.

  JSON on stdout unless asked otherwise. A business outcome is never an exit code: quarantine and
  inconclusive exit 0. Exit 1 is a technical failure (Argo retries it), exit 2 a usage error
  (argparse).
  """
  ~~~

- [ ] 6.4 Dans `uske/cli.py`, remplacer `from datetime import UTC, datetime` par
  `from datetime import UTC, date, datetime` (`date` sert à l'annotation de `_day`), et ajouter
  `decisions` à l'import groupé :
  `from uske import census, decisions, dtsync, gate, outcomes, playbooks, policies, results`.
- [ ] 6.5 Dans `uske/cli.py`, ajouter cette fonction juste avant `def parser(`:

  ~~~python
  def _day(text: str) -> date:
      try:
          return datetime.strptime(text, "%Y-%m-%d").date()
      except ValueError as exc:
          raise argparse.ArgumentTypeError(
              f"expected YYYY-MM-DD (a UTC day), got {text!r}"
          ) from exc


  def cmd_decisions(args) -> None:
      try:
          lines, read = decisions.load(Path(args.results), args.policy_name)
      except decisions.JournalError as exc:
          raise Failure(str(exc)) from exc
      for entry in read:
          print(entry, file=sys.stderr)
      states = set(args.state.split(",")) if args.state else None
      found = decisions.select(lines, args.image, states, args.since)
      if args.image and not found:
          close = decisions.suggest(lines, args.image)
          hint = (
              f"did you mean: {', '.join(close)}"
              if close
              else "the journal holds full references (docker.io/library/…) or digests"
          )
          print(f"no decision on {args.image}; {hint}", file=sys.stderr)
      if args.format == "json":
          _json(found)
      elif found:
          render = decisions.render_text if args.format == "text" else decisions.render_md
          print(render(found))
  ~~~

- [ ] 6.6 Dans `uske/cli.py`, dans `parser()`, juste avant `return p`, ajouter :

  ~~~python
      s = sub.add_parser(
          "decisions", help="read the journal for a person: which decisions, on which image, why"
      )
      s.add_argument("image", nargs="?", help="a full reference, a digest, or <repository>@sha256:…")
      s.add_argument(
          "--results", required=True, help="where the uske-results volume is mounted"
      )
      s.add_argument(
          "--policy-name", help="a policy's metadata.name: read its journal only"
      )
      s.add_argument(
          "--state", help="comma-separated, any state (e.g. placed-by-exception,abandoned)"
      )
      s.add_argument("--since", type=_day, help="YYYY-MM-DD, a UTC day, inclusive")
      s.add_argument("--format", choices=("json", "text", "md"), default="json")
      s.set_defaults(run=cmd_decisions)
  ~~~

- [ ] 6.7 Lancer `uv run python -m pytest tests/test_decisions.py --no-cov -q`. Attendu :
  `31 passed`.
- [ ] 6.8 Lancer `uv run uske decisions --help`. Attendu : l'aide liste `image`, `--results`,
  `--policy-name`, `--state`, `--since` et `--format {json,text,md}`.
- [ ] 6.9 Commit :

  ~~~bash
  git add uske/cli.py tests/test_decisions.py
  git commit -m "feat: uske decisions lit le journal pour l'équipe applicative et l'auditeur

  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  ~~~

## 7. La documentation

- [ ] 7.1 Dans `README.md`, section *Use*, remplacer le paragraphe qui commence par « One subcommand
  per workflow step » par :

  ~~~markdown
  One subcommand per workflow step, JSON on stdout: `list`, `prepare`, `pending`, `resolve`,
  `classify`, `record`, `approve`, then `dt-plan`, `dt-publish`, `dt-retire` and `census`.

  One more reads the journal for a person, and is not a workflow step: `decisions`.

  ### Why was an image not placed?

  The journal lives on the `uske-results` volume. Read it from a throwaway pod that mounts the
  volume read-only, in the namespace where the `CronWorkflow` runs, with the image it runs:

  ```bash
  NS=uske IMAGE=ghcr.io/trivoallan/uske:<version> REF=docker.io/library/redis:7.2.8
  kubectl -n "$NS" run uske-decisions --rm -i --restart=Never --image="$IMAGE" --overrides='{
    "spec": {
      "volumes": [{"name": "results", "persistentVolumeClaim": {"claimName": "uske-results", "readOnly": true}}],
      "containers": [{
        "name": "uske-decisions", "image": "'"$IMAGE"'",
        "args": ["decisions", "'"$REF"'", "--results", "/results", "--format", "md"],
        "volumeMounts": [{"name": "results", "mountPath": "/results", "readOnly": true}]
      }]
    }
  }'
  ```

  Paste the output into the ticket: a Mermaid timeline per image, then the full table, with the
  rule that refused it and who decided an exception. References are matched in full; a short one
  (`redis:7.2.8`) gets the full ones suggested. The volume is `ReadWriteOnce`: if a screening is
  running on another node, wait for it to finish.

  For the auditor, the same pod with other arguments:
  `decisions --state placed-by-exception,abandoned --since 2026-09-01 --results /results --format md`.
  ~~~

  Remplacer `ghcr.io/trivoallan/uske:<version>` et `NS=uske` par ce que la tâche 8 a réellement
  utilisé sur le banc, si cela diffère, avec `<version>` laissé en clair.

- [ ] 7.2 Dans `openspec/discovery.md`, story 2, remplacer la ligne `  - **Change** : _not yet proposed_`
  par `  - **Change** : \`decisions\` (sous-commande \`uske decisions\`)`.
- [ ] 7.3 Commit :

  ~~~bash
  git add README.md openspec/discovery.md
  git commit -m "docs: dire comment lire le journal avec uske decisions

  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  ~~~

## 8. Essayer la recette sur le banc, chronomètre en main

- [ ] 8.1 Lancer `deploy/kind/up.sh` depuis la branche du change. Attendu : il construit
  `uske:dev` depuis l'arbre courant (`up.sh`, `docker build … -t uske:dev`), un screening joué à
  la main va au bout, et le volume `uske-results` du namespace `uske` porte au moins un journal.
- [ ] 8.2 Retrouver une référence jugée :
  `kubectl -n uske logs -l workflows.argoproj.io/workflow --tail=-1 | grep -m1 '"ref"'`, ou
  reprendre celle d'une politique de `deploy/kind/policies/`. Attendu : une référence complète.
- [ ] 8.3 Dans un terminal neuf, démarrer un chronomètre, puis suivre la section *Why was an image
  not placed?* du `README.md` à la lettre, avec `NS=uske`, `IMAGE=uske:dev` et la référence de
  8.2. Arrêter le chronomètre quand le Markdown est copié.
  Attendu : le Markdown s'affiche, sans ligne de stderr mêlée à la frise ni au tableau.
  Si des lignes `…: N lines` s'y mêlent, ajouter à la recette ce qu'il faut pour les séparer,
  sans changer la commande.
- [ ] 8.4 Écrire dans ce fichier, sous cette tâche, le temps mesuré, le namespace et l'image
  utilisés, et ce qui a coincé. Objectif : 2 à 5 minutes (revue DX, D5). Au-delà, le dire dans la
  demande de fusion avec la cause.
- [ ] 8.5 Commit :

  ~~~bash
  git add README.md openspec/changes/decisions/tasks.md
  git commit -m "docs: recette d'accès au journal essayée sur le banc

  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  ~~~

## 9. Vérifier l'ensemble

- [ ] 9.1 Lancer `make test`. Attendu : aucun `failed`, et la ligne `Required test coverage of 90%
  reached`. Si `uske/decisions.py` n'est pas couvert en entier, lire les lignes manquantes dans
  `term-missing` et ajouter le test du scénario de spec correspondant.
- [ ] 9.2 Lancer `make lint`. Attendu : ruff sans erreur, puis `argo lint` sans erreur (les
  manifestes ne changent pas). Sans `kubectl` ni `argo` sur le poste, lancer `uv run ruff check .`
  et `uv run ruff format --check .`, attendu `All checks passed!` puis aucun fichier à reformater,
  et le noter dans la demande de fusion.
- [ ] 9.3 Lancer `openspec validate decisions --type change --strict`. Attendu :
  `Change 'decisions' is valid`.
- [ ] 9.4 Relire `review.md`, *Critère d'achèvement*, et cocher ce qui est tenu ; un point non tenu
  s'écrit dans la demande de fusion.
- [ ] 9.5 Commit, s'il reste un changement (formatage, coche de `review.md`) :

  ~~~bash
  git add -A uske tests openspec/changes/decisions
  git commit -m "chore: clore la revue du change decisions

  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  ~~~
