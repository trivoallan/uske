# Review

## Grilles retenues

- **Contrôle** : la base décide si une image est refusée ou rendue au placeur. Ce qui l'altère,
  la périme ou la fait disparaître touche directement aux refus.
- **Ingénierie** : une donnée distribuée par le dépôt d'artefacts à tous les enfants, un mécanisme
  nouveau dans ce déploiement.

La première version de cette revue a été faite à la main. La revue d'ingénierie du 2026-10-17
(`/plan-eng-review`, rapport dans `~/.gstack/projects/trivoallan-uske/`) a corrigé la chaîne du
refus (D3) et ajouté D4 à D10. À l'application, #53 (SDR-0021) a fait abandonner le volume partagé
pour le dépôt d'artefacts : D4 (générations sur le volume) et D7 (taille du volume) tombent, et les
findings ci-dessous sont revus pour la nouvelle conception.

## Findings et traitement

| # | Grille · dimension | Finding | Sévérité | Traitement |
| --- | --- | --- | --- | --- |
| 1 | Contrôle · intégrité | Quiconque détient les identifiants du dépôt d'artefacts peut remplacer `grype-db/current.tar.zst`, et toute la flotte rend alors de faux verdicts sains. | haute | Accepté, frontière au dépôt d'artefacts, la même que pour le travail des enfants (SDR-0021). grype vérifie le hachage de la base à chaque démarrage (D5), et la somme consignée dans chaque rapport permet de constater après coup quelle base a jugé. Inscrit dans *Risks* de `design.md`. |
| 2 | Contrôle · disponibilité | Après 48 h sans rafraîchissement, le régime complet passe en *inconclusive*. On refuse bien, mais rien ne prévient : on ne s'en aperçoit qu'en voyant le cron en échec dans Argo. | moyenne | La spec exige que l'exécution planifiée soit marquée en échec, et la vérification toutes les 6 h laisse environ sept essais avant la limite (D6). L'alerte sort du périmètre et est notée hors du dépôt (D10). |
| 3 | Ingénierie · compatibilité | Une montée de version de regis qui change de schéma de base trouve, jusqu'au rafraîchissement suivant, une base que son grype ne lit plus : jusqu'à 6 h d'évaluations *inconclusive* dans le régime complet. | moyenne | Tâche 4.4 : la documentation prescrit de lancer un rafraîchissement à la main après chaque montée de version de regis. D3 garantit qu'ensuite les versions concordent. |
| 4 | Ingénierie · stockage | Chaque pod `regis-analyze` occupe ~3,8 Go de stockage éphémère (archive puis base). Des nœuds trop petits feraient échouer ou évincer des pods. | moyenne | L'archive est supprimée dès qu'elle est déballée (D4), et les deux plafonds de `uske-screening` bornent les pods simultanés. Le dimensionnement des nœuds revient à l'overlay de production ; inscrit dans *Risks*. |
| 5 | Ingénierie · provenance | L'emballage pourrait faire perdre à la base sa source et sa somme, que regis lit dans `descriptor.db.status.from`. | moyenne | Tâche 1.3, le spike : vérifier `from` après déballage dans un autre conteneur. Repli s'il est perdu : remplacer `import.json` par celui de la base téléchargée, qui le porte (vu le 2026-10-17). |
| 6 | DevEx · chemin local | Rien ne prévient la personne qui lance `uske screen` sans cache grype : chaque évaluation retélécharge la base, sans erreur. | basse | Accepté : c'est à l'appelant de fournir la base. La documentation de `uske screen` le dit (tâche 4.5). |
| 7 | Ingénierie · tests | Les six tests qui emballent ou déballent une vraie archive zstd demandent Python 3.14 et sont sautés en CI (Python 3.13) ; ils passent sur 3.14 (`uv run --python 3.14 …`), et le chemin a été prouvé sur le banc (tâches 4.2, 4.3). | moyenne | Accepté ; à rouvrir quand uske passera à Python 3.14. |

## Critère d'achèvement

La revue est close quand :
- le spike (tâche 1) a tranché le finding 5 ;
- les traitements des findings 3, 4 et 6 sont dans `tasks.md` et `design.md` ;
- les findings 1 et 2, acceptés, figurent dans *Risks* de `design.md`.
