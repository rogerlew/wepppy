# NoDb Broad-Exception Boundary Closure for `wepppy/nodb/**`

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package closes, NoDb broad exception handling is fully classified and stable: internal NoDb logic no longer uses broad catches where narrow handling is possible, and every remaining broad catch in `wepppy/nodb/**` is a true boundary with context logging, contract-safe behavior, rationale comments, and canonical allowlist coverage. This eliminates the need for another NoDb broad-exception cleanup package.

## Progress

- [x] (2026-02-23 00:00Z) Read required guidance: `AGENTS.md`, `wepppy/nodb/AGENTS.md`, and `docs/prompt_templates/codex_exec_plans.md`.
- [x] (2026-02-23 00:00Z) Created package scaffold and initialized package/tracker/execplan files.
- [x] (2026-02-23 00:10Z) Installed active ExecPlan pointer in root `AGENTS.md` and added package in-progress entry in `PROJECT_TRACKER.md`.
- [x] (2026-02-23 00:25Z) Milestone 0 complete: baseline scanner artifacts captured and baseline explorer risk map documented.
- [x] (2026-02-23 01:30Z) Milestone 1 complete: high-risk NoDb boundary characterization tests added (`tests/nodb/test_base_boundary_characterization.py`).
- [x] (2026-02-23 02:10Z) Milestone 2 complete: `wepppy/nodb/base.py` and `wepppy/nodb/core/**` refactor/hardening pass merged.
- [x] (2026-02-23 02:40Z) Milestone 3 complete: `wepppy/nodb/mods/**` focused narrowing and boundary cleanup pass merged.
- [x] (2026-02-23 03:00Z) Milestone 4 complete: NoDb allowlist and artifact synchronization applied.
- [x] (2026-02-23 03:20Z) Milestone 5 complete: final explorer review pass executed and follow-up fixes applied (`wepp.py` telemetry/narrowing + base spawn boundary telemetry).
- [x] (2026-02-23 04:20Z) Milestone 6 complete: required gates/tests/doc-lint passed and package docs/trackers closed.

## Surprises & Discoveries

- Observation: Baseline NoDb scan is broad-heavy even after earlier global cleanup work: `137` broad catches (`except Exception`) across `34` files, concentrated in `wepppy/nodb/base.py` (22) and `wepppy/nodb/core/watershed.py` (15).
  Evidence: `artifacts/baseline_nodb_broad_exceptions.json` and baseline explorer synthesis.
- Observation: Allowlist-aware baseline still has `134` unresolved findings, so full closure requires either substantial narrowing/removal or comprehensive residual boundary allowlisting with line-accurate entries.
  Evidence: `python3 tools/check_broad_exceptions.py wepppy/nodb --json > /tmp/nodb_broad_allow_baseline.json` (`findings_count=134`).
- Observation: Narrowing cache mirror side-effect catches in `NoDbBase.dump` and `_hydrate_instance` regressed existing NoDb characterization tests.
  Evidence: `tests/nodb/test_base_unit.py::test_dump_swallows_redis_cache_side_effect_failures` failed until broad boundary handling was restored for those side effects.

## Decision Log

- Decision: Use required multi-agent orchestration (`explorer` baseline, three parallel workers, final `explorer` review).
  Rationale: User requirement and best fit for disjoint NoDb ownership slices.
  Date/Author: 2026-02-23 / Codex.
- Decision: Prioritize lock/release and orchestration invariants when deciding whether a broad catch may remain as a boundary.
  Rationale: NoDb runtime safety depends on not regressing lock retention, dump consistency, and cancellation semantics; these paths need conservative boundary treatment.
  Date/Author: 2026-02-23 / Codex.
- Decision: Regenerate NoDb allowlist rows from final no-allowlist scanner output at closeout.
  Rationale: Iterative refactors shifted line numbers; regeneration ensures allowlist/file-line sync and deterministic unresolved-finding closure.
  Date/Author: 2026-02-23 / Codex.
- Decision: Keep broad side-effect boundaries in `NoDbBase.dump` and `_hydrate_instance` for Redis/cache mirrors.
  Rationale: Characterization tests demonstrate these side effects must be best-effort and must not break lock-release/persistence flows.
  Date/Author: 2026-02-23 / Codex.

## Outcomes & Retrospective

Package closed with required gates passing and artifacts complete. Final NoDb metrics:
- Baseline no-allowlist broad findings: `137` (`bare-except=0`)
- Final no-allowlist broad findings: `93` (`bare-except=0`)
- Final allowlist-aware unresolved findings: `0`

Lessons learned:
- NoDb lock/persistence side-effect boundaries require conservative broad handling; over-narrowing these paths can regress contract-safe behavior.
- Final allowlist synchronization should happen after all code/test updates to avoid line-drift churn.

## Context and Orientation

This package only targets `wepppy/nodb/**` production exception handling and the directly related tests/docs/allowlist artifacts required for closure. The critical runtime file is `wepppy/nodb/base.py`, which owns NoDb serialization, lock acquisition/release, persistence, and side-effect mirrors. The `wepppy/nodb/core/**` modules implement controller behavior. The `wepppy/nodb/mods/**` modules implement additional model/control surfaces. The checker of record is `tools/check_broad_exceptions.py`; closure gates require both no-allowlist and allowlist-aware scans plus changed-file enforcement.

A broad exception here means `except Exception`, `except BaseException`, or `except:`. Internal parsing/validation/transforms should narrow to expected types. Broad catches may remain only at true boundaries where contract stability and lock/persistence safety require a final defensive boundary.

## Plan of Work

Milestone 0 establishes the baseline and classifies every current NoDb broad catch into `narrowed`, `boundary+allowlisted`, or `removed`. We will create an explicit resolution matrix artifact keyed by file and line. Milestone 1 adds characterization tests first for high-risk boundaries (lock release, dump persistence, and orchestration edges) so narrowing does not widen or mutate existing contracts. Milestones 2 and 3 execute the production refactor split across ownership slices: worker A owns `wepppy/nodb/base.py` and `wepppy/nodb/core/**`, worker B owns `wepppy/nodb/mods/**`, and worker C owns test updates and allowlist/docs synchronization. Milestone 5 runs a final independent explorer review pass for missed swallow paths and contract drift. Milestone 6 runs all required gates/tests, generates final artifacts, and closes the package with synced docs and tracker state.

## Concrete Steps

From `/workdir/wepppy`:

1. Create and activate package docs and pointer.
   - Update `AGENTS.md` to point active work-package ExecPlan at this plan path.
   - Update `PROJECT_TRACKER.md` to include this package in In Progress.

2. Capture baseline data.
   - `python3 tools/check_broad_exceptions.py wepppy/nodb --json --no-allowlist > docs/work-packages/20260223_nodb_broad_exception_boundary_closure/artifacts/baseline_nodb_broad_exceptions.json`
   - `python3 tools/check_broad_exceptions.py wepppy/nodb --json > /tmp/nodb_broad_allow_baseline.json`

3. Execute required sub-agent orchestration.
   - Baseline explorer inventory/risk map.
   - Parallel workers A/B/C with disjoint ownership and explicit collaboration notice.
   - Final explorer regression review pass.

4. Build resolution matrix and apply allowlist sync.
   - Create `artifacts/nodb_broad_exception_resolution_matrix.md` mapping each baseline finding to final disposition.
   - Update `docs/standards/broad-exception-boundary-allowlist.md` entries for NoDb residual boundaries only.

5. Run required gates and tests.
   - Hard bare gate and allowlist-aware unresolved gate.
   - Changed-file enforcement.
   - `wctl run-pytest tests/nodb`
   - `wctl run-pytest tests/nodir` (if touched)
   - `wctl run-pytest tests --maxfail=1`

6. Finalize artifacts and close package.
   - Write `artifacts/final_nodb_broad_exceptions.json` and `artifacts/final_validation_summary.md`.
   - Sync ExecPlan/tracker/`PROJECT_TRACKER.md` and reset root active ExecPlan pointer to `none`.

## Validation and Acceptance

Acceptance requires the explicit gates in this order:

1. `python3 tools/check_broad_exceptions.py wepppy/nodb --json --no-allowlist > /tmp/nodb_broad_no_allow.json`
2. `jq -e '.kinds["bare-except"] == 0' /tmp/nodb_broad_no_allow.json`
3. `python3 tools/check_broad_exceptions.py wepppy/nodb --json > /tmp/nodb_broad_allow.json`
4. `jq -e '.findings_count == 0' /tmp/nodb_broad_allow.json`
5. `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
6. `wctl run-pytest tests/nodb`
7. `wctl run-pytest tests/nodir` when NoDir tests were touched
8. `wctl run-pytest tests --maxfail=1`

Docs lint must pass for each changed doc:

- `wctl doc-lint --path AGENTS.md`
- `wctl doc-lint --path PROJECT_TRACKER.md`
- `wctl doc-lint --path docs/standards/broad-exception-boundary-allowlist.md`
- `wctl doc-lint --path docs/work-packages/20260223_nodb_broad_exception_boundary_closure/package.md`
- `wctl doc-lint --path docs/work-packages/20260223_nodb_broad_exception_boundary_closure/tracker.md`
- `wctl doc-lint --path docs/work-packages/20260223_nodb_broad_exception_boundary_closure/prompts/active/nodb_broad_exception_boundary_closure_execplan.md`
- `wctl doc-lint --path docs/work-packages/20260223_nodb_broad_exception_boundary_closure/artifacts/nodb_broad_exception_resolution_matrix.md`
- `wctl doc-lint --path docs/work-packages/20260223_nodb_broad_exception_boundary_closure/artifacts/final_validation_summary.md`

## Idempotence and Recovery

The broad-exception scans are idempotent and can be re-run at any time. If line-number drift causes allowlist mismatches, regenerate NoDb allowlist entries from the final no-allowlist scan and re-run allowlist-aware checks. If any worker introduces regressions, revert only the offending hunk in the owned files and re-run targeted NoDb tests before continuing.

## Artifacts and Notes

Required final artifacts:

- `docs/work-packages/20260223_nodb_broad_exception_boundary_closure/artifacts/baseline_nodb_broad_exceptions.json`
- `docs/work-packages/20260223_nodb_broad_exception_boundary_closure/artifacts/final_nodb_broad_exceptions.json`
- `docs/work-packages/20260223_nodb_broad_exception_boundary_closure/artifacts/nodb_broad_exception_resolution_matrix.md`
- `docs/work-packages/20260223_nodb_broad_exception_boundary_closure/artifacts/final_validation_summary.md`

## Interfaces and Dependencies

The checker interface is `python3 tools/check_broad_exceptions.py <path> --json [--no-allowlist]` with optional enforcement mode `--enforce-changed --base-ref origin/master`. NoDb exception boundary behavior depends on `wepppy/nodb/base.py` lock and dump helpers and downstream controller/mod modules. Validation depends on `wctl` wrappers for pytest and docs lint.

### Revision Note

- 2026-02-23 / Codex: Initial executable plan authored at package kickoff to satisfy required NoDb broad-exception closure workflow.
- 2026-02-23 / Codex: Updated living sections with baseline scan outcomes, risk-map discoveries, and active worker-orchestration status.
- 2026-02-23 / Codex: Updated all living sections for milestone completion, final validation outcomes, and package closure.
