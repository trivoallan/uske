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
        }
        for case, text in bad.items():
            with self.subTest(case):
                path = self.write("bad.jsonl", line(), "", text)
                with self.assertRaisesRegex(decisions.JournalError, f"^{path}:3: "):
                    decisions.read_journal(path)
