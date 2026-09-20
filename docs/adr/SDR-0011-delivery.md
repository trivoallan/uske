---
adr: SDR-0011
slug: delivery
title: Delivery
status: accepted
date: 2026-09-20
authors: [Tristan Rivoallan]
supersedes: []
traits:
  deploy:
    environments: []
  release:
    tool: release-please
---

# Delivery

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
qui termine un change ne sait pas si le fusionner **le met devant des
utilisateurs** ou seulement dans `main`, ni ce qui **fabrique une version**. Il
fusionne donc sans savoir ce qu'il déclenche — et c'est la seule des questions
de l'adoption dont se tromper a des conséquences pour quelqu'un d'autre que
l'équipe. Une fois ces trois valeurs écrites, il sait ce que sa fusion fait.

**Livrer et déployer ne sont pas le même geste**, et les deux clés le disent :
`release.tool` fabrique une version nommée et son journal, le déclencheur de
chaque environnement la met en service. Un dépôt peut faire l'un sans l'autre.

## Considered Options

**Ces options ne pèsent que le déclencheur d'un environnement**, la seule part
de ces clés qui ait un ensemble fermé. Le reste se lit dans
`## More Information`.

**Elles se pèsent environnement par environnement**, pas une fois pour le dépôt :
la même équipe veut souvent `merge` sur son intégration et `tag` sur sa
production.

* **Déployer sur tag** — ce qui tourne porte un nom. Un geste de plus après la
  fusion, et un retour arrière qui a une cible.
* **Déployer sur fusion** — la fusion suffit, le délai est minimal. « Ce qui
  tourne » devient un SHA que personne n'a en tête, et le retour arrière n'a
  plus de cible évidente.
* **Déployer à la main** — quelqu'un décide et lance. Honnête pour un dépôt qui
  livre rarement ; le coût est que le geste n'est écrit nulle part.

## Decision Outcome

**La réponse que la méthode propose, et ses motifs.**

| Clé | Valeur proposée | Motif |
| --- | --- | --- |
| `deploy.environments` | `staging` sur `merge`, `production` sur `tag` | **la question se pose, elle ne se devine pas** : la méthode ne sait pas ce que vous servez, mais elle sait quelle paire marche presque toujours — voir ci-dessous |
| `release.tool` | *dépend de `forge.host`* | `release-please` sur GitHub, où il s'installe aujourd'hui. Sur GitLab, `manuel` — la cible de la méthode n'y est **pas livrable**, voir ci-dessous |

**Un déclencheur unique ne décrit pas ce que font les équipes.** C'est pourquoi
il vit désormais **dans** chaque environnement plutôt qu'à côté d'eux.

La paire proposée : **`staging` part à la fusion sur `main`**, parce qu'un
environnement d'intégration doit refléter ce que la branche porte, sans geste
supplémentaire — et **`production` part sur un tag**, parce qu'une version en
service est une version **nommée** : on sait ce qui tourne, on peut le dire à
quelqu'un, et un retour arrière a une cible.

**La liste, elle, se demande.** La méthode ne connaît pas vos environnements :
un dépôt peut n'en servir aucun, un autre en servir quatre. **Écrivez-les dans
l'ordre où une version les traverse** — c'est cet ordre qui dit ce qu'un
déploiement en production a déjà franchi.

**Aucun environnement est une réponse pleine.** Une bibliothèque ne déploie pas :
elle publie. `environments: []` le dit, et `release.tool` porte alors tout le
sujet.

**Sur `release.tool`, la réponse dépend de la forge**, décidée dans
[`SDR-0010`](SDR-0010-forge-and-ci.md). Les deux outils font la même chose : ils
lisent les messages de commit, ouvrent une demande de fusion de release portant
le journal des changements et la version calculée, puis posent le tag à la
fusion. C'est leur disponibilité qui diffère, pas leur intérêt.

Sur **GitHub**, la réponse est
[`release-please`](https://github.com/googleapis/release-please). Il existe, il
s'installe aujourd'hui, et il fait exactement ce que la méthode veut.

Sur **GitLab**, la méthode vise `releaser-pleaser` — mais **le composant n'est
mirroré sur aucune instance**. Le proposer reviendrait à envoyer un aval
installer ce qui n'est pas installable. `manuel` est donc ici une réponse sans
scrupule : c'est ce que la méthode fait elle-même, en attendant. Le nom est
écrit pour dire où elle va, pas pour être adopté aujourd'hui.

**SemVer n'est pas ici, et ce n'est pas un oubli.** La numérotation découle
mécaniquement des types de commit — `feat` donne une mineure, `fix` et `perf`
une corrective, une rupture une majeure. C'est une **norme de la méthode**, pas
une question ouverte : il n'y a pas de clé pour elle parce qu'il n'y a rien à
décider. Choisir `calver` serait une déviation, à écrire dans un ADR à vous.

**Décision de ce dépôt — 2026-09-20.** `deploy.environments: []` s'écarte de la paire
proposée : rien n'est servi — `README.md` dit « Not deployed anywhere yet », et aucun flux ne
publie l'image. `release.tool: release-please` suit la proposition pour la forge que déclare
[`SDR-0010`](SDR-0010-forge-and-ci.md). `aucun` a été proposé et écarté par la personne qui
statue.

- `deploy.environments` : constatée — `README.md` ; confirmée le 2026-09-20
- `release.tool` : répondue — 2026-09-20

**Ce que le dépôt fait aujourd'hui, et qui s'en écarte** : version `0.0.0`, aucun tag, aucun
journal des changements ; `release-please` n'est pas installé.

### Consequences

Fusionner ne met rien devant personne, et un agent le sait. Les versions se déduiront des
messages de commit : c'est ce qui rend `commitlint` pertinent
([`SDR-0006`](SDR-0006-commits.md)). Le coût : l'outil reste à installer ; et la première story
de `openspec/discovery.md`, qui déploie un screening, nommera une cible — un nouvel ADR dépassera
alors celui-ci pour l'écrire.

## More Information

| Clé | Ce qu'elle porte | Valeurs admises |
| --- | --- | --- |
| `deploy.environments` | ce que ce dépôt sert, dans l'ordre où une version les traverse, **chacun avec son déclencheur** | une liste de paires — voir l'exemple ci-dessus. Déclencheurs admis : `tag`, `merge`, `manuel` |
| `release.tool` | ce qui fabrique une version et son journal des changements | `release-please`, `releaser-pleaser`, un autre outil, `manuel`, ou `aucun` |

**`manuel` et `aucun` ne disent pas la même chose.** `manuel` veut dire qu'une
version est bien fabriquée, mais à la main : quelqu'un décide du numéro, écrit le
journal, pose le tag. `aucun` veut dire qu'**il n'y a pas de version du tout** —
rien n'est numéroté, rien n'est tagué. Un dépôt qui publie un paquet répond
`manuel`, jamais `aucun`, même s'il tape lui-même la commande de publication.

**Un outil qui ne fait que la moitié compte quand même.** `release.tool` nomme ce
qui fabrique la version ; si votre outil la publie sans écrire le journal des
changements, écrivez-le tout de même et dites en une ligne, sous
**Consequences**, que le journal se tient à la main.

**Un dépôt qui publie un paquet plutôt qu'il ne sert un service répond quand
même.** Son environnement est le registre où il publie — `[npm]`, `[pypi]`, une
instance interne — et `tag` y est la norme, une version publiée étant une
version nommée par construction.

**`rejected` ici veut dire que rien ne sort de ce dépôt** : ni service, ni
paquet, ni image. Ça arrive — un dépôt de documentation, de schémas, de
configuration relue à la main. Ce n'est pas la même chose que déployer à la
main, qui se répond `manuel`.

**Une seule part de ces clés est contrôlée.** Le `trigger` d'un environnement a
un ensemble fermé. Le reste est libre — un registre, un nom d'outil, un nom
d'environnement ne se laissent pas énumérer d'avance. Le schéma vérifie que vous
avez répondu, jamais que la réponse est la bonne.

**Ce que ces clés ne couvrent pas** : ni le format des messages dont la version
se déduit, qui est dans [`SDR-0006`](SDR-0006-commits.md), ni ce qui s'exécute
avant le déploiement, qui est dans [`SDR-0010`](SDR-0010-forge-and-ci.md).

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
