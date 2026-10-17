# Proposition — les suites de la revue finale du workflow réutilisable

Suites du change `github-action` (archivé le 2026-10-17), relevées par sa revue finale. Objectifs
qualité : **Contestability** (rang 2) pour les points 2 et 4, **Operability** (rang 3) pour les
autres.

## Why

Le workflow `extra-screen.yml` est fusionné (trivoallan/uske#59) et éprouvé sur le banc en mode
sans clé. La revue finale l'a jugé prêt, en laissant six points :

1. Le mode clé (`cosign-key`, `cosign-password`) n'a jamais tourné de bout en bout (`RISK-11`).
2. `RESULTS` vaut `$GITHUB_WORKSPACE/results` : un dépôt appelant qui suit un répertoire
   `results/` fait échouer le clone de la branche du journal, avant tout screening.
3. `actions/cache` ne sauve la base grype qu'en fin de job réussi : un screening qui échoue la
   fait retélécharger au run suivant (environ 530 Mo).
4. Au rejeu d'un job, `upload-artifact` (v4 et plus) refuse un nom d'archive déjà pris dans le
   run. Le nom ne porte que la politique.
5. `uv tool install git+…` n'honore pas `uv.lock` : les dépendances transitives d'`uske` ne sont
   pas épinglées.
6. `examples/github/playbooks/admission/playbook.yaml` n'est lu par rien : `uske` ne lit que les
   fichiers à la racine du répertoire des playbooks.

## What Changes

- **Banc en mode clé** : `extra-screen-example.yml` gagne une entrée `signer` (`keyless` par
  défaut, ou `key`) ; en `key`, il passe les secrets `BENCH_COSIGN_KEY` et
  `BENCH_COSIGN_PASSWORD`, une clé jetable. Un run `workflow_dispatch` en `key` éprouve `RISK-11`.
- **Résultats hors de l'espace de travail** : `RESULTS` vaut `$RUNNER_TEMP/uske-results`. Seul
  `--work` est monté dans les conteneurs ; `RESULTS` ne l'était pas et ne l'est toujours pas.
- **Cache grype sauvé tôt** : `actions/cache/restore`, puis `actions/cache/save` juste après le
  remplissage, sur un manque de cache seulement. La base est sauvée avant le screening, donc même
  si le job échoue ensuite.
- **Archive au rejeu** : vérifié par une sonde sur la PR (2026-10-17). Rejouer un job ne heurte
  aucun nom, mais **supprime l'archive de la tentative précédente**, quel que soit son nom : un
  suffixe `run_attempt` ne la garde pas. Le nom ne change donc pas. La perte des rapports cités par
  la tentative rejouée est consignée (`RISK-13`), et le guide dit de lancer un nouveau run plutôt
  que de rejouer un job qui a jugé. Garder les rapports hors de l'archive du run est une suite.
- **Dépendances d'`uske`** : accepté et consigné. `uske` n'a qu'une dépendance, `pyyaml>=6.0.2`,
  sans dépendance propre ; l'épingler demanderait de reconstruire `uv.lock` côté appelant pour un
  seul paquet.
- **Exemple** : `examples/github/playbooks/admission/` est retiré ; un test vérifie que le
  répertoire n'a que des fichiers de piste.

## Impact

- `.github/workflows/extra-screen.yml`, `.github/workflows/extra-screen-example.yml`,
  `tests/test_screen_workflow.py`, `examples/github/playbooks/`.
- Docs : `docs/how-to/screen-from-github.md`, `docs/reference/screen-workflow.md`,
  `docs/architecture/arc42.md` (sections 7 et 11).
- Interface publique : rien ne change, ni entrée ni nom d'archive.
- Secrets du dépôt `uske` : deux secrets de banc, créés avec l'accord de Tristan.
