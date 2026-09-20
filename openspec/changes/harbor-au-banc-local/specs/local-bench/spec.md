## ADDED Requirements

### Requirement: Le banc sait éprouver l'API du registre cible

Le banc local SHALL pouvoir monter le registre réellement visé, et non un tenant-lieu, de sorte
que toute sous-commande qui parle à l'API de ce registre s'exerce ailleurs que contre un double de
test. Une sous-commande qu'aucun banc n'exerce n'est pas tenue pour éprouvée.

#### Scenario: Mesurer le contournement contre un registre réel

- **GIVEN** un banc monté dans sa variante qui installe le registre cible
- **WHEN** la sous-commande qui recense la flotte est lancée contre lui
- **THEN** elle rend un rapport obtenu de l'API du registre, sans aucun double de test

#### Scenario: Le tenant-lieu ne prétend rien

- **GIVEN** un banc monté dans sa variante par défaut, qui installe le tenant-lieu
- **WHEN** la même sous-commande est lancée
- **THEN** elle échoue, et cet échec ne se lit pas comme un défaut de la sous-commande

### Requirement: Le banc par défaut reste léger et inchangé

La variante lourde SHALL être optionnelle : la commande de montage sans argument garde le
tenant-lieu, son unique conteneur et son temps de démarrage. Un banc qu'on hésite à lancer ne
sert plus à rien.

#### Scenario: Monter le banc comme avant

- **GIVEN** le dépôt
- **WHEN** le banc est monté sans argument
- **THEN** le tenant-lieu est installé, et le déroulé du screening est celui d'avant ce change

#### Scenario: Demander la variante

- **GIVEN** le dépôt
- **WHEN** le banc est monté avec l'argument qui nomme le registre cible
- **THEN** le registre cible est installé à la place du tenant-lieu, et le tenant-lieu n'est pas
  déployé

### Requirement: Les droits d'écriture sont séparés des droits de lecture

Dans la variante qui monte le registre cible, le banc SHALL employer des identités distinctes pour
lire et pour écrire, et l'identité d'administration ne SHALL être employée que par le montage.
C'est la forme que prendront les secrets d'un environnement réel ; un banc où tout s'écrit avec le
même compte ne l'annonce pas.

#### Scenario: L'outil qui place écrit là où il doit

- **GIVEN** un banc monté dans sa variante avec le registre cible
- **WHEN** l'outil qui place une image y pousse
- **THEN** il emploie une identité dont les droits d'écriture ne portent que sur les projets de
  destination

#### Scenario: L'administration ne sort pas du montage

- **GIVEN** le même banc, une fois monté
- **WHEN** on examine ce que reçoivent les charges de travail
- **THEN** aucune ne reçoit l'identité d'administration

### Requirement: Le banc reste jetable et reproductible d'une commande

Chaque variante SHALL se monter d'une seule commande et se détruire d'une seule autre, sans état
qui survive au cluster. Un banc qui demande une suite de gestes cesse d'être rejouable, et ce qu'il
prouve cesse d'être reproductible.

#### Scenario: Monter, puis détruire

- **GIVEN** un poste sans cluster
- **WHEN** le banc est monté d'une commande dans l'une ou l'autre variante, puis détruit d'une
  commande
- **THEN** rien de ce que le registre a stocké ne subsiste

#### Scenario: Le screening tient dans la variante

- **GIVEN** un banc monté dans sa variante avec le registre cible
- **WHEN** un screening est lancé à la main
- **THEN** il va au bout, et les signatures de l'image placée se vérifient comme dans la variante
  par défaut
