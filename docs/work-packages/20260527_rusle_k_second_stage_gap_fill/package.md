# RUSLE K Conservative Second-Stage Gap Fill

**Status**: Closed (2026-05-28)
**Timezone**: UTC

## Overview

This package extends the existing conservative POLARIS small-hole fill by
adding a second-stage fill pass for medium interior gaps that remain after
stage-1. The goal is to reduce visibly spotty off-channel `K` coverage while
preserving conservative behavior and provenance.

## Objectives

- Reduce residual off-channel `K` nodata islands that persist after stage-1
  small-hole fill.
- Keep second-stage behavior conservative (bounded component size, bounded
  candidate fraction, bounded search distance).
- Preserve explicit non-fill behavior for edge-connected and large unresolved
  voids.
- Expose stage-2 policy/results in `rusle/manifest.json` for auditability.
- Add focused regressions and update RUSLE docs/specification.

## Scope

### Included

- `wepppy/nodb/mods/rusle/k_integration.py` second-stage conservative
  gap-fill implementation and manifest reporting.
- `tests/nodb/mods/test_rusle_k_integration.py` regression coverage for
  stage-2 fill-applied and stage-2 skip paths.
- `wepppy/nodb/mods/rusle/specification.md` contract updates for two-stage
  fill policy.
- `wepppy/nodb/mods/rusle/README.md` user/developer-facing behavior updates.
- Parameterization ADR documenting threshold/policy changes.

### Explicitly Out of Scope

- Changes to `R`, `LS`, `C`, or `P` equations.
- New UI knobs for gap-fill tuning.
- External data source changes for POLARIS acquisition.
- New dependencies.

## Success Criteria

- [x] Stage-1 behavior remains unchanged for small interior holes.
- [x] Stage-2 fills only bounded medium interior holes; edge-connected and very
  large holes remain unfilled.
- [x] Manifest records both stage-1 and stage-2 policy/outcomes per property.
- [x] Targeted RUSLE K tests pass.
- [x] Specification/README/work-package docs are updated and internally
  consistent.

## Parameterization ADR Gate

- **Parameterization change present**: `yes`
- **ADR required**: `yes`
- **ADR link(s)**: `docs/adrs/ADR-0005-rusle-k-second-stage-gap-fill.md`
- **Decision provenance captured**: `yes`

Reference: `docs/standards/parameterization-adr-standard.md`

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: Numerical raster preprocessing only; no
  auth/session/secrets/egress changes.
- **Security review artifact**: `N/A`

## Related Packages

- **Related**: [20260507_rusle_k_polaris_gap_fill](../20260507_rusle_k_polaris_gap_fill/package.md)
- **Related**: [20260507_rusle_k_cfvo_integration](../20260507_rusle_k_cfvo_integration/package.md)

## References

- `wepppy/nodb/mods/rusle/k_integration.py`
- `tests/nodb/mods/test_rusle_k_integration.py`
- `wepppy/nodb/mods/rusle/specification.md`
- `docs/adrs/ADR-0005-rusle-k-second-stage-gap-fill.md`

## Closure Notes

**Closed**: 2026-05-28

**Summary**: Implemented two-stage conservative nodata fill for RUSLE POLARIS
`K` preprocessing. Stage-1 keeps existing behavior (`1-64` px, `<=10%`,
search `6` px). Stage-2 fills medium residual interior components
(`65-4096` px, `<=5%`, search `12` px). Manifest reporting now includes
stage-specific policy and outcomes, with backward-compatible stage-1 top-level
keys retained.

**Validation**:
- `wctl run-pytest tests/nodb/mods/test_rusle_k_integration.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/test_rusle_controller.py --maxfail=1`
- `wctl doc-lint --path ...` for changed docs and tracker artifacts

**Review Artifacts**:
- `artifacts/20260528_independent_review.md`
- `artifacts/20260528_findings_disposition.md`
