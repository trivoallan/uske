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
be a DNS-1123 subdomain, at most 63 characters (lowercase letters, digits, `-` and `.`, starting
and ending with a letter or digit). A policy named otherwise is skipped with one `skipped:` line
on stderr, and nothing else: no child, no journal line, and the screening stays green. Watch for
that line. `--policy` refuses such a file with exit 1.

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
pod that appends to `uske-results`, under the `uske-journal` lock. Each child uploads its new lines
as an archive of its own, `runs/<run>/out/<policy>/<created>-<child>.tgz`; the merge appends every
archive of a policy, in the order its children were created, by the journal's usual rule, so
replaying it appends nothing. Until it has run, the journal on the volume lags behind what was
placed; the decisions are in the artifact repository.

The snapshot leaves a mark, `.pending-merge/<run>`, beside the journals, and the merge clears it
once every archive is in, with no error and no conflict. A screening whose snapshot finds another run's mark **fails** at once,
naming that run: its children may have placed images whose lines are not in the journal yet, and
judging on that journal would judge them again. Every five minutes the next screening fails the
same way, until the merge succeeds.

- **A failed merge** fails the parent and keeps its mark: `argo -n uske retry <parent>` replays
  it, and the next screening starts. `argo retry` on the parent also replays its failed children:
  each one is re-created under a new name, uploads an archive of its own, and the merge takes
  both, the first one's lines included.
- **A parent that is gone** (deleted, or stopped before its merge) leaves its mark. Its children's
  archives are still under `runs/<run>/out/`; to give their lines up, remove the mark from a pod
  that mounts the volume: `rm /results/.pending-merge/<run>`.
- **A conflict**: someone wrote a line to a policy's journal after the snapshot (an arbitrated
  `quarantine`, a `uske/reopened`), on a digest the child also wrote lines on. That line wins:
  the merge does not write the child's lines on that digest, names each one on stderr
  (`<policy>: conflict: <digest>: …`, with the state, reason and date of the line that won),
  merges every other line, then fails and **keeps the mark**. The check makes the conflict
  visible; it does not undo it: the child may have placed the image before the merge. For each
  digest named, look at the registry and act on the hand-written decision (remove the placed
  tag if it should not be there). Then remove the mark by hand, `rm
  /results/.pending-merge/<run>`, from a pod that mounts the volume. Do not `argo retry` the
  parent to clear it: the hand-written line is still after the snapshot, so a replay refuses the
  same lines and fails again. The next screening judges on the journal as it now stands.
  An archive without `meta.json` (written by an older `uske export`) is refused like an unreadable
  one.
- **One policy alone**: resubmit its child with `merge=true`, and it merges its policy's lines at
  the end, under the same lock: `argo -n uske resubmit <child> -p merge=true`. It does not clear
  the parent's mark. Do it while the parent's snapshot is still in the artifact repository;
  children are deleted a day after they finish.

The mark is not a `*.jsonl`: `decisions`, the snapshot and the merge never read it as a journal.

#### The artifact repository fills up

A child's `work`, its judgements and reports go with it (`artifactGC: OnWorkflowDeletion`), a day
after it finishes; the parent's snapshot and list go with the parent, when the `CronWorkflow`'s
history limit deletes it. What the parent's merge and summary read after a child is gone, its
`out/` archives and its `done/` mark, is never collected by Argo. Add a lifecycle rule on the
bucket that expires `runs/` after a few days, longer than you would take to `argo retry` a failed
merge:

```bash
mc ilm rule add --prefix runs/ --expire-days 7 <alias>/<bucket>   # MinIO; S3 has the same rule
```

Artifact GC needs the controller's finalizer on each Workflow and the `uske` account's right to
report its GC tasks (Role `uske-executor`).

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
