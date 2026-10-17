# Contribuer

Les contributions sont bienvenues. En en proposant une, vous acceptez qu'elle soit publiée sous
la licence Apache 2.0, comme le dit la section 5 de [LICENSE](LICENSE). Aucun CLA ni
`Signed-off-by` n'est demandé.

## Avant d'ouvrir une demande de fusion

- Lancez `make lint test security` sur votre poste. La CI lance les mêmes cibles.
- Titrez la demande au format [Conventional Commits](https://www.conventionalcommits.org/fr/)
  (`feat: …`, `fix: …`). Le titre devient le commit fusionné, et c'est de lui que se
  déduisent la version et le changelog.
- Signalez une vulnérabilité en privé : voir [SECURITY.md](SECURITY.md).

Les conventions et l'architecture du dépôt sont dans [CLAUDE.md](CLAUDE.md) et
[`docs/architecture/arc42.md`](docs/architecture/arc42.md).

## Test

```bash
make test       # pytest, branch coverage, fails under 90 %
make lint       # ruff, then the manifests rendered by kustomize and checked by argo lint
make security   # pip-audit, fails from HIGH
make image      # build the image and run it once
```

The CI's build steps call these targets and nothing else; it also installs the tools
(`make ci-tools`) and runs three repository checks of its own: no tracked nanopm data, actions
pinned by SHA, and a self-test of the settings script. `make lint` needs `kubectl` and `argo`
on the `PATH`.

[`tests/fixtures/repo`](tests/fixtures/repo) is a frozen copy of a policy repository — playbooks, one
policy and its refusal journal — so the tests do not depend on a checkout next door.
