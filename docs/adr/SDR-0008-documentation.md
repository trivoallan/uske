---
adr: SDR-0008
slug: documentation
title: Documentation
status: proposed
date:
authors: []
supersedes: []
traits:
  docs:
    tool:
    root:
    audience:
---

# Documentation

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
qui doit écrire une page ne sait pas **où la poser**, ni **s'il doit toucher à
une navigation**, ni **ce qu'il a le droit d'y écrire**. Il pose le fichier au
jugé, laisse un sommaire périmé derrière lui, et peut publier une URL interne
dans une page que le monde lit. Une fois ces quatre valeurs écrites, il sait.

**Le classement, lui, ne se décide pas ici.** La méthode impose
[Diataxis](https://diataxis.fr/) — tutoriel, guide, explication, référence — et
le Google developer documentation style pour la prose. Ce qui vous revient est
l'**outillage**, l'**emplacement** et l'**audience**.

## Considered Options

* **Un site engendré, navigation automatique** — la page suffit, l'outil
  s'occupe du reste.
* **Un site engendré, navigation tenue à la main** — plus de contrôle sur
  l'ordre, un fichier de plus à maintenir à chaque page.
* **Pas de site** — les fichiers se lisent sur la forge. Réponse tenable, et
  fréquente pour un dépôt qui n'a pas de lecteurs extérieurs.

## Decision Outcome

**La réponse que la méthode propose, et ses motifs.**

| Clé | Valeur proposée | Motif |
| --- | --- | --- |
| `docs.tool` | `docusaurus` | c'est ce que la méthode utilise, et sa navigation **s'engendre depuis l'arborescence** : ajouter une page ne demande de toucher à aucun sommaire, donc rien ne périme derrière vous |
| `docs.root` | `docs/` | l'outil l'attend là, et un agent qui cherche où poser une page n'a pas à deviner |
| `docs.audience` | `équipe` | c'est l'hypothèse **sûre** : élargir se relit, restreindre ne se rattrape pas — une page lue plus largement qu'elle n'était écrite ne se dé-publie pas |

**Cette proposition ne lie pas ce dépôt.** Un dépôt sous `mkdocs` ou sans site du tout
répond autrement, et `docs.audience: public` est une décision légitime — elle
se prend, elle ne se subit pas.

**L'audience est une échelle, pas un interrupteur.** Cinq crans, du plus étroit
au plus large, et chacun élargit ce qui peut être lu :

| Valeur | Qui lit |
| --- | --- |
| `mono-utilisateur` | une seule personne — celle qui ouvre le dépôt |
| `équipe` | l'équipe qui tient ce dépôt |
| `LS` | la ligne de service |
| `groupe` | le groupe |
| `public` | hors de l'organisation |

**Ce n'est pas un détail de vocabulaire.** Chaque cran décide de ce qu'un agent
a le droit d'écrire dans une page — un nom de client, une URL interne, un
détail d'infrastructure, une adresse de personne. Ce qui passe à `équipe` ne
passe pas à `groupe`, et rien ne l'attrape après coup.

**Les quadrants ne sont pas une clé de cet ADR, et c'est délibéré.** Ils ne se
répondent pas à l'adoption : les quadrants qu'un dépôt tient se **constatent**
une fois qu'il porte des pages, et au démarrage il n'en porte aucune. Poser la
question là forcerait soit une réponse inventée, soit une clé laissée vide que
le schéma refuse.

Le classement Diataxis s'applique quand même — page par page, au moment de
l'écrire. Une bibliothèque finira avec de la référence et pas de tutoriel, un
service interne avec des guides et peu d'explications ; **ça se lit dans son
arborescence, ça ne se déclare pas d'avance**.

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
adr: SDR-0008
slug: documentation
title: Documentation
status: accepted
date: 2026-03-14
authors: []
supersedes: []
traits:
  docs:
    tool: docusaurus
    root: docs/
    audience: équipe
---
```

**`## Considered Options` ci-dessus est une proposition de l'amont, pas
votre délibération.** La méthode a pesé ces options sans connaître votre
contexte. La confrontation au vôtre reste à faire, et c'est elle qui
distingue une décision d'un défaut accepté.

### Consequences

<!-- Ce que votre décision facilite, et ce qu'elle coûte. Deux ou trois lignes
     suffisent — par exemple sur ce qu'un site engendré coûte à installer, ou
     sur ce qu'une audience publique interdit d'écrire. -->

## More Information

| Clé | Ce qu'elle porte | Valeurs admises |
| --- | --- | --- |
| `docs.tool` | ce qui engendre le site, s'il y en a un | `docusaurus`, `mkdocs`, `aucun` |
| `docs.root` | le répertoire où vivent les pages | un chemin, par exemple `docs/` |
| `docs.audience` | jusqu'où cette documentation porte | `mono-utilisateur`, `équipe`, `LS`, `groupe`, `public` — l'échelle est décrite ci-dessus |

**`docs.audience` n'est pas décorative.** `public` engage un agent à ne jamais
écrire d'URL interne, de nom de client ni de détail d'infrastructure dans une
page. `mono-utilisateur` dit l'inverse : rien ne sort du dépôt, et une note
brute y a sa place.

**Les trois crans du milieu sont ceux où l'on se trompe**, parce qu'ils se
ressemblent. Un nom de client passe à l'`équipe` et pas au `groupe` ; une URL
d'outil interne passe au `groupe` et pas au `public`. **Rien ne le vérifie** —
c'est la relecture, et c'est pour ça que la valeur doit être écrite plutôt que
supposée.

**Deux de ces trois clés se décident en regardant le dépôt**, pas en lisant ce
fichier : un site existe-t-il déjà, et où vivent les pages. Seule
`docs.audience` se décide à la lecture.

**Si `docs.root` n'est pas `docs/`**, la commande ci-dessous change de chemin
avec lui : ce répertoire d'ADR vit sous la racine documentaire, quelle qu'elle
soit.

**Ce que ces clés ne couvrent pas** : ni le classement Diataxis, ni le style de
prose, ni la langue — celle-ci est décidée par
[`SDR-0002`](SDR-0002-localization.md). Ni le plan de documentation qu'un change
doit produire : il appartient au cycle, pas à ce fichier. **Et le classement
Diataxis lui-même ne se refuse pas** — `rejected` ici veut dire que vous ne
tenez pas de documentation, pas que vous la classez autrement.

**La valeur s'écrit dans ce fichier, et nulle part ailleurs.** Aucun autre
fichier ne la recopie : celui qui en a besoin renvoie ici. C'est ce qui garantit
qu'elle ne peut pas être contredite ailleurs.

**Une clé laissée vide n'est pas une réponse** — les quatre sont exigées. Vous
n'avez pas à le vérifier à l'œil. Depuis la racine de votre dépôt :

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
