# decision-lookup Specification

## Purpose
Ce que `uske decisions` garantit à qui lit le journal : il le lit sans jamais l'écrire, retrouve
les décisions sur une image et ce qui en a été reconstruit, les filtre par état et par jour, et les
rend dans l'ordre du fichier, en JSON, en texte ou en Markdown avec une chronologie Mermaid. Un
journal illisible se signale par son fichier et sa ligne ; rien d'incomplet n'est jamais rendu.

## Requirements

### Requirement: Lire le journal ne le modifie jamais, et dit ce qu'il a lu

`uske decisions` MUST NOT écrire, réécrire ni créer aucun fichier sous `--results`. Elle lit les
fichiers `*.jsonl` du premier niveau de `--results`, sans descendre dans les sous-répertoires ; le
nom d'un fichier, sans `.jsonl`, est le nom de sa politique (son `metadata.name`).
`--policy-name` restreint la lecture au journal de ce nom : la commande tourne à côté du volume,
où le dépôt de politiques n'est pas, et ne demande donc aucun fichier de politique. La commande
SHALL écrire sur la sortie d'erreur chaque fichier lu et son nombre de lignes. Un `--results`
absent ou sans aucun `*.jsonl` MUST faire échouer la commande avec `error:`, le code 1 et un
rappel que `--results` est le répertoire où le volume `uske-results` est monté ; un nom de
politique inconnu MUST la faire échouer en listant les noms présents. « Aucune décision » et
« rien n'a été lu » ne se confondent pas.

#### Scenario: Une lecture laisse le journal intact

- **GIVEN** un répertoire de résultats qui contient deux journaux et un sous-répertoire `reports/`
- **WHEN** `uske decisions --results <dir>` est lancée
- **THEN** le contenu et la date de modification des deux journaux sont inchangés
- **AND** les décisions des deux politiques figurent dans la sortie
- **AND** la sortie d'erreur nomme les deux journaux et leur nombre de lignes, et rien sous `reports/`

#### Scenario: Une seule politique, par son nom

- **GIVEN** la fixture `redis-7` et un second journal dans le même répertoire
- **WHEN** `uske decisions --policy-name a-4711-redis-7` est lancée
- **THEN** seules les décisions de `a-4711-redis-7` figurent dans la sortie

#### Scenario: Un nom de politique inconnu

- **GIVEN** la fixture `redis-7`
- **WHEN** `uske decisions --policy-name redis-7` est lancée
- **THEN** la commande sort avec le code 1 et la sortie d'erreur nomme `a-4711-redis-7` parmi les
  noms présents

#### Scenario: Rien à lire

- **GIVEN** un répertoire de résultats sans aucun `*.jsonl`
- **WHEN** `uske decisions --results <dir>` est lancée
- **THEN** la commande écrit `error:` sur la sortie d'erreur et sort avec le code 1

### Requirement: Retrouver les décisions sur une image et ses reconstructions

`IMAGE` SHALL accepter une référence complète, une empreinte `sha256:…` ou une forme
`<dépôt>@sha256:…`, et la résoudre en l'ensemble des empreintes dont une ligne porte cette `ref` ou
ce `digest`. La sortie MUST contenir les lignes de ces empreintes, de
leurs ascendants (la `source` d'une image retenue, de proche en proche) et de leurs descendants
(les reconstructions d'une source, par `source` et `rebuilt`). Une reconstruction amène ainsi sa
source, la première porte, mais MUST NOT amener ses sœurs, les autres reconstructions de la même
source ; une source amène toutes ses reconstructions. Aucune correspondance approchée n'est tentée : une référence courte
ne correspond à rien. Quand rien ne correspond, la sortie d'erreur SHALL proposer les références
complètes du journal qui finissent par `/<IMAGE>`, ou, à défaut, rappeler que le journal porte des
références complètes ; la sortie standard n'en est pas changée.

#### Scenario: Par référence

- **GIVEN** la fixture `redis-7`
- **WHEN** `uske decisions docker.io/library/redis:7.2.8` est lancée
- **THEN** la sortie contient les deux décisions sur `redis:7.2.8`, la quarantaine puis l'exception
- **AND** aucune décision sur `redis:7.2.6` ni `redis:7.4.1`

#### Scenario: Par empreinte, avec le dépôt

- **GIVEN** la fixture `redis-7`
- **WHEN** `uske decisions docker.io/library/redis@<empreinte de redis:7.2.6>` est lancée
- **THEN** la sortie contient ses deux décisions, `quarantine` puis `abandoned`

#### Scenario: Une source cherchée par sa référence montre ses reconstructions

- **GIVEN** un journal où une image retenue, de référence prise dans le transit, porte `source`
  égal à l'empreinte S de la référence R
- **AND** une ligne de clôture sur S porte `rebuilt` égal à l'empreinte de l'image retenue
- **WHEN** `uske decisions R` est lancée
- **THEN** la sortie contient les lignes de S et celles de l'image retenue, avec son rapport

#### Scenario: Une reconstruction montre sa source, pas ses sœurs

- **GIVEN** un journal où la source S est en `transformation-required`
- **AND** deux images retenues H1 et H2 portent `source` égal à S
- **WHEN** `uske decisions` est lancée avec l'empreinte de H1
- **THEN** la sortie contient les lignes de S et de H1, et pas celles de H2
- **AND** lancée avec l'empreinte de S, elle contient les lignes de S, de H1 et de H2

#### Scenario: Une référence courte

- **GIVEN** la fixture `redis-7`
- **WHEN** `uske decisions redis:7.2.8` est lancée
- **THEN** la sortie JSON est `[]` et la commande sort avec le code 0
- **AND** la sortie d'erreur propose `docker.io/library/redis:7.2.8`

#### Scenario: Une référence que rien ne prolonge

- **GIVEN** la fixture `redis-7`
- **WHEN** `uske decisions nginx:1.27` est lancée
- **THEN** la sortie JSON est `[]` et la sortie d'erreur rappelle que le journal porte des
  références complètes

### Requirement: L'ordre est celui du journal

Les lignes SHALL être rendues groupées par politique puis par empreinte, et, dans un groupe, dans
l'ordre du fichier, qui fait foi puisque le journal n'est qu'en ajout. Les groupes se suivent dans
l'ordre de leur première ligne. Une ligne dont le `ts` est antérieur à celui d'une ligne précédente
du même groupe MUST être marquée comme antidatée en `text` et en `md`, et porter `"backdated": true`
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
- **THEN** cette ligne reste en dernier et porte la marque « antidatée »

### Requirement: Filtrer par état et par date

`--state` SHALL accepter une liste d'états séparés par des virgules et ne garder que les lignes dont
l'`state` en fait partie ; tout état est accepté, y compris un état que `uske` n'écrit pas.
`--since` SHALL accepter une date `AAAA-MM-JJ`, lue comme un jour UTC, et ne garder que les lignes
dont le `ts` tombe ce jour-là ou après. Une date mal formée est une erreur d'usage (code 2) dont le
message donne la forme attendue, `AAAA-MM-JJ`. Les
filtres MUST se cumuler entre eux et avec `IMAGE`.

#### Scenario: Les exceptions d'une période

- **GIVEN** la fixture `redis-7`
- **WHEN** `uske decisions --state placed-by-exception,abandoned --since 2026-09-21` est lancée
- **THEN** la sortie contient la ligne `abandoned` du 2026-09-21 et la ligne `placed-by-exception`
  du 2026-10-09, et rien d'autre

#### Scenario: Une date mal formée

- **WHEN** `uske decisions --results <tmp> --since 21/09/2026` est lancée
- **THEN** la commande sort avec le code 2

#### Scenario: Rien ne correspond

- **GIVEN** la fixture `redis-7`
- **WHEN** `uske decisions --state direct-placement` est lancée
- **THEN** la commande sort avec le code 0 et la sortie JSON est `[]`

### Requirement: Trois formats, JSON par défaut

La sortie par défaut MUST être un tableau JSON des lignes retenues, telles qu'au journal, chacune
augmentée d'une clé `policy`. `--format text` SHALL rendre chaque décision avec son horodatage UTC,
son état, sa raison, son jeu de règles, son rapport, et chaque clé que `uske` n'écrit pas, sous la
forme `clé: valeur` dans l'ordre du fichier — `arbitration` compris, sans que ce change en fixe le
vocabulaire. L'état MUST toujours être rendu avec sa raison, qui lève l'ambiguïté de `quarantine`
(SDR-0016) ; une raison absente se rend `—`. Une ligne dont l'état n'est pas l'un des quatre que
`uske` écrit, ou dont la raison est `uske/reopened`, et qui ne porte pas d'`arbitration`, MUST être
marquée « arbitrage absent ».

#### Scenario: Texte sur la fixture

- **GIVEN** la fixture `redis-7`
- **WHEN** `uske decisions docker.io/library/redis:7.2.8 --format text` est lancée
- **THEN** la sortie est identique au fichier attendu du golden test `text`
- **AND** elle contient `cao-data` et le motif de l'exception

#### Scenario: Une réouverture sans arbitre

- **GIVEN** une ligne `inconclusive` de raison `uske/reopened` sans `arbitration`
- **WHEN** elle est rendue en `text`
- **THEN** elle porte la marque « arbitrage absent »

### Requirement: Le Markdown porte une chronologie Mermaid et le tableau complet

`--format md` SHALL rendre, pour chaque groupe, un titre qui nomme la politique et la référence,
l'empreinte en code, un bloc ```` ```mermaid ```` de type `timeline` dont chaque période est un
criblage, `run <id>` (SDR-0018), et porte les décisions qu'il a écrites ; une ligne sans `run`
(écrite avant SDR-0018, ou à la main) a pour période sa minute UTC `AAAA-MM-JJ HH:MM`. Suit
un tableau Markdown des colonnes du format `text`, dont `run`, rendu en lien quand c'est une URL.
Dans le
bloc Mermaid, titre compris, `#` puis `%`, `:` et `;` MUST être remplacés par leurs entités
(`#35;`, `#37;`, `#58;`, `#59;`) et tout `\r` ou `\n` par une espace. Dans le tableau, `|` MUST
être échappé et tout `\r` ou `\n` remplacé par une espace ; dans le titre et dans le format
`text`, tout `\r` ou `\n` d'une valeur MUST aussi devenir une espace, pour qu'une ligne écrite à
la main ne puisse pas fabriquer une fausse ligne ni un faux titre. Le `report` y SHALL être rendu en code ;
un chemin absolu, sur le volume, SHALL être suivi de `(volume uske-results)` : le lecteur du ticket
ne peut pas l'ouvrir, il doit savoir où il se trouve. Un chemin relatif désigne un fichier rangé à
côté du journal, dans un dépôt de résultats, et se rend sans suffixe.

#### Scenario: Markdown sur la fixture

- **GIVEN** la fixture `redis-7`
- **WHEN** `uske decisions docker.io/library/redis:7.2.8 --format md` est lancée
- **THEN** la sortie est identique au fichier attendu du golden test `md`

#### Scenario: Une colonne par criblage

- **GIVEN** deux lignes d'une même empreinte écrites par le run `https://ci.example/runs/41`, une
  par le run `wf-abc`, et une sans `run`
- **WHEN** elles sont rendues en `md`
- **THEN** la chronologie a trois périodes : `run 41` avec les deux décisions, `run wf-abc`, puis
  la minute UTC de la ligne sans `run`
- **AND** la colonne `run` du tableau porte `[41](https://ci.example/runs/41)` et `wf-abc`

#### Scenario: Des caractères qui cassent le rendu

- **GIVEN** une décision dont la référence contient `:` et dont la raison contient `:`, `#`,
  `;`, `%%`, `|` et un saut de ligne
- **WHEN** elle est rendue en `md`
- **THEN** la sortie est identique au fichier attendu du golden test d'échappement

### Requirement: Un journal illisible se signale, il ne se tait pas

Une ligne de journal qui n'est pas un objet JSON, à qui manque `ts`, `digest` ou `state`, dont
l'une de ces clés, ou `ref`, `reason`, `ruleset`, `report`, `source` ou `rebuilt` si elle est
présente, n'est pas une chaîne, dont le `ts` n'est pas exactement au format `%Y-%m-%dT%H:%M:%SZ` (zéros compris), qui contient
`NaN` ou `Infinity`, ou qui porte déjà une clé `policy`, MUST faire
échouer la commande avec `error:`, le fichier et le numéro de ligne sur la sortie d'erreur, et le
code 1 ; un journal illisible comme fichier (droits, encodage autre qu'UTF-8) aussi, avec son
chemin. Les lignes se séparent sur `\n` seulement : un U+2028 dans une valeur ne coupe pas la
ligne. La commande MUST NOT rendre une sortie partielle qui laisserait croire le journal complet.

#### Scenario: Une ligne corrompue

- **GIVEN** un journal dont la troisième ligne n'est pas du JSON
- **WHEN** `uske decisions --results <dir>` est lancée
- **THEN** la sortie d'erreur nomme ce fichier et la ligne 3
- **AND** la commande sort avec le code 1 sans rien écrire sur la sortie standard

#### Scenario: Une référence qui n'est pas du texte

- **GIVEN** un journal dont une ligne porte `"ref": null`
- **WHEN** `uske decisions --results <dir> --format md` est lancée
- **THEN** la sortie d'erreur nomme ce fichier, cette ligne et la clé `ref`, et la commande sort
  avec le code 1 sans rien écrire sur la sortie standard

#### Scenario: Une ligne écrite à la main sans horodatage valide

- **GIVEN** un journal dont une ligne porte `"ts": "2026-10-09T09:00:00+02:00"`
- **WHEN** `uske decisions --results <dir>` est lancée
- **THEN** la sortie d'erreur nomme ce fichier et cette ligne, et la commande sort avec le code 1
