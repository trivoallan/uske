# How uske works

What uske knows, how rebuilds and repairs flow, where decisions live, and where the name comes from. Moved from the README.

## What it knows

`uske` is not generic glue. Its step subcommands never run `regis` or `knock`: the workflow runs
each in its own image, by its command line, and `uske` reads the files they write. Only
`uske screen`, which runs a whole screening outside the cluster, runs them itself, by their command
lines too, and reads nothing else from them than their files and exit codes. It knows **Harbor** by its
API (`census`: enumerate the registry, subtract what was admitted, count the bypass) and
**Dependency-Track** (`dt-*`: send the SBOMs `knock` signed, retire what left the registry). The
track-to-playbook table lives in [`uske/playbooks.py`](../../uske/playbooks.py), and nowhere else.

Policies and playbooks are not in the image: a screening checks out the repository that holds them.

## Rebuilds and repairs

`knock` applies two lists of a policy. `transform:` (internal CAs, package mirrors, timezone) is
applied to every rebuild, which is placed directly: it is not judged again. `remediate:`
(`upgradePackages`) is applied only to an operation `uske` orders remediated, and the repaired
image is judged before it is placed. That needs a `knock` with remediation orders (`remediate:`
and `--applied-out`); an older one refuses the plan.

`uske` orders a remediation when the source's verdict is the tier *Transformation requise*, at
least one of its failed rules is in its track's repairable list (`REPAIRABLE` in
[`uske/playbooks.py`](../../uske/playbooks.py): `standard` repairs `cve-critical`), and every failed
**critical** rule is. A failed rule that is not critical does not stop the order. The order carries
the screening's epoch (its start, UTC). A refusal on a critical rule outside that list is not
ordered.

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

A source is repaired once per plan: if `knock` replans a repaired tag because its transform
changed, the order is renewed and the new image is judged; the source is not judged again.

A repair is also renewed on the tag it repaired. When `knock`'s plan marks an operation
`remediated: true` (the destination tag it replaces carries a repair), `uske` orders a remediation
again, even when the new source is sound: placed as is, the next upstream patch would silently
undo the repair, and an image repaired to run without root would run as root again. Without a
transit, the operation is withheld and its source recorded `inconclusive` (`uske/no-transit`). A
refused or closed source stays withheld. `uske` never reads the destination to guess: it trusts
the mark. That needs a `knock` that writes `remediated` in its plan (its current `main`); an older
one does not write the key, and nothing is renewed. A
repaired image that is judged and refused closes its source: the
journal gets a `quarantine` line on the source digest, reason `uske/remediation-refused` (older
lines say `uske/rebuild-refused`), and that source is not ordered again. An order on an import
that declares no `remediate:` closes the source too (`uske/remediation-undeclared`). A held image
left without a verdict is retried, three times at most.

The journal keeps both verdicts and the link: the source's line, the held image's line (with its
`source` and the order's `epoch`), and a placement line on the source naming the digest `knock`
wrote (`placed`): at `--apply-plan` for a copy or a transform-only rebuild, after `knock promote`
for a repaired image.

To reopen a source, append one line to the policy's results file, dated when you write it:

```json
{"ts": "2026-10-10T16:13:29Z", "ref": "<source ref>", "digest": "<source digest>", "state": "inconclusive", "ruleset": "none", "reason": "uske/reopened"}
```

The next screening judges it again. The date must be in exactly that format and not older than
the source's last line, or `uske record` refuses or drops it. The file lives on a volume: writing
to it takes a throwaway pod. A line written while a screening runs can make a child's line on the
same digest stale: the merge drops that line and says so on stderr.

## Decisions

The documentation is in English; architecture decisions, discovery and change proposals are
written in French, the language of the people who decide ([`SDR-0022`](../adr/SDR-0022-documentation-en-anglais.md)).

- [`docs/architecture/arc42.md`](../architecture/arc42.md): the quality goals, the architecture,
  the decision log and the glossary, in one place. Start here.
- [`docs/adr/`](../adr/): the architecture decisions, one per file, each with its verdict and
  where each value comes from. In French.
- [`openspec/discovery.md`](../../openspec/discovery.md): the personas, the ordered quality goals,
  and the stories to come. In French.

## The name

After [Uské Orchestra](https://nazlorecords.bandcamp.com/album/le-temple-de-la-partie-manquante),
whose *Le temple de la partie manquante* assembles ten years of other people's sounds into one piece.
`regis` and `knock` existed; what was missing is what plays them together.
