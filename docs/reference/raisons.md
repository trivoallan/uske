# Raisons du journal

<!-- Engendré par `uv run python -m uske.outcomes`. Ne pas modifier à la main. -->

Chaque ligne du journal porte un état et, souvent, une raison. **Lisez le couple** :
une même raison ne dit pas la même chose sous deux états. `<...>` marque une partie
remplie à l'écriture ; `<provider>/<criterion>` est une règle du playbook.

| Raison | État | Ce qu'elle dit | Que faire |
| --- | --- | --- | --- |
| `<provider>/<criterion>` | `quarantine`, `transformation-required` | La première règle critique du playbook qui a échoué. C'est la première, pas la seule cause : le report les donne toutes. | Lire la règle dans le report, et sa définition dans la référence des règles de `regis` (`docs/reference/rules`). |
| `<provider>/<criterion>` | `inconclusive` | Une règle critique n'a pas abouti : un outil a échoué, ou une donnée manquait. Rien n'est décidé sur l'image (D-23). | Lire dans le report pourquoi la règle est `incomplete`. Le prochain criblage la rejuge. |
| `uske/better-tier-missed:<provider>/<criterion>` | `inconclusive` | Aucune règle critique n'a échoué, mais cette règle non critique n'a pas abouti : l'image a peut-être manqué un meilleur tier. Une évaluation qui ne conclut pas ne décide rien (D-23). | Lire dans le report pourquoi la règle est `incomplete`. L'image est peut-être saine ; le prochain criblage la rejuge. |
| `regis/exit-1` | `inconclusive` | `regis` a échoué techniquement, après les nouvelles tentatives d'Argo. Ce n'est pas un verdict sur l'image. | Lire les journaux de l'étape `regis` du workflow. |
| `regis/exit-3` | `inconclusive` | L'appel à `regis` était mal formé : les métadonnées ne satisfont pas un schéma déclaré par le playbook. Ce n'est pas un verdict sur l'image. | Corriger le playbook ou les métadonnées ; le report liste les champs en défaut. |
| `regis/exit-<N>` | `inconclusive` | `regis` s'est arrêté sur un autre code (2 : ligne de commande refusée). | Lire les journaux de l'étape `regis` du workflow. |
| `regis/no-report` | `inconclusive` | `regis` n'a laissé aucun report lisible. | Lire les journaux de l'étape `regis`, puis vérifier le volume de travail. |
| `regis/no-verdict` | `inconclusive` | Le report ne contient aucun résultat de playbook. | Vérifier que le workflow passe bien un playbook à `regis`. |
| `regis/unknown-tier` | `inconclusive` | Le tier rendu n'est aucun de ceux que `uske` connaît : `Placement direct`, `Transformation requise puis placement`, `Quarantaine`. | Aligner le nom des tiers du playbook sur cette liste. |
| `uske/unknown-track` | `inconclusive` | La politique désigne un régime sans playbook connu : l'image n'a pas été évaluée (D-21). | Ajouter le playbook de ce régime, ou corriger le régime de la politique. |
| `uske/rebuild-refused` | `quarantine` | Ligne de clôture sur la source : son image reconstruite a été jugée et refusée. Ce n'est pas un verdict sur la source (SDR-0016). | Lire le report de l'image reconstruite (clé `rebuilt`). Pour réessayer, rouvrir la source. |
| `uske/reopened` | `inconclusive` | Ligne écrite à la main : une personne a rouvert la source (SDR-0016). | Rien : le prochain criblage la rejuge. |
| *(aucune)* | `direct-placement`, `transformation-required` | Aucune raison. En `transformation-required`, le tier vient d'une condition du playbook qui ne nomme aucune règle critique échouée. | Rien pour un placement direct ; sinon, lire le report. |
