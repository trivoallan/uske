# Discovery : uske

> Status: complete
> Created: 2026-09-20 · Last revised: 2026-09-20

> Plan de version produit par la skill discovery. Reprendre ou réviser en relançant la skill.
> Pour construire : lancer `/opsx:propose` et lui demander la prochaine story non cochée ci-dessous.
> Une story = un change OpenSpec (proposition ≈ 200 mots). Une à la fois.

## Sources

- 2026-09-20 — Pas de PRD. Entrées : le `README.md` du dépôt, la lecture du code (`uske/`,
  `deploy/`), et trois passes de questions conduites dans le change `onboarding`
  (office-hours, puis discovery). Réponses reçues le 2026-09-20.

## Périmètre

`uske` joue ensemble un outil qui juge une image et un outil qui la place : sur planification,
pour chaque politique active, il conduit un **screening** et consigne chaque décision. Il ne juge
rien et ne place rien.

**Hors périmètre** : devenir une colle générique pour d'autres juges ou d'autres placeurs ;
toute interface graphique.

**Prémisses tenues**

- `uske` reste une colle non générique : il connaît ses deux voisins par leur ligne de commande.
- Le premier utilisateur réel est l'auteur, sur un seul registre.

**Prémisse rejetée** — « le mal est d'abord l'impossibilité de contester une décision après
coup ». Réponse reçue : le mal est d'abord **l'absence d'automatisation** ; aujourd'hui des
scripts et des chaînes d'intégration maison, écrits par équipe, mêlent jugement et placement.
La contestabilité vient ensuite.

## Objectifs qualité

Ordonnés : en cas de conflit, le rang le plus haut l'emporte.

1. **Sûreté** — dans le doute, ne rien placer. Un verdict absent, illisible ou non concluant
   vaut refus de placement. *Renonce à* la fraîcheur : une image saine peut attendre un
   screening de plus.
2. **Contestabilité** — toute décision est consignée, jamais réécrite, et se retrouve des
   semaines plus tard avec la règle et la raison. *Renonce à* la compacité du journal et à
   toute correction en place d'une ligne fausse : on ajoute, on ne rature pas.
3. **Opérabilité** — un screening qui échoue se diagnostique et se rejoue sans dégât, par une
   seule personne. *Renonce à* la vitesse d'exécution : les étapes restent séparées, lisibles
   et rejouables plutôt que fondues.
4. **Minceur** — `uske` ne juge ni ne place, et ne grossit pas. *Renonce à* la commodité d'un
   outil qui ferait tout. Dernière du rang : quand la sûreté exige que `uske` vérifie
   lui-même quelque chose, il grossit.

## Personas

### Responsable plateforme (principale)

- **Who** : tient le registre d'images ; c'est elle qu'on appelle quand une image manque ou
  qu'une image douteuse est passée.
- **Goal** : que les images entrent seules, selon des règles déclarées, sans qu'elle y passe
  ses journées.
- **Pain today** : des scripts maison par équipe, où jugement et placement sont mêlés ; rien
  n'est planifié de façon uniforme, rien n'est contestable après coup.
- **Success looks like** : un screening tourne sur planification sans elle ; rien de douteux
  n'entre ; un refus vieux de trois semaines se retrouve et s'explique en une minute.

### Équipe applicative (secondaire)

- **Who** : attend une image dans le registre pour livrer.
- **Goal** : savoir pourquoi son image n'est pas arrivée, et quoi faire.
- **Pain today** : un refus est un silence ; il faut trouver la bonne personne pour l'expliquer.
- **Success looks like** : la raison du refus et la règle appliquée lui sont communiquées sans
  archéologie.

### Auditeur sécurité / conformité (secondaire)

- **Who** : doit prouver ce qui a été admis, refusé, et selon quelle règle.
- **Goal** : lire un journal qui fait foi.
- **Pain today** : aucune trace uniforme ; la preuve se reconstitue à la main.
- **Success looks like** : pour une image et une date, le journal donne la décision, le jeu de
  règles et la raison, et il est établi qu'aucune ligne n'a été réécrite.

## Journey Map

Parcours de la responsable plateforme :

```
 Déclarer ─► Planifier ─► Juger ─► Placer ─► Mettre à ─► Enregistrer ─► Retrouver ─► Mesurer le
 politique   screening    le dû    l'admis   l'écart     la décision    un refus     contournement
    │           │           │         │          │            │             │             │
 supported   partial    supported  partial      gap       supported        gap        supported
```

1. **Déclarer une politique** — les politiques vivent dans un dépôt à part, extrait à chaque
   screening (`uske/policies.py`, `uske list`) — supported
2. **Planifier le screening** — les manifestes existent (`deploy/base/`), rien n'est déployé
   ailleurs que dans le banc local (`deploy/kind/`) — partial
3. **Juger ce qui est dû** — `prepare`, `pending`, `resolve`, `classify` (`uske/gate.py`,
   `uske/outcomes.py`, `uske/playbooks.py`) — supported
4. **Placer ce qui est admis** — `approve` retire du plan les opérations refusées ; des quatre
   issues, seule `direct-placement` agit (`uske/outcomes.py`) — partial
5. **Mettre à l'écart ce qui est refusé** — l'issue `quarantine` est consignée et ne fait rien
   — gap
6. **Enregistrer la décision** — une ligne par décision, ajoutée, jamais réécrite
   (`uske/results.py`, `uske record`) — supported
7. **Retrouver et expliquer un refus** — aucune sous-commande ne lit le journal pour un
   humain ; il faut ouvrir le fichier — gap
8. **Mesurer le contournement** — `census` (`uske/census.py`) — supported

## MoSCoW

### Must

- Un screening planifié qui tourne pour de vrai — c'est l'automatisation qui manque d'abord à
  la responsable plateforme (étape 2).
- Retrouver et expliquer un refus — sans cela ni l'équipe applicative ni l'auditeur n'ont
  rien (étape 7).
- L'issue quarantaine agit — un refus qui ne met rien à l'écart n'est pas un refus ; la sûreté
  est l'objectif de rang 1 (étape 5).

### Should

- L'issue « transformation requise » agit — étape 4, deuxième des trois issues muettes.
- L'issue « non concluante » agit — rejouer plutôt que laisser en suspens ; sert l'opérabilité.

### Could

- Recensement planifié, avec son relevé consigné — l'auditeur le lira, mais `census` se lance
  déjà à la main.
- Circuit de contestation — l'équipe applicative conteste, une personne tranche, la décision
  s'ajoute au journal.

### Won't (this release)

- Colle générique pour d'autres juges ou placeurs — prémisse tenue : `uske` connaît ses voisins.
- Interface graphique — le journal et la ligne de commande suffisent à trois personas qui
  lisent du texte.

## Stories

Liste ordonnée. Une story = un change OpenSpec (proposition ≈ 200 mots).
Chaque story est une tranche verticale fine — de bout en bout et démontrable.

- [ ] 1. `premier-screening-deploye` — un screening tourne sur planification, hors du banc local
  - **Persona served** : responsable plateforme
  - **Journey segment** : 2 (planifier), traversant 3, 4, 6
  - **MoSCoW** : Must
  - **Why this story / why now** : squelette marchant ; le mal premier est l'absence
    d'automatisation, et rien n'est déployé nulle part.
  - **Depends on** : nothing
  - **Scope** : in — une surcouche de déploiement pour une cible réelle ; une politique, un
    registre ; placement direct seul ; la ligne de résultat écrite et relue après le premier
    passage. out — les trois autres issues ; plusieurs registres.
  - **Relevant code** : `deploy/base/`, `deploy/kind/` (modèle de surcouche), `uske/cli.py`,
    `Dockerfile`
  - **Added** : 2026-09-20
  - **Change** : _not yet proposed_

- [ ] 2. `retrouver-un-refus` — pour une image, lire ses décisions, leur règle et leur raison
  - **Persona served** : équipe applicative, auditeur
  - **Journey segment** : 7
  - **MoSCoW** : Must
  - **Why this story / why now** : le journal existe et personne ne peut le lire sans ouvrir
    le fichier ; la contestabilité est l'objectif de rang 2.
  - **Depends on** : nothing (plus parlant après la story 1)
  - **Scope** : in — une sous-commande de lecture ; filtre par référence ou empreinte ; sortie
    lisible par un humain, avec date, état, jeu de règles, raison, rapport. out — contester ;
    modifier le journal.
  - **Relevant code** : `uske/results.py` (`read`, `last_states`, `ResultLine`), `uske/cli.py`
  - **Added** : 2026-09-20
  - **Change** : _not yet proposed_

- [ ] 3. `issue-quarantaine` — une image refusée est mise à l'écart, et c'est consigné
  - **Persona served** : responsable plateforme, auditeur
  - **Journey segment** : 5
  - **MoSCoW** : Must
  - **Why this story / why now** : sûreté, rang 1 ; aujourd'hui l'issue est consignée sans effet.
  - **Depends on** : story 1
  - **Scope** : in — ce que « mettre à l'écart » veut dire pour une image jamais placée et
    pour une image déjà placée ; l'action ; sa ligne au journal. out — la levée de
    quarantaine ; la contestation.
  - **Relevant code** : `uske/outcomes.py` (`Outcome.QUARANTINE`, `classify`), `uske/gate.py`
    (`approve`), `deploy/base/workflowtemplate.yaml`
  - **Added** : 2026-09-20
  - **Change** : _not yet proposed_

- [ ] 4. `issue-transformation` — une image à transformer suit son chemin au lieu d'attendre
  - **Persona served** : responsable plateforme
  - **Journey segment** : 4
  - **MoSCoW** : Should
  - **Why this story / why now** : deuxième issue muette ; après la quarantaine, c'est la plus
    fréquente des non-placements.
  - **Depends on** : story 1
  - **Scope** : in — router l'issue vers la reconstruction que le placeur sait faire ;
    consigner. out — définir de nouvelles transformations.
  - **Relevant code** : `uske/outcomes.py` (`Outcome.TRANSFORMATION_REQUIRED`), `uske/gate.py`
  - **Added** : 2026-09-20
  - **Change** : _not yet proposed_

- [ ] 5. `issue-non-concluante` — un verdict non concluant se rejoue, sans rien placer entre-temps
  - **Persona served** : responsable plateforme
  - **Journey segment** : 3, 4
  - **MoSCoW** : Should
  - **Why this story / why now** : sûreté (ne rien placer) et opérabilité (rejouer sans dégât).
  - **Depends on** : story 1
  - **Scope** : in — l'image reste due au screening suivant ; borne de rejeux ; ligne au
    journal à chaque essai. out — alerter quelqu'un.
  - **Relevant code** : `uske/outcomes.py` (`Outcome.INCONCLUSIVE`), `uske/results.py`
    (`pending`)
  - **Added** : 2026-09-20
  - **Change** : _not yet proposed_

## Open Questions

- Story 1 frôle la taille limite. Ligne de coupe candidate : (a) la surcouche de déploiement
  pour la cible réelle, (b) le premier passage et sa relecture. À trancher à la proposition.
- Quelle est la « cible réelle » de la story 1 ? Aucune n'est nommée à ce jour.
- Que veut dire « mettre à l'écart » pour une image déjà placée par un screening antérieur ?
- Ligne de backlog dans `openspec/config.yaml` (pour que `/opsx:propose` lise ce fichier de
  lui-même) : non posée, faute de confirmation demandée — la borne de cinq passes du cadrage
  l'a écartée.
- Recherche de l'existant et second avis d'office-hours : non conduits, pour la même raison.

## Change Log

- 2026-09-20 — Plan initial, conduit dans le change `onboarding`. Prémisse « contestabilité
  d'abord » rejetée au profit de « automatisation d'abord » ; objectifs qualité ordonnés
  Sûreté > Contestabilité > Opérabilité > Minceur ; auditeur ajouté aux personas ; quarantaine
  montée en Must.
