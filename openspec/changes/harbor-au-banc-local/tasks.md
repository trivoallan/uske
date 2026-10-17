# Plan — harbor-au-banc-local

> **Pour un agent exécutant** : les cases `- [ ]` suivent l'avancement, et chaque groupe finit par
> un point de commit.
>
> **Ordre** : ce plan s'exécute **après** `demenagement-gitlab-et-livraison`. Il emploie les noms
> d'après le renommage — namespace `uske`, secrets `uske-harbor` et `uske-knock`. Si le renommage
> n'a pas encore été fusionné, s'arrêter et le faire d'abord : les deux chantiers réécrivent
> `deploy/kind/up.sh`.

**But** : que `deploy/kind/up.sh harbor` monte un vrai Harbor à l'adresse de Zot, et que `uske
census` rende un rapport contre son API — sans rien changer au banc par défaut.

**Architecture** : un argument positionnel de plus dans `up.sh`, qui branche trois différences —
ce qui est installé, les identités créées, le contenu des secrets.

**Outils** : `helm` (Harbor 1.19.2), `kind`, `kubectl`, `jq`, `curl`.

## Plan de documentation

| Chemin | Quadrant | Destinataire | Geste |
| --- | --- | --- | --- |
| `README.md` | — | Un visiteur du dépôt | Modifiée — la commande de la variante, à côté de celles du banc |
| `deploy/kind/up.sh` (en-tête) | — | Qui monte le banc, et les agents | Modifiée — l'en-tête liste les modes du script ; `harbor` s'y ajoute |
Le document de design autonome écrit pendant le cadrage a été supprimé avant la demande de fusion
de ce change : son contenu est devenu `design.md`, et deux copies auraient divergé.

## ADR

- **Relus au frontmatter** : les douze fichiers de `docs/adr/`, plus `SDR-0014` et `SDR-0015` s'ils
  sont déjà écrits par le change précédent. Graphe de dépassement au 2026-09-20 : tous les
  `supersedes:` vides.
- **Relus au corps** : `SDR-0002` (la prose de ce change est en français, le script et ses
  commentaires en anglais) ; `SDR-0008` (racine de la documentation, pour la page supprimée) ;
  `SDR-0009` (branche et titre de la demande de fusion).
- **Créés** : aucun. Un banc de développement local n'est pas un engagement durable
  d'architecture : il ne contraint aucun change à venir, et rien ici ne s'écarte d'une décision en
  vigueur.

## 1. Monter Harbor à l'adresse de Zot

- [ ] 1.1 Créer la branche.

```bash
git switch -c feat/harbor-au-banc-local
```

- [ ] 1.2 Ajouter le dépôt Helm et épingler la version, dans `up.sh`, sous le mode `harbor`.

```bash
helm repo add harbor https://helm.goharbor.io
helm repo update harbor
```

- [ ] 1.3 Écrire l'installation dans `up.sh`, avec les valeurs qui donnent à Harbor l'adresse de
  Zot. `$NS` vaut `uske`, et `$REGISTRY` reste `registry.$NS.svc.cluster.local:5000`.

```bash
helm upgrade --install harbor harbor/harbor --version 1.19.2 --namespace "$NS" --wait \
  --set expose.type=clusterIP \
  --set expose.clusterIP.name=registry \
  --set expose.clusterIP.ports.httpsPort=5000 \
  --set expose.tls.certSource=secret \
  --set expose.tls.secret.secretName=registry-tls \
  --set externalURL="https://$REGISTRY" \
  --set persistence.enabled=false \
  --set trivy.enabled=false \
  --set harborAdminPassword="$HARBOR_ADMIN_PASSWORD"
```

- [ ] 1.4 En mode `harbor`, retirer Zot du rendu kustomize. Le rendu actuel passe déjà par un
  tube (`kubectl kustomize "$HERE" | sed … | kubectl apply`) ; la variante applique le même rendu
  privé de `registry.yaml`, sans introduire de seconde surcouche.

- [ ] 1.5 Attendre que le cœur réponde, comme `up.sh` attend déjà le déploiement de Zot.

```bash
kubectl -n "$NS" rollout status deploy/harbor-core --timeout=300s
```

- [ ] 1.6 Vérifier que le service porte le nom et le port attendus.

```bash
kubectl -n "$NS" get svc registry -o jsonpath='{.spec.ports[*].port}{"\n"}'
```

Attendu : la liste contient `5000`.

- [ ] 1.7 Vérifier que le registre répond en TLS sous le certificat du banc, depuis un pod jetable.

```bash
kubectl -n "$NS" run probe --rm -i --restart=Never --image=curlimages/curl -- \
  curl -sf --cacert /dev/null -o /dev/null -w '%{http_code}\n' "https://$REGISTRY/v2/"
```

Attendu : un code HTTP, `401` ou `200` — les deux prouvent que le point d'entrée du registre
répond. Un échec TLS signale un SAN qui ne couvre pas l'adresse.

- [ ] 1.8 Committer.

```bash
git add -A && git commit -m "feat: monter Harbor à l'adresse de Zot dans le banc"
```

## 2. Les projets et les identités

- [ ] 2.1 Créer les sept projets, **publics**, par l'API, avec `admin`. La liste se dérive des
  politiques du banc plutôt que de se recopier.

```bash
projects="mirror $(grep -h 'project:' "$HERE"/policies/*.yaml | awk '{print $2}' | sort -u | tr '\n' ' ')"
for p in $projects; do
  curl -sf -u "admin:$HARBOR_ADMIN_PASSWORD" -X POST "https://$REGISTRY/api/v2.0/projects" \
    -H 'Content-Type: application/json' \
    -d "{\"project_name\":\"$p\",\"public\":true}" || true
done
```

Attendu : `curl -sf -u admin:… "https://$REGISTRY/api/v2.0/projects" | jq length` rend **7**.

- [ ] 2.2 Créer `robot$uske-read`, de portée système, en lecture sur tous les projets, par
  `POST /api/v2.0/robots`. Conserver le secret qu'Harbor rend à la création : il n'est affiché
  qu'une fois.

- [ ] 2.3 Créer `robot$uske-knock`, de portée système, en `push` et `pull` sur les six projets de
  destination et en `pull` sur `mirror`, par le même point d'entrée.

- [ ] 2.4 **Mesurer ce qui n'est pas su** : un robot de portée système énumère-t-il les projets ?
  C'est ce dont `census` a besoin en premier.

```bash
curl -sf -u "$READ_ROBOT_NAME:$READ_ROBOT_SECRET" "https://$REGISTRY/api/v2.0/projects" | jq length
```

Attendu : **7**. Si la commande rend `0`, une erreur d'autorisation, ou moins que sept, appliquer
le repli décidé d'avance : `census` reçoit `admin` dans le banc, et un commentaire d'`up.sh` dit
que la séparation lecture/écriture n'y est pas éprouvée pour l'API. Ne pas inventer un troisième
chemin sans en parler.

- [ ] 2.5 Committer.

```bash
git add -A && git commit -m "feat: créer les projets et les deux robots du banc Harbor"
```

## 3. Les secrets, et `census` qui tourne

- [ ] 3.1 En mode `harbor`, compléter `uske-harbor` : `HARBOR_URL` (`https://$REGISTRY`),
  `HARBOR_USER` et `HARBOR_PASSWORD` (le robot en lecture, ou `admin` selon la tâche 2.4), en
  gardant `HARBOR_HOST` (`$REGISTRY`, sans schéma) et `SSL_CERT_FILE`.

- [ ] 3.2 En mode `harbor`, ajouter `username` et `password` à `KNOCK_REGISTRIES`, avec le robot
  d'écriture. Les deux champs vont par paire.

```bash
--from-literal=KNOCK_REGISTRIES="{\"local\": {\"host\": \"$REGISTRY\", \"username\": \"$KNOCK_ROBOT_NAME\", \"password\": \"$KNOCK_ROBOT_SECRET\"}}"
```

- [ ] 3.3 Sauter, en mode `harbor`, le pod `trust-key` qui pousse la clé publique dans
  `/v2/_zot/ext/cosign` : l'extension est propre à Zot.

- [ ] 3.4 Amorcer `mirror` avec `crane`, comme aujourd'hui, mais authentifié — le pod reçoit les
  identifiants d'`admin` ou du robot d'écriture, puisque `mirror` n'accepte pas la poussée
  anonyme.

Attendu : la sortie du pod liste `copied mirror/redis`, `copied mirror/nginx`, et les cinq autres.

- [ ] 3.5 Ajouter à la fin d'`up.sh`, en mode `harbor`, la commande qui lance le recensement — il
  n'est dans aucun gabarit du workflow.

```bash
kubectl -n uske run census --rm -i --restart=Never --image=uske:dev \
  --overrides='{"spec":{"containers":[{"name":"c","image":"uske:dev","imagePullPolicy":"Never",
  "args":["census"],"envFrom":[{"secretRef":{"name":"uske-harbor"}}]}]}}'
```

- [ ] 3.6 Lancer un screening, puis le recensement.

```bash
kubectl -n uske create -f deploy/kind/screening.yaml && kubectl -n uske get wf -w
```

Attendu : le workflow finit `Succeeded`, puis la commande de la tâche 3.5 rend un rapport JSON dont
le total d'artefacts est non nul — c'est la première fois que `census` voit une vraie API.

- [ ] 3.7 Vérifier les signatures de l'image placée, sans changer le script.

```bash
deploy/kind/attestations.sh 2.0
```

Attendu : les trois vérifications passent, comme avec Zot.

- [ ] 3.8 Committer.

```bash
git add -A && git commit -m "feat: authentifier le banc Harbor et y lancer le recensement"
```

## 4. Le défaut reste intact

- [ ] 4.1 Détruire le banc, puis le remonter **sans argument**.

```bash
deploy/kind/up.sh down && deploy/kind/up.sh
```

Attendu : Zot est installé, aucun composant Harbor n'apparaît
(`kubectl -n uske get pods` n'affiche rien qui commence par `harbor-`), et le montage retrouve son
temps d'avant.

- [ ] 4.2 Lancer un screening sur ce banc par défaut et vérifier les signatures.

```bash
kubectl -n uske create -f deploy/kind/screening.yaml && kubectl -n uske get wf -w
deploy/kind/attestations.sh 2.0
```

Attendu : `Succeeded`, et les trois vérifications passent.

- [ ] 4.3 Vérifier que `census` échoue proprement sur le banc par défaut, et que l'échec se lise
  comme l'absence d'API Harbor plutôt que comme un défaut de la sous-commande.

- [ ] 4.4 Rendre et vérifier les manifestes, comme le fait la chaîne d'intégration.

```bash
kubectl kustomize deploy/kind > /tmp/uske.yaml && argo lint --offline /tmp/uske.yaml
kubectl kustomize deploy/example > /tmp/example.yaml && argo lint --offline /tmp/example.yaml
```

Attendu : aucune erreur sur les deux.

- [ ] 4.5 Committer.

```bash
git add -A && git commit -m "test: constater que le banc par défaut n'a pas bougé"
```

## 5. La documentation, et la copie en trop

- [ ] 5.1 Mettre l'en-tête d'`up.sh` à jour : il liste les modes du script, `harbor` s'y ajoute,
  avec une ligne sur son coût — six composants, quelques minutes — et sur ce qu'il apporte, une
  vraie API pour le recensement.

- [ ] 5.2 Mettre `README.md` à jour : la commande de la variante à côté de celles du banc, et une
  phrase qui dit pourquoi elle existe.

- [ ] 5.3 Valider le change.

```bash
openspec validate harbor-au-banc-local --type change --strict
```

Attendu : aucune erreur.

- [ ] 5.4 Committer, ouvrir la demande de fusion sous le titre
  `feat: monter un vrai Harbor dans le banc local, en option`, et la fusionner une fois la chaîne
  au vert.

```bash
git add -A && git commit -m "docs: dire ce que la variante Harbor apporte et ce qu'elle coûte"
```
