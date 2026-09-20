---
adr: SDR-0007
slug: tests
title: Tests
status: accepted
date: 2026-09-20
authors: [Tristan Rivoallan]
supersedes: []
traits:
  tests:
    coverage_target: 90
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

**Décision de ce dépôt — 2026-09-20.** La proposition de la méthode est adoptée telle quelle,
avec ses trois bornes. `aucun` a été proposé et écarté par la personne qui statue.

- `tests.coverage_target` : répondue — 2026-09-20

**Ce que le dépôt fait aujourd'hui, et qui s'en écarte** : la chaîne lance les tests sans
instrument de couverture ; la couverture réelle n'est pas connue. Tant qu'elle n'est pas
mesurée, ce chiffre est un engagement, pas un constat.

### Consequences

Un agent sait quel niveau tenir avant de proposer sa demande de fusion. Le coût : un instrument
à brancher, une mesure à prendre, et sans doute des tests à écrire — au premier change qui
touche au code. Si la mesure montre que le chiffre ne se tient pas, un nouvel ADR le dit plutôt
que de le laisser mentir.

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
