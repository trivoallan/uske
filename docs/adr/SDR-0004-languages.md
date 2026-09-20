---
adr: SDR-0004
slug: languages
title: Languages
status: accepted
date: 2026-09-20
authors: [Tristan Rivoallan]
supersedes: []
traits:
  languages:
    main:
      name: Python
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

**Décision de ce dépôt — 2026-09-20.** `Python`, l'un des trois langages recommandés : aucune
justification d'écart n'est due.

- `languages.main.name` : constatée — `pyproject.toml` (`requires-python = ">=3.12"`) ;
  confirmée le 2026-09-20

**Du Go figure au dépôt sans être un langage de `uske`** : `deploy/kind/candidate-go/` est une
image candidate de démonstration pour le banc local, pas du code de `uske`.

### Consequences

Un agent écrit en Python sans déduire, et l'outillage suit : la bibliothèque de validation de
[`SDR-0005`](SDR-0005-validation.md), le seuil de [`SDR-0007`](SDR-0007-tests.md). Le coût :
une image à construire avec son interpréteur plutôt qu'un binaire seul, et rien d'autre — le
code était déjà là.

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
