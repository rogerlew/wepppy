# slidedecks/AGENTS.md
> Local playbook for slide-deck work under `slidedecks/`.

## Scope
- Applies to all files under `slidedecks/`.

## Purpose
- Keep slide-deck authoring reproducible for technical and academic presentations.
- Ensure agents use the in-repo Marp workflow and evidence-backed slide rules.

## Required Workflow
1. Follow `presentation-authoring/SKILL.md`.
2. Use references in `presentation-authoring/references/` for:
- slide-content reduction rules
- Marp/Marp CLI syntax and commands
3. Start new decks from `presentation-authoring/assets/technical-talk-template.md`.
4. Render exports via:
- `presentation-authoring/scripts/render_marp.sh`

## Directory conventions
- Place each deck in its own folder:
- `slidedecks/<topic-slug>/`
- Expected files per deck:
- `deck.md`
- optional `figures/*`
- generated outputs: `deck.html`, `deck.pdf`, `deck.pptx`, `deck.notes.txt`

## Authoring constraints
- Keep one major idea per primary slide.
- Prefer assertion-style headings over generic headings.
- Keep implementation detail in backup slides unless central to the thesis.
- Do not invent claims when compressing source material.
