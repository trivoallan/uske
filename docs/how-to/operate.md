# Operate uske

Run the subcommands, screen on your machine, deploy the workflow, and find out why an image was
not placed. Moved from the README.

## Use

```bash
uv run uske --help
```

One subcommand per workflow step, JSON on stdout: `list`, `prepare`, `pending`, `resolve`,
`classify`, `record`, `approve`, then `export` and `merge` (a child's new lines, then the journal;
see [The workflow](#the-workflow)), then `dt-plan`, `dt-publish`, `dt-retire` and `census`. The step
subcommands never run `regis` or `knock`: the workflow runs each in its own image.

Two more are not workflow steps. `screen` runs a whole screening in one command, outside the
cluster, and is the only one that runs `regis` and `knock` (see [Screen locally](#screen-locally)).
`decisions` reads the journal for a person (see
[Why was an image not placed?](#why-was-an-image-not-placed)).

```bash
docker build -t uske .        # the image the workflow runs
deploy/kind/up.sh             # kind + Argo Workflows + Zot for Harbor; prints how to start a screening
deploy/kind/up.sh repair      # on that cluster: buildkitd and two sources to repair (tens of GB)
deploy/kind/up.sh down
```

[`deploy/base`](../../deploy/base) is the workflow; an overlay pins the images and names the repository to
check out.

A policy's `metadata.name` names its journal, its reports and its child Workflow's label: it must
be a DNS-1123 label of at most 63 characters (lowercase letters, digits, `-` and `.`). A policy
named otherwise is skipped (`skipped:` on stderr), and `--policy` refuses it with exit 1.

## Screen locally

`uske screen` runs the steps of one child Workflow for each policy, in the same order, with the
same decisions: plan, judge each digest still owed a decision, record, approve, apply, judge the
held images, promote the sound ones, record. It writes each decision to the journal before the
placement it allows.

```bash
uv run uske screen --policies policies/ --playbooks playbooks/ --results results/ \
  --work /tmp/screen --transit transit
uv run uske screen --policy policies/redis.yaml --playbooks playbooks/ --results results/ --judge-only
```

- `--policies <dir>` screens every policy, in `uske list` order; `--policy <file>` screens one.
- `--judge-only` plans and judges, prints the verdict lines, and records and places nothing: the
  check for a pull request.
- `--work` holds the plans, reports and lines, laid out like `/work` in the workflow. Unset, a new
  temporary directory is named on stderr and kept: read it to diagnose a failed policy.
- `--transit` names the registry remediated images are held in. Unset, no source is repaired:
  each source to repair is recorded `inconclusive` (`uske/no-transit`), with a warning on stderr.

It runs `regis` and `knock` from `PATH`, without a shell, and reads only the files they write and
their exit codes. Three environment variables change that:

```bash
# A prefix replaces the command name; the arguments are appended.
export USKE_REGIS_CMD="docker run --rm -v $PWD:$PWD ghcr.io/trivoallan/regis:VERSION"
export USKE_KNOCK_CMD="docker run --rm -v $PWD:$PWD --env-file knock.env ghcr.io/trivoallan/knock:VERSION"
# Run by `sh -c`, with USKE_POLICY and USKE_RESULTS set, after each step that wrote the journal.
export USKE_AFTER_RECORD='git -C "$USKE_RESULTS" add -A && git -C "$USKE_RESULTS" commit -qm "journal($USKE_POLICY)"'
```

`uske` hands the tools the paths it sees: mount the work directory and the results directory
**at the same path** in a tool's container (`-v "$PWD:$PWD"` above, with `--work` and `--results`
under it). A path the container cannot see makes `knock` fail (exit 1) or `regis` give
`inconclusive`, never a placement.

The hook runs after each journal write and before the placement that follows: commit the
journal there, as `base-images` does, and no image is placed without its decision committed. A
hook that fails stops its policy, with nothing more placed.

On stdout, one JSON object per policy: `policy`, `judged`, `approved`, `ordered`, `promoted` and
`outcome` (`ok` or `failed`); with `--judge-only`, the verdict lines. Exit 0 when every policy
went through, whatever its verdicts (`quarantine` and `inconclusive` included); 1 when one failed
(a missing tool, a journal write, the hook, `--apply-plan` or `promote`), after the others were
screened; 2 for a usage error. A missing tool is checked before anything is written.

Reports are copied to `reports/<policy>/<digest>/<run>.<ext>`, relative to `--results`, where
`<run>` is `--run` or the epoch; the journal line cites the Markdown one (the HTML without it) by
that relative path, so the journal can travel in a git repository.

## The workflow

The `CronWorkflow` starts the parent, `uske-screening`. It checks out the repository once and
fixes its commit, the epoch and the `run` written on every line, snapshots the journals, then
creates one child Workflow per policy, `uske-policy`, labelled `uske.io/policy=<name>` and owned
by the parent: deleting the parent deletes its children. A failed child does not stop the
others; the parent fails if one did, and names it.

Two ceilings, both 1 in the base and on the kind bench: the parent's `parallelism` (policies at a
time) and the child's (steps at a time, so judgements at a time). They are integers, not
parameters: an overlay sets them with a kustomize patch.

```yaml
patches:
  - target: {kind: WorkflowTemplate, name: uske-screening}
    patch: |-
      - {op: replace, path: /spec/parallelism, value: 20}
  - target: {kind: WorkflowTemplate, name: uske-policy}
    patch: |-
      - {op: replace, path: /spec/parallelism, value: 4}
```

No volume is shared. A child passes its work from step to step as Argo artifacts, on a copy of its
policy's journal taken from the parent's snapshot, and uploads its new lines before any
placement. The overlay must provide the artifact repository: the configmap
`artifact-repositories`, key `default-v1` (S3 or MinIO; the bench installs MinIO,
[`deploy/kind/minio.yaml`](../../deploy/kind/minio.yaml)). If it cannot be reached, nothing is
placed.

After every child, failed ones included, the parent's `merge` step runs `uske merge`: the only
pod that writes `uske-results`, under the `uske-journal` lock. It appends each child's lines by the
journal's usual rule, so replaying it appends nothing. Until it has run, the journal on the volume
lags behind what was placed; the decisions are in the artifact repository.

- **A failed merge** fails the parent: `argo -n uske retry <parent>` replays it.
- **One policy alone**: resubmit its child with `merge=true`, and it merges its own lines at the
  end, under the same lock: `argo -n uske resubmit <child> -p merge=true`. Do it while the parent's
  snapshot is still in the artifact repository; children are deleted a day after they finish.

The `policy-<name>` and `uske-journal` locks are namespace resources: run **one namespace per
`uske-results` volume**, or two writers could meet on a journal.

### Why was an image not placed?

The journal lives on the `uske-results` volume. Read it from a throwaway pod that mounts the
volume read-only, in the namespace where the `CronWorkflow` runs, with the image it runs:

```bash
NS=uske IMAGE=ghcr.io/trivoallan/uske:VERSION REF=docker.io/library/redis:7.2.8
kubectl -n "$NS" run uske-decisions --rm -i -q --restart=Never --image="$IMAGE" --overrides='{
  "spec": {
    "volumes": [{"name": "results", "persistentVolumeClaim": {"claimName": "uske-results", "readOnly": true}}],
    "containers": [{
      "name": "uske-decisions", "image": "'"$IMAGE"'",
      "args": ["decisions", "'"$REF"'", "--results", "/results", "--format", "md"],
      "volumeMounts": [{"name": "results", "mountPath": "/results", "readOnly": true}]
    }]
  }
}'
```

Paste the output into the ticket: a Mermaid timeline per image, then the full table, with the
rule that refused it and who decided an exception. References are matched in full; a short one
(`redis:7.2.8`) gets the full ones suggested. The lines the command writes on stderr (the
journals it read, a suggestion) may show up before the Markdown: leave them out of the ticket.
The volume is `ReadWriteOnce`: if a screening's snapshot or merge is running on another node, wait
for it to finish. Lines decided since the last merge are not there yet.

Each line's state and reason are explained in [`docs/reference/reasons.md`](../reference/reasons.md).

For the auditor, the same pod with other arguments:
`decisions --state placed-by-exception,abandoned --since 2026-09-01 --results /results --format md`.
