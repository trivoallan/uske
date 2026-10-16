# Contribuer

Les contributions sont bienvenues. En en proposant une, vous acceptez qu'elle soit publiée sous
la licence Apache 2.0, comme le dit la section 5 de [LICENSE](LICENSE). Aucun CLA ni
`Signed-off-by` n'est demandé.

## Avant d'ouvrir une demande de fusion

- Lancez `make lint test security` sur votre poste. La CI lance les mêmes cibles.
- Titrez la demande au format [Conventional Commits](https://www.conventionalcommits.org/fr/)
  (`feat: …`, `fix(journal): …`). Le titre devient le commit fusionné, et c'est de lui que se
  déduisent la version et le changelog.
- Signalez une vulnérabilité en privé : voir [SECURITY.md](SECURITY.md).

Les conventions et l'architecture du dépôt sont dans [CLAUDE.md](CLAUDE.md) et
[`docs/architecture/arc42.md`](docs/architecture/arc42.md).
