# AGENTS.md
> AI Coding Agent Guide for wepppy

## Authorship
**This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**

## Purpose
- This is the global, high-signal onboarding map for agent work in this repository.
- Keep root guidance concise; place deep subsystem details in nested `AGENTS.md` files and docs.
- Prefer progressive disclosure: read only the docs needed for the task at hand.

## Instruction Discovery
- Instruction precedence is nearest-to-workdir: global defaults -> repo root -> nested directories.
- When a nested `AGENTS.md` exists for files you are editing, treat it as the primary local playbook.
- Use root `AGENTS.md` for repository-wide invariants and routing only.

## Core Directives
- `??` in prompt means provide critical analysis only; do not implement code.
- Ask for human clarification when requirements or debug context are ambiguous.
- Keep docs terse: Codex loads context in bulk and does not compress verbose guidance.
- Do not add fallback wrappers that silently mask missing required dependencies.
- Prefer explicit failures over hidden recovery paths for easier debugging.

## Exception Handling (Required)
- Do not introduce bare `except:` or broad `except Exception` handlers in production paths unless the block is a deliberate boundary.
- Prefer narrow, expected exception types and preserve canonical error contracts when translating errors.
- Never swallow exceptions silently; log with context and either re-raise or return an explicit, contract-compliant error response.
- If a broad catch is unavoidable (for example, boundary cleanup/telemetry), document why in a short comment and keep the protected block minimal.

## ExecPlans (Required)
- For complex features, significant refactors, or multi-hour work, execute against an active ExecPlan.
- Standard location for active ExecPlans is `docs/work-packages/*/prompts/active/`.
- Ad hoc ExecPlans may live under `docs/mini-work-packages/*.md` when explicitly designated by the user.
- Current ad hoc active ExecPlan: `none`.
- Current work-package active ExecPlan: `none`.
- Before authoring or revising an ExecPlan, read `docs/prompt_templates/codex_exec_plans.md`.
- Active plans are living documents: keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current.
- When asked to run a plan end-to-end, proceed milestone by milestone without pausing for extra confirmation unless blocked by an external dependency.
- If multiple active ExecPlans exist, explicitly identify which plan you are executing before edits.
- If the active plan is under `docs/work-packages/*/prompts/active/`, update both the active ExecPlan and `docs/work-packages/*/tracker.md` before handoff.

## Change Scope Discipline (Required)
- Do not add speculative abstractions for unsupported or hypothetical cases.
- Match existing data and API contracts first; call out contract changes before implementation.
- Prefer the smallest fix that resolves the confirmed failing path.
- State assumptions explicitly in change notes before broadening behavior.
- Add regression coverage for the exact failure mode.

## Repository Contracts
- Canonical RQ response and error payload contract: `docs/schemas/rq-response-contract.md`.
- Canonical CSRF contract for browser/session boundaries: `docs/schemas/weppcloud-csrf-contract.md`.
- Update `wepppy/rq/job-dependencies-catalog.md` whenever enqueue sites or dependency edges change in:
  - `wepppy/rq/*.py`
  - `wepppy/microservices/rq_engine/*`
  - rq-initiated route handlers
- Run `wctl check-rq-graph` after queue wiring edits; if drift is reported, regenerate with `python tools/check_rq_dependency_graph.py --write`.
- After queue wiring changes, manually validate against live job trees via `wepppy/rq/job_info.py` or the job dashboard.

## Environment Baseline
- Assume Linux host with Docker, Docker Compose, and `wctl` installed.
- Compose source of truth: `docker/docker-compose.dev.yml`.
- Use `wctl` wrappers for tests, container exec, and local orchestration.
- Canonical run root is `/wc1/runs/`; check it first when debugging run data.

## Validation Entry Points
- Iteration loop: `wctl run-pytest tests/<path or module>`
- Pre-handoff sanity: `wctl run-pytest tests --maxfail=1`
- Frontend changes: `wctl run-npm lint` and `wctl run-npm test`
- Stub/API surface changes: `wctl run-stubtest <module>` and `wctl check-test-stubs`
- RQ queue wiring changes: `wctl check-rq-graph`
- Code quality observability (non-blocking): `python3 tools/code_quality_observability.py --base-ref origin/master`
- Broad exception inventory/enforcement: `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- Docs changes: `wctl doc-lint --path <file>`; preview spelling normalization with `diff -u <file> <(uk2us <file>)`
- Root onboarding size gate: `tools/check_agents_size.sh AGENTS.md`

## Code Quality Observability (Observe-Only)
- Treat complexity/LOC bands as triage telemetry, not merge blockers.
- Prefer changed-file deltas first; use hotspot tables to plan opportunistic cleanup.
- When a touched file worsens materially, capture a brief rationale or follow-up note in review artifacts.

## Documentation Map
- Architecture overview: `ARCHITECTURE.md`
- Human-facing project overview: `readme.md`
- Active initiative board: `PROJECT_TRACKER.md`
- Full work package process: `docs/work-packages/README.md`
- Mini packages: `docs/mini-work-packages/`
- Prompt/template catalog: `docs/prompt_templates/AGENTS.md`
- NoDb facade/collaborator implementation standard: `docs/standards/nodb-facade-collaborator-pattern.md`

## Subsystem Maps (Nearest AGENTS Wins)
- NoDb controllers and module contracts: `wepppy/nodb/AGENTS.md`
- WEPPcloud app/routes/controllers: `wepppy/weppcloud/AGENTS.md`
- Controller JS specifics: `wepppy/weppcloud/controllers_js/AGENTS.md`
- GL dashboard specifics: `wepppy/weppcloud/static/js/gl-dashboard/AGENTS.md`
- WEPP report templates: `wepppy/weppcloud/templates/reports/wepp/AGENTS.md`
- RQ engine microservice: `wepppy/microservices/rq_engine/AGENTS.md`
- Test fixtures, stubs, markers, isolation: `tests/AGENTS.md`
- Docker stack conventions: `docker/AGENTS.md`
- WCTL and tooling wrappers: `wctl/AGENTS.md`
- Status/preflight/cao services: `services/status2/AGENTS.md`, `services/preflight2/AGENTS.md`, `services/cao/AGENTS.md`

## Security Guardrails
- Never commit secrets or tokens. Keep secrets in gitignored files and runtime env.
- Preserve run-scoped access expectations and auth checks when editing endpoints.
- Do not weaken validation, locking, or serialization safeguards in NoDb/RQ flows.

## Root Exclusions
- Do not place long tutorials in this file (NoDb internals, frontend migration guides, route catalogs, or markdown tooling manuals).
- Do not duplicate subsystem instructions already maintained in nested `AGENTS.md` files.
- Do not embed prompt templates in root onboarding text; keep templates under `docs/prompt_templates/`.
- Move growing sections to canonical docs and leave a short pointer here.

## If Blocked
- Check the nearest subsystem `AGENTS.md`, then module README and tests.
- Reuse existing patterns from adjacent code before introducing new abstractions.
- Ask a human when requirements are unclear or an external dependency blocks progress.

## Root Size Policy
- Keep this file within roughly 100-160 lines.
- If a section grows beyond quick onboarding value, move detail to a canonical doc and leave a pointer.
- Prefer stable links over copied prose when updating this file.
- Re-check line count after major edits to avoid onboarding bloat.
