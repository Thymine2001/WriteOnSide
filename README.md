<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/writeonside_logo_dark.svg" />
    <source media="(prefers-color-scheme: light)" srcset="assets/writeonside_logo_light.svg" />
    <img src="assets/writeonside_logo_light.svg" alt="WriteOnSide logo" width="96" />
  </picture>
</p>

<h1 align="center">WriteOnSide</h1>

<p align="center">
  <strong>Your notes, one shortcut away.</strong><br />
  A local-first Markdown and text editor that lives at the edge of Windows.
</p>

<p align="center">
  <a href="https://github.com/Thymine2001/WriteOnSide/releases/latest"><img src="https://img.shields.io/github/v/release/Thymine2001/WriteOnSide?include_prereleases&sort=semver&label=release" alt="Latest release" /></a>
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows&logoColor=white" alt="Windows 10 and 11" />
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
  <a href="LICENSE"><img src="https://img.shields.io/github/license/Thymine2001/WriteOnSide" alt="MIT license" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Markdown-editor-000000?logo=markdown&logoColor=white" alt="Markdown editor" />
  <img src="https://img.shields.io/badge/storage-local--first-16A34A" alt="Local-first storage" />
  <img src="https://img.shields.io/badge/app-portable-0EA5E9" alt="Portable application" />
  <img src="https://img.shields.io/badge/interface-10_languages-F59E0B" alt="10 interface languages" />
</p>

<p align="center">
  <a href="https://github.com/Thymine2001/WriteOnSide/releases"><strong>Download for Windows</strong></a>
  ·
  <a href="#quick-start">Quick start</a>
  ·
  <a href="#run-from-source">Run from source</a>
</p>

WriteOnSide（**随边记**）is a lightweight side-panel editor for quick capture,
Markdown writing, local knowledge bases, and small source-file edits. Press one
global shortcut and it slides in beside whatever you are doing. Press it again
and it gets out of the way.

There is no proprietary database and no required account. Notes remain ordinary
files in a folder you choose, ready to use with Obsidian, VS Code, Git, backup
software, or any other tool you trust.

<p align="center">
  <img src="assets/screenshots/writeonside-screenshot.png" alt="WriteOnSide side-panel workflow demonstration" width="800" />
</p>

> [!NOTE]
> WriteOnSide is under active development. Back up important notes and review
> release notes before upgrading.

## Why WriteOnSide?

- **Instant access.** Show or hide the panel globally with `Ctrl+Shift+Enter`.
- **Local by default.** Your notes and attachments stay in your chosen folder.
- **A real Markdown workspace.** Edit, render, search, link, tag, and organize notes without opening a full-screen application.
- **Obsidian-friendly.** Use an existing vault, wiki links, embeds, backlinks, YAML metadata, tags, and relative attachments.
- **Useful beyond notes.** Edit common text, configuration, web, and source-code files with syntax highlighting.
- **Fits your desktop.** Choose either screen edge and configure width, opacity, typography, theme, behavior, and shortcuts.

## Quick start

<table>
  <tr>
    <td width="92" align="center">
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="assets/icon_dark.png" />
        <source media="(prefers-color-scheme: light)" srcset="assets/icon_light.png" />
        <img src="assets/icon_light.png" alt="WriteOnSide application icon" width="72" />
      </picture>
    </td>
    <td>
      <strong>No installer required.</strong><br />
      Download the portable executable, choose your notes folder, and start writing.
    </td>
  </tr>
</table>

1. Download the newest `WriteOnSide.exe` from [GitHub Releases](https://github.com/Thymine2001/WriteOnSide/releases).
2. Run it and select a notes folder or an existing Obsidian vault.
3. Follow the generated `Welcome.md` guide to create your first note and explore the workspace.
4. Use `Ctrl+Shift+Enter` whenever you want to show or hide the panel.

WriteOnSide is a portable, single-file Windows application. Windows SmartScreen
may warn about unsigned development builds; verify that the executable came from
this repository before running it.

## Highlights

### ✍️ Write and read

- Live Markdown highlighting in Edit mode and a clean rendered Read mode
- Formatting commands for headings, emphasis, color, highlights, quotes, lists, tasks, tables, links, images, and code
- Rendered images, clickable links, callouts, note embeds, footnotes, and copyable fenced code blocks
- YAML front matter editor for titles, tags, dates, aliases, and other metadata
- Line numbers, heading folding, sticky headings, and outline navigation
- Find and replace, configurable auto-save, and command shortcuts
- Large-document safeguards that keep editing responsive

### 🔗 Connect and organize

- Wiki links with completion: `[[Note]]`, `[[Note|alias]]`, `[[Note#Heading]]`, and `[[Note#^block-id]]`
- `Ctrl`+click navigation and create-on-follow for missing wiki-link targets
- Backlinks for every note that points to the current note
- Note and image embeds with `![[...]]`
- Inline and nested tags such as `#idea` and `#project/writeonside`
- Multi-select YAML tag filtering from the Files panel
- Incoming wiki-link updates when a note is renamed

### 📁 Work across files

- Recursive workspace search by filename and content
- Create, rename, move, copy, paste, delete, preview, reveal, and open files externally
- Drag files or folders into the workspace
- Paste or drag images directly into Markdown notes
- Configurable attachment folder with portable relative links
- Image preview with zoom and pan
- Split editing with up to four open notes

### 🪟 Stay out of the way

- Borderless, always-on-top panel on the left or right screen edge
- Resizable editor and Files panel with adjustable opacity
- Global show/hide shortcut and Windows system-tray controls
- Optional launch at Windows startup
- Single-instance behavior and multi-monitor work-area positioning
- Light and dark themes with configurable fonts and sizes

## Markdown and Obsidian compatibility

| Feature | Support |
|---|:---:|
| Standard Markdown headings, emphasis, lists, quotes, links, images, tables, and code | Yes |
| Wiki links, aliases, heading links, and block references | Yes |
| Note and image embeds | Yes |
| Backlinks and rename-aware incoming links | Yes |
| YAML front matter, aliases, and tag filtering | Yes |
| Inline and nested tags | Yes |
| Task lists, footnotes, comments, and dividers | Yes |
| Obsidian-style callouts | Read mode |
| Inline HTML colors, underline, superscript, and subscript | Yes |

WriteOnSide reads and writes normal Markdown; it is not an Obsidian plugin and
does not require Obsidian to be installed.

## Supported files

Markdown, plain-text, log, CSV, web, configuration, data, script, and common
source-code formats can be edited directly. This includes Python, JavaScript,
TypeScript, HTML, CSS, JSON, YAML, TOML, PowerShell, shell scripts, C/C++, C#,
Java, Kotlin, Rust, Go.
Images in PNG, JPEG, GIF, BMP, WebP, TIFF, and ICO formats can be inserted or previewed.
Other files can be opened with their default Windows application.

## Privacy and data safety

- WriteOnSide has no account system, built-in cloud, or hidden note database.
- Notes leave your computer only when **you** place their folder in a separately configured sync service.
- Files are saved atomically to reduce the risk of partial writes.
- Replaced files receive timestamped managed backups outside the workspace.

Managed backups are a recovery aid, not a complete backup strategy. Use a
versioned or synced backup for important work.

## Essential shortcuts

| Action | Default shortcut |
|---|---:|
| Show or hide WriteOnSide | `Ctrl+Shift+Enter` |
| New note | `Ctrl+N` |
| Open file | `Ctrl+O` |
| Save | `Ctrl+S` |
| Toggle Edit / Read mode | `Ctrl+E` |
| Find / Replace | `Ctrl+F` / `Ctrl+H` |
| Outline | `Ctrl+Shift+O` |
| Backlinks | `Ctrl+Shift+B` |

Editor command shortcuts and the global shortcut can be reassigned in Settings.

## Interface languages

English · 中文 · Português · Deutsch · Français · Nederlands · 한국어 · Italiano · हिन्दी · Українська

Change the interface language under **Settings → General → Language**.

## Run from source

### Requirements

- Windows 10 or Windows 11
- Python 3.12

```powershell
git clone https://github.com/Thymine2001/WriteOnSide.git
cd WriteOnSide

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\writeonside.py
```

## Development

Run the test suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

Build a portable Windows executable:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\build_release.ps1
```

The release script updates version metadata, exports application icons, builds
the single-file executable, and writes it to a versioned distribution folder.
See [BUILDING.md](BUILDING.md) for the complete packaging workflow.

## Data locations

| Data | Location |
|---|---|
| Notes and attachments | User-selected folder or Obsidian vault |
| Settings | `%LOCALAPPDATA%\WriteOnSide\config.json` |
| Managed backups | `%LOCALAPPDATA%\WriteOnSide\Backups\` |

## License

WriteOnSide is released under the [MIT License](LICENSE). Third-party components
retain their respective licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

<p align="center">
  <sub>Local files. Fast capture. No lock-in.</sub>
</p>
