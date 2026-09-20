---
adr: SDR-0010
slug: forge-and-ci
title: Forge and continuous integration
status: proposed
date:
authors: []
supersedes: []
traits:
  forge:
    host:
  ci:
    tool:
    gate:
---

# Forge and continuous integration

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
qui ouvre une merge request ne sait pas **où elle part**, ce qui **s'exécute**
quand il pousse, ni si une chaîne rouge **empêche** la fusion ou se contente de
l'annoncer. Il perd du temps à réparer un rouge qui n'avait aucune conséquence —
ou il fusionne un rouge qui en avait une. Une fois ces trois valeurs écrites, il
sait.

**La forge n'est pas qu'un hébergeur, et c'est pourquoi elle est ici avec la
CI.** Elle décide le vocabulaire — merge request ou pull request —, l'outil qui
exécute la chaîne, et l'endroit où vivent les protections de branche. Les deux
questions ne se décident pas séparément : répondre `github` répond déjà à
moitié à `ci.tool`.

**Ce qui n'est pas ici.** La stratégie de branche et de fusion est dans
[`SDR-0009`](SDR-0009-branching.md) — elle ne dépend pas de la forge. Ce qui part
en production est dans [`SDR-0011`](SDR-0011-delivery.md).

## Considered Options

* **Une chaîne bloquante** — rien ne fusionne au rouge. Le coût est réel : une
  chaîne instable bloque des gens qui n'y sont pour rien, et la pression pour la
  contourner monte.
* **Une chaîne informative** — elle rapporte, la relecture décide. Moins de
  friction, et aucune garantie : un rouge signalé se néglige.
* **Aucune chaîne** — la relecture est le seul contrôle. Réponse tenable, et
  c'est le régime du dépôt de la méthode lui-même.

## Decision Outcome

**La réponse que la méthode propose, et ses motifs.**

| Clé | Valeur proposée | Motif |
| --- | --- | --- |
| `forge.host` | `gitlab` | c'est là que vit l'équipe qui publie la méthode, et son vocabulaire en vient — elle écrit « merge request » là où GitHub dit « pull request ». **`github` est un choix admis, pas une déviation** — voir juste en dessous |
| `ci.tool` | *découle de `forge.host`* | `gitlab-ci` sur GitLab, `github-actions` sur GitHub. Cette clé existe pour être **lue** par un agent, pas pour être délibérée |
| `ci.gate` | `bloquante` | un contrôle qui n'empêche rien n'est pas un contrôle, c'est un rapport. Des trois clés, c'est la seule qui soit une vraie décision |

**Sur `forge.host`, la réponse a une forme que les autres ADR hérités n'ont
pas.** Ailleurs, la méthode propose une valeur, ou borne le champ sans choisir.
Ici elle fait les deux : elle **propose `gitlab` tout en admettant `github` à
égalité**, sans justification à fournir. Les deux sont des réponses pleines. Une
troisième forge — Gitea, Bitbucket, Forgejo — reste possible ; elle demande
seulement d'écrire pourquoi dans ce fichier, parce que le reste de la méthode
n'a pas été éprouvé contre elle.

**La méthode ne fait pas ce qu'elle propose ici, et le dire vaut mieux que le
taire.** Le dépôt de la méthode n'a aucune pipeline — il a retiré la sienne, et
sa relecture est son seul contrôle. Cette décision-là est **locale**, elle ne
descend pas jusqu'à vous : elle tient parce que ce dépôt ne porte pas de code
exécutable. Un dépôt qui en porte n'est pas dans ce cas, et c'est pour ça que la
proposition ci-dessus est `bloquante` et non « aucune ».

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
adr: SDR-0010
slug: forge-and-ci
title: Forge and continuous integration
status: accepted
date: 2026-03-14
authors: []
supersedes: []
traits:
  forge:
    host: gitlab
  ci:
    tool: gitlab-ci
    gate: bloquante
---
```

**`## Considered Options` ci-dessus est une proposition de l'amont, pas
votre délibération.** La méthode a pesé ces options sans connaître votre
contexte. La confrontation au vôtre reste à faire, et c'est elle qui
distingue une décision d'un défaut accepté.

### Consequences

<!-- Ce que votre décision facilite, et ce qu'elle coûte. Deux ou trois lignes
     suffisent — par exemple sur ce qu'une chaîne bloquante impose quand elle
     devient instable, ou sur ce qu'une forge impose à qui doit y accéder. -->

## More Information

| Clé | Ce qu'elle porte | Valeurs admises |
| --- | --- | --- |
| `forge.host` | où vivent le dépôt et ses demandes de fusion | `gitlab`, `github`, ou une autre à justifier |
| `ci.tool` | ce qui exécute la chaîne à chaque poussée | dépend de la forge : `gitlab-ci`, `github-actions`, … ou `aucun` |
| `ci.gate` | ce qu'une chaîne rouge empêche | `bloquante` — rien ne fusionne au rouge ; `informative` — elle rapporte, la relecture décide ; `aucune` — il n'y a pas de chaîne |

**Attention à `aucun` et `aucune`, voisins et inégaux.** `ci.tool: aucun` dit
qu'il n'y a pas d'outil ; `ci.gate: aucune` dit qu'il n'y a pas de contrôle. Les
deux vont ensemble, mais **seule la seconde est contrôlée** : écrire
`ci.tool: aucune` ne sera signalé par rien. La raison est juste en dessous.

**Deux de ces trois clés ne sont pas vérifiables, et c'est délibéré.** Les
forges et les outils de CI ne forment pas une liste fermée ; un contrôle qui en
figerait une refuserait mécaniquement la réponse que ce fichier autorise. Seule
`ci.gate` a un ensemble fermé, donc seule elle est réellement contrôlée. Pour
les deux autres, la contrainte est **sociale, tenue par la relecture** — ne
comptez pas sur l'outil pour vous rattraper.

**`ci.gate: aucune` n'est pas un aveu.** C'est la réponse d'un dépôt qui n'a rien
à exécuter — de la documentation, des schémas, de la configuration relue à la
main. Elle se prend, comme les autres.

**Et c'est elle qu'il faut, pas `rejected`.** Un dépôt vit forcément quelque
part : `forge.host` a toujours une réponse, donc la question de ce fichier se
pose toujours. Un dépôt sans chaîne répond `ci.gate: aucune` et garde son bloc
`traits:` ; il ne rejette pas. **`rejected` n'a pratiquement pas d'emploi ici** —
si vous croyez en avoir un, c'est le signe qu'il faut plutôt écrire l'ADR de
déviation décrit en tête.

**Ce que ces clés ne couvrent pas** : ni ce que la chaîne exécute — les
instruments de test et de lint se déclarent ailleurs, et
[`SDR-0007`](SDR-0007-tests.md) porte le seuil de couverture — ni comment on
contribue au dépôt, qui est dans [`SDR-0009`](SDR-0009-branching.md).

**La valeur s'écrit dans ce fichier, et nulle part ailleurs.** Aucun autre
fichier ne la recopie : celui qui en a besoin renvoie ici. C'est ce qui garantit
qu'elle ne peut pas être contredite ailleurs.

**Une clé laissée vide n'est pas une réponse** — les trois sont exigées. Vous
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
