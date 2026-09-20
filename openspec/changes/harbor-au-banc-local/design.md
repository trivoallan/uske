# Conception — un Harbor au banc local

**Sections arc42 touchées** : aucune. Le banc local n'est décrit dans aucune section d'arc42
aujourd'hui — §7 *Deployment View* est resté au gabarit —, et ce change ne l'y fait pas entrer :
un banc n'est pas une frontière de déploiement du produit.

## Context

Le banc `deploy/kind` monte **Zot** en tenant-lieu de Harbor : un pod, TLS par une autorité
auto-signée fabriquée par `up.sh`, son UI, et la vérification cosign par une extension propre à
Zot. Il sert le protocole de registre, ce qui suffit à `regis` et à `knock`.

`census` est le seul code de `uske` qui parle à l'API v2.0 de Harbor, par trois points d'entrée :
`/projects`, `/projects/{p}/repositories`, et
`/projects/{p}/repositories/{r}/artifacts?q=type=IMAGE&with_tag=true`. Zot ne l'implémente pas, et
`tests/test_census.py` emploie un `FakeHarbor`. La sous-commande n'a donc jamais rencontré l'API
qu'elle appelle.

**Un second écart, trouvé en concevant.** `census` exige `HARBOR_URL`, `HARBOR_USER` et
`HARBOR_PASSWORD` (`uske/cli.py:195`) ; le secret du banc ne pose que `HARBOR_HOST` et
`SSL_CERT_FILE`. La commande échouerait avant d'atteindre un registre, Harbor ou pas.

**Décisions en vigueur qui contraignent.** Graphe de dépassement construit le 2026-09-20 : tous les
`supersedes:` sont vides. `SDR-0002` fixe la langue (prose en français, code et commentaires en
anglais) ; `SDR-0008` la racine de la documentation ; `SDR-0009` le modèle de branches. Aucune ne
statue sur l'outillage local, et ce change n'en dépasse aucune : un banc de développement n'est pas
un engagement d'architecture.

## Goals / Non-Goals

**Goals**

- Que `census` s'exerce contre une vraie API Harbor.
- Que le banc porte la forme des identités du staging : une qui lit, une qui écrit sur un périmètre
  borné.
- Que le défaut reste ce qu'il est — un pod, quelques secondes.

**Non-Goals**

- Le proxy-cache, la réplication, les quotas, la rétention, Trivy, le ramasse-miettes.
- Éprouver la lecture authentifiée : les projets du banc sont publics, et c'est délibéré.
- Toute modification de `uske/*.py`.

## Decisions

**D1 — Harbor prend l'adresse de Zot.** Le chart expose un service dont le nom et le port se
paramètrent : `expose.type: clusterIP`, `expose.clusterIP.name: registry`, `ports.httpsPort: 5000`.
Harbor répond alors sur `registry.uske.svc.cluster.local:5000`, et `externalURL` vaut cette même
adresse. Ne changent donc pas : les neuf politiques du banc qui nomment cet hôte en dur, le
certificat TLS et son SAN — repris tels quels par `expose.tls.certSource: secret`,
`secretName: registry-tls` —, `KNOCK_REGISTRIES`, `HARBOR_HOST`, l'amorçage par `crane`,
`screening.yaml` et `attestations.sh`. Alternative écartée : donner à Harbor sa propre adresse, ce
qui obligerait à une seconde série de politiques, un second certificat et d'autres secrets, pour ne
gagner qu'un nom de service plus juste.

**D2 — La variante se choisit par un argument positionnel.** `up.sh harbor`, comme `up.sh dt` et
`up.sh down`. Le nom `REGISTRY` était indisponible : `up.sh` l'emploie déjà pour l'hôte du
registre. Alternatives écartées : une seconde surcouche complète, qui dupliquerait tout ce qui ne
change pas ; un script d'appoint, qui ferait perdre la reproductibilité d'une commande.

**D3 — Chart épinglé, composants réduits.** `harbor/harbor` **1.19.2** (Harbor **2.15.2**), depuis
`https://helm.goharbor.io`. `trivy.enabled: false` — `regis` fait l'analyse, et l'activer coûterait
une image de plus et sa base de failles. `persistence.enabled: false` — le banc reste jetable,
comme il l'est avec l'`emptyDir` de Zot. Restent six composants : cœur, portail, registre, tâches,
PostgreSQL, Valkey.

**D4 — Sept projets, créés publics.** `mirror` pour les sources, puis `hub`, `a-4711`, `a-5203`,
`a-6100`, `a-7300`, `shared-test`, dérivés des politiques du banc et non recopiés à la main.
Publics parce qu'`attestations.sh` tire l'image placée sans identifiants, par un port-forward, pour
en vérifier les signatures ; Harbor crée ses projets privés par défaut et ce tir échouerait. Le
prix est que le banc n'éprouve pas la lecture authentifiée ; la séparation qui compte, le droit
d'écrire, reste entière.

**D5 — Trois identités.** `admin`, dont le mot de passe est fixe et écrit dans `up.sh` — banc
jetable, comme l'est déjà celui de Dependency-Track — et qui ne sert qu'au montage : créer les
projets et les robots, amorcer `mirror`. `robot$uske-read`, en lecture, pour `census` et `regis`.
`robot$uske-knock`, en écriture sur les six projets de destination et en lecture sur `mirror`, pour
`knock`. Aucune charge de travail ne reçoit `admin`.

**D6 — Les secrets gagnent ce qui leur manquait.** `uske-harbor` reçoit `HARBOR_URL` (avec le
schéma), `HARBOR_USER` et `HARBOR_PASSWORD`, et garde `HARBOR_HOST` (hôte et port, sans schéma :
c'est la forme qu'attend l'option d'authentification de `regis`) et `SSL_CERT_FILE`.
`KNOCK_REGISTRIES` gagne `username` et `password`, deux champs qui existent et vont par paire —
vérifié dans le `README.md` de `knock`, tableau `RegistryConfig`. En mode Zot, rien ne change.

**D7 — Le geste de confiance cosign est sauté en mode Harbor.** `up.sh` pousse aujourd'hui la clé
publique de `knock` dans `/v2/_zot/ext/cosign`, une extension propre à Zot. Elle n'a pas
d'équivalent Harbor, et `attestations.sh` vérifie déjà les signatures avec la clé, ce qui est le
vrai sujet.

## Risks / Trade-offs

- Le robot en lecture n'énumère pas les projets → mesuré à la première tâche ; repli sur `admin`
  pour `census` dans le banc, écrit en commentaire plutôt que tu.
- `externalURL` ne correspond pas à l'adresse employée, et les poussées échouent sur une
  redirection → il vaut exactement ce que les politiques et les secrets nomment.
- Harbor met plusieurs minutes à répondre → `helm --wait`, puis attente du déploiement du cœur,
  comme `up.sh` attend déjà celui de Zot.
- Six images à tirer au premier montage, un peu plus d'un gigaoctet de mémoire → coût annoncé, une
  fois par poste ; c'est la raison pour laquelle Zot reste le défaut.
- Un projet manque et `knock` échoue à pousser → les sept sont créés avant l'amorçage.
- Le mot de passe administrateur ne satisfait pas la politique de Harbor → une valeur fixe et
  conforme dans `up.sh`.
- Les projets publics éloignent le banc du staging → assumé, et écrit ici pour que personne ne
  déduise du banc que la lecture anonyme est admise en réel.

## Migration Plan

Rien à migrer : la variante s'ajoute, le défaut ne bouge pas.

1. Écrire la variante et ses valeurs de chart.
2. Monter le banc par défaut, vérifier qu'il se comporte comme avant.
3. Monter la variante, lancer un screening, vérifier les signatures, lancer `census`.
4. Détruire, remonter une fois de chaque, pour que la reproductibilité soit constatée et non
   supposée.

**Retour arrière** : `deploy/kind/up.sh down`, et le défaut n'a jamais changé.

## Open Questions

- Un robot Harbor de portée système peut-il énumérer les projets ? Première tâche, repli nommé.
- Un projet proxy-cache dans le banc, plus tard ? Écarté aujourd'hui ; à rouvrir si le staging
  montre que ce motif casse quelque chose que le banc aurait pu révéler.
- Aucun ADR en vigueur n'est à revisiter : ce change n'introduit aucun engagement durable
  d'architecture. La section `## ADR` de `tasks.md` le consigne.
