---
adr: SDR-0003
slug: software-architecture
title: Software Architecture
status: proposed
date:
authors: []
supersedes: []
traits:
  architecture:
    pattern:
    document:
---

# Software Architecture

> **Qu'est-ce que ce fichier ?** Un ADR — *Architecture Decision Record* — est
> une décision consignée : son contexte, les options pesées, ce qui a été
> retenu, et ce que ça coûte. **Tant qu'il porte `status: proposed`, il s'écrit
> et se corrige librement.**
>
> **`rejected` est une réponse pleine, pas un abandon.** Quand la question ne se
> pose pas dans ce dépôt, l'ADR reçoit le verdict `rejected` avec son motif, et le bloc
> `traits:` disparaît en entier — une clé sans objet ne se laisse pas vide. Le
> motif dit alors **ce qui en tient lieu**, pour qu'un agent qui le lit sache à
> quoi s'en tenir. **Un ADR `rejected` sans bloc `traits:` passe la
> vérification** — c'est mesuré, pas supposé.

## Context and Problem Statement

**Concrètement, ce que statuer change.** Tant que cette clé est vide, un agent
qui ajoute un module à ce dépôt invente une structure — et il en invente une
différente à chaque fois, parce qu'il déduit du fichier qu'il a sous les yeux.
Une fois la valeur écrite, il sait où poser le code et ce qui a le droit de
dépendre de quoi.

La question se pose tôt parce qu'elle est chère à défaire : une arborescence et
des frontières de dépendance se changent module par module, longtemps après
qu'on a cessé d'y penser.

**Cet ADR gouverne aussi le sort de `docs/architecture/arc42.md`.** Tant que
ce fichier manque, le premier artefact de chaque change propose de le créer
depuis le gabarit `node_modules/surdesrails/resources/docs/arc42/index.md`. Si
votre architecture vit déjà ailleurs — un document mûr sous un autre chemin —,
ou si vous ne tenez pas de document d'architecture, dites-le par la clé
`architecture.document` : `ailleurs` ou `aucun` font taire la proposition.

## Considered Options

* **`hexagonal`** — ports & adapters : le domaine ne dépend d'aucune I/O.
* **`layered`** — couches classiques, chacune ne connaissant que la suivante.
* **`microservices`** — des services déployés séparément.
* **`monolithic`** — un seul déployable, sans frontière interne forte.
* **`event-driven`** — les composants communiquent par événements.
* **`soa`** — services partagés, couplés par contrats.

## Decision Outcome

**La réponse que la méthode propose, et ses motifs.**

| Clé | Valeur proposée | Motif |
| --- | --- | --- |
| `architecture.pattern` | `hexagonal` | **il convient bien au travail agentique** : le domaine ne dépend d'aucune I/O, donc un agent l'écrit et le teste sans environnement qui tourne, et change un adaptateur sans toucher au domaine |

Le motif mérite d'être développé, parce qu'il n'est pas le motif habituel. Un
pattern hexagonal borne ce qu'un agent doit tenir en tête pour modifier une
règle : le domaine seul, sans base, sans réseau, sans framework. C'est aussi ce
qui rend une modification vérifiable sans monter d'environnement — un agent sait
donc s'il a cassé quelque chose, au lieu de le supposer.

**Cette proposition ne lie pas ce dépôt.** Elle vaut pour un service applicatif de
taille moyenne. Sous 500 lignes, ou pour un dépôt qui n'est pas un service,
`monolithic` est souvent la réponse honnête — et si la question n'a pas d'objet
ici, statuez `rejected`.

**Tout ce qui suit disparaît quand vous statuez** — de cette phrase-ci
**jusqu'au titre** **Consequences**, ce titre non compris.

**Comment statuer : cinq gestes, tous dans ce fichier.** Lisez-les tous
avant d'en faire un seul — le dernier efface les quatre autres —, et faites-les
en **un seul acte, dans une seule merge request**.

1. **Écrire la valeur de chaque clé** dans le `traits:` du frontmatter — ou,
   si vous statuez `rejected`, **retirer le bloc `traits:` en entier**.
2. **Passer `status:`** de `proposed` à `accepted`, ou à `rejected`.
3. **Renseigner `date:` et `authors:`** — `date:` au format `AAAA-MM-JJ`, le
   jour où vous statuez ; `authors:`, les noms des personnes qui ont décidé,
   sans adresse courriel.
4. **Écrire deux ou trois lignes sous le titre Consequences**, à la place du
   commentaire qui s'y trouve : ce que votre décision facilite, et ce qu'elle
   coûte.
5. **En dernier seulement, supprimer ce bloc**, de sa première phrase
   jusqu'au titre Consequences non compris. À sa place : le motif de ce que
   vous avez décidé, partout où vous vous écartez de la proposition ; ou, si
   vous l'adoptez telle quelle, une ligne qui le dit.

**Le premier geste est celui qu'on oublie** : une décision écrite seulement en
prose laisse un agent deviner. **Le titre Consequences n'est pas écrit en
code, et c'est voulu** : la chaîne qui borne la coupe ne doit apparaître
qu'une fois dans ce fichier, sinon qui la cherche coupe au premier faux
positif.

**Ce qui reste**, et rien de tout cela ne s'efface : la proposition de la
méthode et ses motifs, en tête de cette section ; le titre **Consequences** et
ce que vous y écrivez au geste 4 ; et `## More Information`, qui décrit les clés
et sert encore après.

**Cette proposition survit à la coupe** : la perdre appauvrirait cet ADR. Si
vous décidez autrement, remplacez-la par votre décision et son motif.

**Voici à quoi ressemble ce frontmatter une fois rempli.** C'est la seule
part de ce fichier qu'un agent lit sans l'interpréter :

```yaml
---
adr: SDR-0003
slug: software-architecture
title: Software Architecture
status: accepted
date: 2026-03-14
authors: []
supersedes: []
traits:
  architecture:
    pattern: hexagonal
    document: arc42
---
```

**`## Considered Options` ci-dessus est une proposition de l'amont, pas
votre délibération.** La méthode a pesé ces options sans connaître votre
contexte. La confrontation au vôtre reste à faire, et c'est elle qui
distingue une décision d'un défaut accepté.

### Consequences

<!-- Ce que votre décision facilite, et ce qu'elle coûte. Deux ou trois lignes
     suffisent — par exemple sur l'arborescence qu'elle impose, ou sur ce qu'un
     changement de pattern coûterait plus tard. -->

## More Information

| Clé | Ce qu'elle porte | Valeurs admises |
| --- | --- | --- |
| `architecture.pattern` | le pattern qui structure le code de ce dépôt | `event-driven`, `hexagonal`, `layered`, `microservices`, `monolithic`, `soa` |
| `architecture.document` | où vit le document d'architecture de ce dépôt | `arc42` (`docs/architecture/arc42.md`), `ailleurs`, `aucun` |

**Deux clés, et c'est délibéré.** La méthode ne transporte pas votre
arborescence, vos noms de paquets ni vos règles de dépendance : elles se
décident chez vous et se lisent dans ce corps. Le trait ne porte que ce qu'un
agent doit lire sans interpréter.

**La valeur s'écrit dans ce fichier, et nulle part ailleurs.** Aucun autre
fichier ne la recopie : celui qui en a besoin renvoie ici. C'est ce qui garantit
qu'elle ne peut pas être contredite ailleurs.

**Une clé laissée vide n'est pas une réponse** — celle-ci est exigée, et vous n'avez pas à le vérifier
à l'œil. Depuis la racine de votre dépôt :

```bash
( cd docs/adr && npx @jackchuka/mdschema@0.15.1 check '*.md' )
```

**Si votre dépôt n'a ni Node ni `npm`, cette ligne ne vous sert à rien**, et
le dire vaut mieux que le supposer. `mdschema` est un binaire autonome :
prenez-le dans les *releases* de [son dépôt](https://github.com/jackchuka/mdschema)
et lancez `mdschema check '*.md'` depuis ce répertoire. Le raccourci ci-dessus
n'existe que parce que `npx` évite d'installer quoi que ce soit quand Node est
déjà là.

Le schéma qu'elle applique est le `.mdschema.yml` de ce même répertoire, posé
par la méthode. Elle nomme, fichier par fichier : une clé restée vide, une
valeur hors de l'ensemble admis, un `status:` resté `proposed`, une `date:`
absente, et le mode d'emploi qu'on aurait oublié de supprimer. **Elle reconnaît
ce dernier à sa première phrase**, pas au tableau : le tableau a le droit de
rester, et le garder ne déclenche rien. Elle ne juge pas votre décision —
seulement qu'elle est prise.
