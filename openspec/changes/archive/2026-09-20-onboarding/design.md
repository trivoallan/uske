> **Sections arc42 touchées** : 1 — *Introduction and Goals* ; 9 — *Architecture Decisions*.
> Le document `docs/architecture/arc42.md` est créé par ce change. Aucun bloc, conteneur ni
> frontière de déploiement ne se déplace ; aucun diagramme.

## Context

La méthode est posée dans `uske` ; rien n'y est statué. État au 2026-09-20 :

- `openspec/discovery.md` existe depuis le premier artefact de ce change, avec quatre objectifs
  qualité ordonnés : Sûreté > Contestabilité > Opérabilité > Minceur.
- `docs/adr/` porte onze ADR hérités. **Un seul est en vigueur : `SDR-0001`**, `accepted`,
  que rien ne dépasse. Les dix autres, `SDR-0002` à `SDR-0011`, sont `proposed`, leurs clés
  `traits:` vides, chacun avec son mode d'emploi en cinq gestes. Aucun `supersedes` n'est
  renseigné : le graphe de dépassement est vide.
- `docs/architecture/arc42.md` n'existe pas ; le gabarit est dans
  `node_modules/surdesrails/resources/docs/arc42/index.md`.

**Ce que `SDR-0001` impose à ce design.** Format MADR, en-têtes en anglais, corps dans la langue
du dépôt ; le frontmatter est la source machine ; **le corps gèle à `accepted`** — seul le
`status` s'écrit encore après, et rouvrir une décision demande un nouvel ADR qui la nomme dans
son `supersedes:` ; la vérification par schéma atteste qu'un verdict est porté, elle ne juge
pas la décision ; limite de 500 par ADR.

Parties prenantes : l'auteur, seul à décider aujourd'hui ; les agents qui écriront les cinq
stories de la découverte et liront les `traits:` sans les interpréter.

Motivation : voir `proposal.md`. Exigences : `specs/repository-method/spec.md`.

## Goals / Non-Goals

**Goals:**

- Chaque ADR hérité porte un verdict sur réponse reçue, ou figure *sans réponse* au tableau
  final.
- Chaque valeur statuée dit sa provenance, dans le corps de l'ADR.
- `docs/architecture/arc42.md` existe, avec ses sections 1 et 9, relu, et `SDR-0003` le désigne.
- La vérification de `docs/adr/` ne nomme que les fichiers restés *sans réponse*.

**Non-Goals:**

- Toucher au code de `uske`, aux manifestes de `deploy/`, aux tests ou à l'intégration continue
  — y compris pour les mettre en accord avec un verdict : cela revient aux changes suivants.
- Rédiger d'autres sections de l'arc42 que la 1 et la 9.
- Écrire de nouveaux ADR propres à `uske`. Ce change statue sur l'hérité.
- Déclarer des commandes dans un `CLAUDE.local.md`.

## Decisions

| Décision | Cran de réversibilité |
| --- | --- |
| D1 — une passe, puis l'écriture | réversible — un procédé, sans trace au dépôt |
| D2 — deux tas | réversible — idem |
| D3 — `SDR-0009` ouvre les actes | réversible sur une branche ; coûteux sur `main`, dont l'historique est public |
| D4 — cinq gestes et provenance | **irréversible** à `accepted` : `SDR-0001` gèle le corps. Couvert : chaque verdict *est* un ADR, et se dépasse par un autre |
| D5 — l'arc42 après les verdicts | réversible — un document vivant |
| D6 — vérification à la demande | réversible |

### D1 — Les réponses se recueillent en une passe, à l'application, avant toute écriture

Toutes les questions de verdict partent ensemble, une fois le tri fait. Rien ne s'écrit dans
`docs/adr/` avant que la passe soit close.

*Pourquoi* : `SDR-0001` gèle le corps à `accepted`. Un verdict écrit au fil des réponses, puis
contredit par une réponse suivante — la langue de `SDR-0002` change ce qu'on écrit dans tous
les autres —, ne se corrigerait que par un ADR de dépassement. Recueillir d'abord, écrire
ensuite, rend l'écriture atomique.

*Écarté* : statuer ADR par ADR, question puis écriture. Plus simple à suivre, mais expose au
gel décrit ci-dessus, et multiplie les allers-retours.

### D2 — Deux tas, et le doute va au tas « à choisir »

**Constaté** : toutes les clés de l'ADR sont fixées par un fichier du dépôt ; une seule
confirmation couvre le tas, preuves affichées. **À choisir** : au moins une clé ne l'est pas ;
une confirmation par ADR. Un ADR prouvé en partie — `SDR-0010`, dont `ci.gate` ne se lit nulle
part — va **en entier** au tas « à choisir », avec ses valeurs constatées proposées par défaut.

*Pourquoi* : un ADR se statue en un seul acte ; le couper en deux tas produirait un fichier à
moitié rempli, que la vérification refuse. Cela ferme la question ouverte du brainstorm.

*Écarté* : trier clé par clé. Plus fin, mais la confirmation par tas perd son sens.

### D3 — `SDR-0009` ouvre les actes

Les réponses reçues, le verdict sur les branches est lu le premier : il dit si tout ce qui suit
— découverte, verdicts, arc42, et le `.gitignore` en attente — part sur une branche avec merge
request, ou sur `main`. La branche, s'il en faut une, se crée avant la première écriture dans
`docs/adr/`.

*Si `SDR-0009` reste sans réponse* : on travaille sur une branche. C'est le choix réversible —
une branche se fusionne en avance rapide sur `main`, l'inverse ne se défait pas proprement —,
et c'est ce que chaque ADR demande déjà : « un seul acte, une seule merge request ».

### D4 — Les cinq gestes de chaque fichier, dans leur ordre, et la provenance en plus

Pour chaque ADR statué, les gestes sont ceux que le fichier prescrit : `traits:` remplis — ou
bloc retiré en entier si `rejected` — ; `status` ; `date: 2026-09-20` et `authors` ;
conséquences ; coupe du mode d'emploi **en dernier**. La provenance s'écrit là où le mode
d'emploi demande déjà « le motif de ce que vous avez décidé » : une ligne par clé,
*constatée — `<fichier>`* ou *répondue — 2026-09-20*. Un `rejected` y dit ce qui en tient lieu.

*Pourquoi là* : pas de nouvelle section, donc pas d'écart au format MADR que `SDR-0001` impose,
et le schéma n'a pas à changer.

*Écarté* : une clé `provenance:` au frontmatter. Lisible par machine, mais le schéma de
`docs/adr/` est posé par la méthode ; l'étendre ici serait réécrit à la prochaine mise à jour.

### D5 — L'arc42 vient après les verdicts, et ne dit que ce qui est décidé

Ordre : copie du gabarit ; section 1 par `arc42-section-01`, depuis `openspec/discovery.md` —
les quatre objectifs, même ordre, mêmes renoncements ; section 9 par `arc42-section-09`, depuis
les seuls ADR qui portent un verdict ; puis `arc42-review`. Les dix autres sections gardent le
texte du gabarit. `SDR-0003` reçoit `architecture.document` en même temps que les autres
verdicts, mais le fichier qu'il désigne est créé dans le même change : à la fusion, les deux
sont là.

*Pourquoi cet ordre* : la section 9 renvoie aux ADR statués ; écrite avant, elle serait vide ou
fausse. Accord reçu le 2026-09-20 pour les trois skills ; sans elles, rédaction à la main et
relecture sur quatre questions — objectifs ordonnés et qui départagent, exigences vérifiables,
aucune technologie non décidée, parties prenantes avec leurs attentes.

### D6 — La vérification est une commande, lancée à la demande

`( cd docs/adr && npx @jackchuka/mdschema@0.15.1 check '*.md' )`, sans entrée dans
`package.json` ni tâche d'intégration continue.

*Pourquoi* : `ci.gate` est précisément l'une des clés à statuer ; brancher une porte avant le
verdict le préjugerait. Un change suivant pourra la poser.

## Risks / Trade-offs

- [Un verdict pris à vide — branches, livraison, seuil de couverture n'ont pas encore de
  pratique] → `rejected` et *sans réponse* restent ouverts pour chaque ADR et sont proposés
  comme options à part entière ; un ADR `accepted` trop tôt se dépasse par un nouvel ADR, le
  journal garde l'histoire.
- [Le corps gèle à `accepted` : une faute de rédaction ne se corrige plus en place] → D1 ;
  et la vérification est lancée, le diff relu, **avant** le commit.
- [La coupe du mode d'emploi mord trop loin — le titre *Consequences* borne la coupe et
  n'apparaît qu'une fois] → coupe faite fichier par fichier, la vérification reconnaît un mode
  d'emploi oublié, le diff montre une coupe excessive.
- [`SDR-0002` choisit une autre langue que le français pour la documentation] → les artefacts
  de ce change et `openspec/discovery.md` seraient à reprendre ; consigné, non traité ici.
- [Plafond de quatre questions par appel de l'outil de questions, pour au moins neuf
  confirmations] → la passe tient en appels consécutifs, sans travail entre eux ; D1 garantit
  qu'aucune écriture ne s'intercale.
- [Un arc42 aux dix sections vides fait illusion de document] → la relecture le dit ; les
  sections non rédigées gardent le texte du gabarit, reconnaissable, plutôt qu'un remplissage.

## Migration Plan

Aucun déploiement : le change est documentaire. Retour arrière : revenir sur le commit, ou
fermer la merge request. Après la fusion, un ADR `accepted` ne se défait plus par retour
arrière d'usage — il se dépasse.

## Open Questions

- Le plafond de quatre questions par appel respecte-t-il « une seule passe » ? À la relecture
  de le dire.
- La ligne de backlog dans `openspec/config.yaml`, proposée par la skill discovery, reste non
  posée.
- Aucun ADR en vigueur n'est à revoir : `SDR-0001` tient, et ce design s'y plie.
