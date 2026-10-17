# Tâches — reports-survive-rerun

**Branche :** `feat/reports-survive-rerun`, partie d'`origin/main` (69f9587, `v0.11.0`). Les
messages de commit n'ont pas de portée (SDR-0017). Test d'abord dans `tests/test_screen_workflow.py`,
puis `make lint` et `make test` verts. Ce change modifie une exigence que modifie aussi
`screen-workflow-followups` : archiver celui-ci d'abord.

## Plan de documentation

| Chemin | Quadrant | Geste |
| --- | --- | --- |
| `docs/how-to/screen-from-github.md` | guide | le rapport sur la branche ; rejouer un job redevient sûr |
| `docs/reference/screen-workflow.md` | référence | produits : rapports sur la branche, archive en copie |
| `docs/architecture/arc42.md` | explication | section 7 (branche et archive), section 9 (`SDR-0024`), `RISK-13` clos |
| `docs/adr/SDR-0024-rapports-sur-la-branche.md` | décision | amende `SDR-0023` sur les rapports |

## Tâches

- [x] 1. Comparer les options sous Contestability ; Tristan retient A (2026-10-17).
- [x] 2. Le crochet commite `reports/<nom>/` avec `<nom>.jsonl`, `-f` compris ; seulement la
      politique du job.
- [x] 3. La branche naît par un commit vide, sans `.gitignore`.
- [x] 4. Docs (plan ci-dessus).
- [x] 5. Banc : run 39028551786, une empreinte jugée, job rejoué ; le rapport cité reste dans le
      commit de sa ligne. La tentative 2 a montré que l'archive reprenait toute la branche :
      corrigé (témoin `.git/uske-cloned`).
- [ ] 6. PR verte.
