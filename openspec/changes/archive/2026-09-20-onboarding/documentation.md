# Plan de documentation

Le corpus Diataxis n'existe pas encore : `SDR-0008` dira s'il y en a un, et où. Aucune page de
ce plan n'y entre ; la colonne Quadrant porte donc `—` partout. La langue de la prose attend le
verdict de `SDR-0002` : tant qu'il est `proposed`, `french-language` ne s'invoque pas.

| Chemin | Quadrant | Destinataire | Geste |
| --- | --- | --- | --- |
| `openspec/discovery.md` | — | la personne ou l'agent qui propose le prochain change | créée (au premier artefact) |
| `docs/adr/SDR-0002-localization.md` | — | l'agent qui écrit du code, des commentaires, des commits ou de la prose | modifiée |
| `docs/adr/SDR-0003-architecture.md` | — | l'agent qui conçoit un change ; le contributeur qui cherche le document d'architecture | modifiée |
| `docs/adr/SDR-0004-languages.md` | — | l'agent qui ajoute du code | modifiée |
| `docs/adr/SDR-0005-validation.md` | — | l'agent qui écrit une frontière d'entrée ou un fichier de données | modifiée |
| `docs/adr/SDR-0006-commits.md` | — | quiconque écrit un message de commit | modifiée |
| `docs/adr/SDR-0007-tests.md` | — | l'agent qui écrit ou juge des tests | modifiée |
| `docs/adr/SDR-0008-documentation.md` | — | l'agent qui écrit une page ; le lecteur qui cherche où elle est | modifiée |
| `docs/adr/SDR-0009-branching.md` | — | quiconque ouvre une branche ou une merge request | modifiée |
| `docs/adr/SDR-0010-forge-and-ci.md` | — | l'agent qui touche à l'intégration continue | modifiée |
| `docs/adr/SDR-0011-delivery.md` | — | la personne qui livre ou déploie | modifiée |
| `docs/architecture/arc42.md` | — | le contributeur qui arrive ; l'auditeur qui veut les objectifs et les décisions en un lieu | créée |
| `README.md` | — | l'arrivant qui lit le dépôt pour la première fois | modifiée — une courte section qui mène à `docs/adr/`, à `docs/architecture/arc42.md` et à `openspec/discovery.md` |

`CLAUDE.md` n'est pas touché : les ADR disent que les valeurs s'écrivent chez eux « et nulle
part ailleurs ». Un ADR resté *sans réponse* à l'application sort de ce plan : son fichier ne
bouge pas.
