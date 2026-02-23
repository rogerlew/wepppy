# Broad Exception Elimination With Contract-Safe Regression Control

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package completes, broad exception handling in core production paths will be intentional, documented, and test-locked rather than incidental. Users should continue to see stable API/workflow behavior, but hidden failure masking should be removed. The main observable result is safer and more diagnosable runtime behavior with no contract drift.

## Progress

- [x] (2026-02-22 21:19Z) Reviewed global/subsystem standards and exception policy documents.
- [x] (2026-02-22 21:19Z) Captured broad-catch baseline counts across production scope.
- [x] (2026-02-22 21:19Z) Drafted and installed this active ExecPlan under work-package prompts.
- [x] (2026-02-22) Milestone 0: baseline artifact + report-mode checker + boundary allowlist template + tests.
- [x] (2026-02-22 22:31Z) Milestone 1: characterization tests for high-risk boundary paths (rq-engine, NoDb, WEPPcloud, query-engine) + milestone artifact.
- [x] (2026-02-22 23:25Z) Milestone 2: rq-engine route cleanup batch A completed (`bootstrap_routes.py`, `omni_routes.py`, `fork_archive_routes.py`, `project_routes.py`, `job_routes.py`) with 8 broad catches removed and regression tests added.
- [x] (2026-02-23 00:13Z) Milestone 3: RQ worker cleanup batch A completed (`project_rq.py`, `batch_rq.py`, `omni_rq.py`) with 4 broad catches removed, reviewer findings integrated, and worker regression tests added.
- [x] (2026-02-23 01:04Z) Milestone 4: NoDb cleanup batch A completed (`nodb/base.py`) with lock-safe boundary retention, 3 broad catches removed, and NoDb regression tests added.
- [x] (2026-02-23 01:32Z) Milestone 5: WEPPcloud route cleanup batch A completed (`user.py`, `wepp_bp.py`) by eliminating 12 bare catches via explicit `except Exception` boundaries with route regression tests passing.
- [x] (2026-02-23 02:09Z) Milestone 6: query-engine/services tail cleanup batch completed (`query_engine/app/server.py`, `services/cao/.../inbox_service.py`) with 2 broad catches removed and focused regression tests.
- [x] (2026-02-23) Milestone 7: changed-file guard activation and package closeout completed (allowlist, final metrics artifact, and full-suite gate).
- [x] (2026-02-23) Milestone 7a: broad-catch checker changed-file enforcement mode (`--enforce-changed`, `--base-ref`) + unit tests.
- [x] (2026-02-23) Milestone 8: deferred swallow-style hotspot closure (`user.py`, `inbox_service.py`) with subagent loop completion, regression tests, allowlist promotion for true boundaries, and full-suite gate.

## Surprises & Discoveries

- Observation: broad catches are highly concentrated in runtime-critical subsystems rather than isolated utility code.
  Evidence: `wepppy/weppcloud` (`249`), `wepppy/microservices/rq_engine` (`174`), `wepppy/rq` (`162`), `wepppy/nodb` (`141`).

- Observation: many broad catches are boundary wrappers that currently preserve canonical route payloads; naive narrowing will regress contracts.
  Evidence: route-level wrappers in `wepppy/microservices/rq_engine/job_routes.py` rely on broad boundary catches that log + return canonical `error` payloads.

- Observation: no repository-level changed-file guard currently prevents new broad catches.
  Evidence: latest code-quality summary reports exception rules source/configured/applied as none/0/0.

- Observation: characterization coverage in this host environment is gated by optional runtime dependencies and unavailable Docker socket access.
  Evidence: `wctl run-pytest ...` fails with Docker socket permission errors; direct pytest runs skip/error when `fastapi`, `flask`, `starlette`, or `jsonpickle` are absent.

- Observation: narrowing invalid-runid classification exposed a hidden type-validation edge for non-string `target_runid` payloads.
  Evidence: reviewer detected `target_runid=123` path could drift from 400 validation into 500; fixed with explicit non-string guard before `get_wd(...)`.

- Observation: previous Docker/socket blocker was transient; milestone-local RQ suites now run in canonical `wctl` containers.
  Evidence: `wctl run-pytest tests/rq/test_exception_logging.py tests/rq/test_wepp_rq_stage_post.py --maxfail=1` passed (`6 passed`), and `wctl run-pytest tests/rq/test_project_rq_readonly.py --maxfail=1` passed (`3 passed`).

- Observation: narrowing prep bookkeeping catches in `set_run_readonly_rq` exposed a boundary placement issue where unexpected pre-`try` failures could skip `EXCEPTION` status publishing.
  Evidence: reviewer flagged `project_rq.py` pre-boundary path; fixed by moving prep bookkeeping into the outer function `try` and test-locking the behavior in `tests/rq/test_project_rq_readonly.py`.

- Observation: NoDb test monkeypatching `logging.getLogger` can destabilize pytest internals if the monkeypatch does not preserve the no-argument call signature.
  Evidence: first `wctl run-pytest tests/nodb/test_base_misc.py --maxfail=1` failed with pytest logging `TypeError` until tests restored a compatible fallback logger shim.

- Observation: bare-catch normalization can materially reduce `bare-except` risk without changing total broad-catch count.
  Evidence: Milestone 5 converted 12 bare catches to explicit `except Exception` in WEPPcloud routes, leaving total broad count unchanged (`1105`) but reducing global bare catches from `94` to `82`.

- Observation: current `QueryRequest` validation failures in query-engine are limited to `TypeError`/`ValueError` in this code path (including pydantic validation behavior in the runtime env), allowing safe narrowing of the 422 mapping boundary.
  Evidence: Milestone 6 test run validated invalid payload handling remains 422 with existing envelope while broad catch was removed in `run_query_endpoint`.

- Observation: Python 3.11+ `except*` handlers (`ast.TryStar`) are a distinct AST node family and were not detected by the initial checker implementation.
  Evidence: reviewer flagged `scan_python_source` walking only `ast.Try`; Milestone 7 updated scanner to include `ast.TryStar` and added regression coverage in `tests/tools/test_check_broad_exceptions.py`.

- Observation: changed-file enforcement in this package is intentionally per-file increase based, not purely global-net based.
  Evidence: enforcement report fails when any changed file has `delta > 0` even if aggregate net delta is zero; wording/help text was updated in Milestone 7 to match this behavior.

- Observation: deferred swallow hotspots split cleanly into two classes: control-flow catches that can be narrowed and true per-item boundaries that should stay broad but logged/allowlisted.
  Evidence: Milestone 8 narrowed `_claim_names`, `_has_idle_pattern`, and provider import detection while promoting `user.py` per-run list boundaries to canonical allowlist entries (`BEA-20260223-010`, `BEA-20260223-011`).

## Decision Log

- Decision: execute phased cleanup by subsystem instead of a global codemod.
  Rationale: phased changes reduce blast radius and keep regressions attributable.
  Date/Author: 2026-02-22 / Codex

- Decision: require characterization tests before narrowing high-risk boundary catches.
  Rationale: broad catches currently encode implicit contracts in several modules.
  Date/Author: 2026-02-22 / Codex

- Decision: preserve boundary catches only when they are explicit boundaries with logging and documented rationale.
  Rationale: root policy allows deliberate boundaries but forbids silent swallowing.
  Date/Author: 2026-02-22 / Codex

- Decision: retain canonical traceback-bearing `error.details` behavior on rq-engine exception boundaries during cleanup phases.
  Rationale: `docs/schemas/rq-response-contract.md` requires stacktrace details for exception-driven failures, so narrowing must preserve that response contract.
  Date/Author: 2026-02-22 / Codex

- Decision: defer reviewer-identified broader rq-engine contract harmonization (enqueue 202 semantics, auth-mode policy, legacy error classification) out of Milestone 2.
  Rationale: those issues predate this package and exceed minimal catch-narrowing scope; batching them with this change would increase regression risk.
  Date/Author: 2026-02-22 / Codex

- Decision: narrow optional Discord integration import guards from broad `Exception` to `ImportError` in RQ worker modules.
  Rationale: missing optional dependency should degrade gracefully, but unexpected import-time errors should fail fast instead of being silently masked.
  Date/Author: 2026-02-23 / Codex

- Decision: keep `set_run_readonly_rq` prep bookkeeping inside the main exception boundary when narrowing best-effort catches.
  Rationale: preserves worker `EXCEPTION` status telemetry for unexpected prep failures while still narrowing expected operational errors (`redis`/I/O/serialization classes).
  Date/Author: 2026-02-23 / Codex

- Decision: retain broad best-effort boundaries for `NoDbBase.dump` Redis side effects in this batch while narrowing log-level helpers and bare cleanup catches.
  Rationale: `dump()` executes inside `dump_and_unlock`; raising from cache-mirror side effects risks lock-retention regressions, so those boundaries stay explicit and documented until a broader lock-flow refactor is planned.
  Date/Author: 2026-02-23 / Codex

- Decision: prioritize WEPPcloud bare `except:` removal before deeper per-route exception taxonomy narrowing.
  Rationale: replacing bare catches with `except Exception` is low-risk, preserves fail-closed behavior, and avoids swallowing `BaseException` subclasses while keeping endpoint contracts stable.
  Date/Author: 2026-02-23 / Codex

- Decision: narrow query-engine payload validation boundary to explicit validation exception families (`TypeError`, `ValueError`) while preserving existing 422 envelope shape.
  Rationale: this removes an incidental broad catch without changing characterized invalid-payload responses.
  Date/Author: 2026-02-23 / Codex

- Decision: enforce changed-file policy as "no per-file broad-catch increases" rather than global-net-only gating.
  Rationale: a new broad catch in one changed file should not be masked by removals in another changed file.
  Date/Author: 2026-02-23 / Codex

- Decision: extend checker AST traversal to include `ast.TryStar` handlers.
  Rationale: without `TryStar` support, `except* Exception` sites could evade report/enforcement checks.
  Date/Author: 2026-02-23 / Codex

- Decision: close deferred swallow hotspots in-place rather than opening a new package by running a Milestone 8 addendum with the same mandatory subagent loop.
  Rationale: the remaining hotspots were bounded and testable in one focused batch without contract drift risk.
  Date/Author: 2026-02-23 / Codex

- Decision: keep WEPPcloud per-run metadata load catches broad but explicit, logged, and canonical-allowlisted.
  Rationale: list endpoints must degrade by omitting a bad run, not fail globally; this is a deliberate boundary and now audit-tracked.
  Date/Author: 2026-02-23 / Codex

## Outcomes & Retrospective

- (2026-02-22 21:19Z) Outcome: package scaffold and active plan installed with phased execution model and explicit regression gates.
- (2026-02-22 22:31Z) Outcome: Milestone 0 completed with baseline inventory artifact, report-mode checker, suppression support, and tool tests (`3 passed` in local pytest).
- (2026-02-22 22:31Z) Outcome: Milestone 1 completed with new characterization tests spanning rq-engine/NoDb/WEPPcloud/query-engine; full `wctl` validation remains pending due external Docker/runtime dependency blockers in this environment.
- (2026-02-22 23:25Z) Outcome: Milestone 2 completed with rq-engine batch A narrowing and global broad-catch reduction from `1120` to `1112` (`artifacts/milestone_2_catch_diff.md`); full microservice `wctl` validation remains blocked by Docker socket restrictions in this environment.
- (2026-02-23 00:13Z) Outcome: Milestone 3 completed with targeted RQ worker narrowing in `project_rq.py`, `batch_rq.py`, and `omni_rq.py`, reducing global broad catches from `1112` to `1108` (`artifacts/milestone_3_catch_diff.md`) with milestone-local `wctl` worker suites passing (`9 passed` total).
- (2026-02-23 01:04Z) Outcome: Milestone 4 completed with NoDb `base.py` catch cleanup and lock-safety test hardening, reducing global broad catches from `1108` to `1105` (`artifacts/milestone_4_catch_diff.md`) with milestone-local NoDb suites passing (`63 passed` across targeted commands).
- (2026-02-23 01:32Z) Outcome: Milestone 5 completed with WEPPcloud route bare-catch elimination batch (`user.py`, `wepp_bp.py`) and expanded route regression coverage; global total broad count stayed `1105` while bare catches dropped from `94` to `82` (`artifacts/milestone_5_catch_diff.md`).
- (2026-02-23 02:09Z) Outcome: Milestone 6 completed with query-engine/services tail narrowing (`artifacts/milestone_6_catch_diff.md`), reducing global broad catches from `1105` to `1103` with query-engine and CAO targeted suites passing (`30 passed` combined).
- (2026-02-23) Outcome: Milestone 7 completed with changed-file enforcement activation hardening (`TryStar` support + clarified per-file policy messaging), populated boundary allowlist, and final metrics artifact (`artifacts/final_validation_summary.md`).
- (2026-02-23) Outcome: required pre-handoff full-suite gate passed: `wctl run-pytest tests --maxfail=1` -> `2048 passed, 29 skipped`.
- (2026-02-23) Outcome: Milestone 8 completed with deferred hotspot cleanup, broadened regression coverage in WEPPcloud/CAO tests, and final full-suite gate pass (`2057 passed, 29 skipped`); package broad catches reduced from `1103` to `1099` (`artifacts/milestone_8_catch_diff.md`).

## Context and Orientation

Production baseline from repository scan:

1. Broad catches (`except Exception`, bare `except`, `except BaseException`, including tuples) in `wepppy/` + `services/`: `1120` (plus `6` suppressed via inline tags).
2. Bare catches in `wepppy/` + `services/`: `96`.
3. Highest concentration folders:
   - `wepppy/weppcloud`: `249`
   - `wepppy/microservices/rq_engine`: `174`
   - `wepppy/rq`: `162`
   - `wepppy/nodb`: `141`

High-risk contract areas:

1. `wepppy/microservices/rq_engine/*` must retain `docs/schemas/rq-response-contract.md` payload/status shape.
2. `wepppy/rq/*` must retain failure publishing and exception propagation semantics.
3. `wepppy/nodb/*` must retain lock/persistence safety (`locked`, `dump`, `dump_and_unlock`).
4. `wepppy/weppcloud/routes/*` must preserve auth/session and route behavior.

Representative high-volume files:

1. `wepppy/rq/project_rq.py`
2. `wepppy/weppcloud/routes/nodb_api/wepp_bp.py`
3. `wepppy/nodb/base.py`
4. `wepppy/microservices/rq_engine/bootstrap_routes.py`
5. `wepppy/microservices/rq_engine/omni_routes.py`
6. `wepppy/microservices/rq_engine/fork_archive_routes.py`

## Plan of Work

This plan runs in eight milestones with strict subagent orchestration. Each milestone follows this fixed loop:

1. Explorer pass (`explorer`): map exact catch blocks for touched files and classify each as `boundary`, `control_flow`, or `swallow`.
2. Refactor pass (domain specialist):
   - `rq_refactorer` for `wepppy/microservices/rq_engine/*` and `wepppy/rq/*`
   - `nodb_refactorer` for `wepppy/nodb/*`
   - `weppcloud_refactorer` for `wepppy/weppcloud/routes/*`
   - `query_engine_refactorer` for `wepppy/query_engine/*`
   - `worker` for tools/long tail and cross-cutting edits
3. Reviewer pass (`reviewer`): severity-ranked findings with file/line references.
4. Test pass (`test_guardian`): run targeted commands, author missing regression tests, and report uncovered risk.
5. Integrator closeout: resolve findings, rerun gates, update this ExecPlan + package tracker.

No milestone is complete until reviewer and test guardian outputs are reflected in docs and required validations are green.

## Milestone Narrative

### Milestone 0: Baseline Artifacts and Guard Bootstrap

Create a repeatable baseline and a preliminary broad-catch checker for changed-file policy.

Work:

1. Add baseline artifact `docs/work-packages/20260222_broad_exception_elimination/artifacts/broad_exception_baseline_20260222.md` with counts by subsystem and top files.
2. Add preliminary checker `tools/check_broad_exceptions.py` (report mode first) and tests under `tests/tools/`.
3. Add package artifact for approved boundary template (owner, rationale, expiry).

Go/No-Go:

1. Go when checker output matches raw `rg` spot checks and tests pass.
2. No-Go if checker cannot distinguish deliberate boundaries from accidental catches.

### Milestone 1: Characterization Test Net

Lock current behavior in high-risk boundary paths before large edits.

Work:

1. Add/extend rq-engine tests to assert canonical error envelope and status behavior for boundary failures.
2. Add NoDb-focused tests for lock/persistence-related exception translation boundaries.
3. Add WEPPcloud route exception-path tests for key nodb_api and auth-adjacent routes.
4. Add query-engine MCP/server failure-envelope tests.

Go/No-Go:

1. Go when tests fail under intentional break patches and pass with baseline behavior.
2. No-Go if coverage remains ambiguous on contract-critical branches.

### Milestone 2: rq-engine Cleanup

Narrow over-broad catches in `wepppy/microservices/rq_engine/*` while preserving `docs/schemas/rq-response-contract.md`.

Initial target file set:

1. `wepppy/microservices/rq_engine/bootstrap_routes.py`
2. `wepppy/microservices/rq_engine/omni_routes.py`
3. `wepppy/microservices/rq_engine/fork_archive_routes.py`
4. `wepppy/microservices/rq_engine/project_routes.py`
5. `wepppy/microservices/rq_engine/job_routes.py`

Go/No-Go:

1. Go when payload keys/status codes remain contract-identical on characterized paths.
2. No-Go on any `error` envelope drift or auth classification drift.

### Milestone 3: RQ Worker Cleanup

Narrow worker catches in `wepppy/rq/*` without changing failure semantics.

Initial target file set:

1. `wepppy/rq/project_rq.py`
2. `wepppy/rq/batch_rq.py`
3. `wepppy/rq/culvert_rq.py`
4. `wepppy/rq/wepp_rq.py`
5. `wepppy/rq/omni_rq.py`

Go/No-Go:

1. Go when worker failure paths still publish/log and re-raise as expected.
2. No-Go if any path flips from failure to apparent success or drops exception telemetry.

### Milestone 4: NoDb Cleanup

Address high-risk broad catches in NoDb with lock/persistence safety first.

Initial target file set:

1. `wepppy/nodb/base.py`
2. `wepppy/nodb/core/wepp_prep_service.py`
3. `wepppy/nodb/core/climate.py`
4. `wepppy/nodb/core/watershed.py`
5. `wepppy/nodb/core/wepp.py`
6. `wepppy/nodb/core/landuse.py`

Go/No-Go:

1. Go when lock and persistence test matrix remains green.
2. No-Go on lock ownership regressions, stale-write regressions, or silent conversion to `None`/`False`/`0` for unexpected failures.

### Milestone 5: WEPPcloud Route Cleanup

Narrow catches in `wepppy/weppcloud/routes/*`, prioritizing bare catches and nodb_api hotspots.

Initial target file set:

1. `wepppy/weppcloud/routes/nodb_api/wepp_bp.py`
2. `wepppy/weppcloud/routes/nodb_api/project_bp.py`
3. `wepppy/weppcloud/routes/nodb_api/climate_bp.py`
4. `wepppy/weppcloud/routes/_security/oauth.py`
5. `wepppy/weppcloud/routes/user.py`

Go/No-Go:

1. Go when route contracts and auth/session behavior are unchanged on characterized paths.
2. No-Go on any 401/403/500 misclassification or fail-open regression.

### Milestone 6: Query Engine and Services Tail

Close remaining targeted broad catches in query engine and selected service paths.

Initial target file set:

1. `wepppy/query_engine/app/server.py`
2. `wepppy/query_engine/app/mcp/router.py`
3. `services/cao/src/cli_agent_orchestrator/*` (only touched broad catches linked to runtime boundaries)

Go/No-Go:

1. Go when MCP/server error envelopes remain stable and tests pass.
2. No-Go on contract drift or diagnostic visibility loss.

### Milestone 7: Guard Activation and Closeout

Turn broad-catch checker into changed-file enforcement and close package artifacts.

Work:

1. Activate changed-file enforcement mode in checker.
2. Add/update allowlist artifact for intentionally broad boundaries.
3. Run full validation and produce final before/after metrics artifact.
4. Update `package.md`, `tracker.md`, and move finished prompt(s) to `prompts/completed/` if appropriate.

Go/No-Go:

1. Go when guard blocks undocumented per-file broad-catch increases in changed files.
2. No-Go if policy cannot be enforced without suppressing legitimate boundaries.

### Milestone 8: Deferred Swallow Hotspot Closure

Resolve the deferred swallow-style hotspots carried from Milestone 7 closeout.

Target file set:

1. `wepppy/weppcloud/routes/user.py`
2. `services/cao/src/cli_agent_orchestrator/services/inbox_service.py`

Work:

1. Reclassify each deferred hotspot as either removable control-flow catch or deliberate boundary.
2. Narrow removable control-flow catches to expected exception families and add explicit logging.
3. For retained boundaries, add short rationale comments, add regression coverage, and promote to canonical allowlist when appropriate.
4. Re-run milestone-local and full-suite gates; update package artifacts and trackers.

Go/No-Go:

1. Go when deferred hotspot list is cleared, no silent swallow remains in touched paths, and gates pass.
2. No-Go if contract behavior drifts on WEPPcloud profile/runs or CAO inbox delivery paths.

## Concrete Steps

From `/workdir/wepppy`, execute for each milestone:

    rg -n "^\s*except\s*:\s*$|^\s*except\s+Exception\b|^\s*except\s+BaseException\b" wepppy services > /tmp/broad-exceptions.current.txt

    # targeted suite slices (examples; exact modules vary by milestone)
    wctl run-pytest tests/microservices/test_rq_engine_jobinfo.py tests/microservices/test_rq_engine_auth.py --maxfail=1
    wctl run-pytest tests/rq/test_exception_logging.py tests/rq/test_wepp_rq_stage_post.py --maxfail=1
    wctl run-pytest tests/nodb/test_locked.py tests/nodb/test_base_unit.py tests/nodb/test_lock_race_conditions.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_exception_logging_routes.py tests/weppcloud/routes/test_wepp_bp.py --maxfail=1
    wctl run-pytest tests/query_engine/test_mcp_router.py tests/query_engine/test_server_routes.py --maxfail=1

    # subsystem sweeps after milestone-local green
    wctl run-pytest tests/microservices --maxfail=1
    wctl run-pytest tests/rq --maxfail=1
    wctl run-pytest tests/nodb --maxfail=1
    wctl run-pytest tests/weppcloud/routes --maxfail=1
    wctl run-pytest tests/query_engine --maxfail=1

    # queue graph check when enqueue wiring changes
    wctl check-rq-graph

    # pre-handoff gate
    wctl run-pytest tests --maxfail=1

## Validation and Acceptance

Acceptance requires all conditions:

1. No new undocumented broad catches in changed files.
2. No silent broad-exception swallowing in touched production paths.
3. Boundary catches that remain are minimal, documented, and logged.
4. Contract-sensitive surfaces remain stable:
   - rq-engine canonical error payload and status behavior
   - worker failure publish/log behavior
   - NoDb lock/persistence semantics
   - WEPPcloud auth/session boundary behavior
5. Required targeted suites and full `tests --maxfail=1` pass.

## Idempotence and Recovery

1. Keep milestone diffs small and reversible (recommended <= 40 catch-site edits per milestone batch).
2. If regressions appear, revert only milestone-local changes and rerun milestone-local tests before reattempt.
3. Re-running baseline counts and checker reports is safe and repeatable.
4. Do not advance milestones until the current milestone gates are green and logged.

## Artifacts and Notes

Create/update the following artifacts during execution:

1. `artifacts/broad_exception_baseline_20260222.md`
2. `artifacts/milestone_<n>_catch_diff.md` (per milestone summary)
3. `artifacts/boundary_allowlist.md` (deliberate broad catches with owner/rationale/expiry)
4. `artifacts/final_validation_summary.md`

Each milestone artifact should include:

1. Before/after catch counts for touched files.
2. Exact commands run and pass/fail outcomes.
3. Residual risks and deferred items.

## Interfaces and Dependencies

Must preserve:

1. `docs/schemas/rq-response-contract.md` canonical response/error shape.
2. Existing public route signatures and payload contracts unless explicitly approved.
3. NoDb lock/persistence boundaries and semantics in `wepppy/nodb/base.py` and touched `wepppy/nodb/core/*` modules.
4. Existing queue wiring behavior; if changed, update catalog and run queue graph validation.

Subagent dependency contract:

1. Refactorers do not self-approve; reviewer findings are mandatory input.
2. Test guardian owns final validation command set for each milestone.
3. Integrator updates this ExecPlan and `docs/work-packages/20260222_broad_exception_elimination/tracker.md` at each milestone boundary.

Update log:

- 2026-02-22: Initial plan authored to execute broad exception cleanup end-to-end with phased risk controls and subagent orchestration.
- 2026-02-22: Milestone 0 executed with baseline/checker/bootstrap artifacts (`artifacts/milestone_0_catch_diff.md`).
- 2026-02-22: Milestone 1 executed with cross-subsystem characterization tests and milestone artifact (`artifacts/milestone_1_catch_diff.md`).
- 2026-02-22: Milestone 2 executed with rq-engine route narrowing batch A and milestone artifact (`artifacts/milestone_2_catch_diff.md`).
- 2026-02-23: Milestone 3 executed with RQ worker narrowing batch A, reviewer-integrated boundary fix in `set_run_readonly_rq`, and milestone artifact (`artifacts/milestone_3_catch_diff.md`).
- 2026-02-23: Milestone 4 executed with NoDb `base.py` lock-safe narrowing batch, expanded NoDb regression coverage, and milestone artifact (`artifacts/milestone_4_catch_diff.md`).
- 2026-02-23: Milestone 5 executed with WEPPcloud route bare-catch normalization batch and milestone artifact (`artifacts/milestone_5_catch_diff.md`).
- 2026-02-23: Milestone 6 executed with query-engine/services tail narrowing batch and milestone artifact (`artifacts/milestone_6_catch_diff.md`).
- 2026-02-23: Milestone 7 executed with changed-file guard closeout, approved-boundary allowlist population, final validation metrics artifact, and full-suite pre-handoff gate (`wctl run-pytest tests --maxfail=1`).
- 2026-02-23: Milestone 8 executed for deferred swallow hotspots (`user.py`, `inbox_service.py`) with mandatory subagent loop, new regression tests, allowlist promotion for true boundaries, and milestone artifact (`artifacts/milestone_8_catch_diff.md`).
