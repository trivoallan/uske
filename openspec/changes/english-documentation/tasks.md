# Plan — english-documentation

## Plan de documentation

| Chemin | Quadrant | Destinataire | Geste |
| --- | --- | --- | --- |
| `docs/adr/SDR-0022-documentation-en-anglais.md` | — | mainteneur, agents qui écrivent le dépôt | créée |
| `docs/architecture/arc42.md` | explication | lecteur extérieur qui évalue `uske`, contributeur | modifiée (traduite, glossaire FR→EN) |
| `docs/explanation/how-it-works.md` | explication | participant au talk, lecteur extérieur | modifiée (section « Décisions ») |
| `docs/reference/raisons.md` | référence | équipe applicative, auditeur | supprimée (renommée) |
| `docs/reference/reasons.md` | référence | équipe applicative, auditeur | créée (engendrée par `uske/outcomes.py`) |
| `README.md` | — | comité de sélection, lecteur extérieur | modifiée (lien vers `reasons.md`) |

## ADR

- ADR relus au frontmatter : `SDR-0001` à `SDR-0011`, `SDR-0016` à `SDR-0020` sur `origin/main`, et
  `SDR-0021` sur `feat/screen-and-policy-fan-out`. Graphe en vigueur pour la langue :
  `SDR-0002` ← `SDR-0020`.
- Relus au corps : `SDR-0002` (porte les clés `localization.language.*`), `SDR-0020` (le dépasse
  pour le seul README, et écarte `documentation: anglais`), `SDR-0019` (audience `public`, qui
  impose le glossaire), `SDR-0001` (corps gelés : les ADR ne se traduisent pas).
- À créer : `docs/adr/SDR-0022-documentation-en-anglais.md`, qui dépasse `SDR-0020` (tâche 2.1).
  Il n'est pas écrit au cadrage, parce que ce checkout est en retard sur `origin/main` : écrit ici,
  il le serait sur une branche qui n'a pas `SDR-0020`.

## 1. Branche

- [x] 1.1 Créer la branche depuis `origin/main` et y déplacer le change :
  `git fetch origin && git switch -c docs/english-documentation origin/main`, puis recopier
  `openspec/changes/english-documentation/` depuis le checkout de cadrage. Attendu :
  `git log -1 --format=%s` affiche le dernier commit de `origin/main`, et `ls docs/adr` montre
  `SDR-0020-readme-en-anglais.md`.
- [x] 1.2 Vérifier que le numéro est libre :
  `git ls-tree --name-only origin/feat/screen-and-policy-fan-out docs/adr | grep SDR-002`. Attendu :
  `SDR-0020-readme-en-anglais.md` et `SDR-0021-screen-et-repartition.md`, pas de `SDR-0022`. Si
  `SDR-0022` existe ailleurs, prendre le suivant libre et corriger ce plan.

## 2. Décision

- [x] 2.1 Écrire `docs/adr/SDR-0022-documentation-en-anglais.md` sur le gabarit de `SDR-0020` :
  `status: accepted`, `date: 2026-10-17`, `supersedes: [SDR-0020]`, et les traits
  `default: français`, `documentation: anglais`, `code: anglais`, `comments: anglais`. Le
  *Context* dit pourquoi la question de `SDR-0020` a changé (talk produit à une conférence
  internationale, lecteur au-delà du README). La *Decision Outcome* nomme ce qui reste en français
  (ADR, discovery, `.nanopm/`, artefacts OpenSpec, commits) et donne la provenance de chaque
  valeur : `documentation` répondue le 2026-10-17, les autres reprises de `SDR-0020`.
- [x] 2.2 `( cd docs/adr && npx @jackchuka/mdschema@0.15.1 check '*.md' )`. Attendu : code 0.
- [x] 2.3 Commit : `docs(adr): passer la documentation en anglais, ADR et discovery exceptés`.

## 3. Glossaire

- [x] 3.1 Relever les termes métier de `docs/architecture/arc42.md` (section *Glossary*) et de
  `uske/outcomes.py`. Pour chacun, chercher l'équivalent déjà employé par `regis` et `knock` :
  `grep -rniw "<terme anglais candidat>" ../regis/docs ../knock/docs`.
- [x] 3.2 Ajouter une colonne `English` au tableau *Glossary* de l'arc42, une ligne par terme, avant
  toute autre traduction. Un terme absent de `regis` et `knock` prend le mot du code `uske`
  (`screening`, `transit`, `quarantine`, `inconclusive`, `direct-placement`…).
- [x] 3.3 Commit : `docs(architecture): fixer l'anglais des termes du métier`.

## 4. Sortie de `uske decisions`

- [x] 4.1 Dans `tests/test_decisions.py`, remplacer les attentes des lignes 209, 325 et 326 :
  `[backdated]  [no arbitration]`, `(backdated) (no arbitration)`, `|  | backdated; no arbitration |`.
- [x] 4.2 `uv run --with pyyaml python -m unittest tests.test_decisions -v`. Attendu : 3 échecs,
  sur `test_marks_and_missing_reason` et `test_marks_appear_in_the_timeline_and_the_table`.
- [x] 4.3 Dans `uske/decisions.py`, fonction `marks()` : `"antidatée"` → `"backdated"`,
  `"arbitrage absent"` → `"no arbitration"`.
- [x] 4.4 Relancer 4.2. Attendu : `OK`. Les golden tests `tests/golden/decisions-*` ne portent
  aucune marque et ne changent pas.
- [x] 4.5 Commit : `fix(decisions): rendre les marques en anglais`.

## 5. Page des raisons

- [x] 5.1 `git mv docs/reference/raisons.md docs/reference/reasons.md`. Dans
  `tests/test_reasons.py`, changer `PAGE` en `"reasons.md"` et le message en
  `regenerate: uv run python -m uske.outcomes > docs/reference/reasons.md`.
- [x] 5.2 Traduire en anglais les textes de `REASONS` et l'en-tête que produit
  `outcomes.reference()` dans `uske/outcomes.py`, avec les termes du glossaire (tâche 3). Les codes
  et les noms de tiers (`Placement direct`, `Transformation requise puis placement`, `Quarantaine`)
  restent tels quels, et le texte de `regis/unknown-tier` dit que ce sont les noms écrits par les
  playbooks.
- [x] 5.3 `uv run python -m uske.outcomes > docs/reference/reasons.md`, puis
  `uv run --with pyyaml python -m unittest tests.test_reasons -v`. Attendu : `OK`.
- [x] 5.4 Dans `README.md` (et toute autre page trouvée par `git grep -n raisons.md`), pointer vers
  `docs/reference/reasons.md`. Attendu : `git grep -n raisons.md -- ':!openspec'` ne rend rien.
- [x] 5.5 Commit : `docs(reference): la page des raisons en anglais`.

## 6. Pages

- [x] 6.1 Traduire la section « Décisions » de `docs/explanation/how-it-works.md` (titre
  `## Decisions`). Elle dit désormais que la documentation est en anglais, et que les ADR et la
  discovery restent en français (`SDR-0022`).
- [x] 6.2 Traduire `docs/architecture/arc42.md` section par section, glossaire du 3.2 en main.
  Garder les ancres et les identifiants (`QS-nn`, `R-n`, `SDR-nnnn`, `D-nn`). Les citations de
  réponses datées gardent leur date.
- [x] 6.3 Commit : `docs(architecture): l'arc42 en anglais`.

## 7. Vérification

- [x] 7.1 Prose française restante :
  `git grep -nP '[àâçéèêëîïôûùüœ]' -- README.md docs/architecture docs/explanation docs/how-to docs/reference uske tests/golden`.
  Attendu : seulement les noms de tiers des playbooks, les citations en français volontaires (la
  devise du README) et les commentaires de code qui citent un tier.
- [x] 7.2 Cohérence du vocabulaire : pour chaque terme anglais du glossaire, `git grep -niw` sur les
  pages traduites et `uske/*.py`. Attendu : aucun synonyme concurrent (par exemple `vetting` ou
  `scan` pour `screening`).
- [x] 7.3 Suite complète : `uv run --with pyyaml python -m unittest discover tests -t .`. Attendu :
  `OK`.
- [x] 7.4 Test lectoral : un agent vierge lit `docs/architecture/arc42.md` (sections 1 à 5) et
  `docs/reference/reasons.md`, puis explique ce que fait `uske` et ce que veut dire
  `uske/remediation-undeclared`. Corriger ce qu'il comprend de travers.
- [x] 7.5 `openspec validate english-documentation --type change --strict`. Attendu : valide.
- [ ] 7.6 Dans la merge request, signaler l'ordre de fusion avec `feat/screen-and-policy-fan-out`.
  Si elle fusionne en premier, traduire au rebase ce qu'elle a ajouté (pages, entrées de
  `REASONS`).
- [x] 7.7 Commit : `docs(openspec): cocher la vérification du change`.
