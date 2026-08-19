# ADR-0043: EU ESDAC Soil Quality Contract

**Status**: Proposed
**Date**: 2026-08-19
**Review Date**: Before Phase 3 production implementation
**Review Owner**: EU soil maintainer

## Context

The Phase 0 pilot sampled 1,000 valid ESDAC raster cells. Phase 1 replay
captured a valid control, a degraded land-use metadata case, zero-valued STU
data, non-increasing horizon depths, missing depth classes, missing Ksat
coverage, and categorical lookup/provider exceptions. The current builder can
write a `.sol` file for some invalid profiles or fail with an unstructured
exception for others.

The work package needs an explicit quality result before Phase 3 adds a
validation boundary. The contract must distinguish optional metadata loss from
mandatory physical or structural invalidity and must not introduce a silent
generic-soil fallback.

## Decision

Adopt the following proposed Phase 3 contract:

1. Return `valid` when all source, derived, horizon, Ksat, and serialization
   invariants pass.
2. Return `degraded` when optional land-use metadata is unavailable, or when a
   partially missing Ksat profile remains finite and model-representable. The
   warning must include field, location, raw state, and reason code.
3. Return `rejected` for provider exceptions, unsupported required categorical
   values, unreadable depth classes, all-zero mandatory STU profiles, invalid
   texture balance, nonpositive density, non-finite derived values,
   non-increasing horizons, all-missing Ksat, or nonrepresentable output.
4. Require clay/sand/silt percentages to be finite, bounded in `[0, 100]`, and
   within one percentage point of a 100-percent texture sum. This tolerance is
   for integer source quantization, not a calibration or replacement rule.
5. Allow individual zero texture components and zero gravel; reject an
   all-zero mandatory texture triad. Do not introduce an empirical density
   cutoff or an organic-matter minimum in this phase.
6. Require serialized water contents to satisfy the already accepted contract
   `0 <= wilting_point <= field_capacity <= 1` from ADR-0012.

No production code changes are included in this ADR's Phase 2 commit. Phase 3
must implement the contract at the narrowest source-to-horizon boundary and
must preserve the worker location context.

## Decision Provenance

- **Decision venue**: EU disturbed-soil hardening work-package execution
  session, 2026-08-19, America/Los_Angeles.
- **Participants present**: Codex; EU soil maintainer review required before
  Phase 3 implementation.
- **Decision owner(s)**: EU soil maintainer, to confirm the proposed
  parameterization before Phase 3 merge.
- **Implementer(s)**: Codex, subject to maintainer approval.

## Change Summary

Current behavior has no structured valid/degraded/rejected result and can
silently write decreasing horizon depths or represent an all-missing Ksat
profile with `0.001`.

Proposed behavior adds a field-qualified quality contract. It does not yet
change runtime behavior, generated files, defaults, transfer functions, or
fallback execution.

## Rationale

Structural failures are unambiguous model-input defects: a second horizon
cannot end before the first, and an all-zero mandatory STU profile cannot
produce a physically meaningful layer. Optional land-use metadata does not
invalidate the physical profile by itself, so it is observable degradation.
The one-percentage texture tolerance preserves integer percentage source data
without accepting materially incomplete texture profiles.

The contract rejects missing mandatory evidence instead of manufacturing a
generic replacement soil. This keeps the failure actionable and preserves the
distinction between upstream data quality and approved scientific fallback.

## Alternatives Considered

1. Treat every zero as invalid — rejected because zero gravel and individual
   zero texture components can be valid physical states.
2. Treat every source gap as a generic fallback — rejected because it masks
   source/version/provider defects and changes model parameterization.
3. Keep the current `0.001` all-missing Ksat representation — rejected because
   it converts missing evidence into a plausible-looking model value.
4. Reject every missing optional metadata field — rejected because the Phase 1
   control matrix shows a physically valid profile can exist with missing
   land-use metadata.
5. Add empirical density or organic-matter cutoffs now — rejected because the
   pilot does not establish calibrated domain limits and no such thresholds
   are needed to catch the confirmed failures.

## Evidence

- Work package: `docs/work-packages/20260819_eu_disturbed_soil_hardening/`.
- Phase 1 fixture:
  `tests/eu/soils/fixtures/eu_disturbed_soil_phase1.json`.
- Replay tests:
  `tests/eu/soils/test_esdac_quality_fixture.py`.
- Pilot result: 641 suspicious locations, 596 completed suspicious builds,
  35 builder exceptions, 59 horizon-order findings, and 10 controls.
- Related water-content contract: ADR-0012.

## Consequences

Phase 3 will need a structured result/error carrier and a validation boundary
before `.sol` serialization. Existing callers that expect only a soil key may
need an additive diagnostic path. Locations currently producing invalid files
will become rejected or degraded with visible reasons rather than silently
accepted.

The proposed one-percentage tolerance and Ksat policy are scientific/workflow
parameterization decisions. If the EU soil maintainer changes them, this ADR
must be amended before implementation.

## Risk and Rollback Notes

Risk: legitimate edge profiles may be rejected if their source encoding falls
outside the proposed contract. Phase 3 must retain the Phase 1 valid control,
add a valid-zero matrix, and report rejection counts as a guardrail. Rollback
is to revert the Phase 3 validation boundary while preserving the fixture and
diagnostic tests; do not restore silent fallback without a revised ADR.
