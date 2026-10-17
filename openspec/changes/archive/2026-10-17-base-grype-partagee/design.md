Sections arc42 touchées : *Deployment View* (un `WorkflowTemplate` et un `CronWorkflow` de plus dans *Infrastructure Level 1*, et deux clés de plus dans le dépôt d'artefacts).

## Context

Aujourd'hui, chaque pod `regis-analyze` télécharge la base de vulnérabilités de grype : 3,25 Go
décompressés, 141,7 s à froid (motivation dans `proposal.md`). `uske` n'est encore déployé nulle
part. Seul le banc kind tourne, et la production s'écrira avec son premier overlay.

Depuis #53 (`screen-and-policy-fan-out`, SDR-0021), un screening est un Workflow parent
`uske-screening` qui crée un Workflow enfant `uske-policy` par politique. Les enfants ne partagent
aucun volume : leur travail passe d'une étape à l'autre par le dépôt d'artefacts du namespace (S3 ;
RustFS sur le banc, `deploy/kind/artifacts.yaml`). Seuls les pods `snapshot` et `merge` du parent
montent `uske-results`. SDR-0021 écarte tout stockage `ReadWriteMany`. `regis-analyze` est une
étape de l'enfant, dans l'image regis (Python 3.14, Alpine).

Contraintes : regis est un dépôt tiers, connu par sa ligne de commande (arc42, *Architecture
Constraints*) ; `uske` ne juge pas (Minceur). Les objectifs qualité sont ordonnés, Sûreté d'abord.

Ce que regis fait d'une erreur de grype (vérifié pendant la revue du 2026-10-17) : l'analyseur
`cve` échoue, et regis range l'erreur dans le résultat `cve` sans interrompre l'analyse
(regis, `core/application/analyze_image.py`). Il sort en 0, puisque `regis-analyze` ne passe pas
`--fail`. Les règles qui lisent `cve` restent *incomplete*. `uske` classe en *inconclusive* une
règle critique *incomplete* (`uske/outcomes.py`). Le playbook complet tient `cve-critical` pour
critique ; le playbook allégé la tient pour informative (D-05), et ses tiers ne lisent pas la CVE.

Mesures du 2026-10-17 (poste de développement, grype 0.114.0, base v6.1.10 du 2026-10-16) :

| Geste | Durée | Taille |
|---|---|---|
| `grype db update` à froid (téléchargement + import) | 141,7 s | 3,25 Go sur disque |
| téléchargement de l'archive d'Anchore seul | 51,7 s | 191 Mo |
| `grype db import` de cette archive | 65,2 s | 3,25 Go |
| `zstd -dc` de l'archive d'Anchore | 1,8 s | — |
| emballage de la base importée (tar, zstd niveau 1) | 3,7 s | 531 Mo |
| déballage de cette archive | 12,9 s | 3,25 Go |
| scan `alpine:3.20`, hachage au démarrage activé ou non | 3 à 4 s | — |

L'import est lent non par la décompression (1,8 s) mais par l'hydratation de la base qu'il fait
ensuite. Distribuer la base **déjà importée** évite de la refaire dans chaque pod.

## Goals / Non-Goals

**Goals:**

- Toutes les évaluations Argo entre deux rafraîchissements jugent avec une seule base, téléchargée
  une fois depuis Anchore.
- Aucun volume partagé entre pods (SDR-0021).
- Dans le régime complet, une base de plus de 48 h, ou absente, fait refuser (*inconclusive*) au
  lieu de laisser juger.
- Ni le rafraîchissement ni son échec ne livrent une base partielle.
- Une évaluation n'appelle plus Anchore.

**Non-Goals:**

- Fournir la base au chemin local et CI (`uske screen`) : c'est à l'appelant de le faire, `uske`
  le documente seulement.
- Réseau fermé et miroir interne de la base.
- Modifier regis, le format du journal ou le régime allégé (D-05).
- Alerter quand le rafraîchissement échoue : noté hors du dépôt (revue, D10).

## Decisions

### D1 — La base passe par le dépôt d'artefacts, sous une clé fixe

Le rafraîchissement dépose deux objets, à des clés fixes hors de `runs/` :

```
grype-db/current.tar.zst   <- la base importée, emballée (tar zstd), ~530 Mo
grype-db/current.json      <- {"built": ..., "checksum": ...} de la base publiée qu'elle contient
```

`regis-analyze` reçoit `grype-db/current.tar.zst` en artefact d'entrée **facultatif**
(`optional: true`, `archive: {none: {}}`), dans son propre système de fichiers. Un objet S3 est
remplacé d'un seul geste : un pod qui le lit pendant un rafraîchissement reçoit l'ancien ou le
nouveau, jamais un mélange. Aucune génération n'est à garder ni à nettoyer : la clé ne porte qu'une
base à la fois.

*Écarté* : un PVC `grype-db` partagé, monté en lecture seule (première conception de ce change).
Il contredit SDR-0021 et épinglerait tous les enfants sur un nœud. *Écarté* : figer la clé par
screening, que le parent passerait à ses enfants. Cela ajoute de la plomberie pour un cas rare (un
rafraîchissement pendant un screening), que la somme de contrôle du rapport rend visible.

### D2 — On distribue la base déjà importée, emballée par Python

Le rafraîchissement lance `grype db update`, qui télécharge l'archive d'Anchore, l'importe et
écrit dans `import.json` sa source et sa somme (la base porte ainsi sa provenance jusque dans le
rapport, `descriptor.db.status.from`). Il emballe ensuite le dossier de la base (`6/`) avec
`tarfile` de Python 3.14, en zstd (`w:zst`). L'évaluation le déballe de la même façon (`r:zst`,
`filter="data"`) : l'image regis n'a besoin d'aucun outil de plus.

*Écarté* : distribuer l'archive d'Anchore et l'importer dans chaque pod. 65 s mesurées par
évaluation, contre 13 s de déballage. *Écarté* : laisser Argo emballer le dossier (tar gzip par
défaut). gzip est plusieurs fois plus lent que zstd à décompresser sur 3,25 Go.

### D3 — Le rafraîchissement tourne dans l'image regis, et vérifie toutes les 6 h

Un `WorkflowTemplate` `grype-db`, planifié par un `CronWorkflow` du même nom (le modèle
`uske`/`uske-screening`), tourne dans l'**image regis**, celle-là même que lancent les
évaluations. Il porte `serviceAccountName: uske`, comme les autres templates : l'exécuteur Argo a
besoin du rôle lié à ce compte. La base dépend du schéma que comprend le grype qui la lit (v6) ;
avec la même image, téléchargeur et lecteurs ont toujours la même version de grype. Après une
montée de version de regis qui change de schéma, il faut lancer un rafraîchissement à la main
(finding 3 de `review.md`).

Planification (revue, D6) : `schedules: ["17 */6 * * *"]`, `concurrencyPolicy: Forbid`, avec la
`retryStrategy` des étapes du screening. Le script :

1. lit la première base active de `grype db list -o json` (`built`, `checksum`) ;
2. lit `grype-db/current.json`, reçu en artefact d'entrée facultatif ; si la somme est la même, il
   sort en succès sans rien produire, et Argo ne téléverse rien ;
3. sinon, `grype db update` dans un dossier temporaire, puis `grype db status` (doit dire `valid`) ;
4. emballe la base, écrit le pointeur, et Argo téléverse les deux sorties.

Un échec à l'étape 3 arrête le script : aucune sortie n'est produite, et les objets en place ne
changent pas. Anchore publie vers 06:29 UTC ; une vérification toutes les 6 h récupère une base de
moins de 6 h, et laisse environ sept vérifications pour rattraper un échec avant les 48 h.

*Écarté* : l'image publique `anchore/grype`, dont la version de grype ne suivrait pas celle de
regis. *Écarté* : une fois par jour à 03:17 UTC (revue, D6).

### D4 — Ce que fait `regis-analyze`

Le pod porte un seul volume, un `emptyDir` de 6 Gi monté en `/grype` (ce n'est pas un volume
persistant : SDR-0021 tient). L'archive y arrive à `/grype/current.tar.zst`. Hors d'un volume, un
artefact d'entrée est monté par `subPath` depuis le disque de l'init container : `rm` échouerait
(EBUSY) et ne libérerait rien. Avant regis, le conteneur déballe l'archive s'il l'a reçue, puis la
supprime ; un déballage raté n'arrête pas l'étape :

```sh
if [ -f /grype/current.tar.zst ]; then   # -f, pas -e : un artefact facultatif absent peut devenir un dossier vide
  python3 - <<'PY' || rm -rf /grype/db
import sys, tarfile
try:
    tarfile.open('/grype/current.tar.zst', 'r:zst').extractall('/grype/db', filter='data')
except Exception as e:
    print(f"grype-db: the database could not be unpacked: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(1)
PY
  rm -f /grype/current.tar.zst
fi
```

Le téléchargement de ~530 Mo est fait par l'init container : `regis-analyze` a sa propre
`retryStrategy` (`retryPolicy: Always`, même limite et même attente), car `OnFailure` ne rejoue
pas un échec d'init.

Puis regis tourne avec quatre variables :

| Variable | Valeur | Effet |
|---|---|---|
| `GRYPE_DB_CACHE_DIR` | `/grype/db` | lire la base déballée |
| `GRYPE_DB_AUTO_UPDATE` | `false` | ne jamais télécharger pendant une évaluation |
| `GRYPE_DB_MAX_ALLOWED_BUILT_AGE` | `48h` | refuser de scanner avec une base trop vieille |
| `GRYPE_CHECK_FOR_APP_UPDATE` | `false` | ne pas demander à Anchore si grype a une version plus récente (revue, D8) |

Sans archive, `/grype/db` reste vide. grype échoue alors faute de base, comme avec une base
trop vieille : regis range l'erreur dans le résultat `cve` et sort en 0. La règle `cve-critical`
reste *incomplete* ; dans le régime complet, `uske` consigne *inconclusive* (D-23). Dans le régime
allégé, la décision ne lit pas la CVE (D-05). `uske` n'ajoute aucune vérification.

La vérification par hachage au démarrage (`GRYPE_DB_VALIDATE_BY_HASH_ON_START`) reste à sa valeur
par défaut, activée (revue, D5). Elle ne coûte rien de visible (scan de 3 à 4 s avec ou sans), et
c'est la seule vérification d'intégrité de la base au moment de la lecture.

*Écarté* : faire vérifier l'âge par `uske` avant de lancer regis, ou faire refuser par `uske` toute
erreur `cve` (revue, D3). Les deux feraient juger `uske`, et le second contredit D-05.

### D5 — Sur le banc, le cron est suspendu et `up.sh` remplit

Sur le banc kind, le `CronWorkflow` `grype-db` est suspendu, comme celui des screenings (revue,
D9). `up.sh` lance un remplissage (`deploy/kind/grype-db.yaml`) et l'attend avant d'annoncer le
banc prêt. Après une pause du banc de plus de 48 h, on relance ce remplissage à la main.

## Risks / Trade-offs

- [Chaque pod `regis-analyze` occupe ~3,8 Go de stockage éphémère, l'archive puis la base] → les
  deux plafonds de `uske-screening` bornent le nombre de pods simultanés. L'overlay de production
  doit vérifier que ses nœuds ont ce disque par pod en parallèle. La requête de 5 Gi couvre la
  base, pour le placement ; le `sizeLimit` de 6 Gi de l'`emptyDir` la borne ; l'archive y est
  supprimée dès qu'elle est déballée (c'est possible parce qu'elle est sur ce volume). L'espace
  de travail de l'image analysée n'est pas plafonné, comme avant : une limite du conteneur le
  plafonnerait aussi, et une image de plusieurs Go serait évincée (échec technique).
- [Chaque évaluation lit ~530 Mo du dépôt d'artefacts, puis déballe 3,25 Go (13 s mesurées sur un
  poste)] → c'est le prix de SDR-0021. Le gain reste net : ~20 s au lieu de ~140 s.
- [Une base altérée dans le dépôt d'artefacts produit de faux verdicts sains dans toute la flotte]
  → seul le `WorkflowTemplate` `grype-db` écrit ces clés. Les identifiants du dépôt d'artefacts
  sont la frontière, la même que pour le travail des enfants. grype vérifie le hachage de la base à
  chaque démarrage, et la somme figure dans chaque rapport. Voir `review.md`.
- [Le cron tombe en panne] → environ sept vérifications passent avant la limite. Au-delà de 48 h,
  le régime complet passe en *inconclusive* : le screening ne place plus rien et le dit. La panne
  se voit dans Argo (exécution en échec). Aucune alerte n'est prévue (noté hors du dépôt, revue D10). Pour
  un opérateur, l'indication d'une règle *incomplete* (« le prochain screening la rejuge »,
  `uske/outcomes.py`) trompe dans ce cas : la doc d'exploitation nomme le `CronWorkflow` `grype-db`
  comme première chose à regarder.
- [Anchore cesse de publier pendant plus de 48 h] → la limite porte sur l'âge de *construction*
  de la base. Un cron sain ne suffit donc pas : le régime complet passe en *inconclusive*. C'est
  accepté : on préfère ne pas juger plutôt que juger sur une base vieille.
- [La somme de contrôle disparaît à l'emballage] → la tâche 1 vérifie que `descriptor.db.status.from`
  porte encore l'URL et sa somme après déballage dans un autre pod.
- [Le bucket du dépôt d'artefacts n'existe pas encore] → Argo ne le crée qu'à la première
  écriture, et un artefact d'entrée facultatif dans un bucket absent est une erreur, pas une
  absence (trouvé sur le banc le 2026-10-17). Le bucket doit exister avant le premier
  rafraîchissement ; sur le banc, `up.sh` le crée.
- [Argo écrit les artefacts d'entrée en `0600 root`, et l'image regis tourne en non-root] → le
  pointeur et l'archive étaient illisibles (trouvé sur le banc) ; les deux entrées portent
  `mode: 0444`.

## Migration Plan

1. Appliquer le `WorkflowTemplate` et le `CronWorkflow`, puis lancer un premier rafraîchissement à
   la main.
2. Ajouter l'artefact d'entrée, le déballage et les variables à `regis-analyze`. Un screening lancé
   avant le premier rafraîchissement donne, dans le régime complet, des évaluations
   *inconclusive*, rejouées au screening suivant.
3. Retour arrière : retirer l'artefact, le déballage et les quatre variables de `regis-analyze`.
   Chaque pod retélécharge alors sa base, comme aujourd'hui. Le cron et les deux clés peuvent
   rester en place sans effet.

## Open Questions

- Tranché par le spike du 2026-10-17, dans l'image regis épinglée (0.41.0-full, grype 0.112.0,
  Python 3.14.7, Docker sur un poste) :
  - `grype db list -o json` donne, pour la base active, `status`, `built` et `checksum`
    (`sha256:…`) : le script de D3 s'y appuie.
  - `grype db update` puis l'emballage en `w:zst` : 123 s, puis 15 s, pour une archive de 493 Mo.
  - Déballage dans un conteneur neuf, utilisateur non root (1001) : 13 s. `descriptor.db.status`
    donne `valid: true` et un `from` qui porte l'URL d'Anchore et son `checksum` : la provenance
    survit à l'emballage (finding 5 de `review.md`, tranché).
  - Les quatre variables gardent leur nom sur 0.112.0. Avec elles, grype n'écrit plus « A newer
    version of grype is available ».
  - Base trop vieille (`GRYPE_DB_MAX_ALLOWED_BUILT_AGE=1s`) : sortie 1, « the vulnerability database
    was built 23 hours ago (max allowed age is 1 second) ». Base absente : sortie 1, « database does
    not exist ».
  - regis 0.41.0 sans base : sortie 0, et `results.cve.error` vaut
    `{"type": "tool", "message": "grype failed: … database does not exist"}` : c'est la chaîne de
    D4.
- Aucun ADR en vigueur n'est à revoir. Ce change applique SDR-0021 (aucun volume partagé) et reste
  cohérent avec SDR-0003 et SDR-0017.
