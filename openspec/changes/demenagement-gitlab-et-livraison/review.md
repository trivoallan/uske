# Review

## Grilles retenues

Trois grilles, choisies par ce que le livrable fait à qui lui fait face.

- **DevEx** — `deploy/base` se consomme depuis un autre dépôt, et l'image se tire depuis un
  cluster. Quelqu'un d'autre que l'auteur écrira la surcouche un jour.
- **Contrôle** — la chaîne refuse : titre de fusion hors format, ADR laissé vide, manifestes qui
  ne se rendent plus. Une grille de contrôle demande ce qu'un refus coûte et ce qu'il laisse
  passer.
- **Ingénierie** — le déménagement de forge est cher à défaire, et le plan tient dans une demande
  de fusion qui touche une cinquantaine de fichiers.

Revue conduite à la main, sur `proposal.md`, `design.md` et les deux deltas de spécification. Les
skills `plan-devex-review` et `plan-eng-review` n'ont pas été lancées : elles s'invoquent avec
l'aval de la personne, qui n'a pas été demandé pour cet artefact.

## Findings et traitement

| # | Grille · dimension | Finding | Sévérité | Traitement |
| --- | --- | --- | --- | --- |
| 1 | Contrôle · portée du refus | `ci.gate` vaut `informative` aujourd'hui, faute de protection de branche. Une chaîne rouge n'empêche donc rien : `DEBT-06` se refermerait sur « la vérification est lancée », pas sur « une décision vide ne passe plus ». | Majeure | `SDR-0014` écrit `ci.gate` d'après ce que l'instance permet, et la clôture de `DEBT-06` dans arc42 dit laquelle des deux choses est acquise. Si la protection existe, `bloquante` ; sinon, l'écart se marque *Closed* avec sa réserve écrite. |
| 2 | Contrôle · contournement | `commitlint` ne s'exécute que dans le contexte d'une demande de fusion. Sans protection de branche, une poussée directe sur `main` échappe au contrôle, et `releaser-pleaser` en déduit une version depuis un message que rien n'a vérifié. | Majeure | Même traitement que le finding 1 : la protection de branche est ce qui ferme le contournement. Le noter dans `SDR-0014` plutôt que de laisser croire le contrôle total. |
| 3 | DevEx · contrat implicite | Le contrat de la base tient en trois chemins, quatre images à épingler et quatre noms de secrets — et rien ne l'écrit pour celui qui écrira la surcouche. Le `git` des quatre images a d'ailleurs été oublié une première fois pendant la conception. | Majeure | Une page de `docs/` explique comment consommer la base depuis un autre dépôt. Elle entre au plan de documentation de `tasks.md`, avec son quadrant et son destinataire. |
| 4 | DevEx · contrôle décoratif | Si `deploy/example` n'emploie pas réellement les trois chemins, le lint passe sans rien prouver, et la base peut casser pour un consommateur extérieur sans que la chaîne le dise. | Majeure | La surcouche d'exemple emploie les trois chemins, épingle les quatre images, et la tâche de vérification l'exige explicitement plutôt que de se contenter d'un rendu vert. |
| 5 | Ingénierie · relisibilité | Une seule demande de fusion porte le renommage mécanique (environ 75 occurrences dans 24 fichiers), la chaîne, trois ADR, arc42 et la version. Personne ne relit utilement cet ensemble. | Majeure | Deux demandes de fusion : le renommage seul d'abord, vérifié par le banc `kind` ; puis la forge, la chaîne, la release et les ADR. Le découpage de `tasks.md` suit cet ordre. |
| 6 | Contrôle · fuite par les journaux | Les noms internes passent par des variables de chaîne parce que le dépôt est miroité en clair. Une variable non masquée réapparaît dans un journal de travail, et le miroir reste public. | Majeure | Variables masquées et protégées ; aucun `echo` d'une variable dans un job ; le job d'image ne s'exécute que sur un tag protégé. |
| 7 | Contrôle · asymétrie de confiance | `knock` signe et atteste tout ce qu'il place, mais l'image de `uske` — celle qui décide — est construite et poussée sans signature ni attestation. L'orchestrateur est le maillon le moins attesté de la chaîne qu'il commande. | Mineure | Hors périmètre de ce change, et nommé comme écart candidat dans `tasks.md` afin qu'il ne s'oublie pas. `cosign` est déjà dans l'image : le geste est petit, mais il appartient à un change qui le vérifie. |
| 8 | Ingénierie · fenêtre sans chaîne | `.github/workflows/` disparaît dans la même fusion qui pose `.gitlab-ci.yml`. Si le projet GitLab n'a pas d'exécuteur capable de construire une image, le dépôt se retrouve sans aucune vérification automatique. | Mineure | Ajouter aux faits à établir avant d'écrire : un exécuteur existe, et il sait construire une image. La première demande de fusion doit tourner au vert avant que la seconde ne supprime `.github/`. |
| 9 | Ingénierie · ce que le déménagement laisse | Ce qui reste sur GitHub : quatre demandes de fusion, **zéro commentaire**, **zéro issue** — vérifié le 2026-09-20. Le miroir emporte l'historique des commits, pas les fils de discussion. | Mineure | Rien à traiter : le fait est consigné, et le coût du déménagement est nul de ce côté. |
| 10 | DevEx · repli non éprouvé | Le repli du finding 1 sur la vérification des ADR — binaire autonome si Node manque — est écrit dans la conception mais ne sera éprouvé que le jour où il servira. | Mineure | La tâche qui écrit le job nomme les deux chemins et dit lequel a été essayé, plutôt que de laisser croire que les deux le sont. |

## Critère d'achèvement

La revue est close quand les six findings majeurs ont leur traitement inscrit dans `tasks.md` :
les findings 1 et 2 dans la tâche qui écrit `SDR-0014` et dans celle qui referme les écarts ; le 3
au plan de documentation ; le 4 dans la tâche de vérification de la surcouche d'exemple ; le 5 dans
le découpage en deux demandes de fusion ; le 6 dans la tâche qui pose les variables de la chaîne.
Les quatre mineurs sont consignés, et le 7 porte un écart nommé.
