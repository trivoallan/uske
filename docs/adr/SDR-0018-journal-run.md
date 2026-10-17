---
adr: SDR-0018
slug: journal-run
title: Une ligne du journal nomme le screening qui l'a écrite
status: accepted
date: 2026-10-16
authors: [Tristan Rivoallan]
supersedes: []
---

# Une ligne du journal nomme le screening qui l'a écrite

> Verdict `accepted` reçu de Tristan Rivoallan le 2026-10-16 : « consigner le run », plutôt que
> grouper les décisions par heure. Le code du même changement s'y conforme.

## Context and Problem Statement

Le journal ne disait pas quel screening avait écrit une ligne : seulement son heure (`ts`). Or un
screening écrit en plusieurs temps — la première porte, puis la seconde quelques minutes plus tard —
et deux screenings peuvent se suivre de près. `uske decisions --format md` groupait donc les
décisions par jour UTC : une colonne pour toute une journée, où la responsable plateforme ne
distinguait plus ce qu'un screening avait décidé de ce que le suivant avait corrigé.

Le journal est en ajout seul (SDR-0016) : une clé, une fois écrite dans un journal réel, y reste.
D'où cet ADR.

## Considered Options

* **Grouper par minute UTC, sans toucher au journal** — écartée : les deux portes d'un même
  screening se séparent, et deux screenings voisins se confondent.
* **Déduire le screening des écarts entre `ts`** — écartée : une heuristique, que la durée d'un
  screening ou une reprise d'Argo met en défaut.
* **Une clé `run`, écrite par `uske classify`** — retenue.

## Decision Outcome

| Élément | Où | Ce qu'il dit |
| --- | --- | --- |
| clé `run` | toute ligne écrite par `classify`, clôture de source comprise | le screening qui a jugé : un identifiant opaque, ou l'URL de sa page |

* `classify --run` la reçoit ; sans valeur, la clé n'est pas écrite. Le `WorkflowTemplate` passe
  `{{workflow.name}}` ; un screening hors Argo passe ce qui le désigne, par exemple l'URL du run
  GitHub Actions.
* Une ligne écrite avant cet ADR, ou à la main (réouverture, arbitrage), n'a pas de `run`. Un
  lecteur la range par sa minute UTC.
* `uske decisions` fait une période de chronologie par `run`, et une colonne `run` au tableau, en
  lien quand c'est une URL.

### Consequences

* Bon : la chronologie d'une image se lit screening par screening, les deux portes ensemble.
* Bon : le même identifiant servira à rendre une étape rejouée idempotente, et à mesurer
  l'exposition par passage (`TODOS.md`).
* Coût : une clé de plus, irréversible, sur chaque ligne.
* Coût : le journal d'avant cet ADR reste groupé à la minute ; il ne se réécrit pas.
