# Tracker - Iterative First-Order Link Prune WP-05 TopAZ Parity Validation

> Living document tracking progress, decisions, risks, and handoff state for WP-05 execution.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-13 08:00 UTC  
**Current phase**: Ready for Execution  
**Last updated**: 2026-04-13 08:00 UTC  
**Next milestone**: Execute active WP-05 ExecPlan in `/workdir/weppcloud-wbt`  
**Security impact**: `none`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Prepare fixture run roots with checksum-pinned manifest using WP-00 harness.
- [ ] Capture/verify TopAZ oracle rasters for all fixtures.
- [ ] Generate IFOLP candidate outputs for all fixtures in the manifest.
- [ ] Run parity comparison and produce canonical parity report.
- [ ] Re-run parity campaign to confirm determinism hash stability.
- [ ] Disposition parity mismatches (severity + root cause + fix/accept/defer).
- [ ] Run required gates and update WBT WP-05 row to `done`.
- [ ] Complete code-review findings/disposition and record outcomes.
- [ ] Move ExecPlan to `prompts/completed/` with closure note.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created WP-05 package scaffold (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`) (2026-04-13 08:00 UTC).
- [x] Authored active WP-05 ExecPlan with explicit parity scope, review gate, and acceptance criteria (2026-04-13 08:00 UTC).
- [x] Updated tracker linkage (`PROJECT_TRACKER.md` and WBT implementation-plan row) to point to WP-05 active ExecPlan (2026-04-13 08:00 UTC).

## Timeline

- **2026-04-13 08:00 UTC** - Package created and scoped.
- **2026-04-13 08:00 UTC** - Active WP-05 ExecPlan authored.
- **2026-04-13 08:00 UTC** - Linkage updated in top-level tracker and WBT implementation plan.

## Decisions Log

### 2026-04-13 08:00 UTC: Keep WP-05 focused on parity validation package scope
**Context**: WP-04 algorithm implementation is complete; parity campaign evidence is required before robustness/performance work.

**Options considered**:
1. Fold robustness hardening into parity campaign package.
2. Keep WP-05 constrained to parity execution, mismatch disposition, and deterministic evidence.

**Decision**: Option 2.

**Impact**: Maintains package boundaries and keeps WP-06/WP-07 dependent on validated parity outcomes.

### 2026-04-13 08:00 UTC: Require formal findings disposition as a parity closure gate
**Context**: Parity mismatches can be subtle and recur without explicit triage discipline.

**Options considered**:
1. Treat parity as pass/fail only.
2. Require formal severity + root-cause disposition for every mismatch and review finding.

**Decision**: Option 2.

**Impact**: Improves traceability of parity claims and reduces risk of unresolved medium/high defects.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Candidate runner output contract drifts from comparison harness expectations | High | Medium | Validate candidate output paths/geometry against manifest before comparison | Open |
| False parity confidence from single-run nondeterminism | High | Medium | Require canonical report hash equality across at least two reruns | Open |
| Mismatch triage remains ambiguous without reproducible evidence | Medium | Medium | Require fixture-level evidence and explicit disposition for each mismatch | Open |

## Verification Checklist

### Package Governance
- [x] Package scaffold follows `docs/work-packages/README.md` layout.
- [x] Active ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
- [x] Tracker/linkage updated for current lifecycle state.

### WP-05 Completion (pending execution)
- [ ] Parity campaign executed on full fixture set.
- [ ] Determinism rerun evidence recorded.
- [ ] Mismatch and review findings dispositioned.
- [ ] `cargo check -p whitebox_tools` passes.
- [ ] WBT WP-05 orchestration row marked `done`.

## Progress Notes

### 2026-04-13 08:00 UTC: WP-05 package and prompt setup
**Agent/Contributor**: Codex

**Work completed**:
- Created WP-05 package scaffold in `docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/`.
- Authored active WP-05 ExecPlan for execution-agent handoff.
- Updated project tracker lifecycle alignment (WP-04 moved to Done summary; WP-05 added as In Progress).
- Updated WBT implementation-plan WP-05 row note with active ExecPlan path.

**Blockers encountered**:
- None.

**Next steps**:
- Dispatch execution agent with active WP-05 ExecPlan.
- Execute WP-05 parity campaign end-to-end in `/workdir/weppcloud-wbt`.

**Test results**:
- Package-setup session; no new WP-05 parity runs executed in this step.
