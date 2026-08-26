# Tracker - Batch OMNI Multi-OFE Treatment Propagation

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-06 19:30 UTC
**Current phase**: Closed
**Last updated**: 2026-08-06 20:05 UTC
**Next milestone**: Production deployment and affected-run rebuild (outside package)
**Security impact**: `none`
**Dedicated security review**: `no`
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Production failure boundary confirmed on `wepp1` (2026-08-06 19:26 UTC).
- [x] Work package and active ExecPlan scaffolded (2026-08-06 19:30 UTC).
- [x] Segment-aware treatment propagation implemented (2026-08-06 19:43 UTC).
- [x] Generated WEPP management propagation regression added (2026-08-06 19:45 UTC).
- [x] NoDb and full repository gates passed (2026-08-06 20:05 UTC).
- [x] Documentation and work package closed (2026-08-06 20:05 UTC).

## Timeline

- **2026-08-06 19:26 UTC** - Confirmed treatment keys reached `domlc_d` but not
  `domlc_mofe_d` or generated WEPP management inputs.
- **2026-08-06 19:30 UTC** - Package created and implementation started.
- **2026-08-06 20:05 UTC** - All validation passed and package closed.

## Decisions Log

### 2026-08-06 19:30 UTC: Treat each OFE according to its own class

**Context**: A selected hillslope may contain multiple land-cover classes.

**Options considered**:

1. Replace every OFE with the hillslope-level treatment key - simple but erases
   heterogeneous segments.
2. Apply the treatment eligibility rules independently to each OFE - preserves
   the multi-OFE land-cover contract.

**Decision**: Apply the treatment independently to each OFE and preserve any
segment for which the treatment is not applicable.

**Impact**: The implementation needs a segment-aware mutation seam and must
regenerate synthesized multi-OFE management and soil files.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Treatment overwrites shrub/grass OFEs on mixed hillslopes | High | Medium | Mixed-OFE regression asserting preservation | Closed |
| Stale synthesized management file survives mapping update | High | Medium | Generated-file content regression | Closed |
| Single-OFE behavior regresses | Medium | Low | Existing and explicit single-OFE tests | Closed |

## Hardening Signal Log

- **Baseline health signals**: 1,417 treatment selections logged but all 1,434
  generated management files identical across scenarios.
- **Post-change health signals**: eligible OFE keys change; unrelated segments
  remain unchanged; synthesized and WEPP run management files contain treatment
  cover markers in regression fixtures.
- **Danger signals observed**: none in targeted, NoDb, or full repository gates.
- **Temporary callus register**: none.
- **Softening experiments**: none.

## Verification Checklist

### Code Quality

- [x] Targeted tests pass.
- [x] Full tests pass (`wctl run-pytest tests --maxfail=1`).
- [x] Changed broad-exception gate passes.

### Security

- [x] Security impact triage recorded with rationale.
- [x] No attack-surface change is in scope.

### Documentation

- [x] Batch Runner documentation updated.
- [x] Work package closure notes complete.
- [x] Parameterization ADR not required.

### Testing

- [x] Unit coverage for mixed multi-OFE mutation.
- [x] Generated `wepp/runs/*.man` propagation evidence.
- [x] Backward compatibility verified for single-OFE paths.

### Deployment

- [x] Deployment not included; operator follow-up documented.

## Progress Notes

### 2026-08-06 19:30 UTC: Production diagnosis and package start

**Agent/Contributor**: Codex

**Work completed**:

- Confirmed the failure on `wepp1` without modifying production state.
- Identified stale `domlc_mofe_d` and `hill_*.mofe.man` as the propagation break.
- Scaffolded this work package and active ExecPlan.

**Blockers encountered**: None.

**Next steps**:

- Add failing regressions, implement the smallest segment-aware fix, and validate.

**Test results**: Not started.

### 2026-08-06 20:05 UTC: Implementation and closure

**Agent/Contributor**: Codex

**Work completed**:

- Added OFE-local thinning, prescribed-fire, and mulch mutation.
- Rebuilt multi-OFE management and disturbed-soil artifacts after mutation.
- Added generated `wepp/runs/*.man` propagation coverage and operator docs.

**Blockers encountered**: None.

**Next steps**: Deploy normally and rebuild affected production scenarios.

**Test results**: 33 focused tests passed; 1,559 NoDb tests passed with 26
skipped; final full gate passed with 5,895 tests, 61 skipped, 1,048 warnings,
and 12 passing subtests.

## Watch List

- **Soil regeneration**: Ensure treatment-related soil replacement follows the
  treated OFE mapping and is not limited to the scalar hillslope mapping.

## Communication Log

### 2026-08-06 19:30 UTC: Operator authorization

**Participants**: User, Codex
**Question/Topic**: Add multi-OFE support to the Batch Runner OMNI scenario path.
**Outcome**: User explicitly requested scaffolding and end-to-end execution.
