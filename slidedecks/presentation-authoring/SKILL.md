---
name: presentation-authoring
description: Build academic/technical slide decks from long markdown docs with a concise narrative-first workflow, then render with Marp/Marp CLI into HTML/PDF/PPTX without guessing syntax or commands.
---

# Presentation Authoring (Marp + Marp CLI)

Use this skill when the user asks to turn documentation into a clean slide deck, especially for technical or academic talks.

## What this skill produces
- A reduced-content slide narrative from long source text.
- A Marp-compatible `deck.md` with explicit slide boundaries.
- Reproducible exports (`.html`, `.pdf`, `.pptx`, optional notes `.txt`).

## Inputs you should gather
- Source markdown path(s), for example `wepppy/weppcloud/routes/usersum/weppcloud/user-guide.md`.
- Target audience (technical peers, mixed, executive, students).
- Time budget (minutes) and deck style (conference, tutorial, walkthrough, lightning).

## Workflow
1. Scope the story first, not the slides.
- Define one audience-specific thesis.
- Draft 3-5 section-level takeaways.
- Decide required detail depth by time limit.

2. Reduce source content aggressively.
- Keep only content needed to support the thesis.
- Default: 1 major idea per slide.
- Default pacing: about 1 minute per slide.
- Move implementation details, caveats, and verbose examples to backup slides.

3. Author `deck.md` in Marp markdown.
- Split slides with `---`.
- Use YAML front-matter for global directives (`theme`, `paginate`, `size`).
- Use assertion-style headings that state the takeaway.
- Use visuals/diagrams where possible, minimal on-slide text.

4. Render with Marp CLI.
- Prefer `npx @marp-team/marp-cli@latest` for one-shot reproducible runs.
- Export at least PDF and PPTX unless user asks otherwise.

5. Run a final quality pass.
- Can a distracted person infer each slide's takeaway from heading + visual?
- Any slide taking >1 minute to explain should be split or reduced.
- Verify references and acknowledgments are present when needed.

## Command quick start
Use exact commands from `references/marp_marp-cli_usage.md`.

For fast all-format export, run:

```bash
bash slidedecks/presentation-authoring/scripts/render_marp.sh <deck.md> [output_dir]
```

## Reference files
- Best practices: `references/academic_technical_best_practices.md`
- Marp syntax + CLI cookbook: `references/marp_marp-cli_usage.md`
- Source URLs and evidence map: `references/source_index.md`
- Starter deck template: `assets/technical-talk-template.md`

## Guardrails
- Do not convert paragraphs into bullet dumps.
- Do not keep manuscript-level detail in primary slides.
- Do not invent unsupported claims when compressing technical material.
- Prefer explicit backup slides over overloading core slides.
