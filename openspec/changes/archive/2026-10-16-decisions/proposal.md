# Proposition — `uske decisions` lit le journal pour un humain

## Why

Le journal consigne chaque décision, mais personne ne peut le lire sans ouvrir le fichier JSONL :
l'équipe applicative ne sait pas pourquoi son image n'est pas entrée, et l'auditeur ne peut pas
vérifier que chaque exception a été tranchée par quelqu'un de nommé. C'est la story 2 de
`openspec/discovery.md` (`retrouver-un-refus`) et O2-KR2 (une sous-commande lit le journal pour un
humain avant le 2026-11-30).

Objectif qualité : rang 2, **Contestabilité** (`docs/architecture/arc42.md`, *Quality Goals*) — « un
refus vieux de trois semaines se retrouve et s'explique en une minute ». Le change le sert sans en
arbitrer d'autre : il ne fait que lire.

## What Changes

- Nouvelle sous-commande `uske decisions [IMAGE] --results DIR [--policy-name NOM] [--state a,b]
  [--since AAAA-MM-JJ] [--format json|text|md]`, en lecture seule.
- Elle lit les `*.jsonl` du premier niveau de `--results` (un par politique) et dit sur la sortie
  d'erreur ce qu'elle a lu ; `--policy-name` restreint au journal d'un `metadata.name`, et un nom
  inconnu échoue en listant les noms présents. Rien à lire est une erreur, distincte de « aucune
  décision ».
- Une référence qui ne correspond à rien fait proposer, sur la sortie d'erreur, les références
  complètes du journal qui la prolongent.
- Le `README.md` porte une recette `kubectl run` copiable, qui monte le volume `uske-results` en
  lecture seule et va jusqu'au Markdown à coller dans le ticket. Elle est essayée une fois,
  chronométrée, sur le banc kind. Objectif : de la question reçue au Markdown collé, 2 à 5 minutes.
- En `md`, le rapport est rendu en code suivi de `(volume uske-results)`.
- `IMAGE` est une référence complète, une empreinte ou `<dépôt>@sha256:…` ; elle se résout en
  empreintes, étendues aux lignes dont le `source` ou le `rebuilt` les nomme (SDR-0016). Aucune
  correspondance approchée.
- Les lignes sont groupées par politique puis par empreinte, dans l'ordre du fichier, qui fait foi ;
  une ligne antidatée est marquée.
- `--state` et `--since` (jour UTC) filtrent ; tout état est accepté, y compris ceux que `uske`
  n'écrit pas.
- Une ligne hors des quatre états de `uske`, ou une réouverture, sans `arbitration`, est marquée
  « arbitrage absent ».
- Trois formats : `json` par défaut (convention des autres sous-commandes), `text` pour un humain
  au terminal, `md` pour coller dans un ticket — une `timeline` Mermaid par empreinte suivie du
  tableau complet.
- La raison s'affiche toujours à côté de l'état : `quarantine` a deux sens (SDR-0016).
- Une clé que `uske` n'écrit pas, `arbitration` comprise, s'affiche en `clé: valeur` dans l'ordre
  du fichier ; ce change n'en fixe pas le vocabulaire.
- La docstring de `uske/cli.py` et la section *Use* du `README.md` cessent de dire « une
  sous-commande par étape du workflow » : `decisions` n'en est pas une.
- La fixture `tests/fixtures/repo/policies/projets/a-4711/redis-7.journal.jsonl` est corrigée :
  l'exception sur `redis:7.2.8` lève la raison de sa quarantaine (`sbom/license-blocklist`), pas
  une autre.

## Alternatives écartées

- **Ne rien faire, lire le JSONL à la main** : c'est l'archéologie que l'équipe applicative refuse,
  et le scénario de contestabilité « en une minute » n'est pas tenu.
- **Un rendu visuel autonome (page HTML, graphique, tableau de bord)** : c'est l'anti-persona
  (« une console ») ; les trois personas lisent du texte.
- **Un fichier `.md` rendu et commité à côté du journal à chaque screening** : deux sources pour
  la même histoire ; le jour où elles divergent, l'auditeur ne sait plus laquelle fait foi. Le
  rendu se calcule à la demande.
- **`stateDiagram-v2` au lieu de `timeline`** : un état repassé deux fois fusionne en un nœud et la
  chronologie se perd — faux pour un journal qui n'efface rien.
- **Un camembert des états pour l'auditeur** : un tableau de bord déguisé.
- **Trier par `ts`** : une exception ajoutée après coup et antidatée se rangerait « à sa place », et
  l'auditeur ne verrait jamais qu'elle est venue plus tard. L'ordre du fichier fait foi (revue, 4).
- **Livrer `md` en tableau seul, reporter la `timeline`** : proposé en revue (14) parce que la
  chronologie est la plus grosse surface de bogues ; écarté, la chronologie Mermaid est demandée
  explicitement par la personne.
- **`--policy CHEMIN`, comme `pending`, `record` et `approve`** : retenu par la revue OpenSpec (2),
  puis écarté par la revue DX (D9). Le dépôt de politiques n'est pas dans l'image, donc un chemin
  ne sert à rien dans le pod où la commande tourne. `--policy-name`, d'un autre nom, évite de
  confondre les deux sens.
- **Un accès outillé en moins de 2 minutes (un `WorkflowTemplate` `decisions` à soumettre)** :
  il élargirait le change aux manifestes ; une recette copiable vise 2 à 5 minutes sans y toucher
  (revue DX, D5).
- **Une recette qui s'arrête à `--format text`** : le dev lit le Markdown rendu dans son ticket,
  pas le terminal de la plateforme (revue DX, D6).
- **Une correspondance approchée sur les références courtes** : un `redis:7.2.8` qui retrouve
  `docker.io/library/redis:7.2.8` peut aussi retrouver un autre dépôt ; un rappel sur la sortie
  d'erreur suffit (revue, 7).
- **Texte humain par défaut** : écarté au profit de JSON par défaut, pour garder la convention de
  toutes les sous-commandes (réponse reçue, passe 1).
- **Une étape de workflow qui publie la sortie, ou une recette d'accès au volume** : l'accès au
  journal sur le volume est une affaire de déploiement, hors de ce change (réponse reçue, passe 1).
- **Fixer ici le vocabulaire `arbitration`, `abandoned`, `placed-by-exception`** : c'est le circuit
  de contestation (story 3 et suivantes) ; ici on affiche sans définir (réponse reçue, passe 1).
- **Ignorer les clés que `uske` n'écrit pas** : l'auditeur perdrait l'arbitrage, qui est
  précisément sa question.
- **Le nom `retrouver`, `verdicts`, `history`, `ledger`, `journal`** : `verdicts` appartient à
  `regis` et ne couvre pas les exceptions, `ledger` et `docket` trompent, `journal` se confond avec
  `record` qui écrit ; `decisions` nomme l'objet du journal (une ligne par décision).

## Conception

Conception : aucune condition, pas de `design.md` — une sous-commande de lecture, sans dépendance
nouvelle, sans modèle de données qui change, sans motif d'architecture nouveau.

## Revue

Revue : due — un livrable face à un tiers, une CLI lue par l'équipe applicative et l'auditeur.

## Capabilities

### New Capabilities

- `decision-lookup` : retrouver dans le journal les décisions sur une image, ou sur un ensemble
  filtré par état et par date, et les rendre lisibles en JSON, en texte ou en Markdown avec Mermaid.

### Modified Capabilities

Aucune.

## Impact

- `uske/cli.py` : la sous-commande et son parseur.
- Un module de lecture et de rendu (`uske/decisions.py`), appuyé sur `uske/results.py` (`read`).
- `tests/` : golden tests `text` et `md`, tests des filtres et de l'échappement.
- La fixture `redis-7.journal.jsonl` (une raison corrigée).
- `README.md` : la sous-commande dans la liste de *Use*.
- Aucune dépendance nouvelle ; le workflow Argo ne change pas.

## Cadrage

- Détection : `.nanopm/wiki/docs/product.md` présent, aucun ADR en `proposed`,
  `docs/architecture/arc42.md` présent — rien à proposer.
- Jam préalable (`/nanopm:pm-brainstorm`, 2026-10-16) : lecteurs, forme, nom et format `md` tranchés.
- Cadrage, passe 1 sur 5 : périmètre (lecture locale seule), format par défaut (JSON), clés hors
  SDR-0016 (affichées telles quelles), fixture (corrigée).
- Cadrage, passe 2 sur 5 : conception d'ensemble acceptée.

## Questions ouvertes

- **L'équipe applicative ne lance pas la commande elle-même.** La responsable plateforme la lance,
  par la recette du `README.md`, et lui transmet le Markdown. Les rapports `regis` restent sur le
  volume, hors de sa portée. Rien ne la prévient non plus d'un refus : le canal de notification
  reste à trouver.
- **La recette de réouverture du `README.md`** écrit une décision humaine sans nom : faut-il y
  ajouter un arbitre ? C'est fixer un vocabulaire, donc hors de ce change ; `decisions` la marque
  « arbitrage absent » en attendant.
- **Le vocabulaire de l'arbitrage** (`arbitration`, `abandoned`, `placed-by-exception`) n'est fixé
  par aucun ADR ; il existe seulement dans la fixture.
- **Où vit le journal** : la fixture le nomme `<politique>.journal.jsonl` à côté de la politique,
  le workflow l'écrit `<results>/<metadata.name>.jsonl` sur le volume. `decisions` lit le second.
