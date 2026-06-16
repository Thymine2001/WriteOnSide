---
title: WriteOnSide Test Vault Index
tags: [test/index, test/all, ui]
created: 2026-06-16
aliases: [Test Home, QA Index]
---

# WriteOnSide Test Vault Index

Use this folder as the Notes folder in WriteOnSide. Start here, then open the linked notes to verify each feature.

## Core workflow checklist

- Open this note from Files by double-clicking.
- Single-click other files in Files: selection should change without opening.
- Toggle Edit/Read mode and compare source highlighting with rendered output.
- Open Files, search for `split`, `frontmatter`, `image`, `source`, and `nested`.
- Use tag filters for `test/markdown`, `test/wiki`, `test/files`, `test/split`, and `project/alpha`.
- Right-click [[04_Split_Screen_Workbench]] and [[02_Links_Backlinks_and_Embeds]] in Files, then choose "Open in Split" to open split panes.
- In a split pane, edit text, verify live Markdown highlighting, image preview, Save, and the vertical swap icon.
- Click the split pane swap icon: this note should swap with the selected split note.
- Click the Find button twice: it should open, then close. Search should affect the main note only.
- Open Backlinks on [[03_Target_Note]] and verify incoming links.
- Rename [[03_Target_Note]] from Files and verify incoming wikilinks update.

## Feature notes

1. [[01_Markdown_Rendering_Lab]]
2. [[02_Links_Backlinks_and_Embeds]]
3. [[03_Target_Note]]
4. [[04_Split_Screen_Workbench]]
5. [[05_Files_Attachments_and_Previews]]
6. [[06_Settings_Themes_and_Shortcuts]]
7. [[07_Search_Replace_and_Outline]]
8. [[Projects/Alpha/08_Nested_Project_Note]]

## Non-Markdown preview/edit files

- [[Plain_Text_Sample.txt]]
- [[Source_Code_Sample.py]]
- [[Preview_Sample.html]]

## Intentional test tags

Inline tags: #inline-test #project/alpha #todo/review

## Expected image preview

This image uses a relative path to a repository asset. It should preview in the main editor and split panes:

![WriteOnSide icon](../assets/icon_light.png)
