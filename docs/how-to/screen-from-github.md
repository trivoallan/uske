# Screen from GitHub Actions

This guide shows how to screen one policy from a policy repository, with the reusable workflow
`trivoallan/uske/.github/workflows/extra-screen.yml`. The workflow runs `uske screen` on a
GitHub-hosted runner, writes the journal to a branch of your repository, and attaches the reports to
the run. For every input, see the [reference](../reference/screen-workflow.md).

To run the same screening on a workstation, see [Screen locally](operate.md#screen-locally).

## Before you start

- A repository that holds your policies and playbooks.
- A destination registry. The example below uses GHCR.
- A policy whose `metadata.name` is a valid name (see [operate uske](operate.md)).

## Call the workflow

Add `.github/workflows/screen.yml` to your repository. The caller chooses the trigger. This one
screens every day and on demand:

```yaml
name: screen

on:
  schedule:
    - cron: "17 3 * * *"
  workflow_dispatch:

permissions: {}

jobs:
  screen:
    permissions:
      contents: write
      packages: write
      id-token: write
    uses: trivoallan/uske/.github/workflows/extra-screen.yml@v0.9
    with:
      policy: policies/x.yaml
      registries: '{"ghcr": {"host": "ghcr.io"}, "transit": {"host": "ghcr.io/<owner>/uske-transit"}}'
      transit: transit
```

The workflow checks out your repository itself. Add no checkout step and no other step to the job.
You can also trigger on `push` to your policies.

Your job must grant the three permissions, because a reusable workflow cannot hold more than its
caller gives it. All three are always required, even if you pass `registry-token`, because the
workflow's job declares them:

| Permission | Why |
| --- | --- |
| `contents: write` | Pushes the journal to its branch. |
| `packages: write` | Lets the placer push images to GHCR. |
| `id-token: write` | Lets the placer sign without a key. GitHub rejects the call without it, even if you sign with a key. |

An organization policy can cap job permissions. If the run fails on permissions, check
Settings, Actions, General, Workflow permissions, in the organization and in the repository.

One run screens one policy. To screen several, call the workflow once per policy: add one job each,
or use a matrix over the policy paths.

```yaml
jobs:
  screen:
    strategy:
      matrix:
        policy: [policies/x.yaml, policies/y.yaml]
    permissions:
      contents: write
      packages: write
      id-token: write
    uses: trivoallan/uske/.github/workflows/extra-screen.yml@v0.9
    with:
      policy: ${{ matrix.policy }}
      registries: '{"ghcr": {"host": "ghcr.io"}}'
```

## Write the policy

The policy says where images land. A destination names a registry by its key in `registries`, and
a `project` and `repository` under it. This destination pushes to `ghcr.io/<owner>/uske-example/alpine`:

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
      destinations: [{registry: ghcr, project: <owner>, repository: uske-example/alpine}]
```

GHCR needs the owner and every path lowercase.

## Name your registries

`registries` is the JSON that knock reads as `KNOCK_REGISTRIES`. Put no credentials in it: it is a
plain input, visible in the logs.

The keys are free names. The policy's destinations and the `transit` input refer to them by key. In
the example above, the policy uses `ghcr`, and `transit` is `transit`. A `host` can carry a path, such
as `ghcr.io/<owner>/uske-transit`.

For a plain GHCR destination, `{"ghcr": {"host": "ghcr.io"}}` is enough. The owner goes in the
policy's `project`, not in the host. The workflow does not change case: write the owner in lowercase.

## Repair images with a transit registry

Set `transit` only if a policy has `remediate:` steps. The transit registry is where a repaired
image waits for the judge before it moves to its destination. Without `transit`, each source to
repair is recorded `inconclusive` (`uske/no-transit`). An unused transit is harmless.

Pick a registry whose host and path differ from every destination. Knock rejects a staging registry
that shares its host and path with a destination. On GHCR, use a separate repository path, such as
`ghcr.io/<owner>/uske-transit`, as the example above does.

## Point repairs at package mirrors

If a policy uses `rewritePackageSources`, name the mirrors in `package-mirrors`. The value is the
JSON that knock reads as `KNOCK_TRANSFORM_PACKAGE_MIRRORS`:

```yaml
      package-mirrors: '{"public": {"apt": "http://deb.debian.org", "apk": "https://dl-cdn.alpinelinux.org"}}'
```

Give the host only. Knock keeps the path of the original source, so a mirror URL with a path doubles
it. Without this input, such a source ends in quarantine (`uske/remediation-undeclared`).

## Use your own playbooks

The workflow reads playbooks from `playbooks/` in your repository, laid out as
[`examples/github/playbooks`](../../examples/github/playbooks) is (`version/playbook.yaml` for the
`standard` track). Set `playbooks` to use another directory:

```yaml
      playbooks: ci/playbooks
```

The tree under `playbooks` is the one in the example directory:

```text
playbooks/
  version/playbook.yaml          # track standard
  version/playbook-allege.yaml   # tracks derogation and redistribution
```

The policy picks the track with its label `admission-track`. If the directory or the playbook file is missing, regis fails on each digest. The run stays green,
each digest is recorded `inconclusive` with the reason `regis/exit-<N>`, and nothing is placed (see
[journal states and reasons](../reference/reasons.md)).

## Authenticate to the registry

By default the workflow logs in to `ghcr.io` as the user who started the run, with `GITHUB_TOKEN`.
That works for a demonstration.

The token reaches the judge and the placer, because both need to read and push images. `GITHUB_TOKEN`
here also carries `contents: write`, so a compromised tool could write to your repository. Beyond a
demonstration, give the workflow a token that can only manage packages:

```yaml
    with:
      registry-username: my-bot
    secrets:
      registry-token: ${{ secrets.REGISTRY_TOKEN }}
```

Set `registry-username` to the owner of the token. Left empty, it is the actor of the run. The token
is a personal access token with the scopes `write:packages` and `read:packages`.

With `GITHUB_TOKEN` on GHCR, a package that already exists and is not linked to your repository can
refuse the push. In the package settings, under Manage Actions access, add your repository with the
write role.

GHCR sets visibility per package, and a new package is usually private. Change it in the package
settings if consumers must pull without a login.

## Sign the placed images

By default the placer signs without a key, with the OIDC identity of the run. The signatures go to
the public Fulcio and Rekor services, so the name of every placed image appears in a public
transparency log. You need no secret for it.

To keep names out of a public log, give the workflow a cosign key:

```yaml
    secrets:
      cosign-key: ${{ secrets.COSIGN_KEY }}
      cosign-password: ${{ secrets.COSIGN_PASSWORD }}
```

Keep `id-token: write` in the caller even then.

## Read the journal

The workflow keeps the journal on the branch `uske-journal` of your repository. Set `journal-branch`
to use another name. You do not create it: the first run creates the branch as an orphan, with no shared history. Each
step then adds a commit, and the workflow pushes it before the next placement.

The branch is append-only, so do not protect it in a way that blocks the workflow: no required pull
request, no required status checks. Let `github-actions` push to it.

If two first runs start together, the second fails before it places anything. Run it again.

## Know what success looks like

The job succeeds when the screening ran, whatever it decided. An image that is quarantined or
inconclusive is a business outcome, not a failure. The job fails only on a technical failure, such
as a registry that is unreachable or a push that is refused.

To read the outcome, open the journal on its branch. Each line has a `state` and often a `reason`
(see [journal states and reasons](../reference/reasons.md)).

## Read the results and reports

Each journal line for a verdict or a placement has a `run` field, the URL of the run that wrote it.
To find the report for a line:

1. Open the run from the `run` URL.
2. Download the artifact `uske-reports-<policy name>`. It holds `reports.tar`.
3. Extract it. Each report sits at the path the journal line cites, relative to the journal.

The artifact lives for `report-retention-days` days, 90 by default. GitHub caps it at 90 days on a
public repository; a private repository can keep it longer, up to the limit its settings allow. After that the journal line still records the state, the playbook and the reason
(see [journal states and reasons](../reference/reasons.md)); the full report is gone.

## Avoid parallel runs on one policy

The workflow runs at most one screening per policy name. A second run waits for the first. GitHub
keeps one waiting run per group, so a third run cancels the second, and the newest wins. A cancelled
run that never started places nothing.

## Pin a version

Reference the workflow by a moving tag, currently `v0.9`. While `uske` is in 0.x, a minor version can break callers, so
the tag follows the minor version: `@v0.9`, then `@v0.10`. From 1.0 on, it will be `@v1`. The tag
also selects the versions of `regis`, `knock` and BuildKit that the run uses: you cannot override
them.

## Run on a self-hosted runner

The workflow is tested on GitHub-hosted runners only. A self-hosted runner differs in these ways:

- **Docker.** The runner needs Docker, because the judge, the placer and BuildKit run as containers.
- **BuildKit.** The workflow starts BuildKit as a privileged container. On a shared runner, replace
  it with rootless BuildKit.
- **Internal Harbor.** Describe it in `registries`, and give the runner network access to it and to
  the sources.
- **Keyless signing.** It needs the runner to reach Fulcio and Rekor. If it cannot, sign with a key.
