"""dt-sync without a network: knock's audit, Dependency-Track and cosign are replaced."""

from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uske import cli, dtsync, policies

FIXTURES = Path(__file__).parent / "fixtures" / "policies"
HOST = "registry.example:5000"
D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64


FORMATS = ["cyclonedx-json", "spdx-json"]


def outcome(ref: str, digest: str = D1, covered=True, signed=True, sbom=True, policy="pilot", formats=FORMATS):
    return {"image_ref": f"{HOST}/{ref}", "digest": digest, "covered": covered, "signed": signed,
            "sbom": sbom, "sbom_formats": formats if sbom else ([] if sbom is False else None),
            "policy": policy, "error": None}


def audit(*outcomes: dict) -> dict:
    """knock audit's CoverageReport envelope (knock 0.12.0)."""
    return {"apiVersion": "knock.io/v1alpha1", "kind": "CoverageReport", "registries": ["local"],
            "counts": {}, "outcomes": list(outcomes)}


def policy(name="pilot", track="redistribution", owners=("group:default/TTC",)) -> policies.Policy:
    doc = {"kind": "MirrorPolicy", "metadata": {"name": name},
           "spec": {"imports": [{"name": "a", "owners": list(owners)}, {"name": "b", "owners": list(owners)}]}}
    return policies.Policy(name, Path(f"{name}.yaml"), track, doc)


def tracked(project: str, version: str, digest=D1, active=True, uuid="u-1") -> dict:
    return {"uuid": uuid, "project": project, "version": version, "digest": digest, "active": active}


class Placed(unittest.TestCase):
    def test_only_stamped_signed_with_sbom(self):
        report = audit(
            outcome("shared/app:1.0"),
            outcome("producer/app:1.0", covered=False, signed=None, sbom=None, policy=None),  # a candidate
            outcome("shared/app:0.9", signed=False),
            outcome("shared/app:0.8", sbom=False),
        )
        self.assertEqual([o["image_ref"] for o in dtsync.placed(report)], [f"{HOST}/shared/app:1.0"])

    def test_missing_field_fails_rather_than_sends(self):
        broken = outcome("shared/app:1.0")
        del broken["digest"]
        with self.assertRaisesRegex(dtsync.SyncError, "lacks digest"):
            dtsync.placed(audit(broken))

    def test_unreadable_image_is_left_to_knock(self):
        failed = {"image_ref": f"{HOST}/shared/app:1.0", "error": {"message": "timeout"}}
        self.assertEqual(dtsync.placed(audit(failed)), [])

    def test_not_an_audit(self):
        with self.assertRaises(dtsync.SyncError):
            dtsync.placed({"counts": {}})

    def test_another_report_version_fails(self):
        with self.assertRaisesRegex(dtsync.SyncError, "expected"):
            dtsync.placed({**audit(), "apiVersion": "knock.io/v1beta1"})


class Plan(unittest.TestCase):
    policies = {"pilot": policy()}

    def plan(self, fleet, known):
        return dtsync.plan(dtsync.placed(audit(*fleet)), self.policies, known)

    def test_new_image_is_sent_with_its_identity_and_owners(self):
        result = self.plan([outcome("shared-test/app:2.0")], [])
        self.assertEqual(result["send"], [{
            "ref": f"{HOST}/shared-test/app", "digest": D1, "project": "shared-test/app", "version": "2.0",
            "tags": ["dt-sync", "policy:pilot", "track:redistribution", "owner:group:default/ttc"],
            "uuid": None,
        }])
        self.assertEqual(result["retire"], [])

    def test_same_digest_is_not_sent_again(self):
        result = self.plan([outcome("shared-test/app:2.0")], [tracked("shared-test/app", "2.0")])
        self.assertEqual(result, {"send": [], "retire": [], "report": []})

    def test_republished_tag_is_sent_again(self):
        result = self.plan([outcome("shared-test/app:2.0", digest=D2)], [tracked("shared-test/app", "2.0")])
        self.assertEqual([(s["digest"], s["uuid"]) for s in result["send"]], [(D2, "u-1")])

    def test_image_gone_is_retired(self):
        result = self.plan([], [tracked("shared-test/app", "1.0")])
        self.assertEqual(result["retire"], [{"uuid": "u-1", "project": "shared-test/app", "version": "1.0"}])

    def test_retired_version_is_not_retired_twice(self):
        self.assertEqual(self.plan([], [tracked("shared-test/app", "1.0", active=False)])["retire"], [])

    def test_image_back_reactivates_its_version(self):
        result = self.plan([outcome("shared-test/app:1.0")], [tracked("shared-test/app", "1.0", active=False)])
        self.assertEqual([s["uuid"] for s in result["send"]], ["u-1"])

    def test_only_tracked_versions_are_retired(self):
        # `tracked` is what Dependency-Track lists under the dt-sync tag: a hand-made project
        # never appears in it, so nothing here can retire it.
        result = self.plan([], [])
        self.assertEqual(result["retire"], [])

    def test_unknown_policy_is_sent_without_owners_and_reported(self):
        result = self.plan([outcome("shared-test/app:2.0", policy="gone")], [])
        self.assertEqual(result["send"][0]["tags"], ["dt-sync", "policy:gone"])
        self.assertEqual(result["report"], [{"ref": f"{HOST}/shared-test/app:2.0", "reason": "unknown-policy", "policy": "gone"}])

    def test_image_without_cyclonedx_is_reported_not_sent_nor_retired(self):
        result = self.plan([outcome("shared-test/app:1.0", formats=["spdx-json"])],
                           [tracked("shared-test/app", "1.0")])
        self.assertEqual(result, {"send": [], "retire": [],
                                  "report": [{"ref": f"{HOST}/shared-test/app:1.0", "reason": "no-cyclonedx"}]})

    def test_identity(self):
        self.assertEqual(dtsync.identity("h:5000/a/b/c:1.2"), ("h:5000/a/b/c", "a/b/c", "1.2"))
        with self.assertRaises(dtsync.SyncError):
            dtsync.identity("h:5000/a/b")


def completed(code: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], code, stdout, stderr)


def envelope(predicate: dict) -> str:
    statement = {"predicateType": dtsync.CYCLONEDX, "predicate": predicate}
    return json.dumps({"payload": base64.b64encode(json.dumps(statement).encode()).decode()}) + "\n"


class VerifiedBom(unittest.TestCase):
    ref = f"{HOST}/shared-test/app@{D1}"

    def test_verified_predicate_is_returned(self):
        bom = {"bomFormat": "CycloneDX", "components": []}
        run = mock.Mock(return_value=completed(0, envelope(bom)))
        self.assertEqual(dtsync.verified_bom(self.ref, "k.pub", [], run), bom)
        self.assertIn("--type", run.call_args.args[0])

    def test_unverified_raises(self):
        run = mock.Mock(return_value=completed(1, stderr="signature mismatch"))
        with self.assertRaisesRegex(dtsync.SyncError, "not verified"):
            dtsync.verified_bom(self.ref, "k.pub", [], run)

    def test_key_signatures_skip_the_tlog(self):
        run = mock.Mock(return_value=completed(0, envelope({})))
        dtsync.verified_bom(self.ref, "k.pub", [], run)
        self.assertIn("--insecure-ignore-tlog=true", run.call_args.args[0])


class Client(unittest.TestCase):
    item = {"project": "shared-test/app", "version": "2.0", "digest": D1, "tags": ["dt-sync"], "uuid": None}

    def test_publish_creates_then_updates_the_digest_property(self):
        client = dtsync.DependencyTrack("http://dt", "key")
        calls = []

        def call(method, path, body=None, query=None):
            calls.append((method, path))
            if method == "PUT" and path.endswith("/property"):
                raise dtsync.SyncError("Dependency-Track PUT /property: HTTP 409")
            return {"projectUuid": "u-9"} if path == "/v1/bom" else None

        client.call = call
        self.assertEqual(client.publish(self.item, {"components": []}), "u-9")
        self.assertEqual(calls, [("PUT", "/v1/bom"), ("PATCH", "/v1/project/u-9"),
                                 ("PUT", "/v1/project/u-9/property"), ("POST", "/v1/project/u-9/property")])

    def test_tracked_reads_the_digest_property(self):
        client = dtsync.DependencyTrack("http://dt", "key")
        responses = {
            "/v1/project/tag/dt-sync": [{"uuid": "u-1", "name": "shared-test/app", "version": "2.0", "active": True}],
            "/v1/project/u-1/property": [{"groupName": "oci", "propertyName": "digest", "propertyValue": D1}],
        }
        client.call = lambda method, path, body=None, query=None: responses[path]
        self.assertEqual(client.tracked(), [tracked("shared-test/app", "2.0")])


def run(*argv: str) -> tuple[int, object]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = cli.main(list(argv))
    text = out.getvalue().strip()
    return code, json.loads(text) if text else None


@mock.patch.dict(os.environ, {"DT_URL": "http://dt", "DT_API_KEY": "key"})
class Commands(unittest.TestCase):
    def test_dt_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "audit.json"
            report.write_text(json.dumps(audit(outcome("shared-test/app:2.0", policy="pilot-redistribution"))))
            with mock.patch.object(dtsync.DependencyTrack, "tracked", return_value=[]):
                code, result = run("dt-plan", "--audit", str(report), "--policies", str(FIXTURES))
        self.assertEqual(code, 0)
        self.assertEqual([s["version"] for s in result["send"]], ["2.0"])

    def test_dt_plan_fails_when_dependency_track_is_down(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "audit.json"
            report.write_text(json.dumps(audit()))
            with mock.patch.object(dtsync.DependencyTrack, "tracked", side_effect=dtsync.SyncError("down")):
                code, _ = run("dt-plan", "--audit", str(report), "--policies", str(FIXTURES))
        self.assertEqual(code, 1)

    def test_dt_publish_sends_nothing_when_unverified(self):
        with mock.patch.object(dtsync, "verified_bom", side_effect=dtsync.SyncError("not verified")), \
             mock.patch.object(dtsync.DependencyTrack, "publish") as publish:
            code, _ = run("dt-publish", "--ref", f"{HOST}/a/b", "--digest", D1,
                          "--project", "a/b", "--version", "1", "--uuid", "null")
        self.assertEqual(code, 1)
        publish.assert_not_called()

    def test_dt_publish_pins_the_digest(self):
        with mock.patch.object(dtsync, "verified_bom", return_value={"components": []}) as verify, \
             mock.patch.object(dtsync.DependencyTrack, "publish", return_value="u-1") as publish:
            code, result = run("dt-publish", "--ref", f"{HOST}/a/b", "--digest", D1,
                               "--project", "a/b", "--version", "1", "--tags", "dt-sync,policy:p", "--uuid", "null")
        self.assertEqual(code, 0)
        self.assertEqual(verify.call_args.args[0], f"{HOST}/a/b@{D1}")
        self.assertEqual(publish.call_args.args[0]["tags"], ["dt-sync", "policy:p"])
        self.assertIsNone(publish.call_args.args[0]["uuid"])

    def test_dt_publish_reads_tags_as_argo_renders_them(self):
        with mock.patch.object(dtsync, "verified_bom", return_value={"components": []}), \
             mock.patch.object(dtsync.DependencyTrack, "publish", return_value="u-1") as publish:
            run("dt-publish", "--ref", f"{HOST}/a/b", "--digest", D1, "--project", "a/b",
                "--version", "1", "--tags", '["dt-sync","owner:group:default/ttc"]', "--uuid", "u-1")
        self.assertEqual(publish.call_args.args[0]["tags"], ["dt-sync", "owner:group:default/ttc"])
        self.assertEqual(publish.call_args.args[0]["uuid"], "u-1")

    def test_dt_retire(self):
        with mock.patch.object(dtsync.DependencyTrack, "retire") as retire:
            self.assertEqual(run("dt-retire", "--uuid", "u-1"), (0, {"retired": "u-1"}))
        retire.assert_called_once_with("u-1")

    def test_missing_credentials(self):
        with mock.patch.dict(os.environ, {"DT_URL": ""}):
            self.assertEqual(run("dt-retire", "--uuid", "u-1")[0], 1)
