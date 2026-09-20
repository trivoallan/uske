# Brainstorm

## Contexte

`uske` vient de recevoir la méthode (`chore: pose de la méthode`, `chore: verrou des skills`).
Le change `onboarding` fait entrer le dépôt dedans. À son ouverture, le 2026-09-20 :

- `openspec/discovery.md` absent ;
- dix ADR hérités en `status: proposed` — `docs/adr/SDR-0002` à `SDR-0011` ; seul `SDR-0001`
  est `accepted` ;
- `docs/architecture/arc42.md` absent ;
- aucun refus antérieur consigné sous `openspec/changes/`, archives comprises.

La détection s'est arrêtée à la première proposition : la découverte. Acceptée, elle a été
conduite dans ce change et a produit `openspec/discovery.md`, hors du répertoire du change.

Le cadrage a tenu en cinq passes, la borne.

## Chaîne de décision

### Passe 1 sur 5 — détection et périmètre

- **Q1 — Conduire la découverte dans ce change ?** Oui. Ferme : les verdicts et le document
  d'architecture se statueront contre des objectifs qualité connus.
- **Q2 — Que recouvre « onboarding » ?** Le dépôt dans la méthode : découverte, verdicts des
  ADR hérités, document d'architecture. Ferme : le change n'a pas d'autre travail propre, et
  ne touche pas au code applicatif.

### Passe 2 sur 5 — office-hours

Dépôt d'infrastructure : des six questions de la skill, statu quo et coin étroit, plus le but
et la personne. Recherche de l'existant et second avis non conduits — chacun coûtait une passe.

- **D1 — But ?** Open source / recherche. Ferme : mode builder, pas de diagnostic startup.
- **D2 — Statu quo ?** Scripts et chaînes d'intégration maison, par équipe ; jugement et
  placement mêlés ; rien de contestable après coup.
- **D3 — Qui en a le plus besoin ?** La responsable plateforme, qui tient le registre.
- **D4 — Plus petit usage réel ?** Un screening planifié : une politique, un registre,
  placement direct, la ligne de résultat écrite.

### Passe 3 sur 5 — discovery

- **Q1 — Ordre des objectifs qualité ?** Sûreté > Contestabilité > Opérabilité > Minceur.
  Ferme : le registre d'abord ; `uske` grossit si la sûreté l'exige.
- **Q2 — Personas ?** Responsable plateforme (principale), équipe applicative, et l'auditeur
  sécurité / conformité, ajouté.
- **Q3 — MoSCoW ?** L'issue quarantaine monte en Must, avec le premier screening déployé et
  la lecture d'un refus. Cohérent avec la sûreté au rang 1.
- **Q4 — Prémisses ?** P1 rejetée : le mal est d'abord l'absence d'automatisation, la
  contestabilité vient ensuite. P2 (colle non générique) et P3 (premier utilisateur :
  l'auteur, un seul registre) tenues.

Produit : `openspec/discovery.md`, `Status: complete`, cinq stories.

### Passe 4 sur 5 — brainstorming du travail propre

Tri préalable des ADR contre le dépôt, à affiner à l'application :

| Tas | ADR | Preuve |
| --- | --- | --- |
| Constaté | SDR-0004 langages | `pyproject.toml` |
| Constaté, en partie | SDR-0010 forge et CI | remote `origin`, `.github/workflows/test.yaml` ; `ci.gate` à choisir |
| À choisir | SDR-0002, 0003, 0005, 0006, 0007, 0008, 0009, 0011 | rien dans le dépôt ne fixe toutes leurs valeurs |

- **Q1 — Approche ?** A — tout dans ce change : dix verdicts, document d'architecture,
  relecture, une seule merge request.
- **Q2 — Skills expertes pour l'arc42 ?** Oui, les trois : `arc42-section-01`,
  `arc42-section-09`, `arc42-review`.
- **Q3 — `grill-me` sur l'hypothèse « un dépôt-graine à un seul auteur gagne à statuer dix
  ADR d'un coup » ?** Non ; deux alternatives pesées à la main suffisent (ci-dessous).
- **Q4 — Où travailler : branche et merge request, ou `main` ?** À trancher par le verdict de
  SDR-0009.

### Passe 5 sur 5 — conception

- **Q1 — La conception convient-elle ?** Oui, telle quelle.

## Conception validée

1. **Ordre.** Découverte (faite) → verdicts → arc42 → relecture → vérification. Aucun code
   applicatif.
2. **Verdicts, à l'application.** Lire les dix ADR en entier ; affiner le tri constaté /
   à choisir, preuves affichées fichier par fichier. Recueillir les réponses en une passe : une
   confirmation pour tout le tas constaté, une par ADR à choisir. Aucun verdict sans réponse
   reçue, pas même pour un ADR entièrement prouvé.
3. **SDR-0009 d'abord dans les actes.** Sa réponse dit si le reste part sur une branche avec
   merge request ou sur `main`. Rien ne s'écrit dans `docs/adr/` avant de l'avoir.
4. **Les cinq gestes, ADR par ADR**, tels que chaque fichier les prescrit : `traits:` remplis
   — ou retirés en entier si `rejected`, avec ce qui en tient lieu — ; `status` ; `date` et
   `authors` ; deux ou trois lignes de conséquences ; coupe du mode d'emploi en dernier.
   Provenance de chaque valeur écrite dans l'ADR : *constatée*, avec le fichier ; ou
   *répondue*, avec la date. Un ADR sans réponse reste `proposed` ; le change continue.
   Tableau final à quatre colonnes — ADR en lien, thème, décisions, statut —, où un ADR resté
   `proposed` figure avec *sans réponse*.
5. **arc42.** `docs/architecture/arc42.md` créé depuis
   `node_modules/surdesrails/resources/docs/arc42/index.md`. *Introduction and Goals* par
   `arc42-section-01` depuis `openspec/discovery.md` — les quatre objectifs, dans leur ordre.
   *Architecture Decisions* par `arc42-section-09` depuis les ADR qui portent un verdict.
   Puis `arc42-review` ; les constats critiques se corrigent sur-le-champ. Aucune autre
   section.
6. **Vérification.** `( cd docs/adr && npx @jackchuka/mdschema@0.15.1 check '*.md' )` passe ;
   `arc42-review` sans constat critique ; SDR-0003 porte `architecture.document`.

## Alternatives pesées

- **A — Tout dans ce change** (retenue). C'est ce que la méthode prescrit : un objet accepté
  se conduit dans le change, et ses fichiers partent dans sa merge request. L'arc42 a besoin
  des verdicts pour sa section des décisions. Coût : un gros change documentaire.
- **B — Constatés + arc42.** Écartée : le dépôt resterait à moitié entré ; la détection
  reproposerait les verdicts à chaque change ; la section des décisions de l'arc42 naîtrait
  presque vide.
- **C — Verdicts seuls, arc42 dans un change suivant.** Écartée : deux merge requests pour un
  même geste d'entrée, et SDR-0003 devrait nommer un document qui n'existe pas encore.

**L'hypothèse attaquée à la main** — « un dépôt-graine à un seul auteur gagne à statuer dix
ADR d'un coup ». Contre : plusieurs questions (branches, livraison, seuil de couverture) n'ont
pas encore de pratique pour les éclairer, et un verdict pris à vide est un défaut accepté.
Pour : tant qu'une clé est vide, un agent devine ; `rejected` est une réponse pleine, qui dit
ce qui en tient lieu ; un ADR se remplace par un autre qui le `supersedes`. L'hypothèse tient,
à condition que `rejected` et *sans réponse* restent des issues ouvertes pour chaque ADR. La
relecture tranche.

## Questions ouvertes

- **Branche ou `main`** — renvoyé au verdict de SDR-0009, recueilli à l'application. Le
  `.gitignore` modifié et non commité suivra le même chemin.
- **Plafond de l'outil de questions** — quatre questions par appel ; une confirmation par ADR
  à choisir en demande au moins huit. La passe de verdicts tiendra en plusieurs appels
  consécutifs, sans travail entre eux. À la relecture de dire si cela respecte « une seule
  passe ».
- **`ci.gate` de SDR-0010** — la seule clé non prouvée d'un ADR par ailleurs constaté : le
  range-t-on au tas « à choisir » en entier ?
- **Langue des artefacts** — ce change est écrit en français, le `README.md` est bilingue,
  le code est en anglais ; SDR-0002 tranchera, et pourra demander de reprendre ce qui est
  déjà écrit.
- **Ligne de backlog dans `openspec/config.yaml`**, proposée par la skill discovery : non
  posée, la borne des cinq passes n'a pas laissé de place pour la demander.
- **Questions ouvertes de la découverte** — cible réelle de la story 1, coupe de la story 1,
  sens de « mettre à l'écart » pour une image déjà placée : elles vivent dans
  `openspec/discovery.md` et ne bloquent pas ce change.
