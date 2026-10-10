# Proposition — l'issue « transformation requise » agit : reconstruire dans un transit, juger la sortie, promouvoir ce qui est sain

## Why

Des quatre issues d'un verdict, seule `direct-placement` agit. Une source dont la faille critique a
un correctif est consignée, puis attend. Et quand une politique déclare un `transform`, `knock`
pousse l'image qu'il a reconstruite à sa destination sans que rien n'ait jugé ce qu'il a produit :
seule sa source l'a été.

`knock` vient de livrer ce qui manquait (son ADR 0055, `trivoallan/knock#310`, fusionnée le
2026-10-10). Avec un registre de transit, il y retient tout ce qu'il construit, écrit la liste des
images retenues, et `knock promote` ne place que celles qu'un fichier filtré nomme encore. Ce
change y branche le screening. C'est la story 4 de `openspec/discovery.md`, `issue-transformation`,
classée *Should*.

**Objectif qualité.** Ce change sert la **sûreté** (rang 1 de `docs/architecture/arc42.md`, §1) :
aucune image reconstruite n'atteint une destination sans son propre verdict, et une source à
réparer n'est approuvée que si le placeur dit qu'il la reconstruira. Il sert la **contestabilité**
(rang 2) : le verdict de l'image reconstruite et le refus de la version s'écrivent au journal. Il
arbitre une fois, la sûreté contre l'**opérabilité** (rang 3) : le transit devient obligatoire pour
tout déploiement, y compris ceux qui ne reconstruisent rien. `uske` gagne une seconde boucle sans
entamer la **minceur** (rang 4) : il ne juge toujours rien et ne place toujours rien.

## Détection

- `.nanopm/wiki/docs/product.md` est présent : rien à proposer.
- `docs/adr/SDR-0013-frontend.md` est en `status: proposed`. Son verdict est **déjà pris en charge**
  par le change `demenagement-gitlab-et-livraison`, qui l'a reçu le 2026-09-20 et le conduit. Le
  proposer ici le ferait rendre deux fois ; la branche des verdicts n'est pas ouverte dans ce
  change, et ce n'est pas un refus.
- `docs/architecture/arc42.md` existe : rien à proposer.

## Passes de cadrage

Cadrage conduit par `superpowers:brainstorming` le 2026-10-10, depuis une session ouverte sur la
PR `trivoallan/knock#310`. Les questions sont passées par `AskUserQuestion`, **une par envoi** et
non groupées par passe : la borne du schéma n'est pas tenue telle qu'elle est écrite. Compte réel :

1. **Périmètre** — brancher `uske`, plutôt que mettre à jour le dossier `docs` ou les deux.
2. **Portée** — la story 4 entière, plutôt que la seconde porte seule.
3. **Preuve** — le banc local de bout en bout, plutôt qu'un passage à la main ou les tests seuls.
4. **Approche** — `knock` dit ce qu'il construit, plutôt que `uske` le devine.
5. **Emplacement** — ce change, plutôt qu'un fichier hors du schéma.

Puis trois envois de section de conception, en prose, tous acceptés ; le deuxième avec une
réponse : la source d'une reconstruction refusée est close par une ligne `quarantine`. La
découverte n'a consommé aucune passe.

## What Changes

- **Routage** — `approve` garde une opération dont la source est en `transformation-required`
  quand le plan de `knock` la dit `transformed`. Champ absent : refus. La règle sur
  `direct-placement` ne change pas.
- **Transit** — `place` passe toujours `--stage-to` et `--staged-out` à `knock reconcile
  --apply-plan`. Le workflow gagne un paramètre `transit`, un nom de `KNOCK_REGISTRIES`. Les copies
  sont placées comme aujourd'hui ; tout ce qui est construit est retenu.
- **BREAKING pour un déploiement** — l'entrée de transit est obligatoire. Sans elle, `place`
  échoue et rien n'entre. Rien n'étant déployé, le coût est nul aujourd'hui.
- **Seconde porte** — après `place`, la même boucle rejoue sur les images retenues : celles encore
  dues, leur jugement par le même playbook, leur consignation, le fichier filtré, puis `knock
  promote`. Seul `direct-placement` promeut.
- **Journal** — une ligne par image retenue jugée, avec une clé facultative `source` qui porte
  l'empreinte de sa source. Quand la reconstruction est refusée, une seconde ligne clôt la source :
  `state: quarantine`, `reason: uske/rebuild-refused`. Une seule tentative par empreinte source.
- **Sous-commandes** — aucune nouvelle. `pending` et `approve` acceptent `--staged` à la place de
  `--plan` ; `classify` reçoit la source d'une image retenue.
- **Banc local** — un `buildkitd`, une entrée de transit, un miroir de paquets et deux politiques
  de démonstration : l'une sort réparée, promue et signée ; l'autre sort refusée, absente de la
  destination, avec ses deux lignes au journal.
- **Hors de ce dépôt, en prérequis** — `knock` ajoute `transformed` à chaque opération de son plan,
  et publie une version qui contient aussi sa PR #310. Le banc épingle aujourd'hui `knock` 0.12.0,
  qui la précède.
- **Écrits** — `README.md` (« seul le placement direct agit » devient faux), la story 4 dans
  `openspec/discovery.md`, les *Essential Features* de `docs/architecture/arc42.md`.

Les artefacts emploient les noms d'après le renommage `orchestrator` → `uske` que porte
`demenagement-gitlab-et-livraison`.

## Alternatives écartées

- **Ne rien faire** — écartée : l'issue reste muette, et toute politique à `transform` continue de
  placer une sortie que personne n'a jugée.
- **La seconde porte seule**, sans approuver les sources `transformation-required` — écartée le
  2026-10-10 : elle laisse muette l'issue que la story nomme, pour un écart de code faible.
- **`uske` relit la politique pour savoir ce qui sera reconstruit** — écartée : un `transform` se
  déclare à trois niveaux (`defaults`, import, variante), et `uske` réimplémenterait la fusion de
  `knock`. Le jour où elles divergent, une source à réparer est copiée telle quelle, sans bruit.
- **Une règle grossière** : ne réparer que les politiques dont le `transform` est dans `defaults`
  seulement — écartée : la sûreté reposerait sur une hypothèse à propos de `knock` que rien ne
  vérifie.
- **Un transit éphémère lancé par le workflow** — écartée pour ce change : TLS ou HTTP en clair à
  régler dans quatre outils, et un volume à dimensionner pour toutes les couches d'un passage. Elle
  reste possible plus tard sans toucher au Python : c'est un choix de manifeste.
- **Un interrupteur pour se passer de transit** — écartée : sans transit, une source
  `transformation-required` approuvée serait reconstruite et placée sans que sa sortie soit jugée.
- **Ne rien écrire sur la source**, et laisser `approve` chercher une image retenue refusée qui la
  nomme — écartée le 2026-10-10 : la version resterait en `transformation-required` au journal
  alors qu'elle est refusée.
- **De nouvelles sous-commandes pour la seconde porte** — écartée : ce sont les mêmes gestes sur un
  autre fichier.
- **Un passage réel hors du banc, ou les tests seuls** — écartées le 2026-10-10 : une story est une
  tranche démontrable, et `knock` a trouvé les deux défauts de sa PR au passage réel, pas dans ses
  tests.

## Conception

`design` est dû : changement transverse — le plan de `knock` gagne un champ, sur deux dépôts — ;
modèle de données qui change — le journal gagne une clé et une raison — ; et ambiguïtés que des
décisions techniques lèvent avant le code : qui clôt la source, ce que fait une panne de `place`.

## Revue

`review` est due. Une décision est irréversible à la première ligne réelle : le vocabulaire du
journal — la clé `source`, la raison `uske/rebuild-refused`, la clôture en `quarantine` — s'écrit
dans un fichier en ajout seul. Et la surface d'attaque bouge : l'identité de `knock` écrit dans un
lieu de plus, et `promote` écrit dans la destination et signe sur la foi d'un fichier que `uske`
filtre.

## Capabilities

### New Capabilities

- `rebuild-gate`: ce qu'un screening garantit d'une image que le placeur construit — elle est
  jugée dans le transit avant toute destination, promue seulement sur un placement direct, tentée
  une seule fois par empreinte source, et chacune de ces décisions est consignée.

### Modified Capabilities

Aucune. `repository-method` ne décrit pas le screening. `local-bench` n'est pas sur `main` : elle
vit dans le change `harbor-au-banc-local` (PR #7). Si elle y arrive avant ce change, l'épreuve du
banc s'y ajoute en delta ; sinon elle reste un critère des tâches.

## Impact

- **Fichiers** : `uske/gate.py`, `uske/cli.py`, `uske/results.py` ; `tests/test_orchestrator.py`
  et ses fichiers figés ; `deploy/base/workflowtemplate.yaml` ; `deploy/kind/up.sh`,
  `deploy/kind/kustomization.yaml`, deux politiques sous `deploy/kind/policies/` et un manifeste
  pour `buildkitd` ; `README.md`, `openspec/discovery.md`, `docs/architecture/arc42.md`.
- **Dépendances** : aucune dépendance Python nouvelle. Une version de `knock` à paraître ; l'image
  de BuildKit, tirée au montage du banc seulement.
- **Surface d'attaque** : l'identité de `knock` reçoit l'écriture sur le transit. Un transit que des
  consommateurs peuvent tirer n'en est pas un ; `knock` ne refuse que celui qui est aussi une
  destination de la politique. Sa fermeture relève du registre, pas de ce change.
- **Ordre** : le Python et ses tests peuvent précéder. Les manifestes viennent après
  `demenagement-gitlab-et-livraison`, qui renomme tout `deploy/`, et après la version de `knock`.
- **Premier screening réel**, dû le 2026-10-31 : si ce change est fusionné avant, la surcouche de
  staging doit nommer un transit, même si aucune politique n'y reconstruit.
- **Hors de ce change** : le dossier `docs` (D-32, DEBT-21, §5.2), qui décrit encore un transit
  proposé ; la consignation d'une construction en échec ; la levée d'une source close ; la
  fermeture et la rétention du transit ; l'issue `quarantine` qui agit (story 3).
- **Branche** : `github-flow`, `squash`, préfixe `feat` selon `SDR-0009`.

## Questions ouvertes

- **Quelles images pour le banc ?** Il en faut une dont la source tombe dans le tier
  « Transformation requise » et sort réparée, et une qui ne l'est pas. Les notes de `knock` donnent
  des candidates (`alpine:3.18.0`, `redis:7.2.0`), non vérifiées contre le playbook complet. Le
  résultat dépend de la base de failles du jour.
- **La story 4 attend-elle la story 1 ?** `openspec/discovery.md` l'en fait dépendre. Ce change se
  prouve sur le banc et ne l'attend pas ; à confirmer.
- **Le nom du champ côté `knock`.** `transformed` est celui que `knock` emploie déjà dans son
  prédicat de provenance ; c'est à son propre change de le fixer.
- **La variante Harbor du banc.** Si `harbor-au-banc-local` est fusionné, le transit peut y être un
  projet privé, et le banc prouverait alors la fermeture que Zot ne prouve pas.
