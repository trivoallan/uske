# Review

## Grilles retenues

Deux grilles, choisies par ce que le livrable fait à qui lui fait face.

- **DevEx** — le livrable se consomme : une sous-commande, ses options, ses codes de sortie, lus par
  l'équipe applicative et l'auditeur.
- **Contrôle** — le livrable ne refuse rien, mais il dit ce qui a été refusé et pourquoi ; un rendu
  qui trompe l'auditeur trahit la contestabilité (objectif qualité de rang 2) aussi sûrement qu'un
  journal raturé.

L'**Ingénierie** s'y ajoute pour la testabilité des scénarios et les pièges de Mermaid, sans
décision `irréversible` : la commande n'écrit rien. La grille Design ne s'applique pas : la sortie
est du texte.

**Conduite.** Revue le 2026-10-16, sur `proposal.md` et le delta `decision-lookup`. L'auteur ne
s'est pas relu seul : un relecteur à contexte neuf a lu les deux fichiers contre `uske/cli.py`,
`uske/results.py`, la fixture `redis-7`, SDR-0016, le `README.md` et le workflow. L'auteur a
revérifié dans le code les findings 2, 6, 7 et 9 (`metadata.name: a-4711-redis-7`, docstring
« exit 2 a usage error », forme `<dépôt>@<empreinte>` de `_target`, même `ts` pour l'image retenue
et la clôture). Les skills `plan-devex-review` et `plan-eng-review` n'ont pas été lancées : elles
s'invoquent avec l'aval de la personne, qui n'a pas été demandé pour cet artefact.

**Ce que la revue déduit sans exécution** : la forme des `ref` d'un vrai journal (finding 7), le
comportement exact du parseur Mermaid sur `title` et `;` (finding 11).

## Findings et traitement

| # | Grille · dimension | Finding | Sévérité | Traitement |
| --- | --- | --- | --- | --- |
| 1 | Contrôle · complétude | Un `--results` erroné, une politique mal nommée ou un répertoire vide rendaient `[]` et le code 0, comme « aucune décision » : `results.read` rend `[]` pour un fichier absent. | Majeure | Rien à lire est une erreur (code 1) ; les fichiers lus et leur nombre de lignes s'écrivent sur la sortie d'erreur. Scénario « Rien à lire ». |
| 2 | DevEx · cohérence | `--policy NOM` contredisait `pending`, `record` et `approve`, qui prennent le chemin ; le journal porte le `metadata.name`, pas le nom du YAML. | Majeure | `--policy` prend le chemin. Alternative consignée. |
| 3 | Contrôle · regroupement | Grouper « par empreinte » enchaînait la quarantaine d'une politique et l'exception d'une autre comme une seule histoire. | Majeure | Groupes par politique puis par empreinte, titrés par la politique. Scénario dédié. |
| 4 | Contrôle · ordre | Trier par `ts` rangeait « à sa place » une exception ajoutée après coup et antidatée. | Majeure | Ordre du fichier, qui fait foi ; ligne antidatée marquée, `backdated` en JSON. Alternative consignée. |
| 5 | Ingénierie · lecture | `results.read` laisse passer une trace Python sans fichier ni ligne, accepte un non-objet, et casse sur une clé manquante ; un `ts` hors format fausse `--since` en silence. | Majeure | Un lecteur dédié, numéroté, qui échoue en `error:` sur JSON invalide, non-objet, clé manquante, `ts` mal formé, clé `policy` déjà présente. Deux scénarios. |
| 6 | Ingénierie · testabilité | Les scénarios n'avaient pas `--results`, et la fixture n'a pas le nom d'un vrai journal. | Majeure | Préambule de la spec : fixture copiée en `<tmp>/a-4711-redis-7.jsonl`, `--results <tmp>`. Les valeurs des scénarios sont vérifiées contre la fixture. |
| 7 | Contrôle · correspondance | Chercher une source par sa référence perdait ses reconstructions, qui portent une référence du transit ; `<dépôt>@sha256:` ne correspondait jamais. | Majeure | `IMAGE` se résout en empreintes, puis s'étend par `source` et `rebuilt` ; `@sha256:` accepté ; rappel sur la sortie d'erreur pour une référence courte. |
| 8 | Contrôle · objectif | Une décision humaine sans nom (la réouverture du `README.md`) ne se distinguait pas à l'œil. | Majeure | Marque « arbitrage absent » sur toute ligne hors des quatre états, ou réouverture, sans `arbitration`. La recette passe en question ouverte. |
| 9 | DevEx · codes de sortie | Le code 1 pour une date mal formée contredisait la convention « exit 2, erreur d'usage ». | Mineure | Validation par argparse, code 2 ; scénario corrigé. |
| 10 | Contrôle · fuseau | « Ce jour-là » ne disait pas en quel fuseau. | Mineure | Jour UTC, horodatage rendu avec `Z`. |
| 11 | Ingénierie · Mermaid | Le titre, `\r`, `%%`, `;`, la raison absente et les sauts de ligne du tableau n'étaient pas couverts ; l'assertion « aucun `:` hors séparateurs » était floue. | Mineure | Échappement étendu et ordonné ; période = date seule ; raison absente `—` ; golden test d'échappement sur une ligne fabriquée. |
| 12 | Contrôle · vocabulaire | « Qui, quand, pourquoi » fixait en douce `by`, `date`, `reason`. | Mineure | Rendu générique `clé: valeur` dans l'ordre du fichier. |
| 13 | Contrôle · fichiers lus | « Tous les fichiers » lirait `reports/` et les sauvegardes ; une clé `policy` d'origine serait écrasée. | Mineure | `*.jsonl` du premier niveau, sans récursion ; clé `policy` présente = erreur. |
| 14 | Ingénierie · YAGNI | La `timeline` coûte plus que le tableau sur 1 à 3 lignes par empreinte. | Mineure | Écarté : la chronologie Mermaid est demandée par la personne. Consigné dans les alternatives. |
| 15 | DevEx · découvrabilité | `--state` à virgules quand `census --project` se répète ; docstring et `README.md` disent « une sous-commande par étape » ; `report` est un chemin du volume. | Mineure | Virgules gardées et écrites dans l'aide ; docstring et `README.md` corrigés par une tâche ; `report` rattaché à la question ouverte sur l'accès. `--results` reste requis, comme chez les voisins. |

## Critère d'achèvement

La revue est close quand :

- les findings 1 à 13 ont modifié le delta `decision-lookup` et `proposal.md` (fait le 2026-10-16) ;
- chaque scénario du delta a son test, et les trois golden tests (`text`, `md`, échappement)
  passent ;
- le finding 15 a sa tâche (docstring, `README.md`, aide de `--state`) cochée ;
- le finding 14 reste écarté sauf décision contraire de la personne ;
- ~~la tâche 8 de `tasks.md` porte le temps mesuré de la recette sur le banc (revue DX, D11)~~ :
  abandonné par décision de la personne le 2026-10-16 (voir la tâche 8) ; la mesure revient à
  `/devex-review` après livraison.

## Revue DX (`/plan-devex-review`, 2026-10-16)

Mode **DX POLISH** (D7) : rien n'est ajouté au périmètre, et chaque point de contact est revu.
Produit : une CLI (D1). Pas de design doc gstack : `proposal.md` en tient lieu (D3).

### Persona

```
TARGET DEVELOPER PERSONA
========================
Who:       la responsable plateforme, opératrice relais (D2)
Context:   un dev d'équipe applicative demande « pourquoi mon image n'est pas dans Harbor ? »
Tolerance: quelques minutes ; elle a kubectl et l'accès au cluster, pas le temps d'écrire un pod
Expects:   une commande copiable qui lit le volume et rend quelque chose de collable dans le ticket
```

### Récit, validé tel quel (D4)

Le dev lui écrit. Elle sait que `uske decisions` existe, mais rien ne dit comment atteindre le
volume `uske-results` (ReadWriteOnce), sinon « writing to it takes a throwaway pod » (README). Elle
écrit un `kubectl run --overrides` à la main [observé : `ENTRYPOINT ["python", "-m", "uske"]`].
Elle tape `redis:7.2.8` et obtient `[]` [prévu par la spec], puis recommence avec la référence
complète. `--policy CHEMIN` ne lui sert à rien, car les politiques ne sont pas dans l'image
[observé : README]. Elle colle le Markdown, dont le lien `report` mène à `/results/reports/…`, que
le dev ne peut pas ouvrir [observé : `workflowtemplate.yaml:195`]. Estimation : 10 à 20 minutes la
première fois.

### Comparaison

| Outil | Du départ au résultat | Temps et type de preuve | Choix DX | Source |
|------|----------------|----------------------|-----------|--------|
| Kyverno, refus en *enforce* | `kubectl get events`, raison `PolicyViolation` | estimé < 2 min ; aucune trace durable | kubectl natif, sans historique | [policy reports](https://main.kyverno.io/docs/policy-reports) |
| Kyverno PolicyReport | `kubectl get policyreport -A` | estimé < 2 min ; état courant seulement | ressource Kubernetes | [guides/reports](https://main.kyverno.io/docs/guides/reports) |
| Harbor, pull refusé | erreur au pull, puis UI de scan | estimé 2–5 min ; pas de CLI documentée | l'erreur nomme la politique | [goharbor#19486](https://github.com/goharbor/harbor/issues/19486) |
| `uske decisions`, avant la revue | pod écrit à la main | estimé 10–20 min | historique complet, accès non documenté | ce change |
| `uske decisions`, après la revue | recette copiable du README | **objectif 2–5 min (D5), à mesurer (D11)** | historique complet, recette lecture seule | ce change |

Les temps des pairs sont estimés d'après leur documentation, pas mesurés. Aucun des pairs ne garde
l'historique.

### Moment magique (D6)

La responsable colle **une seule sortie** dans le ticket, et le dev y voit, rendus par GitHub ou
GitLab, la frise de son image, la règle qui a bloqué et qui a tranché. Le véhicule est la recette du
README, qui se termine par `--format md` (tâche 7.1), et qui est essayée une fois sur le banc
(tâche 8).

### Parcours

```
STAGE           | ELLE FAIT                              | FRICTION                          | STATUS
----------------|----------------------------------------|-----------------------------------|--------
1. Discover     | uske --help, README « Why was an       | aucune                            | ok
                | image not placed? »                    |                                   |
2. Install      | copie la recette kubectl run           | pas de recette (D5)               | fixed
3. Hello World  | lance avec la référence du dev         | réf. courte → [] (D8)             | fixed
4. Real Usage   | filtre par politique                   | --policy CHEMIN inutile (D9)      | fixed
5. Debug        | lit les erreurs                        | messages sans cause ni remède     | fixed (routine)
6. Upgrade      | —                                      | commande neuve, rien ne casse     | ok
```

### Rapport de première utilisation

```
FIRST-TIME DEVELOPER REPORT
============================
Persona: responsable plateforme, relais
Attempting: uske decisions, depuis la question du dev jusqu'au ticket

T+0:00  Ouvre le README, section « Why was an image not placed? » : une recette copiable.  [D5, D6]
T+0:40  Remplace NS, IMAGE, REF. Tape « redis:7.2.8 » comme le dev l'a écrit.
T+1:10  [] ; stderr : « did you mean: docker.io/library/redis:7.2.8 ». Recolle.            [D8]
T+1:40  Le Markdown sort : frise, tableau, arbitre, rapport « (volume uske-results) ».     [D10]
T+2:30  Colle dans le ticket. Fin.
Risque à mesurer : PVC ReadWriteOnce attaché ailleurs pendant un screening (tâche 8.3).
```

### Décisions de la revue DX

| # | Question | Réponse |
| --- | --- | --- |
| D1 | Type de produit | CLI |
| D2 | Persona | responsable plateforme, relais |
| D3 | `/office-hours` d'abord | passé |
| D4 | Le récit | juste |
| D5 | Objectif de temps | compétitif, 2–5 min, recette dans le README |
| D6 | Moment magique | la recette se termine par `--format md` |
| D7 | Mode | DX POLISH |
| D8 | Référence courte | suggérer sur stderr, stdout inchangé |
| D9 | `--policy` | `--policy-name NOM`, un nom inconnu liste les noms présents |
| D10 | Rapport dans le ticket | en code, suivi de « (volume uske-results) » |
| D11 | Mesurer l'objectif | un passage chronométré sur le banc kind |
| D12 | TODO notification | non ajouté ; reste en question ouverte |
| D13 | TODO hébergement des rapports | non ajouté ; reste en question ouverte |

**Travail courant, sans nouvelle décision** (passe 3, messages d'erreur dans le contrat déjà
déclaré) : `--results` vide rappelle que c'est le point de montage du volume ; une date mal formée
donne la forme attendue ; l'aide de `--results` et de `--policy-name` dit d'où vient la valeur.
La recette monte le volume en `readOnly`, ce qui fait tenir « la lecture ne modifie jamais le
journal » par Kubernetes en plus du code.

### Passes

| Passe | Avant | Après | Ce qui reste |
| --- | --- | --- | --- |
| 1. Getting started | 3 | 7 | le temps réel, mesuré en tâche 8 ; le PVC RWO |
| 2. CLI | 6 | 8 | JSON par défaut, décidé au cadrage : la recette passe `--format md` |
| 3. Erreurs | 5 | 8 | pas de lien vers une doc par erreur (pas de site de doc) |
| 4. Documentation | 3 | 7 | une seule page (README), pas de référence générée |
| 5. Mise à jour | 8 | 8 | commande neuve ; `policy` et `backdated` réservés dans le JSON |
| 6. Environnement | 7 | 8 | rien |
| 7. Communauté | 5 | 5 | dépôt privé, l'ouverture est un « non » déclaré de la stratégie |
| 8. Mesure | 2 | 6 | un seul passage chronométré, pas de mesure continue |

### Hors périmètre

- Un accès outillé en moins de 2 minutes (un `WorkflowTemplate`) : il élargirait le change aux
  manifestes (D5).
- La notification d'un refus à l'équipe applicative, et l'hébergement des rapports : questions
  ouvertes de `proposal.md`, non reportées dans `TODOS.md` (D12, D13).
- Ouvrir le dépôt et animer une communauté : un « non » de la stratégie, jusqu'à dix screenings
  d'affilée.

### Ce qui existe déjà

- Le banc `deploy/kind/up.sh` construit `uske:dev` depuis l'arbre courant et joue un screening :
  c'est le terrain de la tâche 8.
- La convention `error:` et les codes 1 et 2 de `uske/cli.py` (`main`, `Failure`, argparse).
- `results.read` et le format des lignes fixé par SDR-0016.

### Scorecard

```
+====================================================================+
|              DX PLAN REVIEW — SCORECARD                             |
+====================================================================+
| Dimension            | Score  | Prior  | Trend  |
|----------------------|--------|--------|--------|
| Getting Started      |  7/10  |  3/10  |  ↑     |
| API/CLI/SDK          |  8/10  |  6/10  |  ↑     |
| Error Messages       |  8/10  |  5/10  |  ↑     |
| Documentation        |  7/10  |  3/10  |  ↑     |
| Upgrade Path         |  8/10  |  8/10  |  =     |
| Dev Environment      |  8/10  |  7/10  |  ↑     |
| Community            |  5/10  |  5/10  |  =     |
| DX Measurement       |  6/10  |  2/10  |  ↑     |
+--------------------------------------------------------------------+
| TTHW                 | 2–5 min (objectif) | 10–20 min (estimé) | ↑ |
| Competitive Rank     | Competitive (visé, non mesuré)                |
| Magical Moment       | designed via recette README → --format md     |
| Product Type         | CLI                                           |
| Mode                 | POLISH                                        |
| Overall DX           |  7/10  |  4/10  |  ↑     |
+====================================================================+
| DX PRINCIPLE COVERAGE                                               |
| Zero Friction      | covered (recette copiable)                     |
| Learn by Doing     | covered (golden tests, banc)                   |
| Fight Uncertainty  | covered (erreurs : problème, cause, remède)    |
| Opinionated + Escape Hatches | covered (JSON défaut, text, md)       |
| Code in Context    | covered (recette réelle, pas un hello world)   |
| Magical Moments    | covered (le Markdown du ticket)                |
+====================================================================+
```

Aucune passe sous 5. La communauté reste à 5 par choix de stratégie, pas par oubli.

### Implementation Tasks

Toutes sont déjà reportées dans `tasks.md`.

- [ ] **T1 (P1, human: ~1h / CC: ~10min)** — README — recette `kubectl run` en lecture seule, jusqu'au Markdown
  - Surfaced by: Step 0, D5 et D6
  - Files: `README.md` (tâche 7.1)
  - Verify: tâche 8.3
- [ ] **T2 (P1, human: ~1h / CC: ~10min)** — CLI — `--policy-name` à la place de `--policy`
  - Surfaced by: parcours, Real Usage (D9)
  - Files: `uske/decisions.py`, `uske/cli.py`, `tests/test_decisions.py` (tâches 2, 6)
  - Verify: `test_one_policy_by_its_name`, `test_an_unknown_policy_name_lists_the_present_ones`
- [ ] **T3 (P2, human: ~30min / CC: ~5min)** — CLI — suggérer les références complètes
  - Surfaced by: parcours, Hello World (D8)
  - Files: `uske/decisions.py`, `uske/cli.py` (tâches 3, 6)
  - Verify: `test_a_short_reference_gets_the_full_one_on_stderr`
- [ ] **T4 (P2, human: ~20min / CC: ~3min)** — rendu md — rapport « (volume uske-results) »
  - Surfaced by: parcours, Real Usage (D10)
  - Files: `uske/decisions.py`, `tests/golden/decisions-redis-728.md` (tâche 5)
  - Verify: golden test `md`
- [ ] **T5 (P2, human: ~20min / CC: ~3min)** — erreurs — cause et remède dans les messages
  - Surfaced by: passe 3
  - Files: `uske/decisions.py`, `uske/cli.py` (tâches 2, 6)
  - Verify: `test_nothing_to_read_is_an_error`, `test_a_bad_date_is_a_usage_error_that_says_the_form`
- [ ] **T6 (P1, human: ~30min / CC: ~15min)** — banc — un passage chronométré de la recette
  - Surfaced by: passe 8 (D11)
  - Files: `openspec/changes/decisions/tasks.md` (tâche 8)
  - Verify: temps consigné sous la tâche 8.4

### Unresolved Decisions

Aucune : les treize questions ont reçu une réponse. La seconde voix extérieure (Codex) n'a pas
tourné, faute de modèle utilisable (`MODEL_UNUSABLE`), et le repli natif n'était pas disponible sur
cet hôte.

## Revue d'ingénierie (`/plan-eng-review`, 2026-10-16)

Cible : le change `openspec/changes/decisions/` (proposal.md, delta `decision-lookup`, tasks.md),
tel qu'amendé par la revue DX. Rapport : ce fichier.

### Scope record

feature answers: aucune coupe proposée ; structure: A, Original arrangement (D15) ; accepted
scope: les 9 fichiers du plan, dont `tests/golden/` (3 fichiers) ; pending remedies: R1.
Scope Challenge : scope accepted as-is.

### Reality rows

| Premise | Claim | Receipt | Verdict |
| --- | --- | --- | --- |
| Le journal d'une politique est `<results>/<metadata.name>.jsonl` | `path_for` | `uske/results.py:27-28`, `uske/cli.py:171` | vrai |
| Le rapport vit sous `/results/reports/` | `--report-link` | `deploy/base/workflowtemplate.yaml:195` | vrai |
| Les politiques ne sont pas dans l'image | README | `README.md:38` | vrai |
| L'image lance `python -m uske` | ENTRYPOINT | `Dockerfile:13` | vrai |
| Le banc construit `uske:dev` depuis l'arbre courant | `docker build … -t uske:dev` | `deploy/kind/up.sh:147` | vrai |
| Le PVC est en ReadWriteOnce | `accessModes` | `deploy/base/storage-and-access.yaml:8` | vrai |
| L'image publiée est `ghcr.io/trivoallan/uske` | `image=ghcr.io/${GITHUB_REPOSITORY,,}` | `.github/workflows/release.yml:92` | vrai |
| Les pods du banc journalisent les lignes (`"ref"`) | `_json(line.to_dict())` dans `classify` | `uske/cli.py:130` | vrai pour la sortie ; leur rétention sur le banc : unverified |
| `#58;` est rendu `:` dans une `timeline` Mermaid | — | aucune | unverified (tâche 5.7) |

unverified=2

```
REALITY: premise-table finding 2 unverified premises (bench log retention, Mermaid entities in timeline) uske/cli.py:130
REALITY: already-done pass origin/main has no commit on uske/, tests/, README.md since 2026-10-16 nor any "decisions" commit uske/cli.py:1
REALITY: surface-check pass new flags defined in tasks.md 6.6; kubectl run --rm -i --restart=Never --overrides are standard kubectl flags; openspec validate ran openspec/changes/decisions/tasks.md:1
REALITY: binding-decisions pass gstack-decision-search returned none; D1-D15 of this file honored openspec/changes/decisions/review.md:1
REALITY: numbers finding test counts derived from the plan's test lists [estimated]; DX times [estimated], measured in task 8 openspec/changes/decisions/tasks.md:1
REALITY: deferred-asks pass story 2 asks (ref or digest filter; date, state, ruleset, reason, report) all covered openspec/discovery.md:166
REALITY: pr-count pass no .gstack/ship-policy.json, one PR openspec/changes/decisions/tasks.md:1
```

### Findings

**Section 1, Architecture**

- `[P3] (confidence: 5/10) tasks.md, tâche 5.5, « out.append(f"    title {ref.translate(MERMAID)}") »` :
  que Mermaid rende `#58;` en `:` dans une `timeline` n'est pas vérifié. Medium confidence,
  verify this is actually an issue. Travail courant : la tâche 5.7 (aperçu Mermaid du golden)
  est la preuve du contrat approuvé.
- `[P3] (confidence: 6/10) uske/results.py:59, « Append in a single write »` : un `decisions`
  lancé pendant qu'un `record` écrit peut lire une dernière ligne incomplète. Le lecteur échoue
  alors en `error: <fichier>:<ligne>`, sans sortie partielle, et un nouvel essai suffit. Mode de
  défaillance visible, aucun changement.

**Section 2, Qualité du code**

- `[P2] (confidence: 8/10) tasks.md, tâches 3.3 et 5.5, « l.get("ref", "").endswith("/" + image) »
  et « ref.translate(MERMAID) »` : `read_journal` ne vérifie que la présence de `ts`, `digest`,
  `state` et le format de `ts`. Une ligne écrite à la main avec `"ref": null` (ou un nombre)
  passe, puis `suggest` et `render_md` lèvent `AttributeError` : une trace Python, au lieu de
  `error: fichier:ligne`. → R1.
- `results.read` (`uske/results.py:31-34`) et `read_journal` lisent tous deux du JSONL, mais avec
  deux contrats différents : laxiste pour `record` et `approve`, strict et numéroté pour
  `decisions`. Extraction écartée (rubrique : contrats incompatibles), aucune question.

**Section 3, Tests** : voir le diagramme ci-dessous.

- `[P2] (confidence: 9/10) spec, « marquée comme antidatée en text et en md »` : la marque n'est
  testée qu'en `text` (`test_marks_and_missing_reason`) ; rien ne casse si `render_md` cesse de
  concaténer `marks(line)`. Preuve requise d'un contrat approuvé : un test
  `test_marks_appear_in_the_timeline_and_the_table` s'ajoute à la classe `Markdown`, sans question.

**Section 4, Performance** : aucun problème. Un journal porte une ligne d'environ 500 octets par
décision ; même 10 000 décisions par politique font 5 Mo lus une fois [estimated].

## Decision ledger

### R1: valider le type des clés lues avant tout rendu
Finding: Section 2, P2, confidence 8/10, tasks.md tâches 3.3 et 5.5, reviewer: plan-eng-review
Plan baseline: spec, exigence « Un journal illisible se signale » : erreur si non-objet, si `ts`, `digest` ou `state` manque, si `ts` est mal formé, si `policy` est présent (revue OpenSpec, constats 5 et 13). Aucune condition sur le type des valeurs.
Runtime evidence: unknown (code proposé, pas encore écrit) ; déduit de la lecture du code des tâches 3.3 et 5.5.
Comparison grid:

| Choix | Actuel | A | B |
| --- | --- | --- | --- |
| R1 type des clés | non vérifié | `ts`, `digest`, `state` doivent être des chaînes ; `ref`, `reason`, `ruleset`, `report`, `source`, `rebuilt`, s'ils sont présents, aussi ; sinon `error: fichier:ligne`, code 1 | non vérifié ; une valeur non textuelle peut lever une trace Python |
| Test de la marque en md | — | ajouté (preuve requise) | ajouté (preuve requise) |

Question D16:
D16 — Une valeur non textuelle dans le journal
Projet : uske, change `decisions`.
ELI10 : le journal accepte des lignes écrites à la main (arbitrages, réouvertures). Le plan vérifie que `ts`, `digest` et `state` sont présents, mais pas que ce sont du texte. Une ligne avec `"ref": null` passerait la lecture, puis ferait planter le rendu Markdown et les suggestions avec une trace Python. Pour la responsable plateforme, c'est un message incompréhensible à l'endroit exact où elle avait besoin d'une réponse.
Stakes if we pick wrong : une seule ligne mal tapée rend la commande inutilisable pour toute la politique, sans dire laquelle.
Recommendation : A, parce que la spec promet déjà « un journal illisible se signale », et qu'une valeur du mauvais type, c'est une ligne illisible.
Completeness : A=10/10, B=6/10
Pros / cons:
A) Valider le type (recommended)
  ✅ Une ligne fautive donne `error: fichier:ligne: ref must be a string`, code 1, comme les autres lignes illisibles.
  ✅ Une boucle de quatre lignes dans `read_journal`, un scénario de spec et un cas de test de plus (human: ~30 min / CC: ~3 min).
  ❌ Une ligne avec une valeur exotique mais affichable (un nombre dans `reason`) est refusée au lieu d'être affichée.
B) Ne rien valider
  ✅ Aucune ligne de code en plus, et toute valeur que `str()` sait afficher s'affiche.
  ✅ La spec reste telle qu'elle a été validée au cadrage OpenSpec.
  ❌ `"ref": null` fait planter `--format md` et les suggestions avec une trace Python, sans nommer la ligne.
Net : refuser tôt une valeur bizarre, ou planter tard sur la même valeur.
Header: Question
Options:
A) Valider le type (recommended)
`ts`, `digest`, `state`, et `ref`, `reason`, `ruleset`, `report`, `source`, `rebuilt` s'ils sont présents, doivent être des chaînes ; sinon error: fichier:ligne, code 1.
B) Ne rien valider
Le plan tel quel : une valeur non textuelle peut lever une trace Python au rendu.

State: approved
Actual answer: A) Valider le type (recommended), réponse à D16, 2026-10-16
Accepted scope: dans `read_journal`, `ts`, `digest`, `state`, et `ref`, `reason`, `ruleset`, `report`, `source`, `rebuilt` s'ils sont présents, doivent être des chaînes ; sinon `error: fichier:ligne: <clé> must be a string`, code 1. Un scénario de spec, un cas de test (sous-test de `test_an_unreadable_line_names_its_file_and_line`).
History: none

Approval readiness: PASS — R1 (D16, réponse A) ; structure D15 (réponse A) ; test de la marque en md : preuve requise du contrat approuvé « marquée comme antidatée en text et en md » (spec, exigence « L'ordre est celui du journal »).

### Test review

Framework : `pytest` via `make test`, couverture de branches, seuil global et par fichier à 90 %
(`uske/CLAUDE.md`, `pyproject.toml:34`). Tests existants : `tests/test_orchestrator.py`,
`tests/test_census.py`, `tests/test_dtsync.py`. Tout le code de `decisions` est proposé : le
diagramme porte sur les tests prévus par `tasks.md`, pas sur des tests existants.

```
CODE PATHS (proposés)                                  USER FLOWS
[+] uske/decisions.py                                  [+] Répondre au ticket (responsable plateforme)
  ├── read_journal()                                     ├── [★★★ PLANNED] recette README → md   tâche 8 [→E2E banc]
  │   ├── [★★★ PLANNED] JSON invalide, non-objet,        ├── [★★★ PLANNED] réf. courte → suggestion  Command
  │   │     clé manquante, type, ts, policy  Read        └── [★★  PLANNED] --policy-name inconnu     Command
  ├── load()                                           [+] Auditeur
  │   ├── [★★★ PLANNED] tout lire, une politique,        └── [★★★ PLANNED] --state + --since         Select, Command
  │   │     rien à lire, nom inconnu         Read      [+] Erreurs visibles
  ├── annotate()  [★★★ PLANNED] antidatée     Select     ├── [★★★ PLANNED] ligne corrompue → code 1, stdout vide
  ├── select()    [★★★ PLANNED] réf, empreinte,          └── [★★★ PLANNED] date mal formée → code 2 + forme
  │                 @sha256, source/rebuilt, filtres
  ├── suggest()   [★★  PLANNED] avec et sans suggestion
  ├── render_text() [★★★ PLANNED] golden + groupes + marques + source/rebuilt
  └── render_md()   [★★★ PLANNED] golden + échappement + marques (ajouté, preuve requise)
[+] uske/cli.py
  ├── _day()        [★★★ PLANNED] date valide, mal formée
  └── cmd_decisions() [★★★ PLANNED] json/text/md, vide, indice stderr, journal intact

COVERAGE (prévue) : 20/20 chemins | QUALITY : ★★★ 17, ★★ 3 | GAPS : 0 (1 E2E au banc, tâche 8)
```

Legend: ★★★ comportement + bord + erreur | ★★ chemin nominal | [→E2E] = test d'intégration

Ajouté au plan : `test_marks_appear_in_the_timeline_and_the_table` (classe `Markdown`) et deux
sous-tests de lecture (`ref` non textuel, `state` non textuel, D16). Aucun test rendu obsolète.
Aucune portée LLM. Test Plan Artifact :
`~/.gstack/projects/trivoallan-uske/tristan-main-eng-review-test-plan-20261016-154919.md`.

**Dispositions.** Section 1 : les deux constats, routine et mode de défaillance visible, sans
question. Section 2 : R1 accepté (D16, A) ; extraction de `results.read` écartée. Section 3 : test
de la marque en md ajouté (preuve requise). Section 4 : aucun constat.

### Flux

```
 question du dev
       │
       ▼
 kubectl run (README) ── monte uske-results en lecture seule ──► pod uske:<version>
       │                                                           │
       ▼                                                           ▼
 python -m uske decisions IMAGE --results /results --format md
       │
       ├─ load(): *.jsonl du 1er niveau ─► read_journal() ── illisible ──► error: f:l, code 1
       │                │
       │                └─► annotate() : marque les lignes antidatées
       ├─ select(): IMAGE → empreintes (+ source/rebuilt), --state, --since
       │        └─ rien ─► stderr : suggest() ou rappel ; stdout [] / vide
       └─ render_md(): groupe (politique, empreinte) → timeline Mermaid + tableau
                │
                ▼
      stdout → collé dans le ticket
```

### Failure modes

| Chemin | Défaillance réaliste | Test | Gestion d'erreur | Visible ? |
| --- | --- | --- | --- | --- |
| lecture | ligne incomplète pendant un `record` | sous-test JSON invalide | `error: f:l`, code 1 | oui |
| lecture | `"ref": null` écrit à la main | sous-test (D16) | `error: f:l: ref must be a string` | oui |
| recette | PVC RWO attaché sur un autre nœud | tâche 8 (banc) | kubectl : pod en attente | oui, côté kubectl |
| recette | stderr mêlé au Markdown | tâche 8.3 | à séparer dans la recette | oui, à l'œil |
| rendu md | entité Mermaid non rendue | tâche 5.7 (visuel) | aucune | oui, à l'œil |

Aucun écart critique : pas de chemin à la fois sans test, sans gestion d'erreur et silencieux.

### NOT in scope

- Valider le vocabulaire `arbitration` : la spec affiche ces clés telles quelles, sans fixer leur
  forme (cadrage, passe 1).
- Factoriser `results.read` et `read_journal` : les deux contrats sont incompatibles.
- Rejouer en test une écriture concurrente de `record` : le mode de défaillance est déjà visible et
  sans dégât.

### What already exists

- `results.path_for` (`uske/results.py:27`) fixe le nom du journal ; `decisions` relit le même
  nom, sans le recalculer depuis une politique.
- `Failure` et `main` (`uske/cli.py:23`, `uske/cli.py:438`) pour le code 1, argparse pour le code 2.
- Le banc `deploy/kind/up.sh` pour la tâche 8 ; `tests/fixtures/repo` pour la fixture.

### Parallélisation

Sequential implementation, no parallelization opportunity : un module principal
(`uske/decisions.py`), et la CLI, les goldens et la recette en dépendent.

### Implementation Tasks (eng)

- [ ] **E1 (P1, human: ~30min / CC: ~3min)** — lecture — valider le type des clés écrites
  - Surfaced by: Section 2, R1 (D16)
  - Files: `uske/decisions.py`, `tests/test_decisions.py` (tâche 2)
  - Verify: `test_an_unreadable_line_names_its_file_and_line`, sous-tests `ref`/`state`
- [ ] **E2 (P2, human: ~20min / CC: ~2min)** — rendu md — tester la marque dans la frise et le tableau
  - Surfaced by: Section 3, preuve du contrat « antidatée en text et en md »
  - Files: `tests/test_decisions.py` (tâche 5.3)
  - Verify: `test_marks_appear_in_the_timeline_and_the_table`

_No new tasks from Architecture or Performance._

### Unresolved decisions

Aucune.

### Completion summary

- Step 0: Scope Challenge — scope accepted as-is (D15, Original arrangement)
- Reality rows: 7/7 applicable rows emitted, 2 unverified premises
- Architecture Review: 2 issues found (P3, routine)
- Code Quality Review: 1 issue found (R1, accepted)
- Test Review: diagram produced, 1 gap identified (md marks, added)
- Performance Review: 0 issues found
- NOT in scope: written
- What already exists: written
- TODOS.md updates: 0 items proposed (D12 and D13 reused)
- Failure modes: 0 critical gaps flagged
- Unresolved decisions: 0 in this review
- Outside voice: codex, unavailable (MODEL_UNUSABLE; native fallback unavailable, no TaskOutput)
- Parallelization: 1 lane, 0 parallel / 1 sequential
- Lake Score: 1/1 (D16 picked the 10/10 option)

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Outside Review | codex (plan-review, default-on) | Independent 2nd opinion | 2 | unavailable | Codex `MODEL_UNUSABLE` (gpt-6-astra) twice; native fallback unavailable (no TaskOutput) |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | issues_open | 4 issues, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 1 | issues_open | score: 4/10 → 7/10, TTHW: 10-20 min (estimated) → 2-5 min |

- **OUTSIDE COVERAGE:** codex, plan-review, unavailable on both the DX and eng runs (model not usable for this account; `gstack-config set model_frontier_openai <model-id>` or `gstack-config set plan_review_tier host`), no findings. Native fallback not run: no TaskOutput on this host. Missing coverage, not a clean pass.
- **VERDICT:** no review CLEAR. Eng review issues_open: all 4 findings mapped to accepted work (R1 via D16, one added test, two routine), none pending; DX review issues_open (TTHW target unmeasured until task 8); eng review required.

NO UNRESOLVED DECISIONS
