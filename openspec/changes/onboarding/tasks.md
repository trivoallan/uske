# Onboarding — plan d'application

> **But** : les dix ADR hérités portent un verdict sur réponse reçue, et
> `docs/architecture/arc42.md` existe, relu. **Approche** : recueillir toutes les réponses,
> puis écrire — un ADR `accepted` gèle son corps (`design.md`, D1). **Outils** : l'éditeur, `git`,
> la vérification par schéma de `docs/adr/`, les skills `arc42-section-01`, `arc42-section-09`,
> `arc42-review`. Aucun code, aucun test : le diff ne touche ni `uske/`, ni `deploy/`, ni
> `tests/`, ni `.github/`, ni `docs/adr/SDR-0001-record-architecture-decisions.md`.
>
> Sources : `specs/repository-method/spec.md` (quoi), `design.md` (comment), `review.md`
> (findings F1 à F8), `documentation.md` (pages dues). Toutes les commandes se lancent depuis la
> racine du dépôt, sauf mention.

**`CHECK`** désigne, dans tout ce plan, la vérification de `docs/adr/` :

```bash
( cd docs/adr && npx --yes @jackchuka/mdschema@0.15.1 check '*.md' )
```

**Procédure V — statuer un ADR.** Les tâches du groupe 4 l'appliquent telle quelle, sur le
fichier qu'elles nomment, avec les valeurs du récapitulatif (tâche 2.4). Cinq gestes, dans cet
ordre, tous dans ce seul fichier :

1. Frontmatter, `traits:` — écrire la valeur de chaque clé. Verdict `rejected` : supprimer le
   bloc `traits:` en entier, de la ligne `traits:` à la dernière clé.
2. Frontmatter, `status:` — `proposed` devient `accepted` ou `rejected`.
3. Frontmatter — `date: 2026-09-20` (ou le jour de l'application, format `AAAA-MM-JJ`) et
   `authors: [Tristan Rivoallan]`.
4. Sous le titre `### Consequences`, remplacer le commentaire HTML par deux ou trois lignes :
   ce que la décision facilite, ce qu'elle coûte.
5. **En dernier** : supprimer le mode d'emploi, de la ligne qui commence par
   `**Tout ce qui suit disparaît quand vous statuez**` jusqu'à la ligne vide qui précède
   `### Consequences`, ce titre non compris. À sa place, écrire :
   - une ligne qui dit si la proposition de la méthode est adoptée telle quelle, ou le motif
     de l'écart ;
   - **une ligne de provenance par clé** : `` `<clé>` : constatée — `<fichier>` `` ou
     `` `<clé>` : répondue — 2026-09-20 `` ;
   - pour un `rejected` : ce qui tient lieu de la décision dans ce dépôt.

   Ne toucher ni au texte au-dessus du mode d'emploi, ni à `## More Information`.

Un ADR resté *sans réponse* au récapitulatif **ne s'ouvre pas** : sa tâche se coche avec la
mention « sans réponse, fichier intact ».

## 1. Préparer la vérification

- [x] 1.1 (F1) Lancer `CHECK`. Attendu : `✗ Found 53 violation(s) in 10 file(s)`. Si la sortie
  est `sh: mdschema: command not found` : le cache `~/.npm/_npx/68b2df2189094176` a un `.bin`
  vide. Il est hors du dépôt — **demander à la personne** de le supprimer
  (`rm -rf ~/.npm/_npx/68b2df2189094176`), puis relancer. Si elle refuse, `CHECK` devient pour
  tout le plan :
  `( cd docs/adr && node ~/.npm/_npx/68b2df2189094176/node_modules/@jackchuka/mdschema/bin/cli.js check '*.md' )`
- [x] 1.2 Confirmer le point de départ : `CHECK 2>&1 | grep -c '^/'` imprime `10`, et
  `CHECK 2>&1 | grep -c SDR-0001` imprime `0`.
- [x] 1.3 Confirmer que rien d'autre n'attend : `git status --short` imprime exactement
  ` M .gitignore`, `?? openspec/changes/` et `?? openspec/discovery.md`. Autre chose : s'arrêter
  et le dire.

## 2. Trier, puis recueillir les réponses — aucune écriture dans `docs/adr/`

- [x] 2.1 Lire en entier les dix fichiers `docs/adr/SDR-0002-localization.md`,
  `SDR-0003-architecture.md`, `SDR-0004-languages.md`, `SDR-0005-validation.md`,
  `SDR-0006-commits.md`, `SDR-0007-tests.md`, `SDR-0008-documentation.md`,
  `SDR-0009-branching.md`, `SDR-0010-forge-and-ci.md`, `SDR-0011-delivery.md` — leurs sections
  `## Considered Options` et `## More Information` surtout : elles disent ce que chaque clé
  porte.
- [x] 2.2 Relever les preuves, une commande par ligne, et noter la sortie :
  `grep -n 'requires-python\|^name' pyproject.toml` ; `git remote get-url origin` ;
  `ls .github/workflows/` ; `git log --format=%s` ; `git branch -a` ;
  `ls commitlint.config.* .commitlintrc* .husky .pre-commit-config.yaml 2>&1` ;
  `ls mkdocs.yml docusaurus.config.* 2>&1` ; `grep -rn 'cov' pyproject.toml .github/ 2>&1` ;
  `grep -c '^ *#' uske/*.py`.
- [x] 2.3 (D2) Écrire le tri dans `openspec/changes/onboarding/verdicts.md`, section
  `## Tri` : un tableau `ADR | Clé | Valeurs admises | Preuve | Valeur proposée | Tas`. Un ADR
  n'est **constaté** que si *toutes* ses clés ont une preuve ; sinon il va **en entier** à
  « à choisir », valeurs constatées proposées par défaut. Valeurs admises, d'après
  `docs/adr/.mdschema.yml` :
  `localization.language.{default,documentation,commits,code,comments}` ∈ `français|anglais` ;
  `architecture.pattern` ∈ `event-driven|hexagonal|layered|microservices|monolithic|soa` ;
  `architecture.document` ∈ `arc42|ailleurs|aucun` (proposer `arc42` : accord reçu le
  2026-09-20) ; `languages.main.name` chaîne ; `validation.boundary`,
  `validation.data_files` chaînes ; `commits.scopes` liste, `commits.tool` ∈
  `commitlint|hook|aucun` ; `tests.coverage_target` libre ; `docs.tool` ∈
  `docusaurus|mkdocs|aucun`, `docs.root` chaîne, `docs.audience` ∈
  `mono-utilisateur|équipe|LS|groupe|public` ; `branching.model` ∈
  `github-flow|trunk-based|gitflow`, `branching.merge` ∈ `squash|merge-commit|rebase`,
  `branching.prefixes` liste ; `forge.host`, `ci.tool` chaînes, `ci.gate` ∈
  `bloquante|informative|aucune` ; `deploy.environments` liste, `release.tool` chaîne.
  Attendu au tri : `SDR-0004` constaté (`pyproject.toml`) ; les neuf autres à choisir.
- [x] 2.4 (F3, D1) Recueillir les réponses **en une passe** : appels consécutifs de l'outil de
  questions, quatre questions au plus par appel, **sans aucune écriture entre deux appels**.
  Première question : une seule confirmation pour tout le tas constaté, preuves affichées.
  Puis une question par ADR à choisir, `SDR-0009` en tête. Chaque question porte : ce que la
  clé change pour un agent, en une phrase ; les valeurs admises ; la preuve relevée ; la valeur
  proposée ; et toujours deux options en plus — `rejected` (la question ne se pose pas ici) et
  *sans réponse* (laisser `proposed`). Aucun verdict ne se déduit du silence ou de l'historique.
- [x] 2.5 (F2) Écrire les réponses dans `openspec/changes/onboarding/verdicts.md`, section
  `## Récapitulatif` : `ADR | Verdict | Clé | Valeur | Provenance`. L'afficher en entier à la
  personne et demander une confirmation unique : « J'écris ces verdicts ; un ADR `accepted` ne
  se corrige plus que par un nouvel ADR. » Sans oui, corriger le récapitulatif et le
  réafficher. Rien ne s'écrit dans `docs/adr/` avant ce oui.

## 3. Ouvrir les actes — la branche, puis ce qui attendait

- [x] 3.1 (D3) Lire le verdict de `SDR-0009` au récapitulatif. `accepted` avec un modèle à
  branches, **ou** *sans réponse* : `git switch -c onboarding` — attendu :
  `Switched to a new branch 'onboarding'`. Si `branching.prefixes` est renseigné, préfixer le
  nom en conséquence. Verdict qui dit de travailler sur `main` : rester sur `main` et le noter
  dans `verdicts.md`.
- [x] 3.2 (F6) Commiter le `.gitignore` seul, il est étranger au change :
  `git add .gitignore && git commit -m "chore: ignorer les skills posés, node_modules et .serena"`.
  Attendu : `1 file changed, 4 insertions(+)`.
- [x] 3.3 Commiter la découverte et le cadrage :
  `git add openspec/discovery.md openspec/changes/onboarding && git commit -m "docs: découverte et cadrage du change onboarding"`.
  Attendu : `git status --short` n'imprime rien.

## 4. Statuer les dix ADR

- [x] 4.1 Procédure V sur `docs/adr/SDR-0009-branching.md` — clés `branching.model`,
  `branching.merge`, `branching.prefixes`. Puis `CHECK 2>&1 | grep -c SDR-0009` imprime `0`.
- [x] 4.2 Procédure V sur `docs/adr/SDR-0002-localization.md` — clés
  `localization.language.default`, `.documentation`, `.commits`, `.code`, `.comments`. Puis
  `CHECK 2>&1 | grep -c SDR-0002` imprime `0`.
- [x] 4.3 Procédure V sur `docs/adr/SDR-0003-architecture.md` — clés `architecture.pattern`,
  `architecture.document`. Puis `CHECK 2>&1 | grep -c SDR-0003` imprime `0`.
- [x] 4.4 Procédure V sur `docs/adr/SDR-0004-languages.md` — clé `languages.main.name`,
  provenance « constatée — `pyproject.toml` ». Puis `CHECK 2>&1 | grep -c SDR-0004` imprime `0`.
- [x] 4.5 Procédure V sur `docs/adr/SDR-0005-validation.md` — clés `validation.boundary`,
  `validation.data_files`. Puis `CHECK 2>&1 | grep -c SDR-0005` imprime `0`.
- [x] 4.6 Procédure V sur `docs/adr/SDR-0006-commits.md` — clés `commits.scopes`,
  `commits.tool`. Puis `CHECK 2>&1 | grep -c SDR-0006` imprime `0`.
- [x] 4.7 Procédure V sur `docs/adr/SDR-0007-tests.md` — clé `tests.coverage_target`. Puis
  `CHECK 2>&1 | grep -c SDR-0007` imprime `0`.
- [x] 4.8 Procédure V sur `docs/adr/SDR-0008-documentation.md` — clés `docs.tool`, `docs.root`,
  `docs.audience`. Puis `CHECK 2>&1 | grep -c SDR-0008` imprime `0`.
- [x] 4.9 Procédure V sur `docs/adr/SDR-0010-forge-and-ci.md` — clés `forge.host`, `ci.tool`,
  `ci.gate`. Puis `CHECK 2>&1 | grep -c SDR-0010` imprime `0`.
- [x] 4.10 Procédure V sur `docs/adr/SDR-0011-delivery.md` — clés `deploy.environments`,
  `release.tool`. Puis `CHECK 2>&1 | grep -c SDR-0011` imprime `0`.
- [x] 4.11 Vérifier l'ensemble. `CHECK` : attendu `0` écart si tout a reçu une réponse ; sinon,
  les seuls fichiers nommés sont ceux portés *sans réponse* au récapitulatif — comparer les
  deux listes, elles doivent être identiques. Puis
  `grep -l 'Tout ce qui suit disparaît' docs/adr/*.md` ne liste que ces mêmes fichiers, et
  `git diff --stat -- docs/adr/SDR-0001-record-architecture-decisions.md` n'imprime rien.
- [x] 4.12 (F2) Relire `git diff -- docs/adr/` fichier par fichier : la proposition de la
  méthode en tête de `## Decision Outcome` est toujours là ; `## More Information` est intact ;
  la coupe s'arrête avant `### Consequences` ; chaque clé a sa ligne de provenance ; un
  `rejected` n'a plus de `traits:` et dit ce qui en tient lieu.
- [x] 4.13 Écrire le tableau final dans `openspec/changes/onboarding/verdicts.md`, section
  `## Tableau final`, quatre colonnes : `ADR` (lien relatif vers le fichier) `| Thème |
  Décisions | Statut`. Les dix ADR y figurent ; un ADR resté `proposed` porte *sans réponse*
  dans la colonne Décisions. L'afficher à la personne.
- [x] 4.14 Commit :
  `git add docs/adr openspec/changes/onboarding/verdicts.md && git commit -m "docs: verdicts des ADR hérités"`.

## 5. Le document d'architecture

- [x] 5.1 `mkdir -p docs/architecture && cp node_modules/surdesrails/resources/docs/arc42/index.md docs/architecture/arc42.md`.
  Attendu : `grep -c '^# ' docs/architecture/arc42.md` imprime `12` ou plus.
- [x] 5.2 Invoquer la skill `arc42-section-01` sur `docs/architecture/arc42.md`, source
  `openspec/discovery.md`. La section `# Introduction and Goals` porte : l'aperçu des exigences
  (le périmètre de la découverte) ; sous `## Quality Goals`, les quatre objectifs **dans cet
  ordre** — Sûreté, Contestabilité, Opérabilité, Minceur — chacun avec son renoncement ; sous
  `## Stakeholders`, les trois personas avec leurs attentes. Aucune technologie qu'un ADR
  statué ne décide.
- [x] 5.3 Invoquer la skill `arc42-section-09` sur le même fichier, source : les seuls ADR
  `accepted` ou `rejected` du tableau final, plus `SDR-0001`. La section
  `# Architecture Decisions` renvoie à chacun par un lien relatif `../adr/<fichier>`. Un ADR
  *sans réponse* n'y est pas présenté comme une décision.
- [x] 5.4 Invoquer la skill `arc42-review` sur `docs/architecture/arc42.md`. Corriger
  sur-le-champ tout constat critique, avec la skill de la section concernée. Attendu : aucun
  constat critique restant. Les dix sections non rédigées gardent le texte du gabarit : le
  noter au rapport, ne pas les remplir.
- [x] 5.5 Contrôler l'accord avec la découverte :
  `grep -n 'Sûreté\|Contestabilité\|Opérabilité\|Minceur' docs/architecture/arc42.md` imprime
  les quatre noms, dans cet ordre de lignes. Et, si `SDR-0003` est `accepted` :
  `grep -n 'document:' docs/adr/SDR-0003-architecture.md` imprime `document: arc42`.
- [x] 5.6 Commit :
  `git add docs/architecture/arc42.md && git commit -m "docs: document d'architecture, sections 1 et 9"`.

## 6. Mener l'arrivant aux décisions, et clore

- [ ] 6.1 (F5) Dans `README.md`, ajouter avant `## Test` une section `## Decisions`, dans la
  langue que `SDR-0002` donne à la documentation (`anglais` par défaut si *sans réponse* : le
  `README.md` l'est déjà en majorité). Trois lignes, trois liens : `docs/adr/` — les décisions
  et leur verdict ; `docs/architecture/arc42.md` — les objectifs et les décisions en un lieu ;
  `openspec/discovery.md` — les personas, les objectifs qualité ordonnés, les stories.
- [ ] 6.2 Vérifier les liens : `ls docs/adr docs/architecture/arc42.md openspec/discovery.md`
  ne rapporte aucune erreur.
- [ ] 6.3 Vérifier le périmètre : `git diff --stat main -- uske deploy tests .github` n'imprime
  rien (sur `main` : `git diff --stat cffa75a -- uske deploy tests .github`).
- [ ] 6.4 `openspec validate onboarding --type change --strict`. Attendu :
  `Change 'onboarding' is valid`.
- [ ] 6.5 Commit : `git add README.md && git commit -m "docs: mener aux décisions depuis le README"`.
  Sur une branche : ne pas pousser, ne pas ouvrir la merge request — le proposer à la personne,
  avec le tableau final en description.
