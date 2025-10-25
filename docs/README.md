# Documentation Overview

This directory holds top-level documentation that supports the codebase. Use these guides to locate the right place for architectural notes, UI references, and multi-step initiatives.

## Directory Guide
- `work-packages/` — Formal, multi-deliverable work packages with full templates, trackers, and prompts.
- `mini-work-packages/` — Lightweight “mini packages” for focused efforts (for example, one-off controller upgrades) that still need a tracked plan or retrospective but do not warrant the full work-package structure.
- `dev-notes/` — Deep dives, design investigations, and subsystem notes that should live close to—but outside—the source tree.
- `ui-docs/` — Front-end documentation: control behaviors, style guidance, and UI-focused how-tos.
- `prompt_templates/` — Prompt scaffolds for recurring agent tasks (documentation workflows, code migrations, etc.).

Prefer to keep documentation alongside the relevant source module when practical. Use the `docs/` tree for cross-cutting references, UI guidance, or coordinated efforts (work packages and mini packages).

## Authoring Notes
- Always reference the authoritative guides in `AGENTS.md` when creating or updating docs.
- Link related source files so future readers know where behavior is implemented.
- When a mini package graduates into a broader initiative, migrate it into `work-packages/` and note the transition in its tracker.

