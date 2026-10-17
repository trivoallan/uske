"""The `grype-db` refresh: what the manifest promises, read from `deploy/base/grype-db.yaml`.

Each test names the scenario of `specs/shared-vulnerability-db/spec.md` (change
`base-grype-partagee`) it makes true. `GrypeDb` reads the manifest; `Script` runs the refresh
script against the fake grype in `tests/fakes/`, and `RegisAnalyze` does the same for the
judging step. The tests that pack or unpack a real zstd archive need Python 3.14.
"""

from __future__ import annotations

import atexit
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
SCREENING = ROOT / "deploy" / "base" / "workflowtemplate.yaml"
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
        # Argo writes inputs 0600 root; the regis image runs as non-root (found on the kind bench).
        self.assertEqual(pointer["mode"], 0o444)
        self.assertEqual(pointer["s3"], {"key": POINTER})
        outputs = {a["s3"]["key"]: a for a in self.template["outputs"]["artifacts"]}
        self.assertEqual(set(outputs), {ARCHIVE, POINTER})
        self.assertEqual(
            [a["name"] for a in self.template["outputs"]["artifacts"]],
            ["archive", "pointer"],
        )
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


def _has_zstd(python: str) -> bool:
    probe = (
        "import tarfile, io; tarfile.open(fileobj=io.BytesIO(), mode='w:zst').close()"
    )
    try:
        return (
            subprocess.run(
                [python, "-c", probe], capture_output=True, check=False
            ).returncode
            == 0
        )
    except OSError:
        return False


def _zstd_python() -> str | None:
    """The interpreter the scripts run: the `python3` on PATH if it has zstd (3.14), else a uv one."""
    if _has_zstd("python3"):
        return "python3"
    try:
        found = subprocess.run(
            ["uv", "python", "find", "3.14"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
    except OSError:
        return None
    return found if found and _has_zstd(found) else None


PYTHON = _zstd_python()
SHIM = (
    ""  # a directory that makes `python3` resolve to PYTHON in the scripts under test
)
if PYTHON and PYTHON != "python3":
    SHIM = tempfile.mkdtemp()
    atexit.register(shutil.rmtree, SHIM, ignore_errors=True)
    os.symlink(PYTHON, os.path.join(SHIM, "python3"))
PATH = ":".join(p for p in (str(FAKES), SHIM, os.environ["PATH"]) if p)

needs_zstd = unittest.skipUnless(PYTHON, "tarfile 'w:zst' needs Python 3.14")


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
            "PATH": PATH,
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
        # read with the interpreter that packed it, which is not always the tests' own
        listing = subprocess.run(
            [
                PYTHON or "python3",
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


def _regis_analyze() -> dict:
    for doc in yaml.safe_load_all(SCREENING.read_text()):
        for template in (doc or {}).get("spec", {}).get("templates", []):
            if template["name"] == "regis-analyze":
                return template
    raise AssertionError("no regis-analyze template")


class RegisAnalyze(unittest.TestCase):
    """The judging step reads the distributed database and never fetches one."""

    template = _regis_analyze()
    container = template["container"]
    script = container["args"][0]

    def test_the_database_comes_in_as_an_optional_artifact(self) -> None:
        """*Aucune base distribuée*: the step starts without it."""
        (db,) = [
            a
            for a in self.template["inputs"]["artifacts"]
            if a.get("name") == "grype-db"
        ]
        self.assertEqual(db["path"], "/grype/current.tar.zst")
        self.assertTrue(db["optional"])
        self.assertEqual(db["mode"], 0o444)  # readable by regis's non-root user
        self.assertEqual(db["archive"], {"none": {}})
        self.assertEqual(db["s3"], {"key": ARCHIVE})

    def test_no_download_and_a_database_at_most_two_days_old(self) -> None:
        """*Une évaluation ne télécharge pas de base*."""
        env = {e["name"]: e["value"] for e in self.container["env"]}
        self.assertEqual(
            env,
            {
                "GRYPE_DB_CACHE_DIR": "/grype/db",
                "GRYPE_DB_AUTO_UPDATE": "false",
                "GRYPE_DB_MAX_ALLOWED_BUILT_AGE": "48h",
                "GRYPE_CHECK_FOR_APP_UPDATE": "false",
            },
        )
        self.assertEqual(
            self.container["envFrom"], [{"secretRef": {"name": "uske-harbor"}}]
        )

    def test_the_storage_is_sized_for_the_database_and_no_volume_is_added(self) -> None:
        resources = self.container["resources"]
        self.assertEqual(resources["requests"]["ephemeral-storage"], "5Gi")
        # no limit: it would also cap the scratch space of the image being judged
        self.assertNotIn("ephemeral-storage", resources.get("limits", {}))
        self.assertEqual(
            self.template["volumes"],
            [{"name": "grype", "emptyDir": {"sizeLimit": "6Gi"}}],
        )
        self.assertEqual(
            self.container["volumeMounts"], [{"name": "grype", "mountPath": "/grype"}]
        )

    def test_a_failed_artifact_fetch_is_retried(self) -> None:
        """OnFailure would not retry the init container that downloads the archive."""
        self.assertEqual(
            self.template["retryStrategy"],
            {
                "limit": "2",
                "retryPolicy": "Always",
                "backoff": {"duration": "10s", "factor": "2"},
            },
        )

    def test_the_archive_is_unpacked_with_the_safe_filter_before_regis(self) -> None:
        self.assertIn("r:zst", self.script)
        self.assertIn("filter='data'", self.script)
        self.assertLess(self.script.index("r:zst"), self.script.index("regis analyze"))

    def run_step(self, archive: bytes | None):
        """The script with `/grype` and `/tmp` redirected to a temp dir, regis being the fake."""
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        (root / "grype").mkdir()
        if archive is not None:
            (root / "grype" / "current.tar.zst").write_bytes(archive)
        script = (
            self.script.replace("/grype/", f"{root}/grype/")
            .replace("/tmp/", f"{root}/")
            .replace("{{inputs.parameters.target}}", "reg.test/app@sha256:aa")
            .replace("{{inputs.parameters.playbook}}", "playbook.yaml")
        )
        env = {
            **os.environ,
            "PATH": PATH,
            "FAKE_CALLS": str(root / "calls"),
            "FAKE_ENV": str(root / "env.json"),
            **{e["name"]: e["value"] for e in self.container["env"]},
        }
        proc = subprocess.run(
            ["sh", "-c", script], check=False, env=env, capture_output=True, text=True
        )
        return proc, root

    def pack(self) -> bytes:
        """A database archive (`6/vulnerability.db`, incompressible), packed by the PATH's python3."""
        src = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(src, ignore_errors=True))
        (src / "6").mkdir()
        (src / "6" / "vulnerability.db").write_bytes(os.urandom(300_000))
        packed = src.parent / f"{src.name}.tar.zst"
        self.addCleanup(lambda: packed.unlink(missing_ok=True))
        subprocess.run(
            [
                PYTHON or "python3",
                "-c",
                (
                    "import sys, tarfile; t = tarfile.open(sys.argv[1], 'w:zst'); "
                    "t.add(sys.argv[2] + '/6', arcname='6'); t.close()"
                ),
                str(packed),
                str(src),
            ],
            check=True,
        )
        return packed.read_bytes()

    def assertRegisRan(self, proc, root: Path) -> None:
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((root / "report" / "report.json").exists())
        self.assertIn("regis analyze", (root / "calls").read_text().replace("'", ""))

    def test_without_an_archive_regis_still_runs(self) -> None:
        """*Aucune base distribuée*: regis reports the missing database itself."""
        proc, root = self.run_step(None)
        self.assertRegisRan(proc, root)
        self.assertFalse((root / "grype" / "db").exists())

    def test_a_corrupt_archive_is_removed_and_regis_still_runs(self) -> None:
        proc, root = self.run_step(b"not a zstd archive")
        self.assertRegisRan(proc, root)
        self.assertFalse((root / "grype" / "db").exists())
        self.assertFalse((root / "grype" / "current.tar.zst").exists())
        self.assertIn("grype-db: the database could not be unpacked: ", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    @needs_zstd
    def test_a_truncated_archive_leaves_no_partial_database(self) -> None:
        archive = self.pack()
        proc, root = self.run_step(archive[: len(archive) * 2 // 3])
        self.assertRegisRan(proc, root)
        self.assertFalse((root / "grype" / "db").exists())
        self.assertFalse((root / "grype" / "current.tar.zst").exists())
        self.assertNotIn("Traceback", proc.stderr)

    @needs_zstd
    def test_a_valid_archive_is_unpacked_then_deleted_before_regis(self) -> None:
        """*Deux évaluations entre deux rafraîchissements jugent avec la même base*."""
        proc, root = self.run_step(self.pack())
        self.assertRegisRan(proc, root)
        self.assertTrue((root / "grype" / "db" / "6" / "vulnerability.db").exists())
        self.assertFalse((root / "grype" / "current.tar.zst").exists())
        seen = json.loads((root / "env.json").read_text())
        self.assertEqual(seen["GRYPE_DB_AUTO_UPDATE"], "false")
        self.assertEqual(seen["GRYPE_DB_MAX_ALLOWED_BUILT_AGE"], "48h")
        self.assertEqual(seen["GRYPE_CHECK_FOR_APP_UPDATE"], "false")
        self.assertEqual(seen["GRYPE_DB_CACHE_DIR"], "/grype/db")


if __name__ == "__main__":
    unittest.main()
