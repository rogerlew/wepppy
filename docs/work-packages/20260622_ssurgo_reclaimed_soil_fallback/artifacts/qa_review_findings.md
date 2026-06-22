# QA Review Findings - SSURGO Reclaimed Soil Conversion and Fallback Transparency

**Status**: Completed
**Created**: 2026-06-22 18:28 UTC
**Reviewed**: 2026-06-22 20:27 UTC

## Review Scope

QA review must cover:

- Fairpoint MUKEY regression coverage for `3294459`, `3294460`, and `3294461`.
- First-horizon restrictive-layer behavior and generated `.sol` outputs.
- Invalid-MUKEY fallback transparency and backward compatibility.
- Documentation and ADR completeness.

## Findings

### QA-1: Restrictive-layer scan still considered invalid low-ksat horizons

**Severity**: Medium
**Status**: Accepted and fixed
**Files**: `wepppy/soils/ssurgo/ssurgo.py`,
`tests/soils/test_ssurgo_reclaimed_fairpoint.py`

During review, `_analyze_restrictive_layer()` retained the first valid
low-ksat horizon, but it still allowed invalid low-ksat horizons to trigger a
restrictive break. That was inconsistent with the documented "valid horizons"
algorithm and could still produce zero-layer profiles when invalid horizons
preceded valid ones.

Disposition: fixed by skipping invalid horizons during restrictive-layer
analysis. Added
`test_invalid_low_ksat_horizon_does_not_trigger_zero_layer_profile`.

### QA-2: Full-suite validation stops at unrelated route test

**Severity**: Low for this package
**Status**: Deferred as unrelated blocker
**Files**: `tests/weppcloud/routes/test_wepp_bp.py`,
`wepppy/weppcloud/routes/nodb_api/wepp_bp.py`

`wctl run-pytest tests --maxfail=1` reached 4,425 passing tests and 59 skipped
tests, then stopped at
`test_view_management_effective_returns_texture_specific_preview[clay-...]`.
The same test fails standalone, and neither the route nor the test file has a
local diff in this work package.

Disposition: documented as an unrelated existing blocker. Package-targeted
tests, docs, stub hygiene, py_compile, and changed-file exception gates pass.

### QA-3: ADR needed explicit Tahoe precedent rationale

**Severity**: Low
**Status**: Accepted and fixed
**Files**: `docs/adrs/ADR-0008-ssurgo-reclaimed-soil-restrictive-layer-fallback.md`,
`docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/tracker.md`,
`docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/prompts/active/ssurgo_reclaimed_soil_fallback_execplan.md`,
`docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/package.md`

After the initial QA pass, operator review asked why the original Erin
Brooks/Lake Tahoe workflow excluded restrictive layers. The ADR had the
Fairpoint behavior decision but did not yet record the historical Tahoe
interpretation.

Disposition: fixed by amending ADR-0008 to distinguish Tahoe-style
lower-boundary restrictive material below a modeled soil mantle from reclaimed
profiles whose first valid horizon is already low-conductivity. The work
package now also references the Brooks et al. paper and records local
comparison-run evidence.

## Disposition

All QA findings are dispositioned. There are no open package-blocking QA
findings.
