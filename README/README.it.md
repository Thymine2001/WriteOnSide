<p align="center">
  <img src="../assets/writeonside_logo_light.svg" alt="Logo WriteOnSide" width="96" />
</p>

<h1 align="center">WriteOnSide</h1>

<p align="center">
  <strong>随边记 · App leggera di note Markdown in pannello laterale per Windows.</strong><br />
  File in chiaro su disco. Compatibile con Obsidian. Sempre al bordo dello schermo.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows" alt="Windows 10 e 11" />
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/version-0.1.0-2ea44f" alt="Versione 0.1.0" />
</p>

<p align="center">
  <strong>Lingue:</strong>
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

WriteOnSide (随边记) conserva le note Markdown in una cartella a tua scelta. Non c'è un database privato né un servizio cloud obbligatorio, quindi lo stesso Vault può essere aperto in WriteOnSide, Obsidian, VS Code o un altro editor.

> [!NOTE]
> WriteOnSide `0.1.0` è un progetto pre-release in sviluppo attivo. Esegui il backup delle note importanti e consulta le note di rilascio prima di aggiornare.

<p align="center">
  <img src="../assets/screenshots/writeonside-screenshot.png" alt="Pannello laterale WriteOnSide su Windows" width="720" />
</p>

## Installazione

### Scaricare una build Windows

Scarica l'ultima `WriteOnSide.exe` da
[GitHub Releases](https://github.com/Thymine2001/WriteOnSide/releases).

WriteOnSide è attualmente distribuito come applicazione Windows portatile in un singolo file:

1. Scarica `WriteOnSide.exe`.
2. Mettila in una cartella dove vuoi conservare l'applicazione.
3. Avvia e seleziona una cartella note o un Vault Obsidian esistente.
4. Usa `Ctrl+Shift+Enter` per mostrare o nascondere il pannello.

Windows SmartScreen può mostrare un avviso per build di sviluppo non firmate. Verifica che il file provenga da questo repository prima di eseguirlo.

## Caratteristiche principali

### Pannello laterale

- Pannello senza bordi, a tutta altezza, sempre in primo piano
- Layout configurabile a sinistra o a destra dello schermo
- Scorciatoia globale mostra/nascondi, predefinita `Ctrl+Shift+Enter`
- Larghezza pannello, larghezza Esplora file e opacità regolabili
- Apertura, chiusura, layout e ridimensionamento fluidi
- Controlli nella area di notifica e avvio opzionale con Windows
- Istanza singola e posizionamento su aree di lavoro multi-monitor

### Modifica Markdown

- Sorgente Markdown modificabile con evidenziazione sintassi in tempo reale
- Modalità resa in sola lettura con link e immagini
- Barra strumenti per titoli, enfasi, citazioni, elenchi, attività, tabelle, codice, link, immagini, evidenziazioni e colori testo
- Front matter YAML con titoli, tag, date, alias e altri metadati
- Trova e sostituisci, numeri di riga, struttura e titoli fissi
- Blocchi di codice con etichetta lingua e copia con un clic
- Font, dimensioni testo, temi e scorciatoie comandi configurabili

### Lingue dell'interfaccia

L'app include **English**, **中文**, **Português**, **Deutsch**, **Français**, **Nederlands**, **한국어**, **Italiano**, **हिन्दी** e **Українська**. Modifica in **Impostazioni → Generale → Lingua**.

### Compatibilità Obsidian

| Funzionalità | Supporto |
|---|---|
| Wiki link: `[[Note]]`, `[[Note\|alias]]`, `[[Note#Heading]]` | Sì |
| Riferimenti blocco: `[[Note#^block-id]]` | Sì |
| Incorporazioni note e immagini: `![[file]]` | Sì |
| Callout: `> [!note]` | Modalità lettura |
| Note a piè di pagina, `%%commenti%%` e `#tags` inline | Sì |
| Elenchi attività: `- [ ]` e `- [x]` | Sì |
| Rinomina nota e aggiorna wikilink in entrata | Sì |

Digitare `[[` apre il completamento note. `Ctrl+clic` segue un wikilink in modalità modifica. Lo strumento Backlink elenca le note che puntano a quella corrente.

### File e allegati

- Esplora file a caricamento lazy con ricerca ricorsiva
- Filtro tag YAML con selezione multipla
- Crea, rinomina, elimina, trascina e anteprima file
- Modifica Markdown e formati testo o codice comuni
- Incolla o trascina immagini nelle note
- Cartella allegati configurabile con link relativi portabili
- Salvataggi atomici e backup con timestamp fuori dal Vault
- Visualizzatore immagini con zoom e pan

## Requisiti di sistema

**Per utenti finali:**

- Windows 10 o Windows 11
- Sessione desktop standard; Windows on ARM non è ancora stato testato formalmente

**Per sviluppo dal codice sorgente:**

- Python 3.12
- I pacchetti elencati in [`requirements.txt`](../requirements.txt)

## Eseguire dal codice sorgente

```powershell
git clone https://github.com/Thymine2001/WriteOnSide.git
cd WriteOnSide

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\writeonside.py
```

Al primo avvio, seleziona una cartella note o un Vault Obsidian esistente.

## Uso di base

- Usa il pulsante hamburger per aprire o chiudere l'Esplora file.
- Passa tra modalità Modifica e Lettura dalla barra strumenti.
- Crea note dalla barra strumenti o dall'Esplora file.
- Incolla un'immagine direttamente in una nota Markdown per copiarla nella cartella allegati configurata.
- Seleziona tag YAML nella sezione inferiore dell'Esplora per filtrare le note.
- Apri Impostazioni per configurare cartella note, layout, larghezze, opacità, tema, font, scorciatoia globale e scorciatoie barra strumenti.
- Chiudere il pannello nasconde l'app; usa la scorciatoia globale o il menu tray per mostrarla di nuovo.

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

Il codice sorgente attuale contiene test unitari su configurazione, rendering Markdown, scorciatoie, archiviazione, indicizzazione note, sintassi Obsidian, rinomina wikilink e internazionalizzazione.

## Creare un EXE Windows

Lo script di release richiede PyInstaller e PyMuPDF oltre alle dipendenze runtime:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller pymupdf
.\build_release.ps1
```

Lo script:

1. Incrementa la versione patch in `VERSION`.
2. Esporta file PNG e ICO dalle sorgenti logo SVG.
3. Crea un eseguibile Windows monofile con PyInstaller.
4. Lo scrive in `dist-native-tree-vX.Y.Z\WriteOnSide.exe`.
5. Mantiene le tre directory di release più recenti.

Vedi [`BUILDING.md`](../BUILDING.md) per comandi aggiuntivi e risoluzione problemi.

## Posizioni dei dati

| Dati | Posizione |
|---|---|
| Note e allegati | Cartella scelta dall'utente o Vault Obsidian |
| Impostazioni | `%LOCALAPPDATA%\WriteOnSide\config.json` |
| Backup gestiti | `%LOCALAPPDATA%\WriteOnSide\Backups\` |

WriteOnSide non richiede account né servizio cloud integrato. Le note lasciano il computer solo quando l'utente colloca il Vault in un servizio di sincronizzazione configurato separatamente.

## Struttura del progetto

```text
writeonside.py          Punto di ingresso applicazione
writeonside_app/        Codice sorgente applicazione
assets/                 Risorse SVG, PNG e ICO
scripts/                Script di supporto build
tests/                  Test unitari
licenses/               Testi licenza terze parti
WriteOnSide.spec        Configurazione PyInstaller
build_release.ps1       Script release Windows versionato
BUILDING.md             Istruzioni build dettagliate
THIRD_PARTY_NOTICES.md  Attribuzione dipendenze e indice licenze
LICENSE                 Licenza MIT codice sorgente WriteOnSide
```

## Licenza

Il codice sorgente originale di WriteOnSide è sotto
[licenza MIT](../LICENSE).

I componenti di terze parti restano soggetti alle rispettive licenze elencate in
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

<p align="center">
  <sub>Python | Tkinter | Markdown | File in chiaro compatibili Obsidian</sub>
</p>
