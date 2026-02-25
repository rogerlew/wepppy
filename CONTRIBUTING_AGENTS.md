# Contributing Guide for AI Coding Agents

> Quickstart for Copilot, Codex, Claude, Gemini, and other assistants contributing to wepppy.

## Purpose
- Provide a fast day-1 contribution workflow for agents.
- Route contributors to canonical docs instead of duplicating policy.
- Keep contribution hygiene consistent across coding, testing, and handoff.

## First Session Checklist
1. Read root `AGENTS.md` for global directives and repository contracts.
2. Open the nearest subsystem `AGENTS.md` for the files you will edit.
3. Skim the local README/tests for patterns before changing implementation.
4. Decide validation commands up front (`wctl` wrappers).
5. Update docs alongside behavior changes (README, AGENTS, or work package notes).

## Core References
- Global onboarding map: `AGENTS.md`
- Active work board: `PROJECT_TRACKER.md`
- Full work package process: `docs/work-packages/README.md`
- System architecture: `ARCHITECTURE.md`
- Human-facing overview: `readme.md`
- Tests playbook: `tests/AGENTS.md`
- Prompt/template index: `docs/prompt_templates/AGENTS.md`

## Subsystem Entry Points
- NoDb: `wepppy/nodb/AGENTS.md`
- WEPPcloud: `wepppy/weppcloud/AGENTS.md`
- Controller JS: `wepppy/weppcloud/controllers_js/AGENTS.md`
- RQ engine: `wepppy/microservices/rq_engine/AGENTS.md`

## Change Routing Cheatsheet
| Change type | Primary location | Notes |
| --- | --- | --- |
| NoDb state or run config | `wepppy/nodb/core/` and `wepppy/nodb/mods/` | Follow locking/serialization rules in `wepppy/nodb/AGENTS.md`. |
| RQ jobs and orchestration | `wepppy/rq/` | Update dependency catalog when queue wiring changes. |
| Run-scoped routes and views | `wepppy/weppcloud/routes/` | Preserve run-scoped auth and URL construction expectations. |
| WEPPcloud controller JavaScript | `wepppy/weppcloud/controllers_js/` | Rebuild/validate with frontend `wctl run-npm` checks. |
| GL dashboard code | `wepppy/weppcloud/static/js/gl-dashboard/` | Follow local AGENTS guidance for scenario/query flows. |
| RQ engine microservice routes | `wepppy/microservices/rq_engine/` | Keep payload contracts aligned with `docs/schemas/rq-response-contract.md`. |
| Docs/onboarding updates | `docs/`, root docs, nested AGENTS | Keep docs terse and linked, not duplicated. |

## Validation Checklist
- Canonical command list lives in root `AGENTS.md` (`Validation Entry Points`).
- Contributor minimum:
  - Run at least one targeted validation for the touched surface while iterating.
  - Run at least one pre-handoff sanity gate for the touched surface, or document why it was skipped.
- For exact command forms, use root `AGENTS.md` (`Validation Entry Points`).

## Code Quality Review Component
- Review the code-quality observability report for changed-file deltas (`improved`, `unchanged`, `worsened`).
- Treat severity bands as non-blocking telemetry; do not stall delivery solely on threshold crossings.
- If a touched file worsens materially, include a short rationale or follow-up cleanup note in handoff text.

## Exception Handling Policy
- Exception observability is a **canonical requirement**: failures must be diagnosable via logs and surfaced error payloads (for example `error.details` / stack traces) unless doing so would leak PII or secrets.
- Avoid broad handlers (`except Exception` or bare `except`) in normal code paths.
- Catch specific exception types when possible; keep error translation explicit and contract-compliant.
- If a boundary must use a broad catch, keep the block tight, log context, and document the rationale inline.
- When withholding details for safety, still return a contract-compliant error with a non-sensitive summary, and log the full details to a protected sink.

## Handoff Hygiene
- Summarize exactly what changed and why (file-level scope).
- List validations run and any validations not run.
- Record assumptions, risks, and unresolved blockers explicitly.
- Update the relevant work package tracker/mini package notes when work spans phases.

## When Something Feels Off
- Re-check nearest subsystem `AGENTS.md` and adjacent tests.
- Reuse established patterns from nearby modules before introducing new structures.
- Ask for human clarification when requirements are ambiguous or externally blocked.

---

**Last Updated**: 2026-02-19 (aligned with root `AGENTS.md` map-style onboarding)
