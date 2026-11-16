# Tracker - Omni MOFE Disturbed Soil Repair

> Living document tracking progress, decisions, risks, and verification.

## Quick Status

**Timezone**: UTC
**Started**: 2026-11-16 00:38 UTC
**Current phase**: Closed - locally validated
**Last updated**: 2026-11-16 00:55 UTC
**Next milestone**: Separately authorized deployment and run recovery
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

- [x] Diagnosed nested MOFE source reuse in `innovative-tailor` (2026-11-16
      00:15 UTC).
- [x] Scaffolded package and active ExecPlan (2026-11-16 00:38 UTC).
- [x] Repaired source selection in the shared MOFE producer (2026-11-16
      00:55 UTC).
- [x] Added direct repeated-generation and prepared-input evidence (2026-11-16
      00:55 UTC).
- [x] Completed focused validation and correctness review (2026-11-16
      00:55 UTC).

## Timeline

- **2026-11-16 00:38 UTC** - Package created; conformance scope and focused
  validation direction recorded.
- **2026-11-16 00:55 UTC** - Implementation, generated-artifact validation, and
  local code-delivery review completed; package closed.

## Decisions Log

### 2026-11-16 00:38 UTC: Reuse one shared producer

**Context**: Ordinary Disturbed parameterization is correct on a clean build,
but Omni invokes the same producer after `domsoil_d` points to generated MOFE
outputs.

**Options considered**:

1. Add an Omni-specific MOFE reparameterizer - duplicates scientific lookup and
   risks drift.
2. Relax the one-OFE stack validation - restores silent malformed output.
3. Make the shared producer resolve stable pre-disturbance sources - preserves
   one implementation and the accepted validation.

**Decision**: Use option 3.

**Impact**: Ordinary builds, treatments, Omni, and retries share the same
per-segment logic.

### 2026-11-16 00:38 UTC: Scope validation to the change

**Context**: The operator explicitly prohibited a full-suite run.

**Decision**: Run focused Disturbed, Treatments, Omni artifact, preparation,
and documentation checks only.

**Impact**: Closure will claim locally validated focused scope, not repository-
wide regression coverage.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Stable mapping absent in a supported legacy state | Medium | Low | Explicit source-resolution error and legacy-state test | Mitigated |
| Reusing treated output compounds multiplier replacements | High | Medium | Always resolve retained pre-disturbance source | Mitigated |
| Segment order or class lookup drifts | High | Low | Parse mixed-class generated and prepared artifacts | Mitigated |

## Hardening Signal Log

- **Baseline health signals**: ordinary base artifacts contain 1,065 correctly
  parameterized OFEs; subsequent Omni treatment builds fail at soil stacking.
- **Post-change health signals**: repeated real-writer generation and normal
  preparation produced matching, parseable three-OFE artifacts.
- **Danger signals observed**: no existing source resolver distinguishes durable
  input assignment from published MOFE assignment.
- **Temporary callus register**: none.
- **Softening experiments**: N/A.

## Verification Checklist

### Code Quality

- [x] Focused tests pass.
- [x] Changed-file broad exception enforcement passes.

### Documentation

- [x] Disturbed developer documentation updated.
- [x] Work package closure notes complete.
- [x] Scoped docs lint passes.

### Testing

- [x] Unit coverage for source resolution.
- [x] Direct real-writer integration coverage.
- [x] Ordinary first-build behavior preserved.
- [x] Legacy populated state and malformed state covered.

### Generated Artifacts

- [x] Combined and prepared soils parsed for OFE count and parameter semantics.
- [x] Direct failing writer boundary exercised unmocked.
- [x] Completion language remains below deployment/recovery.

## Progress Notes

### 2026-11-16 00:38 UTC: Scaffold and diagnosis

**Agent/Contributor**: Codex

**Work completed**:

- Confirmed current canonical contracts require one single-OFE stack member per
  final OFE and per-segment management-class/texture lookup.
- Verified the production base run's 455 hillslopes and 1,065 OFEs have zero
  count, lookup, or checked parameter mismatches.
- Confirmed `domsoil_d` points at published `hill_*.mofe` keys while
  `ssurgo_domsoil_d` retains original source keys.

**Blockers encountered**: None.

**Next steps**: Implement source resolution, add direct regression, and run the
focused validation matrix.

**Test results**: Pre-change production artifact readback only; local tests
pending.

### 2026-11-16 00:55 UTC: Implementation and closure

**Agent/Contributor**: Codex

**Work completed**:

- Added one shared resolver that selects retained single-OFE sources only after
  detecting published MOFE state.
- Kept ESDAC quality validation and component generation on the same resolved
  source key.
- Added unit and direct real-writer regressions, updated developer guidance, and
  completed the correctness evidence.

**Blockers encountered**: None.

**Next steps**: Deployment and regeneration of affected jobs require separate
operator authorization.

**Test results**: Final affected-boundary run: 34 passed; the strengthened direct
assignment-change case then passed independently. Earlier adjacent focused run:
134 passed. Broad-exception enforcement and diff check passed. No full-suite run
was performed.

## Watch List

- **Non-SSURGO soil modes**: ESDAC quality identity is covered in the final
  focused run; malformed retained state fails explicitly.
- **Existing production run**: deployment and repair are explicitly outside this
  package.

## Communication Log

### 2026-11-16 00:38 UTC: Operator direction

**Participants**: Operator, Codex
**Question/Topic**: Repair scope and implementation topology.
**Outcome**: Execute a work package, use one shared implementation, and avoid the
full test suite.
