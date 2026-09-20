# Plan — demenagement-gitlab-et-livraison

> **Pour un agent exécutant** : ce plan s'exécute tâche par tâche. Les cases `- [ ]` suivent
> l'avancement. Chaque groupe finit par un point de commit.

**But** : que le dépôt produise une version nommée, l'image correspondante dans le registre
interne, et une base de manifestes qu'une surcouche extérieure épingle — sur la forge GitLab de
l'employeur.

**Architecture** : deux demandes de fusion. La première ne fait que renommer, et se vérifie par le
banc local. La seconde porte la forge, la chaîne, la release, les décisions et la documentation.

**Outils** : GitLab CI, `releaser-pleaser`, `commitlint`, `mdschema`, `kustomize`, `argo lint`,
`kind`, `docker`.

## Plan de documentation

| Chemin | Quadrant | Destinataire | Geste |
| --- | --- | --- | --- |
| `docs/consommer-la-base.md` | Guide | Qui écrit une surcouche de déploiement dans un autre dépôt — aujourd'hui l'auteur, demain l'équipe plateforme | Créée |
| `docs/architecture/arc42.md` | Explication | L'auteur, et les agents qui écrivent les changes | Modifiée — journal des décisions, écarts refermés |
| `README.md` | — | Un visiteur du dépôt, sur le miroir public | Modifiée — adresse, phrase sur le nom du rôle, commandes de construction |
| `openspec/discovery.md` | — | Les agents qui proposent la prochaine story | Modifiée — story 1 coupée en deux, cible nommée, mention du quasi-doublon retirée |
| `docs/adr/SDR-0013`, `SDR-0014`, `SDR-0015` | Référence | Qui doit savoir ce qui est décidé sans lire le code | Verdict rendu ; deux créées |

Hors périmètre de ce change, et nommés pour qu'ils ne s'oublient pas : le `CLAUDE.md` de la racine
de l'espace de travail, qui décrit encore `docs/orchestrator/` comme un quasi-doublon vivant, et
`.nanopm/wiki/docs/roadmap.md`, qui parle d'un « compte robot de production » là où la première
cible est le staging. Le premier appartient à un autre dépôt ; la seconde se régénère par sa skill,
et ne s'édite pas à la main.

## ADR

- **Relus au frontmatter** : les douze fichiers de `docs/adr/`. Graphe de dépassement construit le
  2026-09-20 : tous les `supersedes:` sont vides, aucun ADR n'en dépasse un autre.
- **Relus au corps** : `SDR-0001` (un ADR `accepted` est gelé ; seul un `proposed` s'écrit
  librement) ; `SDR-0002` (prose en français, code et commentaires en anglais — il décide de la
  langue des trois ADR à écrire) ; `SDR-0006` (`commitlint` est l'outil déjà décidé, ce change ne
  le rechoisit pas) ; `SDR-0009` (`squash` — c'est lui qui déplace le contrôle du format vers le
  titre de la demande de fusion) ; `SDR-0010` (forge et intégration, que ce change dépasse) ;
  `SDR-0011` (livraison, que ce change dépasse) ; `SDR-0013` (frontend, `proposed`, dont le verdict
  se rend ici).
- **Créés** : `SDR-0014` (forge et intégration) et `SDR-0015` (livraison). Aucun fichier existant
  n'est modifié, sauf `SDR-0013` qui porte encore `proposed` et n'est donc pas gelé.

## 1. Établir les faits avant d'écrire

Ces cinq réponses décident du contenu des ADR et de la chaîne. Aucune ne se devine.

- [ ] 1.1 Vérifier que `releaser-pleaser` est utilisable sur l'instance GitLab de l'employeur —
  composant disponible dans son catalogue, ou image exécutable depuis ses exécuteurs. Indice à
  vérifier, pas une preuve : `package.json` épingle déjà `surdesrails` sur une branche nommée
  `releaser-pleaser--branches--main`, ce qui atteste que l'outil tourne en amont de la méthode,
  côté GitHub, et non qu'il est disponible ici. Réponse attendue : oui, ou non.
- [ ] 1.2 Vérifier si la protection de branche existe sur le projet GitLab (`main` protégée,
  chaîne rouge bloquante). C'est elle qui décide de `ci.gate` et qui ferme le contournement du
  finding 2 de `review.md`.
- [ ] 1.3 Vérifier si Node est présent sur les exécuteurs : un job jetable qui lance `node
  --version`. Si non, le repli est le binaire autonome de `mdschema`, épinglé par version et
  vérifié par empreinte.
- [ ] 1.4 Vérifier qu'un exécuteur sait construire une image de conteneur — gabarit d'entreprise,
  ou `docker`/`buildah` disponible. Tant que ce n'est pas établi, ne pas supprimer `.github/`.
- [ ] 1.5 Demander à l'équipe plateforme s'il existe un gabarit CI d'entreprise pour construire et
  pousser une image dans le registre interne. S'il existe, le job l'emploie.
- [ ] 1.6 Écrire les cinq réponses dans la section `## Questions ouvertes` de `proposal.md`, avec
  leur date, puis committer.

```bash
git add openspec/changes/demenagement-gitlab-et-livraison/proposal.md
git commit -m "docs: consigner les faits établis avant d'écrire les décisions"
```

## 2. Renommer `orchestrator` en `uske` — première demande de fusion

Le renommage ne touche que `deploy/`, trois textes de `uske/`, une valeur de `uske/cli.py` et une
phrase du `README.md`. Il ne touche **ni** `openspec/changes/archive/`, **ni** `CONTEXT.md`, où le
mot désigne l'histoire et non une ressource.

- [ ] 2.1 Créer la branche.

```bash
git switch -c chore/renommer-orchestrator-en-uske
```

- [ ] 2.2 Renommer dans `deploy/` — ressources, secrets, namespace, nom logique d'image, et le nom
  DNS du registre du banc, qui dérive du namespace.

```bash
grep -rl orchestrator deploy/ | xargs sed -i '' 's/orchestrator/uske/g'
```

Vérification : `grep -rc orchestrator deploy/ | grep -v ':0'` ne doit rien afficher.

- [ ] 2.3 Renommer les trois textes de `uske/`, qui décrivent le rôle et non une ressource.

```bash
sed -i '' 's/The orchestrator seed/The uske seed/' uske/__init__.py
sed -i '' 's/the orchestrator judges/uske judges/; s/The orchestrator has those digests/uske has those digests/' uske/gate.py
```

- [ ] 2.4 Renommer la raison écrite au journal pour un régime inconnu. **C'est une valeur, pas un
  commentaire** : elle apparaîtra dans les lignes du journal à venir. Aucun test ni aucune fixture
  ne l'affirme — vérifié le 2026-09-20 — et aucun journal réel n'existe encore, donc le geste est
  sans coût aujourd'hui et impossible plus tard sans raturer une ligne.

Dans `uske/cli.py:85`, remplacer `"orchestrator/unknown-track"` par `"uske/unknown-track"`.

- [ ] 2.5 Supprimer la phrase du `README.md:52` qui justifiait l'ancien nom (« In the manifests the
  role keeps its name — `orchestrator` — whatever tool fills it. »). Le rôle qu'elle nommait
  vivait dans `docs/orchestrator/`, supprimé le 2026-09-20.

- [ ] 2.6 Vérifier qu'il ne reste aucun résidu hors de l'histoire.

```bash
grep -rn orchestrator --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv \
  --exclude-dir=.serena --exclude-dir=.nanopm --exclude-dir=archive .
```

Attendu : seul `CONTEXT.md` ressort, où le mot cite `docs/orchestrator/` comme fait historique.

- [ ] 2.7 Lancer les tests.

```bash
uv run --with pyyaml python -m unittest discover tests -t .
```

Attendu : `OK`.

- [ ] 2.8 Rendre les manifestes du banc et les vérifier.

```bash
kubectl kustomize deploy/kind > /tmp/uske.yaml && argo lint --offline /tmp/uske.yaml
```

Attendu : aucune erreur, et `grep -c 'name: uske' /tmp/uske.yaml` rend un nombre non nul.

- [ ] 2.9 Rejouer le banc de bout en bout — c'est la seule vérification qui prouve que les secrets,
  le namespace et le nom DNS du registre se retrouvent.

```bash
deploy/kind/up.sh
```

Attendu : le script va au bout, puis un screening lancé à la main finit `Succeeded`. Ensuite
`deploy/kind/up.sh down`.

- [ ] 2.10 Committer, ouvrir la demande de fusion, la faire relire, la fusionner.

```bash
git add -A
git commit -m "chore: nommer uske ce que les manifestes appelaient orchestrator"
```

Titre de la demande de fusion : `chore: nommer uske ce que les manifestes appelaient orchestrator`.

## 3. Créer le projet GitLab et le miroir — gestes de la personne

Ces gestes demandent des identifiants ; ils ne s'automatisent pas ici.

- [ ] 3.1 Créer le projet `uske` sur le GitLab de l'employeur et y pousser `main`.
- [ ] 3.2 Configurer le miroir **poussé** vers `github.com/trivoallan/uske`, et vérifier qu'un
  commit poussé sur GitLab arrive sur GitHub.
- [ ] 3.3 Poser les variables CI/CD, **masquées et protégées** : hôte du registre, projet du
  registre, index des paquets, identifiants d'écriture du compte robot. Aucune ne doit figurer dans
  un fichier suivi — le dépôt est miroité en clair (finding 6 de `review.md`).
- [ ] 3.4 Protéger le motif de tag `v*`, pour que le job d'image ne s'exécute que dans un contexte
  protégé.
- [ ] 3.5 Basculer `origin` sur GitLab, et garder GitHub sous un autre nom.

```bash
git remote rename origin github
git remote add origin <url-gitlab>
git remote -v
```

## 4. Écrire la chaîne d'intégration — seconde demande de fusion

- [ ] 4.1 Créer la branche.

```bash
git switch -c ci/gitlab-et-livraison
```

- [ ] 4.2 Créer `.gitlab-ci.yml` avec six jobs. Les quatre premiers s'exécutent sur demande de
  fusion, le cinquième sur `main`, le sixième sur tag `v*`.

1. `test` — `python3 -m venv /tmp/venv && /tmp/venv/bin/pip install --quiet pyyaml==6.0.2 &&
   /tmp/venv/bin/python -m unittest discover tests -t .`
2. `lint-manifests` — `kubectl kustomize deploy/kind` et `kubectl kustomize deploy/example`, chacun
   passé à `argo lint --offline`. L'installation d'`argo` reprend la recette de
   `.github/workflows/test.yaml` : téléchargement, empreinte `sha256sum -c`, `gunzip`.
3. `adr-schema` — `cd docs/adr && npx @jackchuka/mdschema@0.15.1 check '*.md'`. Attendu : aucun
   fichier nommé. Si la tâche 1.3 a dit que Node manque, prendre à la place le binaire autonome des
   *releases* de `mdschema`, épinglé et vérifié par empreinte. **Dire dans le commentaire du job
   lequel des deux chemins a été essayé** (finding 10 de `review.md`).
4. `commit-format` — `commitlint` sur le **titre de la demande de fusion**, jamais sur les commits
   de la branche : sous `squash` (`SDR-0009`), c'est ce titre qui devient le message dont la
   version se déduit. Le job ne s'exécute que dans le contexte d'une demande de fusion.
5. `release` — `releaser-pleaser`, qui ouvre la demande de fusion de release et pose le tag à sa
   fusion. Si la tâche 1.1 a répondu non, ce job n'existe pas et le tag se pose à la main.
6. `image` — construit `Dockerfile` et pousse `$HARBOR_HOST/$HARBOR_PROJECT/uske:$CI_COMMIT_TAG`.
   Emploie le gabarit d'entreprise si la tâche 1.5 en a trouvé un.

Aucun job ne fait `echo` d'une variable (finding 6 de `review.md`).

- [ ] 4.3 Ajouter la configuration de `commitlint` — Conventional Commits, portées libres
  (`SDR-0006` déclare `scopes: []`), et l'entrée qui la lance dans `package.json`.

- [ ] 4.4 Supprimer `.github/`, **seulement si la tâche 1.4 a établi qu'un exécuteur construit une
  image** (finding 8 de `review.md`).

```bash
git rm -r .github
```

- [ ] 4.5 Vérifier qu'aucun nom propre à l'employeur n'est entré dans un fichier suivi. Le dépôt
  est miroité en clair : ce contrôle est une relecture, aucun outil ne le tient.

```bash
git ls-files -z | xargs -0 grep -nIF -e '<hôte-du-registre-interne>' -e '<projet-interne>' -e '<hôte-gitlab-interne>'
```

Attendu : aucune ligne. Remplacer les trois marques par les valeurs réelles au moment de lancer la
commande — elles ne s'écrivent pas dans ce fichier, qui est lui-même suivi.

- [ ] 4.6 Committer.

```bash
git add -A && git commit -m "ci: poser la chaîne GitLab, la release et la vérification des décisions"
```

## 5. Rendre la base consommable de l'extérieur

- [ ] 5.1 Créer `deploy/example/kustomization.yaml` : une surcouche aux valeurs factices qui
  référence `../base` et **emploie les trois chemins, tous les trois** (finding 4 de `review.md`) —
  `images:` pour les **quatre** images (`git`, `uske`, `regis`, `knock`),
  `/spec/arguments/parameters` remplacé en bloc (dépôt, politiques, playbooks), et
  `/spec/podSpecPatch` pour `HTTPS_PROXY`, `NO_PROXY`, `SSL_CERT_FILE` et le montage d'une autorité
  de certification. Aucun patch à index.

- [ ] 5.2 Vérifier que la surcouche rend et passe le linter, et qu'elle prouve quelque chose.

```bash
kubectl kustomize deploy/example > /tmp/example.yaml && argo lint --offline /tmp/example.yaml
grep -c "HTTPS_PROXY" /tmp/example.yaml
```

Attendu : le linter ne signale rien, et le `grep` rend un nombre non nul — sinon le correctif de
spécification de pod n'a pas été appliqué, et le contrôle serait décoratif.

- [ ] 5.3 Ajouter au `Dockerfile` trois `ARG` avec leurs valeurs publiques par défaut : l'image
  `cosign`, l'image `python`, l'index des paquets.

- [ ] 5.4 Vérifier que la construction marche encore sans rien désigner.

```bash
docker build -q --provenance=false -t uske:dev .
```

Attendu : une empreinte d'image, sans erreur.

- [ ] 5.5 Committer.

```bash
git add -A && git commit -m "feat: rendre la base consommable depuis un autre dépôt"
```

## 6. Rendre les décisions

- [ ] 6.1 Statuer `SDR-0013` (frontend) : `status: rejected`, `date: 2026-09-20`, `authors`
  renseigné, **le bloc `traits:` supprimé en entier**. Le motif dit ce qui en tient lieu : `uske`
  ne sert aucune interface — une console est l'anti-persona déclaré —, et ses trois personas lisent
  du texte, la ligne de commande et le journal. Supprimer le mode d'emploi en tête, reconnaissable
  à sa première phrase.

- [ ] 6.2 Écrire `docs/adr/SDR-0014-forge-and-ci.md` : `supersedes: ["SDR-0010"]`,
  `forge.host: gitlab`, `ci.tool: gitlab-ci`, `ci.gate` selon la réponse de la tâche 1.2. Le corps
  dit pourquoi `SDR-0010` est revisité — la forge a changé —, nomme la vérification des ADR comme
  lancée par la chaîne, et écrit la réserve des findings 1 et 2 de `review.md` : sans protection de
  branche, un rouge n'empêche rien et une poussée directe sur `main` échappe au contrôle du format.
  **Ne pas toucher au fichier de `SDR-0010`.**

- [ ] 6.3 Écrire `docs/adr/SDR-0015-delivery.md` : `supersedes: ["SDR-0011"]`, `release.tool` selon
  la réponse de la tâche 1.1, et `deploy.environments` portant `staging` puis `production`, tous
  deux au déclencheur `manuel`. Le corps dit pourquoi `manuel` plutôt que la paire proposée : la
  mise en service est un changement de version épinglée dans le dépôt GitOps, fait à la main, et
  écrire `merge` ou `tag` affirmerait une automatisation qui n'existe pas.

- [ ] 6.4 Vérifier les décisions.

```bash
( cd docs/adr && npx @jackchuka/mdschema@0.15.1 check '*.md' )
```

Attendu : aucun fichier nommé. Si `npx` échoue sur un lien de binaire — défaut connu de ce poste —,
prendre celui de Homebrew ou le binaire autonome.

- [ ] 6.5 Mettre `docs/architecture/arc42.md` à jour : les trois ADR au *Decision Log* avec leur
  objectif qualité servi ; `DEBT-03`, `DEBT-05` et `DEBT-06` marqués *Closed* — en écrivant pour
  `DEBT-06` ce qui est réellement acquis, la vérification lancée, et ce qui ne l'est pas tant que
  la chaîne n'est pas bloquante ; et une ligne pour l'écart candidat du finding 7 de `review.md` :
  l'image de `uske` est construite et poussée sans signature ni attestation, alors que `knock`
  atteste tout ce qu'il place.

- [ ] 6.6 Committer.

```bash
git add -A && git commit -m "docs: statuer la forge, la livraison et la question du front"
```

## 7. Écrire la documentation

- [ ] 7.1 Créer `docs/consommer-la-base.md` — un guide pour qui écrit une surcouche dans un autre
  dépôt. Il dit : les trois chemins et rien d'autre ; les **quatre** images à épingler, `git`
  compris ; les quatre noms de secrets attendus et ce que chacun porte ; comment épingler la base
  par version ; et que `deploy/example` est le modèle à copier.

- [ ] 7.2 Mettre `README.md` à jour : l'adresse du dépôt, la construction de l'image avec ses
  `ARG`, et le renvoi vers le nouveau guide.

- [ ] 7.3 Mettre `openspec/discovery.md` à jour : la story 1 est coupée en deux — ce change, puis
  le premier screening déployé ; la cible réelle est nommée (le staging de l'employeur) ; la
  question ouverte « quelle est la cible réelle ? » reçoit sa réponse ; la mention du quasi-doublon
  `docs/orchestrator/` disparaît.

- [ ] 7.4 Committer.

```bash
git add -A && git commit -m "docs: expliquer comment consommer la base depuis un autre dépôt"
```

## 8. Livrer la première version

- [ ] 8.1 Porter `pyproject.toml` de `version = "0.0.0"` à `version = "0.1.0"`. Si `releaser-pleaser`
  est en place, c'est lui qui écrit cette ligne dans sa demande de fusion de release ; ne pas la
  poser à la main dans ce cas.

- [ ] 8.2 Valider le change.

```bash
openspec validate demenagement-gitlab-et-livraison --type change --strict
```

Attendu : aucune erreur.

- [ ] 8.3 Ouvrir la seconde demande de fusion, titre
  `ci: déménager sur GitLab et livrer une version épinglable`, vérifier que les quatre jobs de
  demande de fusion sont au vert, puis fusionner.

- [ ] 8.4 Poser le tag et vérifier l'image.

```bash
git tag v0.1.0 && git push origin v0.1.0
```

Attendu : le job `image` finit vert, et `regctl image digest $HARBOR_HOST/$HARBOR_PROJECT/uske:v0.1.0`
rend une empreinte.

- [ ] 8.5 Vérifier depuis le cluster de staging qu'un pod jetable tire cette image. C'est le
  premier des faits que le jalon suivant exige, et il se vérifie ici tant que le contexte est frais.

- [ ] 8.6 Vérifier que le miroir a bien reçu le tag.

```bash
git ls-remote --tags github | grep v0.1.0
```
