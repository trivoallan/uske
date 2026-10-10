---
adr: SDR-0016
slug: journal-et-transit
title: Vocabulaire du journal pour une reconstruction, et transit obligatoire
status: accepted
date: 2026-10-10
authors: [Tristan Rivoallan]
supersedes: []
---

# Vocabulaire du journal pour une reconstruction, et transit obligatoire

> Première décision propre à `uske` : les douze autres sont héritées de la méthode. Verdict
> `accepted` reçu de Tristan Rivoallan le 2026-10-10 ; le code du change `issue-transformation`
> s'y conforme. Les numéros `SDR-0014` et `SDR-0015` sont réservés par le change
> `demenagement-gitlab-et-livraison`.

## Context and Problem Statement

Depuis le change `issue-transformation`, `uske` fait reconstruire par le placeur une source que
le juge envoie en réparation, retient la sortie dans un transit, la fait juger, et ne laisse
promouvoir que ce qui est sain. Deux choix de ce change engagent les suivants.

**Le journal est en ajout seul.** Ce qu'il porte ne se rature pas : un nom de clé ou une raison,
une fois écrits dans un journal réel, y restent. Or ce change en introduit quatre.

**Sans transit, la réparation serait dangereuse.** Une source à réparer que l'on rend au placeur
sans lieu où retenir sa sortie est reconstruite et placée sans que rien n'ait jugé ce qui a été
construit.

Le raisonnement complet, les alternatives pesées et les limites vivent dans
`openspec/changes/issue-transformation/design.md`, décisions D3, D5, D6 et D7. Cet ADR n'en
retient que ce qui dure.

## Considered Options

* **Ne rien écrire sur la source d'une reconstruction refusée**, et laisser le filtrage chercher
  une image retenue refusée qui la nomme — écartée : la version resterait « à réparer » au
  journal alors qu'elle est refusée.
* **Un interrupteur pour se passer de transit** — écartée : c'est le cas dangereux ci-dessus.
* **Un vocabulaire fixé, et un transit obligatoire** — retenue.

## Decision Outcome

**Le vocabulaire du journal**, fixé :

| Élément | Où | Ce qu'il dit |
| --- | --- | --- |
| clé `source` | ligne d'une image retenue | l'empreinte de la source dont elle a été reconstruite |
| clé `rebuilt` | ligne de clôture d'une source | l'empreinte de l'image retenue qui a été refusée |
| raison `uske/rebuild-refused` | ligne de clôture, état `quarantine` | la reconstruction a été jugée et refusée ; ce n'est pas un verdict du juge sur la source |
| raison `uske/reopened` | ligne ajoutée à la main, état `inconclusive` | une personne rouvre une source ; elle sera rejugée |

**Le journal n'avance que vers l'avant** : une ligne plus ancienne que la plus récente du même
digest n'est pas écrite. C'est ce qui tient « une source close reste close » quand une étape est
rejouée.

**Le transit est obligatoire** dès que le workflow nomme une seconde porte : sans entrée de
transit, le placeur refuse d'appliquer et rien n'entre, copies comprises.

### Consequences

* Bon : un refus de reconstruction se lit au journal, sur la source, avec le rapport qui
  l'explique ; une source close ne se rouvre pas par accident.
* Bon : aucune image reconstruite n'atteint une destination sans son propre verdict.
* Coût : la clôture porte sur l'empreinte source, donc sur toutes ses variantes et destinations.
* Coût : tout déploiement doit nommer un transit, même s'il ne reconstruit rien.
* Coût : tout lecteur du journal — la story 3 la première — doit lire la raison, et pas seulement
  l'état : `quarantine` a désormais deux sens.

## More Information

Preuve sur le banc local le 2026-10-10, consignée dans
`openspec/changes/issue-transformation/tasks.md` : une réparation réussie promue et signée, une
réparation refusée close et jamais retentée, une source rouverte à la main puis rejugée.
