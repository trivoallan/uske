# Screen workflow reference

`trivoallan/uske/.github/workflows/extra-screen.yml` is a reusable workflow that screens one policy
with `uske screen`. For a walk-through, see [Screen from GitHub Actions](../how-to/screen-from-github.md).
The file name and the inputs are a public interface: renaming or removing one is a breaking change.

## Inputs

| Name | Type | Default | Meaning |
| --- | --- | --- | --- |
| `policy` | string | required | Path of the policy in the calling repository. |
| `registries` | string | required | `KNOCK_REGISTRIES`: JSON, without credentials. |
| `transit` | string | empty | Name, in `registries`, of the transit registry. Empty, no source is repaired. |
| `registry-username` | string | empty | User for the login to `ghcr.io`. Empty, the actor of the run. |
| `playbooks` | string | `playbooks` | Directory of the playbooks in the calling repository, one `<track>.yaml` per track. Missing, or holding a playbook `uske` cannot read, the job fails before anything is judged. A track with no file is recorded `inconclusive` (`uske/unknown-track`). |
| `journal-branch` | string | `uske-journal` | Branch of the calling repository that holds the journal. |
| `report-retention-days` | number | `90` | Lifetime of the reports artifact, in days. |
| `package-mirrors` | string | empty | `KNOCK_TRANSFORM_PACKAGE_MIRRORS`: JSON of the mirrors that `rewritePackageSources` names. Empty, a source to repair ends in quarantine (`uske/remediation-undeclared`). |
| `uske-ref` | string | empty | Reserved for this repository's tests. Installs `uske` from this commit instead of the release tag. Do not set it. |

## Secrets

| Name | Required | Meaning |
| --- | --- | --- |
| `registry-token` | no | Token for the login to `ghcr.io`. Absent, `GITHUB_TOKEN`. |
| `cosign-key` | no | Cosign key for the placer. Absent, the placer signs without a key. Not yet proven on the bench (RISK-11). |
| `cosign-password` | no | Password of `cosign-key`. |

## Registries

The workflow logs in to `ghcr.io` only. Destinations on another registry, and sources that need a
login (a private registry, or Docker Hub beyond its anonymous pull limits), are not supported yet.

## Permissions

The caller's job must grant all three. The workflow declares them on its `screen` job.

| Permission | Level | Use |
| --- | --- | --- |
| `contents` | write | Push the journal branch. |
| `packages` | write | Push images to GHCR. |
| `id-token` | write | Keyless signing. Required even with `cosign-key`. |

A second job, `name`, reads the policy name with `contents: read`.

## Outputs and artifacts

The workflow has no outputs. It produces:

| Product | Where | Content |
| --- | --- | --- |
| Journal | Branch `journal-branch` | `<metadata.name>.jsonl`. Each line carries `run`, the URL of the run. |
| Reports | Artifact `uske-reports-<metadata.name>` | `reports.tar`, holding `reports/<name>/<digest>/…`. Kept `report-retention-days` days, at most 90 on a public repository. |

## Concurrency

The `screen` job uses the group `uske-screen-<metadata.name>`, with `cancel-in-progress: false`. The
group is keyed on the policy name, not its path. GitHub keeps at most one pending run per group: a
newer run replaces the pending one.

## Journal commits

A commit is made after each step that writes the journal, and once more at the end of the run.

```text
journal (<metadata.name>) : <step>, <run URL>
```

`<step>` is a `uske` step, such as `record` or `record-applied`, or `final`. The first commit of a
new branch reads `journal : naissance de la branche`.

## Tags

Pin the moving tag `v0.<minor>` of the `uske` release you want, for example `@v0.11`. The workflow
exists from `v0.11`.

| Tag | Moves to | Use |
| --- | --- | --- |
| `v0.N` | The latest release of minor version `0.N`. | Pin while `uske` is in 0.x. |
| `v1` | The latest 1.x release. | From 1.0 on. |

The release also pins the versions of `regis`, `knock` and BuildKit the workflow runs. The workflow
installs `uske` at the version recorded in the file.

## Keyless verification identity

In keyless mode, the promotion verifies the signature against this issuer and identity:

| Setting | Value |
| --- | --- |
| `KNOCK_ATTEST_VERIFY_OIDC_ISSUER` | `https://token.actions.githubusercontent.com` |
| `KNOCK_ATTEST_VERIFY_IDENTITY` | `^https://github\.com/trivoallan/uske/\.github/workflows/extra-screen\.yml@` |

In a reusable workflow the certificate names the called workflow, not the calling repository. The
identity is therefore hard-coded to `trivoallan/uske`, for any ref. A fork of the workflow must change
it, or the promotion refuses its own signatures. It does not bind the signature to the calling
repository.
