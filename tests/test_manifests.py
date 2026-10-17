"""The manifests as kustomize renders them: who mounts the journal, and the two ceilings.

Each test names the scenario of `specs/screening-fan-out/spec.md` (change
`screen-and-policy-fan-out`) it makes true. Skipped where kubectl is missing; `make lint` runs
it after `argo lint`.
"""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
JOURNAL = "uske-results"


def render(overlay: str) -> dict[str, dict]:
    """The overlay's WorkflowTemplates, by name."""
    out = subprocess.run(
        ["kubectl", "kustomize", str(ROOT / "deploy" / overlay)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {
        doc["metadata"]["name"]: doc
        for doc in yaml.safe_load_all(out)
        if doc and doc.get("kind") == "WorkflowTemplate"
    }


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
        """*Le rendu des manifestes*: the merges write uske-results, the snapshot only reads it."""
        parent = mounts(self.base["uske-screening"]["spec"], JOURNAL)
        child = mounts(self.base["uske-policy"]["spec"], JOURNAL)
        self.assertEqual(set(child), {"merge"})
        self.assertEqual(set(parent), {"merge", "snapshot"})
        self.assertTrue(all(m.get("readOnly") for m in parent["snapshot"]))
        self.assertFalse(
            any(m.get("readOnly") for m in parent["merge"] + child["merge"])
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
            ("regis-analyze", {"registry-ca"}),
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


if __name__ == "__main__":
    unittest.main()
