"""The `grype-db` refresh: what the manifest promises, read from `deploy/base/grype-db.yaml`.

Each test names the scenario of `specs/shared-vulnerability-db/spec.md` (change
`base-grype-partagee`) it makes true. The script itself is checked for its order, not run:
grype is not in this image.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "deploy" / "base" / "grype-db.yaml"
POINTER = "grype-db/current.json"
ARCHIVE = "grype-db/current.tar.zst"


class GrypeDb(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
        cls.by_kind = {d["kind"]: d for d in docs}
        cls.template = cls.by_kind["WorkflowTemplate"]["spec"]["templates"][0]
        cls.script = "\n".join(cls.template["container"]["args"])

    def test_the_cron_runs_the_refresh_every_six_hours_one_at_a_time(self) -> None:
        """*Le rafraîchissement planifié distribue une nouvelle base*."""
        cron = self.by_kind["CronWorkflow"]
        self.assertEqual(cron["metadata"]["name"], "grype-db")
        self.assertEqual(cron["spec"]["concurrencyPolicy"], "Forbid")
        self.assertEqual(cron["spec"]["schedules"], ["17 */6 * * *"])
        self.assertEqual(
            cron["spec"]["workflowSpec"]["workflowTemplateRef"], {"name": "grype-db"}
        )

    def test_the_template_runs_the_regis_image_as_uske(self) -> None:
        template = self.by_kind["WorkflowTemplate"]
        self.assertEqual(template["metadata"]["name"], "grype-db")
        self.assertEqual(template["spec"]["serviceAccountName"], "uske")
        self.assertEqual(self.template["container"]["image"], "regis")
        self.assertEqual(self.template["container"]["command"], ["sh", "-c"])

    def test_the_pointer_in_is_optional_and_the_outputs_stay_in_place(self) -> None:
        """*Aucune base nouvelle n'est publiée*: nothing uploaded, the keys do not move."""
        (pointer,) = self.template["inputs"]["artifacts"]
        self.assertEqual(pointer["path"], "/tmp/in/current.json")
        self.assertTrue(pointer["optional"])
        self.assertEqual(pointer["s3"], {"key": POINTER})
        outputs = {a["s3"]["key"]: a for a in self.template["outputs"]["artifacts"]}
        self.assertEqual(set(outputs), {ARCHIVE, POINTER})
        for key, artifact in outputs.items():
            with self.subTest(key=key):
                self.assertTrue(artifact["optional"])
                self.assertEqual(artifact["archive"], {"none": {}})
                # outside `runs/`: they must outlive the Workflow
                self.assertEqual(artifact["artifactGC"], {"strategy": "Never"})
        self.assertEqual(outputs[ARCHIVE]["path"], "/tmp/out/current.tar.zst")
        self.assertEqual(outputs[POINTER]["path"], "/tmp/out/current.json")

    def test_the_script_lists_before_it_downloads(self) -> None:
        script = self.script
        self.assertLess(script.index("grype db list"), script.index("grype db update"))
        self.assertIn("exit 0", script)  # "no newer database" ends in success, empty

    def test_an_interrupted_download_publishes_nothing(self) -> None:
        """*Un téléchargement interrompu*: `set -eu`, and the status check precedes the packing."""
        script = self.script
        self.assertIn("set -eu", script)
        self.assertLess(
            script.index("grype db update"), script.index("grype db status")
        )
        self.assertLess(script.index("grype db status"), script.index("tarfile"))
        self.assertIn("'w:zst'", script)
        # the pointer is moved to the outputs only after the archive is written
        self.assertLess(script.index("tarfile"), script.index("/tmp/out/current.json"))

    def test_the_retry_is_the_screenings(self) -> None:
        self.assertEqual(
            self.template["retryStrategy"],
            {
                "limit": "2",
                "retryPolicy": "OnFailure",
                "backoff": {"duration": "10s", "factor": "2"},
            },
        )


if __name__ == "__main__":
    unittest.main()
