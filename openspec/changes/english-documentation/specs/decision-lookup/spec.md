## MODIFIED Requirements

### Requirement: L'ordre est celui du journal

Les lignes SHALL être rendues groupées par politique puis par empreinte, et, dans un groupe, dans
l'ordre du fichier, qui fait foi puisque le journal n'est qu'en ajout. Les groupes se suivent dans
l'ordre de leur première ligne. Une ligne dont le `ts` est antérieur à celui d'une ligne précédente
du même groupe MUST porter la marque `backdated` en `text` et en `md`, et porter `"backdated": true`
en `json`.

#### Scenario: Une même empreinte sous deux politiques

- **GIVEN** une empreinte en `quarantine` dans le journal de la politique A
- **AND** la même empreinte en `placed-by-exception` dans le journal de la politique B
- **WHEN** elle est rendue en `text`
- **THEN** les deux décisions sont dans deux groupes distincts, chacun titré par sa politique

#### Scenario: Une exception ajoutée après coup et antidatée

- **GIVEN** un groupe dont la dernière ligne du fichier porte un `ts` antérieur à la ligne
  précédente
- **WHEN** il est rendu en `text`
- **THEN** cette ligne reste en dernier et porte la marque `backdated`

### Requirement: Trois formats, JSON par défaut

La sortie par défaut MUST être un tableau JSON des lignes retenues, telles qu'au journal, chacune
augmentée d'une clé `policy`. `--format text` SHALL rendre chaque décision avec son horodatage UTC,
son état, sa raison, son jeu de règles, son rapport, et chaque clé que `uske` n'écrit pas, sous la
forme `clé: valeur` dans l'ordre du fichier — `arbitration` compris, sans que ce change en fixe le
vocabulaire. L'état MUST toujours être rendu avec sa raison, qui lève l'ambiguïté de `quarantine`
(SDR-0016) ; une raison absente se rend `—`. Une ligne dont l'état n'est pas l'un des quatre que
`uske` écrit, ou dont la raison est `uske/reopened`, et qui ne porte pas d'`arbitration`, MUST être
marquée `no arbitration`.

#### Scenario: Texte sur la fixture

- **GIVEN** la fixture `redis-7`
- **WHEN** `uske decisions docker.io/library/redis:7.2.8 --format text` est lancée
- **THEN** la sortie est identique au fichier attendu du golden test `text`
- **AND** elle contient `cao-data` et le motif de l'exception

#### Scenario: Une réouverture sans arbitre

- **GIVEN** une ligne `inconclusive` de raison `uske/reopened` sans `arbitration`
- **WHEN** elle est rendue en `text`
- **THEN** elle porte la marque `no arbitration`

