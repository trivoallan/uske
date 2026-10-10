# Conception — l'issue « transformation requise », par le transit de `knock`

**Sections arc42 touchées** : §1 *Introduction and Goals* — les *Essential Features* gagnent le
transit et la seconde porte. Aucun bloc de `uske` ne bouge : le transit est une entrée de la liste
de registres de `knock`, pas un composant de ce dépôt, et §7 *Deployment View* reste au gabarit.

## Context

Ce que le code fait aujourd'hui, lu le 2026-10-10 :

1. `gate.approve` ne garde que les opérations dont l'empreinte source est en `direct-placement`.
   Les trois autres issues sont consignées et ne placent rien.
2. Le journal est indexé par empreinte. `pending` ne rejuge que ce qui n'a jamais été décidé ou
   qui est `inconclusive` ; `append` écarte une ligne qui répète le dernier état d'une empreinte.
3. Le banc n'a pas de voie reconstruction : pas de BuildKit, aucune politique à `transform`, et
   `knock` y est épinglé en 0.12.0.

Ce que `knock` fait depuis sa PR #310 (ADR 0055), lu dans son code à `ce2278b` :

4. `reconcile --apply-plan F --stage-to NOM --staged-out G` pousse tout ce qu'il **construit** dans
   le registre `NOM` de `KNOCK_REGISTRIES`, au chemin de la destination. L'image y est marquée,
   inventoriée, attestée, et **pas signée comme admise**. Les copies sont placées directement. Les
   trois options vont ensemble.
5. `G` est un document `StagedRebuilds` : une entrée par image retenue, avec `policy`, `import`,
   `variant`, `kind`, `destination`, `tag`, `source`, `sourceTag`, `sourceDigest`, `staged`,
   `stagedDigest` et `aliases`. Il est écrit **même quand des opérations ont échoué** ; le code de
   sortie est alors non nul. Il ne l'est pas si `knock` s'arrête avant son rapport, sur une erreur
   de configuration.
6. `promote DIR --staged G'` place les entrées qu'un fichier filtré nomme encore. Il redérive la
   destination, le lieu de transit et l'identité de l'image ; il copie par empreinte avec les
   attestations, vérifie qu'elles sont arrivées, écrit le tag, signe si la politique admet, puis
   rejoue les alias. Une entrée en échec n'arrête pas les autres. Rejouer le même fichier ne change
   rien.
7. Une image retenue et jamais promue ne laisse aucune trace dans la destination : l'opération
   revient au plan suivant. **C'est le journal de l'orchestrateur qui arrête la répétition.**
8. Un hôte de la liste accepte un préfixe de chemin (`registre/transit`), et l'entrée la plus
   spécifique l'emporte. `knock` ne refuse qu'un transit dont l'hôte est exactement celui d'une
   destination de la politique.
9. Une opération du plan porte `policy`, `kind`, `destination`, `tag`, `source`, `sourceTag`,
   `sourceDigest`. **Elle ne dit pas si elle sera reconstruite**, et un `transform` se déclare à
   trois niveaux : `defaults`, import, variante.

Décisions en vigueur qui contraignent cette conception — aucun ADR n'en dépasse un autre, tous
portent `supersedes: []` : `SDR-0001` (ADR immuables), `SDR-0002` (prose en français, code et
commentaires en anglais), `SDR-0003` (hexagonal), `SDR-0005` (validation aux frontières),
`SDR-0007` (couverture), `SDR-0009` (github-flow, `squash`). `SDR-0013` est `proposed` et ne
contraint rien.

## Goals / Non-Goals

**Goals**

- Une source en `transformation-required` est reconstruite quand le placeur dit qu'il la
  reconstruira, et seulement alors.
- Aucune image reconstruite n'atteint une destination sans un verdict sur sa propre empreinte.
- Une reconstruction refusée n'est tentée qu'une fois par empreinte source.
- Le banc local le montre de bout en bout, sur une réparation réussie et une refusée.

**Non-Goals**

- Juger ou placer : `uske` appelle, attend, écrit.
- Fermer le transit aux consommateurs, ou y tenir une rétention. `knock` n'y supprime rien.
- Consigner une construction qui échoue, ou rouvrir une source close.
- Faire agir l'issue `quarantine` (story 3).
- Mettre à jour le dossier `docs`, qui décrit encore un transit proposé.
- Rapprocher le code de `SDR-0003` et `SDR-0005` : ce chantier passe après le premier screening
  réel, décidé le 2026-09-20.

## Decisions

**D1 — `knock` dit ce qu'il construit.** Chaque opération de son plan gagne un booléen
`transformed`, hors de la clé d'approbation. C'est une petite PR additive dans `knock`, avec son
propre change. Alternatives écartées : relire la politique dans `uske`, ou une règle grossière —
voir `proposal.md`. Le fait 9 les rend toutes deux fragiles, et l'échec serait silencieux : une
source à réparer copiée telle quelle.

**D2 — La règle de `approve`.** Une opération est gardée si sa source est en `direct-placement`,
ou en `transformation-required` avec `transformed` à vrai **et un transit nommé à `approve`**, par
une option `--transit` que seul le workflow à seconde porte passe. Champ absent vaut faux, option
absente vaut la règle d'avant ce change. La panne est fermée des deux côtés : un `knock` qui
n'écrit pas le champ ne répare rien, et un workflow sans transit ne reçoit jamais une source à
réparer, même avec l'image neuve de `uske` (revue, finding 2). `approve` rend aussi le nombre
d'opérations écartées, par cause.

**D3 — Le transit est un nom, toujours passé, obligatoire.** Le workflow reçoit un paramètre
`transit` ; `place` passe `--stage-to` et `--staged-out` pour toute politique. Une politique en
voie copie produit un fichier vide et la suite ne fait rien : un seul chemin. Sans entrée de
transit dans la liste, `knock` refuse de tourner et rien n'entre. Alternative écartée : un
interrupteur. Sans transit, une source approuvée par D2 serait reconstruite et placée sans que sa
sortie soit jugée. Pour un déploiement qui ne reconstruit rien, le coût est une clé de plus dans
un secret, pointant un préfixe où rien n'est écrit, mais où `knock` ouvre une session à chaque
passage.

**D4 — La seconde porte rejoue la première, avec les mêmes verbes.** Après `place` :

1. `pending --staged G` rend un candidat par `stagedDigest` encore dû, pour cette politique :
   `ref` = `{staged}:{tag}`, `digest` = `stagedDigest`, `target` = `{staged}@{stagedDigest}`, et
   la source dont il vient.
2. Le gabarit `evaluate` existant le juge, avec le playbook déjà résolu pour la politique. Il
   écrit ses lignes dans un **répertoire propre à la seconde porte**, passé en paramètre : dans
   celui de la première, `record` relirait la ligne de la source après sa clôture et la rouvrirait
   (revue, finding 1).
3. `record` consigne.
4. `approve --staged G` écrit `G` moins les entrées dont l'image retenue n'est pas en
   `direct-placement`.
5. `knock promote` place ce qui reste, s'il reste quelque chose.

Seul `direct-placement` promeut. Ces étapes forment une sous-séquence du workflow, appelée quand
`approve` a gardé au moins une opération. Alternative écartée : des sous-commandes propres à la
seconde porte ; ce sont les mêmes gestes sur un autre fichier.

**D5 — Une image retenue a sa ligne, qui nomme sa source.** Mêmes clés qu'une ligne d'aujourd'hui,
plus une clé facultative `source` : l'empreinte source. Le rapport `regis` de l'image retenue est
conservé sous sa propre empreinte, comme les autres. Un lecteur qui part de la source retrouve
l'image retenue par cette clé.

**D6 — Une reconstruction refusée clôt sa source.** Quand l'image retenue ressort en
`transformation-required` ou en `quarantine`, le même `classify` émet deux lignes : celle de
l'image retenue, puis une ligne sur l'empreinte source — `state: quarantine`, `reason:
uske/rebuild-refused`. Ses autres clés sont fixées : `ref` = la référence source, `ruleset` = le
jeu de règles qui a jugé l'image retenue, `report` = le rapport de l'image retenue, et `rebuilt` =
l'empreinte de l'image retenue, où se lit la règle en échec. `record` accepte déjà une liste par
fichier. Le préfixe est `uske/`, sans condition : une raison neuve n'a aucun passé à suivre. Cette
clôture n'est pas une quarantaine prononcée par le juge ; la story 3 devra les distinguer par la
raison.

| Verdict de l'image retenue | Lignes écrites | Au screening suivant |
|---|---|---|
| `direct-placement` | une, sur l'image retenue | promue ; l'opération n'est plus au plan |
| `transformation-required`, `quarantine` | deux : l'image retenue, puis la source close | `approve` écarte la source, `pending` ne la rejuge pas |
| `inconclusive` | une, sur l'image retenue | la source reste approuvable : reconstruite, rejugée |

**Une règle qui n'a pas conclu ne clôt rien.** Quand aucune règle critique n'a échoué et qu'une
règle est restée *incomplete*, `classify` rend `inconclusive`, pour les deux portes : le tier a été
manqué sur une règle que le juge n'a pas su lire. Trouvé sur le banc, où une image réparée était
close parce que `regis` ne lisait pas sa date de création (`trivoallan/regis#870`).

Alternative écartée le 2026-10-10 : ne rien écrire sur la source et laisser `approve` chercher une
image retenue refusée qui la nomme. La version resterait `transformation-required` au journal
alors qu'elle est refusée, et `approve` gagnerait une recherche.

**Cette décision est irréversible à la première ligne réelle** : le journal ne se rature pas.

**D7 — Une reconstruction refusée n'est tentée qu'une fois ; les autres essais sont bornés ; une
ligne rouvre.** D6 donne la tentative unique sans logique nouvelle. Deux règles de plus :

- *La borne.* Un verdict non concluant fait reconstruire au screening suivant, sous une
  empreinte neuve à chaque fois. `approve` compte les lignes d'images retenues **non
  concluantes** dont `source` vaut l'empreinte, écrites depuis la dernière ligne sur l'empreinte
  source elle-même, et n'approuve plus à partir de **trois**. Rien n'est écrit : la source garde
  son état, et `approve` la compte parmi les écartées. Une réparation réussie ne compte pas :
  sinon trois variantes saines épuiseraient leur source (relecture finale, I3).
- *Une ligne plus ancienne ne s'écrit pas.* `append` écarte une ligne dont la date précède la
  dernière ligne du même digest. C'est ce qui tient « une source close reste close » quand une
  étape de consignation est rejouée, sans dépendre de l'ordre des fichiers ni du workflow
  (relecture finale, I1). Le répertoire propre à la seconde porte (D4) reste, en ceinture.
- *La réouverture.* Une ligne ajoutée à la main sur l'empreinte source — `state: inconclusive`,
  `reason: uske/reopened` — la rend due : `pending` la fait rejuger, la suite reprend, et le
  compte repart de zéro. Sa date doit être celle du geste : plus ancienne que la dernière ligne
  de la source, elle serait écartée. Aucun code nouveau. Le journal vivant sur un volume, le geste demande un
  pod jetable, et le `README.md` le décrit.

Trois plafonds de la borne, nommés plutôt que cachés (relecture finale, I2 et I3) : elle
compte des lignes, pas des screenings, donc quatre variantes et une panne du juge épuisent une
source en un passage — la corriger demande un identifiant de passage, que le journal n'a pas ;
elle suppose une empreinte neuve à chaque reconstruction, ce que le marquage horodaté de `knock`
garantit aujourd'hui — une reconstruction reproductible répéterait sa ligne, que `append`
écarterait ; et elle ne voit pas une promotion en échec, que le journal ne distingue pas d'une
réussite.

Trois limites, assumées :

- Une source close ne se rouvre pas seule : ni un nouvel `epoch` de `upgradePackages`, ni un
  correctif paru depuis, ni un miroir de paquets qui rattrape son retard. Et la reconstruction
  est tentée même quand aucune étape déclarée ne peut lever la règle en échec — `no-root`, par
  exemple, qu'aucune étape de `knock` ne fixe. Savoir quelle étape répare quelle règle est hors
  de ce change.
- Un tag déjà en service dont la re-réparation est refusée garde son ancienne image, et sa source
  est close.
- La clôture porte sur l'empreinte source, donc sur toutes ses variantes et toutes ses
  destinations : une variante refusée empêche de reconstruire plus tard une variante saine, et
  clôt une source dont une copie peut être en service.

Une construction qui échoue n'écrit aucune ligne : la borne ne la voit pas. `place` sort des
reprises communes d'Argo, pour ne pas tripler chaque essai.

**D8 — Une panne n'emporte pas ce qui a réussi.**

- *Une opération échoue pendant `place`.* Le fichier des images retenues existe quand même (fait
  5). La seconde porte tourne sur ce qui a été retenu, puis le screening de la politique finit en
  échec. Sans cela, un seul tag impossible à reconstruire bloquerait la promotion de tous les
  autres, à chaque screening.
- *Une entrée échoue pendant `promote`.* Les autres sont placées, l'étape finit en échec, rien
  n'est écrit au journal. L'opération revient au plan suivant, la source est toujours approuvable.
  Les reprises d'Argo sont sans risque (fait 6).
- *Pas de fichier d'images retenues.* Aucun candidat, rien de promu.

**D9 — Le banc : un préfixe du même registre, et la réparation en variante.** Le banc par
défaut ne gagne que l'entrée de transit, obligatoire, et ne reconstruit rien. `up.sh repair`,
sur un banc déjà monté comme `up.sh dt`, ajoute le reste : un passage de la voie reconstruction
retient des dizaines de gigaoctets de couches dans le nœud, et a rempli un disque le
2026-10-10 (revue, finding 19). Il ajoute un `buildkitd` sans privilège,
repris du composant de `knock` et qui fait confiance à l'autorité de certification du banc ; une
entrée `transit` dans `KNOCK_REGISTRIES`, préfixe du Zot existant ; un miroir de paquets dans
`KNOCK_TRANSFORM_PACKAGE_MIRRORS`, dont les dépôts publics de la distribution tiennent lieu ; et
deux politiques sous le régime `standard`, le seul dont le playbook a le tier « Transformation
requise », qui déclarent `rewritePackageSources` puis `upgradePackages`. `knock` ne porte aucun
réglage pour l'adresse du démon : `buildctl` la lit dans son environnement, à confirmer au
montage. Alternative écartée : un second registre, ou un registre éphémère — un composant de plus
pour un banc jetable.

**D10 — Les tests.** Dans `tests/test_orchestrator.py`, sur un plan et un fichier d'images
retenues figés :

- `approve` garde `transformation-required` si `transformed`, la refuse sinon, la refuse si le
  champ manque ;
- `pending --staged` rend un candidat par `stagedDigest`, saute les décidés, rend une liste vide
  sans fichier ;
- `approve --staged` ne garde que `direct-placement` ;
- `classify` d'une image retenue écrit deux lignes sur un refus, une sinon ;
- après la ligne de clôture, le même plan n'est plus approuvé, même quand la ligne de première
  porte de la source est rejouée ;
- `approve` sans `--transit` refuse `transformation-required` ;
- trois images retenues non concluantes pour une source : elle n'est plus approuvée ; une ligne
  `uske/reopened` la rend due ;
- `approve --staged` rend les entrées gardées telles qu'il les a lues, et un fichier vide sans
  fichier lu ;
- `argo lint` passe sur les manifestes.

## Risks / Trade-offs

- La base de failles bouge → les deux images du banc peuvent changer de tier d'un jour à l'autre.
  Les choisir par la mesure, et écrire dans la politique ce qu'on attend d'elles.
- `deploy/kind` patche le workflow par index de gabarit → tout gabarit ajouté avant un index
  patché le décale. Ajouter en fin de liste ; `argo lint` et un passage du banc le montrent.
- Une construction qui échoue toujours se rejoue à chaque screening, trois fois avec les reprises
  d'Argo, et fait finir la politique en échec → visible, mais nulle part au journal. Suite nommée
  dans `proposal.md`.
- Le transit accumule : `knock` n'y supprime rien → sans objet sur un banc jetable ; sur un
  registre réel, c'est à son exploitant d'y tenir une rétention.
- Zot n'a aucun contrôle d'accès → le banc ne prouve pas que le transit est fermé.
- `regis` ne s'authentifie qu'à un hôte, et `knock` n'ouvre qu'une session par hôte nu → le
  transit vit sur l'hôte de la destination, avec une seule identité `knock` pour les deux projets
  et la lecture pour `regis`. Écrit dans le `README.md` et la surcouche d'exemple.
- La version de `knock` tarde → le Python et ses tests ne l'attendent pas ; le workflow et le banc,
  si.
- Un `knock` sans `transformed` ne répare rien, sans bruit → le `README.md` dit la version
  minimale.
- La clôture par empreinte source est grossière (D7) → acceptée ; l'affiner demande une clé de
  décision plus fine que l'empreinte, ce qui touche tout le journal.

## Migration Plan

1. Dans `knock` : `transformed` au plan, puis une version publiée.
2. Ici, le Python : `gate`, `cli`, `results`, et leurs tests.
3. Ici, le workflow et le banc, sur l'image `knock` publiée, après le renommage de `deploy/` et
   **après le premier screening réel** : le transit obligatoire n'entre pas sur son chemin.
4. Ici, les écrits : `README.md`, `openspec/discovery.md`, `docs/architecture/arc42.md`.

**Retour arrière.** Révoquer la fusion suffit tant qu'aucun journal réel ne porte une ligne à clé
`source` ou une clôture. Après, ces lignes restent lisibles par l'ancien code — il n'en lit que
`digest` et `state` — mais une source close le reste.

## Open Questions

- **La lecture du fichier des images retenues, à la main ou validée ?** `SDR-0005` décide une
  validation aux frontières, et `knock` publie un schéma JSON pour ce fichier. Le plan est lu à la
  main aujourd'hui (`DEBT-02`), et le rapprochement est remis à après le premier screening réel.
  Proposé : à la main ici, comme le plan, pour ne pas ouvrir ce chantier par un seul fichier.
- **Un ADR propre à `uske` ?** Le transit obligatoire (D3) et le vocabulaire du journal (D5, D6)
  contraignent les changes suivants. Aucun ADR n'est encore propre à ce dépôt ; la section ADR de
  `tasks.md` tranche.
- Les images du banc, la dépendance à la story 1, le nom du champ dans `knock` et la variante
  Harbor : listées dans `proposal.md`.
