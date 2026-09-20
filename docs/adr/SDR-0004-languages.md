---
adr: SDR-0004
slug: languages
title: Languages
status: proposed
date:
authors: []
supersedes: []
traits:
  languages:
    main:
      name:
---

# Languages

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
qui ajoute du code à ce dépôt ne sait pas dans quel langage l'écrire — il déduit
de ce qu'il voit, et se trompe dès qu'un dépôt en porte plusieurs. Une fois la
valeur écrite, il la lit et s'y tient.

Le langage principal n'est pas le seul langage du dépôt : c'est celui dans lequel
on écrit par défaut, et celui dont l'outillage fait référence. Un dépôt peut en
porter d'autres sans que ça change la réponse.

## Considered Options

* **`Python`** — outillage de test et de typage mûr, forte disponibilité de
  compétences.
* **`Go`** — un seul binaire à déployer, compilation rapide, concurrence simple.
* **`TypeScript`** — un seul langage du navigateur au serveur, typage graduel.
* **Un autre langage** — possible, et à justifier dans ce fichier : ce que la
  liste ci-dessus ne vous donnait pas, et ce que l'équipe sait déjà en tenir.
* **Aucun langage principal** — pour un dépôt de documentation, de
  configuration ou d'infrastructure. Statuez alors `rejected`.

## Decision Outcome

**La méthode ne choisit pas pour vous, mais elle borne le champ.** Trois
langages sont recommandés — `Python`, `Go`, `TypeScript` — parce que l'équipe
en tient l'outillage et sait les relire. Aucun des trois n'est meilleur que les
autres dans l'absolu ; le bon est celui que votre équipe tient déjà.

**Un autre langage reste possible, et se justifie ici** — pas ailleurs, pas en
réunion. Écrivez ce que la liste ne vous donnait pas. C'est la seule chose que
la méthode vous demande en échange de sa liberté.

**Rien de tout cela n'est vérifié par un outil.** Le schéma s'assure qu'une
valeur est écrite, jamais qu'elle est dans la liste : refuser mécaniquement un
langage hors liste rendrait impossible le cas que cette section autorise
justement. C'est la relecture qui lit votre justification, pas une commande.

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
adr: SDR-0004
slug: languages
title: Languages
status: accepted
date: 2026-03-14
authors: []
supersedes: []
traits:
  languages:
    main:
      name: python
---
```

**`## Considered Options` ci-dessus est une proposition de l'amont, pas
votre délibération.** La méthode a pesé ces options sans connaître votre
contexte. La confrontation au vôtre reste à faire, et c'est elle qui
distingue une décision d'un défaut accepté.

### Consequences

<!-- Ce que votre décision facilite, et ce qu'elle coûte. Deux ou trois lignes
     suffisent — par exemple sur le choix d'outillage qu'elle entraîne, ou sur
     ce qu'un second langage coûterait. -->

## More Information

| Clé | Ce qu'elle porte | Valeurs admises |
| --- | --- | --- |
| `languages.main.name` | le langage principal, tel qu'un humain l'écrit | `Python`, `Go`, `TypeScript` — ou un autre, justifié ci-dessus |

**Ce que cette clé ne couvre pas** : ni runner, ni commande de test, ni seuil de
couverture, ni commande de lint, ni instrument. Le seuil de couverture fera
l'objet d'un ADR hérité dédié aux tests ; les commandes, elles, ne se
transportent pas. La méthode ne les transporte pas — elle ne sait
pas ce que votre dépôt lance. Déclarez-les dans `CLAUDE.local.md`, qu'aucune
mise à jour ne réécrit.

**La valeur s'écrit dans ce fichier, et nulle part ailleurs.** Aucun autre
fichier ne la recopie : celui qui en a besoin renvoie ici. C'est ce qui garantit
qu'elle ne peut pas être contredite ailleurs.

**Une clé laissée vide n'est pas une réponse** — les deux sont exigées, et vous n'avez pas à le vérifier
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
