---
adr: SDR-0009
slug: branching
title: Branching
status: accepted
date: 2026-09-20
authors: [Tristan Rivoallan]
supersedes: []
traits:
  branching:
    model: github-flow
    merge: squash
    prefixes: [feat, fix, docs, ci]
---

# Branching

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
qui commence un travail ne sait pas **comment nommer sa branche**, s'il a le
droit de **pousser sur la branche de référence**, ni si ses huit commits
arriveront à l'autre bout **en huit ou en un**. Les trois se devinent — mal, et
différemment à chaque fois. Une fois ces trois valeurs écrites, il n'a plus à
deviner.

**Cette question ne dépend pas de la forge.** Les trois modèles ci-dessous se
tiennent aussi bien sur GitLab que sur GitHub ; c'est pourquoi ils vivent ici et
non dans [`SDR-0010`](SDR-0010-forge-and-ci.md).

## Considered Options

* **`github-flow`** — une branche courte par change, une demande de fusion, une
  relecture, et la branche de référence reste livrable en permanence. Le nom
  vient de GitHub ; le modèle n'a rien de propre à cette forge.
* **`trunk-based`** — on pousse sur la branche de référence, et ce qui n'est pas
  prêt est masqué derrière un drapeau. Très rapide, et cher : il faut les
  drapeaux, et une chaîne à laquelle on fait confiance.
* **`gitflow`** — des branches `develop`, `release` et `hotfix` en plus. Fait
  pour un logiciel livré par versions installées chez des tiers ; coûteux pour
  un service déployé en continu.

## Decision Outcome

**La réponse que la méthode propose, et ses motifs.**

| Clé | Valeur proposée | Motif |
| --- | --- | --- |
| `branching.model` | `github-flow` | c'est ce que le cycle de la méthode suppose déjà : **un change, une branche, une demande de fusion, une relecture**. Les deux autres modèles obligeraient à réécrire le cycle |
| `branching.merge` | `squash` | un change devient **un** commit sur la branche de référence, dont l'historique se lit alors comme la liste des changes livrés |
| `branching.prefixes` | `[feat, fix, docs]` | ce sont déjà des types de commit : rien de nouveau à retenir, et le nom d'une branche annonce ce qu'elle porte |

**`squash` déplace le message qui compte, et ça surprend une fois.** Les commits
d'une branche écrasée disparaissent de l'historique ; ce qui reste est le
message de la fusion. C'est **lui** qui doit porter le type Conventional Commits
et la mention de rupture, puisque c'est lui dont SemVer se déduit. Soigner ses
commits intermédiaires reste utile à la relecture, mais ne suffit pas.

**Les préfixes de branche sont un sous-ensemble, pas une seconde liste.** La
méthode n'admet que onze types de commit, et les voici en entier, pour que vous
n'ayez rien à aller chercher :

`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`,
`chore`, `revert`.

`branching.prefixes` n'en retient que ceux qui nomment utilement une branche. Si
vous en ajoutez, **prenez-les dans les onze** : inventer un douzième préfixe ici
créerait une norme concurrente de celle des commits.

**Décision de ce dépôt — 2026-09-20.** La proposition de la méthode est adoptée pour
`branching.model` et `branching.merge`. `branching.prefixes` s'en écarte d'un préfixe : `ci`,
pris parmi les onze types de commit. Ce que l'écart constate : une branche `ci/…` existe déjà.

- `branching.model` : répondue — 2026-09-20
- `branching.merge` : répondue — 2026-09-20
- `branching.prefixes` : répondue — 2026-09-20. La première réponse était `[feat, fix, docs]` ;
  `ci` a été ajouté le même jour, avant la fusion, une fois la branche existante constatée.

**Ce que le dépôt faisait jusqu'ici** : quatre commits faits droit sur `main`, dont deux
poussés ; aucune fusion. Une branche de travail précède cette décision —
`ci/dependabot-candidate-go`, demande de fusion n° 2, ouverte ; la liste retenue couvre son
préfixe. Le change qui statue cet ADR part sur `docs/onboarding`.

### Consequences

L'historique de `main` se lira comme la liste des changes livrés, et un agent sait nommer sa
branche sans deviner. Le coût : une demande de fusion même pour un auteur seul, et un message
de fusion à soigner — c'est lui que lira l'outil de release retenu par
[`SDR-0011`](SDR-0011-delivery.md).

## More Information

| Clé | Ce qu'elle porte | Valeurs admises |
| --- | --- | --- |
| `branching.model` | comment le travail arrive sur la branche de référence | `github-flow`, `trunk-based`, `gitflow` |
| `branching.merge` | ce que devient une branche une fois fusionnée | `squash` — un seul commit ; `merge-commit` — l'historique est conservé sous un commit de fusion ; `rebase` — les commits sont rejoués tels quels |
| `branching.prefixes` | les préfixes admis dans un nom de branche | une liste prise parmi les onze types de commit, par exemple `[feat, fix, docs]` |

**Un préfixe ne fait pas un nom de branche**, et il faut le dire ici pour que la
clé serve à quelque chose. La forme est `préfixe/description-en-tirets` — le
séparateur est une **barre oblique**, la description est en minuscules et en
tirets. Par exemple `feat/portage-des-schemas` ou `fix/lien-mort-du-glossaire`.
Cette forme n'est pas un trait : elle découle des préfixes, et une clé de plus
pour un séparateur serait du bruit.

**Le nom de la branche de référence n'est pas un trait, délibérément.** Il se
lit dans le dépôt — `git symbolic-ref refs/remotes/origin/HEAD` le donne — et
une clé qui recopie un fait vérifiable se contente de vieillir.

**Deux de ces trois clés sont contrôlées, la troisième non.** `branching.model`
et `branching.merge` ont un ensemble fermé. `branching.prefixes` est une liste
libre : le schéma vérifie que vous en avez écrit une, jamais ce qu'elle contient.
La cohérence avec les onze types est tenue par la **relecture**.

**Ce que ces clés ne couvrent pas** : ni le format des messages de commit, qui
est dans [`SDR-0006`](SDR-0006-commits.md), ni ce qu'une chaîne exécute sur une
branche, qui est dans [`SDR-0010`](SDR-0010-forge-and-ci.md), ni ce qui part en
production, qui est dans [`SDR-0011`](SDR-0011-delivery.md).

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
