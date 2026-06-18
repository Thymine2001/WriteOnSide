<p align="center">
  <img src="../assets/writeonside_logo_light.svg" alt="WriteOnSide-logo" width="96" />
</p>

<h1 align="center">WriteOnSide</h1>

<p align="center">
  <strong>随边记 · Een lichte Windows-zijpaneel-app voor Markdown-notities.</strong><br />
  Platte bestanden op schijf. Obsidian-vriendelijk. Altijd aan de schermrand.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows" alt="Windows 10 en 11" />
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/version-0.1.1-2ea44f" alt="Versie 0.1.1" />
</p>

<p align="center">
  <strong>Talen:</strong>
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

WriteOnSide (随边记) bewaart Markdown-notities in een map naar keuze. Er is geen privédatabase en geen verplichte clouddienst, dus dezelfde Vault kan worden geopend in WriteOnSide, Obsidian, VS Code of een andere editor.

> [!NOTE]
> WriteOnSide `0.1.1` is een pre-releaseproject in actieve ontwikkeling. Maak back-ups van belangrijke notities en lees de release-opmerkingen vóór een upgrade.

<p align="center">
  <img src="../assets/screenshots/writeonside-screenshot.png" alt="WriteOnSide-zijpaneel op Windows" width="720" />
</p>

## Installatie

### Een Windows-build downloaden

Download de nieuwste `WriteOnSide.exe` van
[GitHub Releases](https://github.com/Thymine2001/WriteOnSide/releases).

WriteOnSide wordt momenteel gedistribueerd als draagbare Windows-app in één bestand:

1. Download `WriteOnSide.exe`.
2. Plaats het in een map waar u de app wilt bewaren.
3. Start en kies een notitiemap of een bestaande Obsidian Vault.
4. Gebruik `Ctrl+Shift+Enter` om het paneel te tonen of te verbergen.

Windows SmartScreen kan een waarschuwing tonen voor niet-ondertekende ontwikkelbuilds. Controleer of het bestand van deze repository komt voordat u het uitvoert.

## Hoogtepunten

### Zijpaneel

- Randloos paneel over de volledige hoogte, altijd bovenaan
- Configureerbare indeling links of rechts aan de schermrand
- Globale sneltoets om te tonen/verbergen, standaard `Ctrl+Shift+Enter`
- Instelbare paneelbreedte, bestandsverkenner-breedte en dekking
- Vloeiend openen, sluiten, lay-out wijzigen en schalen
- Systeemvakbediening en optioneel opstarten met Windows
- Enkele-instantiegedrag en positionering op multi-monitorwerkgebieden

### Markdown-bewerking

- Bewerkbare Markdown-bron met live syntaxismarkering
- Alleen-lezen weergavemodus met links en afbeeldingen
- Opmaakwerkbalk voor koppen, nadruk, citaten, lijsten, taken, tabellen, code, links, afbeeldingen, markering en tekstkleuren
- YAML-front matter met titels, tags, datums, aliassen en andere metadata
- Zoeken en vervangen, regelnummers, overzicht en vastgezette koppen
- Omheinde codeblokken met taallabel en kopiëren met één klik
- Configureerbare lettertypen, tekstgroottes, thema's en opdrachtsneltoetsen

### Interfacetalen

De app bevat **English**, **中文**, **Português**, **Deutsch**, **Français**, **Nederlands**, **한국어**, **Italiano**, **हिन्दी** en **Українська**. Wijzig in **Instellingen → Algemeen → Taal**.

### Obsidian-compatibiliteit

| Functie | Ondersteuning |
|---|---|
| Wiki-links: `[[Note]]`, `[[Note\|alias]]`, `[[Note#Heading]]` | Ja |
| Blokverwijzingen: `[[Note#^block-id]]` | Ja |
| Notitie- en afbeeldingsembeds: `![[file]]` | Ja |
| Callouts: `> [!note]` | Leesmodus |
| Voetnoten, `%%opmerkingen%%` en inline `#tags` | Ja |
| Takenlijsten: `- [ ]` en `- [x]` | Ja |
| Notitie hernoemen en inkomende wikilinks bijwerken | Ja |

Typ `[[` voor notitie-aanvulling. `Ctrl+klik` volgt een wikilink in bewerkingsmodus. De Backlinks-tool toont notities die naar de huidige notitie linken.

### Bestanden en bijlagen

- Lazy-geladen bestandsverkenner met recursief zoeken
- YAML-tagfiltering met meervoudige selectie
- Bestanden maken, hernoemen, verwijderen, slepen en bekijken
- Markdown en gangbare tekst- of broncodeformaten bewerken
- Afbeeldingen plakken of slepen naar notities
- Configureerbare bijlagenmap met draagbare relatieve links
- Atomaire opslag en back-ups met tijdstempel buiten de Vault
- Afbeeldingsviewer met zoomen en pannen

## Systeemvereisten

**Voor eindgebruikers:**

- Windows 10 of Windows 11
- Standaard desktopsessie; Windows on ARM is nog niet formeel getest

**Voor ontwikkeling vanuit broncode:**

- Python 3.12
- De pakketten in [`requirements.txt`](../requirements.txt)

## Uit broncode uitvoeren

```powershell
git clone https://github.com/Thymine2001/WriteOnSide.git
cd WriteOnSide

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\writeonside.py
```

Kies bij de eerste start een notitiemap of een bestaande Obsidian Vault.

## Basisgebruik

- Gebruik de hamburgerknop om de bestandsverkenner te openen of te sluiten.
- Schakel tussen Bewerken en Lezen via de werkbalk.
- Maak notities via de werkbalk of bestandsverkenner.
- Plak een afbeelding direct in een Markdown-notitie om deze naar de geconfigureerde bijlagenmap te kopiëren.
- Selecteer YAML-tags in het onderste gedeelte van de verkenner om notities te filteren.
- Open Instellingen om notitiemap, lay-out, breedtes, dekking, thema, lettertype, globale sneltoets en werkbalksneltoetsen te configureren.
- Het sluiten van het paneel verbergt de app; gebruik de globale sneltoets of het systeemvakmenu om deze weer te tonen.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

De huidige broncode bevat unit-tests voor configuratie, Markdown-rendering, sneltoetsen, opslag, notitie-indexering, Obsidian-syntaxis, wikilink-hernoemen en internationalisatie.

## Een Windows-EXE bouwen

Het release-script vereist PyInstaller en PyMuPDF naast de runtime-afhankelijkheden:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller pymupdf
.\build_release.ps1
```

Het script:

1. Verhoogt het patchversienummer in `VERSION`.
2. Exporteert PNG- en ICO-bestanden vanuit de SVG-logobronnen.
3. Bouwt een Windows-executable in één bestand met PyInstaller.
4. Schrijft naar `dist-native-tree-vX.Y.Z\WriteOnSide.exe`.
5. Behoudt de drie nieuwste release-mappen.

Zie [`BUILDING.md`](../BUILDING.md) voor extra commando's en probleemoplossing.

## Gegevenslocaties

| Gegevens | Locatie |
|---|---|
| Notities en bijlagen | Door gebruiker gekozen map of Obsidian Vault |
| Instellingen | `%LOCALAPPDATA%\WriteOnSide\config.json` |
| Beheerde back-ups | `%LOCALAPPDATA%\WriteOnSide\Backups\` |

WriteOnSide vereist geen account of ingebouwde clouddienst. Notities verlaten de computer alleen wanneer de gebruiker de Vault in een apart geconfigureerde synchronisatiedienst plaatst.

## Projectstructuur

```text
writeonside.py          Toegangspunt van de applicatie
writeonside_app/        Applicatiebroncode
assets/                 SVG-, PNG- en ICO-resources
scripts/                Hulp-scripts voor builds
tests/                  Unittests
licenses/               Licentieteksten van derden
WriteOnSide.spec        PyInstaller-configuratie
build_release.ps1       Versiegebonden Windows-release-script
BUILDING.md             Gedetailleerde build-instructies
THIRD_PARTY_NOTICES.md  Attributie van afhankelijkheden en licentie-index
LICENSE                 MIT-licentie voor WriteOnSide-broncode
```

## Licentie

De originele broncode van WriteOnSide valt onder de
[MIT-licentie](../LICENSE).

Componenten van derden blijven onder hun respectieve licenties zoals vermeld in
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

<p align="center">
  <sub>Python | Tkinter | Markdown | Obsidian-compatibele platte bestanden</sub>
</p>
