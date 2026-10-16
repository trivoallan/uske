# uske

> `regis` dit si. `knock` fait. `uske` bat la mesure, et enregistre.
>
> *`regis` says whether. `knock` does. `uske` beats time, and records.*

[`regis`](https://github.com/trivoallan/regis) judges a container image against a playbook.
[`knock`](https://github.com/trivoallan/knock) places images in your registry and attests what it
did. Neither knows the other. `uske` is what plays them together: on a schedule, for each active
policy, it runs one **screening**.

1. `knock` writes its plan — every import, update or rebuild it is about to make, with the source
   digest (`reconcile --plan-out`).
2. `uske` has `regis` judge each digest still owed a decision, with the playbook the policy's regime
   calls for.
3. `uske` hands `knock` the plan minus the refused operations; `knock` applies only that
   (`reconcile --apply-plan`). Copies are placed. What `knock` rebuilds is held in a **transit**
   registry instead (`--stage-to`).
4. `uske` has `regis` judge each held image by its own digest, then hands `knock` the list minus
   the refused ones; `knock` places those (`promote`), with their evidence, and signs them.
5. `uske` appends one line per decision to a results file. Lines are added, never rewritten: weeks
   later, a refusal can still be found, explained and contested.

`uske` judges nothing and places nothing. It calls, it waits, it writes down.

> **Status — a seed.** The decisions of one screening, exposed as subcommands that an Argo Workflows
> `CronWorkflow` chains. Of the four outcomes a verdict can route to, two are acted on: direct
> placement, and remediation when the source is refused on repairable rules. Quarantine and
> inconclusive are recorded and place nothing. Not deployed anywhere yet.

## What it knows

`uske` is not generic glue. It knows `regis` and `knock` by their command lines, **Harbor** by its
API (`census`: enumerate the registry, subtract what was admitted, count the bypass) and
**Dependency-Track** (`dt-*`: send the SBOMs `knock` signed, retire what left the registry). The
regime-to-playbook table lives in [`uske/playbooks.py`](uske/playbooks.py), and nowhere else.

Policies and playbooks are not in the image: a screening checks out the repository that holds them.

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
deploy/kind/up.sh             # kind + Argo Workflows + Zot for Harbor, then one screening by hand
deploy/kind/up.sh repair      # on that cluster: buildkitd and two sources to repair (tens of GB)
deploy/kind/up.sh down
```

[`deploy/base`](deploy/base) is the workflow; an overlay pins the images and names the repository to
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

Each line's state and reason are explained in [`docs/reference/raisons.md`](docs/reference/raisons.md).

For the auditor, the same pod with other arguments:
`decisions --state placed-by-exception,abandoned --since 2026-09-01 --results /results --format md`.

## Rebuilds and repairs

`knock` applies two lists of a policy. `transform:` (internal CAs, package mirrors, timezone) is
applied to every rebuild, which is placed directly: it is not judged again. `remediate:`
(`upgradePackages`) is applied only to an operation `uske` orders remediated, and the repaired
image is judged before it is placed. That needs a `knock` with remediation orders (`remediate:`
and `--applied-out`); an older one refuses the plan.

`uske` orders a remediation when the source's verdict is the tier *Transformation requise* and its
failed rules are all in its regime's repairable list (`REPAIRABLE` in
[`uske/playbooks.py`](uske/playbooks.py): `standard` repairs `cve-critical`), with at least one of
them failed. The order carries the screening's epoch (its start, UTC). A refusal outside that list
is not ordered.

An overlay must provide:

- the workflow parameter `transit`, a name of `KNOCK_REGISTRIES` (default `transit`). It is passed
  to `knock` only when the plan carries an order. Without it, an operation to repair is withheld
  and its source recorded `inconclusive` (`uske/no-transit`), to be judged again; copies and
  transform-only rebuilds are still placed;
- that entry **on the destination's host**, as a path prefix (`harbor.example/transit`). `regis`
  authenticates to one host, and `knock` opens one session per host: one `knock` identity writes
  to both the destination and the transit, and `regis` reads the transit;
- a transit **consumers cannot pull from**. `knock` only refuses a transit that is also a
  destination; closing it is the registry's job, and nothing here deletes from it;
- `BUILDKIT_HOST` for `knock`, and `KNOCK_TRANSFORM_PACKAGE_MIRRORS` if a policy rewrites package
  sources. A mirror is a host, without a path: `knock` keeps the path of each source.
  The bench's `buildkitd` listens in clear on the cluster network, which is fine for a throwaway
  cluster only: elsewhere, restrict who can reach it (mTLS, a NetworkPolicy).

A source is repaired once. A repaired image that is judged and refused closes its source: the
journal gets a `quarantine` line on the source digest, reason `uske/remediation-refused` (older
lines say `uske/rebuild-refused`), and that source is not ordered again. An order on an import
that declares no `remediate:` closes the source too (`uske/remediation-undeclared`). A held image
left without a verdict is retried, three times at most.

The journal keeps both verdicts and the link: the source's line, the held image's line (with its
`source` and the order's `epoch`), and a placement line on the source naming the digest `knock`
wrote (`placed`).

To reopen a source, append one line to the policy's results file, dated when you write it:

```json
{"ts": "2026-10-10T16:13:29Z", "ref": "<source ref>", "digest": "<source digest>", "state": "inconclusive", "ruleset": "none", "reason": "uske/reopened"}
```

The next screening judges it again. The date must be in exactly that format and not older than
the source's last line, or `uske record` refuses or drops it. The file lives on a volume: writing
to it takes a throwaway pod.

## Décisions

La prose de ce dépôt s'écrit en français, le code en anglais : c'est l'une des décisions ci-dessous.

- [`docs/adr/`](docs/adr/) — les décisions d'architecture, une par fichier, chacune avec son verdict
  et la provenance de ses valeurs.
- [`docs/architecture/arc42.md`](docs/architecture/arc42.md) — les objectifs qualité et le journal des
  décisions, en un lieu.
- [`openspec/discovery.md`](openspec/discovery.md) — les personas, les objectifs qualité ordonnés,
  et les stories à venir.

## Test

```bash
make test       # pytest, branch coverage, fails under 90 %
make lint       # ruff, then the manifests rendered by kustomize and checked by argo lint
make security   # pip-audit, fails from HIGH
make image      # build the image and run it once
```

The CI calls these targets and nothing else. `make lint` needs `kubectl` and `argo` on the `PATH`.

[`tests/fixtures/repo`](tests/fixtures/repo) is a frozen copy of a policy repository — playbooks, one
policy and its refusal journal — so the tests do not depend on a checkout next door.

## The name

After [Uské Orchestra](https://nazlorecords.bandcamp.com/album/le-temple-de-la-partie-manquante),
whose *Le temple de la partie manquante* assembles ten years of other people's sounds into one piece.
`regis` and `knock` existed; what was missing is what plays them together.

## Licence

[Apache-2.0](LICENSE).
