---
adr: SDR-0023
slug: workflow-github
title: Hors du cluster, un workflow GitHub réutilisable, et le journal sur une branche du dépôt appelant
status: accepted
date: 2026-10-17
authors: [Tristan Rivoallan]
supersedes: []
---

# Hors du cluster, un workflow GitHub réutilisable, et le journal sur une branche du dépôt appelant

> Verdict `accepted` reçu de Tristan Rivoallan le 2026-10-17, après le banc qui a éprouvé chaque
> scénario sur GitHub. Le raisonnement complet, les alternatives et les risques vivent dans
> `openspec/changes/github-action/design.md`, décisions D1 à D7 et D2bis ; la revue dans
> `review.md`. Le banc `extra-screen-example.yml` les a éprouvées sur GitHub, reconstruction
> promue comprise. Cet ADR n'en retient que ce qui engage les changes suivants.

## Context and Problem Statement

`uske screen` (SDR-0021) permet de cribler hors du cluster, mais rien ne le livrait : chaque dépôt
de politiques sur GitHub recomposait l'installation d'`uske`, les images de `regis` et `knock`, un
démon BuildKit, le verrou par politique et l'écriture du journal dans git. C'est la dérive que
SDR-0021 a fermée pour `screen.sh`. Hors du cluster, le journal n'a pas non plus de support :
SDR-0016 en fixe le vocabulaire, pas le stockage (`DEBT-08`).

## Considered Options

* **Un exemple à recopier** : écartée, chaque copie dérive.
* **Une action composite** : écartée ; l'appelant devrait déclarer lui-même le verrou par
  politique, les permissions et l'enchaînement de deux jobs.
* **Un workflow réutilisable (`workflow_call`)** : retenue.
* **GitHub Actions comme planificateur de production** (cron et matrice sur toutes les
  politiques) : écartée ; la matrice plafonne à 256 jobs, et Argo reste le candidat pour 10 000+
  politiques (`DEBT-07`).
* **Le journal sur la branche par défaut, dans un dépôt séparé, ou en artefact** : écartées ;
  bloqué par la protection de `main`, un jeton de plus, ou rien de durable.

## Decision Outcome

* **L'interface publique est `.github/workflows/extra-screen.yml`**, ses entrées et ses secrets.
  Les renommer casse les appelants : un changement cassant, noté au CHANGELOG, précédé d'une
  dépréciation d'une mineure. Elle se nomme par une étiquette mobile, `v0.N` en 0.x puis `vN`.
* **Une étiquette d'`uske` désigne un trio** : `uske` de cette version, `regis` et `knock` à des
  versions écrites dans le workflow et suivies par Renovate, sans lier les trois paquets.
* **Hors du cluster, le journal vit sur une branche dédiée du dépôt appelant** (`uske-journal`),
  poussée après chaque écriture et une dernière fois à la fin. L'historique de cette branche rend
  l'ajout seul vérifiable, à l'échelle d'un dépôt. Les rapports partent dans une archive du run.
* **Le placeur signe sans clé par défaut**, avec l'identité OIDC du workflow appelé, ou par une clé
  cosign que l'appelant fournit.

### Consequences

* Bon : un dépôt de politiques crible en un job, avec le même verbe qu'en local.
* Bon : `RISK-01` a une réponse hors du cluster.
* Coût : un nom de fichier et des entrées figés comme interface.
* Coût : sans jeton de registre dédié, `GITHUB_TOKEN` atteint le juge et le placeur (`RISK-08`) ;
  la signature sans clé est acceptée de tout dépôt qui appelle le workflow (`RISK-09`), jusqu'à un
  change de `knock` ; elle inscrit chaque image placée dans Rekor public (`RISK-10`).
* Ne décide ni le planificateur (`DEBT-07`) ni le support du journal dans le cluster (`DEBT-08`).
