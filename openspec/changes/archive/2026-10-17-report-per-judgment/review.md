# Review

Les skills `/plan-devex-review` et `/plan-eng-review` n'ont pas été lancées. La revue applique leurs
grilles à la main, sur `proposal.md` et le delta `screen-command`. Il n'y a pas de `design.md`.

## Grilles retenues

- **DevEx** : `uske screen` est un outil que des tiers utilisent. Deux publics sont concernés :
  l'opérateur d'une CI, `base-images` en premier, qui lit les noms de rapports, et l'auteur d'un
  crochet, qui reçoit `USKE_STEP`.
- **Contrôle** : le change protège une garantie du journal, « un rapport cité n'est jamais
  réécrit ». Une erreur sur cette garantie doit se voir, et non passer en silence.
- **Ingénierie** : non retenue. Aucune décision n'est `irréversible`, le plan tient en une merge
  request, et rien de neuf n'est introduit (droit, dépendance, format de journal).

## Findings et traitement

| # | Grille · dimension | Finding | Sévérité | Traitement |
| --- | --- | --- | --- | --- |
| 1 | Contrôle · intégrité | Entre la recherche du nom libre (`_free_stem`) et la copie, un autre processus qui écrit dans le même `--results` sous le même epoch peut prendre ce nom. | moyenne | La copie se fait par création exclusive (`open("xb")`). La collision lève une erreur : la politique échoue, aucune ligne n'est écrite pour ce jugement, rien n'est placé, et rien n'est réécrit (tâche 1.4). C'est un échec visible, accepté tel quel. |
| 2 | Contrôle · fail-closed | Si la copie du HTML échoue après celle du Markdown, le `.md` reste sans ligne qui le cite. | basse | Accepté. Un rapport orphelin ne trompe personne, et le jugement est refait au screening suivant. |
| 3 | Contrôle · parité | Le `WorkflowTemplate` nomme toujours ses rapports `<run>.html`, et `uske merge` garde un fichier existant (`_keep`). Si un même run d'Argo rejugeait une empreinte, la nouvelle ligne citerait l'ancien rapport. | moyenne | Hors de portée de ce change. Dans Argo, un run correspond à un `Workflow` par screening, et une empreinte n'y est jugée qu'une fois avant la fusion. Le cas ne se produit que si l'on relance un enfant à la main, ce que `operate.md` déconseille. À vérifier dans un change à part avant d'aligner les deux chemins. |
| 4 | DevEx · attentes | Le crochet n'est appelé qu'après une étape qui a écrit. L'auteur d'un crochet qui attend les cinq valeurs en verra souvent deux ou trois. | basse | Les scénarios du delta montrent les séquences réelles, et `operate.md` le dit (tâche 3.1). |
| 5 | DevEx · contrat | Les valeurs de `USKE_STEP` deviennent un vocabulaire public : en renommer une casserait les crochets qui la testent. | moyenne | Les cinq valeurs sont écrites dans le delta. Toute modification passe donc par un change sur `screen-command`. Elles reprennent les noms des étapes du `WorkflowTemplate`, sauf `record-held`, qui n'y a pas d'équivalent nommé. |
| 6 | DevEx · migration | Les nouveaux rapports de `base-images` s'appelleront `<epoch>.md`, et non plus `<run_id>-<tentative>.md` (`screen.sh`) ni le nom tiré de l'URL du run (`uske screen` 0.9.0). | basse | Accepté : les lignes existantes citent leur fichier par son chemin, et le journal n'est pas réécrit. La tâche 4.3 fait la suite côté `base-images`. |
| 7 | DevEx · lisibilité | `<epoch>` seul ne dit pas quel run a produit le rapport. | basse | Accepté : la ligne qui cite le rapport porte `run`, et c'est par elle qu'on retrouve un rapport. |
| 8 | Contrôle · injection | `USKE_STEP` arrive au shell du crochet. | — | Rien à faire : la valeur est une constante du code, jamais une donnée lue en entrée, et elle passe par l'environnement, comme `USKE_POLICY`. |

## Critère d'achèvement

Les findings 1 et 4 ont leur tâche cochée (1.4, 3.1) avant l'archivage. Le finding 3 aura un change
ou une issue ouverte et citée dans la PR. Les findings acceptés restent tels quels dans ce tableau.
