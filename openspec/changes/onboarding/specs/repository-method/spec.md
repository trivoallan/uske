## ADDED Requirements

### Requirement: La découverte déclare des objectifs qualité ordonnés

Le dépôt MUST porter un fichier `openspec/discovery.md` dont la section `## Objectifs qualité`
liste de trois à cinq objectifs, numérotés dans l'ordre où ils l'emportent en cas de conflit.
Chaque objectif MUST dire ce à quoi il fait renoncer. La section MUST NOT nommer de technologie.

#### Scenario: Deux objectifs se contredisent

- **GIVEN** un change dont deux objectifs qualité appellent des choix opposés
- **WHEN** une personne ou un agent lit `openspec/discovery.md`
- **THEN** le rang des objectifs désigne celui qui l'emporte, sans autre source à consulter

#### Scenario: Un objectif ne coûte rien

- **GIVEN** un objectif qualité écrit sans renoncement
- **WHEN** la découverte est relue
- **THEN** l'objectif est refusé tant qu'il ne dit pas ce qu'il fait abandonner

### Requirement: Aucun verdict sans réponse reçue

Un ADR hérité MUST NOT passer de `proposed` à `accepted` ou `rejected` sans qu'une personne ait
répondu, y compris quand chacune de ses valeurs est prouvée par un fichier du dépôt. Une
inférence — l'historique, le silence, l'état du dépôt — MUST NOT tenir lieu de réponse.

#### Scenario: Un ADR entièrement prouvé par le dépôt

- **GIVEN** un ADR hérité `proposed` dont toutes les valeurs se lisent dans des fichiers du dépôt
- **WHEN** les verdicts sont conduits
- **THEN** les preuves sont affichées et une confirmation est demandée
- **AND** le statut ne change qu'après cette confirmation

#### Scenario: Une question reste sans réponse

- **GIVEN** un ADR hérité `proposed` pour lequel aucune réponse n'a été reçue
- **WHEN** les verdicts sont conduits
- **THEN** l'ADR reste `proposed`, son fichier n'est pas modifié
- **AND** il figure au tableau final avec la mention *sans réponse*

### Requirement: Chaque valeur statuée porte sa provenance

Un ADR hérité qui reçoit le verdict `accepted` MUST écrire chaque valeur dans le bloc `traits:`
de son frontmatter, et MUST dire dans son corps d'où vient chacune : *constatée*, avec le
fichier qui la fixe, ou *répondue*, avec la date de la réponse. Il MUST renseigner `date:` et
`authors:`, écrire ses conséquences, et ne plus contenir le mode d'emploi du verdict.

#### Scenario: Retrouver d'où vient une valeur

- **GIVEN** un ADR hérité `accepted`
- **WHEN** une personne conteste une valeur de son bloc `traits:` des semaines plus tard
- **THEN** le corps de l'ADR dit si la valeur a été constatée, et dans quel fichier, ou répondue, et à quelle date

#### Scenario: Une valeur écrite seulement en prose

- **GIVEN** un ADR hérité dont la décision figure dans le corps mais dont une clé de `traits:` est vide
- **WHEN** la vérification du répertoire `docs/adr/` est lancée
- **THEN** elle nomme ce fichier et la clé restée vide

### Requirement: Un verdict rejected dit ce qui en tient lieu

Un ADR hérité qui reçoit le verdict `rejected` MUST retirer son bloc `traits:` en entier et MUST
écrire dans son corps ce qui tient lieu de la décision dans ce dépôt.

#### Scenario: La question ne se pose pas dans ce dépôt

- **GIVEN** un ADR hérité dont la question est sans objet pour le dépôt
- **WHEN** il reçoit le verdict `rejected`
- **THEN** son frontmatter ne contient plus aucune clé `traits:`
- **AND** son corps dit à quoi un agent doit s'en tenir à la place
- **AND** la vérification du répertoire `docs/adr/` passe pour ce fichier

### Requirement: Les verdicts se vérifient mécaniquement

La vérification du répertoire `docs/adr/` contre son schéma MUST passer pour tout ADR qui porte
un verdict. Les seuls fichiers qu'elle nomme MUST être ceux qui figurent au tableau final avec
la mention *sans réponse*.

#### Scenario: Tous les ADR ont reçu une réponse

- **GIVEN** dix ADR hérités ayant chacun reçu un verdict
- **WHEN** la vérification du répertoire `docs/adr/` est lancée
- **THEN** elle ne nomme aucun fichier

#### Scenario: Un ADR est resté sans réponse

- **GIVEN** un ADR hérité resté `proposed` faute de réponse
- **WHEN** la vérification du répertoire `docs/adr/` est lancée
- **THEN** elle nomme ce fichier, et lui seul
- **AND** ce fichier figure au tableau final avec la mention *sans réponse*

### Requirement: Un tableau final rend compte des verdicts

La conduite des verdicts MUST se terminer par un tableau à quatre colonnes — l'ADR en lien, son
thème, les décisions prises, son statut — qui liste tous les ADR hérités, statués ou non.

#### Scenario: Lire l'état des décisions d'un coup d'œil

- **GIVEN** les verdicts conduits
- **WHEN** une personne lit le tableau final
- **THEN** elle y trouve chaque ADR hérité, avec son statut et ses valeurs, ou la mention *sans réponse*

### Requirement: L'ADR d'architecture désigne le document d'architecture

Le dépôt MUST porter un document d'architecture à `docs/architecture/arc42.md`, et le trait
`architecture.document` de l'ADR hérité d'architecture MUST le désigner. Le document MUST
contenir une introduction dont les objectifs qualité sont ceux de `openspec/discovery.md`, dans
le même ordre, et une section des décisions qui renvoie à chaque ADR portant un verdict.
Il MUST NOT présenter comme décidée une technologie qu'aucun ADR statué ne décide.

#### Scenario: Les objectifs du document et de la découverte divergent

- **GIVEN** un document d'architecture dont les objectifs qualité diffèrent de ceux de la découverte, par leur contenu ou leur ordre
- **WHEN** le document est relu
- **THEN** l'écart est relevé comme un constat critique et corrigé avant la fin du change

#### Scenario: Un ADR resté sans réponse

- **GIVEN** un ADR hérité resté `proposed`
- **WHEN** la section des décisions est rédigée
- **THEN** elle ne le présente pas comme une décision prise
