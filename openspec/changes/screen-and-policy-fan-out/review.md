# Review

Les skills `/plan-devex-review` et `/plan-eng-review` n'ont pas été lancées : ce change a été ouvert
par une autre session, et elles mènent un entretien que personne ne pouvait tenir ici. La revue
suit leurs grilles, à la main, sur `proposal.md`, les deux deltas et `design.md`.

## Grilles retenues

- **DevEx** : `uske screen` se consomme. La personne qui lui fait face est l'opératrice de
  `base-images` ou d'une CI, qui l'appelle à la place de `screen.sh`.
- **Contrôle** : la commande refuse des placements, et un échec doit se voir. Elle s'ajoute aux
  quatre premières.
- **Ingénierie** : le plan dépasse une merge request (le verbe, puis la scission du workflow) et
  ajoute un droit Kubernetes.

## Findings et traitement

| # | Grille · dimension | Finding | Sévérité | Traitement |
| --- | --- | --- | --- | --- |
| 1 | DevEx · découverte | Trois réglages vivent dans l'environnement (`USKE_REGIS_CMD`, `USKE_KNOCK_CMD`, `USKE_AFTER_RECORD`) : invisibles pour qui lit `--help`. | moyenne | `uske screen --help` les nomme dans son épilogue, chacun avec un exemple (tâche 2.6). |
| 2 | DevEx · premier échec | Avec un préfixe `docker run`, un chemin non monté au même endroit fait échouer l'outil loin de sa cause. | haute | Un outil qui sort en erreur fait écrire à `uske` la commande complète lancée et son code (tâche 2.3). Le README impose le montage au même chemin (plan de documentation). |
| 3 | DevEx · migration | `screen.sh` cite ses rapports en `results/reports/<politique>/<empreinte>.md` ; `uske screen` en `reports/<politique>/<empreinte>/<run>.md`. Les liens déjà dans le journal de `base-images` ne bougent pas, les nouveaux changent de forme. | basse | Accepté : le journal n'est pas réécrit, et `decision-lookup` lit les deux. Le README le dit. |
| 4 | Contrôle · fail-closed | Un crochet qui échoue après la première porte doit arrêter le placement. Cette garantie ne tient que si `screen` lance le crochet *entre* `record` et `--apply-plan`. | haute | C'est un scénario du delta (*Le crochet échoue*) ; tâche 2.4. |
| 5 | Contrôle · injection | Le crochet passe par `sh -c`. S'il interpolait le nom de la politique, un `metadata.name` choisi exécuterait du code. | haute | Le nom ne passe que par `USKE_POLICY`, jamais par la chaîne de commande. La tâche 2.4 porte un test sur un nom avec `;`. |
| 6 | Ingénierie · dérive | Le seul garde contre une dérive entre `screen` et le template est le test de parité. Il exerce les sous-commandes, pas le YAML d'Argo. | moyenne | Accepté : le YAML n'a pas de banc automatique. L'ordre des étapes de `screen` porte en commentaire le nom de l'étape du template qu'il suit (tâche 2.2). |
| 7 | Ingénierie · droits | Le compte `uske` peut désormais créer n'importe quel `Workflow` de son namespace. | moyenne | Accepté : il les exécute déjà. Le `Role` reste limité au namespace et aux verbes de D8 (tâche 4.3). |
| 8 | Ingénierie · réversibilité | Aucune décision `irréversible` : le journal garde sa forme ; un chemin `report` relatif était déjà admis. | — | Rien à faire. |
| 9 | Ingénierie · charge | 10 000 `Workflow` par screening n'ont jamais été mesurés. | haute | Hors de portée du code : `ttlStrategy` et `podGC` (tâche 4.2), et le spike du 2026-10-19 avant tout plafond au-delà de 1. |
| 10 | Contrôle · fail-closed | Un tag réparé que le correctif amont suivant replace sans ordre perd sa réparation sans bruit (un non-root redevient root). | haute | Exigence ajoutée à `rebuild-gate` ; tâche 3.1. Sans transit, l'opération est retirée plutôt que placée nue. |

## Critère d'achèvement

Chaque finding de sévérité haute a sa tâche cochée, ou son scénario vert, avant l'archivage. Les
findings acceptés restent tels quels dans ce tableau.
