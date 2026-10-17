# Plan — github-action

> **Pour les agents :** exécuter avec `superpowers:subagent-driven-development` (recommandé) ou
> `superpowers:executing-plans`, tâche par tâche. Les cases `- [ ]` suivent l'avancement.

**But :** un dépôt de politiques crible une politique depuis GitHub Actions en appelant le workflow
réutilisable `extra-screen.yml`.

**Architecture :** deux jobs. `name` lit le `metadata.name` de la politique. `screen` fait naître
ou extrait la branche du journal, lance BuildKit, compose les préfixes de `regis` et `knock`, puis
lance `uske screen`. Le journal est poussé par le crochet et une dernière fois à la fin ; les
rapports partent dans une archive attachée au run. Les scripts vivent en `env:` d'une étape
`scripts`, ce qui permet aux tests de les rejouer contre un dépôt nu.

**Outils :** GitHub Actions, Docker, BuildKit, git, `uv`, `pytest` (`unittest`), `actionlint`.

**Branche :** `feat/github-action`, partie du dernier `main`, et rebasée sur `main`, jamais
fusionnée (CLAUDE.md, Git workflow). Les messages de commit n'ont pas de portée
(`commits.scopes: []`, SDR-0017).

## Plan de documentation

| Chemin | Quadrant | Destinataire | Geste |
| --- | --- | --- | --- |
| `docs/how-to/screen-from-github.md` | guide | l'équipe qui tient un dépôt de politiques sur GitHub et veut le cribler | créée |
| `docs/reference/screen-workflow.md` | référence | qui écrit l'appel : entrées, permissions, branche, artefact, étiquettes | créée |
| `docs/architecture/arc42.md` | explication | mainteneur et auditeur : section 7 (second environnement), section 11 (`RISK-01`, `DEBT-08`) | modifiée |
| `README.md` | — | visiteur du dépôt : un lien vers le guide, à côté de « Screen locally » | modifiée |

Toutes ces pages sont en anglais (SDR-0022). La skill `diataxis` n'est pas lancée sans aval : le
classement ci-dessus a été fait à la main. Le guide décrit une tâche, la référence décrit une
interface.

## ADR

- Relus au frontmatter : les vingt fichiers de `docs/adr/`. Graphe de supersession : SDR-0022 ←
  SDR-0020 ← SDR-0002 ; SDR-0019 ← SDR-0008 ; SDR-0017 ← SDR-0006 et SDR-0010. Le plus haut
  numéro est SDR-0022.
- Relus au corps : SDR-0016 (le journal en ajout seul, que la branche git doit tenir) ; SDR-0017
  (socle commun : `extra-*.yml`, `renovate.json5` et `release.yml` intouchables ici) ; SDR-0018
  (`run` = URL du run) ; SDR-0021 (`uske screen`, `USKE_AFTER_RECORD`, trois versions séparées) ;
  SDR-0022 (langue des pages).
- Créés : **SDR-0023**, à écrire à la tâche 7.1 avec le statut `proposed`, et dont le verdict
  revient à Tristan. Il porte deux engagements durables : le screening hors cluster se distribue
  sous la forme d'un workflow réutilisable, dont le nom et les entrées forment une interface
  publique ; hors cluster, le journal vit sur une branche git dédiée du dépôt appelant.

## 1. Mesurer la variante de `regis` (finding 12)

- [x] 1.1 Prendre le digest d'une image de test.
  Lancer : `docker buildx imagetools inspect docker.io/library/alpine:3.22 --format '{{json .Manifest.Digest}}'`.
  Attendu : une chaîne `"sha256:…"`, notée `D`.
- [x] 1.2 Chronométrer la variante slim, deux fois de suite, en conteneur neuf à chaque fois :
  ```bash
  for i in 1 2; do /usr/bin/time -p docker run --rm \
    -v "$PWD/tests/fixtures/repo/playbooks:/pb:ro" -v /tmp/r$i:/out \
    ghcr.io/trivoallan/regis:0.41.0 analyze "docker.io/library/alpine@$D" \
    --playbook /pb/version/playbook.yaml -D /out -o 'report.{format}' --html; done
  ```
  Attendu : deux lignes `real` ; noter les deux durées.
- [x] 1.3 Refaire la même mesure avec `ghcr.io/trivoallan/regis:0.41.0-full`, et noter les deux
  durées.
- [x] 1.4 Écrire le résultat dans `design.md`, sous D2, au point « `regis` tourne en variante
  `-full` » : les quatre durées et le choix qui en découle. Si `-full` est plus lent que slim au
  second run, D2 retient slim avec un cache de la base grype monté depuis
  `$RUNNER_TEMP/grype-db`, et la tâche 3.1 en tient compte.
- [x] 1.5 Commit : `docs: mesurer la variante de regis pour le workflow GitHub`.

## 2. Les scripts du workflow, par leurs tests

**Fichiers :** à créer, `tests/test_screen_workflow.py` et `.github/workflows/extra-screen.yml`
(squelette, complété au groupe 3).

- [x] 2.1 Écrire le test, qui échoue tant que le workflow n'existe pas :
  ```python
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
  ```
- [x] 2.2 Lancer : `uv run python -m pytest --no-cov -q tests/test_screen_workflow.py`.
  Attendu : échec à la collecte ou dans chaque `setUp`, `FileNotFoundError: … extra-screen.yml`.
- [x] 2.3 Les tests passent au groupe 3, une fois le workflow écrit. Commit, tests seuls :
  `test: décrire le workflow GitHub de screening avant de l'écrire`.

## 3. Le workflow réutilisable

**Fichier :** à créer, `.github/workflows/extra-screen.yml`. Les épinglages d'actions reprennent
ceux de `ci.yml` et `release.yml`. `upload-artifact` est nouveau : il est épinglé ici par SHA, et
Renovate le suivra.

- [x] 3.1 Écrire le fichier :
  ```yaml
  # Workflow réutilisable : crible une politique d'un dépôt appelant par `uske screen`
  # (change github-action). Son nom et ses entrées sont une interface publique : les renommer
  # casse les appelants. Guide : docs/how-to/screen-from-github.md.
  name: uske screen

  on:
    workflow_call:
      inputs:
        policy:
          description: chemin de la politique dans le dépôt appelant
          type: string
          required: true
        registries:
          description: KNOCK_REGISTRIES, JSON sans identifiants
          type: string
          required: true
        transit:
          description: nom, dans registries, du registre de transit ; vide, rien n'est réparé
          type: string
          default: ""
        registry-username:
          description: utilisateur du registre ; vide, l'acteur du run
          type: string
          default: ""
        playbooks:
          description: répertoire des playbooks dans le dépôt appelant
          type: string
          default: playbooks
        journal-branch:
          description: branche du dépôt appelant où vit le journal
          type: string
          default: uske-journal
        report-retention-days:
          description: durée de vie de l'archive des rapports, en jours
          type: number
          default: 90
        package-mirrors:
          description: KNOCK_TRANSFORM_PACKAGE_MIRRORS, miroirs de paquets nommés par les politiques
          type: string
          default: ""
        uske-ref:
          description: réservé au banc de ce dépôt ; installe uske depuis ce commit
          type: string
          default: ""
      secrets:
        registry-token:
          description: jeton du registre ; absent, GITHUB_TOKEN
          required: false
        cosign-key:
          description: clé cosign du placeur ; absente, signature sans clé (OIDC du run)
          required: false
        cosign-password:
          description: mot de passe de cosign-key
          required: false

  permissions: {}

  env:
    USKE_VERSION: 0.9.1 # x-release-please-version
    # renovate: datasource=docker depName=ghcr.io/trivoallan/regis
    REGIS_VERSION: 0.41.0
    # renovate: datasource=docker depName=ghcr.io/trivoallan/knock
    KNOCK_VERSION: 0.16.0
    # renovate: datasource=docker depName=moby/buildkit
    BUILDKIT_VERSION: v0.34.0

  jobs:
    name:
      runs-on: ubuntu-latest
      permissions:
        contents: read
      outputs:
        name: ${{ steps.name.outputs.name }}
      steps:
        - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
          with:
            persist-credentials: false
        - uses: astral-sh/setup-uv@bec219d24cd3e171d82865faccec33120bb574f4 # v10.1.0
        - id: name
          env:
            POLICY: ${{ inputs.policy }}
            USKE_REF: ${{ inputs.uske-ref }}
          run: |
            uv tool install -q "git+https://github.com/trivoallan/uske@${USKE_REF:-v$USKE_VERSION}"
            want="$(realpath -- "$POLICY")"
            name=""
            count=0
            while IFS="$(printf '\t')" read -r path listed; do
              [ "$(realpath -- "$path")" = "$want" ] || continue
              name="$listed"
              count=$((count + 1))
            done <<EOF
            $(uske list --policies "$(dirname -- "$POLICY")" | jq -r '.[] | "\(.path)\t\(.name)"')
            EOF
            [ "$count" -eq 1 ] || { echo "::error::$POLICY : aucune politique lisible à ce chemin"; exit 1; }
            echo "name=$name" >> "$GITHUB_OUTPUT"

    screen:
      needs: name
      runs-on: ubuntu-latest
      permissions:
        contents: write
        packages: write
        id-token: write
      concurrency:
        group: uske-screen-${{ needs.name.outputs.name }}
        cancel-in-progress: false
      env:
        JOURNAL_BRANCH: ${{ inputs.journal-branch }}
        JOURNAL_REMOTE: ${{ github.server_url }}/${{ github.repository }}.git
        RUN_URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        RESULTS: ${{ github.workspace }}/results
      steps:
        - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
          with:
            persist-credentials: false
        - uses: astral-sh/setup-uv@bec219d24cd3e171d82865faccec33120bb574f4 # v10.1.0
        - name: Installer uske
          env:
            USKE_REF: ${{ inputs.uske-ref }}
          run: uv tool install -q "git+https://github.com/trivoallan/uske@${USKE_REF:-v$USKE_VERSION}"
        - name: Poser l'identité git
          run: |
            git config --global user.name "uske"
            git config --global user.email "uske@users.noreply.github.com"
        - id: scripts
          name: Écrire les scripts du journal
          env:
            BIRTH: |
              #!/bin/sh
              # Extrait la branche du journal sous $RESULTS, ou la fait naître orpheline.
              # Un push refusé n'est pas rejoué : deux premiers runs simultanés, le second échoue
              # ici, avant tout placement.
              set -eu
              auth="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$GITHUB_TOKEN" | base64 | tr -d '\n')"
              if git -c "http.extraheader=$auth" ls-remote --exit-code --heads "$JOURNAL_REMOTE" "$JOURNAL_BRANCH" >/dev/null; then
                git -c "http.extraheader=$auth" clone -q --single-branch --branch "$JOURNAL_BRANCH" "$JOURNAL_REMOTE" "$RESULTS"
              else
                rc=$?
                [ "$rc" -eq 2 ] || exit "$rc"
                git init -q -b "$JOURNAL_BRANCH" "$RESULTS"
                printf 'reports/\n' > "$RESULTS/.gitignore"
                git -C "$RESULTS" add .gitignore
                git -C "$RESULTS" commit -q -m "journal : naissance de la branche"
                git -C "$RESULTS" remote add origin "$JOURNAL_REMOTE"
                git -C "$RESULTS" -c "http.extraheader=$auth" push -q origin "HEAD:$JOURNAL_BRANCH"
              fi
            HOOK: |
              #!/bin/sh
              # USKE_AFTER_RECORD : commite le journal de la politique et le pousse ; trois rebases
              # au plus. Un échec arrête la politique, sans rien placer de plus (SDR-0021).
              set -eu
              auth="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$GITHUB_TOKEN" | base64 | tr -d '\n')"
              g() { git -C "$USKE_RESULTS" -c "http.extraheader=$auth" "$@"; }
              g add -- "$USKE_POLICY.jsonl"
              g diff --cached --quiet || g commit -q -m "journal ($USKE_POLICY) : $USKE_STEP, $RUN_URL"
              for attempt in 1 2 3; do
                g push -q origin "HEAD:$JOURNAL_BRANCH" && exit 0
                g pull -q --rebase origin "$JOURNAL_BRANCH" || { g rebase --abort 2>/dev/null || true; exit 1; }
              done
              g push -q origin "HEAD:$JOURNAL_BRANCH"
          run: |
            printf '%s' "$BIRTH" > "$RUNNER_TEMP/journal-birth.sh"
            printf '%s' "$HOOK" > "$RUNNER_TEMP/after-record.sh"
            chmod +x "$RUNNER_TEMP/journal-birth.sh" "$RUNNER_TEMP/after-record.sh"
        - name: Extraire ou faire naître la branche du journal
          env:
            GITHUB_TOKEN: ${{ github.token }}
          run: '"$RUNNER_TEMP/journal-birth.sh"'
        - uses: docker/login-action@dbcb813823bdd20940b903addbd779551569679f # v4.6.0
          with:
            registry: ghcr.io
            username: ${{ inputs.registry-username || github.actor }}
            password: ${{ secrets.registry-token || github.token }}
        - id: tools
          name: Tirer les images et lancer BuildKit
          run: |
            docker pull -q "ghcr.io/trivoallan/regis:$REGIS_VERSION-full"
            docker pull -q "ghcr.io/trivoallan/knock:$KNOCK_VERSION"
            docker run -d --name buildkitd --privileged -p 127.0.0.1:1234:1234 \
              "moby/buildkit:$BUILDKIT_VERSION" --addr tcp://0.0.0.0:1234
        - id: grype-date
          run: echo "day=$(date -u +%F)" >> "$GITHUB_OUTPUT"
        - uses: actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0
          with:
            path: ${{ runner.temp }}/grype-db
            key: grype-db-${{ steps.grype-date.outputs.day }}
        - name: Remplir la base grype une fois par jour
          run: |
            G="$RUNNER_TEMP/grype-db"
            mkdir -p "$G"
            [ -n "$(ls -A "$G")" ] || docker run --rm --user "$(id -u):$(id -g)" -v "$G:/grype-db" \
              -e GRYPE_DB_CACHE_DIR=/grype-db -e GRYPE_CHECK_FOR_APP_UPDATE=false \
              --entrypoint grype "ghcr.io/trivoallan/regis:$REGIS_VERSION-full" db update
        - name: Composer les commandes du juge et du placeur
          env:
            COSIGN_KEY: ${{ secrets.cosign-key }}
          run: |
            W="$GITHUB_WORKSPACE"; T="$RUNNER_TEMP/uske-work"; U="$(id -u):$(id -g)"
            C="$HOME/.docker/config.json"
            mkdir -p "$T"
            # Le placeur signe (D2bis) : sans clé par l'OIDC du run, ou par la clé fournie.
            # Sans clé, la promotion vérifie l'identité du workflow appelé, quel que soit son ref.
            signer="-e KNOCK_ATTEST_SIGNER=keyless -e ACTIONS_ID_TOKEN_REQUEST_URL -e ACTIONS_ID_TOKEN_REQUEST_TOKEN"
            signer="$signer -e KNOCK_ATTEST_VERIFY_OIDC_ISSUER=https://token.actions.githubusercontent.com"
            signer="$signer -e 'KNOCK_ATTEST_VERIFY_IDENTITY=^https://github\.com/trivoallan/uske/\.github/workflows/extra-screen\.yml@'"
            if [ -n "$COSIGN_KEY" ]; then
              K="$RUNNER_TEMP/cosign.key"
              (umask 077; printf '%s\n' "$COSIGN_KEY" > "$K")
              signer="-v $K:/tmp/cosign.key:ro -e KNOCK_ATTEST_SIGNER=key -e KNOCK_ATTEST_KEY_REF=/tmp/cosign.key -e COSIGN_PASSWORD"
            fi
            common="docker run --rm --network host --user $U -v $W:$W -v $T:$T -w $W"
            {
              echo "USKE_REGIS_CMD=$common -v $C:/home/regis/.docker/config.json:ro -v $RUNNER_TEMP/grype-db:/grype-db -e GRYPE_DB_CACHE_DIR=/grype-db -e GRYPE_DB_AUTO_UPDATE=false -e GRYPE_DB_MAX_ALLOWED_BUILT_AGE=48h -e GRYPE_CHECK_FOR_APP_UPDATE=false ghcr.io/trivoallan/regis:$REGIS_VERSION-full"
              echo "USKE_KNOCK_CMD=$common -v $C:/tmp/.docker/config.json:ro -e KNOCK_REGISTRIES -e KNOCK_TRANSFORM_PACKAGE_MIRRORS $signer -e BUILDKIT_HOST=tcp://127.0.0.1:1234 ghcr.io/trivoallan/knock:$KNOCK_VERSION"
              echo "USKE_AFTER_RECORD=$RUNNER_TEMP/after-record.sh"
              echo "USKE_WORK=$T"
            } >> "$GITHUB_ENV"
        - name: Cribler
          env:
            POLICY: ${{ inputs.policy }}
            PLAYBOOKS: ${{ inputs.playbooks }}
            TRANSIT: ${{ inputs.transit }}
            KNOCK_REGISTRIES: ${{ inputs.registries }}
            KNOCK_TRANSFORM_PACKAGE_MIRRORS: ${{ inputs.package-mirrors }}
            COSIGN_PASSWORD: ${{ secrets.cosign-password }}
            GITHUB_TOKEN: ${{ github.token }}
          run: |
            set -- --policy "$POLICY" --results "$RESULTS" --work "$USKE_WORK" \
              --playbooks "$PLAYBOOKS" --run "$RUN_URL"
            [ -z "$TRANSIT" ] || set -- "$@" --transit "$TRANSIT"
            uske screen "$@"
        - id: final
          name: Pousser le journal une dernière fois
          if: always() && steps.scripts.outcome == 'success'
          env:
            GITHUB_TOKEN: ${{ github.token }}
            USKE_POLICY: ${{ needs.name.outputs.name }}
            USKE_RESULTS: ${{ github.workspace }}/results
            USKE_STEP: final
          run: |
            [ -f "$USKE_RESULTS/$USKE_POLICY.jsonl" ] || exit 0
            "$RUNNER_TEMP/after-record.sh"
        - name: Archiver les rapports
          if: always()
          run: |
            [ ! -d "$RESULTS/reports" ] || tar -C "$RESULTS" -cf "$RUNNER_TEMP/reports.tar" reports
        - uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2
          if: always()
          with:
            name: uske-reports-${{ needs.name.outputs.name }}
            path: ${{ runner.temp }}/reports.tar
            retention-days: ${{ inputs.report-retention-days }}
            if-no-files-found: ignore
  ```
  La tâche 1 a retenu `-full` et montré que la base grype se télécharge à chaque jugement : le
  cache quotidien ci-dessus (étapes `grype-date`, `actions/cache` et « Remplir ») suit D2.
- [x] 3.2 Lancer : `uv run python -m pytest --no-cov -q tests/test_screen_workflow.py`.
  Attendu : `19 passed, 2 failed` ; les deux échecs sont ceux de `MovingTag`
  (`FileNotFoundError` sur `extra-major-tag.yml`), réparés au groupe 4.
- [x] 3.3 Lancer : `actionlint .github/workflows/extra-screen.yml`. Attendu : aucune sortie,
  code 0.
- [x] 3.4 Lancer : `make lint`. Attendu : code 0.
- [x] 3.5 Commit : `feat: cribler une politique depuis GitHub Actions par un workflow réutilisable`.

## 4. Version écrite par Release Please, et étiquette mobile

- [x] 4.1 Dans `release-please-config.json`, ajouter au paquet `"."` :
  `"extra-files": [{"type": "generic", "path": ".github/workflows/extra-screen.yml"}]`. Le
  marqueur `# x-release-please-version` de la ligne `USKE_VERSION` fait le reste.
- [x] 4.2 Créer `.github/workflows/extra-major-tag.yml` :
  ```yaml
  # Déplace l'étiquette mobile vers chaque version publiée (change github-action, D6) :
  # v<majeure>.<mineure> en 0.x, v<majeure> à partir de 1.0. Hors du socle : release.yml ne change pas.
  name: extra-major-tag

  on:
    release:
      types: [published]

  permissions: {}

  jobs:
    tag:
      runs-on: ubuntu-latest
      permissions:
        contents: write
      steps:
        - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
          with:
            persist-credentials: false
        - id: name
          env:
            VERSION: ${{ github.event.release.tag_name }}
          run: |
            VERSION="${VERSION#v}"
            case "$VERSION" in
              0.*) echo "tag=v$(echo "$VERSION" | cut -d. -f1,2)" >> "$GITHUB_OUTPUT" ;;
              *) echo "tag=v${VERSION%%.*}" >> "$GITHUB_OUTPUT" ;;
            esac
        - env:
            TAG: ${{ steps.name.outputs.tag }}
            SHA: ${{ github.sha }}
            GITHUB_TOKEN: ${{ github.token }}
          run: |
            auth="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$GITHUB_TOKEN" | base64 | tr -d '\n')"
            git tag -f "$TAG" "$SHA"
            git -c "http.extraheader=$auth" push -f origin "refs/tags/$TAG"
  ```
- [x] 4.3 Lancer : `uv run python -m pytest --no-cov -q tests/test_screen_workflow.py`.
  Attendu : `21 passed`.
- [x] 4.4 Lancer : `actionlint .github/workflows/extra-major-tag.yml`. Attendu : aucune sortie.
- [x] 4.5 Commit : `feat: suivre chaque version par une étiquette mobile du workflow GitHub`.

## 5. Le banc : un appelant d'exemple, rejoué sur GitHub

- [x] 5.1 Créer `examples/github/policies/alpine.yaml` :
  ```yaml
  apiVersion: knock.io/v1alpha1
  kind: MirrorPolicy
  metadata:
    name: example-alpine
    labels:
      admission-track: standard
  spec:
    artifactType: image
    source: {registry: docker.io, repository: library/alpine}
    imports:
      - name: v3
        tags: {includeRegex: "^3\\.22\\.[0-9]+$"}
        destinations: [{registry: ghcr, project: trivoallan, repository: uske-example/alpine}]
  ```
- [x] 5.2 Copier les playbooks : `cp -R tests/fixtures/repo/playbooks examples/github/playbooks`.
  Vérifier : `uske resolve --policy examples/github/policies/alpine.yaml --playbooks examples/github/playbooks`
  doit imprimer un chemin qui finit par `playbook.yaml`.
- [x] 5.3 Créer `.github/workflows/extra-screen-example.yml` :
  ```yaml
  # Banc du workflow réutilisable (change github-action, D7) : appelle extra-screen.yml par son
  # chemin, sur le code de la PR. Les PR venues d'un fork sont exclues : leur jeton ne peut pas pousser.
  name: extra-screen-example

  on:
    workflow_dispatch:
      inputs:
        policy:
          type: string
          default: examples/github/policies/alpine.yaml
    pull_request:
      paths:
        - .github/workflows/extra-screen.yml
        - .github/workflows/extra-screen-example.yml
        - examples/github/**

  permissions: {}

  jobs:
    screen:
      if: github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository
      permissions:
        contents: write
        packages: write
        id-token: write
      uses: ./.github/workflows/extra-screen.yml
      with:
        policy: ${{ inputs.policy || 'examples/github/policies/alpine.yaml' }}
        registries: '{"ghcr": {"host": "ghcr.io"}, "transit": {"host": "ghcr.io/trivoallan/uske-transit"}}'
        transit: transit
        playbooks: examples/github/playbooks
        journal-branch: uske-journal-example
        package-mirrors: '{"public": {"apt": "http://deb.debian.org", "apk": "https://dl-cdn.alpinelinux.org"}}'
        uske-ref: ${{ github.event.pull_request.head.sha || github.sha }}
  ```
- [x] 5.4 Lancer : `actionlint .github/workflows/extra-screen-example.yml`. Attendu : aucune
  sortie.
- [x] 5.5 Commit : `test: éprouver le workflow GitHub sur une politique d'exemple`, puis pousser
  la branche et ouvrir la PR, qui déclenche le banc.
- [x] 5.6 Premier run, appel minimal et branche du journal. Lancer :
  `gh run watch "$(gh run list -w extra-screen-example -L1 --json databaseId -q '.[0].databaseId')" --exit-status`.
  Attendu : code 0. Puis
  `git fetch origin uske-journal-example && git ls-tree -r --name-only origin/uske-journal-example`
  doit imprimer `.gitignore` et `example-alpine.jsonl`. Puis
  `git show origin/uske-journal-example:example-alpine.jsonl | jq -r .run | sort -u` doit imprimer
  une seule ligne, l'URL du run.
  **Si `knock` échoue à pousser vers GHCR, faute d'identifiants** (il lit
  `/tmp/.docker/config.json` par `regctl` : déduit, non éprouvé), appliquer le repli : une étape
  qui ajoute `username` et `password` (`github.actor`, `github.token`) à l'entrée `ghcr.io` de
  `KNOCK_REGISTRIES`, masquée par `::add-mask::`. L'écrire dans D2, et la question est close.
- [x] 5.7 Second run sans changement : `gh workflow run extra-screen-example.yml`, puis la même
  attente. Attendu : le journal ne gagne aucune ligne de verdict, ce qui montre que le juge n'a pas
  été appelé pour une empreinte déjà décidée.
- [x] 5.8 Archive des rapports. Lancer :
  `gh run download <id> -n uske-reports-example-alpine -D /tmp/a && tar -tf /tmp/a/reports.tar`.
  Attendu : des chemins `reports/example-alpine/sha256:…/…`, identiques à ceux que citent les
  lignes du journal.
- [x] 5.9 Reconstruction. Choisir une source que le playbook `standard` refuse sur une règle
  réparable : lancer `regis analyze` (commande de la tâche 1.2) sur `docker.io/library/nginx:1.29`,
  puis chercher dans `report.json` un échec marqué réparable. Écrire
  `examples/github/policies/repair.yaml` sur cette source, et lancer
  `gh workflow run extra-screen-example.yml -f policy=examples/github/policies/repair.yaml`.
  Attendu : le journal porte une ligne de placement après une remédiation, et l'image retenue a sa
  propre ligne de verdict. Si aucune candidate ne ressort, revenir à la personne avant de continuer.
- [x] 5.10 Chemin piégé. Lancer :
  `gh workflow run extra-screen-example.yml -f policy='x.yaml"; echo PWNED; "'`. Attendu : le job
  `name` échoue, aucune ligne de `gh run view <id> --log` n'est `PWNED` seul (le mot ne figure que dans l'écho de l'entrée), et le job `screen` ne tourne
  pas.
- [x] 5.11 Commit des corrections que le banc a demandées, avec un message qui nomme le scénario.

## 6. Documentation

- [ ] 6.1 `docs/how-to/screen-from-github.md` (guide, en anglais) : l'appel minimal en un job ;
  `registries`, `transit` et `playbooks` ; la branche du journal et la protection ; ce que l'on lit
  dans l'archive des rapports et pendant combien de temps ; l'écart du runner auto-hébergé (Docker,
  BuildKit sans root, Harbor interne). Proposer `doc-coauthoring` pour son seul test lectoral, et
  attendre l'aval.
- [ ] 6.2 `docs/reference/screen-workflow.md` (référence) : la table des entrées de D1, les
  permissions, le verrou par `metadata.name` (au plus un run en attente), le nom de l'archive, les
  étiquettes mobiles `v0.N` puis `v1`.
- [ ] 6.3 `docs/architecture/arc42.md` : section 7, sous « Infrastructure Level 1 », le runner
  GitHub comme second environnement ; section 11, une ligne à `RISK-01` et à `DEBT-08` (la branche
  git rend l'ajout seul vérifiable, à l'échelle d'un dépôt). Proposer `arc42-section-07`,
  `arc42-section-11` puis `arc42-review`, et attendre l'aval.
- [ ] 6.4 `README.md` : un lien « Screen from GitHub Actions » à côté de « Screen locally ».
- [ ] 6.5 Lancer : `make lint`. Attendu : code 0, liens compris.
- [ ] 6.6 Commit : `docs: expliquer comment cribler depuis GitHub Actions`.

## 7. ADR

- [ ] 7.1 Écrire `docs/adr/SDR-0023-workflow-github.md` en `status: proposed`, au format de
  SDR-0021 : contexte, options (action composite, workflow réutilisable, GitHub Actions comme
  planificateur), décision, conséquences. Il renvoie à `design.md` pour le détail. Proposer la
  skill `architectural-decision-records`, et attendre l'aval.
- [ ] 7.2 Demander le verdict à Tristan. Une fois reçu, passer le statut à `accepted` et citer le
  verdict en tête, comme SDR-0021.
- [ ] 7.3 Commit : `docs: consigner le workflow GitHub de screening (SDR-0023)`.

## 8. Clôture

- [ ] 8.1 Lancer : `make test`. Attendu : code 0, avec une couverture globale et par fichier d'au
  moins 90 % (aucun fichier d'`uske/` n'a changé).
- [ ] 8.2 Lancer : `openspec validate github-action --type change --strict`. Attendu :
  `Change 'github-action' is valid`.
- [ ] 8.3 Revenir à `review.md` : marquer traités les findings 12, 14 et 17.
- [ ] 8.4 Titre de la PR, en Conventional Commit sans portée :
  `feat: cribler une politique depuis GitHub Actions par un workflow réutilisable`.
