<p align="center">
  <img src="../assets/writeonside_logo_light.svg" alt="Logo WriteOnSide" width="96" />
</p>

<h1 align="center">WriteOnSide</h1>

<p align="center">
  <strong>随边记 · Une application légère de notes Markdown en panneau latéral pour Windows.</strong><br />
  Fichiers en clair sur le disque. Compatible Obsidian. Toujours au bord de l'écran.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows" alt="Windows 10 et 11" />
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/version-0.1.2-2ea44f" alt="Version 0.1.2" />
</p>

<p align="center">
  <strong>Langues :</strong>
  <a href="../README.md">English</a> |
  <a href="README.zh-CN.md">中文</a> |
  <a href="README.pt.md">Português</a> |
  <a href="README.de.md">Deutsch</a> |
  <a href="README.fr.md">Français</a> |
  <a href="README.nl.md">Nederlands</a> |
  <a href="README.ko.md">한국어</a> |
  <a href="README.it.md">Italiano</a> |
  <a href="README.hi.md">हिन्दी</a> |
  <a href="README.uk.md">Українська</a>
</p>

WriteOnSide (随边记) conserve vos notes Markdown dans un dossier de votre choix. Il n'y a pas de base de données privée ni de service cloud obligatoire : le même Vault peut être ouvert dans WriteOnSide, Obsidian, VS Code ou un autre éditeur.

> [!NOTE]
> WriteOnSide `0.1.2` est un projet en développement actif, encore en préversion. Sauvegardez vos notes importantes et consultez les notes de version avant une mise à jour.

<p align="center">
  <img src="../assets/screenshots/writeonside-screenshot.png" alt="Panneau latéral WriteOnSide sur Windows" width="720" />
</p>

## Installation

### Télécharger une build Windows

Téléchargez la dernière `WriteOnSide.exe` sur
[GitHub Releases](https://github.com/Thymine2001/WriteOnSide/releases).

WriteOnSide est actuellement distribué comme application Windows portable en un seul fichier :

1. Téléchargez `WriteOnSide.exe`.
2. Placez-la dans le dossier où vous souhaitez conserver l'application.
3. Lancez-la et sélectionnez un dossier de notes ou un Vault Obsidian existant.
4. Utilisez `Ctrl+Shift+Enter` pour afficher ou masquer le panneau.

Windows SmartScreen peut afficher un avertissement pour les builds de développement non signées. Vérifiez que le fichier provient de ce dépôt avant de l'exécuter.

## Points forts

### Panneau latéral

- Panneau sans bordure, pleine hauteur, toujours au premier plan
- Disposition configurable à gauche ou à droite de l'écran
- Raccourci global d'affichage/masquage, par défaut `Ctrl+Shift+Enter`
- Largeur du panneau, largeur de l'explorateur et opacité réglables
- Ouverture, fermeture, changement de disposition et redimensionnement fluides
- Contrôles dans la zone de notification et démarrage Windows optionnel
- Instance unique et positionnement sur les zones de travail multi-écrans

### Édition Markdown

- Source Markdown modifiable avec coloration syntaxique en direct
- Mode rendu en lecture seule avec liens et images
- Barre d'outils pour titres, emphase, citations, listes, tâches, tableaux, code, liens, images, surlignage et couleurs de texte
- Front matter YAML avec titres, tags, dates, alias et autres métadonnées
- Rechercher et remplacer, numéros de ligne, plan et titres épinglés
- Blocs de code avec étiquette de langue et copie en un clic
- Polices, tailles, thèmes et raccourcis de commandes configurables

### Langues de l'interface

L'application inclut **English**, **中文**, **Português**, **Deutsch**, **Français**, **Nederlands**, **한국어**, **Italiano**, **हिन्दी** et **Українська**. Modifiez dans **Paramètres → Général → Langue**.

### Compatibilité Obsidian

| Fonctionnalité | Prise en charge |
|---|---|
| Liens wiki : `[[Note]]`, `[[Note\|alias]]`, `[[Note#Heading]]` | Oui |
| Références de bloc : `[[Note#^block-id]]` | Oui |
| Intégrations de notes et d'images : `![[file]]` | Oui |
| Callouts : `> [!note]` | Mode lecture |
| Notes de bas de page, `%%commentaires%%` et `#tags` inline | Oui |
| Listes de tâches : `- [ ]` et `- [x]` | Oui |
| Renommer une note et mettre à jour les wikilinks entrants | Oui |

Taper `[[` ouvre la complétion de notes. `Ctrl+clic` suit un wikilink en mode édition. L'outil Backlinks liste les notes qui pointent vers la note actuelle.

### Fichiers et pièces jointes

- Explorateur de fichiers à chargement différé avec recherche récursive
- Filtrage par tags YAML avec sélection multiple
- Créer, renommer, supprimer, glisser et prévisualiser des fichiers
- Modifier Markdown et formats texte ou code courants
- Coller ou glisser des images dans les notes
- Dossier de pièces jointes configurable avec liens relatifs portables
- Sauvegardes atomiques et copies horodatées hors du Vault
- Visionneuse d'images avec zoom et déplacement

## Configuration requise

**Pour les utilisateurs finaux :**

- Windows 10 ou Windows 11
- Session de bureau standard ; Windows on ARM n'a pas encore été testé formellement

**Pour le développement à partir des sources :**

- Python 3.12
- Les paquets listés dans [`requirements.txt`](../requirements.txt)

## Exécuter depuis les sources

```powershell
git clone https://github.com/Thymine2001/WriteOnSide.git
cd WriteOnSide

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\writeonside.py
```

Au premier lancement, sélectionnez un dossier de notes ou un Vault Obsidian existant.

## Utilisation de base

- Utilisez le bouton hamburger pour ouvrir ou fermer l'explorateur de fichiers.
- Basculez entre les modes Édition et Lecture depuis la barre d'outils.
- Créez des notes depuis la barre d'outils ou l'explorateur.
- Collez une image directement dans une note Markdown pour la copier dans le dossier de pièces jointes configuré.
- Sélectionnez des tags YAML dans la section inférieure de l'explorateur pour filtrer les notes.
- Ouvrez Paramètres pour configurer le dossier de notes, la disposition, les largeurs, l'opacité, le thème, la police, le raccourci global et les raccourcis de la barre d'outils.
- Fermer le panneau masque l'application ; utilisez le raccourci global ou le menu de la zone de notification pour l'afficher à nouveau.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

L'arborescence source actuelle contient des tests unitaires couvrant la configuration, le rendu Markdown, les raccourcis, le stockage, l'indexation des notes, la syntaxe Obsidian, le renommage des wikilinks et l'internationalisation.

## Créer un EXE Windows

Le script de publication nécessite PyInstaller et PyMuPDF en plus des dépendances d'exécution :

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller pymupdf
.\build_release.ps1
```

Le script :

1. Incrémente la version de correctif dans `VERSION`.
2. Exporte les fichiers PNG et ICO à partir des logos SVG.
3. Construit un exécutable Windows monofichier avec PyInstaller.
4. L'écrit dans `dist-native-tree-vX.Y.Z\WriteOnSide.exe`.
5. Conserve les trois répertoires de publication les plus récents.

Voir [`BUILDING.md`](../BUILDING.md) pour d'autres commandes et le dépannage.

## Emplacements des données

| Données | Emplacement |
|---|---|
| Notes et pièces jointes | Dossier choisi par l'utilisateur ou Vault Obsidian |
| Paramètres | `%LOCALAPPDATA%\WriteOnSide\config.json` |
| Sauvegardes gérées | `%LOCALAPPDATA%\WriteOnSide\Backups\` |

WriteOnSide ne nécessite pas de compte ni de service cloud intégré. Les notes ne quittent l'ordinateur que si l'utilisateur place le Vault dans un service de synchronisation configuré séparément.

## Structure du projet

```text
writeonside.py          Point d'entrée de l'application
writeonside_app/        Code source de l'application
assets/                 Ressources SVG, PNG et ICO
scripts/                Scripts d'aide au build
tests/                  Tests unitaires
licenses/               Textes de licence tiers
WriteOnSide.spec        Configuration PyInstaller
build_release.ps1       Script de publication Windows versionné
BUILDING.md             Instructions de build détaillées
THIRD_PARTY_NOTICES.md  Attribution des dépendances et index des licences
LICENSE                 Licence MIT du code source WriteOnSide
```

## Licence

Le code source original de WriteOnSide est sous
[licence MIT](../LICENSE).

Les composants tiers restent soumis à leurs licences respectives listées dans
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

<p align="center">
  <sub>Python | Tkinter | Markdown | Fichiers en clair compatibles Obsidian</sub>
</p>
