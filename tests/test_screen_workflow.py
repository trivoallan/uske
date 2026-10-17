"""Le workflow réutilisable `extra-screen.yml` : ses scripts, rejoués contre un dépôt nu.

Chaque test nomme l'exigence de `specs/github-screening-workflow/spec.md` (change
`github-action`) qu'il rend vraie. Le reste se joue sur le banc `extra-screen-example.yml`.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
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
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.remote = self.tmp / "remote.git"
        git("init", "-q", "--bare", str(self.remote))
        env = step(load(SCREEN), "screen", "scripts")["env"]
        for name in ("BIRTH", "HOOK"):
            path = self.tmp / f"{name.lower()}.sh"
            path.write_text(env[name])
            path.chmod(0o755)
        self.env = {
            **os.environ,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
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
        env = {
            **self.env,
            "RESULTS": str(results),
            "USKE_RESULTS": str(results),
            **extra,
        }
        return subprocess.run(
            [str(self.tmp / f"{name}.sh")], check=False, env=env, capture_output=True
        ).returncode

    def born(self, name: str) -> Path:
        results = self.tmp / name
        self.assertEqual(self.run_script("birth", results), 0)
        return results

    def remote_files(self) -> list[str]:
        return git(
            "--git-dir",
            str(self.remote),
            "ls-tree",
            "-r",
            "--name-only",
            "uske-journal",
        ).split()

    def record(self, results: Path, policy: str) -> int:
        with (results / f"{policy}.jsonl").open("a") as journal:
            journal.write('{"state": "placed"}\n')
        return self.run_script("hook", results, USKE_POLICY=policy, USKE_STEP="record")

    def test_first_run_creates_an_orphan_branch(self) -> None:
        results = self.born("r1")
        self.assertEqual(self.remote_files(), [".gitignore"])
        self.assertEqual((results / ".gitignore").read_text(), "reports/\n")
        roots = git(
            "--git-dir", str(self.remote), "rev-list", "--max-parents=0", "uske-journal"
        ).split()
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
        first = self.born("r1")
        self.record(first, "x")
        second = self.born("r2")
        for results in (first, second):
            config = (results / ".git" / "config").read_text()
            self.assertNotIn("extraheader", config)
            self.assertNotIn("token", config)

    def test_the_hook_replays_on_rebase_three_times_at_most(self) -> None:
        results = self.born("r1")
        counter = self.tmp / "pushes"
        hook = self.remote / "hooks" / "pre-receive"
        hook.write_text(f"#!/bin/sh\necho x >> {counter}\nexit 1\n")
        hook.chmod(0o755)
        self.assertNotEqual(self.record(results, "x"), 0)
        self.assertEqual(len(counter.read_text().splitlines()), 4)

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
            scripts = [
                v
                for v in (s.get("env") or {}).values()
                if isinstance(v, str) and "\n" in v
            ]
            for text in [s.get("run", ""), *scripts]:
                self.assertNotIn("${{", text, s.get("name"))

    def test_the_registry_login_takes_the_optional_token_and_user(self) -> None:
        login = next(
            s
            for s in self.all_steps()
            if s.get("uses", "").startswith("docker/login-action@")
        )
        self.assertEqual(
            login["with"]["password"], "${{ secrets.registry-token || github.token }}"
        )
        self.assertEqual(
            login["with"]["username"],
            "${{ inputs.registry-username || github.actor }}",
        )

    def test_the_registry_token_is_an_optional_secret(self) -> None:
        # PyYAML lit la clé `on` comme le booléen True.
        call = self.workflow[True]["workflow_call"]
        self.assertIs(call["secrets"]["registry-token"]["required"], False)
        self.assertEqual(call["inputs"]["registry-username"]["type"], "string")
        self.assertEqual(call["inputs"]["registry-username"]["default"], "")

    def test_the_tools_never_receive_the_git_token(self) -> None:
        compose = next(
            s
            for s in self.all_steps()
            if s.get("name") == "Composer les commandes du juge et du placeur"
        )
        self.assertNotIn("GITHUB_TOKEN", compose["run"])
        self.assertNotIn("extraheader", compose["run"])

    def test_permissions_are_the_least(self) -> None:
        self.assertEqual(self.workflow["permissions"], {})
        self.assertEqual(
            self.workflow["jobs"]["name"]["permissions"], {"contents": "read"}
        )
        self.assertEqual(
            self.screen["permissions"],
            {"contents": "write", "packages": "write", "id-token": "write"},
        )

    def compose(self) -> str:
        return next(
            s
            for s in self.all_steps()
            if s.get("name") == "Composer les commandes du juge et du placeur"
        )["run"]

    def prefix(self, name: str) -> str:
        line = next(line for line in self.compose().splitlines() if f'"{name}=' in line)
        return line

    def test_the_package_mirrors_reach_the_placer_by_name(self) -> None:
        # Exigence « la reconstruction est disponible sur un runner hébergé ».
        call = self.workflow[True]["workflow_call"]
        self.assertEqual(call["inputs"]["package-mirrors"]["type"], "string")
        self.assertEqual(call["inputs"]["package-mirrors"]["default"], "")
        env = next(s for s in self.all_steps() if s.get("name") == "Cribler")["env"]
        self.assertEqual(
            env["KNOCK_TRANSFORM_PACKAGE_MIRRORS"], "${{ inputs.package-mirrors }}"
        )
        self.assertIn(
            "-e KNOCK_TRANSFORM_PACKAGE_MIRRORS ", self.prefix("USKE_KNOCK_CMD")
        )
        self.assertNotIn("KNOCK_TRANSFORM", self.prefix("USKE_REGIS_CMD"))

    def test_the_signing_key_is_an_optional_secret(self) -> None:
        # Exigence « le placeur signe ce qu'il place ».
        secrets = self.workflow[True]["workflow_call"]["secrets"]
        for name in ("cosign-key", "cosign-password"):
            self.assertIs(secrets[name]["required"], False)
        env = next(s for s in self.all_steps() if s.get("name") == "Cribler")["env"]
        self.assertEqual(env["COSIGN_PASSWORD"], "${{ secrets.cosign-password }}")

    def test_the_placer_signs_keyless_by_default(self) -> None:
        compose = self.compose()
        self.assertIn(
            "-e KNOCK_ATTEST_SIGNER=keyless -e ACTIONS_ID_TOKEN_REQUEST_URL"
            " -e ACTIONS_ID_TOKEN_REQUEST_TOKEN",
            compose,
        )
        self.assertIn("$signer", self.prefix("USKE_KNOCK_CMD"))

    def test_the_placer_signs_with_a_key_when_given(self) -> None:
        compose = self.compose()
        self.assertIn('[ -n "$COSIGN_KEY" ]', compose)
        self.assertIn("umask 077", compose)
        self.assertIn('"$RUNNER_TEMP/cosign.key"', compose)
        self.assertIn(":/tmp/cosign.key:ro", compose)
        self.assertIn(
            "-e KNOCK_ATTEST_SIGNER=key -e KNOCK_ATTEST_KEY_REF=/tmp/cosign.key",
            compose,
        )
        self.assertIn("-e COSIGN_PASSWORD", compose)
        step_env = next(
            s
            for s in self.all_steps()
            if s.get("name") == "Composer les commandes du juge et du placeur"
        )["env"]
        self.assertEqual(step_env, {"COSIGN_KEY": "${{ secrets.cosign-key }}"})

    def test_the_judge_never_sees_the_signer(self) -> None:
        regis = self.prefix("USKE_REGIS_CMD")
        for word in ("ACTIONS_ID_TOKEN", "cosign", "COSIGN", "KNOCK_ATTEST", "$signer"):
            self.assertNotIn(word, regis)

    def composed(self, cosign_key: str) -> dict[str, list[str]]:
        """Les préfixes tels qu'`uske` les lit : écrits dans GITHUB_ENV par bash, puis shlex."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "env"
            subprocess.run(
                ["bash", "-e", "-c", self.compose()],
                check=True,
                env={
                    **os.environ,
                    "COSIGN_KEY": cosign_key,
                    "GITHUB_WORKSPACE": tmp,
                    "RUNNER_TEMP": tmp,
                    "GITHUB_ENV": str(out),
                    "HOME": tmp,
                    "REGIS_VERSION": "r",
                    "KNOCK_VERSION": "k",
                },
            )
            pairs = (line.split("=", 1) for line in out.read_text().splitlines())
            return {k: shlex.split(v) for k, v in pairs if k.endswith("_CMD")}

    def test_keyless_promotion_verifies_the_called_workflow(self) -> None:
        # Scénario « une image réparée promue sans clé » : les antislashs survivent.
        knock = self.composed("")["USKE_KNOCK_CMD"]
        for flag in (
            "KNOCK_ATTEST_SIGNER=keyless",
            "KNOCK_ATTEST_VERIFY_OIDC_ISSUER=https://token.actions.githubusercontent.com",
            (
                r"KNOCK_ATTEST_VERIFY_IDENTITY=^https://github\.com/trivoallan/uske/"
                r"\.github/workflows/extra-screen\.yml@"
            ),
            "ACTIONS_ID_TOKEN_REQUEST_URL",
            "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
        ):
            self.assertEqual(knock[knock.index(flag) - 1], "-e")

    def test_key_mode_does_not_verify_an_identity(self) -> None:
        cmds = self.composed("KEY")
        knock = cmds["USKE_KNOCK_CMD"]
        self.assertIn("KNOCK_ATTEST_SIGNER=key", knock)
        self.assertFalse([a for a in knock if a.startswith("KNOCK_ATTEST_VERIFY")])
        self.assertFalse([a for a in knock if a.startswith("ACTIONS_ID_TOKEN")])
        for arg in cmds["USKE_REGIS_CMD"]:
            self.assertNotIn("cosign", arg)

    def test_the_lock_is_the_policy_name(self) -> None:
        self.assertEqual(
            self.screen["concurrency"],
            {
                "group": "uske-screen-${{ needs.name.outputs.name }}",
                "cancel-in-progress": False,
            },
        )

    def test_no_checkout_keeps_the_token(self) -> None:
        for s in self.all_steps():
            if s.get("uses", "").startswith("actions/checkout@"):
                self.assertIs(s["with"]["persist-credentials"], False)

    def test_the_final_push_runs_always(self) -> None:
        final = step(self.workflow, "screen", "final")
        self.assertIn("always()", final["if"])
        self.assertIn("after-record.sh", final["run"])

    def test_regis_reads_the_shared_grype_db(self) -> None:
        compose = next(
            s
            for s in self.all_steps()
            if s.get("name") == "Composer les commandes du juge et du placeur"
        )
        for flag in (
            "GRYPE_DB_CACHE_DIR=/grype-db",
            "GRYPE_DB_AUTO_UPDATE=false",
            "GRYPE_DB_MAX_ALLOWED_BUILT_AGE=48h",
            "GRYPE_CHECK_FOR_APP_UPDATE=false",
        ):
            self.assertIn(flag, compose["run"])

    def test_buildkit_listens_on_loopback_only(self) -> None:
        self.assertIn(
            "-p 127.0.0.1:1234:1234", step(self.workflow, "screen", "tools")["run"]
        )

    def test_each_image_version_is_followed_by_renovate(self) -> None:
        lines = SCREEN.read_text().splitlines()
        versions = [
            i
            for i, line in enumerate(lines)
            if re.match(r"\s+(REGIS|KNOCK|BUILDKIT)_VERSION:", line)
        ]
        self.assertEqual(len(versions), 3)
        for i in versions:
            self.assertRegex(lines[i - 1], r"# renovate: datasource=docker depName=\S+")


class MovingTag(unittest.TestCase):
    """Exigence « une étiquette mobile suit chaque version »."""

    def tag_for(self, version: str) -> str:
        script = step(load(MAJOR_TAG), "tag", "name")["run"]
        with tempfile.NamedTemporaryFile("r") as out:
            subprocess.run(
                ["sh", "-c", script],
                check=True,
                env={**os.environ, "VERSION": version, "GITHUB_OUTPUT": out.name},
            )
            return out.read().strip()

    def test_a_0x_version_moves_the_minor(self) -> None:
        self.assertEqual(self.tag_for("0.10.2"), "tag=v0.10")

    def test_a_1x_version_moves_the_major(self) -> None:
        self.assertEqual(self.tag_for("1.2.0"), "tag=v1")
