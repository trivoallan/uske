## ADDED Requirements

### Requirement: Une version nommée produit une image dans le registre interne

Le dépôt SHALL produire, pour chaque version nommée par un tag, une image portant ce nom dans le
registre interne. Une surcouche de déploiement n'épingle que ce qui a une version : ni `main`, ni un
SHA, ne sont des points d'épinglage.

#### Scenario: Un tag de version est poussé

- **GIVEN** le dépôt sur sa forge, avec sa chaîne d'intégration
- **WHEN** un tag `v<x.y.z>` est poussé
- **THEN** une image `<registre-interne>/<projet>/uske:v<x.y.z>` existe et se tire depuis le cluster
- **AND** son empreinte est celle qu'une surcouche épingle

#### Scenario: Un commit sans tag

- **GIVEN** un commit fusionné sur `main`, sans tag
- **WHEN** la chaîne d'intégration s'exécute
- **THEN** aucune image n'est publiée dans le registre interne

### Requirement: La construction ne dépend d'aucun registre public

La construction de l'image SHALL pouvoir s'exécuter depuis un réseau qui n'atteint que les
services internes : les images de base et l'index des paquets se désignent par des paramètres, dont
les valeurs par défaut restent publiques pour qui construit hors de ce réseau.

#### Scenario: Construire depuis le réseau de l'employeur

- **GIVEN** un exécuteur qui n'atteint ni `ghcr.io`, ni `docker.io`, ni `pypi.org`
- **WHEN** la chaîne d'intégration construit l'image en désignant le registre et le miroir internes
- **THEN** la construction aboutit

#### Scenario: Construire sans rien désigner

- **GIVEN** un poste qui atteint les registres publics
- **WHEN** l'image se construit sans désigner aucun registre
- **THEN** la construction aboutit avec les sources publiques

### Requirement: La base de manifestes se consomme depuis un autre dépôt

La base de manifestes SHALL se paramétrer depuis une surcouche extérieure par trois chemins
seulement : l'épinglage des images, les paramètres du workflow, et un correctif de spécification de
pod. Une surcouche n'a pas à connaître l'ordre ni le nombre des gabarits de la base : aucun chemin à
index n'est requis pour l'employer.

#### Scenario: Une surcouche extérieure rend les manifestes

- **GIVEN** une surcouche dans un autre dépôt, qui référence la base par une version
- **AND** qui n'emploie que l'épinglage des images, les paramètres du workflow et un correctif de
  spécification de pod
- **WHEN** les manifestes sont rendus, puis passés au linter de l'ordonnanceur
- **THEN** le rendu aboutit et le linter ne signale rien

#### Scenario: La base change sans prévenir la surcouche

- **GIVEN** une modification de la base qui ajoute, retire ou déplace un gabarit
- **WHEN** la surcouche d'exemple du dépôt est rendue et passée au linter
- **THEN** l'échec est signalé par la chaîne d'intégration avant qu'une version ne soit nommée

### Requirement: La chaîne d'intégration vérifie la surcouche d'exemple

Le dépôt SHALL porter une surcouche d'exemple, aux valeurs factices, rendue et vérifiée à chaque
demande de fusion. C'est le seul contrôle permanent du contrat de la base avec l'extérieur, et le
modèle qu'une surcouche réelle copie.

#### Scenario: Une demande de fusion touche les manifestes

- **GIVEN** une demande de fusion qui modifie la base
- **WHEN** la chaîne d'intégration s'exécute
- **THEN** la surcouche d'exemple et celle du banc local sont toutes deux rendues et vérifiées

### Requirement: Les ressources déployées portent le nom de l'outil

Les ressources que la base déclare — planification, gabarit de workflow, identité d'exécution,
droits, volume du journal, secrets — SHALL porter le nom de l'outil qui les remplit. Ces noms sont
le contrat qu'une surcouche épingle et sous lesquels les secrets d'un environnement sont créés.

#### Scenario: Chercher le nom d'un rôle qui n'existe plus

- **GIVEN** les manifestes du dépôt
- **WHEN** on y cherche le nom de l'ancien rôle générique
- **THEN** il n'apparaît nulle part, hors des changes archivés

#### Scenario: Nommer les secrets d'un environnement

- **GIVEN** une surcouche pour un environnement réel
- **WHEN** ses secrets sont créés d'après les noms que la base attend
- **THEN** ces noms dérivent du nom de l'outil, et le screening les trouve

### Requirement: Aucun nom propre à un environnement dans un fichier suivi

Le dépôt SHALL rester exempt des noms propres à l'organisation qui l'héberge — hôte du registre,
projet, chemins internes : ils se désignent par des variables de la chaîne d'intégration. Le dépôt
est miroité en clair, et la surcouche d'un environnement réel vit dans le dépôt de déploiement de
cette organisation.

#### Scenario: Relire le dépôt avant de l'ouvrir

- **GIVEN** l'ensemble des fichiers suivis
- **WHEN** on y cherche l'hôte du registre interne ou le nom d'un projet interne
- **THEN** aucun ne s'y trouve, ni dans l'arbre, ni dans un fichier de chaîne d'intégration
