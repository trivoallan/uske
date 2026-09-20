---
adr: SDR-0002
slug: localization
title: Localization
status: accepted
date: 2026-09-20
authors: [Tristan Rivoallan]
supersedes: []
traits:
  localization:
    language:
      default: français
      code: anglais
      comments: anglais
---

# Localization

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

**Concrètement, ce que statuer change.** Tant que ces clés sont vides,
un agent qui écrit du code dans ce dépôt ne sait pas en quelle langue nommer une
fonction, ni s'il doit commenter en français, ni comment rédiger un message de
commit. Il devine — et il devine différemment d'une fois sur l'autre. Une fois
la valeur écrite, il la lit et l'applique, sans vous la redemander.

La question se pose parce que les supports n'ont pas les mêmes lecteurs. Une
documentation s'adresse à l'équipe et à ceux qui la rejoindront ; un symbole, à
quiconque lit le code, y compris hors de l'équipe ; un commentaire, à celui qui
relit une fonction dans six mois ; un message de commit, à qui remonte
l'historique dans deux ans. Répondre « la même langue partout » est une réponse,
mais c'en est une, et elle se choisit — c'est ce que `default` sert à dire.

## Considered Options

- **Tout en français** — documentation, commits, symboles, commentaires.
- **Prose française, symboles anglais** — la proposition de la méthode, décrite
  ci-dessous.
- **Tout en anglais** — pour un dépôt ouvert ou une équipe non francophone.
- **Un autre découpage** — les quatre surcharges sont indépendantes, rien n'oblige à
  les aligner.

## Decision Outcome

**La réponse que la méthode propose, et ses motifs.** Une langue par défaut, et une
seule surcharge :

| Clé       | Valeur proposée | Motif                                                                                                    |
| --------- | --------------- | -------------------------------------------------------------------------------------------------------- |
| `default` | `français`      | l'équipe l'est, et tout ce qui s'adresse à elle suit                                                     |
| `code`    | `anglais`       | un symbole est lu par des outils et par des gens hors de l'équipe ; l'anglais y est la langue par défaut |

`documentation`, `commits` et `comments` ne sont pas renseignés : ils prennent
`default`. **Ne remplissez une de ces trois clés que pour vous écarter du
défaut** — sinon, laissez-la vide, c'est ce qui rend la décision lisible d'un
coup d'œil.

**Cette proposition ne lie pas ce dépôt.** Elle existe pour qu'il y ait quelque chose à
quoi réagir, plutôt qu'une page blanche : elle se garde, s'amende ou s'écarte.

**Décision de ce dépôt — 2026-09-20.** La proposition de la méthode est adoptée, avec une
surcharge de plus : `comments: anglais`. Motif de l'écart : les commentaires et les docstrings
de `uske/` sont déjà en anglais, au plus près de symboles anglais ; les traduire n'apprendrait
rien à personne. `documentation` et `commits` sont retirées du frontmatter : elles suivent
`default`, donc le français.

- `localization.language.default` : répondue — 2026-09-20
- `localization.language.code` : constatée — `uske/*.py` ; confirmée le 2026-09-20
- `localization.language.comments` : constatée — `uske/*.py` ; confirmée le 2026-09-20

**Ce qui précède cette décision et s'en écarte** : `README.md`, bilingue et anglais d'abord, et
le premier message de commit, en anglais. Aucun des deux n'est repris ici.

### Consequences

Un agent sait dans quelle langue écrire chaque support, et la prose du dépôt — ADR, découverte,
document d'architecture, messages de commit — reste dans la langue de qui décide. Le coût : un
lecteur non francophone lit le code, pas les décisions ; et `README.md` s'écarte de la règle tant
qu'un change ne l'a pas repris ou qu'un nouvel ADR n'a pas surchargé `documentation`.

## More Information

| Clé             | Ce qu'elle porte                                               | Valeurs admises       |
| --------------- | -------------------------------------------------------------- | --------------------- |
| `default`       | la langue de tout ce qui n'est pas surchargé ci-dessous        | `français`, `anglais` |
| `documentation` | la documentation, si elle diffère du défaut                    | `français`, `anglais` |
| `commits`       | les messages de commit, s'ils diffèrent                        | `français`, `anglais` |
| `code`          | les symboles — fonctions, classes, variables — s'ils diffèrent | `français`, `anglais` |
| `comments`      | les commentaires de code, s'ils diffèrent                      | `français`, `anglais` |

**Seule `default` est exigée.** Les quatre autres sont des surcharges : une clé
vide veut dire « comme `default` », et c'est une réponse, pas un oubli.

**La valeur s'écrit dans ce fichier, et nulle part ailleurs.** Aucun autre
fichier ne la recopie : celui qui en a besoin renvoie ici. C'est ce qui garantit
qu'elle ne peut pas être contredite ailleurs.

**`default` laissée vide n'est pas une réponse** — les quatre surcharges, si :
vides, elles disent « comme `default` ». Vous n'avez pas à distinguer les deux à
l'œil. Depuis la racine de votre dépôt :

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
