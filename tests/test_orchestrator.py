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
from pathlib import Path

import yaml

from uske import cli, outcomes
from uske.outcomes import Outcome

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


def run(*argv: str) -> tuple[int, object]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = cli.main(list(argv))
    text = out.getvalue().strip()
    return code, json.loads(text) if text else None


def report(tier: str | None, rules: list[dict] | None = None) -> dict:
    return {"playbooks": [{"tier": tier, "rules": rules or []}]}


SECRET_FAILED = {"slug": "no-secret", "level": "critical", "passed": False, "status": "failed"}
SECRET_INCOMPLETE = {"slug": "no-secret", "level": "critical", "passed": False, "status": "incomplete"}


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

    def classify(self, playbook: Path, ref: str, digest: str, value, regis_exit: int = 0) -> dict:
        path = self.write(f"report-{digest[-4:]}.json", value) if value is not None else str(self.tmp / "absent.json")
        code, line = run("classify", "--playbook", str(playbook), "--ref", ref, "--digest", digest,
                         "--report", path, "--regis-exit", str(regis_exit))
        self.assertEqual(code, 0)
        return line


class ListAndResolve(unittest.TestCase):
    def test_list_skips_broken_file_and_exits_0(self):
        code, found = run("list", "--policies", str(FIXTURES))
        self.assertEqual(code, 0)
        self.assertEqual({p["name"] for p in found},
                         {"fixture-standard", "fixture-redistribution", "fixture-unknown"})

    def test_each_regime_gets_its_playbook(self):
        for fixture, expected in [("standard", FULL), ("redistribution", LIGHT)]:
            code, out = run("resolve", "--policy", str(FIXTURES / f"{fixture}.yaml"), "--playbooks", str(PLAYBOOKS))
            self.assertEqual(code, 0)
            self.assertEqual(Path(out["playbook"]), expected)

    def test_derogation_uses_the_light_tier(self):
        code, out = run("resolve", "--policy", str(ROOT / "policies/projets/a-4711/redis-7.yaml"),
                        "--playbooks", str(PLAYBOOKS))
        self.assertEqual(Path(out["playbook"]), LIGHT)

    def test_unknown_regime_has_no_playbook(self):
        code, out = run("resolve", "--policy", str(FIXTURES / "unknown.yaml"))
        self.assertEqual((code, out["playbook"]), (0, None))

    def test_unreadable_policy_is_a_technical_failure(self):
        code, _ = run("resolve", "--policy", str(FIXTURES / "broken.yaml"))
        self.assertEqual(code, 1)


class Classify(Workdir):
    def test_known_tiers(self):
        self.assertEqual(self.classify(LIGHT, "r:1", D1, report("Placement direct"))["state"], "direct-placement")
        line = self.classify(LIGHT, "r:1", D1, report("Quarantaine", [SECRET_FAILED]))
        self.assertEqual((line["state"], line["reason"]), ("quarantine", "secrets/verified-secrets"))
        line = self.classify(FULL, "r:1", D1, report("Transformation requise puis placement"))
        self.assertEqual(line["state"], "transformation-required")

    def test_fail_closed(self):
        cases = {
            "unknown tier": (report("Gold"), 0),
            "no tier": (report(None), 0),
            "incomplete critical rule": (report("Placement direct", [SECRET_INCOMPLETE]), 0),
            "empty report": ({}, 0),
            "no report": (None, 0),
            "regis failed": (report("Placement direct"), 3),
        }
        for name, (value, regis_exit) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.classify(LIGHT, "r:1", D1, value, regis_exit)["state"], "inconclusive")

    def test_the_recorded_report_is_the_one_that_survives(self):
        path = self.write("report.json", report("Quarantaine", [SECRET_FAILED]))
        durable = "/results/reports/pilote/abcdef.html"
        code, line = run("classify", "--playbook", str(LIGHT), "--ref", "r:1", "--digest", D1,
                         "--report", path, "--report-link", durable)
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


def plan(policy: str, ops: list[tuple[str, str]], kind: str = "import") -> dict:
    """A ReconcilePlan as `knock reconcile --plan-out` writes it: (tag, source digest) per op."""
    return {"apiVersion": "knock.io/v1alpha1", "kind": "ReconcilePlan", "operations": [
        {"policy": policy, "kind": kind, "destination": "harbor.example/shared-test/app", "tag": tag,
         "source": "harbor.example/producer/app", "sourceTag": tag, "sourceDigest": digest}
        for tag, digest in ops]}


class Pending(Workdir):
    def test_candidates_come_from_the_plan_by_digest(self):
        p = plan("fixture-redistribution", [("1.0", D1), ("latest", D1), ("1.1", D2)])
        p["operations"].append({**p["operations"][0], "policy": "another-policy", "sourceDigest": D3})
        _, todo = run("pending", "--policy", str(FIXTURES / "redistribution.yaml"),
                      "--plan", self.write("plan.json", p), "--results", str(self.results))
        self.assertEqual([c["digest"] for c in todo], [D1, D2])  # one per digest, this policy only
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
            (linedir / f"{digest[-4:]}.json").write_text(json.dumps(self.classify(LIGHT, "r:1", digest, None)))
        _, out = run("record", "--policy", str(FIXTURES / "standard.yaml"), "--results", str(self.results),
                     "--lines", str(linedir))
        self.assertEqual(out, {"written": 2})

    def test_refusal_line_has_the_journal_keys(self):
        journal = [json.loads(l) for l in JOURNAL.read_text().splitlines() if l.strip()]
        refusal = next(l for l in journal if l["state"] == "quarantine")
        line = self.classify(LIGHT, "r:1", D1, report("Quarantaine", [SECRET_FAILED]))
        self.assertEqual(set(line), set(refusal))

    def test_append_only_and_repeat_suppressed(self):
        policy = str(FIXTURES / "standard.yaml")
        first = self.classify(LIGHT, "r:1", D1, None)
        self.assertEqual(run("record", "--policy", policy, "--results", str(self.results),
                             "--lines", self.write("a.json", [first]))[1], {"written": 1})
        before = (self.results / "fixture-standard.jsonl").read_text()
        again = self.classify(LIGHT, "r:1", D1, None)
        self.assertEqual(run("record", "--policy", policy, "--results", str(self.results),
                             "--lines", self.write("b.json", [again]))[1], {"written": 0})
        placed = self.classify(LIGHT, "r:1", D1, report("Placement direct"))
        run("record", "--policy", policy, "--results", str(self.results), "--lines", self.write("c.json", placed))
        after = (self.results / "fixture-standard.jsonl").read_text()
        self.assertTrue(after.startswith(before))
        self.assertEqual(len(after.splitlines()), 2)


class Screening(Workdir):
    """A screening as the CronWorkflow runs it: knock's plan in, the approved plan out."""

    POLICY = "fixture-redistribution"

    def screening(self, policy_file: Path, ops: list[tuple[str, str]], verdicts: dict, name: str | None = None):
        policy = str(policy_file)
        plan_file = self.write("plan.json", plan(name or self.POLICY, ops))
        _, todo = run("pending", "--policy", policy, "--plan", plan_file, "--results", str(self.results))
        _, resolved = run("resolve", "--policy", policy, "--playbooks", str(PLAYBOOKS))
        calls = len(todo) if resolved["playbook"] else 0
        lines = []
        for c in todo:
            if resolved["playbook"]:
                lines.append(self.classify(Path(resolved["playbook"]), c["ref"], c["digest"], verdicts[c["digest"]]))
            else:
                _, line = run("classify", "--ref", c["ref"], "--digest", c["digest"])
                lines.append(line)
        if lines:
            run("record", "--policy", policy, "--results", str(self.results), "--lines", self.write("lines.json", lines))
        out = self.tmp / "approved.json"
        _, approved = run("approve", "--policy", policy, "--plan", plan_file, "--results", str(self.results),
                          "--out", str(out))
        applied = [op["tag"] for op in json.loads(out.read_text())["operations"]]
        return calls, approved, applied

    def results_of(self, name: str) -> list[dict]:
        path = self.results / f"{name}.jsonl"
        return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []

    def test_two_policies_each_get_their_playbook(self):
        self.screening(FIXTURES / "redistribution.yaml", [("1.0", D1)], {D1: report("Placement direct")})
        self.screening(FIXTURES / "standard.yaml", [("1.0", D1)], {D1: report("Placement direct")}, "fixture-standard")
        light = self.results_of("fixture-redistribution")[0]["ruleset"]
        full = self.results_of("fixture-standard")[0]["ruleset"]
        self.assertNotEqual(light, full)

    def test_only_direct_placement_is_approved(self):
        ops = [("1.0", D1), ("1.1", D2), ("1.2", D3)]
        verdicts = {D1: report("Transformation requise puis placement"),
                    D2: report("Quarantaine", [SECRET_FAILED]), D3: report("Gold")}
        _, approved, applied = self.screening(FIXTURES / "standard.yaml", ops, verdicts, "fixture-standard")
        self.assertEqual((approved, applied), ({"approved": 0}, []))
        self.assertEqual([l["state"] for l in self.results_of("fixture-standard")],
                         ["transformation-required", "quarantine", "inconclusive"])

    def test_unknown_regime_never_calls_regis(self):
        calls, approved, _ = self.screening(FIXTURES / "unknown.yaml", [("1", D1)], {}, "fixture-unknown")
        self.assertEqual((calls, approved), (0, {"approved": 0}))
        line = self.results_of("fixture-unknown")[0]
        self.assertEqual((line["state"], line["ruleset"]), ("inconclusive", "none"))

    def test_policy_without_candidate_records_nothing(self):
        _, out = run("record", "--policy", str(FIXTURES / "standard.yaml"), "--results", str(self.results),
                     "--lines", str(self.tmp / "no-such-dir"))
        self.assertEqual(out, {"written": 0})

    def test_empty_plan_does_nothing(self):
        self.screening(FIXTURES / "redistribution.yaml", [("1.0", D1)], {D1: report("Placement direct")})
        calls, approved, applied = self.screening(FIXTURES / "redistribution.yaml", [], {})
        self.assertEqual((calls, approved, applied), (0, {"approved": 0}, []))
        self.assertEqual(len(self.results_of(self.POLICY)), 1)

    def test_inconclusive_is_retried_and_approved(self):
        ops = [("1.0", D1)]
        self.screening(FIXTURES / "redistribution.yaml", ops, {D1: report("Placement direct", [SECRET_INCOMPLETE])})
        calls, approved, applied = self.screening(FIXTURES / "redistribution.yaml", ops, {D1: report("Placement direct")})
        self.assertEqual((calls, approved, applied), (1, {"approved": 1}, ["1.0"]))

    def test_failed_placement_is_approved_again_without_regis(self):
        ops = [("1.0", D1)]
        self.screening(FIXTURES / "redistribution.yaml", ops, {D1: report("Placement direct")})
        # knock failed to apply: the op is back in the next plan, already judged
        calls, _, applied = self.screening(FIXTURES / "redistribution.yaml", ops, {})
        self.assertEqual((calls, applied), (0, ["1.0"]))

    def test_republished_tag_is_withheld_until_judged(self):
        policy = FIXTURES / "redistribution.yaml"
        self.screening(policy, [("1.0", D1)], {D1: report("Placement direct")})
        _, _, applied = self.screening(policy, [("1.0", D2)], {D2: report("Quarantaine", [SECRET_FAILED])})
        self.assertEqual(applied, [])  # the new digest is refused: nothing to apply for 1.0


class NothingHardcoded(unittest.TestCase):
    def test_no_fixture_identifier_in_code(self):
        words = {"fixture-standard", "fixture-redistribution", "producer/app", "shared-test", "hub", "public"}
        for path in (HERE.parent / "uske").glob("*.py"):
            text = path.read_text()
            for word in words:
                with self.subTest(file=path.name, word=word):
                    self.assertIsNone(re.search(rf"['\"]{re.escape(word)}['\"]", text))


if __name__ == "__main__":
    unittest.main()
