# Documentation Overview

This directory holds top-level documentation that supports the codebase. Use these guides to locate the right place for architectural notes, UI references, and multi-step initiatives.

## Directory Guide
- `work-packages/` — Formal, multi-deliverable work packages with full templates, trackers, and prompts.
- `mini-work-packages/` — Lightweight “mini packages” for focused efforts (for example, one-off controller upgrades) that still need a tracked plan or retrospective but do not warrant the full work-package structure.
- `schemas/` — Normative contracts for cross-service behavior and payloads (for example CSRF/session/auth-response contracts).
- `standards/` — Cross-cutting implementation standards that should stay stable across modules (for example, NoDb facade/collaborator extraction rules).
- `ablation/` — Canonical investigation package structure and templates for ablation testing (`incident.md`, `notes.md`, `matrix.csv`, artifacts manifest) across dev (`forest`) and prod (`wepp1`/`wepp2`) environments.
- `dev-notes/` — Deep dives, design investigations, and subsystem notes that should live close to—but outside—the source tree.
- `ui-docs/` — Front-end documentation: control behaviors, style guidance, and UI-focused how-tos.
- `prompt_templates/` — Prompt scaffolds for recurring agent tasks (documentation workflows, code migrations, etc.).

Prefer to keep documentation alongside the relevant source module when practical. Use the `docs/` tree for cross-cutting references, UI guidance, or coordinated efforts (work packages and mini packages).

## Canonical Contracts
- CSRF: `docs/schemas/weppcloud-csrf-contract.md`
- Browser/session lifecycle: `docs/schemas/weppcloud-session-contract.md`
- JWT/auth claims and token classes: `docs/dev-notes/auth-token.spec.md`
- RQ API response envelope: `docs/schemas/rq-response-contract.md`
- RQ agent API surface: `docs/schemas/rq-engine-agent-api-contract.md`
- RQ controller-state/schema API (draft): `docs/schemas/rq-controller-state-contract.md`

## Authoring Notes
- Always reference the authoritative guides in `AGENTS.md` when creating or updating docs.
- Link related source files so future readers know where behavior is implemented.
- When a mini package graduates into a broader initiative, migrate it into `work-packages/` and note the transition in its tracker.
