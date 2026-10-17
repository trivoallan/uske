"""`uske screen`, driven against fake `regis` and `knock` (tests/fakes) that write frozen files.

Each test names the scenario of `specs/screen-command/spec.md` (change
`screen-and-policy-fan-out`) it makes true.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shlex
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uske import cli, policies, screen

HERE = Path(__file__).parent
FAKES = HERE / "fakes"
FIXTURES = HERE / "fixtures" / "policies"
PLAYBOOKS = HERE / "fixtures" / "repo" / "playbooks"
STANDARD = FIXTURES / "standard.yaml"
REDISTRIBUTION = FIXTURES / "redistribution.yaml"
UNKNOWN = FIXTURES / "unknown.yaml"

D1, D2, D3, D4, D5 = ("sha256:" + c * 64 for c in "12345")
EPOCH = "20261017T040000Z"


def held(source: str) -> str:
    """The digest the fake knock gives the image it repairs from `source`."""
    return "sha256:" + hashlib.sha256(f"held:{source}".encode()).hexdigest()


def placed(source: str) -> str:
    return "sha256:" + hashlib.sha256(f"placed:{source}".encode()).hexdigest()


def without_ts(lines: list[dict]) -> list[dict]:
    return [{k: v for k, v in line.items() if k != "ts"} for line in lines]


class Fakes(unittest.TestCase):
    """A temporary directory, the fakes first on PATH, and their calls logged."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(
            self._tmp.cleanup
        )  # last: other cleanups may need the directory
        self.tmp = Path(self._tmp.name)
        self.results = self.tmp / "results"
        self.work = self.tmp / "work"
        self.calls_file = self.tmp / "calls.log"
        self.env = {
            "PATH": f"{FAKES}{os.pathsep}{os.environ['PATH']}",
            "FAKE_CALLS": str(self.calls_file),
            "FAKE_VERDICTS": "{}",
            "FAKE_FAIL": "",
        }
        for name in ("USKE_REGIS_CMD", "USKE_KNOCK_CMD", "USKE_AFTER_RECORD"):
            self.env[name] = ""
        patcher = mock.patch.dict(os.environ, self.env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def verdicts(self, **by_digest: str) -> None:
        os.environ["FAKE_VERDICTS"] = json.dumps(by_digest)

    def screen(self, *argv: str) -> tuple[int, list[dict], str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(
                [
                    "screen",
                    "--results",
                    str(self.results),
                    "--work",
                    str(self.work),
                    "--playbooks",
                    str(PLAYBOOKS),
                    "--epoch",
                    EPOCH,
                    *argv,
                ]
            )
        lines = [json.loads(line) for line in out.getvalue().splitlines() if line]
        return code, lines, err.getvalue()

    def calls(self) -> list[str]:
        if not self.calls_file.exists():
            return []
        return self.calls_file.read_text().splitlines()

    def journal(self, name: str) -> list[dict]:
        path = self.results / f"{name}.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines()]


def step(*argv: str) -> object:
    """One workflow step, as the `uske` template runs it."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = cli.main(list(argv))
    assert code == 0, argv
    text = out.getvalue().strip()
    return json.loads(text) if text else None


def tool(*argv: str) -> int:
    """`regis` or `knock`, as their templates run them."""
    return subprocess.run(list(argv), check=False, capture_output=True).returncode


class Parity(Fakes):
    """*Les mêmes lignes que les étapes*."""

    def steps(self, policy_file: Path, results: Path, work: Path, run: str) -> None:
        """The `policy` template of deploy/base/workflowtemplate.yaml, step by step."""
        path = str(policy_file)
        name = policies.load(policy_file).name
        directory = work / "policies" / name
        for d in ("plans", "staged", "applied", "approve-lines"):
            (work / d).mkdir(parents=True, exist_ok=True)
        plan, approved = (
            work / "plans" / f"{name}.json",
            work / "plans" / f"{name}.approved.json",
        )
        staged = work / "staged" / f"{name}.json"
        staged_approved = work / "staged" / f"{name}.approved.json"
        applied = work / "applied" / f"{name}.json"
        approve_lines = work / "approve-lines" / f"{name}.json"
        # prepare
        step("prepare", "--policy", path, "--out", str(directory / "policy.yaml"))
        # plan
        tool("knock", "reconcile", str(directory), "--plan-out", str(plan))
        # pending, resolve
        todo = step(
            "pending", "--policy", path, "--plan", str(plan), "--results", str(results)
        )
        resolved = step("resolve", "--policy", path, "--playbooks", str(PLAYBOOKS))

        def evaluate(item: dict, lines: str, track: str) -> None:
            out = work / lines / name / f"{item['key']}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            if resolved["playbook"] is None:  # unevaluated
                value = step(
                    "classify",
                    "--ref",
                    item["ref"],
                    "--digest",
                    item["digest"],
                    "--run",
                    run,
                )
            else:  # evaluate: regis-analyze, then classify
                reports = work / "reports" / item["key"]
                code = tool(
                    "regis", "analyze", item["target"], "--playbook", resolved["playbook"],
                    "-D", str(reports), "-o", "report.{format}", "--html", "--markdown",
                )  # fmt: skip
                value = step(
                    "classify", "--playbook", resolved["playbook"],
                    "--ref", item["ref"], "--digest", item["digest"],
                    "--report", str(reports / "report.json"),
                    "--report-link", f"reports/{name}/{item['digest']}/{run}.md",
                    "--regis-exit", str(code),
                    "--source-ref", item.get("sourceRef", ""),
                    "--source-digest", item.get("source", ""),
                    "--track", track, "--epoch", item.get("epoch", ""), "--run", run,
                )  # fmt: skip
            out.write_text(json.dumps(value))

        for item in todo:
            evaluate(item, "lines", resolved["track"] or "")
        # record
        record = ("record", "--policy", path, "--results", str(results))
        step(*record, "--lines", str(work / "lines" / name))
        # approve
        count = step(
            "approve", "--policy", path, "--results", str(results), "--plan", str(plan),
            "--out", str(approved), "--transit", "transit", "--epoch", EPOCH,
            "--lines-out", str(approve_lines), "--run", run,
        )  # fmt: skip
        # record-approve
        step(*record, "--lines", str(approve_lines))
        if count["approved"] == 0:
            return
        # place, place-staged
        stage = (
            ["--stage-to", "transit", "--staged-out", str(staged)]
            if count["ordered"]
            else []
        )
        tool(
            "knock", "reconcile", str(directory), "--apply-plan", str(approved), *stage,
            "--applied-out", str(applied),
        )  # fmt: skip
        # record-applied
        step(*record, "--applied", str(applied), "--run", run)
        if not count["ordered"]:
            return
        # second-gate: pending, evaluate, record, approve, promote, record-promoted
        held_items = step(
            "pending",
            "--policy",
            path,
            "--staged",
            str(staged),
            "--results",
            str(results),
        )
        for item in held_items:
            evaluate(item, "staged-lines", "")
        step(*record, "--lines", str(work / "staged-lines" / name))
        promoted = step(
            "approve", "--policy", path, "--results", str(results),
            "--staged", str(staged), "--out", str(staged_approved),
        )  # fmt: skip
        if promoted["approved"]:
            tool("knock", "promote", str(directory), "--staged", str(staged_approved))
            step(*record, "--promoted", str(staged_approved), "--run", run)

    def test_parity_screen_writes_the_lines_of_the_steps(self):
        # a copy, a source to repair whose repair is sound, a quarantine; then an unknown regime
        self.verdicts(
            **{D1: "direct", D2: "repairable", D3: "quarantine", "*": "direct"}
        )
        for policy_file in (STANDARD, UNKNOWN):
            name = policies.load(policy_file).name
            with self.subTest(policy=name):
                steps_results = self.tmp / f"steps-{name}"
                self.steps(
                    policy_file, steps_results, self.tmp / f"steps-work-{name}", "41"
                )
                code, _, _ = self.screen(
                    "--policy", str(policy_file), "--transit", "transit", "--run", "41"
                )
                self.assertEqual(code, 0)
                by_steps = [
                    json.loads(line)
                    for line in (steps_results / f"{name}.jsonl")
                    .read_text()
                    .splitlines()
                ]
                self.assertEqual(without_ts(self.journal(name)), without_ts(by_steps))
        self.assertEqual(len(self.journal("fixture-standard")), 6)


class Copy(Fakes):
    def test_a_sound_copy_is_recorded_then_placed(self):
        """*Une copie saine*."""
        code, out, _ = self.screen("--policy", str(REDISTRIBUTION))
        self.assertEqual(code, 0)
        journal = self.journal("fixture-redistribution")
        self.assertEqual(
            [(line["digest"], line["state"], line.get("placed")) for line in journal],
            [(D4, "direct-placement", None), (D4, "direct-placement", placed(D4))],
        )
        applies = [c for c in self.calls() if "--apply-plan" in c]
        self.assertEqual(len(applies), 1)
        self.assertTrue(applies[0].startswith("knock reconcile "))
        self.assertNotIn("--stage-to", applies[0])
        approved = json.loads(Path(shlex.split(applies[0])[4]).read_text())
        self.assertEqual([op["sourceDigest"] for op in approved["operations"]], [D4])
        self.assertEqual(
            out,
            [
                {
                    "policy": "fixture-redistribution",
                    "judged": 1,
                    "approved": 1,
                    "ordered": 0,
                    "promoted": 0,
                    "outcome": "ok",
                }
            ],
        )

    def test_a_quarantine_is_a_business_outcome(self):
        """*Une quarantaine*."""
        self.verdicts(**{"*": "quarantine"})
        code, out, _ = self.screen("--policy", str(REDISTRIBUTION))
        self.assertEqual(code, 0)
        self.assertEqual(
            [line["state"] for line in self.journal("fixture-redistribution")],
            ["quarantine"],
        )
        self.assertEqual((out[0]["approved"], out[0]["outcome"]), (0, "ok"))
        self.assertFalse([c for c in self.calls() if "--apply-plan" in c])

    def test_a_failed_judge_is_inconclusive_not_a_failure(self):
        self.verdicts(**{"*": "fail"})
        code, _, _ = self.screen("--policy", str(REDISTRIBUTION))
        self.assertEqual(code, 0)
        line = self.journal("fixture-redistribution")[0]
        self.assertEqual(line["state"], "inconclusive")
        self.assertNotIn("report", line)

    def test_a_policy_with_nothing_owed_records_nothing(self):
        os.environ["FAKE_PLANS"] = str(self.tmp / "none")
        code, out, _ = self.screen("--policy", str(REDISTRIBUTION))
        self.assertEqual(
            (code, out[0]["judged"], self.journal("fixture-redistribution")), (0, 0, [])
        )


class Reports(Fakes):
    def test_the_report_is_copied_and_cited_relative_to_the_results(self):
        """*Un rapport cité par un chemin relatif*."""
        code, _, _ = self.screen("--policy", str(REDISTRIBUTION), "--run", "41")
        self.assertEqual(code, 0)
        relative = f"reports/fixture-redistribution/{D4}/41.md"
        self.assertTrue((self.results / relative).is_file())
        self.assertTrue((self.results / relative).with_suffix(".html").is_file())
        self.assertEqual(self.journal("fixture-redistribution")[0]["report"], relative)

    def test_without_a_run_the_epoch_names_the_report(self):
        self.screen("--policy", str(REDISTRIBUTION))
        self.assertEqual(
            self.journal("fixture-redistribution")[0]["report"],
            f"reports/fixture-redistribution/{D4}/{EPOCH}.md",
        )

    def test_a_run_given_as_a_url_becomes_a_file_name(self):
        self.screen(
            "--policy", str(REDISTRIBUTION), "--run", "https://ci.example/runs/77/"
        )
        line = self.journal("fixture-redistribution")[0]
        self.assertEqual(
            line["report"],
            f"reports/fixture-redistribution/{D4}/https_ci.example_runs_77.md",
        )
        self.assertEqual(line["run"], "https://ci.example/runs/77/")

    def test_a_run_of_dots_falls_back_to_the_epoch(self):
        self.screen("--policy", str(REDISTRIBUTION), "--run", "../..")
        self.assertEqual(
            self.journal("fixture-redistribution")[0]["report"],
            f"reports/fixture-redistribution/{D4}/{EPOCH}.md",
        )

    def test_a_json_only_report_is_copied_and_cited(self):
        wrapper = self.tmp / "regis-json"
        wrapper.write_text(
            '#!/bin/sh\nfor a; do shift; case "$a" in --markdown|--html) ;; '
            '*) set -- "$@" "$a";; esac; done\n'
            f'exec "{FAKES / "regis"}" "$@"\n'
        )
        wrapper.chmod(0o755)
        os.environ["USKE_REGIS_CMD"] = str(wrapper)
        self.screen("--policy", str(REDISTRIBUTION), "--run", "41")
        relative = f"reports/fixture-redistribution/{D4}/41.json"
        self.assertEqual(self.journal("fixture-redistribution")[0]["report"], relative)
        self.assertTrue((self.results / relative).is_file())

    def test_the_html_is_cited_when_there_is_no_markdown(self):
        # a judge without --markdown: drop the flag through a wrapper
        wrapper = self.tmp / "regis-html"
        wrapper.write_text(
            '#!/bin/sh\nfor a; do shift; [ "$a" = --markdown ] || set -- "$@" "$a"; done\n'
            f'exec "{FAKES / "regis"}" "$@"\n'
        )
        wrapper.chmod(0o755)
        os.environ["USKE_REGIS_CMD"] = str(wrapper)
        self.screen("--policy", str(REDISTRIBUTION), "--run", "41")
        self.assertEqual(
            self.journal("fixture-redistribution")[0]["report"],
            f"reports/fixture-redistribution/{D4}/41.html",
        )


class JudgeOnly(Fakes):
    def test_judge_only_prints_the_verdicts_and_places_nothing(self):
        """*Une demande de fusion*."""
        os.environ["USKE_AFTER_RECORD"] = f'touch "{self.tmp}/hooked"'
        code, out, _ = self.screen("--policy", str(REDISTRIBUTION), "--judge-only")
        self.assertEqual(code, 0)
        self.assertEqual(
            [(line["digest"], line["state"]) for line in out],
            [(D4, "direct-placement")],
        )
        self.assertTrue(out[0]["report"].startswith(str(self.work)))
        self.assertFalse(self.results.exists())
        self.assertFalse((self.tmp / "hooked").exists())
        knock = [c for c in self.calls() if c.startswith("knock")]
        self.assertEqual(len(knock), 1)
        self.assertIn("reconcile", knock[0])
        self.assertIn("--plan-out", knock[0])

    def test_judge_only_with_a_failed_plan_fails(self):
        os.environ["FAKE_FAIL"] = "plan"
        code, out, err = self.screen("--policy", str(REDISTRIBUTION), "--judge-only")
        self.assertEqual((code, out), (1, []))
        self.assertIn("--plan-out", err)


class UnknownRegime(Fakes):
    def test_an_unknown_regime_is_never_judged(self):
        """*Un régime inconnu*."""
        code, _, _ = self.screen("--policy", str(UNKNOWN))
        self.assertEqual(code, 0)
        self.assertFalse([c for c in self.calls() if c.startswith("regis")])
        self.assertEqual(
            [
                (line["digest"], line["state"], line["reason"])
                for line in self.journal("fixture-unknown")
            ],
            [(D5, "inconclusive", "uske/unknown-track")],
        )


def only_a_source_to_repair(tmp: Path) -> None:
    """fixture-standard's plan reduced to 1.1, D2: a source to repair."""
    os.environ["FAKE_PLANS"] = str(tmp / "plans")
    (tmp / "plans").mkdir()
    plan = json.loads((HERE / "fixtures/fakes/plans/fixture-standard.json").read_text())
    plan["operations"] = plan["operations"][1:2]
    (tmp / "plans/fixture-standard.json").write_text(json.dumps(plan))


class Repair(Fakes):
    def setUp(self) -> None:
        super().setUp()
        only_a_source_to_repair(self.tmp)

    def test_a_source_to_repair_is_held_judged_then_promoted(self):
        """*Une source à réparer*: promoted on direct-placement."""
        self.verdicts(**{D2: "repairable", held(D2): "direct"})
        code, out, _ = self.screen("--policy", str(STANDARD), "--transit", "transit")
        self.assertEqual(code, 0)
        calls = self.calls()
        apply = next(c for c in calls if "--apply-plan" in c)
        self.assertIn("--stage-to transit", apply)
        self.assertTrue(
            any(c.startswith("regis analyze") and held(D2) in c for c in calls)
        )
        self.assertTrue(any(c.startswith("knock promote") for c in calls))
        journal = self.journal("fixture-standard")
        self.assertEqual(journal[-1]["placed"], held(D2))
        self.assertEqual(journal[-1]["digest"], D2)
        self.assertEqual((out[0]["ordered"], out[0]["promoted"]), (1, 1))

    def test_a_refused_repair_is_never_promoted(self):
        """*Une source à réparer*: refused, not promoted, and the source closed."""
        self.verdicts(**{D2: "repairable", held(D2): "quarantine"})
        code, out, _ = self.screen("--policy", str(STANDARD), "--transit", "transit")
        self.assertEqual(code, 0)
        self.assertFalse([c for c in self.calls() if c.startswith("knock promote")])
        self.assertEqual(
            self.journal("fixture-standard")[-1]["reason"], "uske/remediation-refused"
        )
        self.assertEqual(out[0]["promoted"], 0)

    def test_without_a_transit_nothing_is_ordered(self):
        self.verdicts(**{D2: "repairable"})
        code, _, err = self.screen("--policy", str(STANDARD))
        self.assertEqual(code, 0)
        self.assertIn("warning: fixture-standard: 1 source(s) to repair", err)
        self.assertIn("--transit", err)
        self.assertEqual(
            self.journal("fixture-standard")[-1]["reason"], "uske/no-transit"
        )
        self.assertFalse([c for c in self.calls() if "--apply-plan" in c])

    def test_a_failed_promotion_fails_the_policy_and_records_no_placement(self):
        self.verdicts(**{D2: "repairable", held(D2): "direct"})
        os.environ["FAKE_FAIL"] = "promote"
        code, out, err = self.screen("--policy", str(STANDARD), "--transit", "transit")
        self.assertEqual(
            (code, out[0]["outcome"], out[0]["promoted"]), (1, "failed", 0)
        )
        self.assertFalse(
            [line for line in self.journal("fixture-standard") if line.get("placed")]
        )
        self.assertIn("knock promote", err)

    def test_a_failed_apply_still_judges_and_promotes_what_was_held(self):
        self.verdicts(**{D2: "repairable", held(D2): "direct"})
        os.environ["FAKE_FAIL"] = "apply"
        code, out, _ = self.screen("--policy", str(STANDARD), "--transit", "transit")
        self.assertEqual(
            (code, out[0]["outcome"], out[0]["promoted"]), (1, "failed", 1)
        )
        self.assertTrue(any(c.startswith("knock promote") for c in self.calls()))


class Policies(Fakes):
    def test_a_policy_breaks_the_next_goes_through(self):
        """*Une politique casse, la suivante passe*."""
        os.environ["FAKE_FAIL"] = "apply:fixture-redistribution"
        code, out, err = self.screen("--policies", str(FIXTURES))
        self.assertEqual(code, 1)
        self.assertIn("skipped:", err)
        self.assertEqual(
            [(o["policy"], o["outcome"]) for o in out],
            [
                ("fixture-redistribution", "failed"),
                ("fixture-standard", "ok"),
                ("fixture-unknown", "ok"),
            ],
        )
        self.assertTrue(
            any("--apply-plan" in c and "fixture-standard" in c for c in self.calls())
        )
        self.assertIn("error: screening failed for: fixture-redistribution", err)

    def test_a_failed_plan_fails_its_policy_only(self):
        os.environ["FAKE_FAIL"] = "plan:fixture-standard"
        code, out, _ = self.screen("--policies", str(FIXTURES))
        self.assertEqual(code, 1)
        self.assertEqual([o["outcome"] for o in out], ["ok", "failed", "ok"])

    def test_an_unreadable_policy_file_is_a_failure(self):
        code, out, err = self.screen("--policy", str(FIXTURES / "broken.yaml"))
        self.assertEqual((code, out), (1, []))
        self.assertIn("error:", err)

    def test_a_reused_work_directory_replays_nothing(self):
        self.screen("--policy", str(REDISTRIBUTION))
        stale = self.work / "lines" / "fixture-redistribution" / "stale.json"
        stale.write_text(
            json.dumps(
                {
                    "ts": "2099-01-01T00:00:00Z",
                    "ref": "x",
                    "digest": D1,
                    "state": "quarantine",
                    "ruleset": "none",
                }
            )
        )
        code, out, _ = self.screen("--policy", str(REDISTRIBUTION))
        self.assertEqual((code, out[0]["judged"]), (0, 0))
        self.assertNotIn(
            D1, [line["digest"] for line in self.journal("fixture-redistribution")]
        )

    def test_without_work_a_kept_temporary_directory_is_named(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(
                ["screen", "--policy", str(REDISTRIBUTION), "--results", str(self.results),
                 "--playbooks", str(PLAYBOOKS), "--judge-only"]
            )  # fmt: skip
        self.assertEqual(code, 0)
        work = Path(
            next(
                line
                for line in err.getvalue().splitlines()
                if line.startswith("work: ")
            )[6:]
        )
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(work)], check=False))
        self.assertTrue((work / "plans" / "fixture-redistribution.json").is_file())


class Names(Fakes):
    def write_policy(self, directory: Path, name: str) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{len(list(directory.iterdir()))}.yaml"
        path.write_text(
            REDISTRIBUTION.read_text().replace("fixture-redistribution", name)
        )
        return path

    def test_a_name_that_is_a_path_is_refused(self):
        canary = self.tmp / "x"
        canary.mkdir()
        (canary / "keep").write_text("")
        policy = self.write_policy(self.tmp / "p", "../x")
        code, out, err = self.screen("--policy", str(policy))
        self.assertEqual((code, out), (1, []))
        self.assertIn("DNS-1123", err)
        code, out, err = self.screen("--policies", str(self.tmp / "p"))
        self.assertEqual((code, out), (0, []))
        self.assertIn("skipped:", err)
        self.assertTrue((canary / "keep").exists())

    def test_names_follow_the_dns_1123_subdomain_rule(self):
        for name, valid in [
            ("base.debian", True),
            ("a-4711-redis-7", True),
            ("x" * 253, True),
            ("x" * 254, False),
            ("../x", False),
            ("Upper", False),
            ("a;b", False),
            ("-a", False),
            ("a.", False),
        ]:
            with self.subTest(name=name):
                path = self.write_policy(self.tmp / "n", name)
                if valid:
                    self.assertEqual(policies.load(path).name, name)
                else:
                    with self.assertRaises(policies.PolicyError):
                        policies.load(path)

    def test_paths_never_leave_work_or_results_even_for_an_unchecked_name(self):
        """Belt and braces: a Policy built without `load` cannot escape either."""
        canary = self.tmp / "x"
        (canary / "keep").mkdir(parents=True)
        loaded = policies.load(REDISTRIBUTION)
        escaping = policies.Policy(
            "../../x", loaded.path, loaded.track, loaded.document
        )
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            summary = screen.screen_policy(
                escaping, self.work, self.results, PLAYBOOKS, None, EPOCH, "",
                screen.Tools.from_env(os.environ), None, False,
            )  # fmt: skip
        self.assertEqual(summary["outcome"], "failed")
        self.assertIn("outside", err.getvalue())
        self.assertTrue((canary / "keep").is_dir())
        self.assertEqual(self.calls(), [])

    def test_a_digest_that_is_a_path_is_refused(self):
        plans = self.tmp / "plans"
        plans.mkdir()
        plan = json.loads(
            (HERE / "fixtures/fakes/plans/fixture-redistribution.json").read_text()
        )
        plan["operations"][0]["sourceDigest"] = "sha256:../../../x"
        (plans / "fixture-redistribution.json").write_text(json.dumps(plan))
        os.environ["FAKE_PLANS"] = str(plans)
        code, out, err = self.screen("--policy", str(REDISTRIBUTION))
        self.assertEqual((code, out[0]["outcome"]), (1, "failed"))
        self.assertIn("outside", err)

    def test_a_dotted_name_with_nothing_owed_is_ok(self):
        """`lines/base.debian` missing is no line, not a missing file."""
        policy = self.write_policy(self.tmp / "p", "base.debian")
        code, out, _ = self.screen("--policy", str(policy))
        self.assertEqual((code, out[0]["outcome"], out[0]["judged"]), (0, "ok", 0))

    def test_a_malformed_plan_fails_its_policy_only(self):
        plans = self.tmp / "plans"
        plans.mkdir()
        plan = json.loads(
            (HERE / "fixtures/fakes/plans/fixture-redistribution.json").read_text()
        )
        del plan["operations"][0]["sourceDigest"]
        (plans / "fixture-redistribution.json").write_text(json.dumps(plan))
        (plans / "fixture-standard.json").write_text(
            (HERE / "fixtures/fakes/plans/fixture-standard.json").read_text()
        )
        os.environ["FAKE_PLANS"] = str(plans)
        two = self.tmp / "two"
        two.mkdir()
        (two / "a.yaml").write_text(REDISTRIBUTION.read_text())
        (two / "b.yaml").write_text(STANDARD.read_text())
        code, out, err = self.screen("--policies", str(two))
        self.assertEqual(code, 1)
        self.assertEqual(
            [(o["policy"], o["outcome"]) for o in out],
            [("fixture-redistribution", "failed"), ("fixture-standard", "ok")],
        )
        self.assertIn("error: fixture-redistribution: unexpected input: KeyError", err)


class Journal(Fakes):
    def test_an_unwritable_journal_stops_before_placement(self):
        """*Le journal ne peut pas être écrit*: the report lands, the journal does not."""
        reports = self.results / "reports" / "fixture-redistribution" / D4
        reports.mkdir(
            parents=True
        )  # writable: the first write that fails is the journal's
        self.results.chmod(stat.S_IRUSR | stat.S_IXUSR)
        self.addCleanup(self.results.chmod, stat.S_IRWXU)
        code, out, err = self.screen("--policy", str(REDISTRIBUTION))
        self.assertEqual((code, out[0]["outcome"]), (1, "failed"))
        self.assertTrue(list(reports.iterdir()))
        self.assertFalse([c for c in self.calls() if "--apply-plan" in c])
        self.assertIn("error: fixture-redistribution:", err)
        self.assertIn("fixture-redistribution.jsonl", err)


class Hook(Fakes):
    def screen_policy(self, policy: policies.Policy) -> dict:
        with contextlib.redirect_stderr(io.StringIO()):
            return screen.screen_policy(
                policy,
                self.work,
                self.results,
                PLAYBOOKS,
                "transit",
                EPOCH,
                "",
                screen.Tools.from_env(os.environ),
                os.environ["USKE_AFTER_RECORD"],
                False,
            )

    def test_a_hook_failing_at_the_second_gate_stops_the_promotion(self):
        only_a_source_to_repair(self.tmp)
        self.verdicts(**{D2: "repairable", held(D2): "direct"})
        count = self.tmp / "count"
        # succeeds after the first gate's record, fails after the held image's
        os.environ["USKE_AFTER_RECORD"] = (
            f'n=$(cat "{count}" 2>/dev/null || echo 0); n=$((n+1)); '
            f'echo $n > "{count}"; [ $n -lt 2 ]'
        )
        code, out, _ = self.screen("--policy", str(STANDARD), "--transit", "transit")
        self.assertEqual((code, out[0]["outcome"]), (1, "failed"))
        self.assertEqual(count.read_text().strip(), "2")
        calls = self.calls()
        self.assertTrue(any("--apply-plan" in c for c in calls))
        self.assertTrue(
            any(c.startswith("regis analyze") and held(D2) in c for c in calls)
        )
        self.assertFalse([c for c in calls if c.startswith("knock promote")])

    def test_the_journal_is_committed_before_the_placement(self):
        """*Commiter le journal avant de placer*."""
        os.environ["USKE_AFTER_RECORD"] = (
            'echo "hook $USKE_POLICY $USKE_RESULTS" >> "$FAKE_CALLS"'
        )
        code, _, _ = self.screen("--policy", str(REDISTRIBUTION))
        self.assertEqual(code, 0)
        calls = self.calls()
        hook = calls.index(f"hook fixture-redistribution {self.results}")
        apply = next(i for i, c in enumerate(calls) if "--apply-plan" in c)
        self.assertLess(hook, apply)
        # after the verdicts, then after the placement line
        self.assertEqual(calls.count(f"hook fixture-redistribution {self.results}"), 2)
        self.assertTrue(calls[-1].startswith("hook"))

    def test_a_failing_hook_stops_the_placement(self):
        """*Le crochet échoue*."""
        os.environ["USKE_AFTER_RECORD"] = "false"
        code, out, err = self.screen("--policy", str(REDISTRIBUTION))
        self.assertEqual((code, out[0]["outcome"]), (1, "failed"))
        self.assertFalse([c for c in self.calls() if "--apply-plan" in c])
        self.assertIn("exit 1: sh -c false", err)

    def test_the_policy_name_never_reaches_the_shell(self):
        # `policies.load` refuses such a name; the hook must not rely on it
        name = "a;touch pwned"
        loaded = policies.load(STANDARD)
        odd = policies.Policy(
            name,
            loaded.path,
            loaded.track,
            {**loaded.document, "metadata": {"name": name}},
        )
        plans = self.tmp / "plans"
        plans.mkdir()
        plan = json.loads(
            (HERE / "fixtures/fakes/plans/fixture-redistribution.json").read_text()
        )
        for op in plan["operations"]:
            op["policy"] = name
        (plans / f"{name}.json").write_text(json.dumps(plan))
        os.environ["FAKE_PLANS"] = str(plans)
        witness = self.tmp / "witness"
        os.environ["USKE_AFTER_RECORD"] = (
            f'true; printf %s "$USKE_POLICY" > "{witness}"'
        )
        cwd = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, cwd)
        summary = self.screen_policy(odd)
        self.assertEqual(summary["outcome"], "ok")
        self.assertEqual(witness.read_text(), name)
        self.assertFalse((self.tmp / "pwned").exists())
        self.assertFalse(Path(cwd, "pwned").exists())


class Tools(Fakes):
    def test_a_docker_prefix_is_split_and_run_without_a_shell(self):
        """*Un préfixe docker*."""
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        docker = bin_dir / "docker"
        docker.write_text('#!/bin/sh\nprintf "docker %s\\n" "$*" >> "$FAKE_CALLS"\n')
        docker.chmod(0o755)
        os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
        os.environ["USKE_REGIS_CMD"] = "docker run --rm -v /w:/w regis:1"
        self.assertEqual(
            screen.Tools.from_env(os.environ).regis,
            ["docker", "run", "--rm", "-v", "/w:/w", "regis:1"],
        )
        code, _, _ = self.screen("--policy", str(REDISTRIBUTION))
        self.assertEqual(code, 0)
        judged = [c for c in self.calls() if c.startswith("docker")]
        self.assertEqual(len(judged), 1)
        self.assertTrue(
            judged[0].startswith(
                "docker run --rm -v /w:/w regis:1 analyze harbor.example/"
            )
        )
        # no report from that judge: inconclusive, never a failure
        self.assertEqual(
            self.journal("fixture-redistribution")[0]["state"], "inconclusive"
        )

    def test_a_missing_placer_fails_before_anything(self):
        """*Le placeur manque*."""
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "regis").symlink_to(FAKES / "regis")
        os.environ["PATH"] = str(bin_dir)
        code, out, err = self.screen("--policy", str(REDISTRIBUTION))
        self.assertEqual((code, out), (1, []))
        self.assertIn("error: knock", err)
        self.assertFalse(self.results.exists())
        self.assertEqual(self.calls(), [])

    def test_the_bare_names_are_the_default(self):
        tools = screen.Tools.from_env({"USKE_REGIS_CMD": "  "})
        self.assertEqual((tools.regis, tools.knock), (["regis"], ["knock"]))

    def test_a_tool_that_cannot_start_is_reported(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = screen.launch([str(self.tmp)])  # a directory: found, not executable
        self.assertEqual(code, 127)
        self.assertIn("failed to start", err.getvalue())

    def test_the_help_names_the_three_variables(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            cli.main(["screen", "--help"])
        for name in ("USKE_REGIS_CMD", "USKE_KNOCK_CMD", "USKE_AFTER_RECORD"):
            self.assertIn(name, out.getvalue())

    def test_policies_and_policy_are_exclusive(self):
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as raised,
        ):
            cli.main(["screen", "--results", "r", "--policy", "a", "--policies", "b"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
