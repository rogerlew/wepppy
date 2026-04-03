# Marp / Marp CLI Usage Reference

Use this file as the authoritative command and syntax cookbook.

## Prerequisites
- Node.js `v18+` for `npx @marp-team/marp-cli@latest`.
- A supported browser installed for PDF/PPTX/image rendering:
  - Google Chrome, Microsoft Edge, or Mozilla Firefox.

## Minimal deck skeleton

```markdown
---
marp: true
theme: gaia
paginate: true
size: 16:9
---

# Slide 1 title

Key point.

---

# Slide 2 title

Next key point.
```

Notes:
- Split slides with `---`.
- Marp syntax is CommonMark-based with directives.
- Front-matter can define global directives (`theme`, `paginate`, `size`).

## Directive usage
- HTML comments can define directives.
- Non-directive HTML comments are collected as presenter notes in Marpit-compatible tooling.

Examples:

```markdown
<!-- _backgroundColor: #ffffff -->
<!-- _color: #1e293b -->

# A slide with local styling

<!-- Presenter note: Emphasize the assumptions behind this chart. -->
```

## Core CLI commands

```bash
# HTML (default)
npx @marp-team/marp-cli@latest deck.md -o deck.html

# PDF
npx @marp-team/marp-cli@latest deck.md --pdf -o deck.pdf

# PPTX
npx @marp-team/marp-cli@latest deck.md --pptx -o deck.pptx

# Presenter notes export (txt)
npx @marp-team/marp-cli@latest deck.md --notes -o deck.notes.txt

# Watch mode
npx @marp-team/marp-cli@latest -w deck.md

# Server mode
npx @marp-team/marp-cli@latest -s ./slides
```

## Useful export options

```bash
# PDF notes and outlines
npx @marp-team/marp-cli@latest deck.md --pdf --pdf-notes --pdf-outlines -o deck.pdf

# Convert first slide to image (title card)
npx @marp-team/marp-cli@latest deck.md --image png -o title.png

# Convert all slides to images
npx @marp-team/marp-cli@latest deck.md --images png
```

## Local files and security
Browser-based conversion blocks local file access by default.
Use only with trusted markdown:

```bash
npx @marp-team/marp-cli@latest deck.md --pdf --allow-local-files -o deck.pdf
```

## Theme and math notes
- Built-in themes include `default`, `gaia`, and `uncover`.
- Marp Core supports `math` global directive (`mathjax` or `katex`).
- For custom CSS themes, use `--theme` or `--theme-set`.

## Known tradeoff: editable PPTX
`--pptx-editable` is experimental and may reduce visual fidelity.
Use only when downstream editing in PowerPoint is required.
