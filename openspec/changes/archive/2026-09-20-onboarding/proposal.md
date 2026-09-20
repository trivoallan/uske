## Why

La méthode est posée dans le dépôt, mais rien n'y est encore statué : dix ADR hérités sont en
`proposed` avec des clés vides, et il n'y a pas de document d'architecture. Tant qu'une clé est
vide, un agent qui ajoute du code devine — le langage, les branches, la langue des commits, le
seuil de tests. Le faire maintenant, avant la première story de `openspec/discovery.md`, évite
que cinq changes se construisent sur des défauts que personne n'a choisis.

**Objectif qualité.** Ce change sert la **contestabilité** (rang 2 de
`openspec/discovery.md`) : toute décision est consignée, jamais réécrite, et se retrouve avec
sa raison. Il l'applique au dépôt lui-même — chaque valeur d'ADR portera sa provenance,
*constatée* avec le fichier ou *répondue* avec la date. Il n'arbitre aucun conflit entre
objectifs.

## What Changes

- **Découverte** — `openspec/discovery.md` créé (déjà conduit au premier artefact) : trois
  personas, un parcours annoté contre le code, cinq stories, et quatre objectifs qualité
  ordonnés — Sûreté > Contestabilité > Opérabilité > Minceur.
- **Verdicts** — les dix ADR hérités `docs/adr/SDR-0002` à `SDR-0011` reçoivent chacun un
  verdict `accepted` ou `rejected`, sur réponse reçue. Un ADR sans réponse reste `proposed` et
  figure comme tel dans un tableau final. `SDR-0009` (branches) est statué le premier : il dit
  où part le reste.
- **Document d'architecture** — `docs/architecture/arc42.md` créé depuis le gabarit de la
  méthode, avec deux sections rédigées : *Introduction and Goals*, depuis la découverte, et
  *Architecture Decisions*, depuis les ADR statués. Puis une relecture du document.
- **Aucun changement de comportement de `uske`** : ni code applicatif, ni manifestes de
  déploiement, ni tests.

## Capabilities

### New Capabilities

- `repository-method`: l'état que le dépôt doit tenir une fois entré dans la méthode — une
  découverte avec des objectifs qualité ordonnés ; des ADR hérités qui portent chacun un
  verdict vérifiable, avec la provenance de chaque valeur ; un document d'architecture que
  l'ADR d'architecture désigne.

### Modified Capabilities

Aucune — `openspec/specs/` est vide.

## Impact

- **Fichiers** : `openspec/discovery.md` (nouveau) ; `docs/adr/SDR-0002` à `SDR-0011`
  (frontmatter, corps, mode d'emploi coupé) ; `docs/architecture/arc42.md` (nouveau) ;
  `.gitignore` (quatre lignes en attente, qui suivent le même chemin).
- **Code, interfaces, dépendances** : aucun. La vérification des ADR passe par
  `npx @jackchuka/mdschema@0.15.1`, lancé à la demande, sans entrée dans `package.json`.
- **Skills** : `arc42-section-01`, `arc42-section-09`, `arc42-review`, accord reçu le
  2026-09-20.
- **Changes à venir** : les cinq stories de la découverte liront les verdicts. Un verdict sur
  la langue (`SDR-0002`) peut demander de reprendre des artefacts déjà écrits en français.
- **Surface d'attaque** : aucune nouvelle. Le change n'ajoute ni code exécuté, ni dépendance
  installée, ni secret, ni accès réseau au produit. Seule exécution : la vérification des ADR,
  lancée à la main, à version épinglée.
- **Branche ou `main`** : non tranché ici ; le verdict de `SDR-0009` le dira avant toute
  écriture dans `docs/adr/`.
