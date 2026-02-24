# Residual Broad-Exception Closure Finish Line ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` are updated as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package closes, allowlist-aware unresolved broad-exception findings are zero for the Debt Project #1 residual target files (`wepppy/query_engine/app/mcp/router.py`, `wepppy/weppcloud/app.py`) while preserving existing contracts, correlation-id behavior, and runtime responses.

## Progress

- [x] (2026-02-23 23:51Z) Read required planning template and applicable AGENTS guidance (`AGENTS.md`, `wepppy/weppcloud/AGENTS.md`, `tests/AGENTS.md`).
- [x] (2026-02-23 23:51Z) Created package scaffold (`package.md`, `tracker.md`, active ExecPlan path, `artifacts/`).
- [x] (2026-02-23 23:55Z) Executed baseline artifact command: `python3 tools/check_broad_exceptions.py --json > artifacts/baseline_broad_exceptions.json`.
- [x] (2026-02-24 00:05Z) Completed baseline `explorer` inventory and published `artifacts/baseline_scope_inventory.md`.
- [x] (2026-02-24 00:20Z) Query-engine worker pass completed:
  - narrowed non-boundary broad catches in catalog parse paths,
  - retained endpoint true-boundary broad catches,
  - added focused MCP regression tests for malformed catalog and runtime error paths.
- [x] (2026-02-24 00:25Z) Weppcloud worker pass completed:
  - validated `Run.meta` broad catch as true boundary,
  - synced boundary allowlist line location.
- [x] (2026-02-24 00:35Z) Reviewer pass completed and findings dispositioned.
- [x] (2026-02-24 00:40Z) Executed postfix artifact command: `python3 tools/check_broad_exceptions.py --json > artifacts/postfix_broad_exceptions.json`.
- [x] (2026-02-24 00:55Z) All required validation commands passed in this session.
- [x] (2026-02-24 01:00Z) Synchronized closeout docs (`tracker.md`, `PROJECT_TRACKER.md`, this ExecPlan).

## Surprises & Discoveries

- Observation: `test_guardian` sub-agent could not run `wctl` pytest commands due Docker socket restrictions, while the main session could run them successfully.
  Evidence: sub-agent reported `/var/run/docker.sock` permission error; direct session runs passed (`36 passed`, `18 passed`, `2107 passed, 29 skipped`).
- Observation: In-scope unresolved findings were residual line-drift plus non-boundary catches.
  Evidence: baseline in-scope findings were exactly 8 (7 in `router.py`, 1 in `app.py`); postfix in-scope findings are 0.
- Observation: Changed-file enforcement scanned only `router.py` in python scope because `app.py` behavior ended unchanged.
  Evidence: `Changed Python files scanned: 1`; `router.py (base=7 current=0 delta=-7)`.

## Decision Log

- Decision: Execute sub-agent orchestration in the requested order (`explorer` -> workers -> `reviewer` -> `test_guardian`).
  Rationale: Required by package contract and keeps role responsibilities explicit.
  Date/Author: 2026-02-23 / Codex
- Decision: Narrow only non-boundary catches in `router.py` and keep true boundary catches broad.
  Rationale: Preserves MCP error-envelope compatibility on unexpected runtime failures while reducing unresolved debt in parse-specific paths.
  Date/Author: 2026-02-24 / Codex
- Decision: Keep `weppcloud/app.py::Run.meta` broad catch as a true boundary and synchronize allowlist location.
  Rationale: Preserves existing metadata fallback/runtime behavior and avoids introducing hidden behavior changes in callers.
  Date/Author: 2026-02-24 / Codex

## Outcomes & Retrospective

Package completed end-to-end with required orchestration, artifacts, and gates. In-scope unresolved broad-exception findings closed from `8` to `0` with minimal scope change: non-boundary catches in `router.py` were narrowed, true boundaries were retained with line-accurate allowlist synchronization, and focused regression coverage was added for malformed catalog paths. Required targeted and full-suite pytest gates passed.

## Context and Orientation

The broad-exception scanner (`tools/check_broad_exceptions.py`) flags `except Exception`, `except BaseException`, and bare `except:` handlers unless suppressed by policy mechanisms. This package closes residual findings in two files only.

- `wepppy/query_engine/app/mcp/router.py`: MCP API handlers for run/catalog/query endpoints.
- `wepppy/weppcloud/app.py`: Flask app models and run metadata helpers.

Focused tests for touched behavior:

- `tests/query_engine/test_mcp_router.py`
- `tests/query_engine/test_server_routes.py`
- `tests/weppcloud/test_config_logging.py`
- `tests/test_observability_correlation.py`

## Plan of Work

Milestone 0 captures baseline scanner output and inventory. Milestone 1 closes query-engine scope by narrowing non-boundary catches and preserving boundary contracts, with focused tests. Milestone 2 closes weppcloud scope using boundary classification and allowlist sync. Milestone 3 runs independent risk review. Milestone 4 executes required gates and synchronizes artifacts/docs.

## Concrete Steps

Run from `/workdir/wepppy`:

    python3 tools/check_broad_exceptions.py --json > docs/work-packages/20260224_residual_broad_exception_finishline/artifacts/baseline_broad_exceptions.json

    python3 tools/check_broad_exceptions.py --json > docs/work-packages/20260224_residual_broad_exception_finishline/artifacts/postfix_broad_exceptions.json

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

    wctl run-pytest tests/query_engine/test_mcp_router.py tests/query_engine/test_server_routes.py

    wctl run-pytest tests/weppcloud/test_config_logging.py tests/test_observability_correlation.py

    wctl run-pytest tests --maxfail=1

## Validation and Acceptance

Acceptance requires zero unresolved allowlist-aware findings for the two in-scope files, passing changed-file broad-exception enforcement, passing required targeted/full tests, and no unresolved contract-risk findings from reviewer pass.

## Idempotence and Recovery

Scanner and pytest commands are idempotent. If future line drift reopens unresolved findings, re-run scanner commands, refresh line-accurate allowlist entries for true boundaries, and re-run required gates.

## Artifacts and Notes

Required artifacts for this package:

- `artifacts/baseline_broad_exceptions.json`
- `artifacts/postfix_broad_exceptions.json`
- `artifacts/baseline_scope_inventory.md`
- `artifacts/scope_resolution_matrix.md`
- `artifacts/final_validation_summary.md`

## Interfaces and Dependencies

- Broad exception scanner: `tools/check_broad_exceptions.py`
- Query-engine MCP handlers: `wepppy/query_engine/app/mcp/router.py`
- WEPPcloud app model helpers: `wepppy/weppcloud/app.py`
- Test runner wrapper: `wctl run-pytest`

Revision note (2026-02-24 01:00Z): Closed plan milestones, updated living sections with final decisions/outcomes, and synchronized validation/artifact results.
