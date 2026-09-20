# Conception — déménagement sur GitLab et livraison d'une version épinglable

**Sections arc42 touchées** : §9 *Architecture Decisions* — le journal des décisions accueille
trois ADR, et trois écarts passent *Closed*. Aucun bloc ni frontière de déploiement ne bouge dans
ce dépôt : le déploiement lui-même vit dans le dépôt GitOps de l'employeur, et §7 *Deployment View*
reste au gabarit jusque-là.

## Context

`uske` est une graine : le code d'un screening, des manifestes Argo Workflows, et un banc local
`kind` où tout a été éprouvé. Rien n'est déployé, aucune version n'est nommée, `pyproject.toml`
porte `0.0.0` et le distant n'a aucun tag — vérifié le 2026-09-20.

Le premier screening réel est dû le 2026-10-31 sur le staging de l'employeur. Le cadrage a établi
cinq faits qui décident de tout ce qui suit :

1. Le staging est une préproduction distincte, que l'employeur a déjà, et la marche qui précède la
   production.
2. Rien n'y est installé, mais les ressources sont gérées par ArgoCD depuis un dépôt GitOps.
3. Un Harbor de staging existe, tenu par une autre équipe ; `uske` n'a pas à le monter.
4. Le cluster ne tire que du Harbor interne, et la sortie vers les registres sources publics passe
   par le proxy de l'entreprise, avec son autorité de certification.
5. La forge de l'employeur est GitLab, et `uske` y déménage.

Les décisions en vigueur qui contraignent cette conception, après construction du graphe de
dépassement (`supersedes:` vide partout, aucun ADR n'en dépasse un autre au 2026-09-20) :
`SDR-0001` (les ADR sont immuables), `SDR-0002` (prose en français, code et commentaires en
anglais), `SDR-0003` (hexagonal, arc42), `SDR-0006` (`commitlint`), `SDR-0008` (`docs/`),
`SDR-0009` (github-flow, `squash`), `SDR-0010` (forge et intégration), `SDR-0011` (livraison).
`SDR-0013` est `proposed` : il ne contraint rien tant qu'il n'a pas reçu son verdict.

## Goals / Non-Goals

**Goals**

- Produire une version nommée, et l'image correspondante dans le registre interne.
- Rendre `deploy/base` consommable depuis un autre dépôt, sans patch à index, et le prouver à
  chaque demande de fusion.
- Poser les noms de ressources définitifs avant qu'un environnement ne les grave dans ses secrets.
- Refermer les trois écarts que la chaîne d'intégration peut refermer : `DEBT-03`, `DEBT-05`,
  `DEBT-06`.

**Non-Goals**

- Installer Argo Workflows, écrire la surcouche `staging`, poser ses secrets, lancer le premier
  screening : tout cela vit dans le dépôt GitOps de l'employeur.
- La fédération d'identité et l'archive PostgreSQL : elles servent l'interface d'Argo Workflows,
  qui n'est pas installée avant la production.
- Le rapprochement du code avec `SDR-0003` et `SDR-0005` (`DEBT-01`, `DEBT-02`) et la mesure de
  couverture (`DEBT-04`) : décidé le 2026-09-20, ce chantier passe après le premier screening
  réel, pour ne pas organiser le code d'après les fixtures.
- Toute modification du comportement de `uske`.

## Decisions

**D1 — GitLab devient l'amont, GitHub un miroir poussé.** Alternative pesée : garder GitHub en
amont et miroiter vers GitLab. Écartée parce que `releaser-pleaser` écrirait sur le miroir des
commits que l'amont n'a pas, et que les deux divergeraient. Le miroir garde une adresse publique
citable — le dépôt `docs/` en a besoin depuis la suppression de `docs/orchestrator/` — et la
vision d'ouverture ne perd rien. `.github/workflows/` est supprimé dans la même demande de fusion :
un miroir poussé relancerait sinon les mêmes tests une seconde fois.

**D2 — L'image se construit dans le Harbor interne, pas sur un registre public.** Le cluster ne
tire que de là (fait 4). Publier d'abord sur `ghcr.io` puis recopier ajouterait un saut sans
lecteur : personne, aujourd'hui, ne tire `uske` depuis l'extérieur. Le jour où le dépôt s'ouvrira,
un second job publiera vers un registre public — c'est un ajout, pas une reprise. `regis` et
`knock`, eux, restent publics et entrent par le proxy-cache : ils ne sont pas construits ici.

**D3 — Le `Dockerfile` reçoit des `ARG` plutôt qu'un fichier de construction propre à l'entreprise.**
Trois paramètres : l'image `cosign`, l'image `python`, l'index des paquets. Les valeurs par défaut
restent publiques, donc `docker build .` marche encore chez un adopteur, et la CI les remplace par
le registre et le miroir internes. Alternative écartée : un second `Dockerfile`, qui dériverait du
premier à la première modification.

**D4 — La base se paramètre par trois chemins, et rien d'autre.** `images:` pour les quatre images
(`git`, `uske`, `regis`, `knock`), `/spec/arguments/parameters` remplacé en bloc pour le dépôt, la
politique et les playbooks, et `/spec/podSpecPatch` pour le proxy, `NO_PROXY`, `SSL_CERT_FILE` et
le montage de l'autorité de certification. Aucun de ces trois ne dépend de l'ordre ni du nombre des
gabarits. Alternative écartée : ajouter à la base des crochets faits exprès — un `envFrom`
optionnel, un montage à chemin fixe. Inutile, puisque `podSpecPatch` les couvre ; et un crochet
sans second utilisateur est une abstraction spéculative. `deploy/kind` garde ses patches à index :
il vit dans le dépôt, il casse bruyamment, il n'a pas besoin du contrat.

**D5 — `deploy/example` est le contrat, et c'est la CI qui le tient.** Une surcouche factice,
rendue et passée à `argo lint --offline` à chaque demande de fusion. C'est le seul contrôle
permanent que la base reste consommable de l'extérieur, et c'est aussi le fichier qu'on copie pour
écrire la surcouche `staging`. Sans lui, un déplacement de gabarit ne se verrait qu'au déploiement
suivant, dans un autre dépôt.

**D6 — Le renommage `orchestrator` → `uske` a lieu maintenant, avant `v0.1.0`.** Ces noms sont le
contrat qu'une surcouche épingle et sous lesquels les secrets d'un environnement sont créés. Tant
que rien n'est déployé et qu'aucun tag n'existe, le renommage ne coûte qu'un `sed` et un passage du
banc. Après J2, il coûterait de recréer les secrets et le volume du journal. Le nom générique avait
un sens tant que `docs/orchestrator/` portait le même rôle sous un autre nom ; ce répertoire est
supprimé, et dans `deploy/` il ne s'agit plus que de `uske`.

**D7 — La vérification des ADR entre dans la chaîne.** `DEBT-06` se referme par « le contrôle
ajouté à la chaîne, ou dit manuel dans un ADR qui dépasse `SDR-0010` » ; ce change fait les deux
gestes possibles à la fois, et retient le contrôle. Le job lance l'outil depuis le paquet déjà
déclaré dans `package.json`. **Repli nommé d'avance** : si Node manque sur l'exécuteur, ou si le
lien de binaire est capricieux — la mémoire du dépôt relève ce défaut sur le poste de l'auteur —,
le job prend le binaire autonome des *releases* de l'outil, épinglé par version et vérifié par
empreinte, comme le fait déjà le job qui installe `argo`.

**D8 — `commitlint` vérifie le titre de la demande de fusion, pas les commits de la branche.**
`SDR-0009` a décidé `squash` : le titre devient le message, et c'est de lui que `releaser-pleaser`
déduira la version. Vérifier les commits intermédiaires laisserait passer le seul texte qui compte.
En GitLab, ce titre est disponible dans la variable de la demande de fusion ; le job ne s'exécute
que dans ce contexte.

**D9 — Les deux environnements partent au déclencheur `manuel`.** `SDR-0011` proposait `staging`
sur fusion et `production` sur tag. Aucun des deux ne décrit ce qui va se passer : la mise en
service est un changement de version épinglée dans le dépôt GitOps, fait à la main par une
personne. Écrire `merge` ou `tag` affirmerait une automatisation — Renovate, un *image updater* —
qui n'existe pas. `manuel` est la réponse honnête, et elle se révisera quand l'automatisation
existera.

**D10 — `releaser-pleaser`, avec son repli écrit dans l'ADR.** `SDR-0011` tenait le composant pour
mirroré sur aucune instance. Si la vérification le confirme, `SDR-0015` écrit `release.tool:
manuel`, `DEBT-05` reste ouvert et l'ADR dit pourquoi. Le reste du change ne dépend pas de ce
choix : le tag se pose, l'image se construit.

## Risks / Trade-offs

- `releaser-pleaser` indisponible sur l'instance → repli `manuel` écrit dans `SDR-0015` ; le tag
  `v0.1.0` se pose à la main et rien d'autre ne bouge.
- Node absent des exécuteurs → binaire autonome épinglé et vérifié par empreinte (D7).
- Le renommage laisse un résidu → `grep -r orchestrator` doit revenir vide hors de
  `openspec/changes/archive/`, puis le banc `kind` rejoue un screening complet.
- La CI reçoit un droit d'écriture sur le registre → un compte robot borné à **un** projet, et rien
  d'autre ; aucune identité qui puisse écrire ailleurs.
- Le dépôt est miroité en clair → aucun nom propre à l'employeur dans un fichier suivi ; hôte,
  projet et chemins internes passent par des variables de la chaîne. Le contrôle est une relecture,
  pas un outil : c'est sa limite.
- `commitlint` sur le titre impose un format dès la première demande de fusion → c'est le but ;
  le coût est qu'un titre refusé bloque une fusion pressée.
- Le miroir cesse d'être poussé sans qu'on le voie → l'adresse publique que `docs/` cite se fige
  en silence. Aucun contrôle ne l'attrape ; la relecture du dépôt `docs/` le verra.
- `SDR-0013` nomme un portail interne dans sa prose héritée ; le verdict `rejected` retire les
  `traits:`, pas le texte. À trancher au moment d'ouvrir le dépôt, pas ici.

## Migration Plan

1. Créer le projet GitLab et le miroir poussé vers GitHub — gestes de la personne, identifiants
   compris.
2. Dans une demande de fusion : renommage, `.gitlab-ci.yml`, suppression de `.github/`,
   `deploy/example`, `ARG` du `Dockerfile`, les trois ADR, la mise à jour d'arc42, la version.
3. Vérifier la chaîne au vert sur cette demande de fusion, `deploy/example` et `deploy/kind`
   rendus et lintés, la vérification des ADR silencieuse.
4. Fusionner, poser `v0.1.0`, vérifier que l'image existe dans le registre interne et se tire
   depuis le cluster.

**Retour arrière.** Avant l'étape 4, révoquer la demande de fusion suffit : le dépôt GitHub existe
encore et rien n'a été publié. Après, un tag ne se défait pas mais ne gêne pas : une surcouche
épingle une empreinte, et une version suivante se pose.

## Open Questions

- **ADR à dépasser** : `SDR-0010` et `SDR-0011` sont en vigueur et cette conception s'en écarte.
  Ils ne se modifient pas ; la section `## ADR` de `tasks.md` consigne `SDR-0014` et `SDR-0015`.
- La disponibilité de `releaser-pleaser`, la protection de branche, Node sur les exécuteurs et le
  gabarit CI d'entreprise : quatre faits à établir avant d'écrire les ADR, listés dans
  `proposal.md`.
- **Le journal vit sur un volume, pas dans le dépôt de politiques.** La feuille de route annonce
  une ligne « relue dans le dépôt de politiques » ; `record` écrit dans un volume persistant. Le
  relire demandera un pod jetable. Rien à décider ici : c'est une entrée pour la story
  `retrouver-un-refus`.
- **Les deux volumes sont `ReadWriteOnce` sur un cluster à plusieurs nœuds.** Sur `kind`, un seul
  nœud masquait le coût de rattachement d'un disque à chaque étape. Si la durée mesurée au premier
  screening est dominée par lui, le réglage est une classe de stockage `ReadWriteMany` dans la
  surcouche — sans toucher à la base. À mesurer, pas à décider d'avance.
