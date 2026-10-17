# Plan — screen-workflow-followups

**Branche :** `feat/screen-workflow-followups`, partie de `origin/main` (731c9e5). Les messages de
commit n'ont pas de portée (SDR-0017). Chaque tâche : test d'abord dans
`tests/test_screen_workflow.py`, puis `make lint` et `make test` verts.

## Plan de documentation

| Chemin | Quadrant | Geste |
| --- | --- | --- |
| `docs/reference/screen-workflow.md` | référence | nom de l'archive, `cosign-key` éprouvé |
| `docs/how-to/screen-from-github.md` | guide | archive par tentative, `results/` libre chez l'appelant |
| `docs/architecture/arc42.md` | explication | section 7 (cache), section 11 (`RISK-11`, dépendances d'`uske`) |

## Tâches

- [x] 1. Rejouer le job `screen` d'un run vert du banc, et noter si l'upload entre en conflit.
      Rejeu du run 39025651106 : vert, mais sans preuve (aucune empreinte due, aucune archive).
      Sonde sur la PR (runs 39026356045, 39026418538) : pas de conflit ; le rejeu supprime
      l'archive de la tentative 1, nom fixe ou suffixé (`RISK-13`).
- [x] 2. `RESULTS` sous `$RUNNER_TEMP/uske-results` ; l'étape finale lit `$RESULTS`.
- [x] 3. `actions/cache/restore` et `actions/cache/save` (sur manque de cache), au même SHA.
- [x] 4. Pas de suffixe : aucun conflit, et il ne garderait rien. `RISK-13` et le guide.
- [x] 5. Consigner l'absence d'épinglage des dépendances d'`uske` (arc42, section 11).
- [x] 6. Retirer `examples/github/playbooks/admission/` ; test : seuls des fichiers de piste.
- [ ] 7. Banc : entrée `signer`, secrets `BENCH_COSIGN_KEY` et `BENCH_COSIGN_PASSWORD` (accord de
      Tristan), puis un run en `key` ; clore ou amender `RISK-11`.
- [ ] 8. Docs, puis PR verte.
