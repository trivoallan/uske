---
adr: SDR-0006
slug: commits
title: Commits
status: proposed
date:
authors: []
supersedes: []
traits:
  commits:
    scopes:
    tool:
---

# Commits

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

**Concrètement, ce que statuer change.** Tant que ces clés sont vides, un agent
qui rédige un message de commit **invente une portée** — `fix(api)`, puis
`fix(backend)`, puis `fix(server)` pour le même endroit. L'historique devient
illisible par filtre, et une release engendrée depuis les messages range mal.
Une fois la liste écrite, il choisit dedans.

**Le format, lui, ne se décide pas ici.** La méthode impose
[Conventional Commits](https://www.conventionalcommits.org/) et ses onze types ; ce qui vous revient est le **vocabulaire des
portées** de ce dépôt, et **l'outil** qui le tient — ou son absence.

**Ce que `rejected` veut dire dans cet ADR**, du coup : que vous ne nommez ni
portées ni outil — pas que vous refusez le format, qui ne dépend pas de vous.
Un dépôt d'une seule zone sans pipeline est le cas type.

## Considered Options

* **Une liste fermée de portées** — un mot par zone du dépôt, décidé une fois.
* **Aucune portée** — `feat:` sans parenthèse. Réponse tenable pour un dépôt à
  une seule zone ; écrivez `[]`, pas rien.
* **`commitlint`** — la référence, branchée en CI : elle refuse la merge
  request, donc elle protège aussi ce qui arrive par la forge.
* **`hook`** — un contrôle local, avant le commit. Il vous prévient plus tôt,
  mais il ne voit pas ce qui est poussé depuis une machine qui ne l'a pas.
* **Aucun outil** — la relecture tient la convention, comme chez la méthode.

## Decision Outcome

**Ce que la méthode fixe, et qui n'est pas négociable :** le format
[Conventional Commits](https://www.conventionalcommits.org/), ses **onze
types** — `feat`, `fix`, `docs`, `style`, `refactor`, `perf`,
`test`, `build`, `ci`, `chore`, `revert` — et la syntaxe de rupture. C'est la
seule chose qui rende un historique comparable d'un dépôt à l'autre.

**La réponse que la méthode propose sur l'outil, et ses motifs.**

| Clé | Valeur proposée | Motif |
| --- | --- | --- |
| `commits.tool` | `commitlint` | **si ce dépôt engendre ses versions depuis les messages** — un message hors format produit alors une version fausse, que la relecture n'attrape pas de façon fiable |

**Vérifiez d'abord ce présupposé** : si vos versions se posent à la main, la
recommandation tombe et `aucun` est une réponse aussi bonne. C'est le pivot du
motif, et il ne vaut que pour les dépôts qu'il décrit.

**La méthode répond `aucun` pour elle-même**, et ce n'est pas une contradiction :
elle n'a pas de pipeline et n'engendre pas de version. Un dépôt applicatif en a
une. La réponse dépend donc de ce que vous faites, pas de ce qu'elle fait.

**Sur `commits.scopes`, la méthode n'a pas de réponse à proposer**, et c'est une
information : les portées nomment **vos** zones, et elle ne les connaît pas. Une
liste par défaut serait un aveu déguisé en recommandation. Écrivez un mot par
zone que vous voulez pouvoir filtrer, et pas un de plus. **`[]` reste une
réponse pleine** : un dépôt d'une seule zone n'a rien à nommer, et une liste
inventée à l'adoption vieillit plus mal qu'une liste absente.

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
adr: SDR-0006
slug: commits
title: Commits
status: accepted
date: 2026-03-14
authors: []
supersedes: []
traits:
  commits:
    scopes: [api, web, infra]
    tool: commitlint
---
```

**`## Considered Options` ci-dessus est une proposition de l'amont, pas
votre délibération.** La méthode a pesé ces options sans connaître votre
contexte. La confrontation au vôtre reste à faire, et c'est elle qui
distingue une décision d'un défaut accepté.

### Consequences

<!-- Ce que votre décision facilite, et ce qu'elle coûte. Deux ou trois lignes
     suffisent — par exemple sur ce qu'une portée oubliée coûte à ajouter plus
     tard, ou sur le frein qu'un outil qui refuse met à un commit pressé. -->

## More Information

| Clé | Ce qu'elle porte | Valeurs admises |
| --- | --- | --- |
| `commits.scopes` | les portées admises dans ce dépôt | une liste de mots, ou `[]` |
| `commits.tool` | ce qui tient la convention, et **où** | `commitlint` en CI, `hook` en local, ou `aucun` |

**Ce que ces clés ne couvrent pas** : ni les onze types, ni la syntaxe de
rupture — ils viennent de la méthode et ne se déclarent pas ici. La liste
opposable des types vit dans le corpus, pas dans ce fichier.

**La valeur s'écrit dans ce fichier, et nulle part ailleurs.** Aucun autre
fichier ne la recopie : celui qui en a besoin renvoie ici. C'est ce qui garantit
qu'elle ne peut pas être contredite ailleurs.

**Une clé laissée vide n'est pas une réponse** — les deux sont exigées. `[]` et
`aucun` en sont, le vide non.

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
