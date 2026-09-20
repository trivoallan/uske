"""The census without a network: Harbor and the usage oracle are replaced."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from uske import census, cli

D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64
D3 = "sha256:" + "3" * 64
NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def artifact(digest: str, repository: str, *, stamped: bool = False, tags=("v1",)) -> dict:
    return {"project": repository.split("/")[0], "repository": repository, "digest": digest,
            "tags": list(tags), "annotations": {census.STAMP_KEY: "pilot"} if stamped else {}}


class FakeHarbor:
    """Harbor's three listings, with the shapes its API really returns."""

    def __init__(self, tree: dict):
        self.tree = tree  # {"project": {"repo": [raw artifact, ...]}}

    def projects(self):
        return list(self.tree)

    def repositories(self, project):
        return list(self.tree[project])

    def artifacts(self, project, repository):
        return self.tree[project][repository]


def raw(digest, *, stamped=False, tags=("v1",)):
    return {"digest": digest, "tags": [{"name": t} for t in tags],
            "annotations": {census.STAMP_KEY: "pilot"} if stamped else {}}


class Walk(unittest.TestCase):
    def test_flattens_projects_repositories_artifacts(self):
        harbor = FakeHarbor({"hub": {"redis": [raw(D1, stamped=True)], "nginx": [raw(D2)]}})
        fleet = census.walk(harbor)
        self.assertEqual([a["repository"] for a in fleet], ["hub/redis", "hub/nginx"])
        self.assertEqual(fleet[0]["annotations"], {census.STAMP_KEY: "pilot"})
        self.assertEqual(fleet[1]["tags"], ["v1"])

    def test_restricts_to_the_given_projects(self):
        harbor = FakeHarbor({"hub": {"redis": [raw(D1)]}, "helios": {"app": [raw(D2)]}})
        self.assertEqual([a["digest"] for a in census.walk(harbor, ["helios"])], [D2])

    def test_drops_an_artifact_without_a_digest(self):
        harbor = FakeHarbor({"hub": {"redis": [{"tags": []}, raw(D1)]}})
        self.assertEqual([a["digest"] for a in census.walk(harbor)], [D1])


class Suspects(unittest.TestCase):
    def test_stamped_images_came_through_the_door(self):
        fleet = [artifact(D1, "hub/redis", stamped=True), artifact(D2, "helios/app")]
        self.assertEqual([a["digest"] for a in census.suspects(fleet)], [D2])

    def test_the_existing_chain_bypassed_nothing(self):
        fleet = [artifact(D1, "hub/redis"), artifact(D2, "helios/app")]
        kept = census.suspects(fleet, {"hub/redis"})
        self.assertEqual([a["digest"] for a in kept], [D2])


class InService(unittest.TestCase):
    def test_splits_seen_from_unseen(self):
        answers = {D1: {"last_seen": "2026-09-19T08:00:00Z", "detail": "cluster prod-eu"},
                   D2: {"last_seen": None}}
        seen, unseen, unknown = census.in_service(
            [artifact(D1, "helios/app"), artifact(D2, "boree/old")],
            lambda q: answers[q["digest"]], now=NOW)
        self.assertEqual([a["digest"] for a in seen], [D1])
        self.assertEqual(seen[0]["detail"], "cluster prod-eu")
        self.assertEqual([a["digest"] for a in unseen], [D2])
        self.assertEqual(unknown, [])

    def test_the_window_becomes_the_since_the_oracle_receives(self):
        captured = {}

        def ask(query):
            captured.update(query)
            return {"last_seen": None}

        census.in_service([artifact(D1, "helios/app")], ask, idle_days=15, now=NOW)
        self.assertEqual(captured["since"], "2026-09-05T12:00:00+00:00")
        self.assertEqual(captured["digest"], D1)
        self.assertEqual(captured["image_ref"], "helios/app:v1")

    def test_an_untagged_artifact_still_gets_a_readable_ref(self):
        captured = {}

        def ask(query):
            captured.update(query)
            return {"last_seen": None}

        census.in_service([artifact(D1, "helios/app", tags=())], ask, now=NOW)
        self.assertEqual(captured["image_ref"], "helios/app:<untagged>")

    def test_a_failing_oracle_is_unknown_never_unseen(self):
        """The inverse of knock purge's fail-closed: silence must not shrink the count."""
        def ask(query):
            raise census.CensusError("boom")

        seen, unseen, unknown = census.in_service([artifact(D1, "helios/app")], ask, now=NOW)
        self.assertEqual((seen, unseen), ([], []))
        self.assertEqual(unknown[0]["digest"], D1)
        self.assertIn("boom", unknown[0]["reason"])

    def test_a_malformed_timestamp_is_unknown_not_unseen(self):
        seen, unseen, unknown = census.in_service(
            [artifact(D1, "helios/app")], lambda q: {"last_seen": "yesterday"}, now=NOW)
        self.assertEqual((seen, unseen), ([], []))
        self.assertEqual(len(unknown), 1)


class Report(unittest.TestCase):
    def test_without_an_oracle_the_in_service_question_stays_open(self):
        fleet = [artifact(D1, "hub/redis", stamped=True), artifact(D2, "helios/app")]
        out = census.report(fleet, census.suspects(fleet), None, known_repositories={"x/y"})
        self.assertEqual(out["bypass_stored"], 1)
        self.assertIsNone(out["bypass_in_service"])

    def test_counts_and_bounds(self):
        fleet = [artifact(D1, "hub/redis", stamped=True), artifact(D2, "helios/app"),
                 artifact(D3, "boree/app")]
        suspect = census.suspects(fleet)
        split = ([artifact(D2, "helios/app")], [], [artifact(D3, "boree/app")])
        out = census.report(fleet, suspect, split)
        self.assertEqual(out["fleet"], 3)
        self.assertEqual(out["bypass_in_service"], 1)
        self.assertEqual(out["unknown"], 1)
        self.assertEqual(out["bound"], {"low": 1, "high": 2})
        self.assertEqual(out["rate_in_service"], round(1 / 3, 4))
        self.assertTrue(any("unanswered" in c for c in out["caveats"]))

    def test_a_missing_existing_chain_list_makes_the_number_an_upper_bound(self):
        fleet = [artifact(D1, "hub/redis")]
        out = census.report(fleet, census.suspects(fleet), None)
        self.assertTrue(any("upper bound" in c for c in out["caveats"]))

    def test_a_fleet_with_no_stamp_at_all_is_called_out(self):
        """Harbor not returning annotations would read as a 100 % bypass: say so, loudly."""
        fleet = [artifact(D1, "hub/redis"), artifact(D2, "hub/nginx")]
        out = census.report(fleet, census.suspects(fleet), None, known_repositories={"x/y"})
        self.assertTrue(any("not one artifact" in c for c in out["caveats"]))


class CommandOracle(unittest.TestCase):
    """The command contract, exactly as KNOCK_USAGE_ORACLE_CMD speaks it."""

    def test_reads_stdin_and_returns_the_answer(self):
        ask = census.command_oracle(
            "python3 -c \"import sys,json;"
            "json.load(sys.stdin);print(json.dumps({'last_seen':'2026-09-19T08:00:00Z'}))\"")
        self.assertEqual(ask({"digest": D1})["last_seen"], "2026-09-19T08:00:00Z")

    def test_a_non_zero_exit_raises(self):
        ask = census.command_oracle("python3 -c \"import sys;sys.exit(3)\"")
        with self.assertRaises(census.CensusError):
            ask({"digest": D1})

    def test_unreadable_stdout_raises(self):
        ask = census.command_oracle("python3 -c \"print('not json')\"")
        with self.assertRaises(census.CensusError):
            ask({"digest": D1})

    def test_an_empty_command_is_refused(self):
        with self.assertRaises(census.CensusError):
            census.command_oracle("   ")


class Cli(unittest.TestCase):
    """The wiring: environment, the existing-chain file, and what lands on stdout."""

    ENV = {"HARBOR_URL": "https://harbor.example", "HARBOR_USER": "u",
           "HARBOR_PASSWORD": "p"}

    def run_census(self, *argv, tree=None):
        tree = tree or {"hub": {"redis": [raw(D1, stamped=True)]},
                        "helios": {"app": [raw(D2)]}}
        out = io.StringIO()
        with mock.patch.dict(os.environ, self.ENV, clear=False), \
                mock.patch.object(census, "Harbor", lambda *a: FakeHarbor(tree)), \
                contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(["census", *argv])
        return code, json.loads(out.getvalue())

    def test_without_an_oracle_reports_the_stored_bypass(self):
        code, result = self.run_census()
        self.assertEqual(code, 0)
        self.assertEqual((result["fleet"], result["bypass_stored"]), (2, 1))
        self.assertIsNone(result["bypass_in_service"])

    def test_the_existing_chain_file_ignores_blanks_and_comments(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("# the hub2hub repositories\n\nhelios/app\n")
            path = handle.name
        self.addCleanup(os.unlink, path)
        _, result = self.run_census("--known-repositories", path)
        self.assertEqual(result["suspect"], 0)
        self.assertFalse(any("upper bound" in c for c in result["caveats"]))

    def test_missing_credentials_fail_before_touching_the_registry(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["census"]), 1)

    def test_the_suspects_are_written_out_to_name_the_teams(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "suspects.json")
            self.run_census("--suspects-out", path)
            written = json.loads(Path(path).read_text())
        self.assertEqual([a["repository"] for a in written], ["helios/app"])


if __name__ == "__main__":
    unittest.main()
