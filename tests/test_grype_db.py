"""The `grype-db` refresh: what the manifest promises, read from `deploy/base/grype-db.yaml`.

Each test names the scenario of `specs/shared-vulnerability-db/spec.md` (change
`base-grype-partagee`) it makes true. The script itself is checked for its order, not run:
grype is not in this image.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "deploy" / "base" / "grype-db.yaml"
FAKES = Path(__file__).resolve().parent / "fakes"
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

    def test_the_archive_is_packed_in_staging_and_renamed_before_the_pointer(
        self,
    ) -> None:
        """*Un téléchargement interrompu*: nothing is ever written under `out/` half-done."""
        for line in self.script.splitlines():
            if "tarfile.open(" in line:
                self.assertNotIn("/out", line)
                self.assertIn("/stage/", line)
        archive = self.script.index('mv "$W/stage/current.tar.zst" "$W/out/')
        pointer = self.script.index('mv "$W/latest.json" "$W/out/current.json"')
        self.assertLess(archive, pointer)

    def test_the_retry_is_the_screenings(self) -> None:
        self.assertEqual(self.template["activeDeadlineSeconds"], 1800)
        self.assertEqual(
            self.by_kind["WorkflowTemplate"]["spec"]["podGC"],
            {"strategy": "OnPodSuccess"},
        )
        limits = self.template["container"]["resources"]
        self.assertEqual(limits["requests"]["ephemeral-storage"], "5Gi")
        self.assertEqual(
            self.template["retryStrategy"],
            {
                "limit": "2",
                "retryPolicy": "OnFailure",
                "backoff": {"duration": "10s", "factor": "2"},
            },
        )


OLD = {"built": "2026-10-01T00:00:00Z", "checksum": "sha256:old"}
NEW = {"built": "2026-10-02T00:00:00Z", "checksum": "sha256:new"}
LISTING = [
    {"status": "deprecated", "built": "2025-01-01T00:00:00Z", "checksum": "sha256:x"},
    {"status": "active", **NEW, "url": "https://example.test/db.tar.zst"},
]


def _python3_has_zstd() -> bool:
    """The script runs the `python3` on PATH, which may not be the interpreter of the tests."""
    probe = (
        "import tarfile, io; tarfile.open(fileobj=io.BytesIO(), mode='w:zst').close()"
    )
    return (
        subprocess.run(
            ["python3", "-c", probe], capture_output=True, check=False
        ).returncode
        == 0
    )


needs_zstd = unittest.skipUnless(
    _python3_has_zstd(), "tarfile 'w:zst' needs Python 3.14"
)


class Script(unittest.TestCase):
    """The refresh script run against a fake grype, with WORK redirected to a temp dir."""

    def run_script(self, pointer: str | None = None, **env: str):
        script = "\n".join(
            yaml.safe_load(MANIFEST.read_text().split("\n---\n")[0])["spec"][
                "templates"
            ][0]["container"]["args"]
        )
        work = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(work, ignore_errors=True))
        if pointer is not None:
            (work / "in").mkdir()
            (work / "in" / "current.json").write_text(pointer)
        environ = {
            **os.environ,
            "PATH": f"{FAKES}:{os.environ['PATH']}",
            "WORK": str(work),
            "FAKE_LIST": json.dumps(LISTING),
            "FAKE_CALLS": str(work / "calls"),
            **env,
        }
        proc = subprocess.run(
            ["sh", "-c", script],
            check=False,
            env=environ,
            capture_output=True,
            text=True,
        )
        calls = (work / "calls").read_text() if (work / "calls").exists() else ""
        return proc, work, calls

    def assertPublished(self, work: Path) -> None:
        out = work / "out"
        self.assertEqual(
            sorted(p.name for p in out.iterdir()), ["current.json", "current.tar.zst"]
        )
        self.assertEqual(json.loads((out / "current.json").read_text()), NEW)
        # read with the python3 that packed it, which is not always the tests' interpreter
        listing = subprocess.run(
            [
                "python3",
                "-c",
                (
                    "import sys, tarfile; "
                    "print(*tarfile.open(sys.argv[1], 'r:zst').getnames(), sep='\\n')"
                ),
                str(out / "current.tar.zst"),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        names = listing.stdout.split()
        self.assertIn("6", names)
        self.assertIn("6/vulnerability.db", names)

    @needs_zstd
    def test_a_new_database_is_published(self) -> None:
        """*Le rafraîchissement planifié distribue une nouvelle base*."""
        proc, work, _ = self.run_script(pointer=json.dumps(OLD))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertPublished(work)

    @needs_zstd
    def test_the_first_run_publishes(self) -> None:
        proc, work, _ = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertPublished(work)

    def test_no_newer_database_publishes_nothing(self) -> None:
        """*Aucune base nouvelle n'est publiée*: success, no output, no download."""
        proc, work, calls = self.run_script(pointer=json.dumps(NEW))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(list((work / "out").iterdir()), [])
        self.assertNotIn("update", calls)

    def test_a_failed_download_publishes_nothing(self) -> None:
        """*Un téléchargement interrompu*."""
        proc, work, _ = self.run_script(pointer=json.dumps(OLD), FAKE_UPDATE_FAIL="1")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(list((work / "out").iterdir()), [])

    def test_an_invalid_database_publishes_nothing(self) -> None:
        proc, work, _ = self.run_script(pointer=json.dumps(OLD), FAKE_STATUS_FAIL="1")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(list((work / "out").iterdir()), [])

    def test_a_malformed_pointer_does_not_block_the_refresh(self) -> None:
        """The refresh goes as far as the download (made to fail: no packing needed here)."""
        for pointer in ("{not json", "{}", "[]", '{"checksum": 3}'):
            with self.subTest(pointer=pointer):
                proc, work, calls = self.run_script(
                    pointer=pointer, FAKE_UPDATE_FAIL="1"
                )
                self.assertIn("db update", calls)
                self.assertNotEqual(proc.returncode, 0)
                self.assertEqual(list((work / "out").iterdir()), [])

    @needs_zstd
    def test_a_malformed_pointer_is_replaced_by_a_new_publication(self) -> None:
        proc, work, _ = self.run_script(pointer="{not json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertPublished(work)

    @needs_zstd
    @unittest.skipIf(os.geteuid() == 0, "root reads a mode 000 file")
    def test_a_failure_while_packing_publishes_nothing(self) -> None:
        """Argo saves optional outputs of a failed container: `out/` must stay empty."""
        proc, work, _ = self.run_script(pointer=json.dumps(OLD), FAKE_PACK_FAULT="1")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(list((work / "out").iterdir()), [])

    def test_no_active_database_fails(self) -> None:
        proc, work, _ = self.run_script(FAKE_LIST="[]")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("no active database", proc.stderr)
        self.assertEqual(list((work / "out").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
