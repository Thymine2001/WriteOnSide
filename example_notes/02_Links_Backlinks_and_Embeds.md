---
title: Links, Backlinks, and Embeds
tags: [test/wiki, test/backlinks, project/beta]
created: 2026-06-16
aliases: [Wiki Lab]
---

# Links, Backlinks, and Embeds

Use this note to test wikilinks, aliases, backlinks, heading links, block links, and note embeds.

## Basic links

- Link to target note: [[03_Target_Note]]
- Link using alias: [[03_Target_Note|target alias text]]
- Link to a heading: [[03_Target_Note#Heading Destination]]
- Link to a block: [[01_Markdown_Rendering_Lab#^render-block]]
- Link to nested note: [[Projects/Alpha/08_Nested_Project_Note]]

## Embedded note

The next line embeds another note in read mode:

![[03_Target_Note]]

## Image reference

Markdown image preview:

![Example icon](assets/icon_light.png)

Manual wiki image embed test:

1. Copy or drag an image into this Vault.
2. Rename it `sample-image.png`.
3. Add `![[sample-image.png]]` below.
4. Verify read mode and split editor preview can resolve it after the index refreshes.

## Backlinks expectation

Open [[03_Target_Note]], click Backlinks, and this note should appear as a source.
