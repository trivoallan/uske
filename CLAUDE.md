## Commandes

La CI n'appelle que ces cibles du `Makefile` ; le contrat est le même dans `regis`, `knock` et `uske`.

```bash
make test       # pytest et couverture de branches, bloquant sous 90 %
make lint       # ruff, puis les manifestes rendus par kustomize et validés par argo lint
make security   # pip-audit, bloquant à partir de HIGH
make image      # construit l'image et la lance une fois
```

`make lint` demande `kubectl` et `argo` sur le `PATH`. `make ci-tools` installe `argo` dans `.bin/`, mais seulement sur Linux amd64.

Les fichiers de `.github/` listés dans `.github/workflows/socle-drift.yml` sont le socle commun : ils se modifient dans `regis`, puis se recopient ici à l'identique. Un workflow propre à `uske` s'appelle `extra-*.yml`.

## gstack (recommended)

This project uses [gstack](https://github.com/garrytan/gstack) for AI-assisted workflows.
Install it for the best experience:

```bash
git clone --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack
cd ~/.claude/skills/gstack && ./setup --team
```

Skills like /qa, /ship, /review, /investigate, and /browse become available after install.
Use /browse for all web browsing (Aside first, the bundled gstack browser as fallback). Use ~/.claude/skills/gstack/... for gstack file paths.
