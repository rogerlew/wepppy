# Tracker - Omni Contrast Hillslope Re-run Recovery (`delete_after_interchange`)

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-03-17  
**Current phase**: Completed and closed  
**Last updated**: 2026-03-17  
**Next milestone**: None (package complete)  
**Implementation plan**: `docs/work-packages/20260317_omni_contrast_hillslope_rerun/prompts/completed/omni_contrast_hillslope_rerun_execplan.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Reviewed Omni contrast execution chain across `omni_rq`, Omni station catalog services, and contrast clone execution to identify the concrete failure mechanism (2026-03-17).
- [x] Confirmed `make_watershed_omni_contrasts_run` requires `{wepp_id_path}.pass.dat`, so deleted hillslope sources break contrast watershed runs (2026-03-17).
- [x] Confirmed existing `wepp.run_hillslopes()` path can regenerate hillslope outputs independently from prep/interchange (2026-03-17).
- [x] Authored work-package scaffold (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `notes`, `artifacts`) (2026-03-17).
- [x] Authored active ExecPlan with implementation and validation milestones (2026-03-17).
- [x] Registered package in `PROJECT_TRACKER.md` as in progress (2026-03-17).
- [x] Added Omni contrast preflight helpers in `wepppy/rq/omni_rq.py` to collect scenario keys, resolve scenario working directories, and rerun hillslopes only (2026-03-17).
- [x] Wired preflight into `run_omni_contrasts_rq` before contrast child enqueue fan-out (2026-03-17).
- [x] Corrected preflight rerun path to pass scenario `cli/slp` relpaths back to base `wepp/runs` (matching Omni scenario execution semantics for pre-existing scenario directories) (2026-03-17).
- [x] Extracted shared Omni helper `_hillslope_input_relpath_to_base_runs` and reused it in both scenario orchestration and contrast rerun preflight (2026-03-17).
- [x] Added explicit contrast rerun input validation + diagnostics for missing hillslope inputs before rerun execution (2026-03-17).
- [x] Added regression tests in `tests/rq/test_omni_rq.py` for delete-flag-enabled and delete-flag-disabled paths (2026-03-17).
- [x] Added focused tests for rerun input validation contracts and `max_workers` forwarding behavior (2026-03-17).
- [x] Updated broad-exception allowlist line anchors for `wepppy/rq/omni_rq.py` in `docs/standards/broad-exception-boundary-allowlist.md` after line shifts (2026-03-17).
- [x] Executed targeted and full pytest validation for package closure (2026-03-17).
- [x] Moved ExecPlan from `prompts/active` to `prompts/completed` with outcomes (2026-03-17).
- [x] Updated `AGENTS.md` and `PROJECT_TRACKER.md` for package closure (2026-03-17).

## Timeline

- **2026-03-17** - Package created and scoped.
- **2026-03-17** - Root-cause path confirmed (`delete_after_interchange` removes files required by contrast watershed stubs).
- **2026-03-17** - Active ExecPlan drafted with implementation milestones.
- **2026-03-17** - Implemented rerun preflight in `run_omni_contrasts_rq` and added regression tests.
- **2026-03-17** - Corrected rerun preflight to use base-run relpaths for scenario `cli/slp` inputs after real-project failure feedback.
- **2026-03-17** - Implemented all post-review follow-ups: shared relpath helper, explicit rerun input diagnostics, and expanded regression coverage.
- **2026-03-17** - Validation completed (`tests/rq/test_omni_rq.py`, broad-exception check, full `tests` suite).
- **2026-03-17** - Package closed; tracker/project pointers synchronized.

## Decisions

### 2026-03-17: Implement recovery in `run_omni_contrasts_rq` orchestration layer
**Context**: User requested the rerun behavior specifically in `run_omni_contrasts_rq`, and this is the queue fan-out point where queued contrast IDs are known.

**Options considered**:
1. Implement in `run_omni_contrasts_rq` before enqueueing contrast children.
2. Implement inside each `run_omni_contrast_rq` child task.
3. Implement in `OmniRunOrchestrationService.run_omni_contrasts` only.

**Decision**: Option 1.

**Impact**: Single preflight pass per invocation, deduped scenario reruns, and no per-child repeated reruns.

---

### 2026-03-17: Regenerate hillslope outputs without prep or interchange
**Context**: User explicitly requested no prep and no interchange for this recovery path.

**Options considered**:
1. Full rerun path (`prep_hillslopes` + `run_hillslopes` + interchange).
2. Hillslope rerun only (`run_hillslopes`) in target scenario working directories.

**Decision**: Option 2.

**Impact**: Minimal runtime work, no interchange side effects, and direct regeneration of required `H*.pass.dat` family outputs.

---

### 2026-03-17: Run preflight only for contrasts selected in this invocation
**Context**: Existing skip paths can prune contrasts (`up_to_date`, `in_progress`, landuse unchanged, missing sidecar).

**Options considered**:
1. Rerun all known contrast scenario pairs.
2. Rerun only scenario keys referenced by finalized `run_ids`.

**Decision**: Option 2.

**Impact**: Preserves current skip semantics and avoids unnecessary hillslope reruns.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Scenario working directory resolution mismatch (base vs `_pups/omni/scenarios/<key>`) | High | Medium | Implemented explicit resolution helper and regression test coverage for base + scenario directories. | Mitigated |
| Rerun preflight accidentally reintroduces prep/interchange side effects | High | Low | Helper path restricted to `Wepp.getInstance(...).run_hillslopes()` and tests assert behavior. | Mitigated |
| Runtime overhead from rerunning the same scenario multiple times | Medium | Medium | Scenario keys are deduplicated before rerun loop. | Mitigated |
| Existing skip logic regressions (`up_to_date`, `in_progress`, missing sidecar) | Medium | Medium | Contrast selection flow unchanged; existing and new tests passed. | Mitigated |

## Verification Checklist

### Code Quality
- [x] Targeted tests pass:
  - `wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1`
- [x] Changed-file broad exception guard remains clean:
  - `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- [x] Pre-handoff sanity pass:
  - `wctl run-pytest tests --maxfail=1`

### Documentation
- [x] `wctl doc-lint --path docs/work-packages/20260317_omni_contrast_hillslope_rerun`
- [x] `wctl doc-lint --path PROJECT_TRACKER.md`
- [x] `wctl doc-lint --path AGENTS.md`

### Behavioral Validation
- [x] Delete-flag enabled path reruns hillslopes for deduped scenario targets used by queued contrasts.
- [x] Delete-flag disabled path skips rerun preflight.
- [x] No new queue wiring edges introduced (verified by inspection; no enqueue topology changes).

## Progress Notes

### 2026-03-17: Discovery and package authoring
**Agent/Contributor**: Codex

**Work completed**:
- Traced the full Omni contrast path from rq-engine enqueue to `run_omni_contrasts_rq` and contrast child execution.
- Verified that contrast watershed stubs read `{wepp_id_path}.pass.dat` and that interchange cleanup removes those files when `delete_after_interchange` is enabled.
- Confirmed availability of a no-prep hillslope rerun primitive (`wepp.run_hillslopes()`) suitable for deterministic output regeneration.
- Authored package docs and active ExecPlan for implementation handoff.

**Blockers encountered**:
- None in discovery/planning.

**Next steps**:
1. Implement preflight helper(s) in `wepppy/rq/omni_rq.py`.
2. Add/adjust unit coverage in `tests/rq/test_omni_rq.py`.
3. Run targeted validations and synchronize docs.

**Test results**:
- Discovery/documentation session only (no code-change tests run yet).

### 2026-03-17: Implementation, validation, and closure
**Agent/Contributor**: Codex

**Work completed**:
- Implemented contrast-scenario hillslope rerun preflight in `wepppy/rq/omni_rq.py` with delete-flag gate and scenario-key dedup.
- Corrected rerun invocation to pass `cli_relpath`/`slp_relpath` from scenario runs back to base runs so existing Omni scenario workspaces without local `p*.slp` continue to work.
- Added two regression tests in `tests/rq/test_omni_rq.py` covering delete-flag on/off behavior and rerun ordering before enqueue.
- Synchronized `docs/standards/broad-exception-boundary-allowlist.md` line anchors to reflect `omni_rq.py` line shifts.
- Ran targeted and full validation suites; all pass.
- Finalized work-package documentation and closure bookkeeping.

**Blockers encountered**:
- No code blockers; only allowlist line-anchor drift after file edits.

**Validation results**:
- `wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1` -> `12 passed, 4 warnings`.
- `wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1` (post-review hardening) -> `14 passed, 4 warnings`.
- `wctl run-pytest tests/nodb/mods/test_omni_run_orchestration_service.py --maxfail=1` -> `7 passed, 2 warnings`.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> PASS.
- `wctl run-pytest tests --maxfail=1` -> `2323 passed, 34 skipped, 175 warnings`.

## Communication Log

### 2026-03-17: User request scope
**Participants**: User, Codex  
**Question/Topic**: Author a work package for Omni contrast failures when `delete_after_interchange` removes required hillslope outputs.  
**Outcome**: Scoped package created with active ExecPlan centered on `run_omni_contrasts_rq` hillslope-only rerun preflight and targeted tests.

### 2026-03-17: User requested end-to-end execution
**Participants**: User, Codex  
**Question/Topic**: Execute the authored work package end-to-end.  
**Outcome**: Implemented code/test/doc updates, completed validation gates, and closed the package.
