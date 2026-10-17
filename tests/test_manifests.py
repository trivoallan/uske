"""The manifests as kustomize renders them: who mounts the journal, and the two ceilings.

Each test names the scenario of `specs/screening-fan-out/spec.md` (change
`screen-and-policy-fan-out`) it makes true. Skipped where kubectl is missing; `make lint` runs
it after `argo lint`.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
JOURNAL = "uske-results"


def render_all(overlay: str) -> list[dict]:
    out = subprocess.run(
        ["kubectl", "kustomize", str(ROOT / "deploy" / overlay)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [doc for doc in yaml.safe_load_all(out) if doc]


def render(overlay: str, kind: str = "WorkflowTemplate") -> dict[str, dict]:
    """The overlay's objects of `kind`, by name."""
    return {
        doc["metadata"]["name"]: doc
        for doc in render_all(overlay)
        if doc.get("kind") == kind
    }


def shell(template: dict) -> str:
    """What a template runs: its command, args and script source, as one text."""
    pod = template.get("container") or template.get("script") or {}
    parts = pod.get("command", []) + pod.get("args", []) + [pod.get("source", "")]
    return "\n".join(str(part) for part in parts)


def keys(node: object) -> list[str]:
    """Every `s3.key` under `node`."""
    if isinstance(node, dict):
        found = [node["s3"]["key"]] if isinstance(node.get("s3"), dict) else []
        return found + [k for value in node.values() for k in keys(value)]
    if isinstance(node, list):
        return [k for value in node for k in keys(value)]
    return []


# a token in a URL: git writes the remote URL to .git/config, a disk Argo may upload
TOKEN_IN_URL = re.compile(r"://[^\s\"']*\$\{?TOKEN\b")


def mounts(spec: dict, claim: str) -> dict[str, list[dict]]:
    """template name -> its mounts of the volume backed by `claim`."""
    found: dict[str, list[dict]] = {}
    for template in spec["templates"]:
        volumes = spec.get("volumes", []) + template.get("volumes", [])
        names = {
            v["name"]
            for v in volumes
            if v.get("persistentVolumeClaim", {}).get("claimName") == claim
        }
        pod = template.get("container") or template.get("script") or {}
        hits = [m for m in pod.get("volumeMounts", []) if m["name"] in names]
        if hits:
            found[template["name"]] = hits
    return found


@unittest.skipUnless(shutil.which("kubectl"), "kubectl renders the manifests")
class Manifests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = render("base")
        cls.kind = render("kind")

    def test_only_the_merge_writes_the_journal(self) -> None:
        """*Le rendu des manifestes*: only the parent's snapshot and merge mount uske-results."""
        parent = mounts(self.base["uske-screening"]["spec"], JOURNAL)
        child = mounts(self.base["uske-policy"]["spec"], JOURNAL)
        self.assertEqual(set(child), {"merge"})
        self.assertEqual(set(parent), {"merge", "snapshot"})
        # the snapshot writes its mark there (.pending-merge/<run>), the merge clears it
        self.assertFalse(
            any(
                m.get("readOnly")
                for m in parent["snapshot"] + parent["merge"] + child["merge"]
            )
        )
        templates = {
            t["name"]: t for t in self.base["uske-screening"]["spec"]["templates"]
        }
        self.assertIn("snapshot", templates["snapshot"]["container"]["args"])
        self.assertIn("--pending {{workflow.name}}", shell(templates["merge"]))
        child_merge = {
            t["name"]: t for t in self.base["uske-policy"]["spec"]["templates"]
        }
        self.assertNotIn("--pending", shell(child_merge["merge"]))

    def test_no_token_on_disk(self) -> None:
        """review C1: no remote URL carries the token; the child's .git always goes."""
        for overlay in (self.base, self.kind):
            for wt in overlay.values():
                for template in wt["spec"]["templates"]:
                    with self.subTest(
                        template=f"{wt['metadata']['name']}/{template['name']}"
                    ):
                        self.assertIsNone(TOKEN_IN_URL.search(shell(template)))
        templates = {
            t["name"]: t for t in self.base["uske-policy"]["spec"]["templates"]
        }
        checkout = shell(templates["checkout"])
        self.assertLess(
            checkout.index("trap 'rm -rf /work/repo/.git' EXIT"), checkout.index("git ")
        )
        self.assertIn("http.extraHeader", checkout)
        analyze = templates["regis-analyze"]
        mounts = {
            m["name"]: m["mountPath"] for m in analyze["container"]["volumeMounts"]
        }
        self.assertEqual(mounts["grype"], "/grype")
        (db,) = [a for a in analyze["inputs"]["artifacts"] if a["name"] == "grype-db"]
        self.assertTrue(db["path"].startswith("/grype/"))
        parent = {
            t["name"]: t for t in self.base["uske-screening"]["spec"]["templates"]
        }
        self.assertIn("http.extraHeader", shell(parent["checkout"]))

    def test_a_policy_name_always_follows_a_fixed_directory(self) -> None:
        """review I3, M5: per-child archives; no policy named `out` or `done` meets another key."""
        name = "{{workflow.parameters.name}}"
        found = keys(self.base["uske-policy"]) + keys(self.base["uske-screening"])
        # the one key outside `runs/`: the database the refresh distributes, read by regis-analyze
        (refresh,) = [
            d
            for d in yaml.safe_load_all(
                (ROOT / "deploy" / "base" / "grype-db.yaml").read_text()
            )
            if d and d["kind"] == "WorkflowTemplate"
        ]
        (shared,) = [k for k in keys(refresh) if k.endswith(".tar.zst")]
        readers = [
            t["name"]
            for doc in ("uske-policy", "uske-screening")
            for t in self.base[doc]["spec"]["templates"]
            if shared in keys(t.get("inputs"))
        ]
        self.assertEqual(readers, ["regis-analyze"])
        for doc in ("uske-policy", "uske-screening"):
            for t in self.base[doc]["spec"]["templates"]:
                self.assertNotIn(shared, keys(t.get("outputs")))
        for key in (k for k in found if k != shared):
            with self.subTest(key=key):
                self.assertTrue(key.startswith("runs/{{workflow."), key)
                if name in key:
                    before = key.split(name)[0].rstrip("/").rsplit("/", 1)[-1]
                    self.assertIn(before, {"out", "done", "policies"})
        lines = [
            k for k in found if k.startswith("runs/{{workflow.parameters.run}}/out/")
        ]
        self.assertTrue(lines)
        for key in lines:
            self.assertTrue(key.endswith(("/", "Z-{{workflow.name}}.tgz")), key)

    def test_artifact_gc(self) -> None:
        """review I6: a child's work goes with it, what the parent reads is kept."""
        for name in ("uske-policy", "uske-screening"):
            gc = self.base[name]["spec"]["artifactGC"]
            self.assertEqual(gc["strategy"], "OnWorkflowDeletion")
        kept = {}
        for template in self.base["uske-policy"]["spec"]["templates"]:
            for artifact in template.get("outputs", {}).get("artifacts", []):
                if artifact.get("artifactGC"):
                    kept[artifact["name"]] = artifact["artifactGC"]["strategy"]
        self.assertEqual(kept, {"lines": "Never", "done": "Never"})
        templates = {
            t["name"]: t for t in self.base["uske-policy"]["spec"]["templates"]
        }
        self.assertNotIn("outputs", templates["uske-read"])
        steps = {
            step["name"]: step
            for group in templates["policy"]["steps"] + templates["staged"]["steps"]
            for step in group
        }
        self.assertEqual(steps["pending"]["template"], "uske-read")
        self.assertEqual(steps["resolve"]["template"], "uske-read")
        for template in self.base["uske-policy"]["spec"]["templates"]:
            for group in template.get("steps", []):
                for step in group:
                    for art in step.get("arguments", {}).get("artifacts", []):
                        self.assertNotIn("steps.pending.", art.get("from", ""))
                        self.assertNotIn("steps.resolve.", art.get("from", ""))

    def test_no_list_is_passed_as_a_parameter(self) -> None:
        """review I5: an environment string stops at 128 KiB, ~1,300 policies."""
        aggregate = re.compile(r"\{\{steps\.[^.}]+\.outputs\.(result|parameters)\}\}")
        for wt in self.base.values():
            for template in wt["spec"]["templates"]:
                for group in template.get("steps", []):
                    for step in group:
                        for param in step.get("arguments", {}).get("parameters", []):
                            with self.subTest(step=step["name"], param=param["name"]):
                                self.assertIsNone(
                                    aggregate.search(str(param.get("value", "")))
                                )
                pod = template.get("container") or template.get("script") or {}
                for env in pod.get("env", []):
                    self.assertNotIn("POLICIES", env["name"])

    def test_the_children_role(self) -> None:
        """review I4: blockOwnerDeletion needs the owner's finalizers."""
        rules = render("base", "Role")["uske-children"]["rules"]
        self.assertIn(
            {
                "apiGroups": ["argoproj.io"],
                "resources": ["workflows/finalizers"],
                "verbs": ["update"],
            },
            rules,
        )

    def test_no_child_template_holds_a_persistent_volume(self) -> None:
        """*Le rendu des manifestes*: a child's steps pass their work by artifacts."""
        spec = self.base["uske-policy"]["spec"]
        self.assertNotIn("volumeClaimTemplates", spec)
        claims = [
            (template["name"], volume["name"])
            for template in [{"name": "<workflow>", **spec}] + spec["templates"]
            for volume in template.get("volumes", [])
            if "persistentVolumeClaim" in volume
        ]
        self.assertEqual(claims, [("merge", "results")])
        self.assertEqual(
            {
                v["persistentVolumeClaim"]["claimName"]
                for t in spec["templates"]
                for v in t.get("volumes", [])
                if "persistentVolumeClaim" in v
            },
            {JOURNAL},
        )

    def test_both_ceilings_are_one(self) -> None:
        """*La base et le banc*: policies at a time and judgements at a time, both 1."""
        for overlay in (self.base, self.kind):
            for name in ("uske-screening", "uske-policy"):
                with self.subTest(template=name):
                    self.assertEqual(overlay[name]["spec"]["parallelism"], 1)

    def test_the_bench_patches_hit_the_templates_they_name(self) -> None:
        """deploy/kind patches by index: a moved template must fail here, not on the bench."""
        templates = {
            t["name"]: t for t in self.kind["uske-policy"]["spec"]["templates"]
        }
        for name, wanted in (
            ("regis-analyze", {"grype", "registry-ca"}),
            ("knock", {"registry-ca", "knock-key"}),
            ("knock-once", {"registry-ca", "knock-key"}),
            ("checkout", {"work", "repository"}),
        ):
            with self.subTest(template=name):
                found = {
                    m["name"] for m in templates[name]["container"]["volumeMounts"]
                }
                self.assertEqual(found, wanted)
        parent = {
            t["name"]: t for t in self.kind["uske-screening"]["spec"]["templates"]
        }
        found = {m["name"] for m in parent["checkout"]["container"]["volumeMounts"]}
        self.assertEqual(found, {"work", "repository"})

    def test_the_bench_suspends_the_grype_db_refresh_and_fills_it_by_hand(self) -> None:
        crons = render("kind", "CronWorkflow")
        self.assertTrue(crons["grype-db"]["spec"]["suspend"])
        hand = yaml.safe_load((ROOT / "deploy" / "kind" / "grype-db.yaml").read_text())
        self.assertEqual(hand["kind"], "Workflow")
        self.assertEqual(hand["metadata"]["generateName"], "grype-db-")
        self.assertEqual(hand["spec"]["workflowTemplateRef"]["name"], "grype-db")
        self.assertIn("grype-db", self.kind)


if __name__ == "__main__":
    unittest.main()
