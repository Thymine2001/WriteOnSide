<p align="center">
  <img src="../assets/writeonside_logo_light.svg" alt="WriteOnSide-Logo" width="96" />
</p>

<h1 align="center">WriteOnSide</h1>

<p align="center">
  <strong>随边记 · Eine leichte Windows-Seitenleisten-App für Markdown-Notizen.</strong><br />
  Klartextdateien auf der Festplatte. Obsidian-kompatibel. Immer am Bildschirmrand bereit.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows" alt="Windows 10 und 11" />
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/version-0.0.50-2ea44f" alt="Version 0.0.50" />
</p>

<p align="center">
  <strong>Sprachen:</strong>
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

WriteOnSide (随边记) speichert Markdown-Notizen in einem von Ihnen gewählten Ordner. Es gibt keine private Datenbank und keinen erforderlichen Cloud-Dienst, sodass derselbe Vault in WriteOnSide, Obsidian, VS Code oder einem anderen Editor geöffnet werden kann.

> [!NOTE]
> WriteOnSide `0.0.50` ist ein Vorabrelease-Projekt in aktiver Entwicklung. Sichern Sie wichtige Notizen und lesen Sie die Versionshinweise vor einem Upgrade.

<p align="center">
  <img src="../assets/screenshots/writeonside-screenshot.png" alt="WriteOnSide-Seitenleiste unter Windows" width="720" />
</p>

## Installation

### Windows-Build herunterladen

Laden Sie die neueste `WriteOnSide.exe` von
[GitHub Releases](https://github.com/Thymine2001/WriteOnSide/releases) herunter.

WriteOnSide wird derzeit als portable Windows-Anwendung in einer einzelnen Datei verteilt:

1. `WriteOnSide.exe` herunterladen.
2. In einen Ordner legen, in dem Sie die Anwendung aufbewahren möchten.
3. Starten und einen Notizenordner oder einen bestehenden Obsidian-Vault wählen.
4. `Ctrl+Shift+Enter` zum Ein- oder Ausblenden des Panels verwenden.

Windows SmartScreen kann bei unsignierten Entwicklungsbuilds eine Warnung anzeigen. Prüfen Sie vor dem Start, ob die Datei aus diesem Repository stammt.

## Highlights

### Seitenleiste

- Rahmenloses, bildschirmhohes Panel, das immer im Vordergrund bleibt
- Konfigurierbares Layout links oder rechts am Bildschirmrand
- Globale Ein-/Ausblend-Tastenkombination, Standard `Ctrl+Shift+Enter`
- Einstellbare Panelbreite, Dateibereich-Breite und Deckkraft
- Sanftes Öffnen, Schließen, Layoutwechsel und Größenänderung
- Systemtray-Steuerung und optionaler Windows-Autostart
- Einzelinstanz-Verhalten und Positionierung im Multi-Monitor-Arbeitsbereich

### Markdown-Bearbeitung

- Bearbeitbarer Markdown-Quelltext mit Live-Syntaxhervorhebung
- Schreibgeschützter Render-Modus mit Links und Bildern
- Formatierungsleiste für Überschriften, Hervorhebung, Zitate, Listen, Aufgaben, Tabellen, Code, Links, Bilder, Markierungen und Textfarben
- YAML-Front-Matter mit Titeln, Tags, Daten, Aliasen und weiteren Metadaten
- Suchen und Ersetzen, Zeilennummern, Gliederung und fixierte Überschriften
- Eingezäunte Codeblöcke mit Sprachlabel und Kopieren per Klick
- Konfigurierbare Schriftarten, Textgrößen, Themes und Befehlskürzel

### Oberflächensprachen

Die App enthält **English**, **中文**, **Português**, **Deutsch**, **Français**, **Nederlands**, **한국어**, **Italiano**, **हिन्दी** und **Українська**. Ändern unter **Einstellungen → Allgemein → Sprache**.

### Obsidian-Kompatibilität

| Funktion | Unterstützung |
|---|---|
| Wiki-Links: `[[Note]]`, `[[Note\|alias]]`, `[[Note#Heading]]` | Ja |
| Blockreferenzen: `[[Note#^block-id]]` | Ja |
| Notiz- und Bildeinbettungen: `![[file]]` | Ja |
| Callouts: `> [!note]` | Lesemodus |
| Fußnoten, `%%Kommentare%%` und Inline-`#tags` | Ja |
| Aufgabenlisten: `- [ ]` und `- [x]` | Ja |
| Notiz umbenennen und eingehende Wikilinks aktualisieren | Ja |

`[[` öffnet die Notiz-Vervollständigung. `Strg+Klick` folgt einem Wikilink im Bearbeitungsmodus. Das Backlinks-Werkzeug listet Notizen, die auf die aktuelle Notiz verweisen.

### Dateien und Anhänge

- Lazy-geladener Datei-Explorer mit rekursiver Notizsuche
- YAML-Tag-Filterung mit Mehrfachauswahl
- Dateien erstellen, umbenennen, löschen, ziehen und in der Vorschau anzeigen
- Markdown und gängige Text- oder Quellcodeformate bearbeiten
- Bilder in Notizen einfügen oder hineinziehen
- Konfigurierbarer Anhangsordner mit portablen relativen Links
- Atomare Speicherung und zeitgestempelte Backups außerhalb des Vaults
- Bildbetrachter mit Zoom und Schwenken

## Systemanforderungen

**Für Endanwender:**

- Windows 10 oder Windows 11
- Standard-Desktop-Sitzung; Windows on ARM wurde noch nicht formal getestet

**Für Entwicklung aus dem Quellcode:**

- Python 3.12
- Die in [`requirements.txt`](../requirements.txt) aufgeführten Pakete

## Aus dem Quellcode starten

```powershell
git clone https://github.com/Thymine2001/WriteOnSide.git
cd WriteOnSide

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\writeonside.py
```

Beim ersten Start einen Notizenordner oder einen bestehenden Obsidian-Vault wählen.

## Grundlegende Nutzung

- Mit dem Hamburger-Button den Datei-Explorer öffnen oder schließen.
- Zwischen Bearbeitungs- und Lesemodus in der Symbolleiste wechseln.
- Notizen über die Symbolleiste oder den Explorer erstellen.
- Ein Bild direkt in eine Markdown-Notiz einfügen, um es in den konfigurierten Anhangsordner zu kopieren.
- YAML-Tags im unteren Explorer-Bereich auswählen, um Notizen zu filtern.
- Einstellungen öffnen, um Notizenordner, Layout, Breiten, Deckkraft, Theme, Schriftart, globale Umschalttaste und Symbolleistenkürzel zu konfigurieren.
- Das Schließen des Panels blendet die Anwendung aus; globale Tastenkombination oder Tray-Menü zum erneuten Anzeigen verwenden.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

Der aktuelle Quellcode enthält Unit-Tests für Konfiguration, Markdown-Rendering, Tastenkürzel, Speicher, Notizindexierung, Obsidian-Syntax, Wikilink-Umbenennung und Internationalisierung.

## Windows-EXE erstellen

Das Release-Skript benötigt PyInstaller und PyMuPDF zusätzlich zu den Laufzeitabhängigkeiten:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller pymupdf
.\build_release.ps1
```

Das Skript:

1. Erhöht die Patch-Version in `VERSION`.
2. Exportiert PNG- und ICO-Dateien aus den SVG-Logoquellen.
3. Erstellt eine Windows-EXE in einer Datei mit PyInstaller.
4. Schreibt sie nach `dist-native-tree-vX.Y.Z\WriteOnSide.exe`.
5. Behält die drei neuesten Release-Verzeichnisse.

Siehe [`BUILDING.md`](../BUILDING.md) für weitere Befehle und Fehlerbehebung.

## Datenspeicherorte

| Daten | Ort |
|---|---|
| Notizen und Anhänge | Vom Benutzer gewählter Ordner oder Obsidian-Vault |
| Einstellungen | `%LOCALAPPDATA%\WriteOnSide\config.json` |
| Verwaltete Backups | `%LOCALAPPDATA%\WriteOnSide\Backups\` |

WriteOnSide benötigt kein Konto und keinen integrierten Cloud-Dienst. Notizen verlassen den Computer nur, wenn der Benutzer den Vault in einen separat konfigurierten Synchronisierungsdienst legt.

## Projektstruktur

```text
writeonside.py          Anwendungseinstieg
writeonside_app/        Anwendungsquellcode
assets/                 SVG-, PNG- und ICO-Ressourcen
scripts/                Build-Hilfsskripte
tests/                  Unit-Tests
licenses/               Lizenztexte Dritter
WriteOnSide.spec        PyInstaller-Konfiguration
build_release.ps1       Versioniertes Windows-Release-Skript
BUILDING.md             Ausführliche Build-Anleitung
THIRD_PARTY_NOTICES.md  Abhängigkeitsnachweise und Lizenzindex
LICENSE                 MIT-Lizenz für WriteOnSide-Quellcode
```

## Lizenzierung

Der Originalquellcode von WriteOnSide steht unter der
[MIT-Lizenz](../LICENSE).

Komponenten Dritter unterliegen weiterhin ihren jeweiligen Lizenzen in
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

<p align="center">
  <sub>Python | Tkinter | Markdown | Obsidian-kompatible Klartextdateien</sub>
</p>
