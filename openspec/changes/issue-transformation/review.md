# Review

## Grilles retenues

Trois grilles, choisies par ce que le livrable fait à qui lui fait face.

- **Contrôle** — le livrable refuse : une image retenue n'est pas promue, une source est close. La
  grille demande ce que dit le refus, ce que coûte un refus à tort, s'il se rejoue, comment on en
  sort, et quand il s'impose.
- **Ingénierie** — une décision est irréversible, le vocabulaire du journal, et le plan dépasse une
  demande de fusion : une dans `knock`, deux au moins ici.
- **DevEx** — le livrable se consomme : un paramètre de workflow, des options de ligne de commande,
  un banc local, et un jour une surcouche écrite par quelqu'un d'autre.

La grille Design ne s'applique pas : rien ici ne se regarde.

**Conduite.** Revue à la main, le 2026-10-10, sur `proposal.md`, `design.md` et le delta
`rebuild-gate`. L'auteur de la conception ne s'est pas relu seul : un relecteur à contexte neuf a
lu les trois fichiers contre le code de `uske` et celui de `knock` à `ce2278b`, puis l'auteur a
revérifié dans le code les findings 1, 2, 5 et 6, et dans le playbook les findings 3 et 7. Les
skills `plan-eng-review` et `plan-devex-review` n'ont pas été lancées : elles s'invoquent avec
l'aval de la personne, qui n'a pas été demandé pour cet artefact. L'audit de sécurité n'est pas
conduit ici (finding 18).

**Ce que la revue a vérifié et ce qu'elle déduit.** Les neuf faits du contexte de `design.md` sont
confirmés par le code, un seul avec une imprécision (finding 20). Sont **déduits, sans exécution** :
le verdict de `regis` sur une image donnée (findings 3 et 7), le comportement de Harbor avec deux
comptes robots (finding 6), et celui d'Argo Workflows sur `continueOn` (finding 16).

## Findings et traitement

| # | Grille · dimension | Finding | Sévérité | Traitement |
| --- | --- | --- | --- | --- |
| 1 | Ingénierie · cas limites | **La clôture de la source se défait une fois sur deux.** `evaluate` écrit ses lignes dans `/work/lines/<politique>/` et `record` relit tout le répertoire, trié par nom. À la seconde porte, il relit donc la ligne de première porte de la source. Si la clé de l'image retenue trie avant celle de la source, l'ordre est : clôture `quarantine`, puis `transformation-required`. `append` n'écarte qu'une répétition du dernier état : il garde les deux, et la source est rouverte. | Majeure | Un répertoire de lignes propre à la seconde porte, passé en paramètre à `evaluate`. Un test rejoue la ligne de première porte après la clôture. `design.md` D4 et D6 le disent. |
| 2 | Ingénierie · découpage | **Le Python sans le workflow place une reconstruction non jugée, et signée.** Le plan de migration fusionne `approve` avant les manifestes, et une surcouche épingle l'image et la base séparément. Avec le nouveau `approve`, un `knock` qui écrit `transformed` et un workflow sans `--stage-to`, une source `transformation-required` est approuvée, reconstruite et placée directement. La panne n'est fermée que du côté « vieux `knock` ». | Majeure | `approve` ne garde `transformation-required` que si on lui nomme le transit, par une option que seul le workflow à seconde porte passe. Sans elle, la règle d'aujourd'hui. Un scénario de plus à l'exigence 1. |
| 3 | Contrôle · coût du faux positif | **La clôture est définitive pour des causes que la reconstruction ne peut pas lever.** `transformed` dit « une transformation », pas « celle qui répare ». Le tier « Placement direct » exige `no-root`, et aucune des quatre étapes de `knock` ne fixe l'utilisateur : une source que `regis` juge en `root` est reconstruite, refusée et close au premier screening. Même effet, à tort cette fois, pour un miroir de paquets en retard d'un jour. | Majeure | La réouverture est spécifiée dans ce change (finding 4). Le banc mesure la part des sources closes pour `oci/user-blacklist`. Savoir quelle étape répare quelle règle reste hors de ce change, et `proposal.md` le nomme. |
| 4 | Contrôle · chemin de sortie | **Aucun n'est défini.** D7 dit « acte humain, hors de ce change » sans dire lequel. La seule sortie automatique est une nouvelle empreinte source, qui n'arrive pas pour un tag de version. Un nouvel `epoch` ne rouvre rien, et le journal vit sur un volume. | Majeure | Nommer la ligne qui rouvre : une ligne `inconclusive` ajoutée sur l'empreinte source, avec sa propre raison. `pending` la rend due et la suite reprend, sans code nouveau. Un scénario la couvre, et le `README.md` dit le geste. |
| 5 | Contrôle · rejouabilité | **Trois boucles de reconstruction sans borne, toutes les cinq minutes.** Verdict non concluant, promotion en échec, construction en échec : chacun fait reconstruire au screening suivant. Le marquage porte l'heure du passage, donc chaque essai a une empreinte neuve : une ligne de journal que `append` n'écarte pas, et des couches de plus dans un transit où rien ne se supprime. | Majeure | Borner : compter au journal les lignes dont `source` vaut l'empreinte, et cesser d'approuver au-delà d'un seuil écrit dans `design.md`. Sortir `place` des reprises communes d'Argo, qui triplent chaque essai. |
| 6 | DevEx · surcouche | **Les identités sur le transit ne sont pas conçues.** `regis` ne s'authentifie qu'à un hôte : un transit sur un autre hôte rend toute image retenue non concluante, d'où la boucle du finding 5. Sur le même hôte, `knock` n'ouvre qu'une session par hôte nu : deux comptes robots, l'un pour la destination et l'autre pour le transit, ne marchent pas. | Majeure | Écrire la contrainte dans le `README.md` et la surcouche d'exemple : même hôte que `HARBOR_HOST`, une identité `knock` avec droits sur les deux projets, la lecture du transit pour `regis`. |
| 7 | DevEx · banc | **La réparation d'une faille ne se montre que sur une image que la règle de licence ne voit pas.** Les deux premiers tiers exigent la règle de licence, qui refuse toute image dont Syft remonte une licence GPL : Alpine, Debian, distroless et Ubuntu sur le banc du 2026-09-20 (dossier `docs`, DEBT-13). Or `upgradePackages` a besoin d'un gestionnaire de paquets. Une image réparable par ses paquets part donc en quarantaine à la première porte, avant toute reconstruction, sauf celles où Syft ne remonte aucune licence, comme `redis:7.4-bookworm` le 2026-09-19. `alpine:3.18.0`, candidate de `proposal.md`, porte busybox en GPL-2.0-only. C'est indépendant de la base de failles, seul risque que la proposition nommait. Hors de ces images opaques, ce que la story répare aujourd'hui sous ce playbook, c'est la fraîcheur. | Majeure | Mesurer d'abord, avec `regis`, avant toute autre tâche du banc ; une image à paquets où Syft ne remonte aucune licence est la seule candidate pour réparer une faille. Repli nommé : une candidate faite exprès, poussée par `up.sh`, sans licence bloquée, non `root`, trop ancienne, que toute reconstruction rafraîchit. Si aucune ne ressort en placement direct, la preuve choisie au cadrage ne tient pas : retour à la personne. `proposal.md` renvoie la réparation des failles à l'arbitrage de la règle de licence. |
| 8 | Ingénierie · variantes | Une source saine dont la reconstruction est refusée passe en `quarantine` au journal, alors qu'une copie de la même source peut être en service et signée. La story 3 fera agir `quarantine`. Aucun scénario ne couvre ce cas, et l'exigence 1 dit qu'une source en placement direct « reste rendue ». | Mineure | Un scénario, et une phrase dans la spec : `uske/rebuild-refused` n'est pas une quarantaine prononcée par le juge. Une note à la story 3 dans `openspec/discovery.md`. |
| 9 | Ingénierie · preuve | Les chemins de panne n'ont aucun véhicule de preuve. Les tests unitaires ne peuvent pas éprouver le workflow, et les deux politiques du banc couvrent la réussite et le refus. Restent sans preuve : une construction qui casse, une promotion qui échoue, un déploiement sans transit, et `approve --staged` sans fichier. | Mineure | Une troisième politique de banc à tag non constructible, ou une vérification à la main nommée dans les tâches. Un test pour `approve --staged` sans fichier. |
| 10 | Ingénierie · cohérence | « La destination ne porte pas son tag » est faux pour une mise à jour : le tag y reste, sur l'ancienne image. D7 le dit, la spec non. | Mineure | Écrire « la destination est inchangée » dans les deux scénarios. |
| 11 | Ingénierie · irréversible | Le préfixe de la raison dépend de l'ordre de fusion : la spec fige `uske/rebuild-refused`, D6 le rend conditionnel, et la proposition laisse le Python précéder le renommage. | Mineure | Figer `uske/` sans condition dans D6. Une raison neuve n'a aucun passé à suivre. |
| 12 | Contrôle · message de refus | La ligne de clôture est sous-spécifiée : ni sa référence, ni son jeu de règles ne sont fixés, et elle ne dit pas quelle règle a échoué sur la reconstruction. Et une opération écartée faute de `transformed` n'écrit rien : `approve` ne rend qu'un compte. | Mineure | Fixer les clés de la clôture dans la spec. `approve` rend le nombre d'opérations écartées, par cause. |
| 13 | Ingénierie · interaction | Le paramètre `transit` casse la surcouche d'exemple du change `demenagement-gitlab-et-livraison`, qui remplace les paramètres en bloc. Le banc, lui, les patche par index 0 à 2. `deploy/example` manque à l'impact, et la valeur par défaut n'est pas dite. | Mineure | `transit` en dernier paramètre, avec sa valeur par défaut. `deploy/example` ajouté à l'impact, avec ce qu'une surcouche doit fournir : l'entrée de liste, l'adresse de BuildKit, les miroirs, la version de `knock`. |
| 14 | Contrôle · fenêtre d'adoption | Aucune. Le transit est obligatoire dès la fusion, et une version de `knock` pas encore commencée entre sur le chemin du premier screening réel du 2026-10-31, un *Must*, pour une story *Should*. | Mineure | Trancher la question ouverte : les manifestes de ce change fusionnent après le premier screening réel. |
| 15 | Ingénierie · coût plus tard | `census` tient pour admis tout ce qui porte le marquage de `knock`. Une image retenue le porte sans être signée : un transit tiré par des consommateurs resterait invisible du seul outil qui mesure le contournement. | Mineure | Le nommer dans « Hors de ce change », avec la piste : exclure le préfixe de transit, ou exiger la signature. |
| 16 | Ingénierie · faisabilité | D4 et D8 tiennent dans ce workflow, avec cinq pièges : un paramètre vide passé sans guillemets à `sh -c` fait sortir la première porte en erreur d'usage ; `promote` doit recevoir la politique préparée, sinon l'image est promue non signée ; le gabarit `knock` ne crée que `/work/plans` ; `continueOn.failed` seul ne couvre pas la phase `Error` ; l'étape finale qui fait échouer le screening doit vivre dans un gabarit sans reprise, en fin de liste. | Mineure | Les cinq deviennent des tâches du workflow, chacune vérifiée par `argo lint` ou par un passage du banc. |
| 17 | Contrôle · rejouabilité | Rien ne dit que `approve --staged` rend les entrées gardées telles que `knock` les a écrites. `promote` redérive ce qu'il peut, mais une entrée réécrite échouerait sans raison lisible. | Mineure | Un test : les entrées gardées sont identiques à celles du fichier lu. |
| 18 | Ingénierie · surface d'attaque | Trois des six formes sont touchées : un droit — l'écriture sur le transit, et la signature à la promotion — ; une dépendance nouvelle — BuildKit, et une version de `knock` — ; une exposition réseau — le port de `buildkitd` sur le banc. L'audit est dû et n'est pas conduit. | Mineure | Une tâche d'audit, avec sa checklist de repli si la commande manque. |
| 19 | DevEx · temps du banc | D9 ajoute `buildkitd` et deux reconstructions au banc par défaut, alors que le change `harbor-au-banc-local` pose qu'un banc qu'on hésite à lancer ne sert plus. Le temps ajouté n'est pas mesuré. | Mineure | Le mesurer. S'il pèse, la réparation devient une variante de `up.sh`, comme `dt` ; l'entrée de transit reste au banc par défaut. |
| 20 | Ingénierie · exactitude | Quatre formulations inexactes. Le fait 5 omet la clé `kind` d'une entrée, et le fichier n'est pas écrit si `knock` s'arrête avant son rapport. D3 dit « un préfixe où rien n'est jamais écrit », mais `knock` y ouvre une session à chaque passage. « Une seule tentative par empreinte source » ne vaut que pour une reconstruction refusée. « Identique, à l'octet près » vaut pour les couches, pas pour le manifeste, que `knock` ré-annote. | Mineure | Corriger les quatre dans `design.md`, `proposal.md` et la spec. |
| 21 | Ingénierie · irréversible | Le vocabulaire du journal est irréversible et n'a pas d'ADR. Les numéros `SDR-0014` et `SDR-0015` sont pris par le change ouvert. | Mineure | Un ADR propre à `uske`, au numéro libre suivant, dans la section ADR de `tasks.md`. |

## Critère d'achèvement

La revue est close quand :

- les findings 1, 2, 4 et 5 ont modifié `design.md` et le delta `rebuild-gate`, puis sont inscrits
  dans `tasks.md` avec leur test ;
- les findings 3 et 7 ont leur mesure en tête des tâches du banc, avec le repli nommé et le retour
  à la personne si aucune candidate ne ressort en placement direct ;
- le finding 6 est inscrit au plan de documentation, `README.md` et surcouche d'exemple ;
- les corrections des findings 10, 11, 12 et 20 sont faites dans les trois fichiers ;
- les findings 8, 9, 13, 16, 17, 18, 19 et 21 sont des tâches, et les findings 14 et 15 sont
  consignés dans `proposal.md`, le premier comme question tranchée.
