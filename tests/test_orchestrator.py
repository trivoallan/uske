"""The subcommands one by one, then a screening replayed the way the workflow chains them.

`regis` and `knock` never run: a report is a JSON file written here, knock's plan is written
here in its ReconcilePlan shape, and "placing" is reading the approved plan.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

import yaml

from uske import cli, outcomes, results

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures" / "policies"
ROOT = HERE / "fixtures" / "repo"
PLAYBOOKS = ROOT / "playbooks"
JOURNAL = ROOT / "policies" / "projets" / "a-4711" / "redis-7.journal.jsonl"
FULL = PLAYBOOKS / "version" / "playbook.yaml"
LIGHT = PLAYBOOKS / "version" / "playbook-allege.yaml"

D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64
D3 = "sha256:" + "3" * 64
S1 = "sha256:" + "a" * 64  # held-image digests
S2 = "sha256:" + "b" * 64
S3 = "sha256:" + "c" * 64


def run(*argv: str) -> tuple[int, object]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = cli.main(list(argv))
    text = out.getvalue().strip()
    return code, json.loads(text) if text else None


def report(tier: str | None, rules: list[dict] | None = None) -> dict:
    return {"playbooks": [{"tier": tier, "rules": rules or []}]}


SECRET_FAILED = {
    "slug": "no-secret",
    "level": "critical",
    "passed": False,
    "status": "failed",
}
SECRET_INCOMPLETE = {
    "slug": "no-secret",
    "level": "critical",
    "passed": False,
    "status": "incomplete",
}


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class Workdir(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.results = self.tmp / "results"

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name: str, value) -> str:
        path = self.tmp / name
        path.write_text(json.dumps(value))
        return str(path)

    def classify(
        self, playbook: Path, ref: str, digest: str, value, regis_exit: int = 0
    ) -> dict:
        path = (
            self.write(f"report-{digest[-4:]}.json", value)
            if value is not None
            else str(self.tmp / "absent.json")
        )
        code, line = run(
            "classify",
            "--playbook",
            str(playbook),
            "--ref",
            ref,
            "--digest",
            digest,
            "--report",
            path,
            "--regis-exit",
            str(regis_exit),
        )
        self.assertEqual(code, 0)
        return line


class ListAndResolve(unittest.TestCase):
    def test_list_skips_broken_file_and_exits_0(self):
        code, found = run("list", "--policies", str(FIXTURES))
        self.assertEqual(code, 0)
        self.assertEqual(
            {p["name"] for p in found},
            {"fixture-standard", "fixture-redistribution", "fixture-unknown"},
        )

    def test_each_regime_gets_its_playbook(self):
        for fixture, expected in [("standard", FULL), ("redistribution", LIGHT)]:
            code, out = run(
                "resolve",
                "--policy",
                str(FIXTURES / f"{fixture}.yaml"),
                "--playbooks",
                str(PLAYBOOKS),
            )
            self.assertEqual(code, 0)
            self.assertEqual(Path(out["playbook"]), expected)

    def test_derogation_uses_the_light_tier(self):
        code, out = run(
            "resolve",
            "--policy",
            str(ROOT / "policies/projets/a-4711/redis-7.yaml"),
            "--playbooks",
            str(PLAYBOOKS),
        )
        self.assertEqual(code, 0)
        self.assertEqual(Path(out["playbook"]), LIGHT)

    def test_unknown_regime_has_no_playbook(self):
        code, out = run("resolve", "--policy", str(FIXTURES / "unknown.yaml"))
        self.assertEqual((code, out["playbook"]), (0, None))

    def test_unreadable_policy_is_a_technical_failure(self):
        code, _ = run("resolve", "--policy", str(FIXTURES / "broken.yaml"))
        self.assertEqual(code, 1)


class Classify(Workdir):
    def test_known_tiers(self):
        self.assertEqual(
            self.classify(LIGHT, "r:1", D1, report("Placement direct"))["state"],
            "direct-placement",
        )
        line = self.classify(LIGHT, "r:1", D1, report("Quarantaine", [SECRET_FAILED]))
        self.assertEqual(
            (line["state"], line["reason"]), ("quarantine", "secrets/verified-secrets")
        )
        line = self.classify(
            FULL, "r:1", D1, report("Transformation requise puis placement")
        )
        self.assertEqual(line["state"], "transformation-required")

    def test_fail_closed(self):
        cases = {
            "unknown tier": (report("Gold"), 0),
            "no tier": (report(None), 0),
            "incomplete critical rule": (
                report("Placement direct", [SECRET_INCOMPLETE]),
                0,
            ),
            "empty report": ({}, 0),
            "no report": (None, 0),
            "regis failed": (report("Placement direct"), 3),
        }
        for name, (value, regis_exit) in cases.items():
            with self.subTest(name):
                self.assertEqual(
                    self.classify(LIGHT, "r:1", D1, value, regis_exit)["state"],
                    "inconclusive",
                )

    def test_a_tier_missed_on_an_unfinished_rule_is_inconclusive(self):
        age_unread = {
            "slug": "freshness",
            "level": "warning",
            "passed": False,
            "status": "incomplete",
        }
        critical = {
            "slug": "cve-critical",
            "level": "critical",
            "passed": False,
            "status": "failed",
        }
        repair = "Transformation requise puis placement"
        line = self.classify(FULL, "r:1", D1, report(repair, [age_unread]))
        self.assertEqual(
            (line["state"], line["reason"]),
            ("inconclusive", "uske/better-tier-missed:freshness/age"),
        )
        # a rule that did fail decides, whatever else did not finish
        line = self.classify(FULL, "r:1", D2, report(repair, [critical, age_unread]))
        self.assertEqual(
            (line["state"], line["reason"]),
            ("transformation-required", "cve/cve-count"),
        )
        line = self.classify(
            FULL, "r:1", D3, report("Quarantaine", [SECRET_FAILED, age_unread])
        )
        self.assertEqual(line["state"], "quarantine")

    def test_the_recorded_report_is_the_one_that_survives(self):
        path = self.write("report.json", report("Quarantaine", [SECRET_FAILED]))
        durable = "/results/reports/pilote/abcdef.html"
        code, line = run(
            "classify",
            "--playbook",
            str(LIGHT),
            "--ref",
            "r:1",
            "--digest",
            D1,
            "--report",
            path,
            "--report-link",
            durable,
        )
        self.assertEqual((code, line["report"]), (0, durable))

    def test_without_a_link_the_read_path_is_recorded(self):
        line = self.classify(LIGHT, "r:1", D1, report("Quarantaine", [SECRET_FAILED]))
        self.assertTrue(line["report"].endswith(".json"))

    def test_an_unreadable_report_records_no_pointer(self):
        line = self.classify(LIGHT, "r:1", D1, None)
        self.assertNotIn("report", line)

    def test_ruleset_is_the_playbook_digest(self):
        line = self.classify(LIGHT, "r:1", D1, report("Placement direct"))
        self.assertRegex(line["ruleset"], r"^sha256:[0-9a-f]{64}$")

    def test_every_tier_of_the_real_playbooks_has_an_outcome(self):
        for path in (FULL, LIGHT):
            for tier in yaml.safe_load(path.read_text())["spec"]["tiers"]:
                with self.subTest(path=path.name, tier=tier["name"]):
                    self.assertIn(tier["name"], outcomes.TIERS)


def plan(
    policy: str,
    ops: list[tuple[str, str]],
    kind: str = "import",
    transformed: bool | None = None,
) -> dict:
    """A ReconcilePlan as `knock reconcile --plan-out` writes it: (tag, source digest) per op."""
    extra = {} if transformed is None else {"transformed": transformed}
    return {
        "apiVersion": "knock.io/v1alpha1",
        "kind": "ReconcilePlan",
        "operations": [
            {
                "policy": policy,
                "kind": kind,
                "destination": "harbor.example/shared-test/app",
                "tag": tag,
                "source": "harbor.example/producer/app",
                "sourceTag": tag,
                "sourceDigest": digest,
                **extra,
            }
            for tag, digest in ops
        ],
    }


def staged(policy: str, items: list[tuple[str, str, str]]) -> dict:
    """A StagedRebuilds as `knock reconcile --staged-out` writes it: (tag, source digest, held digest)."""
    return {
        "apiVersion": "knock.io/v1alpha1",
        "kind": "StagedRebuilds",
        "entries": [
            {
                "policy": policy,
                "import": "v1",
                "variant": "default",
                "kind": "import",
                "destination": "harbor.example/shared-test/app",
                "tag": tag,
                "source": "harbor.example/producer/app",
                "sourceTag": tag,
                "sourceDigest": source,
                "staged": "harbor.example/transit/shared-test/app",
                "stagedDigest": held,
                "aliases": [],
            }
            for tag, source, held in items
        ],
    }


class Pending(Workdir):
    def test_candidates_come_from_the_plan_by_digest(self):
        p = plan("fixture-redistribution", [("1.0", D1), ("latest", D1), ("1.1", D2)])
        p["operations"].append(
            {**p["operations"][0], "policy": "another-policy", "sourceDigest": D3}
        )
        _, todo = run(
            "pending",
            "--policy",
            str(FIXTURES / "redistribution.yaml"),
            "--plan",
            self.write("plan.json", p),
            "--results",
            str(self.results),
        )
        self.assertEqual(
            [c["digest"] for c in todo], [D1, D2]
        )  # one per digest, this policy only
        self.assertEqual(todo[0]["target"], f"harbor.example/producer/app@{D1}")
        self.assertEqual(todo[0]["key"], "1" * 16)


class Prepare(Workdir):
    def test_admit_on_the_working_copy_only(self):
        policy = FIXTURES / "redistribution.yaml"
        out = self.tmp / "work" / "policy.yaml"
        run("prepare", "--policy", str(policy), "--out", str(out))
        self.assertIs(yaml.safe_load(out.read_text())["spec"]["admit"], True)
        self.assertNotIn("admit", yaml.safe_load(policy.read_text())["spec"])


class Record(Workdir):
    def test_directory_of_lines(self):
        linedir = self.tmp / "lines"
        linedir.mkdir()
        for digest in (D1, D2):
            (linedir / f"{digest[-4:]}.json").write_text(
                json.dumps(self.classify(LIGHT, "r:1", digest, None))
            )
        _, out = run(
            "record",
            "--policy",
            str(FIXTURES / "standard.yaml"),
            "--results",
            str(self.results),
            "--lines",
            str(linedir),
        )
        self.assertEqual(out, {"written": 2})

    def test_refusal_line_has_the_journal_keys(self):
        journal = [json.loads(l) for l in JOURNAL.read_text().splitlines() if l.strip()]
        refusal = next(l for l in journal if l["state"] == "quarantine")
        line = self.classify(LIGHT, "r:1", D1, report("Quarantaine", [SECRET_FAILED]))
        self.assertEqual(set(line), set(refusal))

    def test_append_only_and_repeat_suppressed(self):
        policy = str(FIXTURES / "standard.yaml")
        first = self.classify(LIGHT, "r:1", D1, None)
        self.assertEqual(
            run(
                "record",
                "--policy",
                policy,
                "--results",
                str(self.results),
                "--lines",
                self.write("a.json", [first]),
            )[1],
            {"written": 1},
        )
        before = (self.results / "fixture-standard.jsonl").read_text()
        again = self.classify(LIGHT, "r:1", D1, None)
        self.assertEqual(
            run(
                "record",
                "--policy",
                policy,
                "--results",
                str(self.results),
                "--lines",
                self.write("b.json", [again]),
            )[1],
            {"written": 0},
        )
        placed = self.classify(LIGHT, "r:1", D1, report("Placement direct"))
        run(
            "record",
            "--policy",
            policy,
            "--results",
            str(self.results),
            "--lines",
            self.write("c.json", placed),
        )
        after = (self.results / "fixture-standard.jsonl").read_text()
        self.assertTrue(after.startswith(before))
        self.assertEqual(len(after.splitlines()), 2)

    def record_lines(self, lines) -> tuple[int, object]:
        return run(
            "record",
            "--policy",
            str(FIXTURES / "standard.yaml"),
            "--results",
            str(self.results),
            "--lines",
            self.write("in.json", lines),
        )

    def test_a_legacy_line_without_ts_is_the_oldest(self):
        self.results.mkdir(exist_ok=True)
        journal = self.results / "fixture-standard.jsonl"
        journal.write_text(json.dumps({"digest": D1, "state": "inconclusive"}) + "\n")
        line = {
            "ts": now(),
            "ref": "r:1",
            "digest": D1,
            "state": "quarantine",
            "ruleset": "x",
        }
        self.assertEqual(self.record_lines([line]), (0, {"written": 1}))

    def test_a_new_line_with_an_unreadable_ts_is_refused(self):
        self.results.mkdir(exist_ok=True)
        journal = self.results / "fixture-standard.jsonl"
        journal.write_text(
            json.dumps(
                {"ts": "2026-01-01T00:00:00Z", "digest": D1, "state": "inconclusive"}
            )
            + "\n"
        )
        before = journal.read_text()
        for bad in (
            "2026-10-10",
            None,
            "2026-10-10T00:00:00.5Z",
            "2026-10-10T00:00:00+00:00",
        ):
            line = {
                "ts": bad,
                "ref": "r:1",
                "digest": D1,
                "state": "quarantine",
                "ruleset": "x",
            }
            self.assertEqual(self.record_lines([line])[0], 1)
            self.assertEqual(journal.read_text(), before)
        self.assertEqual(
            self.record_lines([{"ref": "r:1", "digest": D1, "state": "quarantine"}])[0],
            1,
        )

    def test_the_guard_compares_with_the_newest_ts_not_the_last_line(self):
        self.results.mkdir(exist_ok=True)
        journal = self.results / "fixture-standard.jsonl"
        rows = [
            {
                "ts": "2026-03-01T00:00:00Z",
                "digest": D1,
                "state": "transformation-required",
            },
            {"ts": "2026-05-01T00:00:00Z", "digest": D1, "state": "quarantine"},
            {"ts": "2026-01-01T00:00:00Z", "digest": D1, "state": "abandoned"},
        ]  # added by hand, backdated
        journal.write_text("".join(json.dumps(r) + "\n" for r in rows))
        replay = {**rows[0], "ref": "r:1", "ruleset": "x"}
        self.assertEqual(self.record_lines([replay]), (0, {"written": 0, "stale": 1}))
        self.assertEqual(len(journal.read_text().splitlines()), 3)


class Screening(Workdir):
    """A screening as the CronWorkflow runs it: knock's plan in, the approved plan out."""

    POLICY = "fixture-redistribution"

    def screening(
        self,
        policy_file: Path,
        ops: list[tuple[str, str]],
        verdicts: dict,
        name: str | None = None,
    ):
        policy = str(policy_file)
        plan_file = self.write("plan.json", plan(name or self.POLICY, ops))
        _, todo = run(
            "pending",
            "--policy",
            policy,
            "--plan",
            plan_file,
            "--results",
            str(self.results),
        )
        _, resolved = run("resolve", "--policy", policy, "--playbooks", str(PLAYBOOKS))
        calls = len(todo) if resolved["playbook"] else 0
        lines = []
        for c in todo:
            if resolved["playbook"]:
                lines.append(
                    self.classify(
                        Path(resolved["playbook"]),
                        c["ref"],
                        c["digest"],
                        verdicts[c["digest"]],
                    )
                )
            else:
                _, line = run("classify", "--ref", c["ref"], "--digest", c["digest"])
                lines.append(line)
        if lines:
            run(
                "record",
                "--policy",
                policy,
                "--results",
                str(self.results),
                "--lines",
                self.write("lines.json", lines),
            )
        out = self.tmp / "approved.json"
        _, approved = run(
            "approve",
            "--policy",
            policy,
            "--plan",
            plan_file,
            "--results",
            str(self.results),
            "--out",
            str(out),
        )
        applied = [op["tag"] for op in json.loads(out.read_text())["operations"]]
        return calls, {"approved": approved["approved"]}, applied

    def results_of(self, name: str) -> list[dict]:
        path = self.results / f"{name}.jsonl"
        return (
            [json.loads(l) for l in path.read_text().splitlines()]
            if path.exists()
            else []
        )

    def test_two_policies_each_get_their_playbook(self):
        self.screening(
            FIXTURES / "redistribution.yaml",
            [("1.0", D1)],
            {D1: report("Placement direct")},
        )
        self.screening(
            FIXTURES / "standard.yaml",
            [("1.0", D1)],
            {D1: report("Placement direct")},
            "fixture-standard",
        )
        light = self.results_of("fixture-redistribution")[0]["ruleset"]
        full = self.results_of("fixture-standard")[0]["ruleset"]
        self.assertNotEqual(light, full)

    def test_only_direct_placement_is_approved(self):
        ops = [("1.0", D1), ("1.1", D2), ("1.2", D3)]
        verdicts = {
            D1: report("Transformation requise puis placement"),
            D2: report("Quarantaine", [SECRET_FAILED]),
            D3: report("Gold"),
        }
        _, approved, applied = self.screening(
            FIXTURES / "standard.yaml", ops, verdicts, "fixture-standard"
        )
        self.assertEqual((approved, applied), ({"approved": 0}, []))
        self.assertEqual(
            [l["state"] for l in self.results_of("fixture-standard")],
            ["transformation-required", "quarantine", "inconclusive"],
        )

    def test_unknown_regime_never_calls_regis(self):
        calls, approved, _ = self.screening(
            FIXTURES / "unknown.yaml", [("1", D1)], {}, "fixture-unknown"
        )
        self.assertEqual((calls, approved), (0, {"approved": 0}))
        line = self.results_of("fixture-unknown")[0]
        self.assertEqual((line["state"], line["ruleset"]), ("inconclusive", "none"))

    def test_policy_without_candidate_records_nothing(self):
        _, out = run(
            "record",
            "--policy",
            str(FIXTURES / "standard.yaml"),
            "--results",
            str(self.results),
            "--lines",
            str(self.tmp / "no-such-dir"),
        )
        self.assertEqual(out, {"written": 0})

    def test_empty_plan_does_nothing(self):
        self.screening(
            FIXTURES / "redistribution.yaml",
            [("1.0", D1)],
            {D1: report("Placement direct")},
        )
        calls, approved, applied = self.screening(
            FIXTURES / "redistribution.yaml", [], {}
        )
        self.assertEqual((calls, approved, applied), (0, {"approved": 0}, []))
        self.assertEqual(len(self.results_of(self.POLICY)), 1)

    def test_inconclusive_is_retried_and_approved(self):
        ops = [("1.0", D1)]
        self.screening(
            FIXTURES / "redistribution.yaml",
            ops,
            {D1: report("Placement direct", [SECRET_INCOMPLETE])},
        )
        calls, approved, applied = self.screening(
            FIXTURES / "redistribution.yaml", ops, {D1: report("Placement direct")}
        )
        self.assertEqual((calls, approved, applied), (1, {"approved": 1}, ["1.0"]))

    def test_failed_placement_is_approved_again_without_regis(self):
        ops = [("1.0", D1)]
        self.screening(
            FIXTURES / "redistribution.yaml", ops, {D1: report("Placement direct")}
        )
        # knock failed to apply: the op is back in the next plan, already judged
        calls, _, applied = self.screening(FIXTURES / "redistribution.yaml", ops, {})
        self.assertEqual((calls, applied), (0, ["1.0"]))

    def test_republished_tag_is_withheld_until_judged(self):
        policy = FIXTURES / "redistribution.yaml"
        self.screening(policy, [("1.0", D1)], {D1: report("Placement direct")})
        _, _, applied = self.screening(
            policy, [("1.0", D2)], {D2: report("Quarantaine", [SECRET_FAILED])}
        )
        self.assertEqual(
            applied, []
        )  # the new digest is refused: nothing to apply for 1.0


class Attempts(unittest.TestCase):
    def test_counts_held_images_since_the_last_line_on_the_source(self):
        held = lambda digest: {"digest": digest, "state": "inconclusive", "source": D1}
        own = {"digest": D1, "state": "transformation-required"}
        self.assertEqual(results.attempts([own, held(S1), held(S2)], D1), 2)
        self.assertEqual(results.attempts([own, held(S1), own, held(S2)], D1), 1)
        self.assertEqual(results.attempts([own, held(S1)], D2), 0)
        repaired = {"digest": S2, "state": "direct-placement", "source": D1}
        self.assertEqual(
            results.attempts([own, held(S1), repaired], D1), 1
        )  # a verdict is not an attempt

    def test_a_line_carries_its_source_and_its_rebuild(self):
        line = results.ResultLine(
            ts="t",
            ref="r",
            digest=D1,
            state="quarantine",
            ruleset="x",
            source=D2,
            rebuilt=S1,
        )
        self.assertEqual(
            (line.to_dict()["source"], line.to_dict()["rebuilt"]), (D2, S1)
        )


class Read(unittest.TestCase):
    def test_a_raw_line_separator_inside_a_value_stays_in_its_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.jsonl"
            path.write_text(
                f'{{"digest": "{D1}", "reason": "a\u2028b"}}\r\n\n', "utf-8"
            )
            self.assertEqual(results.read(path), [{"digest": D1, "reason": "a\u2028b"}])


class Rebuild(Workdir):
    """The second gate: a source to repair is rebuilt, its output judged, then promoted or closed."""

    POLICY = str(FIXTURES / "standard.yaml")
    NAME = "fixture-standard"
    SOURCE = "harbor.example/producer/app:1.0"
    HELD = "harbor.example/transit/shared-test/app:1.0"
    REPAIR = report("Transformation requise puis placement")

    def record(self, name: str, lines) -> int:
        return run(
            "record",
            "--policy",
            self.POLICY,
            "--results",
            str(self.results),
            "--lines",
            self.write(name, lines),
        )[1]["written"]

    def judge_source(self, digest: str, value) -> None:
        self.record(
            f"src-{digest[-4:]}.json", self.classify(FULL, self.SOURCE, digest, value)
        )

    def approve(self, value: dict, *extra: str) -> tuple[dict, list[str]]:
        out = self.tmp / "approved.json"
        _, result = run(
            "approve",
            "--policy",
            self.POLICY,
            "--plan",
            self.write("plan.json", value),
            "--results",
            str(self.results),
            "--out",
            str(out),
            *extra,
        )
        return result, [op["tag"] for op in json.loads(out.read_text())["operations"]]

    def journal(self) -> list[dict]:
        path = self.results / f"{self.NAME}.jsonl"
        return [json.loads(l) for l in path.read_text().splitlines()]

    def pending_held(self, value: dict | None) -> list[dict]:
        path = (
            self.write("staged.json", value)
            if value is not None
            else str(self.tmp / "absent.json")
        )
        return run(
            "pending",
            "--policy",
            self.POLICY,
            "--staged",
            path,
            "--results",
            str(self.results),
        )[1]

    def approve_held(self, value: dict | None) -> tuple[dict, list[dict]]:
        path = (
            self.write("staged.json", value)
            if value is not None
            else str(self.tmp / "absent.json")
        )
        out = self.tmp / "staged.approved.json"
        _, result = run(
            "approve",
            "--policy",
            self.POLICY,
            "--staged",
            path,
            "--results",
            str(self.results),
            "--out",
            str(out),
        )
        return result, json.loads(out.read_text())["entries"]

    def test_one_candidate_per_held_digest(self):
        value = staged(
            self.NAME, [("1.0", D1, S1), ("latest", D1, S1), ("1.1", D2, S2)]
        )
        value["entries"].append(
            {**value["entries"][0], "policy": "another-policy", "stagedDigest": S3}
        )
        todo = self.pending_held(value)
        self.assertEqual([c["digest"] for c in todo], [S1, S2])
        self.assertEqual(
            todo[0]["target"], f"harbor.example/transit/shared-test/app@{S1}"
        )
        self.assertEqual((todo[0]["source"], todo[0]["sourceRef"]), (D1, self.SOURCE))

    def test_no_staged_file_means_nothing_held(self):
        self.assertEqual(self.pending_held(None), [])
        self.assertEqual(self.approve_held(None), ({"approved": 0}, []))
        (self.tmp / "broken.json").write_text("{")
        self.assertEqual(
            run(
                "pending",
                "--policy",
                self.POLICY,
                "--staged",
                str(self.tmp / "broken.json"),
                "--results",
                str(self.results),
            )[0],
            1,
        )  # unreadable is still a failure

    def test_a_source_to_repair_needs_a_rebuild_and_a_transit(self):
        self.judge_source(D1, self.REPAIR)
        rebuilt = plan(self.NAME, [("1.0", D1)], transformed=True)
        self.assertEqual(self.approve(rebuilt, "--transit", "transit")[1], ["1.0"])
        self.assertEqual(
            self.approve(rebuilt), ({"approved": 0, "discarded": {"no-transit": 1}}, [])
        )
        self.assertEqual(
            self.approve(rebuilt, "--transit", "")[0]["discarded"], {"no-transit": 1}
        )  # what Argo passes when unset
        copied = plan(self.NAME, [("1.0", D1)], transformed=False)
        self.assertEqual(
            self.approve(copied, "--transit", "transit")[0]["discarded"],
            {"not-rebuilt": 1},
        )
        silent = plan(self.NAME, [("1.0", D1)])
        self.assertEqual(
            self.approve(silent, "--transit", "transit")[0]["discarded"],
            {"not-rebuilt": 1},
        )

    def test_a_sound_source_is_approved_rebuilt_or_not(self):
        self.judge_source(D1, report("Placement direct"))
        for transformed in (True, False, None):
            with self.subTest(transformed=transformed):
                value = plan(self.NAME, [("1.0", D1)], transformed=transformed)
                self.assertEqual(self.approve(value)[1], ["1.0"])

    def judge_held(self, source: str, held: str, value) -> list[dict]:
        path = self.write(f"held-{held[-4:]}.json", value)
        code, lines = run(
            "classify",
            "--playbook",
            str(FULL),
            "--ref",
            self.HELD,
            "--digest",
            held,
            "--report",
            path,
            "--source-ref",
            self.SOURCE,
            "--source-digest",
            source,
        )
        self.assertEqual(code, 0)
        return lines

    def test_a_held_image_names_both_its_source_ref_and_digest(self):
        path = self.write("held.json", self.REPAIR)
        base = [
            "classify",
            "--playbook",
            str(FULL),
            "--ref",
            self.HELD,
            "--digest",
            S1,
            "--report",
            path,
        ]
        self.assertEqual(run(*base, "--source-digest", D1)[0], 1)
        self.assertEqual(run(*base, "--source-ref", self.SOURCE)[0], 1)

    def test_both_lines_of_a_refused_rebuild_name_the_run(self):
        path = self.write("held-run.json", self.REPAIR)
        code, lines = run(
            "classify",
            "--playbook",
            str(FULL),
            "--ref",
            self.HELD,
            "--digest",
            S1,
            "--report",
            path,
            "--source-ref",
            self.SOURCE,
            "--source-digest",
            D1,
            "--run",
            "https://ci.example/runs/42",
        )
        self.assertEqual(code, 0)
        self.assertEqual([l["run"] for l in lines], ["https://ci.example/runs/42"] * 2)

    def test_no_run_writes_no_key(self):
        lines = self.judge_held(D1, S1, report("Placement direct"))
        self.assertNotIn("run", lines[0])

    def test_a_repaired_image_is_promoted_and_closes_nothing(self):
        self.judge_source(D1, self.REPAIR)
        lines = self.judge_held(D1, S1, report("Placement direct"))
        self.assertEqual(
            [(l["digest"], l["state"], l["source"]) for l in lines],
            [(S1, "direct-placement", D1)],
        )
        self.record("held.json", lines)
        value = staged(self.NAME, [("1.0", D1, S1), ("1.1", D2, S2)])
        result, kept = self.approve_held(value)
        self.assertEqual(result, {"approved": 1})
        self.assertEqual(
            kept, [value["entries"][0]]
        )  # handed back exactly as knock wrote it

    def test_a_refused_rebuild_closes_its_source(self):
        self.judge_source(D1, self.REPAIR)
        lines = self.judge_held(D1, S1, self.REPAIR)
        held, closing = lines
        self.assertEqual(
            (held["digest"], held["state"], held["source"]),
            (S1, "transformation-required", D1),
        )
        self.assertEqual(
            (closing["digest"], closing["ref"], closing["state"], closing["reason"]),
            (D1, self.SOURCE, "quarantine", "uske/rebuild-refused"),
        )
        self.assertEqual(
            (closing["rebuilt"], closing["ruleset"], closing["report"]),
            (S1, held["ruleset"], held["report"]),
        )
        self.assertEqual(self.record("held.json", lines), 2)
        self.assertEqual(
            self.record("held-again.json", lines), 0
        )  # replaying the second gate adds nothing
        self.assertEqual(
            self.approve_held(staged(self.NAME, [("1.0", D1, S1)])),
            ({"approved": 0}, []),
        )  # a refused rebuild is never promoted
        rebuilt = plan(self.NAME, [("1.0", D1)], transformed=True)
        self.assertEqual(
            self.approve(rebuilt, "--transit", "transit"),
            ({"approved": 0, "discarded": {"refused": 1}}, []),
        )
        todo = run(
            "pending",
            "--policy",
            self.POLICY,
            "--plan",
            self.write("plan.json", rebuilt),
            "--results",
            str(self.results),
        )[1]
        self.assertEqual(todo, [])  # a closed source is not judged again

    def test_a_first_gate_line_is_untouched(self):
        line = self.classify(FULL, self.SOURCE, D1, self.REPAIR)
        self.assertIsInstance(line, dict)
        self.assertNotIn("source", line)

    def test_a_silent_judge_is_retried_three_times_then_a_line_reopens(self):
        self.judge_source(D1, self.REPAIR)
        rebuilt = plan(self.NAME, [("1.0", D1)], transformed=True)
        for held in (S1, S2):
            lines = self.judge_held(D1, held, report(None))
            self.assertEqual(
                [l["state"] for l in lines], ["inconclusive"]
            )  # nothing closes
            self.record(f"held-{held[-4:]}.json", lines)
            self.assertEqual(
                self.approve_held(staged(self.NAME, [("1.0", D1, held)])),
                ({"approved": 0}, []),
            )  # no verdict, no promotion
            self.assertEqual(self.approve(rebuilt, "--transit", "transit")[1], ["1.0"])
        self.record("held-third.json", self.judge_held(D1, S3, report(None)))
        self.assertEqual(
            self.approve(rebuilt, "--transit", "transit"),
            ({"approved": 0, "discarded": {"attempts-exhausted": 1}}, []),
        )
        self.assertEqual(
            self.journal()[-1]["digest"], S3
        )  # nothing was written on the source

        reopen = {
            "ts": now(),
            "ref": self.SOURCE,
            "digest": D1,
            "state": "inconclusive",
            "ruleset": "none",
            "reason": "uske/reopened",
        }
        self.assertEqual(self.record("reopen.json", reopen), 1)
        todo = run(
            "pending",
            "--policy",
            self.POLICY,
            "--plan",
            self.write("plan.json", rebuilt),
            "--results",
            str(self.results),
        )[1]
        self.assertEqual([c["digest"] for c in todo], [D1])
        self.judge_source(D1, self.REPAIR)
        self.assertEqual(self.approve(rebuilt, "--transit", "transit")[1], ["1.0"])

    def test_replaying_the_first_gate_does_not_reopen_a_closed_source(self):
        original = self.classify(FULL, self.SOURCE, D1, self.REPAIR)
        original["ts"] = "2026-01-01T00:00:00Z"  # judged long before the rebuild
        self.record("src.json", original)
        self.record("held.json", self.judge_held(D1, S1, self.REPAIR))
        self.assertEqual(self.record("src-again.json", original), 0)
        self.assertEqual(
            run(
                "record",
                "--policy",
                self.POLICY,
                "--results",
                str(self.results),
                "--lines",
                self.write("src-again.json", original),
            )[1],
            {"written": 0, "stale": 1},
        )
        self.assertEqual(self.journal()[-1]["reason"], "uske/rebuild-refused")
        rebuilt = plan(self.NAME, [("1.0", D1)], transformed=True)
        self.assertEqual(self.approve(rebuilt, "--transit", "transit")[1], [])

    def test_repaired_images_do_not_exhaust_their_source(self):
        self.judge_source(D1, self.REPAIR)
        for held in (S1, S2, S3):
            self.record(
                f"held-{held[-4:]}.json",
                self.judge_held(D1, held, report("Placement direct")),
            )
        rebuilt = plan(self.NAME, [("1.0", D1)], transformed=True)
        self.assertEqual(self.approve(rebuilt, "--transit", "transit")[1], ["1.0"])

    def test_a_closed_source_reopens_by_the_same_line(self):
        self.judge_source(D1, self.REPAIR)
        self.record("held.json", self.judge_held(D1, S1, self.REPAIR))
        self.record(
            "reopen.json",
            {
                "ts": now(),
                "ref": self.SOURCE,
                "digest": D1,
                "state": "inconclusive",
                "ruleset": "none",
                "reason": "uske/reopened",
            },
        )
        self.judge_source(D1, self.REPAIR)
        rebuilt = plan(self.NAME, [("1.0", D1)], transformed=True)
        self.assertEqual(self.approve(rebuilt, "--transit", "transit")[1], ["1.0"])

    def test_a_sound_source_whose_rebuild_is_refused_is_closed_too(self):
        self.judge_source(D1, report("Placement direct"))
        self.record("held.json", self.judge_held(D1, S1, self.REPAIR))
        closing = self.journal()[-1]
        self.assertEqual(
            (closing["digest"], closing["reason"]), (D1, "uske/rebuild-refused")
        )
        self.assertEqual(closing["state"], "quarantine")
        rebuilt = plan(self.NAME, [("1.0", D1)], transformed=True)
        self.assertEqual(
            self.approve(rebuilt, "--transit", "transit")[1], []
        )  # closed, though the judge found it sound

    def test_a_quarantined_rebuild_closes_its_source_too(self):
        self.judge_source(D1, self.REPAIR)
        lines = self.judge_held(D1, S1, report("Quarantaine", [SECRET_FAILED]))
        self.assertEqual(
            [(l["digest"], l["state"]) for l in lines],
            [(S1, "quarantine"), (D1, "quarantine")],
        )
        self.assertEqual(lines[1]["reason"], "uske/rebuild-refused")
        self.record("held.json", lines)
        self.assertEqual(
            self.approve_held(staged(self.NAME, [("1.0", D1, S1)])),
            ({"approved": 0}, []),
        )

    def test_a_decided_held_image_is_not_judged_again(self):
        self.judge_source(D1, self.REPAIR)
        self.record("held.json", self.judge_held(D1, S1, report("Placement direct")))
        value = staged(self.NAME, [("1.0", D1, S1), ("1.1", D2, S2)])
        self.assertEqual([c["digest"] for c in self.pending_held(value)], [S2])

    def test_another_policy_s_held_images_are_never_handed_back(self):
        self.judge_source(D1, self.REPAIR)
        self.record("held.json", self.judge_held(D1, S1, report("Placement direct")))
        value = staged("another-policy", [("1.0", D1, S1)])
        self.assertEqual(self.approve_held(value), ({"approved": 0}, []))

    def test_the_bound_covers_a_sound_source_and_spares_a_copy(self):
        self.judge_source(D1, report("Placement direct"))
        for held in (S1, S2, S3):
            self.record(
                f"held-{held[-4:]}.json", self.judge_held(D1, held, report(None))
            )
        rebuilt = plan(self.NAME, [("1.0", D1)], transformed=True)
        self.assertEqual(
            self.approve(rebuilt)[0]["discarded"], {"attempts-exhausted": 1}
        )
        self.assertEqual(
            self.approve(plan(self.NAME, [("1.0", D1)], transformed=False))[1], ["1.0"]
        )


class NothingHardcoded(unittest.TestCase):
    def test_no_fixture_identifier_in_code(self):
        words = {
            "fixture-standard",
            "fixture-redistribution",
            "producer/app",
            "shared-test",
            "hub",
            "public",
        }
        for path in (HERE.parent / "uske").glob("*.py"):
            text = path.read_text()
            for word in words:
                with self.subTest(file=path.name, word=word):
                    self.assertIsNone(re.search(rf"['\"]{re.escape(word)}['\"]", text))


if __name__ == "__main__":
    unittest.main()
