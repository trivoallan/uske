"""Le workflow réutilisable `extra-screen.yml` : ses scripts, rejoués contre un dépôt nu.

Chaque test nomme l'exigence de `specs/github-screening-workflow/spec.md` (change
`github-action`) qu'il rend vraie. Le reste se joue sur le banc `extra-screen-example.yml`.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
SCREEN = WORKFLOWS / "extra-screen.yml"
MAJOR_TAG = WORKFLOWS / "extra-major-tag.yml"


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def step(workflow: dict, job: str, step_id: str) -> dict:
    return next(s for s in workflow["jobs"][job]["steps"] if s.get("id") == step_id)


def git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


class Scripts(unittest.TestCase):
    """Naissance de la branche et crochet du journal (exigences « branche dédiée » et
    « poussé avant le placement qui suit »)."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.remote = self.tmp / "remote.git"
        git("init", "-q", "--bare", str(self.remote))
        env = step(load(SCREEN), "screen", "scripts")["env"]
        for name in ("BIRTH", "HOOK"):
            path = self.tmp / f"{name.lower()}.sh"
            path.write_text(env[name])
            path.chmod(0o755)
        self.env = {
            **os.environ,
            "GITHUB_TOKEN": "token",
            "JOURNAL_BRANCH": "uske-journal",
            "JOURNAL_REMOTE": str(self.remote),
            "RUN_URL": "https://github.com/o/r/actions/runs/1",
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.org",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.org",
        }

    def run_script(self, name: str, results: Path, **extra: str) -> int:
        env = {**self.env, "RESULTS": str(results), "USKE_RESULTS": str(results), **extra}
        return subprocess.run(
            [str(self.tmp / f"{name}.sh")], env=env, capture_output=True
        ).returncode

    def born(self, name: str) -> Path:
        results = self.tmp / name
        self.assertEqual(self.run_script("birth", results), 0)
        return results

    def remote_files(self) -> list[str]:
        return git("--git-dir", str(self.remote), "ls-tree", "-r", "--name-only",
                   "uske-journal").split()

    def record(self, results: Path, policy: str) -> int:
        with (results / f"{policy}.jsonl").open("a") as journal:
            journal.write('{"state": "placed"}\n')
        return self.run_script("hook", results, USKE_POLICY=policy, USKE_STEP="record")

    def test_first_run_creates_an_orphan_branch(self) -> None:
        results = self.born("r1")
        self.assertEqual(self.remote_files(), [".gitignore"])
        self.assertEqual((results / ".gitignore").read_text(), "reports/\n")
        roots = git("--git-dir", str(self.remote), "rev-list", "--max-parents=0",
                    "uske-journal").split()
        self.assertEqual(len(roots), 1)

    def test_an_existing_branch_is_read(self) -> None:
        self.assertEqual(self.record(self.born("r1"), "x"), 0)
        self.assertTrue((self.born("r2") / "x.jsonl").is_file())

    def test_the_hook_pushes_the_policy_journal_only(self) -> None:
        results = self.born("r1")
        (results / "reports" / "x" / "sha256:ab").mkdir(parents=True)
        (results / "reports" / "x" / "sha256:ab" / "1.md").write_text("report")
        (results / "y.jsonl").write_text("{}\n")
        self.assertEqual(self.record(results, "x"), 0)
        self.assertEqual(self.remote_files(), [".gitignore", "x.jsonl"])

    def test_the_hook_rebases_on_a_concurrent_push(self) -> None:
        first, second = self.born("r1"), self.born("r2")
        self.assertEqual(self.record(second, "y"), 0)
        self.assertEqual(self.record(first, "x"), 0)
        self.assertEqual(self.remote_files(), [".gitignore", "x.jsonl", "y.jsonl"])

    def test_the_hook_fails_when_the_push_is_refused(self) -> None:
        results = self.born("r1")
        hook = self.remote / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        self.assertNotEqual(self.record(results, "x"), 0)

    def test_no_token_on_disk(self) -> None:
        self.record(self.born("r1"), "x")
        for name in ("r1", "r2"):
            results = self.tmp / name if name == "r1" else self.born(name)
            config = (results / ".git" / "config").read_text()
            self.assertNotIn("extraheader", config)
            self.assertNotIn("token", config)

    def test_a_refused_birth_is_not_retried(self) -> None:
        hook = self.remote / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        self.assertNotEqual(self.run_script("birth", self.tmp / "r1"), 0)


class Shape(unittest.TestCase):
    """Ce que le fichier doit dire, que le banc ne voit pas à coup sûr."""

    def setUp(self) -> None:
        self.workflow = load(SCREEN)
        self.screen = self.workflow["jobs"]["screen"]

    def all_steps(self) -> list[dict]:
        return [s for job in self.workflow["jobs"].values() for s in job["steps"]]

    def test_inputs_never_reach_a_script_text(self) -> None:
        for s in self.all_steps():
            scripts = [v for v in (s.get("env") or {}).values()
                       if isinstance(v, str) and "\n" in v]
            for text in [s.get("run", ""), *scripts]:
                self.assertNotIn("${{", text, s.get("name"))

    def test_the_tools_never_receive_the_token(self) -> None:
        compose = next(s for s in self.all_steps()
                       if s.get("name") == "Composer les commandes du juge et du placeur")
        self.assertNotIn("GITHUB_TOKEN", compose["run"])
        self.assertNotIn("extraheader", compose["run"])

    def test_permissions_are_the_least(self) -> None:
        self.assertEqual(self.workflow["permissions"], {})
        self.assertEqual(self.workflow["jobs"]["name"]["permissions"], {"contents": "read"})
        self.assertEqual(self.screen["permissions"],
                         {"contents": "write", "packages": "write"})

    def test_the_lock_is_the_policy_name(self) -> None:
        self.assertEqual(self.screen["concurrency"], {
            "group": "uske-screen-${{ needs.name.outputs.name }}",
            "cancel-in-progress": False,
        })

    def test_no_checkout_keeps_the_token(self) -> None:
        for s in self.all_steps():
            if s.get("uses", "").startswith("actions/checkout@"):
                self.assertIs(s["with"]["persist-credentials"], False)

    def test_the_final_push_runs_always(self) -> None:
        final = step(self.workflow, "screen", "final")
        self.assertIn("always()", final["if"])
        self.assertIn("after-record.sh", final["run"])

    def test_regis_reads_the_shared_grype_db(self) -> None:
        compose = next(s for s in self.all_steps()
                       if s.get("name") == "Composer les commandes du juge et du placeur")
        for flag in ("GRYPE_DB_CACHE_DIR=/grype-db", "GRYPE_DB_AUTO_UPDATE=false",
                     "GRYPE_DB_MAX_ALLOWED_BUILT_AGE=48h", "GRYPE_CHECK_FOR_APP_UPDATE=false"):
            self.assertIn(flag, compose["run"])

    def test_buildkit_listens_on_loopback_only(self) -> None:
        self.assertIn("-p 127.0.0.1:1234:1234", step(self.workflow, "screen", "tools")["run"])

    def test_each_image_version_is_followed_by_renovate(self) -> None:
        lines = SCREEN.read_text().splitlines()
        versions = [i for i, line in enumerate(lines)
                    if re.match(r"\s+(REGIS|KNOCK|BUILDKIT)_VERSION:", line)]
        self.assertEqual(len(versions), 3)
        for i in versions:
            self.assertRegex(lines[i - 1], r"# renovate: datasource=docker depName=\S+")


class MovingTag(unittest.TestCase):
    """Exigence « une étiquette mobile suit chaque version »."""

    def tag_for(self, version: str) -> str:
        script = step(load(MAJOR_TAG), "tag", "name")["run"]
        with tempfile.NamedTemporaryFile("r") as out:
            subprocess.run(["sh", "-c", script], check=True,
                           env={**os.environ, "VERSION": version, "GITHUB_OUTPUT": out.name})
            return out.read().strip()

    def test_a_0x_version_moves_the_minor(self) -> None:
        self.assertEqual(self.tag_for("0.10.2"), "tag=v0.10")

    def test_a_1x_version_moves_the_major(self) -> None:
        self.assertEqual(self.tag_for("1.2.0"), "tag=v1")
