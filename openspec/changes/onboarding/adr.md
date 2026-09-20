# ADR Review Manifest

- Status: completed
- Review date: 2026-09-20

## Review Summary

ADR review completed for this change.

Le dépôt range ses ADR sous `docs/adr/`, non sous `adr/` à la racine : c'est ce répertoire qui
a été parcouru. Onze fichiers, aucun champ `supersedes` renseigné : le graphe de dépassement
est vide. Plus haut numéro en usage : `SDR-0011`.

Ce change n'introduit aucune décision d'architecture durable qui lui soit propre : ses six
décisions de conception (`design.md`, D1 à D6) règlent la conduite du change, pas le système.
Les décisions durables qu'il fait naître **sont** les verdicts des dix ADR hérités, rendus à
l'application, dans les fichiers qui existent déjà. Statuer un ADR `proposed` n'est pas
modifier un ADR `accepted` : tant qu'il est `proposed`, le fichier « s'écrit et se corrige
librement », dit chacun d'eux. Aucun ADR `accepted` n'est touché.

## In-Force ADRs Reviewed

- `docs/adr/SDR-0001-record-architecture-decisions.md` — `accepted`, 2026-08-29, non dépassé.
  Contraint ce change : format MADR, en-têtes en anglais ; frontmatter source machine ; corps
  gelé à `accepted`, seul le `status` s'écrit encore ; dépassement par un nouvel ADR ;
  vérification par schéma qui atteste sans refuser. `design.md` s'y plie (D1, D4).

Non en vigueur, lus comme contexte : `SDR-0002` à `SDR-0011`, tous `proposed`.

## New Durable ADRs Created

- None - no major durable architectural decisions were introduced, and no new
  repository-level ADR files were created. Dix ADR existants recevront leur verdict à
  l'application ; le tableau final du change en rendra compte.
