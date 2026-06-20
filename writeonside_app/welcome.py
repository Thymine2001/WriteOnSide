from __future__ import annotations


WELCOME_NOTE_BODY = """<span style="color: #e11d48">● IMPORTANT</span> ==Press `Ctrl+E` now to switch to Read mode and see this guide as it is meant to look.==

# Welcome to WriteOnSide

Your notes now have a fast, private workspace at the edge of your screen. This page is both a quick start and a live Markdown example—edit anything, check items off, or delete it when you no longer need it.

> [!note] Your notes stay yours
> WriteOnSide saves ordinary Markdown files in the folder you selected. No account or built-in cloud service is required, and the same folder can be used as an Obsidian Vault.

## Start here: your first minute

- [ ] Press `Ctrl+N`, name a note, and write one sentence.
- [ ] Press `Ctrl+S` to save it. Auto-save is enabled by default.
- [ ] Press `Ctrl+E` to switch between **Edit** and **Read** mode.
- [ ] Press `Ctrl+Shift+Enter` to hide WriteOnSide, then press it again to bring it back.
- [ ] Open **Files** with the menu button and return to this guide at any time.

That is the core workflow. Everything below helps you turn a folder of notes into a connected workspace.

## Know your workspace

| Area | What it does |
|---|---|
| **Files** | Browse folders, search notes, filter by tags, and manage files. |
| **Editor** | Write Markdown with live formatting, line numbers, images, and sticky headings. |
| **Read mode** | See the rendered document, follow links, view embeds, and copy code. |
| **Toolbar** | Create, save, format, search, open the outline, view backlinks, and change settings. |
| **Screen edge** | Resize the panel or move it to the left or right in Settings. |

Closing the panel hides it instead of quitting. Use the global shortcut or the WriteOnSide icon in the Windows system tray to show it again or exit completely.

## Write without leaving the keyboard

Select text and use the toolbar, or type Markdown directly:

- **Bold** with `Ctrl+B`, *italic* with `Ctrl+I`, <u>underline</u> with `Ctrl+U`
- ~~Strikethrough~~, ==highlight==, `inline code`, and [web links](https://www.markdownguide.org/)
- Bulleted and numbered lists
- [ ] Open tasks and - [x] completed tasks
- Quotes, dividers, tables, images, and fenced code blocks

```python
def capture_idea(idea):
    return f"Write it down: {idea}"
```

In Read mode, code blocks include a copy button. The toolbar can insert any of these structures for you, and every command shortcut can be changed in **Settings → Shortcuts**.

## Organize with headings and metadata

Use `#`, `##`, and `###` headings to give a long note structure. Open **Outline** (`Ctrl+Shift+O`) to jump between headings; as you scroll in Edit mode, the current heading stays visible.

Every new note begins with YAML front matter like the block at the top of this file:

```yaml
---
title: Project Journal
tags: [work, journal]
created: 2026-06-19
aliases: [Journal]
---
```

Use **YAML Front Matter** (`Ctrl+Alt+Y`) to add or edit the title, tags, date, aliases, and other metadata. Tags appear in the bottom of Files, where you can select one or more to filter your notes. Inline tags such as #idea and #project/writeonside are supported too.

## Connect your thinking

Type `[[` to search for another note and insert a wiki link:

- `[[Meeting Notes]]` links to a note.
- `[[Meeting Notes|today's meeting]]` gives the link a friendly label.
- `[[Meeting Notes#Decisions]]` jumps to a heading.
- `[[Meeting Notes#^decision-1]]` jumps to a block ID.
- `![[Meeting Notes]]` embeds a note in Read mode.

In Edit mode, hold `Ctrl` and click a wiki link to open it. If the note does not exist, WriteOnSide creates it for you. Try it now with [[My First Note]].

Open **Backlinks** (`Ctrl+Shift+B`) to see every note that points to the current one. If you rename a Markdown note from Files, WriteOnSide can update incoming wiki links so they keep working.

## Find anything again

- Press `Ctrl+F` to find text in the current file.
- Press `Ctrl+H` to find and replace.
- Search in **Files** to find notes recursively by name or content.
- Select YAML tags below the file tree to narrow the results.
- Use **Outline** to navigate a long note without scrolling.

Search this page for `compass` to try the find bar: compass.

## Work with more than one note

Right-click a Markdown file in **Files** and choose **Open in Split**. You can edit and save the second note independently, scroll both notes, and use the swap control to exchange the main and split notes. Up to four notes can be open at once.

This is useful for meeting notes beside an agenda, a draft beside research, or a daily note beside a task list.

## Add images, attachments, and other files

- Paste an image from the clipboard directly into a Markdown note.
- Drag an image into the editor.
- Use the image command (`Ctrl+Shift+I`) to choose a file.
- Drag files or folders into **Files** to copy them into your notes folder.

Images are copied to the attachment folder configured in Settings and inserted with portable relative links. Image files can be previewed with zoom and pan. Markdown and common text or source-code files can be edited; other supported files can be previewed or opened with their Windows application.

## Manage files safely

Right-click items in **Files** to create folders, rename, copy, cut, paste, delete, copy a path, reveal an item in Windows Explorer, preview it, edit it, open it externally, or open a Markdown note in a split.

WriteOnSide uses atomic saves. When it replaces an existing file, it also keeps timestamped managed backups outside your notes folder. Backups are a safety net, not a substitute for your own versioned or synced backup of important notes.

## Make WriteOnSide fit your workflow

Open **Settings** to configure:

- Notes and attachment folders
- Left or right screen-edge position
- Panel width, Files width, and transparency
- Theme, font family, and text size
- Auto-save, startup, and hide behavior
- The global show/hide shortcut and editor command shortcuts
- Interface language

WriteOnSide supports English, 中文, Português, Deutsch, Français, Nederlands, 한국어, Italiano, हिन्दी, and Українська.

## Useful default shortcuts

| Action | Shortcut |
|---|---:|
| New note | `Ctrl+N` |
| Open file | `Ctrl+O` |
| Save | `Ctrl+S` |
| Edit / Read mode | `Ctrl+E` |
| Find / Replace | `Ctrl+F` / `Ctrl+H` |
| Outline | `Ctrl+Shift+O` |
| Backlinks | `Ctrl+Shift+B` |
| Show / hide panel | `Ctrl+Shift+Enter` |

Formatting shortcuts are shown in their toolbar tooltips and can be reassigned in Settings.

## A simple system to try

You do not need to design the perfect folder structure before writing. Start with three notes:

1. A daily note for quick capture.
2. A projects note containing links to active work.
3. A reference note for information you want to keep.

Connect them with wiki links and add tags only when they help retrieval. Your plain Markdown files remain usable in any text editor.

> [!warning] Before switching note folders
> Save open work first. WriteOnSide remembers your last note and can open an existing folder or Obsidian Vault, but it does not move files between workspaces automatically.

## You are ready

Create a note with `Ctrl+N`, or turn [[My First Note]] into your first connected page. Keep this guide as a reference, rename it, or delete it—the workspace is yours.

%% Comments like this remain in the Markdown source but are hidden in Read mode. %%

WriteOnSide also supports footnotes.[^welcome-footnote]

[^welcome-footnote]: Switch to Read mode to see how a footnote is rendered.
"""
