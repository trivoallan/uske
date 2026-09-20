# Context
# nanopm uses this to challenge your product thinking. Edit freely.
# Lines marked [auto] were pre-filled — verify they're accurate.

1. What are you building? (one sentence, no jargon)
   [auto from README.md] Un outil qui, sur planification, fait juger des images de conteneur par `regis`, laisse `knock` ne placer dans le registre que celles qui sont admises, et consigne chaque décision dans un journal qu'on ne réécrit jamais.

2. Who is the primary user? (job title, company size, situation)
   [auto from personas] La responsable plateforme qui tient le registre d'images interne. Aujourd'hui : l'auteur, dans l'équipe plateforme de son employeur.

3. What is the single most important thing users do with it today?
   [auto from product map] Rien : `uske` n'est déployé nulle part. Le seul screening jamais lancé l'a été à la main, sur le banc local kind.

4. What did you ship in the last 30 days?
   [auto from git log] L'essaimage du code depuis `docs/orchestrator/` (un commit, 2026-09-20), puis la méthode : onze ADR statués, l'arc42 (deux sections), la discovery et ses cinq stories. Aucune fonctionnalité depuis l'essaimage.

5. What are your top 1-2 goals for this quarter?
   [auto from openspec/discovery.md, Must] Un screening planifié qui tourne pour de vrai, hors du banc local ; puis pouvoir retrouver et expliquer un refus.

6. What are your users doing RIGHT NOW when your product doesn't cover their need?
   [auto from discovery + FEEDBACK] Des scripts et des chaînes d'intégration maison, écrits équipe par équipe, où jugement et placement sont mêlés ; rien de planifié uniformément, rien de contestable après coup. Le coût n'est pas chiffré, et ce constat vient de l'auteur seul : aucun retour utilisateur n'existe.

7. What have you explicitly decided NOT to build, and why?
   [auto from discovery] Une colle générique pour d'autres juges ou placeurs (uske connaît ses deux voisins, c'est voulu) ; toute interface graphique ou console (les trois personas lisent du texte).

8. Who are your 3 most important users/customers right now?
   [auto] Un seul : l'auteur. Ensuite, non encore rencontrées comme utilisatrices : l'équipe plateforme de l'employeur, puis ses équipes applicatives.

9. What is the one metric that matters most to you right now?
   Le nombre de screenings planifiés qui vont au bout, sans l'auteur, sur le registre de l'employeur. (réponse du 2026-09-20)

10. What's the biggest thing you're uncertain or worried about?
    Que ça ne tienne pas en réel : jamais confronté à un vrai Harbor, un vrai Argo, un vrai volume d'images. (réponse du 2026-09-20)
    Réponse au challenge 1 (« les pairs laisseront-ils uske écrire sur le vrai Harbor ? ») : oui — « ça fait partie d'un effort de modernisation de la supply chain. Je suis soutenu par mes pairs et ma direction. » (2026-09-20). Soutien déclaré ; le compte robot de production n'existe pas encore.

11. What development methodology does your team use?
    [auto from docs/adr + openspec] Kanban — flux continu de stories OpenSpec, une à la fois ; github-flow, squash.

12. How does this project ship?
    [auto from arc42 Stakeholders + git shortlog] a) Solo + AI agents — un auteur, des agents qui écrivent les changes.
