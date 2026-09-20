# Proposition — `uske` déménage sur le GitLab de l'employeur et livre une version qu'une surcouche de déploiement peut épingler

## Why

Rien n'est déployé nulle part, et le premier screening réel est dû le 2026-10-31. Il tournera sur
le staging de l'employeur, dont les manifestes vivent dans un dépôt GitOps sur une forge GitLab et
dont le cluster ne tire que du Harbor interne. Ce change pose ce qui manque en amont : une forge qui
fabrique une version nommée, une image dans le registre interne, et une base de manifestes qu'une
surcouche extérieure peut épingler sans connaître l'intérieur de `deploy/base`.

**Objectif qualité.** Ce change sert l'**opérabilité** (rang 3 de `docs/architecture/arc42.md`,
§1) : une version nommée est ce qui permet à une seule personne de dire ce qui tourne, de le
rejouer et d'y revenir. Il sert aussi la **contestabilité** (rang 2) par ricochet, en branchant la
vérification des ADR et le format des titres de fusion. Il n'arbitre aucun conflit entre objectifs ;
il ne touche ni au jugement, ni au placement, ni au journal.

## Détection

Conduite deux fois : la première au début du cadrage, la seconde après que le dépôt a bougé sous
nos pieds — `HEAD` est passé de `2bf52c0` à `3e2a6fe` pendant la session, et le commit `06faae9` a
ajouté un ADR hérité.

- `.nanopm/wiki/docs/product.md` est présent : rien à proposer.
- `docs/adr/SDR-0013-frontend.md` est en `status: proposed` : les **verdicts** sont proposés, et
  acceptés le 2026-09-20. Le verdict se conduit dans ce change, hors du répertoire du change.
- `docs/architecture/arc42.md` existe : rien à proposer.

## Passes de cadrage

Le cadrage a été conduit par `superpowers:brainstorming` dans la session du 2026-09-20, **en prose
et à une question par envoi**, et non par passes groupées : la borne du cadrage n'a pas été tenue
telle que le schéma la prescrit. Le compte réel, consigné ici faute de mieux : sept envois de
question (staging, existant, briques, dépôt des manifestes, sortie réseau, registres sources,
forge), puis quatre envois de section de conception, puis une passe groupée après le déplacement du
dépôt (verdict de `SDR-0013`, `DEBT-06`, `DEBT-03`). La découverte n'a consommé aucune passe.

## What Changes

- **Forge** — `uske` déménage sur le GitLab de l'employeur. `origin` change ; le dépôt GitHub
  `trivoallan/uske` devient un miroir poussé, qui garde une adresse publique citable ;
  `.github/workflows/` est supprimé, pour qu'une seule CI s'exécute.
- **Décisions** — trois écritures dans `docs/adr/`, sans modifier aucun fichier existant. La
  numérotation suit la méthode, **trous compris** : `SDR-0012` n'existe pas en amont, et le dépôt
  ne renumérote pas (`docs/architecture/arc42.md`, §9).
  - `SDR-0013` (frontend, hérité) reçoit le verdict **`rejected`** : `uske` ne sert aucune
    interface — une console est l'anti-persona déclaré. Le bloc `traits:` disparaît en entier, et
    le motif dit ce qui en tient lieu : la ligne de commande et le journal.
  - `SDR-0014` dépasse `SDR-0010` : `forge.host: gitlab`, `ci.tool: gitlab-ci`, `ci.gate`
    re-statué — la protection de branche peut exister sur cette instance —, et la vérification des
    ADR nommée comme lancée par la chaîne.
  - `SDR-0015` dépasse `SDR-0011` : `release.tool`, et `deploy.environments` qui nomme enfin
    `staging` puis `production`, tous deux au déclencheur `manuel` — la mise en service est un
    changement de version épinglée dans le dépôt GitOps, fait à la main.
- **Intégration** — `.gitlab-ci.yml` porte six jobs : les tests ; le lint des manifestes
  (`kustomize build` puis `argo lint --offline` sur `deploy/kind` **et** `deploy/example`) ; la
  vérification des ADR, qui referme `DEBT-06` ; le lint du titre de la demande de fusion, qui
  referme `DEBT-03` ; la release sur `main`, qui referme `DEBT-05` ; et la construction de l'image
  dans le Harbor interne sur tag `v*`.
- **BREAKING — renommage `orchestrator` → `uske`** dans `deploy/` : nom logique de l'image,
  `CronWorkflow`, `WorkflowTemplate`, `ServiceAccount`, `Role`, `RoleBinding`, volume de
  résultats, les quatre secrets et le namespace du banc. Ces noms sont le contrat de la base avec
  une surcouche ; le rôle qu'ils nommaient n'existe plus depuis la suppression de
  `docs/orchestrator/`. Après un premier déploiement, le renommage coûterait de recréer les secrets
  et le volume du journal.
- **`deploy/example/`** — une surcouche factice, seul fichier neuf des manifestes. Elle n'emploie
  que les trois chemins stables — `images:`, `/spec/arguments/parameters`, `/spec/podSpecPatch` —
  et jamais un patch à index. La CI la construit : c'est ce qui garantit que la base reste
  consommable de l'extérieur.
- **`Dockerfile`** — des `ARG` pour les images de base et l'index pip, afin que la CI passe par le
  registre et le miroir internes. Les valeurs par défaut restent publiques.
- **Version** — `pyproject.toml` passe de `0.0.0` à `0.1.0`, et le tag `v0.1.0` est posé.
- **Écarts refermés** — `DEBT-03`, `DEBT-05` et `DEBT-06` passent *Closed* dans
  `docs/architecture/arc42.md`, et le journal des décisions y accueille les trois ADR.
- **`uske/*.py` ne change presque pas** : trois textes de documentation qui citent l'ancien nom, et
  **une valeur** — la raison `orchestrator/unknown-track`, écrite au journal quand le régime est
  inconnu, devient `uske/unknown-track`. C'est le seul changement observable du produit ; il est
  sans coût aujourd'hui, aucun journal réel n'existant, et impossible plus tard sans raturer une
  ligne. Aucune autre logique ne bouge : ni jugement, ni placement, ni écriture du journal.

## Alternatives écartées

- **Plateforme d'abord** — installer Argo Workflows aux standards de l'entreprise (fédération
  d'identité, archive PostgreSQL sur Azure via les modules Terraform maison) avant de déployer
  `uske` : écartée parce qu'elle met les deux écueils annoncés sur le chemin critique du premier
  screening, dont l'échéance dépendrait alors de Terraform et de l'identité.
- **Banc kind déplacé** — faire tourner le banc local sur un poste du réseau de l'employeur, pointé
  sur le Harbor de staging : écartée comme route complète, parce qu'elle ne dit rien d'ArgoCD, d'un
  Argo Workflows réel ni de la planification, et ne satisfait donc pas le critère « un screening
  déclenché par le `CronWorkflow` ». Elle reste utilisable comme vérification préalable.
- **Garder GitHub comme amont et ne miroiter que vers GitLab** — écartée : `releaser-pleaser` ne
  peut pas tourner sur un miroir sans y écrire des commits que l'amont n'a pas, et le miroir
  divergerait.
- **Mettre la surcouche de staging dans ce dépôt** (`deploy/staging`) — écartée : les noms internes
  de l'employeur entreraient dans l'historique d'un dépôt que la vision veut ouvrir, et ArgoCD
  devrait atteindre GitHub, ce que le cluster ne fait pas.
- **Ne rien faire, et déployer depuis `main` sans version** — écartée : une surcouche a besoin d'un
  point fixe à épingler, et `SDR-0011` a déjà statué qu'une version se fabrique.
- **Repousser le renommage après le premier déploiement** — écartée : ces noms sont le contrat que
  la surcouche épingle et sous lesquels les secrets sont créés ; après coup, il faut recréer les
  secrets et le volume du journal.
- **Ajouter des crochets à `deploy/base`** (un `envFrom` optionnel, un montage de CA à chemin fixe)
  pour rendre la base consommable : écartée comme inutile — `images:`,
  `/spec/arguments/parameters` et `/spec/podSpecPatch` suffisent et ne dépendent d'aucun index.
- **Refuser les verdicts, et laisser `SDR-0013` en `proposed`** — écartée le 2026-09-20 : la
  réponse est connue et tient en quelques lignes ; la laisser ouverte ferait revenir la question à
  chaque change.
- **Dire la vérification des ADR manuelle dans `SDR-0014`** — écartée : `DEBT-06` resterait ouvert,
  et une décision laissée vide continuerait de passer. Le coût retenu à la place est une
  dépendance à Node sur l'exécuteur.
- **Laisser `DEBT-03` ouvert, ou reporter toute la release à un change à part** — écartées : la
  version se déduit des messages, et sous `squash` c'est le titre de la demande de fusion ;
  installer la release sans garde-fou reviendrait à fabriquer des versions fausses, puis à les
  corriger à la main.

## Conception

`design` est dû : dépendance externe nouvelle et complexité de migration — la forge, la chaîne
d'intégration et l'outil de release changent en même temps, et le renommage traverse tous les
manifestes.

## Revue

`review` est due : la surface d'attaque bouge — une chaîne d'intégration reçoit des identifiants
d'écriture sur le registre interne et publie une image que le cluster exécutera — et le
déménagement de forge est une décision coûteuse à défaire.

## Capabilities

### New Capabilities

- `versioned-delivery`: ce que le dépôt doit produire pour qu'un déploiement soit possible — une
  version nommée, une image dans le registre à partir de cette version, et une base de manifestes
  qu'une surcouche extérieure épingle et paramètre sans patch à index ni connaissance de
  l'intérieur de la base.

### Modified Capabilities

- `repository-method`: deux exigences s'ajoutent, sans toucher aux existantes — la vérification
  des ADR est lancée par la chaîne d'intégration et non par une personne qui y pense (`DEBT-06`),
  et le format dont la version se déduit est tenu là où `squash` le laisse, sur le titre de la
  demande de fusion (`DEBT-03`).

## Impact

- **Fichiers** : `.gitlab-ci.yml` (nouveau) ; `.github/workflows/` (supprimé) ;
  `deploy/example/kustomization.yaml` (nouveau) ; `deploy/base/*` et `deploy/kind/*` (renommage) ;
  `Dockerfile` (`ARG`) ; `pyproject.toml` (version) ; `docs/adr/SDR-0013` (verdict), `SDR-0014` et
  `SDR-0015` (nouveaux) ; `docs/architecture/arc42.md` (journal des décisions, écarts refermés) ;
  `README.md` (adresse, phrase sur le nom du rôle) ; `openspec/discovery.md` et
  `.nanopm/wiki/docs/roadmap.md` (mentions périmées).
- **Code, interfaces, dépendances** : aucun changement de comportement de `uske`. Dépendances
  nouvelles du dépôt, pas du produit : `releaser-pleaser`, `commitlint`, la vérification des ADR
  et la chaîne GitLab.
- **Surface d'attaque** : une chaîne d'intégration avec droit d'écriture sur un projet du registre
  interne, et l'image publiée. Aucun secret dans un fichier suivi : les noms propres à l'employeur
  passent par des variables CI/CD, puisque le dépôt est miroité en clair.
- **Hors de ce change** : l'installation d'Argo Workflows, la surcouche `staging`, les secrets et le
  premier screening, qui vivent dans le dépôt GitOps de l'employeur ; la fédération d'identité et
  l'archive PostgreSQL ; la réparation des renvois vers `orchestrator/` dans le dépôt `docs/`.
- **Branche** : `github-flow`, `squash`, préfixe `ci` ou `chore` selon `SDR-0009`.

## Questions ouvertes

- **`releaser-pleaser` est-il disponible sur cette instance GitLab ?** `SDR-0011` tenait le
  composant pour mirroré nulle part. S'il ne l'est pas, `SDR-0015` écrit `release.tool: manuel` et
  le tag se pose à la main ; `DEBT-05` reste alors ouvert, et l'ADR le dit.
- **La protection de branche existe-t-elle sur le projet GitLab ?** Elle décide de `ci.gate` dans
  `SDR-0014` — `bloquante` si elle existe, `informative` sinon, comme aujourd'hui.
- **Node est-il disponible sur les exécuteurs ?** La vérification des ADR en dépend. La mémoire du
  dépôt relève un lien de binaire `npx` capricieux sur le poste de l'auteur ; sur un exécuteur, le
  binaire autonome de l'outil est le repli, et c'est lui que la conception retient si Node manque.
- **L'entreprise fournit-elle un gabarit CI pour construire une image ?** Si oui, le job
  l'emploie ; sinon, il construit avec l'outil disponible sur ses exécuteurs.
- **ArgoCD a-t-il le droit de poser des CRD sur le cluster de staging ?** Hors de ce change, mais
  sur le chemin critique du suivant : si non, l'installation d'Argo Workflows devient une demande à
  l'équipe plateforme, à envoyer tôt.
- **`SDR-0013` nomme le portail interne de l'employeur** (`dev.sncf`) dans un dépôt que la vision
  veut ouvrir. Le verdict `rejected` retire le bloc `traits:`, pas la prose héritée. Faut-il
  élaguer ces renvois avant l'ouverture ? La question n'est pas tranchée ici ; elle ne se pose
  qu'au moment d'ouvrir le dépôt.
