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
RUN = "uske-screening-1"
NO_META: dict = {}  # `archive(..., meta=NO_META)`: an archive from an older `uske export`


def line(digest: str, ts: str, state: str = "admitted", **extra: str) -> dict:
    return {
        "ts": ts,
        "ref": "docker.io/library/example:1.0",
        "digest": digest,
        "state": state,
        "ruleset": "sha256:" + "f" * 64,
        **extra,
    }


def run_cli(*argv: str) -> tuple[int, object, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(argv))
    text = out.getvalue().strip()
    return code, json.loads(text) if text else None, err.getvalue()


def write_journal(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(x) + "\n" for x in lines))


def archive(
    path: Path,
    members: dict[str, bytes],
    links: dict[str, str] | None = None,
    meta: dict | None = None,
):
    """A child's archive; `meta` defaults to a snapshot of 0 lines taken by `RUN`."""
    if meta is None:
        meta = {"snapshot_lines": 0, "run": RUN}
    if meta is not NO_META:
        members = {"meta.json": json.dumps(meta).encode(), **members}
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
        return run_cli("merge", "--results", str(self.results), "--from", str(self.out))


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
        archive(self.out / "alpha" / "1-child.tgz", {"lines.jsonl": jsonl(a)})
        archive(self.out / "beta" / "1-child.tgz", {"lines.jsonl": jsonl(b)})
        code, out, _ = self.merge()
        self.assertEqual((code, out), (0, {"alpha": 2, "beta": 2}))
        self.assertEqual(self.journal("alpha"), a)
        self.assertEqual(self.journal("beta")[1:], b)

    def test_replaying_the_merge_writes_nothing(self) -> None:
        """Scenario: Rejouer la fusion."""
        a = [
            line(D1, "2026-10-17T04:00:00Z", run=RUN),
            line(D2, "2026-10-17T04:00:01Z", run=RUN),
        ]
        archive(self.out / "alpha" / "1-child.tgz", {"lines.jsonl": jsonl(a)})
        self.assertEqual(self.merge()[:2], (0, {"alpha": 2}))
        self.assertEqual(self.merge()[:2], (0, {"alpha": 0}))
        self.assertEqual(self.journal("alpha"), a)

    def test_an_existing_report_is_not_overwritten(self) -> None:
        report = f"reports/alpha/{D1}/run-1.html"
        kept = self.results / report
        kept.parent.mkdir(parents=True)
        kept.write_text("first")
        new = f"reports/alpha/{D2}/run-1.html"
        rows = [line(D1, "2026-10-17T04:00:00Z", report="/results/" + report)]
        archive(
            self.out / "alpha" / "1-child.tgz",
            {"lines.jsonl": jsonl(rows), report: b"second", new: b"fresh"},
        )
        self.assertEqual(self.merge()[:2], (0, {"alpha": 1}))
        self.assertEqual(kept.read_text(), "first")
        self.assertEqual((self.results / new).read_text(), "fresh")
        self.assertEqual(sorted(p.name for p in kept.parent.iterdir()), ["run-1.html"])

    def test_a_name_out_of_dns_1123_is_refused(self) -> None:
        """review.md, finding 12: the name never leads out of the results directory."""
        good = [line(D1, "2026-10-17T04:00:00Z")]
        bad = ("bad..", "UPPER", "-x", "a" * 64)
        for name in bad:
            archive(self.out / name / "1-child.tgz", {"lines.jsonl": jsonl(good)})
        archive(self.out / "alpha" / "1-child.tgz", {"lines.jsonl": jsonl(good)})
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {"alpha": 1}))
        for name in bad:
            self.assertIn(f"error: {name}/1-child.tgz: ", err)
        self.assertIn("a DNS-1123 subdomain, at most 63 characters", err)
        self.assertEqual(
            sorted(p.name for p in self.results.iterdir()), ["alpha.jsonl"]
        )

    def test_a_member_out_of_its_directory_is_refused(self) -> None:
        """review.md, finding 12: an archive member never writes outside `<results>/reports/`."""
        good = jsonl([line(D1, "2026-10-17T04:00:00Z")])
        archive(
            self.out / "a1" / "1-child.tgz",
            {"lines.jsonl": good, "../../x": b"escaped"},
        )
        archive(
            self.out / "a2" / "1-child.tgz", {"lines.jsonl": good, "/tmp/x": b"escaped"}
        )
        archive(
            self.out / "a3" / "1-child.tgz",
            {"lines.jsonl": good, "reports/other/x": b"theirs"},
        )
        archive(
            self.out / "a4" / "1-child.tgz",
            {"lines.jsonl": good},
            links={"reports/a4/x": "/etc/passwd"},
        )
        archive(
            self.out / "a5" / "1-child.tgz",
            {"lines.jsonl": good, "reports/a5/../../x": b"escaped"},
        )
        archive(
            self.out / "a6" / "1-child.tgz",
            {"lines.jsonl": good, "notes.txt": b"stray"},
        )
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {}))
        for n in range(1, 7):
            self.assertIn(f"error: a{n}/1-child.tgz: refused member", err)
        self.assertFalse((self.root / "x").exists())
        self.assertEqual(
            list(self.results.iterdir()), []
        )  # checked whole: nothing written

    def test_an_unreadable_archive_fails_after_the_others(self) -> None:
        (self.out / "alpha").mkdir(parents=True)
        (self.out / "alpha" / "1-child.tgz").write_text("not a tarball")
        archive(self.out / "beta" / "1-child.tgz", {"lines.jsonl": b"{not json\n"})
        archive(
            self.out / "gamma" / "1-child.tgz", {"lines.jsonl": jsonl([{"digest": D1}])}
        )
        archive(
            self.out / "delta" / "1-child.tgz",
            {"lines.jsonl": jsonl([line(D1, "yesterday")])},
        )
        archive(
            self.out / "omega" / "1-child.tgz",
            {"lines.jsonl": jsonl([line(D1, "2026-10-17T04:00:00Z")])},
        )
        (self.out / "README").write_text("not an archive: ignored")
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {"omega": 1}))
        for name in ("alpha", "beta", "gamma", "delta"):
            self.assertIn(f"error: {name}/1-child.tgz: ", err)
        self.assertIn(
            "error: not merged: alpha/1-child.tgz, beta/1-child.tgz, delta/1-child.tgz, "
            "gamma/1-child.tgz",
            err,
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
            self.out / "alpha" / "1-child.tgz",
            {"lines.jsonl": jsonl([line(D1, "2026-10-17T04:00:00Z")])},
        )
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {}))
        self.assertIn("error: alpha/1-child.tgz: ", err)

    def test_a_read_only_journal_is_an_archive_error(self) -> None:
        path = results.path_for(self.results, "alpha")
        path.write_text("")
        path.chmod(0o444)  # readable, so the conflict check passes; append cannot write
        self.addCleanup(path.chmod, 0o644)
        archive(
            self.out / "alpha" / "1-child.tgz",
            {"lines.jsonl": jsonl([line(D1, "2026-10-17T04:00:00Z", run=RUN)])},
        )
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {}))
        self.assertIn("error: alpha/1-child.tgz: ", err)

    def test_a_symlinked_reports_directory_is_not_followed_out(self) -> None:
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        (self.results / "reports").symlink_to(elsewhere)
        rows = jsonl([line(D1, "2026-10-17T04:00:00Z")])
        archive(
            self.out / "alpha" / "1-child.tgz",
            {"lines.jsonl": rows, "reports/alpha/r.md": b"x"},
        )
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {}))
        self.assertIn("outside reports/", err)
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_directory_members_are_accepted(self) -> None:
        (self.out / "alpha").mkdir(parents=True)
        with tarfile.open(self.out / "alpha" / "1-child.tgz", "w:gz") as tar:
            info = tarfile.TarInfo("reports/alpha")
            info.type = tarfile.DIRTYPE
            tar.addfile(info)
            meta = json.dumps({"snapshot_lines": 0, "run": RUN}).encode()
            info = tarfile.TarInfo("meta.json")
            info.size = len(meta)
            tar.addfile(info, io.BytesIO(meta))
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
        return run_cli(
            "export",
            "--policy", str(STANDARD),
            "--results", str(self.child),
            "--snapshot-lines", str(snapshot),
            "--out", str(out or self.out / POLICY / "1-child.tgz"),
            "--run", RUN,
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
        with tarfile.open(self.out / POLICY / "1-child.tgz") as tar:
            self.assertEqual(
                sorted(tar.getnames()),
                sorted(["meta.json", "lines.jsonl", absolute, relative]),
            )
            self.assertEqual(
                json.loads(tar.extractfile("meta.json").read()),
                {"snapshot_lines": 1, "run": RUN},
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
        self.assertFalse((self.out / POLICY / "1-child.tgz").exists())

    def test_a_negative_snapshot_fails(self) -> None:
        code, _, err = self.export(-1)
        self.assertEqual(code, 1)
        self.assertIn("--snapshot-lines must be 0 or more", err)

    def test_an_empty_run_fails(self) -> None:
        with self.assertRaisesRegex(merge.ArchiveError, "--run must name"):
            merge.export(POLICY, self.child, 0, self.out / "x.tgz", "")

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


class Children(Dirs):
    """review I3 and M1: one archive per child, merged in the children's creation order."""

    def test_a_re_created_child_adds_an_archive(self) -> None:
        first = [line(D1, "2026-10-17T04:00:00Z", placed="sha256:" + "a" * 64, run=RUN)]
        second = [
            line(D2, "2026-10-17T04:10:00Z", run=RUN),
            line(D1, "2026-10-17T04:10:01Z", "quarantine", run=RUN),
        ]
        archive(
            self.out / "alpha" / "20261017T040000Z-alpha-x1.tgz",
            {"lines.jsonl": jsonl(first)},
        )
        archive(
            self.out / "alpha" / "20261017T041000Z-alpha-y2.tgz",
            {"lines.jsonl": jsonl(second)},
        )
        code, out, _ = self.merge()
        self.assertEqual((code, out), (0, {"alpha": 3}))
        self.assertEqual(self.journal("alpha"), first + second)
        self.assertEqual(self.merge()[:2], (0, {"alpha": 0}))

    def test_a_bad_archive_holds_back_the_later_ones_of_its_policy(self) -> None:
        archive(self.out / "alpha" / "1-x.tgz", {"lines.jsonl": b"{not json\n"})
        archive(
            self.out / "alpha" / "2-y.tgz",
            {"lines.jsonl": jsonl([line(D1, "2026-10-17T04:00:00Z")])},
        )
        archive(
            self.out / "beta" / "1-z.tgz",
            {"lines.jsonl": jsonl([line(D2, "2026-10-17T04:00:00Z")])},
        )
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {"beta": 1}))
        self.assertIn("error: not merged: alpha/1-x.tgz, alpha/2-y.tgz", err)
        self.assertEqual(self.journal("alpha"), [])

    def test_only_regular_files_are_archives(self) -> None:
        """M1: a missing optional input can show up as an empty directory."""
        (self.out / "alpha" / "1-x.tgz").mkdir(parents=True)
        (self.out / "empty").mkdir()
        (self.out / "stray.tgz").write_text("not under a policy: ignored")
        archive(
            self.out / "beta" / "1-z.tgz",
            {"lines.jsonl": jsonl([line(D2, "2026-10-17T04:00:00Z")])},
        )
        self.assertEqual(
            [(p, [f.name for f in fs]) for p, fs in merge.archives(self.out)],
            [("beta", ["1-z.tgz"])],
        )
        self.assertEqual(self.merge()[:2], (0, {"beta": 1}))


class Conflicts(Dirs):
    """review I1: a line written to the journal after the snapshot wins over the child's."""

    def setUp(self) -> None:
        super().setUp()
        self.before = [
            line(D1, "2026-10-16T00:00:00Z"),
            line(D2, "2026-10-16T00:00:01Z"),
        ]
        self.path = results.path_for(self.results, "alpha")
        write_journal(self.path, self.before)  # the snapshot: two lines
        self.meta = {"snapshot_lines": 2, "run": RUN}

    def add(self, *lines: dict) -> None:
        with self.path.open("a") as out:
            out.write("".join(json.dumps(x) + "\n" for x in lines))

    def test_a_verdict_written_by_hand_during_the_screening_wins(self) -> None:
        """Scenario: Un verdict écrit à la main pendant le screening l'emporte."""
        hand = line(D1, "2026-10-17T03:00:00Z", "quarantine", reason="arbitrated")
        self.add(hand)
        child = [
            line(D1, "2026-10-17T04:00:00Z", "admitted", run=RUN),
            line(
                D1,
                "2026-10-17T04:00:01Z",
                "admitted",
                run=RUN,
                placed="sha256:" + "a" * 64,
            ),
            line(D3, "2026-10-17T04:00:02Z", run=RUN),
        ]
        archive(
            self.out / "alpha" / "1-x.tgz",
            {"lines.jsonl": jsonl(child)},
            meta=self.meta,
        )
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {"alpha": 1}))
        self.assertEqual(self.journal("alpha"), [*self.before, hand, child[2]])
        self.assertEqual(results.last_states(self.journal("alpha"))[D1], "quarantine")
        self.assertEqual(err.count(f"alpha: conflict: {D1}: "), 2)
        self.assertIn(
            "the journal has quarantine (arbitrated) of 2026-10-17T03:00:00Z", err
        )
        self.assertIn("written by hand after the snapshot", err)
        self.assertIn("error: conflict in alpha", err)
        self.assertIn("remove the mark", err)
        self.assertNotIn(D3, err)

    def test_the_screenings_own_lines_are_no_conflict(self) -> None:
        """Scenario: Les lignes du même screening ne sont pas un conflit."""
        first = [line(D1, "2026-10-17T04:00:00Z", "quarantine", run=RUN)]
        second = [line(D1, "2026-10-17T04:10:00Z", "admitted", run=RUN)]
        archive(
            self.out / "alpha" / "1-x.tgz",
            {"lines.jsonl": jsonl(first)},
            meta=self.meta,
        )
        archive(
            self.out / "alpha" / "2-y.tgz",
            {"lines.jsonl": jsonl(second)},
            meta=self.meta,
        )
        code, out, err = self.merge()
        self.assertEqual((code, out, err), (0, {"alpha": 2}, ""))
        self.assertEqual(self.journal("alpha"), [*self.before, *first, *second])

    def test_another_runs_line_is_a_conflict(self) -> None:
        theirs = line(D1, "2026-10-17T03:00:00Z", "inconclusive", run="uske-other")
        self.add(theirs)
        child = [line(D1, "2026-10-17T04:00:00Z", "quarantine", run=RUN)]
        archive(
            self.out / "alpha" / "1-x.tgz",
            {"lines.jsonl": jsonl(child)},
            meta=self.meta,
        )
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {"alpha": 0}))
        self.assertIn("written by run uske-other after the snapshot", err)

    def test_a_hand_line_on_another_digest_does_not_block(self) -> None:
        hand = line(D2, "2026-10-17T03:00:00Z", "inconclusive", reason="uske/reopened")
        self.add(hand)
        child = [line(D1, "2026-10-17T04:00:00Z", "quarantine", run=RUN)]
        archive(
            self.out / "alpha" / "1-x.tgz",
            {"lines.jsonl": jsonl(child)},
            meta=self.meta,
        )
        code, out, err = self.merge()
        self.assertEqual((code, out, err), (0, {"alpha": 1}, ""))
        self.assertEqual(self.journal("alpha"), [*self.before, hand, *child])

    def test_a_conflict_keeps_the_mark(self) -> None:
        mark = self.results / merge.PENDING / RUN
        mark.parent.mkdir()
        mark.write_text("2026-10-17T00:00:00Z\n")
        self.add(line(D1, "2026-10-17T03:00:00Z", "quarantine"))
        child = [line(D1, "2026-10-17T04:00:00Z", run=RUN)]
        archive(
            self.out / "alpha" / "1-x.tgz",
            {"lines.jsonl": jsonl(child)},
            meta=self.meta,
        )
        args = ("merge", "--results", str(self.results), "--from", str(self.out))
        code, _, err = run_cli(*args, "--pending", RUN)
        self.assertEqual(code, 1)
        self.assertIn(
            f"remove the mark {self.results / merge.PENDING}/{RUN} by hand", err
        )
        self.assertEqual(merge.pending(self.results), [RUN])
        # a replay refuses the same lines again: the mark goes only by hand
        self.assertEqual(run_cli(*args, "--pending", RUN)[0], 1)
        self.assertEqual(merge.pending(self.results), [RUN])

    def test_an_archive_without_meta_is_refused(self) -> None:
        """Scenario: Une archive sans instantané est refusée."""
        child = jsonl([line(D3, "2026-10-17T04:00:00Z", run=RUN)])
        archive(self.out / "alpha" / "1-x.tgz", {"lines.jsonl": child}, meta=NO_META)
        archive(self.out / "beta" / "1-x.tgz", {"lines.jsonl": child})
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {"beta": 1}))
        self.assertIn("error: alpha/1-x.tgz: no meta.json: written by an older", err)
        self.assertEqual(self.journal("alpha"), self.before)

    def test_a_bad_meta_is_refused(self) -> None:
        child = jsonl([line(D3, "2026-10-17T04:00:00Z", run=RUN)])
        for n, meta in enumerate(
            ({"snapshot_lines": -1, "run": RUN}, {"snapshot_lines": "2", "run": RUN},
             {"snapshot_lines": 2, "run": ""}, {"snapshot_lines": True, "run": RUN})
        ):  # fmt: skip
            archive(self.out / f"p{n}" / "1-x.tgz", {"lines.jsonl": child}, meta=meta)
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {}))
        self.assertEqual(
            err.count("meta.json: needs snapshot_lines (0 or more) and run"), 4
        )

    def test_a_journal_shorter_than_the_snapshot_is_refused(self) -> None:
        child = jsonl([line(D3, "2026-10-17T04:00:00Z", run=RUN)])
        meta = {"snapshot_lines": 5, "run": RUN}
        archive(self.out / "alpha" / "1-x.tgz", {"lines.jsonl": child}, meta=meta)
        code, out, err = self.merge()
        self.assertEqual((code, out), (1, {}))
        self.assertIn("the journal has 2 lines, fewer than the snapshot's 5", err)
        self.assertEqual(self.journal("alpha"), self.before)


class Pending(Dirs):
    """review I2, scenario: Une fusion en souffrance bloque le screening suivant."""

    def setUp(self) -> None:
        super().setUp()
        self.listed = self.root / "listed.json"
        self.listed.write_text(
            json.dumps(
                [
                    {"name": "alpha", "path": "/work/repo/a.yaml"},
                    {"name": "beta", "path": "/work/repo/b.yaml"},
                ]
            )
        )
        write_journal(
            results.path_for(self.results, "alpha"),
            [line(D1, "2026-10-01T00:00:00Z"), line(D2, "2026-10-01T00:00:01Z")],
        )
        (self.results / "notes.txt").write_text("not a journal")

    def snapshot(self, run: str) -> tuple[int, object, str]:
        return run_cli(
            "snapshot",
            "--listed", str(self.listed),
            "--results", str(self.results),
            "--out", str(self.root / run / "snapshot"),
            "--expected", str(self.root / run / "expected.json"),
            "--run", run,
        )  # fmt: skip

    def test_snapshot_counts_marks_and_lists(self) -> None:
        code, out, _ = self.snapshot("uske-1")
        self.assertEqual(code, 0)
        self.assertEqual(
            [(p["name"], p["lines"]) for p in out], [("alpha", 2), ("beta", 0)]
        )
        self.assertEqual(out[0]["path"], "/work/repo/a.yaml")
        self.assertEqual(
            sorted(p.name for p in (self.root / "uske-1" / "snapshot").iterdir()),
            ["alpha.jsonl"],
        )
        self.assertEqual(
            json.loads((self.root / "uske-1" / "expected.json").read_text()),
            ["alpha", "beta"],
        )
        self.assertEqual(merge.pending(self.results), ["uske-1"])
        # its own retry finds its own mark: it goes on
        self.assertEqual(self.snapshot("uske-1")[0], 0)

    def test_a_pending_merge_blocks_the_next_screening(self) -> None:
        self.assertEqual(self.snapshot("uske-1")[0], 0)
        code, out, err = self.snapshot("uske-2")
        self.assertEqual((code, out), (1, None))
        self.assertIn("the merge of uske-1 is pending", err)
        self.assertIn("argo retry uske-1", err)
        self.assertFalse((self.root / "uske-2" / "expected.json").exists())
        self.assertEqual(merge.pending(self.results), ["uske-1"])

    def test_a_failed_merge_keeps_the_mark_a_merge_clears_it(self) -> None:
        self.assertEqual(self.snapshot("uske-1")[0], 0)
        archive(self.out / "alpha" / "1-x.tgz", {"lines.jsonl": b"{not json\n"})
        args = ("merge", "--results", str(self.results), "--from", str(self.out))
        self.assertEqual(run_cli(*args, "--pending", "uske-1")[0], 1)
        self.assertEqual(merge.pending(self.results), ["uske-1"])
        archive(
            self.out / "alpha" / "1-x.tgz",
            {"lines.jsonl": jsonl([line(D3, "2026-10-17T04:00:00Z", run=RUN)])},
        )
        self.assertEqual(run_cli(*args, "--pending", "uske-1")[:2], (0, {"alpha": 1}))
        self.assertEqual(merge.pending(self.results), [])
        self.assertEqual(self.snapshot("uske-2")[0], 0)
        # a replayed merge, its mark already gone, is fine
        self.assertEqual(run_cli(*args, "--pending", "uske-1")[:2], (0, {"alpha": 0}))

    def test_the_mark_is_never_read_as_a_journal(self) -> None:
        self.assertEqual(self.snapshot("uske-1")[0], 0)
        code, out, _ = run_cli(
            "decisions", "--results", str(self.results), "--format", "json"
        )
        self.assertEqual(code, 0)
        self.assertNotIn("uske-1", json.dumps(out))
        self.assertEqual(self.snapshot("uske-1")[0], 0)
        self.assertNotIn(
            merge.PENDING,
            [p.name for p in (self.root / "uske-1" / "snapshot").iterdir()],
        )

    def test_bad_inputs_fail(self) -> None:
        self.assertIn("not a Workflow name", self.snapshot("../x")[2])
        self.listed.write_text(json.dumps([{"name": "../x", "path": "p"}]))
        self.assertIn("not a policy name", self.snapshot("uske-1")[2])
        self.listed.write_text("{not json")
        self.assertEqual(self.snapshot("uske-1")[0], 1)
        self.assertEqual(merge.pending(self.results), [])
        code, _, err = run_cli(
            "merge", "--results", str(self.results), "--from", str(self.out),
            "--pending", "a/b",
        )  # fmt: skip
        self.assertEqual(code, 1)
        self.assertIn("not a Workflow name", err)

    def test_an_unwritable_mark_fails_the_merge(self) -> None:
        (self.results / merge.PENDING / "uske-1").mkdir(parents=True)
        code, _, err = run_cli(
            "merge", "--results", str(self.results), "--from", str(self.out),
            "--pending", "uske-1",
        )  # fmt: skip
        self.assertEqual(code, 1)
        self.assertIn("uske-1", err)


if __name__ == "__main__":
    unittest.main()
