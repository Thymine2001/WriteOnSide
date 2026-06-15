<p align="center">
  <img src="assets/writeonside_logo_light.svg" alt="WriteOnSide logo" width="96" />
</p>

<h1 align="center">WriteOnSide</h1>

<p align="center">
  <strong>A lightweight Windows side-panel Markdown notes app.</strong><br />
  Plain files on disk. Obsidian-friendly. Always one screen edge away.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows" alt="Windows 10 and 11" />
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/version-0.0.47-2ea44f" alt="Version 0.0.47" />
</p>

<p align="center">
  <strong>Languages:</strong>
  <a href="README.md">English</a> |
  <a href="README.zh-CN.md">中文</a> |
  <a href="README.pt.md">Português</a>
</p>

WriteOnSide keeps Markdown notes in a folder you choose. There is no private
database and no required cloud service, so the same Vault can be opened in
WriteOnSide, Obsidian, VS Code, or another text editor.

> [!NOTE]
> WriteOnSide `0.0.47` is a pre-release project under active development.
> Back up important notes and review release notes before upgrading.

<p align="center">
  <img src="assets/screenshots/writeonside-screenshot.png" alt="WriteOnSide side panel on Windows" width="720" />
</p>

## Install

### Download a Windows build

Download the newest `WriteOnSide.exe` from
[GitHub Releases](https://github.com/Thymine2001/WriteOnSide/releases).

WriteOnSide is currently distributed as a portable, single-file Windows
application:

1. Download `WriteOnSide.exe`.
2. Place it in a folder where you want to keep the application.
3. Run it and select a notes folder or an existing Obsidian Vault.
4. Use `Ctrl+Shift+Enter` to show or hide the panel.

Windows SmartScreen may display a warning for unsigned development builds.
Verify that the file came from this repository before running it.

## Highlights

### Side panel

- Borderless, full-height panel that stays on top
- Configurable left or right screen-edge layout
- Global show/hide shortcut, defaulting to `Ctrl+Shift+Enter`
- Adjustable panel width, Explorer width, and opacity
- Smooth open, close, layout, and resize behavior
- System tray controls and optional Windows startup
- Single-instance behavior and multi-monitor work-area positioning

### Markdown editing

- Editable Markdown source with live syntax highlighting
- Read-only rendered mode with links and images
- Formatting toolbar for headings, emphasis, quotes, lists, tasks, tables,
  code, links, images, highlights, and text colors
- YAML front matter with titles, tags, dates, aliases, and other metadata
- Find and replace, line numbers, outline navigation, and sticky headings
- Fenced code blocks with language labels and one-click copy
- Configurable fonts, text sizes, themes, and command shortcuts

### Interface languages

The app ships with **English**, **中文**, and **Português**. Change it in
**Settings → General → Language**.

### Obsidian compatibility

| Feature | Support |
|---|---|
| Wiki links: `[[Note]]`, `[[Note\|alias]]`, `[[Note#Heading]]` | Yes |
| Block references: `[[Note#^block-id]]` | Yes |
| Note and image embeds: `![[file]]` | Yes |
| Callouts: `> [!note]` | Read mode |
| Footnotes, `%%comments%%`, and inline `#tags` | Yes |
| Task lists: `- [ ]` and `- [x]` | Yes |
| Rename a note and update incoming wikilinks | Yes |

Typing `[[` opens note completion. `Ctrl+click` follows a wikilink in edit
mode. The Backlinks tool lists notes that link to the current note.

### Files and attachments

- Lazy-loaded file Explorer with recursive note search
- YAML tag filtering with multi-select support
- Create, rename, delete, drag, and preview files
- Edit Markdown and common text or source-code formats
- Paste or drag images into notes
- Configurable attachment folder with portable relative links
- Atomic saves and timestamped backups outside the Vault
- Image viewer with zoom and pan

## System Requirements

For end users:

- Windows 10 or Windows 11
- A standard desktop session; Windows on ARM has not yet been formally tested

For source development:

- Python 3.12
- The packages listed in [`requirements.txt`](requirements.txt)

## Run From Source

```powershell
git clone https://github.com/Thymine2001/WriteOnSide.git
cd WriteOnSide

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\writeonside.py
```

On first launch, select a notes folder or an existing Obsidian Vault.

## Basic Use

- Use the hamburger button to open or close the Files Explorer.
- Switch between Edit and Read modes from the toolbar.
- Create notes from the toolbar or Files Explorer.
- Paste an image directly into a Markdown note to copy it into the configured
  attachments folder.
- Select YAML tags in the lower Explorer section to filter notes.
- Open Settings to configure the notes folder, layout, widths, opacity, theme,
  font, global toggle shortcut, and toolbar shortcuts.
- Closing the panel hides the application; use the global shortcut or tray
  menu to show it again.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

The current source tree contains 44 unit tests covering configuration,
Markdown rendering, shortcuts, storage, note indexing, Obsidian syntax,
wikilink rename behavior, and internationalization.

## Build a Windows EXE

The release script requires PyInstaller and PyMuPDF in addition to the runtime
dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller pymupdf
.\build_release.ps1
```

The script:

1. Increments the patch version in `VERSION`.
2. Exports PNG and ICO files from the SVG logo sources.
3. Builds a single-file Windows executable with PyInstaller.
4. Writes it to `dist-native-tree-vX.Y.Z\WriteOnSide.exe`.
5. Retains the three newest release directories.

See [`BUILDING.md`](BUILDING.md) for additional commands and troubleshooting.

## Data Locations

| Data | Location |
|---|---|
| Notes and attachments | User-selected folder or Obsidian Vault |
| Settings | `%LOCALAPPDATA%\WriteOnSide\config.json` |
| Managed backups | `%LOCALAPPDATA%\WriteOnSide\Backups\` |

WriteOnSide does not require an account or built-in cloud service. Notes leave
the computer only when the user places the Vault in a separately configured
sync service.

## Project Layout

```text
writeonside.py          Application entry point
writeonside_app/        Application source code
assets/                 SVG, PNG, and ICO application assets
scripts/                Build helper scripts
tests/                  Unit tests
licenses/               Third-party license texts
WriteOnSide.spec        PyInstaller configuration
build_release.ps1       Versioned Windows release script
BUILDING.md             Detailed build instructions
THIRD_PARTY_NOTICES.md  Dependency attribution and license index
LICENSE                 MIT license for WriteOnSide source code
```


## Licensing

WriteOnSide's original source code is licensed under the
[MIT License](LICENSE).

Third-party components remain subject to their respective licenses listed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

<p align="center">
  <sub>Python | Tkinter | Markdown | Obsidian-compatible plain files</sub>
</p>
