---
adr: SDR-0013
slug: frontend
title: Frontend
status: proposed
date:
authors: []
supersedes: []
traits:
  frontend:
    framework:
    wcs_theme:
---

# Frontend

> **Qu'est-ce que ce fichier ?** Un ADR — *Architecture Decision Record* — est une décision consignée : son contexte, les options pesées, ce qui a été retenu, et ce que ça coûte. **Tant qu'il porte `status: proposed`, il s'écrit et se corrige librement.**
>
> **`rejected` est une réponse pleine, pas un abandon.** Quand la question ne se pose pas dans ce dépôt, l'ADR reçoit le verdict `rejected` avec son motif, et le bloc `traits:` disparaît en entier — une clé sans objet ne se laisse pas vide. Le motif dit alors **ce qui en tient lieu**, pour qu'un agent qui le lit sache à quoi s'en tenir. **Un ADR `rejected` sans bloc `traits:` passe la vérification** — c'est mesuré, pas supposé.

## Context and Problem Statement

**Concrètement, ce que statuer change.** Tant que ces deux clés sont vides, un agent qui écrit une interface pour ce dépôt choisit lui-même le framework, le design system et les skills — et il choisit autrement au projet suivant. Une fois les deux valeurs écrites, il pose Angular et WCS sans délibérer, et il sait de quelle entité ce dépôt porte les couleurs.

**Ce que ce fichier ne décide pas.** Le runner de tests, sa commande et sa sortie attendue se déclarent dans `## Testing` de votre contexte agent ; le seuil de couverture vit dans [`SDR-0007`](SDR-0007-tests.md). Rien de cela ne se recopie ici : deux endroits pour la même chose se contredisent tôt ou tard.

**Ce qui n'est pas ici** : React, Next.js, le rendu serveur, les contrôles WCS autres que le champ texte, et toute règle de mise en page.

**`rejected` est la réponse d'un dépôt qui ne livre pas de front Angular**, et son motif dit **ce qui en tient lieu** — voir `## More Information`.

**D'où viennent les faits de ce fichier.** Les constats viennent d'un essai joué le **2026-09-19** sur une application jetable créée pour ça : Angular **22.1.8**, `wcs-core` et `wcs-angular` **7.8.0**. La page du D2D a été lue le **2026-09-20**. **Tout n'a pas été mesuré** : chaque règle dit si elle est **constatée** ou **non vérifiée**, et « non vérifié » ne veut pas dire « faux ».

## Considered Options

**Ces options ne pèsent que `frontend.framework`.** Le thème ne se délibère pas : il dépend de l'entité à laquelle ce dépôt appartient. La méthode en propose un par défaut, et ce défaut se vérifie — voir `## Decision Outcome`.

* **Angular** : le groupe le prescrit pour un SPA comme pour un rendu serveur (page du D2D `https://dev.sncf/ressources/frameworks-libs/frontend`, lue le 2026-09-20). C'est aussi le seul des trois dont le paquet WCS livre une skill d'agent — `wcs-angular@7.8.0`, `skills/wcs-angular/SKILL.md`. Le coût : une majeure à suivre, et un design system dont le paquet ne livre pas tout.
* **React** : la même page ne le donne que pour le rendu de composants. `wcs-react@7.8.0` ne livre aucune skill — un `README.md` et un `dist/` — et ne déclare aucune `peerDependencies` : un agent qui l'emploie n'a rien à lire, et rien ne l'avertit d'une version de React incompatible.
* **Next.js** : la même page le classe « Utilisé », pas prescrit. Le rendu serveur est hors du périmètre de ce fichier.

**La page du D2D n'est pas recopiée ici**, ni la liste de bibliothèques qu'elle tient : maintenue ailleurs, elle vieillirait dans ce fichier. Elle est citée avec sa date de lecture, et c'est elle qui fait foi.

## Decision Outcome

**La réponse que la méthode propose, et ses motifs.**

| Clé | Valeur proposée | Motif |
| --- | --- | --- |
| `frontend.framework` | `angular` | c'est ce que le groupe prescrit pour un front (page du D2D citée ci-dessus, lue le 2026-09-20), et le seul framework dont le paquet WCS livre une skill d'agent |
| `frontend.wcs_theme` | `sncf-holding` | c'est le thème de l'entité qui publie cette méthode. Deux autres valeurs existent — `sncf-reseau`, `sncf-voyageurs` — et **celle-ci ne vaut que si votre dépôt porte les couleurs de la Holding** : un thème gardé par défaut habille l'application aux couleurs d'une autre entité, sans que rien ne le dise |

**`frontend.framework` n'est pas une proposition parmi d'autres** : c'est la seule valeur que la clé admette. La refuser, ce n'est pas écrire autre chose ici, c'est **statuer `rejected`** — voir `## More Information`. `frontend.wcs_theme`, elle, est modifiable comme toute proposition — et c'est la seule des deux qui appelle une vérification avant d'être gardée : la valeur proposée est celle de l'amont, pas la vôtre.

**Les règles de tout front qu'un agent écrit pour ce dépôt.** Elles valent quel que soit l'écran ; une règle sans objet pour le vôtre se dit sous Consequences. Elles survivent à la coupe. L'essai qui les établit a tourné le **2026-09-19**, sur **Angular 22.1.8** et **WCS 7.8.0** ; ce que cet essai n'a pas couvert est dit à la règle concernée, et la règle 10 ne repose que sur la page du D2D.

**L'ordre des gestes**, pour un front qui part de rien. Il va de la création au **premier écran rendu** : un geste qui manque ici est un défaut de ce fichier, pas une évidence laissée au lecteur.

1. **Monter `npm` s'il est sous le plancher** (règle 13) — avant tout le reste, sinon la création échoue.
2. **Créer le projet** (règles 2 et 3).
3. **Supprimer le `.mcp.json`** que le CLI engendre (règle 4).
4. **Poser WCS** (règle 6).
5. **Appeler `defineCustomElements()` dans `main.ts`** (règle 15) — sans cet appel, aucun composant WCS n'existe.
6. **Poser les polices et les icônes**, et leurs `@font-face`.
7. **Importer le thème et poser sa classe sur `<body>`** (règle 15) — sans la classe, les tokens du thème ne s'appliquent pas.
8. **Régler le serveur de développement** (règle 14) — sans ce réglage, la page reste vide.
9. **Poser les deux skills.**
10. **Jouer les commandes de `### Confirmation`.**

| # | Règle | Ce qui l'établit |
| --- | --- | --- |
| 1 | **Angular, sur une majeure épinglée : la 22.** Aucune fourchette de version ne franchit la majeure. | **constaté** : Angular 22.1.8 et WCS 7.8.0 compilent ensemble. **Non vérifié** sur une autre majeure — WCS 7.8 n'y a pas été essayé |
| 2 | **Le projet se crée par la commande ci-dessous**, telle quelle. Jamais `@latest`, jamais `npm install -g @angular/cli`. | une version résolue à l'exécution n'est pas une version épinglée : deux créations à deux dates ne donnent pas le même CLI, et rien ne dit ce qui a changé entre elles. La skill `angular-new-app` prescrit l'inverse — installation globale et `@latest` — et c'est elle qu'il faut écarter |
| 3 | **`--ai-config` prend une valeur que le CLI accepte** — `claude-code` pour un agent Claude Code. **Jamais `agents`.** | **constaté** le 2026-09-19 : le CLI 22.1.8 refuse `agents`, la valeur que la skill `angular-new-app` recommande. Ses valeurs admises sont `claude-code`, `cursor`, `gemini-cli`, `none`, `open-ai-codex`, `vscode`. Si le CLI refuse celle-ci, lisez `ng new --help` et prenez-en une de **sa** liste — jamais celle de la skill |
| 4 | **Le `.mcp.json` que le CLI génère se supprime**, avant le premier commit. | il lance `npx -y @angular/cli mcp`, soit une version résolue à l'exécution ; il redit ce que le `CLAUDE.md` généré dit déjà ; et le serveur qu'il déclare ordonne à l'agent de préférer ses outils au shell, ce qui concurrence vos propres consignes |
| 5 | **Le `CLAUDE.md` que le CLI génère reste**, dans le sous-dossier de l'application. | **constaté** : 59 lignes, la sortie de `get_best_practices` du serveur MCP. Il porte l'accessibilité en impératif et n'appelle rien à l'exécution |
| 6 | **`wcs-core` et `wcs-angular` à la même version exacte**, sans `^` ni `~`. | `wcs-angular` dépend de la version exacte de `wcs-core` : une fourchette produit un arbre à deux versions de `wcs-core`, où les tokens de l'une habillent les composants de l'autre |
| 7 | **`WcsAngularModule` s'importe dans le `imports` d'un composant standalone.** | **constaté** le 2026-09-19. Le `CLAUDE.md` généré dit « Always use standalone components over NgModules » : ce n'est pas une interdiction d'importer **ce** module, et un agent qui le croit ne peut plus employer aucun composant WCS |
| 8 | **Le style passe par les tokens et le thème WCS.** Pas de Tailwind ; pas de couleur, de graisse ni d'espacement en dur. | un token porte la décision de l'entité et suit ses montées de version ; une valeur en dur la fige au jour où elle a été copiée. La seconde commande de `### Confirmation` en attrape une part, et dit laquelle |
| 9 | **Formulaires : Signal Forms avec `[formField]` sur un `wcs-input`** ; **Reactive Forms** pour tout autre contrôle WCS. | **constaté** le 2026-09-19 : un `wcs-input` lié par `[formField]` met à jour le modèle. **Le sens inverse aussi**, constaté le 2026-09-20 — mais **en différé** : la nouvelle valeur atteint le `<input>` du shadow DOM entre 3 ms et ~530 ms après la mise à jour du modèle. Une assertion qui lit tout de suite voit l'ancienne valeur, et le champ affiche un texte que le modèle ne porte plus. **Non vérifié** : tout autre contrôle WCS. Tant qu'un contrôle n'a pas été éprouvé, c'est Reactive Forms |
| 10 | **Tests de bout en bout : Playwright**, avec les deux utilitaires que le D2D publie dans ses *shared libs front* (monorepo) : « Se logger sur la FID de DEV via Playwright » et « Mocker une authentification à la FID pour la lib angular-oauth2-oidc ». **Deux pièges font échouer une assertion pourtant juste** : la propagation différée de la règle 9 — attendez, ne lisez pas tout de suite —, et le fait que `wcs-app` fasse de sa zone de contenu **son propre conteneur de défilement**, si bien que le `<body>` ne défile pas et qu'un test doit défiler `main`. | la page du D2D, lue le 2026-09-20, nomme les deux utilitaires dans ces termes. Elle **ne donne ni nom de paquet ni version** : ce fichier ne dit donc pas comment les installer, et c'est au D2D qu'il faut le demander. **Non vérifié** : aucun essai de bout en bout n'a été joué pour ce fichier. Les deux pièges, eux, sont **constatés le 2026-09-20** |
| 11 | **Le runner de tests ne se décide pas ici.** Il se déclare dans `## Testing` de votre contexte agent ; le seuil de couverture est celui de [`SDR-0007`](SDR-0007-tests.md). | la skill Angular prend Vitest. Si votre dépôt lance autre chose, c'est `## Testing` qui fait foi, et ce fichier n'a pas à le contredire |
| 12 | **Déroger à l'une de ces règles se déclare** dans un ADR local, avec son motif. | la dérogation se lit alors dans le dépôt. Un contournement silencieux n'en est pas une |
| 13 | **`npm` au moins en 11.6.0**, sans quoi la création du projet échoue. | **constaté le 2026-09-20** par bissection sur les 33 versions 11.x stables : dernière en échec **11.5.2**, première qui passe **11.6.0**. **Toute la série 10 échoue**, `10.9.9` — la dernière jamais publiée — comprise. Angular ne l'impose pas : ses `engines` acceptent `npm >=8.0.0`. Voir la puce sous la commande de création |
| 14 | **Le serveur de développement charge les composants WCS seulement si `angular.json` porte `"serve": { "options": { "prebundle": { "exclude": ["wcs-core"] } } }`.** | **constaté le 2026-09-20** : sans ce réglage, `wcs-input.entry.js` et `wcs-button_3.entry.js` tombent en 404 sous le serveur Vite d'Angular 22. Les éléments sont bien définis — `customElements.get('wcs-input')` répond — et la page reste vide, **sans erreur visible dans la page**. Le build de production les émet sans le réglage : un projet qui compile ne prouve rien ici |
| 15 | **Deux gestes conditionnent tout le reste et ne produisent aucun message quand ils manquent** : `defineCustomElements()` appelé dans `main.ts`, et la classe du thème posée sur `<body>` (`<body class="sncf-holding">`, ou la valeur de votre `frontend.wcs_theme`). | le guide de `wcs-angular` les porte à ses étapes 2 et 6. Sans le premier, aucun composant WCS n'existe ; sans la seconde, les tokens du thème ne s'appliquent pas et l'application s'affiche hors charte, **sans que rien ne le dise** |
| 16 | **`wcs-app` n'expose que les emplacements `header`, `sidebar` et `content` ; `wcs-header` que `logo`, `title`, `center` et `actions`.** Ce qui n'y est pas placé disparaît. | **constaté le 2026-09-20** : un contenu posé en enfant direct de `wcs-app` sans `slot="content"` ne s'affiche pas — **page blanche, aucune erreur, aucune trace en console**. Le composant est pourtant hydraté. C'est le second piège muet de ce fichier, après la règle 14 |

**La commande de création, telle qu'elle a été jouée le 2026-09-19**, depuis le répertoire qui doit accueillir l'application :

```bash
npm exec -- @angular/cli@22.1.8 new <nom> --interactive=false --style=scss --routing --skip-git --ai-config=claude-code --package-manager=npm
```

* **`<nom>` est le vôtre**, et ce fichier ne le choisit pas : `ng new` crée un sous-dossier de ce nom. L'application n'est donc pas à la racine de votre dépôt, et tout ce qui suit se joue depuis ce sous-dossier. Jouez la commande depuis la racine, sauf si votre dépôt range ses applications ailleurs — auquel cas c'est à vous de le dire, ce fichier l'ignore.
* **`--ai-config` nomme *votre* agent**, pas le nôtre. `claude-code` est la valeur de l'essai ; prenez celle qui correspond au vôtre dans la liste de la règle 3, ou `none` si aucune ne convient — le fichier généré est un texte de bonnes pratiques Angular, pas une pièce du montage.
* **La version de Node n'est pas dite ici**, et ce n'est pas un oubli : c'est Angular qui l'impose, et elle change à chaque majeure. Si la commande échoue sur la version de Node, lisez ce qu'`@angular/cli@22.1.8` exige — rien dans ce fichier ne vous préviendra avant.
* **La version de `npm`, elle, est dite ici, et c'est délibéré.** Angular ne l'impose pas — ses `engines` acceptent `npm >=8.0.0` — et pourtant la commande échoue en dessous de **11.6.0** :

  ```text
  npm error Cannot read properties of null (reading 'edgesOut')
  ```

  Le message ne nomme ni Angular, ni `npm`, ni ce qu'il faut faire. Il est levé dans `#loadPeerSet` d'arborist en résolvant `vitest → jsdom → canvas`, des dépendances que `ng new` pose lui-même. **Bissecté le 2026-09-20** sur les 33 versions 11.x stables : dernière en échec `11.5.2`, première qui passe `11.6.0` ; toute la série 10 échoue aussi, `10.9.9` comprise. Si votre `npm` est en dessous :

  ```bash
  npm install -g npm@11.6.0
  ```

  **C'est un plancher, pas une épingle** : un poste qui porte déjà une version supérieure ne redescend pas. Et **c'est mesuré sur l'arbre que pose `ng new` pour Angular 22** : une autre pile de dépendances pourrait échouer ailleurs. Si votre dépôt applique une règle qui interdit de monter le gestionnaire de paquets, cette montée est l'exception à déclarer, et elle se joue une fois.
* **`--package-manager=npm` n'est pas décoratif** : un second gestionnaire pose un second verrou dans le même arbre, et deux verrous ne disent pas la même chose. Un seul gestionnaire, et c'est `npm`.
* **`--ssr` n'a pas été essayé** : le rendu serveur est hors du périmètre de ce fichier, et rien ici ne dit ce qu'il change.

**Les skills : deux, et aucune par la clé `skills` de votre `package.json`.**

* **Celle de WCS voyage avec son paquet.** `wcs-angular@7.8.0` livre `skills/wcs-angular/SKILL.md` : installer le paquet suffit, il n'y a rien à épingler de plus. Sur ce qu'elle prescrit en vain, voir plus bas.
* **Celle d'Angular se pose une fois, à un tag daté**, depuis le dépôt de publication `angular/skills` :

  ```bash
  npm exec --yes -- skills@1.7.0 add "https://github.com/angular/skills#22.1.7+sha-f3358f2" -s angular-developer -a claude-code -y
  ```

  Le tag `22.1.7+sha-f3358f2` désignait, le 2026-09-19, le commit `519938caec77042e4dcf77d36f2b777e01c94f11` — la coupe de la version 22.1.7, du 2026-09-16. **Relisez ce commit avant de faire confiance au résultat** : le verrou que l'outil écrit consigne le **tag** et une empreinte du contenu installé, **pas le commit**, et un tag se déplace. Pour contrôler ce que vous avez reçu, le `SKILL.md` de ce commit a pour SHA-256 `ec5e3a0b1ef218c0d7d40e35c40e5255e7319d7d595c5a6036d8bdac2532c782` (relevé le 2026-09-19) :

  ```bash
  shasum -a 256 .claude/skills/angular-developer/SKILL.md
  ```

Trois choses constatées le 2026-09-19, sur un dépôt jetable qui portait déjà un `skills-lock.json` :

* **un SHA nu ne s'accepte pas** après `#` : l'outil passe la référence à un clonage par branche, qui refuse un commit. D'où le tag, et la relecture du commit à la main ;
* **l'outil interroge `skills.sh`** pour afficher une évaluation de risque : c'est un appel réseau vers un tiers, en plus du clonage. Si votre dépôt ne l'admet pas, copiez le répertoire `angular-developer/` à ce commit ;
* **la skill atterrit dans `.claude/skills/` du dépôt**, et part donc avec votre prochain commit. Le `skills-lock.json` existant **n'est pas écrasé** : l'outil y ajoute son entrée, et `package.json` ne bouge pas.

**Pourquoi aucune des deux ne passe par la clé `skills`** que la méthode fusionne dans votre `package.json` : cette clé s'applique à **tout** dépôt qui pose l'entrée, qu'il ait un front ou non — et la plupart n'en ont pas. C'est le même partage que pour l'outil de mise au point locale de [`SDR-0010`](SDR-0010-forge-and-ci.md), posé par sa propre commande et jamais par le manifeste.

**Ce que les paquets ne livrent pas : les polices Avenir et les icônes SNCF.** Elles ne sont dans aucun paquet npm de WCS. Le guide de `wcs-angular` les fait prendre sur la branche `master` du dépôt WCS : **ne faites pas cela** — une branche n'est pas une version, et son contenu change sous vos pieds. Prenez-les **au tag `7.8.0`**, commit `cb2d573986d86167d4c3cb3ff4d33e94c95c3ddc` (relevé le 2026-09-19), sous `example/angular/public/fonts/` — les six `avenir-*.woff`, et les cinq `icons.*` du sous-dossier `icons/`. Un fichier se lit à ce tag par l'API du dépôt, le chemin étant encodé :

```text
https://gitlab.com/api/v4/projects/13813721/repository/files/<chemin encodé>/raw?ref=7.8.0
```

Posez-les dans `public/fonts/` et `public/fonts/icons/` de l'application — c'est l'emplacement que le guide de `wcs-angular` emploie, et ce que sert Angular 18 et au-delà. **Vérifiez chaque fichier avant de vous en servir.** Les onze empreintes SHA-256, relevées le 2026-09-19 à ce tag :

```text
52bbc57b68d10e9cb50ad5d21c8dc26d42ffd033b79b6622f64ed2e67f690d81  avenir-black.woff
80188055e500d5bf12b021d0db3670b31fc7ed66b4c8ec5ee607e073f4652b83  avenir-book.woff
db061935b9c77519c77f99e131fcb9534d6e3008e5f4fee85934031cfa436d15  avenir-heavy.woff
857eae50831c3932689808777a2d61f0c85f31cb43bd24dac40b9cdcae331d1f  avenir-lighter.woff
164fc25bca96754cea1b507c6ab398826e18d81f768ac000dbec000d178cc401  avenir-medium.woff
a383f0e017a0d5d57486df39ec9d841c16dfceb26e92be448dd2d1d471c76edc  avenir-roman.woff
29b1413390fc3ff96c80cff9b6e3f0b8711c4f3980bdcb328ae7abbca15f809b  icons/icons.eot
2454d08451fcb48736f4aed7cf53087ddb537c5e05ac22a73c2fec8852772d7d  icons/icons.svg
0da36cf7438c2f19dc8821d447e028fff08c755e5d19950fed8e040126c78e54  icons/icons.ttf
54c53bf88694e03c93ffd38d94b2f26de02214c81ae10229f201daa47a1386bd  icons/icons.woff
274a93c94f49e6a2e9dfa0120a91568141cbd8770a014453afee59071e5ddd18  icons/icons.woff2
```

Posez ces lignes dans un fichier à côté des polices, puis, depuis ce répertoire :

```bash
shasum -a 256 -c empreintes.txt   # ou : sha256sum -c empreintes.txt
```

* **Une empreinte qui diffère arrête la pose**, avant que le fichier serve : supprimez-le, ne le servez à personne, et dites-le.
* Ces onze fichiers se posent **une fois**. `npm update` ne les touchera jamais : une montée de WCS demande de les reprendre au nouveau tag et d'en relever les empreintes de nouveau.
* Les `@font-face` **locaux** — ceux d'Avenir et ceux des icônes SNCF — s'écrivent dans votre feuille de style globale, et ne pointent que sur les fichiers que vous venez de poser. Six familles `Avenir`, une par graisse (`avenir-lighter` 100, `avenir-book` 300, `avenir-roman` 400, `avenir-medium` 500, `avenir-heavy` 800, `avenir-black` 900), et une famille `icons` qui sert les cinq fichiers `icons.*`. Leur forme exacte est dans `node_modules/wcs-angular/skills/wcs-angular/references/getting-started.md`, que vous avez déjà sur disque après l'installation : **ce fichier ne la recopie pas**, elle vieillirait ici.

**Et malgré tout cela, `wcs-icon` ne rend rien en 7.8.0.** Ce n'est pas une erreur de pose : les onze fichiers ci-dessus sont exacts et complets pour leurs deux répertoires — vérifié contre l'arbre du dépôt WCS au tag. Le composant émet `<i class="icons-<nom>">`, et **aucune règle `.icons-*` n'existe nulle part** : ni dans `wcs-core@7.8.0`, ni dans le `doc/base.scss` du dépôt WCS à ce tag, ni dans le `styles.scss` de son propre exemple Angular. La police est chargée, ses 192 glyphes sont là, et rien ne permet de les adresser. **Constaté le 2026-09-20** : rendu `0x0`, avec un nom de glyphe valide.

**Posez les onze fichiers quand même** — ils servent aux `@font-face` d'Avenir, qui fonctionnent. Mais **n'attendez pas d'icône SNCF** tant que WCS ne livre pas la feuille de style qui les adresse, et ne cherchez pas l'erreur chez vous. Voir `## More Information` pour l'issue ouverte.

**Les Material Icons, elles, ne sont pas recopiées ici — et vous ne pouvez pas vous en passer.** Le guide de WCS charge cette police-là depuis `fonts.gstatic.com` : chaque poste qui ouvre l'application appelle alors un tiers, à chaque visite.

**Ce n'est pas un choix d'usage : WCS les émet lui-même.** Sur une page d'essai portant les 73 composants, le 2026-09-20, **13 occurrences de `.material-icons`, dont 12 émises par les composants du paquet** et une seule écrite à la main — `wcs-galactic`, `wcs-button` par son `startIcon`, `wcs-counter` pour ses deux boutons, `wcs-editable-field`, `wcs-alert` pour son icône et sa fermeture, `wcs-message`, `wcs-modal`. Une version antérieure de ce fichier concluait « n'employez pas ces icônes » : **cette consigne était intenable**, puisque ce n'est pas le lecteur qui les appelle.

**Sans la police, ces composants affichent la ligature en clair.** On lit `close`, `error`, `check_circle`, `add`, `remove`, `edit`, `more_horiz` à l'écran, à la place des icônes — constaté, et c'est l'état par défaut d'un projet monté selon ce fichier. Le même symptôme se produit hors ligne, derrière un proxy d'entreprise qui bloque `fonts.gstatic.com`, et sous une `Content-Security-Policy` stricte qui ne déclare pas `font-src`.

**Deux issues, et il faut en prendre une :**

* **héberger la police** avec les autres, sous `public/fonts/`, et écrire ses `@font-face` en local. Aucun appel externe, aucune dépendance de disponibilité, et une empreinte vérifiable comme pour les onze autres fichiers ;
* **garder l'appel à `fonts.gstatic.com`**, en écrivant un ADR local qui l'admet avec son motif. Si votre application pose une `Content-Security-Policy`, elle doit alors déclarer `font-src https://fonts.gstatic.com`, faute de quoi la police ne charge pas et vous retombez sur les ligatures en clair, **sans message**.

**Ce fichier ne tranche pas à votre place, et ne donne pas ces `@font-face`** : le guide de `wcs-angular` les porte, avec cinq familles. Mais il ne vous laisse plus croire que ne rien faire est une option : ne rien faire, c'est livrer une interface qui affiche `close` en toutes lettres.

**Notez qu'aucune empreinte ne peut protéger une police chargée ainsi** : `@font-face` n'admet pas d'attribut d'intégrité. Les onze fichiers locaux en ont onze ; celle-ci n'en aura aucune. C'est un argument de plus pour la première issue.

**Le contrôle des tokens ne peut pas être celui que la skill de WCS prescrit.** `wcs-angular@7.8.0` déclare un contrôle « mandatory » et renvoie à `wcs-core/skills/wcs-core/…` et à `scripts/audit-tokens.js` : ces fichiers sont **absents de `wcs-core@7.8.0`**, constaté le 2026-09-19.

**Ce renvoi cassé emporte bien plus que ce contrôle.** Le `SKILL.md` de `wcs-angular` dirige **toute sa table de composants** vers `wcs-core/skills/wcs-core/references/components/`, soit une fiche par composant : un agent qui cherche l'API de `wcs-grid` ou de `wcs-select` ne trouve rien. Constaté le 2026-09-20. Ce n'est donc pas un script qui manque, c'est la documentation par composant du design system. Une issue a été ouverte chez WCS par l'auteur de ce fichier — l'adresse qu'il donne est `https://gitlab.com/SNCF/wcs/-/work_items/547` —, **son état n'a pas été relu depuis son ouverture**, et ce fichier ne présume d'aucun correctif. Ce qui tient lieu de contrôle est la seconde commande de `### Confirmation`, qui ne dépend d'aucun script du paquet. **N'inventez pas de contournement** et ne déclarez pas le contrôle passé : si le script reparaît dans une version ultérieure, c'est à ce moment qu'il reprend sa place.

**Tout ce qui suit disparaît quand vous statuez** — de cette phrase-ci **jusqu'au titre** **Consequences**, ce titre non compris.

**Comment statuer : cinq gestes, tous dans ce fichier.** Lisez-les tous avant d'en faire un seul — le dernier efface les quatre autres —, et faites-les en **un seul acte, dans une seule merge request**.

1. **Écrire la valeur de chaque clé** dans le `traits:` du frontmatter — ou, si vous statuez `rejected`, **retirer le bloc `traits:` en entier**.
2. **Passer `status:`** de `proposed` à `accepted`, ou à `rejected`.
3. **Renseigner `date:` et `authors:`** — `date:` au format `AAAA-MM-JJ`, le jour où vous statuez ; `authors:`, les noms des personnes qui ont décidé, sans adresse courriel.
4. **Écrire deux ou trois lignes sous le titre Consequences**, à la place du commentaire qui s'y trouve : ce que votre décision facilite, et ce qu'elle coûte.
5. **En dernier seulement, supprimer ce bloc**, de sa première phrase jusqu'au titre Consequences non compris. À sa place : le motif de ce que vous avez décidé, partout où vous vous écartez de la proposition ; ou, si vous l'adoptez telle quelle, une ligne qui le dit.

**Le premier geste est celui qu'on oublie** : une décision écrite seulement en prose laisse un agent deviner. **Le titre Consequences n'est pas écrit en code, et c'est voulu** : la chaîne qui borne la coupe ne doit apparaître qu'une fois dans ce fichier, sinon qui la cherche coupe au premier faux positif.

**Ce qui reste**, et rien de tout cela ne s'efface : la proposition de la méthode et ses motifs, en tête de cette section ; le titre **Consequences** et ce que vous y écrivez au geste 4 ; et `## More Information`, qui décrit les clés et sert encore après.

**Cette proposition survit à la coupe** : la perdre appauvrirait cet ADR. Si vous décidez autrement, remplacez-la par votre décision et son motif.

**Voici à quoi ressemble ce frontmatter une fois rempli.** C'est la seule part de ce fichier qu'un agent lit sans l'interpréter :

```yaml
---
adr: SDR-0013
slug: frontend
title: Frontend
status: accepted
date: 2026-03-14
authors: []
supersedes: []
traits:
  frontend:
    framework: angular
    wcs_theme: sncf-holding
---
```

**`## Considered Options` ci-dessus est une proposition de l'amont, pas votre délibération.** La méthode a pesé ces options sans connaître votre contexte. La confrontation au vôtre reste à faire, et c'est elle qui distingue une décision d'un défaut accepté.

### Consequences

<!-- Ce que votre décision facilite, et ce qu'elle coûte. Deux ou trois lignes suffisent. Si vous statuez `rejected`, dites-le ici : l'agent n'appliquera aucune des règles ci-dessus, et le motif dit quel framework et quel design system tiennent lieu de ceux-ci. -->

### Confirmation

**Deux commandes, et ce sont des planchers, pas des garanties.** Elles ont été jouées le 2026-09-19 sur l'application d'essai, dans la forme ci-dessous. **Rien ne les lance** : ce squelette ne distribue aucune pipeline, et c'est la relecture de la merge request qui les réclame.

**1. Aucun élément natif que WCS couvre dans les gabarits.** Depuis le sous-dossier créé par `ng new`, celui qui porte `src/` et `package.json` :

```bash
grep -rnE '<(button|input|select|textarea)([ >]|$)' src --include='*.html' --include='*.ts' | grep -v 'type="hidden"'
```

Sortie attendue : **rien**. Sur un gabarit qui n'emploie que `<wcs-button>` et `<wcs-input>`, elle ne rend aucune ligne ; un `<button type="button">` ajouté rend une ligne, avec son fichier et son numéro. Les deux sorties ont été constatées.

**Elle balaie `src` en entier**, pas le seul premier écran : tout gabarit de l'application y passe, y compris ceux qu'un autre change a écrits.

**Ce qu'elle n'attrape pas**, et qu'il vaut mieux savoir que découvrir :

* `<table>`, là où WCS a `wcs-grid` ; `<a>` ; un composant d'une bibliothèque tierce ; un élément créé par du code plutôt qu'écrit dans un gabarit ;
* elle accuse à tort un `<input` dont le `type="hidden"` se trouve sur la **ligne suivante** : `grep` travaille ligne à ligne, et l'exclusion ne voit que sa propre ligne. Constaté. Sur une seule ligne, `type="hidden"` est bien exclu, y compris avec un attribut avant lui.

**Ce qu'elle accuse à tort, et que vous ne pourrez pas faire disparaître.** `wcs-native-select` est une enveloppe à `<slot>` : le `<select>` natif qu'elle habille **doit** vivre dans le light DOM, c'est son API. La commande le signalera donc à chaque passage, sur un gabarit parfaitement conforme. Constaté le 2026-09-20. **Ce n'est pas un défaut de votre code**, et il n'y a rien à corriger — la même limite ligne à ligne qui produit le faux positif ci-dessus empêche d'écrire une exclusion juste. Si vous employez `wcs-native-select`, attendez-vous à cette ligne et passez outre en le sachant.

**2. Aucun token inventé.** Depuis le même sous-dossier, `sncf-holding` étant à remplacer par la valeur de `frontend.wcs_theme` :

```bash
grep -rhoE 'var\(--wcs-[a-z0-9-]+' src | sed 's/var(//' | sort -u > utilises
grep -hoE '(^|[ ;{])--wcs-[a-z0-9-]+[[:space:]]*:' node_modules/wcs-core/design-tokens/dist/sncf-holding.css node_modules/wcs-core/dist/wcs/wcs.css | grep -oE -e '--wcs-[a-z0-9-]+' | sort -u > definis
comm -23 utilises definis
```

Sortie attendue : **rien**. Un `var(--wcs-x-y)` inventé rend `--wcs-x-y`.

**Constaté sur `sncf-holding` seulement**, le 2026-09-19, où la commande trouve 446 variables définies. Les fichiers des autres thèmes existent bien dans le paquet, mais la commande n'y a **pas** été rejouée : sur un autre thème, elle est une prescription, pas un constat.

**La seconde ligne lit deux fichiers, et ce n'est pas un détail** : `wcs.css` définit lui-même sept variables que le thème ne définit pas (`--wcs-font-sans-serif`, `--wcs-font-monospace`, `--wcs-tooltip-*`, `--wcs-phone-breakpoint-max-width`). Une version qui ne lisait que le thème les accusait à tort — constaté, puis corrigé avant d'écrire ceci.

**Ce qu'elle n'attrape pas :** une variable définie ailleurs — dans les styles internes d'un composant, ou posée par `setProperty` en code — ou dont le nom se construit à l'exécution ; un `--wcs-*` lu autrement que par `var(` ; l'usage d'une variable qui existe mais ne convient pas ; et **les valeurs en dur** — une couleur, une marge — qui n'appellent aucun token, alors qu'elles sont exactement ce que la règle 8 interdit. Elle compare des noms, jamais la portée d'un thème.

## More Information

| Clé | Ce qu'elle porte | Valeurs admises |
| --- | --- | --- |
| `frontend.framework` | le framework du front de ce dépôt | `angular` |
| `frontend.wcs_theme` | le thème WCS de l'entité dont ce dépôt porte les couleurs | `sncf-holding`, `sncf-reseau`, `sncf-voyageurs` |

**`frontend.framework` n'admet qu'une valeur, et ce n'est pas un oubli.** Ce fichier ne propose pas un choix entre plusieurs piles : il en retient une. Un dépôt qui en emploie une autre ne remplit pas cette clé — il statue `rejected`.

**`sncf-groupe` existe dans le paquet et n'est pas admis ici, et c'est un point ouvert.** `wcs-core@7.8.0` porte aussi un `sncf-groupe.css`, avec sa variante `-root-scoped` et son `.json`, comme les trois autres. Le guide de `wcs-angular` **ne le documente pas** : il ne liste que Holding, Réseau et Voyageurs. Cette clé s'en tient à ce que le guide documente ; si votre entité est celle-là, ne forcez pas la valeur — dites-le dans la merge request, et demandez à WCS.

**`rejected` ici veut dire que ce dépôt ne livre pas de front Angular** : un service sans interface, une bibliothèque, un front d'une autre pile. Le bloc `traits:` disparaît alors en entier, et le motif nomme le framework et le design system qui en tiennent lieu. **Ce statut fait taire toutes les règles ci-dessus** : un agent qui lit ce verdict n'en applique aucune.

**La valeur s'écrit dans ce fichier, et nulle part ailleurs.** Aucun autre fichier ne la recopie : celui qui en a besoin renvoie ici. C'est ce qui garantit qu'elle ne peut pas être contredite ailleurs.

**Une clé laissée vide n'est pas une réponse** — les deux sont exigées. Vous n'avez pas à le vérifier à l'œil. Depuis la racine de votre dépôt :

```bash
( cd docs/adr && npx @jackchuka/mdschema@0.15.1 check '*.md' )
```

**Si votre dépôt n'a ni Node ni `npm`, cette ligne ne vous sert à rien**, et le dire vaut mieux que le supposer. **Elle peut aussi échouer alors que Node est là.** Mesuré le 2026-09-20 sur macOS arm64, avec `npm` 10.9.8 puis 11.6.0 : `npx` rend `sh: mdschema: command not found`, parce que `npm` n'installe pas le lien du binaire — sur un répertoire neuf, avec `bin-links` à `true` et `ignore-scripts` à `false`. Le paquet est pourtant posé, sa dépendance de plateforme aussi, et son point d'entrée existe.

Dans les deux cas, `mdschema` est un binaire autonome : prenez-le dans les *releases* de [son dépôt](https://github.com/jackchuka/mdschema) et lancez `mdschema check '*.md'` depuis ce répertoire. **C'est le chemin sûr**, et non un repli de second choix. La ligne ci-dessus n'est qu'un raccourci, qui évite d'installer quoi que ce soit — quand il fonctionne.

Le schéma qu'elle applique est le `.mdschema.yml` de ce même répertoire, posé par la méthode. Elle nomme, fichier par fichier : une clé restée vide, une valeur hors de l'ensemble admis, un `status:` resté `proposed`, une `date:` absente, et le mode d'emploi qu'on aurait oublié de supprimer. **Elle reconnaît ce dernier à sa première phrase**, pas au tableau : le tableau a le droit de rester, et le garder ne déclenche rien. Elle ne juge pas votre décision — seulement qu'elle est prise.

**Qui peut faire appel. Quatre contraintes de ce fichier pèsent sur des gens qui ne l'ont pas adopté.** Adopter la méthode est un acte volontaire ; subir une application bâtie selon elle ne l'est pas. Ce qui suit ne juge aucune des quatre — il dit dans quelle modalité chacune régule, et par quelle voie on peut la contester. Une contrainte notifiée et contestable est du bon droit ; une contrainte qui s'applique sans que personne ne sache qu'une règle vient de lui être appliquée n'en est pas, quel que soit son motif.

```
// incongru-voix: lessig — appel à fonts.gstatic.com à chaque visite — régulée par architecture (les composants l'émettent) — recours: aucun pour le visiteur
// incongru-voix: lessig — thème sncf-holding par défaut — régulée par architecture (le défaut) — recours: aucun pour l'entité dont les couleurs sont portées
// incongru-voix: lessig — plancher npm 11.6.0, montée globale du poste — régulée par architecture (la création échoue) — recours: déclaré (l'exception se déclare)
// incongru-voix: lessig — frontend.framework n'admet qu'angular — régulée par norme aujourd'hui, architecture demain — recours: asymétrique (règle 12 exclue)
```

**1. La police Material Icons, appelée chez un tiers à chaque visite.**

```
CONTRAINTE : chaque poste qui ouvre l'application transmet son adresse IP
             à Google, à chaque visite — visiteur non consulté

  loi           pas rien, contrairement à l'habitude. Un tribunal allemand
                (LG München I, 3 O 17493/20, 20 janvier 2022) a jugé que
                charger une police Google depuis ses serveurs sans consentement
                viole le RGPD, et a accordé des dommages. Jurisprudence
                allemande, non française, non transposée telle quelle — mais
                le RGPD, lui, est le même des deux côtés
  norme         nulle : personne ne regarde d'où vient une police
  prix          du contournement, pour le visiteur : quitter le site
  architecture  totale, et c'est le point — 12 des 13 occurrences sont émises
                par les composants du paquet. Le lecteur de ce fichier ne
                choisit pas d'appeler ce tiers ; il choisit seulement de ne
                pas l'empêcher

  RECOURS       aucun pour le visiteur : ni notification, ni refus possible,
                ni trace. Pour celui qui monte l'application : entier, et
                c'est la première des deux issues déjà écrites plus haut
```

Ce fichier pose « deux issues, et il faut en prendre une ». La ligne `loi` ci-dessus les départage : héberger la police localement ne demande aucune base légale, garder l'appel externe en demande une. L'argument de l'intégrité impossible — `@font-face` n'admet pas d'attribut d'intégrité — n'était pas le seul.

**2. Le thème par défaut. Un défaut est la loi la plus puissante qui soit, parce que personne ne le lit et que presque personne ne le change.**

```
CONTRAINTE : l'application porte les couleurs d'une entité qui ne l'a pas
             autorisée — et le visiteur croit savoir à qui il parle

  loi           le droit des marques protège l'entité, pas le visiteur — et
                il suppose qu'elle apprenne l'existence de l'application
  norme         la relecture de merge request, quand quelqu'un connaît les
                trois valeurs et pense à la question
  prix          du contournement : nul. Une chaîne de caractères à changer
  architecture  le défaut s'applique en silence. Ce fichier le dit lui-même :
                « sans que rien ne le dise »

  RECOURS       aucun automatique. L'entité lésée n'est pas prévenue ; le
                visiteur n'a aucun moyen de savoir qu'il lit les couleurs
                d'un tiers. Le seul garde-fou est la vigilance de celui qui
                statue — et ce fichier a raison de l'exiger explicitement
```

Traitez donc un changement de cette valeur comme un amendement, pas comme un réglage : c'est ce que la colonne `Motif` du tableau de `## Decision Outcome` demande déjà, et c'est la seule des deux clés qui appelle une vérification avant d'être gardée.

**3. Le plancher `npm`. Contrainte bien faite — elle est ici à titre de comparaison.**

```
CONTRAINTE : monter npm sur le poste entier, donc sur tous les autres
             projets qui y vivent — au-delà du périmètre de ce dépôt

  loi           rien
  norme         la politique de poste de l'organisation, qui parfois l'interdit
  prix          une montée globale ; ce fichier précise « un plancher, pas une
                épingle », ce qui limite la casse aux versions inférieures
  architecture  la création échoue, avec un message qui ne nomme ni Angular,
                ni npm, ni ce qu'il faut faire

  RECOURS       DÉCLARÉ. Le fichier écrit : « Si votre dépôt applique une règle
                qui interdit de monter le gestionnaire de paquets, cette montée
                est l'exception à déclarer, et elle se joue une fois. »
```

C'est le modèle. La contrainte est nommée, mesurée par bissection, sa portée avouée (« mesuré sur l'arbre que pose `ng new` pour Angular 22 »), et la voie de dérogation écrite dans le même paragraphe. Une règle qui prévoit sa propre exception est une règle, pas un verrou.

**4. `frontend.framework` : le recours y est asymétrique, et l'asymétrie n'est pas dite.**

```
CONTRAINTE : tout front de ce dépôt est Angular — y compris pour les
             contributeurs et les agents qui arriveront après la décision
             et n'auront rien adopté

  loi           rien
  norme         la prescription du groupe (page du D2D, lue le 2026-09-20),
                et c'est aujourd'hui la seule modalité qui tienne
  prix          du refus : statuer `rejected`, c'est-à-dire faire taire les
                seize règles d'un coup. Il n'existe pas de refus partiel
  architecture  nulle aujourd'hui : le `.mdschema.yml` de ce dépôt ne connaît
                pas la clé `frontend` — vérifié. L'énumération à une valeur
                vit dans la prose de ce fichier, pas dans le schéma qui
                l'applique. Elle deviendra architecture le jour où le schéma
                l'apprend

  RECOURS       la règle 12 ouvre la dérogation par ADR local pour les seize
                règles — mais pas pour cette clé, qui n'admet que le rejet
                global. Deux régimes d'appel coexistent dans ce fichier sans
                qu'aucune phrase ne les oppose
```

Écrivez cette asymétrie. Une phrase suffit, sous la règle 12 : *cette dérogation vaut pour les seize règles ; `frontend.framework`, lui, ne se déroge pas — il se rejette.* Un lecteur qui applique la règle 12 à la clé se croira couvert et ne le sera pas.

**Le geste que ce fichier fait déjà, et qu'il faut nommer : la règle 4 est un acte de dérégulation.** Le `.mcp.json` qu'engendre le CLI déclare un serveur qui, selon ce fichier, « ordonne à l'agent de préférer ses outils au shell, ce qui concurrence vos propres consignes ». Un tiers avait inscrit une règle dans votre dépôt sans vous le dire ; la règle 4 la retire. C'est exactement le bon réflexe, et il mérite d'être posé comme principe plutôt que comme cas d'espèce : **une contrainte qu'un outil dépose dans votre dépôt sans notification se retire, et le retrait se motive.** Le même raisonnement vaut pour l'appel réseau à `skills.sh`, que ce fichier signale et dont il donne la sortie — copier le répertoire à la main. Deux fois le bon geste.

**Ce que cette analyse ne fait pas.** Elle conclut que la contrainte la plus dure — Angular, valeur unique — est légitime, parce qu'adopter la méthode est volontaire. C'est une conclusion confortable pour qui publie la méthode, et la finesse du cadre n'est pas une preuve de sa justesse : elle ne tient que tant que l'adoption reste réellement révocable, et elle ne dit rien du contributeur qui hérite du dépôt sans avoir rien adopté. Si la méthode devient un prérequis d'organisation plutôt qu'un choix de dépôt, cette ligne est à refaire, et la réponse changera.

**Et la question qui suit toujours** : ces quatre règles, les aurait-on votées si elles avaient été présentées comme des règles ? Trois oui, probablement. La première — faire appeler un tiers par chaque visiteur, sans qu'il le sache — n'aurait pas passé le vote. C'est pourquoi elle est arrivée par le code.
