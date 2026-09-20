---
adr: SDR-0008
slug: documentation
title: Documentation
status: accepted
date: 2026-09-20
authors: [Tristan Rivoallan]
supersedes: []
traits:
  docs:
    tool: aucun
    root: docs/
    audience: mono-utilisateur
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

**Décision de ce dépôt — 2026-09-20.** Deux écarts à la proposition, et leurs motifs.
`docs.tool: aucun` plutôt que `docusaurus` : le dépôt n'a pas de site, et ses pages se lisent
sur la forge. `docs.audience: mono-utilisateur` plutôt
qu'`équipe` : le dépôt est privé, et `git log` ne montre qu'un auteur ; c'est plus étroit que la
proposition. `docs.root` suit la proposition.

- `docs.tool` : constatée — ni `mkdocs.yml` ni `docusaurus.config.*` ; confirmée le 2026-09-20
- `docs.root` : constatée — `docs/adr/` ; confirmée le 2026-09-20
- `docs.audience` : répondue — 2026-09-20. `public` a été proposé, au vu de la licence et du but
  open source, et écarté.

### Consequences

Aucun sommaire à tenir, et une note brute a sa place dans une page. Le coût : le jour où le
dépôt s'ouvre, un nouvel ADR élargit l'audience, et **toutes** les pages écrites sous
`mono-utilisateur` se relisent avant — ce qui passait ici ne passe pas à `public`. Le classement
Diataxis s'applique quand même, page par page.

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
