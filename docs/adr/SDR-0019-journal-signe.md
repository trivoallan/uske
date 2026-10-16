---
adr: SDR-0019
slug: journal-signe
title: Le journal reste sur son volume, et chaque screening le scelle d'un point de contrôle signé
status: proposed
date: 2026-10-17
authors: [Tristan Rivoallan]
supersedes: []
---

# Le journal reste sur son volume, et chaque screening le scelle d'un point de contrôle signé

> Statut `proposed` : trois questions restent ouvertes auprès de l'équipe PKI de l'employeur
> (*More Information*). Le support du journal, lui, ne dépend pas de leurs réponses ; la preuve
> d'intégrité, si.

## Context and Problem Statement

Le journal des décisions est un fichier JSON Lines par politique, en ajout seul
(`policies/**/*.journal.jsonl`), écrit sur le volume `uske-results`. `SDR-0016` fixe son
vocabulaire, `SDR-0018` sa clé `run` ; aucun ADR ne dit pourquoi il vit là (`DEBT-08`).

Les objectifs produit supposaient autre chose : `objectives.md` (O1-KR2) et `strategy.md`, dans le
wiki nanopm, tiennent le journal pour commité dans le dépôt de politiques, donc daté et
historisé par git. Il ne l'est pas. Un volume Kubernetes n'a pas d'historique : une écriture
directe sur le volume réécrit une ligne, et rien ne le voit (`RISK-01`). L'objectif de
Contestabilité promet « aucune ligne modifiée » (QS-04) sans moyen de le prouver hors de `uske`.

La question devient concrète : des auditeurs de conformité vont demander comment prouver
qu'aucune ligne n'a été réécrite. L'organisation a une PKI interne, et les auditeurs acceptent un
journal signé. C'est ce besoin d'audit, et non un goût de méthode, qui justifie cet ADR hors de
tout change en cours.

Deux questions, donc : **où vit le journal**, et **comment prouver qu'il n'a pas été réécrit**.

## Considered Options

**Le support.**

* **Le journal commité dans le dépôt de politiques** — ce que supposaient O1-KR2 et
  `strategy.md`. Écartée : chaque screening deviendrait un commit, donc un jeton d'écriture sur
  le dépôt dans le cluster, une file d'attente contre les modifications humaines des politiques,
  et un échec technique de plus à chaque poussée refusée. Et git ne prouve rien seul : un
  historique se réécrit par une poussée forcée ; la preuve viendrait de la protection de branche
  de la forge, que `uske` ne tient pas.
* **Un stockage externe** (base de données, stockage objet à rétention verrouillée) — écartée :
  un service de plus à opérer et à joindre depuis le cluster, contre l'objectif de Minceur, pour
  un volume de quelques lignes par screening. Un stockage objet en mode WORM prouverait la
  non-réécriture, mais déplacerait la confiance vers sa configuration, que l'audit devrait alors
  vérifier à son tour.
* **Un fichier JSON Lines par politique, en ajout seul, sur le volume `uske-results`** —
  retenue : c'est ce qui tourne déjà, il se lit, se copie et se conteste sans serveur, et la
  preuve d'intégrité peut s'y ajouter sans le déplacer.

**La preuve d'intégrité.**

* **Rien de plus que l'ajout seul de `uske`** — écartée : c'est l'état actuel, et `RISK-01`.
* **Une copie datée du journal hors du volume** (la piste notée sous `RISK-01`) — écartée : elle
  rend QS-04 vérifiable entre deux copies, mais ne prouve rien sur la copie elle-même ; il
  faudrait encore la protéger.
* **Signer chaque ligne** — écartée : une signature par décision multiplie les appels à la clé,
  et une ligne retirée ne laisse aucune trace, puisque les autres restent valides.
* **Un point de contrôle signé et chaîné par politique, à la fin de chaque screening** —
  retenue.

## Decision Outcome

**Le support (referme `DEBT-08`).** Le journal reste un fichier JSON Lines par politique, en
ajout seul, sur le volume `uske-results`.

**La preuve d'intégrité (traite `RISK-01`).** À la fin de chaque screening, `uske` écrit pour
chaque politique un point de contrôle, et le signe.

| Champ | Ce qu'il dit |
| --- | --- |
| `fichier` | le chemin du journal de la politique |
| `taille` | sa taille en octets au moment du point de contrôle |
| `sha256` | le hash des `taille` premiers octets — tout le fichier à cet instant |
| `run` | le screening qui l'a écrit, comme la clé de `SDR-0018` |
| `precedent` | le `sha256` du point de contrôle précédent de la même politique ; vide pour le premier |

* **La signature** : `cosign sign-blob`, déjà dans l'image `uske` (`Dockerfile`), sur le point de
  contrôle sérialisé. Le certificat est émis par la PKI interne de l'employeur **au nom de la
  charge de travail**, pas d'une personne. La clé vit **hors du namespace** — HSM ou coffre de
  l'équipe PKI — et `cosign` l'appelle par son URI (KMS ou PKCS#11) : rien dans le cluster ne
  peut signer hors de cet appel.
* **Le temps** : horodatage RFC 3161 par la TSA interne (`--timestamp-server-url`).
* **Aucun journal de transparence public** : `--tlog-upload=false`. Rien du journal ni de ses
  hash ne sort de l'organisation. Avec `cosign` 3, l'option passe par la configuration de
  signature ; la forme exacte se vérifie à l'implémentation sur la version épinglée.
* **La vérification par préfixe** : le journal étant en ajout seul, ses `taille` premiers octets
  doivent toujours avoir le `sha256` du point de contrôle, quel que soit ce qui a été ajouté
  depuis. Une ligne réécrite ou retirée avant `taille` casse ce hash ; un point de contrôle
  retiré ou remplacé casse la chaîne des `precedent`.
* **Le vérificateur** : une future sous-commande `uske decisions --verify` rejoue la chaîne —
  chaque signature, chaque horodatage, chaque `precedent`, chaque préfixe — et nomme le premier
  maillon qui ne tient pas. Un auditeur la lance sur une copie du volume, sans accès au cluster.

### Consequences

* Bon : QS-04 se prouve hors de `uske`, avec la PKI que les auditeurs reconnaissent déjà.
* Bon : le journal ne change ni de place ni de format ; les lecteurs actuels n'ont rien à
  apprendre.
* Bon : un appel à la clé par politique et par screening, pas par décision.
* Coût : **la fenêtre entre l'écriture d'une ligne et le point de contrôle de fin de screening
  reste hors de la preuve.** Une ligne réécrite pendant un screening, avant son point de
  contrôle, est scellée telle quelle. La fenêtre dure un screening ; la refermer demanderait de
  signer à chaque écriture.
* Coût : un screening dépend de la clé et de la TSA. Si l'une manque, le point de contrôle n'est
  pas écrit ; c'est un échec technique (exit 1), qu'Argo rejoue, et non une décision.
* Coût : un volume perdu emporte journal et points de contrôle ensemble. La preuve dit que rien
  n'a été réécrit, pas que rien n'a été perdu ; la sauvegarde reste une affaire d'exploitation.
* Coût : la vérification lit tout le fichier ; elle grossit avec le journal, ce qui reste
  négligeable aux volumes attendus.

## More Information

**Questions ouvertes auprès de l'équipe PKI**, qui retiennent cet ADR en `proposed` :

* **(a)** Émettent-ils un certificat de signature de code pour une charge de travail, et non
  pour une personne ?
* **(b)** Peuvent-ils garder la clé dans leur HSM ou leur coffre, appelable depuis le cluster, et
  journaliser les signatures de leur côté ?
* **(c)** Ont-ils une TSA RFC 3161 ? Sans TSA, le journal des signatures du coffre, s'il existe
  (b), sert d'ancre de temps à la place de l'horodatage.

Le défaut des rapports écrasés quand une décision est rejugée, relevé en même temps, se corrige à
part, dans [trivoallan/uske#44](https://github.com/trivoallan/uske/pull/44).
