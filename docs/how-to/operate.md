# Operate uske

Run the subcommands, deploy the workflow, and find out why an image was not placed. Moved from the README.

## Use

```bash
uv run uske --help
```

One subcommand per workflow step, JSON on stdout: `list`, `prepare`, `pending`, `resolve`,
`classify`, `record`, `approve`, then `dt-plan`, `dt-publish`, `dt-retire` and `census`.

One more reads the journal for a person, and is not a workflow step: `decisions` (see
[Why was an image not placed?](#why-was-an-image-not-placed)).

```bash
docker build -t uske .        # the image the workflow runs
deploy/kind/up.sh             # kind + Argo Workflows + Zot for Harbor; prints how to start a screening
deploy/kind/up.sh repair      # on that cluster: buildkitd and two sources to repair (tens of GB)
deploy/kind/up.sh down
```

[`deploy/base`](../../deploy/base) is the workflow; an overlay pins the images and names the repository to
check out.

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
The volume is `ReadWriteOnce`: if a screening is running on another node, wait for it to finish.

Each line's state and reason are explained in [`docs/reference/raisons.md`](../reference/raisons.md).

For the auditor, the same pod with other arguments:
`decisions --state placed-by-exception,abandoned --since 2026-09-01 --results /results --format md`.
