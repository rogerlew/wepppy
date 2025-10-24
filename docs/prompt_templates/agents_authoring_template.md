# AGENTS.md Authoring Template

## Authorship
**This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**

## Purpose
Use this template when drafting or refreshing an `AGENTS.md`. The goal is to give on-call AI agents a concise operational guide for a directory or subsystem: mission, critical files, standard workflows, validation steps, and escalation paths.

## Required Blocks
- **Authorship directive (mandatory, verbatim):**
  ```
  ## Authorship
  **This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**
  ```
  Place the block immediately after the title. Never paraphrase or relocate it.
- **Mission Snapshot** – 3–5 bullets answering “What does this directory own and why does it matter?”
- **Primary Assets / Key Files** – call out critical modules, data folders, scripts, stubs, and tests.
- **Standard Workflow** – numbered steps an agent should follow when making changes (scope, edit, document, validate).
- **Validation Checklist** – runnable commands, manual review steps, or sanity checks required before handoff.
- **References** – cross-links to adjacent docs (root `AGENTS.md`, README, design notes).

## Suggested Sections
- Troubleshooting or “Common Pitfalls” with quick fixes.
- Implementation Notes capturing domain quirks, invariants, or file format gotchas.
- Communication cues (who to sync with, where to log changes) if relevant to the subsystem.

## Authoring Workflow
1. **Recon** – skim the directory structure, existing READMEs, tests, and stubs. Capture critical commands or data dependencies.
2. **Outline** – map section headers using the required blocks, then add optional sections as needed.
3. **Draft** – write short, direct bullets that assume readers are agents with full repo access. Link to files using workspace-relative paths.
4. **Review** – verify instructions comply with core directives (NoDb patterns, test markers, stub maintenance). Make sure no secrets or credentials slip into examples.
5. **Normalize** – run `uk2us` when you touch prose if the file already follows American English norms; double-check diff to avoid corrupting code blocks.

## Style Guidelines
- Write in active voice with task-oriented phrasing.
- Prefer bullets over dense paragraphs; keep lists to 4–6 items when possible.
- Use inline code for commands (`wctl run-pytest tests/...`), file paths (`wepppy/nodb/base.py`), and config keys.
- Avoid speculation—document current behavior and expectations. Note open questions explicitly in a “TODO / Follow-up” subsection if unavoidable.
- Do not duplicate long explanations from the root `AGENTS.md`; link instead.

## Validation
- `git diff --stat` and skim the rendered Markdown to ensure formatting holds.
- Confirm every referenced command or file exists. Update tooling references if they change (`wctl`, module names, test markers).
- When adding new AGENTS content, notify maintainers if you discover gaps in the global conventions so the root guidance can be updated.

## Maintenance
- Revisit AGENTS files after major refactors, new onboarding tasks, or when tests/tooling expectations shift.
- If multiple directories share similar guidance, factor reusable text into `docs/prompt_templates/` and reference it from individual AGENTS files.
