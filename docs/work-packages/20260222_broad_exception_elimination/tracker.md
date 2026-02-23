# Tracker - Broad Exception Elimination and Boundary Contract Hardening

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-02-22  
**Current phase**: Milestone 8 complete (deferred hotspot addendum closed)  
**Last updated**: 2026-02-23  
**Next milestone**: none (package closed)

## Task Board

### Ready / Backlog

- [ ] None.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Created work-package scaffold (`package.md`, `tracker.md`, prompts, notes/artifacts directories) (2026-02-22).
- [x] Authored active ExecPlan at `prompts/active/broad_exception_elimination_execplan.md` (2026-02-22).
- [x] Authored end-to-end kickoff prompt at `prompts/active/run_broad_exception_elimination_e2e.prompt.md` (2026-02-22).
- [x] Updated root `AGENTS.md` with the active work-package ExecPlan pointer (2026-02-22).
- [x] Added in-progress package entry to `PROJECT_TRACKER.md` (2026-02-22).
- [x] Ran doc lint for package docs plus root tracker files (2026-02-22).
- [x] Milestone 0: baseline artifact + report-mode checker + boundary allowlist template + tests (2026-02-22).
- [x] Milestone 1: characterization tests for rq-engine, NoDb, WEPPcloud, and query-engine boundary behavior (2026-02-22).
- [x] Milestone 2: rq-engine route cleanup batch A with targeted catch narrowing and regression tests (2026-02-22).
- [x] Milestone 3: RQ worker cleanup batch A with targeted catch narrowing and regression tests (2026-02-23).
- [x] Milestone 4: NoDb cleanup batch A in `nodb/base.py` with lock-safe narrowing and regression tests (2026-02-23).
- [x] Milestone 5: WEPPcloud route bare-catch normalization batch in `user.py` + `wepp_bp.py` with route regression tests (2026-02-23).
- [x] Milestone 6: query-engine/services tail cleanup batch with targeted catch narrowing and regression tests (2026-02-23).
- [x] Milestone 7a: broad-catch checker changed-file enforcement mode + unit tests (2026-02-23).
- [x] Milestone 7b: closeout artifacts (`boundary_allowlist.md`, `final_validation_summary.md`), ExecPlan/tracker sync, and required full-suite gate (2026-02-23).
- [x] Milestone 8: deferred swallow-style hotspot closure in `user.py` and `inbox_service.py` with mandatory subagent loop, regression tests, allowlist promotion, and full-suite gate (2026-02-23).
- [x] Updated global trackers for closure (`PROJECT_TRACKER.md` moved package to Done; `AGENTS.md` active plan pointer set to `none`) (2026-02-23).

## Timeline

- **2026-02-22** - Package created and scoped.
- **2026-02-22** - Active ExecPlan installed and kickoff prompt authored.
- **2026-02-22** - Root and project trackers updated for package discoverability.
- **2026-02-23** - Milestones 0-7 completed, closeout artifacts finalized, and full-suite validation gate passed.
- **2026-02-23** - Milestone 8 addendum completed; deferred swallow hotspots cleared and package re-closed.

## Decisions

### 2026-02-22: Use phased cleanup instead of bulk codemod
**Context**: Production broad catches are spread across high-risk runtime surfaces.

**Options considered**:
1. Repository-wide codemod first, then fix regressions.
2. Phased cleanup by subsystem with characterization tests.

**Decision**: Execute phased cleanup with tests-first for high-risk boundaries.

**Impact**: Lower regression risk and clearer attribution for failures.

---

### 2026-02-22: Keep true boundary catches allowed with explicit rationale
**Context**: Some boundary catches are necessary at framework/external edges.

**Options considered**:
1. Ban all broad catches unconditionally.
2. Allow only documented boundary catches with explicit logging and contract-safe output.

**Decision**: Keep documented boundary catches only; eliminate silent broad swallow paths.

**Impact**: Preserves operational resilience while removing hidden failure masking.

---

### 2026-02-22: Defer broader rq-engine contract harmonization beyond Milestone 2
**Context**: Reviewer surfaced pre-existing rq-engine contract debt (enqueue 202 semantics, polling auth-mode policy, legacy auth-status mappings) outside this milestone's narrow catch cleanup scope.

**Options considered**:
1. Expand Milestone 2 to include broad contract shifts.
2. Keep Milestone 2 minimal and defer broader contract alignment to later milestone batches.

**Decision**: Defer broader contract harmonization; close Milestone 2 on high-confidence catch narrowing plus regression coverage.

**Impact**: Preserves milestone scope discipline and limits regression blast radius.

---

### 2026-02-23: Keep optional Discord imports fail-fast on non-import errors
**Context**: RQ worker modules (`batch_rq.py`, `omni_rq.py`) used broad module-import catches for an optional integration.

**Options considered**:
1. Keep broad import catches and silently disable integration on any import-time error.
2. Narrow import catches to `ImportError` and allow unexpected import-time failures to surface.

**Decision**: Narrow to `ImportError`.

**Impact**: Missing optional dependency still degrades gracefully, while runtime/syntax/config import failures are no longer silently masked.

---

### 2026-02-23: Keep explicit broad side-effect boundaries in `NoDbBase.dump` for lock safety
**Context**: Milestone 4 reviewer flagged that over-narrowing Redis side-effect catches in `dump()` could raise during `dump_and_unlock` and risk lock-retention regressions.

**Options considered**:
1. Narrow `dump()` side-effect catches aggressively to Redis-specific exception classes.
2. Keep explicit broad boundary catches for side-effect mirrors (cache + last_modified) and document rationale.

**Decision**: Keep explicit broad side-effect boundaries in this batch; defer deeper lock-flow refactor.

**Impact**: Preserves lock-release safety while still reducing broad catches in lower-risk NoDb helper paths.

---

### 2026-02-23: Normalize WEPPcloud bare catches before deep route taxonomy narrowing
**Context**: WEPPcloud route files had multiple bare `except:` blocks in auth-adjacent and reporting handlers.

**Options considered**:
1. Defer until full per-route exception taxonomy narrowing is ready.
2. First normalize bare catches to explicit `except Exception`, then continue with deeper narrowing later.

**Decision**: Normalize bare catches first.

**Impact**: Removes `BaseException` swallowing risk while preserving current route contracts and fail-closed auth/session behavior.

---

### 2026-02-23: Narrow query payload validation boundary by explicit validation error types
**Context**: `run_query_endpoint` used a broad catch when constructing `QueryRequest` for payload validation responses.

**Options considered**:
1. Keep broad catch for all exceptions as 422 validation errors.
2. Narrow to expected validation exception families while preserving 422 envelope behavior for characterized bad payloads.

**Decision**: Narrow to `(TypeError, ValueError)` and add explicit regression coverage.

**Impact**: Reduces incidental broad exception usage while retaining current invalid-payload contract behavior in tested paths.

---

### 2026-02-23: Enforce changed-file broad-catch policy on per-file increases
**Context**: Milestone 7 enforcement mode initially described "net-new" behavior that could be interpreted as global-net-only.

**Options considered**:
1. Fail only on positive global net delta across changed files.
2. Fail when any changed file has a positive broad-catch delta.

**Decision**: Keep per-file increase gating and align wording/help text to that behavior.

**Impact**: New broad catches in one changed file are not masked by reductions in another file.

---

### 2026-02-23: Extend checker AST support to `TryStar`
**Context**: Reviewer found `except* Exception` handlers were not scanned because the checker walked only `ast.Try`.

**Options considered**:
1. Keep current implementation and defer `except*` handling.
2. Add `ast.TryStar` traversal with regression tests.

**Decision**: Add `ast.TryStar` support immediately in Milestone 7 closeout.

**Impact**: Closes an enforcement/reporting blind spot for Python 3.11+ exception-group handlers.

---

### 2026-02-23: Resolve deferred hotspots with narrow-or-boundary split
**Context**: Milestone 7 closeout left six deferred swallow-style hotspots (`user.py`, `inbox_service.py`) documented in `artifacts/boundary_allowlist.md`.

**Options considered**:
1. Open a separate follow-up package and defer further.
2. Execute a focused Milestone 8 addendum with full subagent loop and regression gates.

**Decision**: Execute Milestone 8 immediately and close deferred hotspots in-place.

**Impact**: Removed/narrowed four control-flow broad catches, promoted two true WEPPcloud per-run boundaries to canonical allowlist entries, and revalidated with full-suite gate.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Contract regressions in rq-engine error payloads/status codes | High | Medium | Characterization tests before narrowing; preserve canonical helpers | Mitigated |
| NoDb lock/persistence semantics regress during catch narrowing | High | Medium | Lock/persistence-focused tests and phased scope | Mitigated |
| Worker jobs mistakenly change success/failure outcomes | High | Medium | Preserve publish+re-raise behavior and add worker regression checks | Mitigated |
| Cleanup stalls due to scope breadth | Medium | Medium | Milestone slicing + changed-file guard to prevent new debt | Closed |

## Verification Checklist

### Code Quality
- [x] Targeted subsystem suites pass for each milestone.
- [x] `wctl run-pytest tests --maxfail=1` passes before closure.
- [x] `wctl check-rq-graph` run when queue wiring changes. (Not required in this package; no queue wiring edits.)

### Documentation
- [x] ExecPlan living sections updated at each milestone boundary.
- [x] `tracker.md` updated with decisions/progress after each milestone.
- [x] `PROJECT_TRACKER.md` status updated as package progresses.

### Testing
- [x] Characterization tests added for high-risk boundary translations.
- [x] New tests assert canonical error envelope on route boundaries.
- [x] NoDb tests cover lock and persistence error paths touched by cleanup.

### Deployment / Runtime Safety
- [x] Boundary catches that remain have short rationale comments.
- [x] No silent swallow behavior remains in touched production paths.
- [x] Residual approved boundaries cataloged with owner + revisit trigger.

## Progress Notes

### 2026-02-22: Package bootstrap and kickoff preparation
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold under `docs/work-packages/20260222_broad_exception_elimination/`.
- Authored package brief, active ExecPlan, and kickoff prompt.
- Registered package/plan visibility in root trackers.

**Blockers encountered**:
- None.

**Next steps**:
- Execute Milestone 0 from the active ExecPlan.
- Produce baseline artifact snapshot in `artifacts/`.

**Test results**:
- `wctl doc-lint --path AGENTS.md --path PROJECT_TRACKER.md --path docs/work-packages/20260222_broad_exception_elimination/package.md --path docs/work-packages/20260222_broad_exception_elimination/tracker.md --path docs/work-packages/20260222_broad_exception_elimination/prompts/active/broad_exception_elimination_execplan.md --path docs/work-packages/20260222_broad_exception_elimination/prompts/active/run_broad_exception_elimination_e2e.prompt.md` -> pass (`6 files validated, 0 errors, 0 warnings`).

### 2026-02-22: Milestone 0 baseline artifacts and checker bootstrap
**Agent/Contributor**: Codex

**Work completed**:
- Added AST-based broad-exception report tool under `tools/` with inline suppressions (`# noqa: BLE001`, `# broad-except:`).
- Added tool tests under `tests/tools/`.
- Added baseline and allowlist artifacts under `artifacts/`.

**Blockers encountered**:
- Docker daemon access is not available in this environment, so `wctl run-pytest ...` could not be executed here.

**Test results**:
- `python3 -m pytest -q tests/tools/test_check_broad_exceptions.py` -> pass (`3 passed`).

### 2026-02-22: Milestone 1 characterization net (tests-first)
**Agent/Contributor**: Codex

**Work completed**:
- Added rq-engine exception-boundary characterization tests in `tests/microservices/test_rq_engine_jobinfo.py`.
- Added NoDb lock/persistence side-effect characterization test in `tests/nodb/test_base_unit.py`.
- Added WEPPcloud route/auth-adjacent exception-path characterization tests in `tests/weppcloud/routes/test_wepp_bp.py` and `tests/weppcloud/routes/test_user_profile_token.py`.
- Added query-engine MCP `context_unavailable` failure-envelope characterization test in `tests/query_engine/test_mcp_router.py`.
- Added milestone artifacts: `artifacts/milestone_0_catch_diff.md`, `artifacts/milestone_1_catch_diff.md`.

**Blockers encountered**:
- `wctl run-pytest ...` is blocked in this environment because Docker socket access is unavailable.
- Local pytest environment is missing optional runtime dependencies (`fastapi`, `flask`, `starlette`, `jsonpickle`), so targeted characterization suites cannot be fully executed here.

**Test results**:
- `python3 -m pytest tests/tools/test_check_broad_exceptions.py --maxfail=1` -> pass (`3 passed`).
- `python3 -m py_compile tools/check_broad_exceptions.py tests/tools/test_check_broad_exceptions.py tests/microservices/test_rq_engine_jobinfo.py tests/nodb/test_base_unit.py tests/weppcloud/routes/test_wepp_bp.py tests/weppcloud/routes/test_user_profile_token.py tests/query_engine/test_mcp_router.py` -> pass.
- Targeted rq-engine/NoDb/WEPPcloud/query-engine pytest modules -> skipped/error due missing optional dependencies (details captured in `artifacts/milestone_1_catch_diff.md`).

### 2026-02-22: Milestone 2 rq-engine route catch narrowing (pass 1)
**Agent/Contributor**: Codex

**Work completed**:
- Narrowed rq-engine catches in `wepppy/microservices/rq_engine/fork_archive_routes.py`, `wepppy/microservices/rq_engine/job_routes.py`, and `wepppy/microservices/rq_engine/project_routes.py`.
- Added regression test for `fork_archive_routes` ensuring `get_wd` runtime failures on `target_runid` return 500 (not 400).

**Blockers encountered**:
- `wctl run-pytest ...` remains blocked in this environment because Docker socket access is unavailable.
- Local pytest environment is missing `fastapi`, so rq-engine microservice tests cannot execute here.

**Test results**:
- `python3 -m compileall -q wepppy/microservices/rq_engine/fork_archive_routes.py wepppy/microservices/rq_engine/job_routes.py wepppy/microservices/rq_engine/project_routes.py tests/microservices/test_rq_engine_fork_archive_routes.py` -> pass.

### 2026-02-22: Milestone 2 rq-engine route catch narrowing (closure)
**Agent/Contributor**: Codex

**Work completed**:
- Extended Milestone 2 narrowing to `wepppy/microservices/rq_engine/bootstrap_routes.py` and `wepppy/microservices/rq_engine/omni_routes.py` by constraining JSON-fallback catches to malformed JSON/encoding failures.
- Added regression tests for invalid-JSON fallback in bootstrap checkout and omni run/contrast routes.
- Added explicit non-string `target_runid` validation guard in `fork_archive_routes.py` with regression coverage.
- Captured Milestone 2 before/after counts and command transcript in `artifacts/milestone_2_catch_diff.md`.

**Blockers encountered**:
- `wctl run-pytest ...` remains blocked in this environment due unavailable Docker socket access.
- Host Python runtime still lacks optional deps (`fastapi`), preventing direct execution of microservice route suites outside `wctl`.

**Test results**:
- `python3 -m py_compile wepppy/microservices/rq_engine/bootstrap_routes.py wepppy/microservices/rq_engine/omni_routes.py wepppy/microservices/rq_engine/job_routes.py wepppy/microservices/rq_engine/fork_archive_routes.py wepppy/microservices/rq_engine/project_routes.py tests/microservices/test_rq_engine_bootstrap_routes.py tests/microservices/test_rq_engine_omni_routes.py tests/microservices/test_rq_engine_fork_archive_routes.py` -> pass.
- `PYTHONPATH=/workdir/wepppy python3 -m pytest -rs tests/microservices/test_rq_engine_fork_archive_routes.py tests/microservices/test_rq_engine_omni_routes.py tests/microservices/test_rq_engine_bootstrap_routes.py tests/microservices/test_rq_engine_jobinfo.py tests/microservices/test_rq_engine_project_routes.py` -> skipped (`fastapi` missing).

### 2026-02-23: Milestone 3 RQ worker cleanup batch A
**Agent/Contributor**: Codex

**Work completed**:
- Narrowed optional Discord import catches from broad `Exception` to `ImportError` in `wepppy/rq/batch_rq.py` and `wepppy/rq/omni_rq.py`.
- Narrowed best-effort prep bookkeeping catches in `wepppy/rq/project_rq.py::set_run_readonly_rq` to explicit operational error classes (`redis`/I/O/serialization/value/type).
- Integrated reviewer finding by moving prep bookkeeping into the main exception boundary so unexpected prep failures still publish `EXCEPTION` telemetry.
- Added focused worker regression coverage in `tests/rq/test_project_rq_readonly.py`.
- Captured Milestone 3 artifact at `artifacts/milestone_3_catch_diff.md` with count deltas and validation commands.

**Blockers encountered**:
- None for canonical `wctl` validation during this milestone.

**Test results**:
- `wctl run-pytest tests/rq/test_exception_logging.py tests/rq/test_wepp_rq_stage_post.py --maxfail=1` -> pass (`6 passed`).
- `wctl run-pytest tests/rq/test_project_rq_readonly.py --maxfail=1` -> pass (`3 passed`).
- `python3 -m py_compile wepppy/rq/batch_rq.py wepppy/rq/omni_rq.py wepppy/rq/project_rq.py tests/rq/test_project_rq_readonly.py` -> pass.

### 2026-02-23: Milestone 4 NoDb cleanup batch A
**Agent/Contributor**: Codex

**Work completed**:
- Narrowed broad catches in `wepppy/nodb/base.py` for Redis log-level get/set helpers and cleanup bare-except paths.
- Tightened log-level retrieval to support both symbolic and numeric persisted values with validation.
- Added/expanded NoDb regression coverage in `tests/nodb/test_base_misc.py` and `tests/nodb/test_base_unit.py` for narrowed catch paths and lock-safety side-effect behavior.
- Captured milestone artifact at `artifacts/milestone_4_catch_diff.md`.

**Blockers encountered**:
- First `test_base_misc` run failed due a test monkeypatch overriding `logging.getLogger` without no-arg compatibility; fixed and rerun green.

**Test results**:
- `wctl run-pytest tests/nodb/test_locked.py tests/nodb/test_base_unit.py tests/nodb/test_lock_race_conditions.py --maxfail=1` -> pass (`34 passed`).
- `wctl run-pytest tests/nodb/test_base_misc.py --maxfail=1` -> pass (`29 passed`) after test shim fix.
- `python3 -m py_compile wepppy/nodb/base.py tests/nodb/test_base_misc.py tests/nodb/test_base_unit.py` -> pass.

### 2026-02-23: Milestone 5 WEPPcloud route cleanup batch A
**Agent/Contributor**: Codex

**Work completed**:
- Replaced bare `except:` with explicit `except Exception:` in targeted route boundaries in `wepppy/weppcloud/routes/user.py` and `wepppy/weppcloud/routes/nodb_api/wepp_bp.py`.
- Added route regression tests in `tests/weppcloud/routes/test_wepp_bp.py` for report template and channel/subcatchment summary exception-path boundaries.
- Captured milestone artifact at `artifacts/milestone_5_catch_diff.md`.

**Blockers encountered**:
- None for canonical `wctl` route validation in this milestone.

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_exception_logging_routes.py tests/weppcloud/routes/test_wepp_bp.py --maxfail=1` -> pass (`14 passed`).
- `wctl run-pytest tests/weppcloud/routes/test_user_profile_token.py tests/weppcloud/routes/test_user_runs_admin_scope.py --maxfail=1` -> pass (`12 passed`).
- `python3 -m py_compile wepppy/weppcloud/routes/user.py wepppy/weppcloud/routes/nodb_api/wepp_bp.py tests/weppcloud/routes/test_wepp_bp.py` -> pass.

### 2026-02-23: Milestone 6 query-engine/services tail cleanup batch
**Agent/Contributor**: Codex

**Work completed**:
- Narrowed query-engine payload validation catch in `wepppy/query_engine/app/server.py` from broad `Exception` to explicit validation error families.
- Narrowed CAO inbox log-tail swallow boundary in `services/cao/src/cli_agent_orchestrator/services/inbox_service.py` to expected subprocess/filesystem exceptions.
- Added regression tests in `tests/query_engine/test_server_routes.py` and `services/cao/test/services/test_inbox_service.py`.
- Captured milestone artifact at `artifacts/milestone_6_catch_diff.md`.

**Blockers encountered**:
- None for canonical `wctl` validation commands in this milestone.

**Test results**:
- `wctl run-pytest tests/query_engine/test_mcp_router.py tests/query_engine/test_server_routes.py --maxfail=1` -> pass (`26 passed`).
- `wctl run-pytest services/cao/test/services/test_inbox_service.py --maxfail=1` -> pass (`4 passed`).
- `python3 -m py_compile wepppy/query_engine/app/server.py services/cao/src/cli_agent_orchestrator/services/inbox_service.py tests/query_engine/test_server_routes.py services/cao/test/services/test_inbox_service.py` -> pass.

### 2026-02-23: Milestone 7 guard closeout + package finalization
**Agent/Contributor**: Codex

**Work completed**:
- Finalized changed-file enforcement in `tools/check_broad_exceptions.py` with `TryStar` support and clarified per-file increase policy messaging.
- Expanded checker tests in `tests/tools/test_check_broad_exceptions.py` for `except* Exception` detection and zero-delta kind-swap behavior.
- Populated approved boundary catalog in `artifacts/boundary_allowlist.md`.
- Added final package validation/metrics artifact `artifacts/final_validation_summary.md`.
- Synced ExecPlan/tracker living sections for package completion.
- Completed required subagent loop (`explorer` -> `worker` -> `reviewer` -> `test_guardian`) and integrated reviewer/test findings before final gates.

**Blockers encountered**:
- None for canonical validation from the integrator session.

**Test results**:
- `python3 -m pytest tests/tools/test_check_broad_exceptions.py --maxfail=1` -> pass (`9 passed`).
- `wctl run-pytest tests/tools/test_check_broad_exceptions.py --maxfail=1` -> pass (`9 passed`).
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> pass (`Result: PASS`, net delta `-17`).
- `wctl run-pytest tests --maxfail=1` -> pass (`2048 passed, 29 skipped`).

### 2026-02-23: Milestone 8 deferred swallow hotspot closure
**Agent/Contributor**: Codex

**Work completed**:
- Completed required subagent loop (`explorer` -> domain refactorers -> `reviewer` -> `test_guardian` -> integrator) for deferred hotspots in `wepppy/weppcloud/routes/user.py` and `services/cao/src/cli_agent_orchestrator/services/inbox_service.py`.
- Narrowed/remediated control-flow swallow catches (`_claim_names`, `_has_idle_pattern`, provider import detection) with explicit logging and new focused tests.
- Kept per-run WEPPcloud list boundaries broad-but-explicit with boundary comments/logging and route-level regression tests; promoted these to canonical allowlist (`BEA-20260223-010`, `BEA-20260223-011`).
- Added milestone artifact `artifacts/milestone_8_catch_diff.md` and refreshed package artifacts/plan/tracker.

**Blockers encountered**:
- None in integrator validation run (canonical `wctl` commands were available in this environment).

**Test results**:
- `wctl run-pytest services/cao/test/services/test_inbox_service.py --maxfail=1` -> pass (`10 passed`).
- `wctl run-pytest tests/weppcloud/routes/test_user_profile_token.py tests/weppcloud/routes/test_user_runs_admin_scope.py --maxfail=1` -> pass (`17 passed`).
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> pass (`Result: PASS`, net delta `-28`).
- `wctl run-pytest tests --maxfail=1` -> pass (`2057 passed, 29 skipped`).

## Watch List

- **rq-engine error envelope drift**: monitor `error.details` and status-code parity.
- **NoDb lock semantics**: monitor for any lock ownership or stale-write regressions.
- **WEPPcloud auth/session boundaries**: ensure fail-closed behavior is preserved.

## Communication Log

### 2026-02-22: Kickoff package requested
**Participants**: User, Codex  
**Question/Topic**: Create work-package, install active ExecPlan in `AGENTS.md`, provide end-to-end kickoff prompt.  
**Outcome**: Work package scaffolded, active plan registered, kickoff prompt authored.
