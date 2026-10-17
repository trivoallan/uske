"""`uske export` and `uske merge`: a screening spread over pods that share no volume.

Each test names the scenario of `specs/screening-fan-out/spec.md` (change
`screen-and-policy-fan-out`) it makes true, or the finding of its `review.md` it closes.
"""

from __future__ import annotations

import contextlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from uske import cli, merge, results

FIXTURES = Path(__file__).parent / "fixtures" / "policies"
STANDARD = FIXTURES / "standard.yaml"  # metadata.name: fixture-standard
POLICY = "fixture-standard"

D1, D2, D3 = ("sha256:" + c * 64 for c in "123")


def line(digest: str, ts: str, state: str = "admitted", **extra: str) -> dict:
    return {
        "ts": ts,
        "ref": "docker.io/library/example:1.0",
        "digest": digest,
        "state": state,
        "ruleset": "sha256:" + "f" * 64,
        **extra,
    }


def run(*argv: str) -> tuple[int, object, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(argv))
    text = out.getvalue().strip()
    return code, json.loads(text) if text else None, err.getvalue()


def write_journal(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(x) + "\n" for x in lines))


def archive(path: Path, members: dict[str, bytes], links: dict[str, str] | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path, "w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        for name, target in (links or {}).items():
            info = tarfile.TarInfo(name)
            info.type = tarfile.SYMTYPE
            info.linkname = target
            tar.addfile(info)


def jsonl(lines: list[dict]) -> bytes:
    return "".join(json.dumps(x) + "\n" for x in lines).encode()


class Dirs(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.results = self.root / "results"  # the journal volume
        self.out = self.root / "out"  # the children's archives
        self.results.mkdir()

    def journal(self, policy: str = POLICY) -> list[dict]:
        return results.read(results.path_for(self.results, policy))

    def merge(self) -> tuple[int, object, str]:
        return run("merge", "--results", str(self.results), "--from", str(self.out))


class Merge(Dirs):
    def test_two_policies_one_merge(self) -> None:
        """Scenario: Deux politiques, une fusion."""
        a = [line(D1, "2026-10-17T04:00:00Z"), line(D2, "2026-10-17T04:00:01Z")]
        b = [
            line(D3, "2026-10-17T04:00:02Z", "quarantine"),
            line(D1, "2026-10-17T04:00:03Z"),
        ]
        write_journal(
            results.path_for(self.results, "beta"), [line(D2, "2026-10-01T00:00:00Z")]
        )
        archive(self.out / "alpha.tgz", {"lines.jsonl": jsonl(a)})
        archive(self.out / "beta.tgz", {"lines.jsonl": jsonl(b)})
        code, out, _ = self.merge()
        self.assertEqual((code, out), (0, {"alpha": 2, "beta": 2}))
        self.assertEqual(self.journal("alpha"), a)
        self.assertEqual(self.journal("beta")[1:], b)

    def test_replaying_the_merge_writes_nothing(self) -> None:
        """Scenario: Rejouer la fusion."""
        a = [line(D1, "2026-10-17T04:00:00Z"), line(D2, "2026-10-17T04:00:01Z")]
        archive(self.out / "alpha.tgz", {"lines.jsonl": jsonl(a)})
        self.assertEqual(self.merge()[:2], (0, {"alpha": 2}))
        self.assertEqual(self.merge()[:2], (0, {"alpha": 0}))
        self.assertEqual(self.journal("alpha"), a)

    def test_a_line_written_by_hand_during_the_screening(self) -> None:
        """Scenario: Une ligne écrite à la main pendant le screening."""
        reopened = line(D1, "2026-10-17T05:00:00Z", "inconclusive", reason="reopened")
        write_journal(results.path_for(self.results, "alpha"), [reopened])
        child = [
            line(D1, "2026-10-17T04:00:00Z", "quarantine"),
            line(D2, "2026-10-17T04:00:01Z"),
        ]
        archive(self.out / "alpha.tgz", {"lines.jsonl": jsonl(child)})
        code, out, err = self.merge()
        self.assertEqual((code, out), (0, {"alpha": 1}))
        self.assertEqual(self.journal("alpha"), [reopened, child[1]])
        self.assertIn(f"stale: {D1} 2026-10-17T04:00:00Z", err)

    def test_an_existing_report_is_not_overwritten(self) -> None:
        report = f"reports/alpha/{D1}/run-1.html"
        kept = self.results / report
        kept.parent.mkdir(parents=True)
        kept.write_text("first")
        new = f"reports/alpha/{D2}/run-1.html"
        rows = [line(D1, "2026-10-17T04:00:00Z", report="/results/" + report)]
        archive(
            self.out / "alpha.tgz",
            {"lines.jsonl": jsonl(rows), report: b"second", new: b"fresh"},
        )
        self.assertEqual(self.merge()[:2], (0, {"alpha": 1}))
        self.assertEqual(kept.read_text(), "first")
        self.assertEqual((self.results / new).read_text(), "fresh")
        self.assertEqual(sorted(p.name for p in kept.parent.iterdir()), ["run-1.html"])

    def test_a_name_out_of_dns_1123_is_refused(self) -> None:
        """review.md, finding 12: the name never leads out of the results directory."""
        good = [line(D1, "2026-10-17T04:00:00Z")]
        for name in ("bad..tgz", "UPPER.tgz", "-x.tgz", ".tgz"):
            archive(self.out / name, {"lines.jsonl": jsonl(good)})
        archive(self.out / "alpha.tgz", {"lines.jsonl": jsonl(good)})
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {"alpha": 1}))
        for name in ("bad..tgz", "UPPER.tgz", "-x.tgz", ".tgz"):
            self.assertIn(f"error: {name}: ", err)
        self.assertEqual(
            sorted(p.name for p in self.results.iterdir()), ["alpha.jsonl"]
        )

    def test_a_member_out_of_its_directory_is_refused(self) -> None:
        """review.md, finding 12: an archive member never writes outside `<results>/reports/`."""
        good = jsonl([line(D1, "2026-10-17T04:00:00Z")])
        archive(self.out / "a1.tgz", {"lines.jsonl": good, "../../x": b"escaped"})
        archive(self.out / "a2.tgz", {"lines.jsonl": good, "/tmp/x": b"escaped"})
        archive(
            self.out / "a3.tgz", {"lines.jsonl": good, "reports/other/x": b"theirs"}
        )
        archive(
            self.out / "a4.tgz",
            {"lines.jsonl": good},
            links={"reports/a4/x": "/etc/passwd"},
        )
        archive(
            self.out / "a5.tgz", {"lines.jsonl": good, "reports/a5/../../x": b"escaped"}
        )
        archive(self.out / "a6.tgz", {"lines.jsonl": good, "notes.txt": b"stray"})
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {}))
        for n in range(1, 7):
            self.assertIn(f"error: a{n}.tgz: refused member", err)
        self.assertFalse((self.root / "x").exists())
        self.assertEqual(
            list(self.results.iterdir()), []
        )  # checked whole: nothing written

    def test_an_unreadable_archive_fails_after_the_others(self) -> None:
        self.out.mkdir()
        (self.out / "alpha.tgz").write_text("not a tarball")
        archive(self.out / "beta.tgz", {"lines.jsonl": b"{not json\n"})
        archive(self.out / "gamma.tgz", {"lines.jsonl": jsonl([{"digest": D1}])})
        archive(self.out / "delta.tgz", {"lines.jsonl": jsonl([line(D1, "yesterday")])})
        archive(
            self.out / "omega.tgz",
            {"lines.jsonl": jsonl([line(D1, "2026-10-17T04:00:00Z")])},
        )
        (self.out / "README").write_text("not an archive: ignored")
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {"omega": 1}))
        for name in ("alpha", "beta", "gamma", "delta"):
            self.assertIn(f"error: {name}.tgz: ", err)
        self.assertIn(
            "error: not merged: alpha.tgz, beta.tgz, delta.tgz, gamma.tgz", err
        )

    def test_no_archive_merges_nothing(self) -> None:
        self.assertEqual(self.merge()[:2], (0, {}))
        self.out.write_text("a file")
        code, _, err = self.merge()
        self.assertEqual(code, 1)
        self.assertIn("not a directory", err)

    def test_an_unwritable_journal_is_an_archive_error(self) -> None:
        path = results.path_for(self.results, "alpha")
        path.mkdir()  # a directory where the journal should be: append cannot write
        archive(
            self.out / "alpha.tgz",
            {"lines.jsonl": jsonl([line(D1, "2026-10-17T04:00:00Z")])},
        )
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {}))
        self.assertIn("error: alpha.tgz: ", err)

    def test_a_symlinked_reports_directory_is_not_followed_out(self) -> None:
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        (self.results / "reports").symlink_to(elsewhere)
        rows = jsonl([line(D1, "2026-10-17T04:00:00Z")])
        archive(
            self.out / "alpha.tgz", {"lines.jsonl": rows, "reports/alpha/r.md": b"x"}
        )
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {}))
        self.assertIn("outside reports/", err)
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_directory_members_are_accepted(self) -> None:
        self.out.mkdir()
        with tarfile.open(self.out / "alpha.tgz", "w:gz") as tar:
            info = tarfile.TarInfo("reports/alpha")
            info.type = tarfile.DIRTYPE
            tar.addfile(info)
            data = jsonl([line(D1, "2026-10-17T04:00:00Z")])
            info = tarfile.TarInfo("lines.jsonl")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        self.assertEqual(self.merge()[:2], (0, {"alpha": 1}))


class Export(Dirs):
    def setUp(self) -> None:
        super().setUp()
        self.child = self.root / "work" / "results"  # the child's copy of the journal
        self.journal_path = results.path_for(self.child, POLICY)

    def export(self, snapshot: int, out: Path | None = None) -> tuple[int, object, str]:
        return run(
            "export",
            "--policy", str(STANDARD),
            "--results", str(self.child),
            "--snapshot-lines", str(snapshot),
            "--out", str(out or self.out / f"{POLICY}.tgz"),
        )  # fmt: skip

    def test_export_then_merge(self) -> None:
        """Requirement: Un enfant juge sur un instantané du journal de sa politique."""
        old = line(D1, "2026-10-01T00:00:00Z", "quarantine")
        absolute = f"reports/{POLICY}/{D2}/run-1.html"
        relative = f"reports/{POLICY}/{D3}/run-1.md"
        new = [
            line(
                D1, "2026-10-16T00:00:00Z", "inconclusive"
            ),  # no report: nothing to pack
            line(D2, "2026-10-17T04:00:00Z", report="/results/" + absolute),
            line(D3, "2026-10-17T04:00:01Z", report=relative),
            line(
                D1,
                "2026-10-17T04:00:02Z",
                report=f"/results/reports/{POLICY}/{D1}/gone.md",
            ),
            line(D1, "2026-10-17T04:00:03Z", "inconclusive", report="/elsewhere/x.md"),
            line(
                D1,
                "2026-10-17T04:00:04Z",
                "quarantine",
                report=f"reports/{POLICY}/../x.md",
            ),
        ]
        write_journal(self.journal_path, [old, *new])
        for name, text in ((absolute, "html"), (relative, "md")):
            (self.child / name).parent.mkdir(parents=True, exist_ok=True)
            (self.child / name).write_text(text)
        (self.child / "reports" / "unrelated.md").write_text("never exported")
        write_journal(results.path_for(self.results, POLICY), [old])  # the snapshot

        code, out, err = self.export(1)
        self.assertEqual((code, out["exported"]), (0, 6))
        self.assertIn("gone.md: no such report", err)
        self.assertIn("/elsewhere/x.md: not under /results", err)
        self.assertIn(f"reports/{POLICY}/../x.md: not under reports/{POLICY}/", err)
        with tarfile.open(self.out / f"{POLICY}.tgz") as tar:
            self.assertEqual(
                sorted(tar.getnames()), sorted(["lines.jsonl", absolute, relative])
            )

        self.assertEqual(self.merge()[:2], (0, {POLICY: 6}))
        self.assertEqual(self.journal(), [old, *new])
        self.assertEqual((self.results / absolute).read_text(), "html")
        self.assertEqual((self.results / relative).read_text(), "md")

    def test_nothing_new_exports_an_empty_archive(self) -> None:
        write_journal(self.journal_path, [line(D1, "2026-10-01T00:00:00Z")])
        out = self.root / "deep" / "er" / "x.tgz"
        self.assertEqual(self.export(1, out)[:2], (0, {"exported": 0, "out": str(out)}))
        with tarfile.open(out) as tar:
            self.assertEqual(tar.extractfile("lines.jsonl").read(), b"")

    def test_fewer_lines_than_the_snapshot_fail(self) -> None:
        write_journal(self.journal_path, [line(D1, "2026-10-01T00:00:00Z")])
        code, _, err = self.export(2)
        self.assertEqual(code, 1)
        self.assertIn("the snapshot is not its prefix", err)
        self.assertFalse((self.out / f"{POLICY}.tgz").exists())

    def test_a_negative_snapshot_fails(self) -> None:
        code, _, err = self.export(-1)
        self.assertEqual(code, 1)
        self.assertIn("--snapshot-lines must be 0 or more", err)

    def test_an_unreadable_journal_fails(self) -> None:
        self.journal_path.parent.mkdir(parents=True)
        self.journal_path.write_text("{not json\n")
        self.assertEqual(self.export(0)[0], 1)

    def test_report_member_maps_the_mount_point(self) -> None:
        source, member = merge._report_member(
            f"/results/reports/{POLICY}/{D1}/r.html", self.child, POLICY
        )
        self.assertEqual(member, f"reports/{POLICY}/{D1}/r.html")
        self.assertEqual(source, self.child / member)


if __name__ == "__main__":
    unittest.main()
