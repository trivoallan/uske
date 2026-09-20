---
adr: SDR-0003
slug: software-architecture
title: Software Architecture
status: accepted
date: 2026-09-20
authors: [Tristan Rivoallan]
supersedes: []
traits:
  architecture:
    pattern: hexagonal
    document: arc42
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

**Décision de ce dépôt — 2026-09-20.** La proposition de la méthode est adoptée telle quelle.
`monolithic`, que ce fichier dit souvent honnête pour un petit dépôt,
a été proposé et écarté par la personne qui statue.

- `architecture.pattern` : répondue — 2026-09-20
- `architecture.document` : répondue — 2026-09-20 ; `docs/architecture/arc42.md` est créé par le
  même change

**Ce que le dépôt fait aujourd'hui, et qui s'en écarte** : `uske/` compte dix modules à plat,
environ mille lignes. Deux d'entre eux, `gate.py` et `outcomes.py`, ne font aucune
entrée-sortie et se testent déjà seuls ; mais rien dans l'arborescence ne dit ce qui a le droit
de dépendre de quoi, et `cli.py` mêle la lecture des arguments, les fichiers et les règles. Le
code n'est pas organisé en ports et adaptateurs. Cet ADR dit où il va, pas où il est.

### Consequences

Les règles d'un screening restent testables sans registre ni outil voisin, et cela devient une
règle de structure plutôt qu'un état de fait : c'est ce que demandent les objectifs de sûreté et
d'opérabilité que déclare `openspec/discovery.md`. Le coût : le code existant reste à
rapprocher, change après change, et d'ici là un agent lit une arborescence qui contredit cet
ADR — il suit l'ADR pour le code nouveau.

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
