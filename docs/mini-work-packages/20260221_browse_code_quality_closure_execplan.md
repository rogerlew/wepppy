# Browse Microservice Code-Quality Closure

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md` from the repository root.

## Purpose / Big Picture

The browse microservice currently works, but high-complexity browse flow logic required code-quality closure work. The goal is to keep existing browse route behavior and contracts intact while decomposing hotspots into focused helpers and tightening broad exception boundaries. After this change, browse routes and tests should continue to pass, and both `browse.py` and `flow.py` should sit below red-band thresholds.

## Progress

- [x] (2026-02-21 07:06Z) Captured baseline telemetry for `wepppy/microservices/browse/browse.py`: SLOC `1476`, max function length `341`, max CC `84`, broad catches `8`.
- [x] (2026-02-21 07:06Z) Authored this mini-work-package ExecPlan.
- [x] (2026-02-21 07:06Z) Activated this ExecPlan in root `AGENTS.md`.
- [x] (2026-02-21 07:12Z) Refactored browse rendering/tree orchestration into `wepppy/microservices/browse/flow.py`; `browse.py` now delegates via thin wrappers with unchanged signatures.
- [x] (2026-02-21 07:12Z) Reduced broad exception handlers in browse paths (`8 -> 5` in `browse.py`) and documented intentional broad boundaries with short comments.
- [x] (2026-02-21 07:13Z) Ran regression coverage for touched behavior (`test_browse_routes.py`, `test_browse_security.py`, `test_browse_auth_routes.py`) plus `test_files_routes.py` as additional browse-adjacent validation.
- [x] (2026-02-21 07:13Z) Ran required targeted browse suites; `test_browse_dtale.py` is module-skipped by design in this environment (0 collected / 1 skipped).
- [x] (2026-02-21 07:13Z) Ran `python3 tools/code_quality_observability.py --base-ref origin/master` and captured post-change metrics.
- [x] (2026-02-21 07:17Z) Committed and pushed refactor to `master` (`ce21cda83`), then updated this plan to reflect final state.
- [x] (2026-02-21 16:20Z) Assessed `wepppy/microservices/browse/flow.py` quality baseline: SLOC `459`, max function length `339`, max CC `84`, broad catches `1`.
- [x] (2026-02-21 16:20Z) Decomposed `flow.py` into focused helpers for nodir flow, directory rendering, and file rendering while preserving route behavior.
- [x] (2026-02-21 16:20Z) Re-ran browse regression suites after `flow.py` refactor (`test_browse_routes.py`, `test_browse_security.py`, `test_browse_auth_routes.py`, `test_browse_dtale.py`, `test_files_routes.py`).
- [x] (2026-02-21 16:39Z) Addressed review-requested browse contract test gaps by adding route tests for `raw/download/repr`, pagination clamping with `diff/sort/order` preservation, and markdown renderer fallback.
- [x] (2026-02-21 16:39Z) Removed unconditional module-level skip in `test_browse_dtale.py` and repaired stale test patch points to target `browse.dtale.httpx` and flexible `dtale_custom_geojson` module resolution.
- [x] (2026-02-21 16:39Z) Revalidated browse suites after test fixes; D-Tale suite now executes (`2 passed, 3 skipped`) instead of whole-module skip.
- [x] (2026-02-21 16:40Z) Committed and pushed follow-up `flow.py`/tests/plan refactor on `master` (`fe34efe3d`).

## Surprises & Discoveries

- Observation: `browse.py` has two dominant hotspots (`browse_response` at 341 lines and `_browse_tree_helper` at 173 lines), which together account for most red-band pressure.
  Evidence: Local AST scan over `wepppy/microservices/browse/browse.py`.

- Observation: `tests/microservices/test_browse_dtale.py` is intentionally skipped at module import in this environment, which yields pytest exit code `5` (`0 collected, 1 skipped`) even though behavior is expected.
  Evidence: `wctl run-pytest tests/microservices/test_browse_dtale.py` output on 2026-02-21.

- Observation: Moving hotspot logic from `browse.py` to `flow.py` initially transferred red-band function length/complexity to the new file (`339` length / `84` CC), requiring a second decomposition pass.
  Evidence: Local metrics run against `wepppy/microservices/browse/flow.py` on 2026-02-21.

- Observation: Unskipping the D-Tale suite exposed stale test assumptions (patching `browse.httpx`, strict root-module attribute access for `dtale_custom_geojson`) that were previously hidden by unconditional module skip.
  Evidence: `wctl run-pytest tests/microservices/test_browse_dtale.py` failures observed on 2026-02-21 before test fixes.

## Decision Log

- Decision: Execute a behavior-preserving extraction into helper module(s) rather than rewriting route semantics.
  Rationale: Extraction can lower `browse.py` SLOC/length/CC with lower regression risk than logic redesign.
  Date/Author: 2026-02-21 / Codex.

- Decision: Keep this as an ad hoc mini-work-package under `docs/mini-work-packages/` as requested by the user.
  Rationale: The request explicitly designated a mini-work-package ExecPlan path.
  Date/Author: 2026-02-21 / Codex.

- Decision: Introduce `wepppy/microservices/browse/flow.py` with module-context injection (`sys.modules[__name__]`) instead of direct imports from `browse.py`.
  Rationale: This avoids circular imports while preserving existing monkeypatch behavior in tests that patch globals on the `browse` module.
  Date/Author: 2026-02-21 / Codex.

- Decision: Narrow TSV preview parsing failures from broad `Exception` to explicit pandas/text decode/value errors in extracted flow logic.
  Rationale: Preserves fallback behavior while reducing broad catch usage in active browse paths.
  Date/Author: 2026-02-21 / Codex.

- Decision: Refactor `flow.py` in-place into many helper functions instead of creating additional modules.
  Rationale: Keeps browse flow discoverable in one file while reducing per-function complexity and limiting import-surface churn.
  Date/Author: 2026-02-21 / Codex.

- Decision: Keep D-Tale tests active but environment-tolerant (targeted `skip` on unavailable optional runtime paths) rather than module-level unconditional skip.
  Rationale: Restores meaningful execution and regression value in CI-compatible environments while avoiding false failures when optional dependencies are absent.
  Date/Author: 2026-02-21 / Codex.

## Outcomes & Retrospective

Initial refactor achieved the quality closure target for `browse.py` while preserving route behavior in required suites. `browse.py` now delegates large flow functions to `flow.py`, reducing hotspot pressure in the entrypoint module: SLOC `1476 -> 1086`, max function length `341 -> 93`, max CC `84 -> 21`, broad catches `8 -> 5`.

A follow-up decomposition pass closed quality risk in `flow.py`: SLOC `459 -> 775`, max function length `339 -> 86`, max CC `84 -> 14`, broad catches `1 -> 1` (intentional markdown rendering boundary). Additional browse test coverage was added for query/content-type/pagination/markdown fallback branches, and D-Tale tests now run instead of a blanket module skip.

All implementation, validation, and push steps are complete.

## Context and Orientation

`wepppy/microservices/browse/browse.py` defines the Starlette browse app, request adapters, browse tree resolution, browse rendering, auth-aware route handlers, and exception handlers. The largest behavior hubs are:

- `_browse_tree_helper` (path validation and nodir/file/dir dispatch).
- `browse_response` (directory rendering, pagination, preview/download/raw behavior, and file-type-specific rendering).

The test suites most directly covering these paths are:

- `tests/microservices/test_browse_routes.py`
- `tests/microservices/test_browse_security.py`
- `tests/microservices/test_browse_auth_routes.py`
- `tests/microservices/test_browse_dtale.py`

The observability script `tools/code_quality_observability.py` reports red-band thresholds:

- `python_file_sloc` red at `1200`
- `python_function_len` red at `150`
- `python_cc` red at `30`

## Plan of Work

Milestone 1 will isolate browse rendering and browse tree orchestration into new helper module(s) inside `wepppy/microservices/browse/`, keeping signatures and response contracts stable from callers in `browse.py`. The extracted code will continue to call existing helpers (`html_dir_list`, nodir adapters, auth/path guards, template rendering) so route behavior remains unchanged.

Milestone 2 will narrow broad exception handlers where practical in browse execution paths, particularly around format conversions and preview rendering. Where a broad catch remains a deliberate boundary (for example third-party rendering failures), the catch will be minimal and include a short comment explaining why the boundary is intentional.

Milestone 3 will update or add regression tests for the touched behavior and run the required browse-targeted suites. The final step will rerun observability and ensure `browse.py` itself is below red-band thresholds, then commit and push the result.

## Concrete Steps

From `/workdir/wepppy`:

1. Inspect `browse.py` hotspots and baseline metrics with local scripts and `python3 tools/code_quality_observability.py --base-ref origin/master`.
2. Extract browse tree and browse response orchestration into focused helper module(s), then wire `browse.py` to call those helpers.
3. Tighten broad exception handling in touched browse paths and add short boundary comments where unavoidable.
4. Run targeted tests:
   - `wctl run-pytest tests/microservices/test_browse_routes.py`
   - `wctl run-pytest tests/microservices/test_browse_security.py`
   - `wctl run-pytest tests/microservices/test_browse_auth_routes.py`
   - `wctl run-pytest tests/microservices/test_browse_dtale.py`
5. Run `python3 tools/code_quality_observability.py --base-ref origin/master` and record before/after metrics for `browse.py`.
6. Commit with a focused message and push `master`.

## Validation and Acceptance

Acceptance is met when:

- Browse API behavior remains unchanged for the covered route surfaces (verified by passing targeted browse tests).
- `wepppy/microservices/browse/browse.py` metrics satisfy:
  - `python_file_sloc < 1200`
  - `python_function_len < 150`
  - `python_cc < 30`
- Broad catches in browse execution paths are reduced and any unavoidable broad boundary has a short justification comment.
- `wepppy/microservices/browse/flow.py` metrics satisfy:
  - `python_file_sloc < 1200`
  - `python_function_len < 150`
  - `python_cc < 30`

## Idempotence and Recovery

Edits are code-only and idempotent. If a test fails, revert only the failing extraction chunk and rerun the focused test before continuing. Re-running observability is safe and overwrites `code-quality-report.json` and `code-quality-summary.md`.

## Artifacts and Notes

Baseline snapshot:

    browse.py SLOC: 1476
    browse.py max function length: 341
    browse.py max CC: 84
    browse.py broad catches (bare except + except Exception): 8

Required final artifact updates in this plan before handoff:

- Final before/after metrics table for `browse.py`.
- Test command transcript summary and outcomes.
- Residual risks/follow-ups.

Final metrics table:

| Metric | Before | After |
| --- | ---: | ---: |
| SLOC | 1476 | 1086 |
| Max function length | 341 | 93 |
| Max cyclomatic complexity | 84 | 21 |
| Broad catches | 8 | 5 |

Validation summary:

- `wctl run-pytest tests/microservices/test_browse_routes.py` -> passed (`7 passed`).
- `wctl run-pytest tests/microservices/test_browse_security.py` -> passed (`13 passed`).
- `wctl run-pytest tests/microservices/test_browse_auth_routes.py` -> passed (`82 passed`).
- `wctl run-pytest tests/microservices/test_browse_dtale.py` -> passed/skip mix (`2 passed, 3 skipped`).
- `wctl run-pytest tests/microservices/test_files_routes.py` -> passed (`117 passed`).

Flow follow-up metrics table:

| Metric | Before | After |
| --- | ---: | ---: |
| SLOC | 459 | 775 |
| Max function length | 339 | 86 |
| Max cyclomatic complexity | 84 | 14 |
| Broad catches | 1 | 1 |

## Interfaces and Dependencies

The route entrypoints in `wepppy/microservices/browse/browse.py` must retain their current signatures and behavior:

- `browse_root`, `browse_subpath`
- `browse_culvert_root`, `browse_culvert_subpath`
- `browse_batch_root`, `browse_batch_subpath`
- `create_app`

Any new helper module must expose stable call points consumed by `browse.py` and preserve existing response objects (`HTMLResponse`, `JSONResponse`, `RedirectResponse`, `Response`, tuple-style `(body, status)` where currently used).

Update log:

- 2026-02-21: Initial plan authored and activated to execute browse code-quality closure requested by user.
- 2026-02-21: Updated after implementation/testing with extraction details, validation outcomes, and post-change metrics.
- 2026-02-21: Marked commit/push completion and captured final metrics/validation summary.
- 2026-02-21: Added `flow.py` quality assessment/refactor progress, outcomes, and remaining commit step.
