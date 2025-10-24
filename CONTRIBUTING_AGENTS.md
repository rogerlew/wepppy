# Contributing Guide for AI Coding Agents

> Quick orientation for Copilot, Claude, Gemini, and other assistants collaborating on wepppy.

## Purpose
- Serve as the lightweight front desk for agents landing in the repo.
- Point to the authoritative playbooks (`AGENTS.md`, READMEs, dev-notes) instead of duplicating them.
- Capture only the routing and validation hints that are unique to day-to-day contribution work.

## Core References
- `AGENTS.md` — canonical agent runbook covering architecture, conventions, and tooling (start here every session).
- `ARCHITECTURE.md` — system topology, service boundaries, and cross-language touch points.
- `docs/dev-notes/style-guide.md` — developer ergonomics and review checklist.
- `readme.md` — human-facing overview suitable for sharing context with project stakeholders.
- `tests/AGENTS.md` — fixtures, stubs, and marker expectations for the pytest suite.
- `docs/prompt_templates/` — templates for writing READMEs, AGENTS docs, and module briefs.

## Workflow Snapshot
1. Read or refresh `AGENTS.md` to align with current directives.
2. Scope the change: skim the relevant README or dev-note before touching code.
3. Edit using the repo’s existing patterns; when unsure, mirror adjacent implementations.
4. Validate locally via the `wctl` tooling wrappers (see checklist below) and document updates alongside code.

## Change Routing Cheatsheet
| Change type | Primary home | Notes |
| --- | --- | --- |
| NoDb state or run configuration | `wepppy/nodb/core/` (mods under `wepppy/nodb/mods/`) | Follow locking and serialization conventions in `AGENTS.md` (“Working with NoDb Controllers”). |
| Background and queued work | `wepppy/rq/` | Use `@job` decorators, emit status via controller loggers, and register orchestration in the relevant Flask route or NoDb controller. |
| Run-scoped HTTP endpoints | `wepppy/weppcloud/routes/` or `wepppy/weppcloud/webservices/` | Leverage `url_for_run()` for run-specific URLs; cross-check associated templates or controllers. |
| Query Engine / MCP extensions | `wepppy/query_engine/app/mcp/` | Keep FastAPI router signatures in sync with stubs and update the catalog if payload shapes change. |
| Templated documentation or onboarding material | `docs/` (see prompt templates) | Run `uk2us` on prose after edits and update audit docs when expanding coverage. |
| Static assets or controllers | `wepppy/weppcloud/static-src/` and `wepppy/weppcloud/controllers_js/` | Rebuild bundles with `wctl build-static-assets` or the controller builder, then run lint/tests via `wctl run-npm`. |

## Validation Checklist
- `wctl run-pytest tests/<path>` — targeted suite while iterating.
- `wctl run-pytest tests --maxfail=1` — broad sanity before handoff.
- `wctl run-npm lint` / `wctl run-npm test` — required for front-end/controller changes.
- `wctl run-stubtest <module>` — when signatures or exports shift.
- `uk2us -i <file>` (after diff review) — normalize American English in touched prose.
- Refresh or author README/AGENTS entries when behavior, APIs, or workflows change.

## When Something Feels Off
- Check `docs/dev-notes/` for subsystem-specific briefs (`controller_foundations.md`, `redis_dev_notes.md`, etc.).
- Inspect existing tests in `tests/` and reuse fixtures before crafting new ones.
- Prefer asking for human clarification when requirements are ambiguous; the maintainers expect agents to surface blockers.

---

**Last Updated**: 2025-10-24 (synchronized with `AGENTS.md`)
