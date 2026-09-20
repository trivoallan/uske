---
adr: SDR-0007
slug: tests
title: Tests
status: proposed
date:
authors: []
supersedes: []
traits:
  tests:
    coverage_target:
---

# Tests

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
qui ajoute du code à ce dépôt ne sait pas quel niveau de couverture tenir — il
n'en vise donc aucun, et livre du code testé au hasard de ce qui lui a semblé
utile. Une fois la valeur écrite, il sait ce qu'il doit atteindre avant de
proposer sa merge request.

La méthode impose déjà **le TDD** et **trois bornes fermées** à ce que
« couverture » veut dire. Ce qui reste à vous : le **chiffre**, parce qu'il
dépend de ce que ce dépôt fait et de ce que votre équipe défend en revue.

## Considered Options

* **Un seuil chiffré** — celui que votre équipe tient et sait défendre.
* **`aucun`** — pour un langage sans instrument de couverture, ou pour un dépôt
  où la mesure n'apprendrait rien. **C'est une réponse**, et elle se justifie
  dans ce corps comme une autre.

## Decision Outcome

**La réponse que la méthode propose, et ses motifs.**

| Clé | Valeur proposée | Motif |
| --- | --- | --- |
| `tests.coverage_target` | `90` | c'est le seuil que la méthode tient pour elle-même, et les trois bornes ci-dessous le rendent atteignable sans tricher |

**Les trois bornes ne se négocient pas**, et c'est ce qui rend le chiffre
comparable d'un dépôt à l'autre :

1. **tests unitaires seulement** — un harnais d'intégration ne compte pas ;
2. **code écrit à la main** — hors tests, hors sorties engendrées, hors
   gabarits ;
3. **couverture de lignes**.

**Cette proposition ne lie pas ce dépôt.** Un dépôt qui vise plus haut le dit ; un dépôt
qui vise plus bas le dit aussi, et écrit pourquoi. Ce qui n'est pas une réponse,
c'est un chiffre qu'on ne tient pas.

**Le seuil vaut pour le langage principal**, celui que
[`SDR-0004`](SDR-0004-languages.md) déclare. Un dépôt qui en porte plusieurs
déclare les autres dans ce corps, avec leur instrument — la clé n'en porte
qu'un, parce qu'un agent n'a besoin que de celui-là pour savoir où il en est.

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
adr: SDR-0007
slug: tests
title: Tests
status: accepted
date: 2026-03-14
authors: []
supersedes: []
traits:
  tests:
    coverage_target: 90
---
```

**`## Considered Options` ci-dessus est une proposition de l'amont, pas
votre délibération.** La méthode a pesé ces options sans connaître votre
contexte. La confrontation au vôtre reste à faire, et c'est elle qui
distingue une décision d'un défaut accepté.

### Consequences

<!-- Ce que votre décision facilite, et ce qu'elle coûte. Deux ou trois lignes
     suffisent — par exemple sur le temps de mise à niveau d'un code existant,
     ou sur ce qu'un seuil élevé coûte à la vitesse de livraison. -->

## More Information

| Clé | Ce qu'elle porte | Valeurs admises |
| --- | --- | --- |
| `tests.coverage_target` | le seuil de couverture du langage principal, en pourcentage | un nombre, ou `aucun` |

**Ce que cette clé ne couvre pas** : ni runner, ni commande de test, ni sortie
attendue, ni instrument de couverture. La méthode ne les transporte pas — elle
ne sait pas ce que votre dépôt lance. Déclarez-les dans la section `## Testing`
de votre contexte agent, qu'aucune mise à jour ne réécrit.

**La valeur s'écrit dans ce fichier, et nulle part ailleurs.** Aucun autre
fichier ne la recopie : celui qui en a besoin renvoie ici. C'est ce qui garantit
qu'elle ne peut pas être contredite ailleurs.

**Une clé laissée vide n'est pas une réponse** — celle-ci est exigée. `aucun`
en est une, le vide non.

**Et sur ce point précis, la commande ne vous protège pas.** Elle sait refuser
une valeur hors d'un ensemble fermé — c'est ce qu'elle fait pour l'architecture
ou pour les langues. Ici la valeur est un **nombre ou le mot `aucun`** : aucun
type ne couvre les deux, donc **une clé restée vide passe au vert**. C'est la
relecture qui l'attrape, et il vaut mieux le savoir que le découvrir.

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
