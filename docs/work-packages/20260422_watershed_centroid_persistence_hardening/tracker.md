# Tracker - Watershed Centroid Persistence Hardening for Climate Build Reliability

> Living document tracking progress, decisions, risks, and handoff context for centroid durability hardening.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-23 01:33 UTC  
**Current phase**: Implementation complete; package validation/handoff complete (global suite blocked externally)  
**Last updated**: 2026-04-23 02:12 UTC  
**Next milestone**: Resolve unrelated Geneva worktree regression, rerun global gate, then mark package closed  
**Security impact**: `none`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [x] Full-suite sanity gate blocked by unrelated existing Geneva failure (`tests/nodb/mods/geneva/test_geneva_wp09_end_to_end.py::test_wp09_watershed_warning_thresholds_propagate_to_results_query_report[...]`, `KeyError: 'severity'`).

### Done
- [x] Work-package scaffold created (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `notes`, `artifacts`) (2026-04-23 01:33 UTC).
- [x] Package brief authored with scope boundaries, compatibility plan, and success criteria (2026-04-23 01:34 UTC).
- [x] Active ExecPlan authored for implementation milestones and validation gates (2026-04-23 01:35 UTC).
- [x] Root `PROJECT_TRACKER.md` updated with new in-progress package entry (2026-04-23 01:37 UTC).
- [x] Implemented watershed repair-or-fail centroid accessor + typed `WatershedCentroidStateError` in `wepppy/nodb/core/watershed_mixins.py` and `wepppy/nodb/core/watershed.py` (2026-04-23 02:03 UTC).
- [x] Migrated climate/station centroid consumers to `require_centroid()` in `wepppy/nodb/core/climate.py` and `wepppy/nodb/core/climate_station_catalog_service.py` (2026-04-23 02:04 UTC).
- [x] Implemented NoDb stale-write rejection at `NoDbBase.dump()` with typed `NoDbStaleWriteError` (2026-04-23 02:05 UTC).
- [x] Implemented post-`abstract_watershed_rq` durability verification with one bounded repair attempt in `wepppy/rq/project_rq.py` (2026-04-23 02:06 UTC).
- [x] Added regression coverage for centroid self-heal/fail, stale overwrite rejection, and RQ durability behavior (2026-04-23 02:11 UTC).
- [x] Added lock-boundary/cache-signature hardening (`NoDbBase.locked()` unlock-on-dump-failure and Redis hydrate mtime/size stamping) required by stale-write enforcement (2026-04-23 02:12 UTC).
- [x] ExecPlan, package tracker, and root tracker updated with implementation + validation evidence (2026-04-23 02:12 UTC).

## Timeline

- **2026-04-23 01:33 UTC** - Package initiated from production incident analysis and user request.
- **2026-04-23 01:35 UTC** - Active ExecPlan drafted.
- **2026-04-23 01:37 UTC** - Root tracker registration completed.
- **2026-04-23 02:06 UTC** - Completed core implementation milestones for centroid hardening, stale-write guard, and RQ durability verification.
- **2026-04-23 02:11 UTC** - Targeted package regressions passed (`43 passed`).
- **2026-04-23 02:12 UTC** - Full-suite gate blocked by unrelated Geneva failure in dirty worktree.

## Decisions Log

### 2026-04-23 01:33 UTC: Prioritize repair-or-fail centroid contract before broader refactors
**Context**: Observed climate failures stem from nullable centroid state after apparently successful watershed jobs.

**Options considered**:
1. Add sleeps/retries around climate execution only.
2. Harden centroid state contract and persistence durability boundaries.
3. Add operator-only manual repair guidance without code changes.

**Decision**: Option 2.

**Impact**: Fix targets root contract integrity and prevents recurrence across climate call sites.

---

### 2026-04-23 01:34 UTC: Keep contract evolution additive and avoid key/column removals
**Context**: Existing run artifacts and downstream readers may depend on current keys/columns.

**Options considered**:
1. Redesign watershed serialization format broadly.
2. Add bounded self-heal and stale-write guard while preserving current schema shape.

**Decision**: Option 2.

**Impact**: Lower migration risk and faster deployability with focused regression coverage.

---

### 2026-04-23 02:12 UTC: Keep stale-write guard strict and harden lock/cache boundaries
**Context**: Stale-write rejection surfaced lock-leak and cache-signature drift edge cases under existing NoDb lock/cache plumbing.

**Options considered**:
1. Relax stale-write guard behavior to reduce regressions.
2. Keep strict guard and patch lock/cache boundaries to eliminate false-positive pathways.

**Decision**: Option 2.

**Impact**: Maintains explicit stale-overwrite rejection while restoring compatibility for existing lock/cache flows.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Stale-write guard rejects legitimate writes in edge race scenarios | High | Medium | Added strict mtime/size detection plus lock-boundary/cache-signature hardening and targeted stale-write regression | Mitigated |
| Self-heal logic masks underlying upstream defects | Medium | Medium | Typed failure path preserved; repair bounded and explicit in logs/tests | Mitigated |
| Climate path changes alter existing exception contract unexpectedly | Medium | Medium | `require_centroid()` migration validated with targeted climate/station/RQ tests | Mitigated |
| Queue path verification adds overhead or flakes | Low | Low | One bounded repair attempt with typed hard fail; covered in `tests/rq/test_project_rq_mutation_guards.py` | Mitigated |
| Full-suite validation blocked by unrelated Geneva failure | Medium | High | Track blocker at `tests/nodb/mods/geneva/test_geneva_wp09_end_to_end.py::test_wp09_watershed_warning_thresholds_propagate_to_results_query_report[...]`; rerun global gate after external fix | Open |

## Verification Checklist

### Code Quality
- [x] Changed Python tests pass for NoDb/RQ/climate areas.
- [x] No new broad exception handlers introduced in changed production paths.
- [x] Error messages include run/context needed for operator triage.

### Documentation
- [x] Work-package docs initialized and linked.
- [x] Relevant contract docs updated for centroid repair/failure semantics (ExecPlan + package tracker + root tracker).
- [x] Tracker/decision log updated at each milestone stop.

### Testing
- [x] Test: centroid missing + artifacts present repairs and proceeds.
- [x] Test: centroid missing + artifacts missing raises typed state error.
- [x] Test: stale instance write attempt is rejected and does not clobber newer state.
- [x] Test: `abstract_watershed_rq` durability verification catches incomplete persisted state.
- [x] Test: climate build failure mode transitions from raw `TypeError` to contract-compliant behavior.

### Deployment/Operational
- [ ] Validate incident run replay path (`immodest-quick` pattern) using staged/local fixture or equivalent reproducible test.
- [x] Document operator recovery path for already-bad runs (repair-or-fail contract + one bounded RQ repair attempt recorded in plan/tracker docs).

## Progress Notes

### 2026-04-23 01:33 UTC: Package authoring session
**Agent/Contributor**: Codex

**Work completed**:
- Created new work package for watershed centroid persistence hardening.
- Recorded objective to harden both read-side centroid contract and write-side NoDb durability behavior.
- Added explicit scope around climate call-site updates, stale-write protection, and RQ post-abstraction verification.
- Authored active ExecPlan and linked package in root project tracker.

**Blockers encountered**:
- None during authoring.

**Next steps**:
1. Implement centroid repair-or-fail accessor and migrate climate/station call sites.
2. Implement stale-write rejection and persistence boundary tests.
3. Implement and test post-abstraction durability verification in RQ path.

**Test results**:
- Docs-only session; no runtime tests executed.

### 2026-04-23 02:12 UTC: Implementation + validation session
**Agent/Contributor**: Codex

**Work completed**:
- Implemented watershed centroid repair/fail accessor + typed failure, migrated climate/station consumers to hardened centroid access, and added RQ post-abstraction durability verification with one bounded repair attempt.
- Implemented stale-write rejection at NoDb persistence boundary and added required stale-overwrite regression coverage.
- Patched NoDb lock/cache boundaries (`locked()` unlock-on-dump-failure, Redis hydrate signature stamping) so strict stale-write enforcement does not leave stale locks or stale signatures.
- Updated living docs (`ExecPlan`, package tracker, root tracker) with progress, decisions, outcomes, and validation evidence.

**Blockers encountered**:
- `wctl run-pytest tests --maxfail=1` blocked by unrelated existing Geneva failure in a dirty worktree (`KeyError: 'severity'`).

**Next steps**:
1. Fix the unrelated Geneva failure in the existing worktree.
2. Re-run `wctl run-pytest tests --maxfail=1`.
3. Mark package closed in root tracker once global gate clears.

**Test results**:
- `wctl run-pytest tests/nodb/mods/disturbed/test_sbs_validation.py::TestColorTablePreservation::test_get_sbs_preserves_color_table tests/nodb/test_watershed_runtime_contract.py tests/nodb/test_base_boundary_characterization.py tests/nodb/test_climate_station_catalog_service.py tests/nodb/test_climate_facade_collaborators.py tests/rq/test_project_rq_mutation_guards.py --maxfail=1` -> `43 passed`.
- `wctl run-pytest tests --maxfail=1` -> failed at unrelated Geneva test `tests/nodb/mods/geneva/test_geneva_wp09_end_to_end.py::test_wp09_watershed_warning_thresholds_propagate_to_results_query_report[...]` (`KeyError: 'severity'`).

## Communication Log

### 2026-04-23 01:33 UTC: User request to author work package
**Participants**: User, Codex  
**Question/Topic**: Create a work package to execute centroid/persistence hardening fixes after production climate failures.  
**Outcome**: New package scaffolded with package brief, tracker, active ExecPlan, and root tracker registration.
