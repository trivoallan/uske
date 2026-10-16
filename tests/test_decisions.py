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


def line(ensure_ascii: bool = True, **fields) -> str:
    base = {"ts": "2026-10-01T00:00:00Z", "digest": D1, "state": "quarantine"}
    return json.dumps({**base, **fields}, ensure_ascii=ensure_ascii)


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
        self.assertEqual(
            [l["policy"] for l in lines], ["a-4711-redis-7"] * 5 + ["other"]
        )
        self.assertEqual(lines[0]["ts"], "2026-09-14T04:12:33Z")
        self.assertEqual(
            read,
            [
                f"{self.dir / 'a-4711-redis-7.jsonl'}: 5 lines",
                f"{self.dir / 'other.jsonl'}: 1 lines",
            ],
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
            "ts not zero-padded": line(ts="2026-1-1T0:0:0Z"),
            "NaN": line().replace("}", ', "n": NaN}'),
        }
        for case, text in bad.items():
            with self.subTest(case):
                path = self.write("bad.jsonl", line(), "", text)
                with self.assertRaisesRegex(decisions.JournalError, f"^{path}:3: "):
                    decisions.read_journal(path)


class Select(Journal):
    def lines(self, **filters) -> list[dict]:
        return decisions.select(decisions.load(self.dir)[0], **filters)

    def test_by_reference(self):
        found = self.lines(image=R728)
        self.assertEqual(
            [l["state"] for l in found], ["quarantine", "placed-by-exception"]
        )

    def test_by_digest_with_or_without_repository(self):
        for image in (D726, f"docker.io/library/redis@{D726}"):
            with self.subTest(image):
                found = self.lines(image=image)
                self.assertEqual(
                    [l["state"] for l in found], ["quarantine", "abandoned"]
                )

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

    def test_a_rebuild_shows_its_source_and_its_siblings(self):
        h2 = "sha256:" + "c" * 64
        self.write(
            "family.jsonl",
            line(ref="hub/app:1", digest=S, state="transformation-required"),
            line(ref="transit/app:1-r", digest=H, source=S, state="direct-placement"),
            line(ref="transit/app:1-r", digest=h2, source=S, state="direct-placement"),
            line(ref="hub/other:2", digest=D1, state="direct-placement"),
        )
        for image in (H, h2, S):
            with self.subTest(image):
                found = self.lines(image=image)
                self.assertEqual([l["digest"] for l in found], [S, H, h2])

    def test_state_and_since_add_up(self):
        found = self.lines(
            states={"placed-by-exception", "abandoned"}, since=date(2026, 9, 21)
        )
        self.assertEqual(
            [(l["ts"], l["state"]) for l in found],
            [
                ("2026-09-21T14:03:07Z", "abandoned"),
                ("2026-10-09T09:00:00Z", "placed-by-exception"),
            ],
        )

    def test_since_is_inclusive_on_the_utc_day(self):
        found = self.lines(since=date(2026, 10, 9))
        self.assertEqual([l["ts"] for l in found], ["2026-10-09T09:00:00Z"])

    def test_a_backdated_line_keeps_its_place_and_is_marked(self):
        self.write(
            "late.jsonl",
            line(ts="2026-10-05T00:00:00Z"),
            line(ts="2026-10-02T00:00:00Z"),
        )
        lines = decisions.load(self.dir, "late")[0]
        self.assertEqual([l.get("backdated") for l in lines], [None, True])


class Text(Journal):
    def test_golden(self):
        found = decisions.select(decisions.load(self.dir)[0], image=R728)
        expected = (GOLDEN / "decisions-redis-728.txt").read_text().rstrip("\n")
        self.assertEqual(decisions.render_text(found), expected)

    def test_one_group_per_policy_and_digest(self):
        self.write(
            "b.jsonl",
            line(ref="r:1", state="placed-by-exception", arbitration={"by": "x"}),
        )
        self.write("a.jsonl", line(ref="r:1"))
        text = decisions.render_text(decisions.load(self.dir)[0])
        self.assertIn(f"== a · r:1 · {D1}", text)
        self.assertIn(f"== b · r:1 · {D1}", text)

    def test_marks_and_missing_reason(self):
        self.write(
            "m.jsonl",
            line(ts="2026-10-05T00:00:00Z", state="direct-placement"),
            line(
                ts="2026-10-02T00:00:00Z", state="inconclusive", reason="uske/reopened"
            ),
        )
        text = decisions.render_text(decisions.load(self.dir, "m")[0])
        self.assertIn("2026-10-05T00:00:00Z  direct-placement  —\n", text)
        self.assertIn(
            "inconclusive  uske/reopened  [antidatée]  [arbitrage absent]", text
        )

    def test_source_and_rebuilt_are_shown(self):
        self.write("s.jsonl", line(source=S, rebuilt=H))
        text = decisions.render_text(decisions.load(self.dir, "s")[0])
        self.assertIn(f"    source: {S}\n    rebuilt: {H}", text)


class Markdown(Journal):
    def test_the_volume_is_named_only_for_a_path_on_it(self):
        on_volume = {
            "policy": "p",
            "ts": "2026-10-01T00:00:00Z",
            "digest": D1,
            "state": "quarantine",
        }
        md = decisions.render_md([{**on_volume, "report": "/results/reports/p/x.html"}])
        self.assertIn("| `/results/reports/p/x.html` (volume uske-results) |", md)
        md = decisions.render_md([{**on_volume, "report": "results/reports/p/x.md"}])
        self.assertIn("| `results/reports/p/x.md` |", md)
        self.assertNotIn("volume", md)

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
            {
                "policy": "p",
                "ts": "2026-10-01T00:00:00Z",
                "digest": D1,
                "state": "quarantine",
            },
        ]
        expected = (GOLDEN / "decisions-escape.md").read_text().rstrip("\n")
        self.assertEqual(decisions.render_md(lines), expected)

    def test_marks_appear_in_the_timeline_and_the_table(self):
        self.write(
            "m.jsonl",
            line(ts="2026-10-05T00:00:00Z", state="direct-placement"),
            line(
                ts="2026-10-02T00:00:00Z", state="inconclusive", reason="uske/reopened"
            ),
        )
        md = decisions.render_md(decisions.load(self.dir, "m")[0])
        self.assertIn("inconclusive — uske/reopened (antidatée) (arbitrage absent)", md)
        self.assertIn("|  | antidatée; arbitrage absent |", md)


class Strict(Journal):
    def test_a_file_that_is_not_utf8_names_its_path(self):
        path = self.dir / "bin.jsonl"
        path.write_bytes(b"\xff\xfe\n")
        with self.assertRaisesRegex(decisions.JournalError, f"^{path}: "):
            decisions.read_journal(path)

    def test_u2028_in_a_value_does_not_split_the_line(self):
        path = self.dir / "sep.jsonl"
        path.write_text(
            line(reason="a\u2028b", ensure_ascii=False) + "\n", encoding="utf-8"
        )
        found = decisions.read_journal(path)
        self.assertEqual([l["reason"] for l in found], ["a\u2028b"])

    def test_crlf_line_endings_are_accepted(self):
        path = self.dir / "crlf.jsonl"
        path.write_bytes((line() + "\r\n" + line() + "\r\n").encode())
        self.assertEqual(len(decisions.read_journal(path)), 2)

    def test_a_newline_in_a_value_stays_on_one_line_in_text(self):
        self.write("n.jsonl", line(ref="x\ny", reason="a\nb", report="c\rd"))
        text = decisions.render_text(decisions.load(self.dir, "n")[0])
        self.assertIn("quarantine  a b\n", text)
        self.assertIn("== n · x y · ", text)
        self.assertIn("    report: c d", text)
        self.assertEqual(len(text.split("\n")), 3)

    def test_a_newline_in_a_ref_cannot_make_a_second_heading_in_md(self):
        self.write("n.jsonl", line(ref="x\n## z"))
        md = decisions.render_md(decisions.load(self.dir, "n")[0])
        self.assertEqual(
            [l for l in md.split("\n") if l.startswith("## ")], ["## n · x ## z"]
        )

    def test_who_is_unsigned(self):
        self.assertTrue(decisions.unsigned(json.loads(line(state="abandoned"))))
        self.assertFalse(
            decisions.unsigned(
                json.loads(line(reason="uske/reopened", arbitration={"by": "x"}))
            )
        )

    def test_a_raw_carriage_return_becomes_a_space(self):
        self.assertEqual("a\rb".translate(decisions.MERMAID), "a b")
        self.assertEqual(decisions._cell("a\rb"), "a b")


class Command(Journal):
    def test_json_by_default_with_the_policy(self):
        code, out, err = self.call(R728)
        found = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(
            [l["state"] for l in found], ["quarantine", "placed-by-exception"]
        )
        self.assertEqual({l["policy"] for l in found}, {"a-4711-redis-7"})
        self.assertIn("a-4711-redis-7.jsonl: 5 lines", err)

    def test_text_and_md(self):
        for fmt, golden in (
            ("text", "decisions-redis-728.txt"),
            ("md", "decisions-redis-728.md"),
        ):
            with self.subTest(fmt):
                code, out, _ = self.call(R728, "--format", fmt)
                self.assertEqual(
                    (code, out), (0, (GOLDEN / golden).read_text().rstrip("\n") + "\n")
                )

    def test_one_policy_by_its_name(self):
        self.write("other.jsonl", line())
        _code, out, _ = self.call("--policy-name", "a-4711-redis-7")
        self.assertEqual({l["policy"] for l in json.loads(out)}, {"a-4711-redis-7"})

    def test_an_unknown_policy_name_lists_the_present_ones(self):
        code, out, err = self.call("--policy-name", "redis-7")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("present: a-4711-redis-7", err)

    def test_the_exceptions_of_a_period(self):
        _code, out, _ = self.call(
            "--state", "placed-by-exception, abandoned", "--since", "2026-09-21"
        )
        self.assertEqual(
            [l["state"] for l in json.loads(out)], ["abandoned", "placed-by-exception"]
        )

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
        code, out, err = self.call()
        self.assertEqual((code, out), (1, ""))
        self.assertIn("error:", err)

    def test_the_journal_is_left_untouched(self):
        path = self.dir / "a-4711-redis-7.jsonl"
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        self.call("--format", "md")
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)
