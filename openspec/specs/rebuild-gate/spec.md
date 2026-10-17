# rebuild-gate Specification

## Purpose
Ce qu'un screening garantit d'une image que le placeur construit : elle est retenue dans un
transit et jugée par sa propre empreinte avant toute destination, promue seulement sur un
placement direct, et sa reconstruction n'est tentée qu'une fois par empreinte source quand elle
est refusée. Chacune de ces décisions est consignée au journal, qui n'avance que vers l'avant.

## Requirements

### Requirement: Une source à réparer n'est rendue au placeur que s'il dit qu'il la reconstruira

Le screening MUST NOT rendre au placeur une opération dont l'empreinte source est en
`transformation-required`, sauf si le plan du placeur déclare que cette opération sera
reconstruite et que le screening a nommé un transit au filtrage. Une opération que le plan ne déclare pas reconstruite MUST être tenue pour une
copie. Une source en `direct-placement` reste rendue, reconstruite ou non. `uske` ne déduit jamais
lui-même, de la politique, ce qui sera reconstruit.

#### Scenario: Une source à réparer, que le placeur reconstruira

- **GIVEN** une empreinte source dont le dernier état au journal est `transformation-required`
- **AND** un plan dont l'opération sur cette empreinte est déclarée reconstruite
- **WHEN** le plan est filtré
- **THEN** l'opération figure dans le plan rendu au placeur

#### Scenario: Une source à réparer, que le placeur copierait

- **GIVEN** une empreinte source dont le dernier état au journal est `transformation-required`
- **AND** un plan dont l'opération sur cette empreinte est déclarée non reconstruite
- **WHEN** le plan est filtré
- **THEN** l'opération est retirée du plan rendu au placeur

#### Scenario: Un plan qui ne dit rien de la reconstruction

- **GIVEN** une empreinte source dont le dernier état au journal est `transformation-required`
- **AND** un plan écrit par un placeur qui ne déclare pas ce qu'il reconstruit
- **WHEN** le plan est filtré
- **THEN** l'opération est retirée du plan rendu au placeur

#### Scenario: Un screening qui ne nomme pas de transit

- **GIVEN** une empreinte source dont le dernier état au journal est `transformation-required`
- **AND** un plan dont l'opération sur cette empreinte est déclarée reconstruite
- **WHEN** le plan est filtré sans qu'un transit soit nommé
- **THEN** l'opération est retirée du plan rendu au placeur

#### Scenario: Une source saine sur une politique qui reconstruit

- **GIVEN** une empreinte source dont le dernier état au journal est `direct-placement`
- **AND** un plan dont l'opération sur cette empreinte est déclarée reconstruite
- **WHEN** le plan est filtré
- **THEN** l'opération figure dans le plan rendu au placeur

### Requirement: Tout ce que le placeur construit est retenu dans le transit

À chaque application d'un plan, pour toute politique, le screening SHALL nommer au placeur un
transit où retenir ce qu'il construit, et lui demander la liste des images retenues. Le screening
MUST NOT appliquer un plan sans transit : un déploiement qui n'en déclare pas ne place rien. Une
image copiée n'est pas retenue : ses couches sont celles de la source déjà jugée.

#### Scenario: Une politique qui reconstruit

- **GIVEN** une politique qui déclare une transformation, et une opération approuvée
- **WHEN** le plan filtré est appliqué
- **THEN** l'image construite se trouve dans le transit et figure dans la liste des images retenues
- **AND** la destination est inchangée

#### Scenario: Une politique en voie copie

- **GIVEN** une politique qui ne déclare aucune transformation, et une opération approuvée
- **WHEN** le plan filtré est appliqué
- **THEN** l'image est placée dans sa destination comme avant ce change
- **AND** la liste des images retenues est vide, et rien n'est promu

#### Scenario: Un déploiement sans transit

- **GIVEN** un déploiement dont la liste de registres du placeur ne déclare pas le transit nommé
- **WHEN** un plan filtré non vide est appliqué
- **THEN** l'application échoue, et aucune image n'est placée ni retenue

### Requirement: Une image retenue n'atteint sa destination que sur son propre verdict

Chaque image retenue encore due d'une décision SHALL être jugée par sa propre empreinte, dans le
transit, avec le jeu de règles que le régime de la politique appelle. Le fichier rendu au placeur
pour la promotion MUST NOT nommer une image retenue dont le dernier état n'est pas
`direct-placement`. Un verdict absent, illisible ou non concluant vaut refus de promotion.

#### Scenario: La reconstruction a réparé

- **GIVEN** une image retenue dont le verdict est `direct-placement`
- **WHEN** la liste des images retenues est filtrée
- **THEN** son entrée figure dans le fichier rendu au placeur pour la promotion

#### Scenario: La reconstruction n'a pas suffi

- **GIVEN** une image retenue dont le verdict est `transformation-required` ou `quarantine`
- **WHEN** la liste des images retenues est filtrée
- **THEN** son entrée est retirée du fichier rendu au placeur
- **AND** la destination est inchangée

#### Scenario: Le juge ne conclut pas

- **GIVEN** une image retenue dont le jugement échoue ou ne rend aucun verdict lisible
- **WHEN** la liste des images retenues est filtrée
- **THEN** son entrée est retirée du fichier rendu au placeur

#### Scenario: Une image retenue déjà décidée

- **GIVEN** une image retenue dont l'empreinte porte déjà un état décidé au journal
- **WHEN** les images retenues encore dues sont listées
- **THEN** elle n'y figure pas, et le juge n'est pas appelé pour elle

### Requirement: Le verdict d'une image retenue est consigné, avec la source dont elle vient

Chaque image retenue jugée SHALL laisser une ligne au journal, sous sa propre empreinte, avec les
clés de toute ligne de décision — date, référence, état, jeu de règles, raison, rapport — et une
clé `source` qui porte l'empreinte de sa source. Cette ligne s'ajoute et ne se réécrit jamais. Le
rapport qu'elle désigne MUST survivre au screening.

#### Scenario: Partir de la source pour retrouver l'image reconstruite

- **GIVEN** un journal où une image retenue a été jugée
- **WHEN** une personne cherche les lignes dont la clé `source` vaut l'empreinte de la source
- **THEN** elle trouve la ligne de l'image retenue, son état, sa raison et son rapport

#### Scenario: Rejouer la seconde porte

- **GIVEN** un screening dont les images retenues ont déjà été consignées
- **WHEN** l'étape de consignation est rejouée sur les mêmes lignes
- **THEN** aucune ligne n'est ajoutée au journal

### Requirement: Une reconstruction refusée clôt sa source, et n'est tentée qu'une fois

Quand une image retenue reçoit un verdict décidé autre que `direct-placement`, le screening SHALL
ajouter au journal, après la ligne de l'image retenue, une ligne sur l'empreinte source :
`state: quarantine`, `reason: uske/rebuild-refused`, la référence de la source, le jeu de règles
qui a jugé l'image retenue, son rapport, et une clé `rebuilt` qui porte son empreinte. Une source
ainsi close MUST NOT être rendue au placeur ni rejugée aux screenings suivants, quelles que soient
les lignes rejouées : le journal MUST NOT accepter une ligne dont la date précède la dernière
ligne du même digest. Cette clôture dit que la reconstruction a été refusée ; elle n'est pas une
quarantaine prononcée par le juge sur la source. Un verdict non concluant ne clôt rien : la source
reste approuvable.

#### Scenario: Le refus s'écrit deux fois

- **GIVEN** une image retenue dont le verdict est `transformation-required` ou `quarantine`
- **WHEN** ce verdict est consigné
- **THEN** le journal gagne la ligne de l'image retenue, puis une ligne `quarantine` de raison
  `uske/rebuild-refused` sur l'empreinte source

#### Scenario: Le screening suivant ne retente pas

- **GIVEN** une empreinte source close par une ligne `uske/rebuild-refused`
- **AND** un plan qui porte de nouveau une opération reconstruite sur cette empreinte
- **WHEN** le screening suivant tourne
- **THEN** le juge n'est pas appelé pour cette empreinte, et l'opération est retirée du plan rendu
  au placeur

#### Scenario: La ligne de première porte est rejouée après la clôture

- **GIVEN** une empreinte source close par une ligne `uske/rebuild-refused`
- **WHEN** l'étape de consignation de la première porte est rejouée, avec la ligne d'origine de
  la source
- **THEN** aucune ligne n'est ajoutée sur l'empreinte source, qui reste close

#### Scenario: Une source saine dont la reconstruction est refusée

- **GIVEN** une empreinte source en `direct-placement`, dont une variante est copiée et une autre
  reconstruite
- **WHEN** l'image retenue de la variante reconstruite est refusée
- **THEN** la source est close par une ligne `uske/rebuild-refused`
- **AND** la copie déjà placée reste en service

#### Scenario: Un verdict non concluant se rejoue

- **GIVEN** une image retenue dont le verdict est `inconclusive`
- **WHEN** ce verdict est consigné, puis que le screening suivant tourne
- **THEN** aucune ligne n'est écrite sur l'empreinte source
- **AND** l'opération sur cette source est de nouveau rendue au placeur

#### Scenario: Une règle que le juge n'a pas su lire ne clôt rien

- **GIVEN** une image retenue dont aucune règle critique n'échoue, et dont une règle est restée
  incomplète
- **WHEN** ce verdict est consigné
- **THEN** l'image retenue est consignée `inconclusive`, avec cette règle pour raison
- **AND** aucune ligne n'est écrite sur l'empreinte source

#### Scenario: Une réparation réussie ne clôt rien

- **GIVEN** une image retenue dont le verdict est `direct-placement`
- **WHEN** ce verdict est consigné
- **THEN** le journal ne gagne que la ligne de l'image retenue

### Requirement: Les essais sans verdict sont bornés, et une ligne rouvre une source

Le screening MUST NOT rendre au placeur une opération reconstruite dont l'empreinte source compte
déjà trois lignes d'images retenues non concluantes, écrites depuis la dernière ligne sur cette
empreinte source. Il n'écrit alors rien. Une image retenue jugée saine ne compte pas. Une ligne `state: inconclusive`, `reason: uske/reopened`, ajoutée sur une
empreinte source, SHALL la rendre due de nouveau, qu'elle ait été close ou bornée, et remettre le
compte à zéro.

#### Scenario: Le juge reste muet trois screenings de suite

- **GIVEN** une empreinte source dont trois images retenues successives ont reçu `inconclusive`
- **WHEN** le plan du screening suivant est filtré
- **THEN** l'opération sur cette source est retirée du plan rendu au placeur
- **AND** aucune ligne n'est écrite sur l'empreinte source

#### Scenario: Trois variantes réparées n'épuisent pas leur source

- **GIVEN** une empreinte source dont trois images retenues ont reçu `direct-placement`
- **WHEN** un plan porte de nouveau une opération reconstruite sur cette source
- **THEN** l'opération est rendue au placeur

#### Scenario: Rouvrir une source close

- **GIVEN** une empreinte source close par une ligne `uske/rebuild-refused`
- **WHEN** une ligne `inconclusive` de raison `uske/reopened`, datée du geste, est ajoutée sur
  cette empreinte
- **THEN** le screening suivant la fait rejuger
- **AND** si elle ressort à réparer, son opération reconstruite est de nouveau rendue au placeur

### Requirement: Une panne n'emporte pas ce qui a réussi

Une opération en échec MUST NOT empêcher de juger ni de promouvoir les images que le placeur a
retenues malgré elle. Le screening d'une politique dont une application ou une promotion a échoué
SHALL finir en échec, pour que la panne se voie. Une panne MUST NOT écrire de décision au
journal : seul un verdict en écrit.

#### Scenario: Une construction casse, les autres sont retenues

- **GIVEN** un plan filtré de deux opérations reconstruites, dont l'une échoue à l'application
- **WHEN** le screening se poursuit
- **THEN** l'image retenue de l'autre est jugée et, si elle est saine, promue
- **AND** le screening de la politique finit en échec

#### Scenario: Une promotion échoue

- **GIVEN** une image retenue en `direct-placement` dont la promotion échoue
- **WHEN** le screening se termine, puis que le suivant tourne
- **THEN** aucune ligne n'a été écrite sur son empreinte source
- **AND** l'opération sur cette source est de nouveau rendue au placeur

#### Scenario: Aucune liste d'images retenues

- **GIVEN** un screening où le placeur n'a écrit aucune liste d'images retenues
- **WHEN** les images retenues encore dues sont listées, puis filtrées
- **THEN** aucune n'est due, et le fichier rendu au placeur pour la promotion ne nomme rien

### Requirement: Une réparation se renouvelle sur le tag qu'elle a réparé

Quand le plan du placeur marque une opération `remediated: true` (le tag de destination qu'elle
remplace porte une réparation), le screening SHALL la rendre au placeur avec un ordre de
remédiation sous l'epoch du screening, même si la source est en `direct-placement`. Sans transit
nommé, cette opération MUST être retirée du plan rendu au placeur, et sa source consignée
`inconclusive`, raison `uske/no-transit` : la placer sans ordre déferait la réparation. Une source
refusée, close ou dont les essais sont épuisés reste retirée, comme sans la marque. Une opération
sans la clé `remediated` MUST être tenue pour non marquée. Le screening ne déduit jamais lui-même,
de la destination, qu'un tag a été réparé.

#### Scenario: Un correctif amont sur un tag réparé

- **GIVEN** une source en `direct-placement`, et un plan dont l'opération sur cette source porte
  `remediated: true`
- **WHEN** le plan est filtré avec un transit nommé
- **THEN** l'opération figure dans le plan rendu au placeur avec `remediate: {epoch: <epoch du
  screening>}`

#### Scenario: Un tag réparé, sans transit

- **GIVEN** une source en `direct-placement`, et un plan dont l'opération sur cette source porte
  `remediated: true`
- **WHEN** le plan est filtré sans transit
- **THEN** l'opération est retirée du plan rendu au placeur
- **AND** le journal gagne une ligne `inconclusive` de raison `uske/no-transit` sur la source

#### Scenario: Un tag jamais réparé

- **GIVEN** une source en `direct-placement`, et un plan dont l'opération ne porte pas
  `remediated`
- **WHEN** le plan est filtré avec un transit nommé
- **THEN** l'opération figure dans le plan rendu au placeur, sans ordre de remédiation

#### Scenario: Un tag réparé dont la nouvelle source est refusée

- **GIVEN** une source en `quarantine`, et un plan dont l'opération sur cette source porte
  `remediated: true`
- **WHEN** le plan est filtré avec un transit nommé
- **THEN** l'opération est retirée du plan rendu au placeur
