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
   (`reconcile --apply-plan`).
4. `uske` appends one line per decision to a results file. Lines are added, never rewritten: weeks
   later, a refusal can still be found, explained and contested.

`uske` judges nothing and places nothing. It calls, it waits, it writes down.

> **Status — a seed.** The decisions of one screening, exposed as subcommands that an Argo Workflows
> `CronWorkflow` chains. Of the four outcomes a verdict can route to, only direct placement is
> acted on; the other three are recorded and place nothing. Not deployed anywhere yet.

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

```bash
docker build -t uske .        # the image the workflow runs
deploy/kind/up.sh             # kind + Argo Workflows + Zot for Harbor, then one screening by hand
deploy/kind/up.sh down
```

[`deploy/base`](deploy/base) is the workflow; an overlay pins the images and names the repository to
check out. In the manifests the role keeps its name — `orchestrator` — whatever tool fills it.

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
uv run --with pyyaml python -m unittest discover tests -t .
kubectl kustomize deploy/kind > /tmp/uske.yaml && argo lint --offline /tmp/uske.yaml
```

[`tests/fixtures/repo`](tests/fixtures/repo) is a frozen copy of a policy repository — playbooks, one
policy and its refusal journal — so the tests do not depend on a checkout next door.

## The name

After [Uské Orchestra](https://nazlorecords.bandcamp.com/album/le-temple-de-la-partie-manquante),
whose *Le temple de la partie manquante* assembles ten years of other people's sounds into one piece.
`regis` and `knock` existed; what was missing is what plays them together.

## Licence

[Apache-2.0](LICENSE).
