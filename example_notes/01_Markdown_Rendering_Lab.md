---
title: Markdown Rendering Lab
tags: [test/markdown, test/rendering, project/alpha]
created: 2026-06-16
aliases:
  - Markdown Lab
  - Rendering Test
---

# Markdown Rendering Lab

This note exercises live editor highlighting, read-mode rendering, headings, outline navigation, sticky headings, folding, lists, tables, code, callouts, footnotes, comments, and inline styles.

## Headings

### H3 heading

#### H4 heading

##### H5 heading

###### H6 heading

## Emphasis and inline formatting

Plain text, **bold text**, *italic text*, <u>underlined text</u>, ~~struck text~~, ==highlighted text==, `inline code`, <sup>superscript</sup>, and <sub>subscript</sub>.

HTML color test: <span style="color:#e11d48">rose text</span>, <font color="#0f766e">teal text</font>, and normal text again.

## Lists

- Bullet item one
- Bullet item two with **bold**
  - Nested bullet

1. Ordered item one
2. Ordered item two
3. Ordered item three

- [ ] Task not done
- [x] Task done
- [ ] Task with #inline-task tag

## Block quote

> This is a block quote.
> It should render with quote styling and live editor highlighting.

## Callouts

> [!note] Normal note
> This verifies Obsidian-style callout rendering in read mode.

> [!warning] Warning
> Warning callouts should stand out.

## Table

| Feature | Edit highlight | Read render |
|---|:---:|---:|
| Bold | yes | yes |
| Table | yes | yes |
| Links | yes | yes |

## Code block

```python
def hello(name: str) -> str:
    return f"Hello, {name}!"

print(hello("WriteOnSide"))
```

Hover the code block in read mode to verify the copy button.

## Horizontal rules

---

***

___

## Comments and footnotes

%% This comment should be hidden in read mode and styled as a comment in edit mode. %%

Footnote reference here.[^rendering-footnote]

[^rendering-footnote]: Footnote content for read-mode rendering.

## Block ID

This paragraph has a block id for wikilink jump tests. ^render-block

## Image preview in editor and split panes

![Icon from example assets](assets/icon_light.png)
