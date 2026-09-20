# Review

## Grilles retenues

- **DevEx** — le livrable se consomme. Deux lecteurs lui font face : l'agent qui lira les
  `traits:` sans les interpréter, et la personne qui répondra à la passe de verdicts.
- **Ingénierie** — ajoutée parce qu'une décision porte le cran `irréversible` : D4, un ADR
  `accepted` gèle son corps (`SDR-0001`). Le plan, lui, tient en une merge request.
- **Design** écartée : rien ne se regarde. **Contrôle** écartée : la vérification de
  `docs/adr/` atteste, elle ne refuse rien (`SDR-0001`, point 4).

Revue conduite à la main sur ces deux grilles. Les skills `/plan-eng-review`,
`/plan-devex-review` et `/plan-design-review` n'ont pas été invoquées : elles relisent un plan
de code — architecture, flux de données, tests, performance — ou un produit destiné à des
développeurs, et ce change n'écrit aucun code. Les lancer reste possible sur ce répertoire.

**Mesure prise pendant la revue** (2026-09-20), avant tout verdict : la vérification de
`docs/adr/` nomme **53 écarts dans 10 fichiers** — exactement `SDR-0002` à `SDR-0011` ;
`SDR-0001` passe. C'est le point de départ contre lequel le critère d'achèvement se lit.

## Findings et traitement

| # | Grille · dimension | Finding | Sévérité | Traitement |
| --- | --- | --- | --- | --- |
| 1 | Ingénierie · vérification | La commande prescrite par chaque ADR, `npx @jackchuka/mdschema@0.15.1 check '*.md'`, échoue sur ce poste : `sh: mdschema: command not found`. Cause : le cache `~/.npm/_npx/68b2df2189094176` a un `.bin` vide ; le binaire, lancé par `node …/@jackchuka/mdschema/bin/cli.js`, fonctionne. Un défaut du poste, pas de la méthode. | élevée | `tasks.md` : la première tâche rétablit la commande — à la personne de purger ce cache, il est hors du dépôt — et, à défaut, nomme le chemin de repli. Aucune tâche ne dépend d'une commande non essayée. |
| 2 | DevEx · erreur et reprise | Une réponse mal comprise se fige dans un ADR `accepted` ; la corriger coûte un ADR de dépassement. | élevée | `tasks.md` : récapitulatif de toutes les réponses affiché avant la première écriture ; vérification puis relecture du diff avant chaque commit. Déjà porté par D1. |
| 3 | DevEx · premier contact | La passe demande au moins neuf confirmations sur vingt-quatre clés à une personne qui n'a pas lu les dix ADR (2 000 lignes). | moyenne | `tasks.md` : chaque question porte les valeurs admises — le schéma les énumère, la mesure ci-dessus les a fait sortir —, la preuve tirée du dépôt, une valeur proposée, et toujours `rejected` et *sans réponse*. |
| 4 | Ingénierie · réversibilité | `design.md` ne disait pas le cran de réversibilité de chaque décision, que le schéma attend. | moyenne | Traité : tableau ajouté en tête des décisions. D4 seule est `irréversible`, et couverte — chaque verdict est un ADR. |
| 5 | DevEx · découvrabilité | Le change fini, rien ne mène un arrivant aux décisions : `README.md` ne cite ni `docs/adr/` ni le document d'architecture. | faible | `documentation.md` : une ligne pour `README.md`. |
| 6 | Ingénierie · périmètre | Le `.gitignore` modifié et non commité est étranger au change et partirait avec lui. | faible | `tasks.md` : commit à part, avant ceux du change. |
| 7 | Ingénierie · cohérence des sources | L'étape `adr` du schéma parle de `<repo>/adr/` et d'ADR dont même le `Status` ne se touche plus ; le dépôt range ses ADR sous `docs/adr/`, et `SDR-0001` laisse le `status` s'écrire. Statuer un ADR `proposed` n'est pas modifier un ADR `accepted`. | faible | Consigné dans `adr.md`. Aucun ADR `accepted` n'est touché. |
| 8 | DevEx · clarté | `proposal.md` ne déclarait pas de surface d'attaque, que le schéma attend. | faible | Traité : ligne ajoutée — aucune nouvelle. |

## Critère d'achèvement

- La vérification de `docs/adr/` passe de 53 écarts dans 10 fichiers à **zéro écart**, ou ne
  nomme plus que les fichiers portés *sans réponse* au tableau final.
- `arc42-review` ne laisse aucun constat critique sur `docs/architecture/arc42.md`.
- Le diff ne touche ni `uske/`, ni `deploy/`, ni `tests/`, ni `.github/`, ni `SDR-0001`.
- `openspec validate onboarding --type change --strict` passe.
- Les findings 1, 2, 3, 5 et 6 se retrouvent chacun dans une tâche cochée.
