# RUSLE K CFVO Profile-Fragment Adjustment Integration

**Status**: Closed (2026-05-07)
**Timezone**: UTC

## Overview
This package implements the deferred `cfvo` profile coarse-fragment path for RUSLE `K` in WEPPpy. The integration adds an explicit, auditable optional adjustment using SoilGrids-style `cfvo` depth layers when present, updates RUSLE specification/README contracts, and closes with code review, QA review, and findings disposition artifacts.

## Objectives
- Replace `cfvo_scope = deferred` with shipped runtime behavior.
- Apply a conservative profile-fragment adjustment that is explicit about approximation scope.
- Preserve deterministic behavior when `cfvo` inputs are unavailable.
- Record all `cfvo` policy, inputs, and outcomes in `rusle/manifest.json`.
- Update RUSLE docs and close package with QA/review disposition artifacts.

## Scope

### Included
- `wepppy/nodb/mods/rusle/k_integration.py` (`cfvo` loading, normalization, adjustment, manifest reporting).
- `wepppy/nodb/mods/rusle/k_nomograph.py` (support for explicit permeability-class override path).
- `tests/nodb/mods/test_rusle_k_integration.py` regression coverage for `cfvo` applied/unavailable modes.
- `wepppy/nodb/mods/rusle/specification.md` and `wepppy/nodb/mods/rusle/README.md` contract updates.
- Work-package tracker, ExecPlan, review artifacts, QA artifacts, and findings disposition.

### Explicitly Out of Scope
- New user-facing UI controls for `cfvo` toggles or thresholds.
- Changes to `R`, `LS`, `C`, `P`, or non-RUSLE modules.
- Full SoilGrids ingestion subsystem redesign.

## Success Criteria
- [x] Runtime manifest no longer reports `cfvo_scope: deferred`.
- [x] `cfvo` adjustment behavior is explicit and test-covered.
- [x] No-`cfvo` runs remain deterministic and backward-compatible.
- [x] Targeted RUSLE tests pass.
- [x] Documentation, code review, QA review, and findings disposition artifacts are complete.

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: numerical soil-factor preprocessing and manifest metadata only; no auth/network/privilege contract changes.
- **Security review artifact**: `N/A`

## References
- `wepppy/nodb/mods/rusle/k_integration.py`
- `wepppy/nodb/mods/rusle/k_nomograph.py`
- `tests/nodb/mods/test_rusle_k_integration.py`
- `wepppy/nodb/mods/rusle/specification.md`

## Closure Notes

**Closed**: 2026-05-07

**Summary**: Implemented shipped optional `cfvo` profile-fragment adjustment for
RUSLE `K` nomograph mode. The path now discovers run-scoped `cfvo` layers,
aligns SoilGrids Q0.5 layers from `soils/` when needed, converts SoilGrids
`cfvo` from per-mille to volumetric percent, applies conservative
permeability-class shifts, and records applied/skipped status plus source
details in `rusle/manifest.json`.

**Validation**:
- `wctl run-pytest tests/nodb/mods/test_rusle_k_integration.py --maxfail=1`
  (`10 passed`)
- `wctl run-pytest tests/nodb/mods/test_rusle_k_nomograph.py tests/nodb/mods/test_rusle_k_epic.py tests/nodb/mods/test_rusle_k_compare.py tests/nodb/mods/test_rusle_k_reference_harness.py tests/nodb/mods/test_rusle_k_integration.py tests/nodb/mods/test_rusle_controller.py --maxfail=1`
  (`31 passed`)
- `wctl run-pytest tests --maxfail=1` stopped on unrelated baseline NoDb
  failure in
  `tests/nodb/test_base_boundary_characterization.py::test_dump_forces_mtime_advance_on_unchanged_signature_then_rejects_stale_writer`
- `wctl doc-lint --path wepppy/nodb/mods/rusle/specification.md --path wepppy/nodb/mods/rusle/README.md --path docs/work-packages/20260507_rusle_k_cfvo_integration`
  (`5 files validated, 0 errors, 0 warnings`)

**Review Artifacts**:
- `artifacts/20260507_code_review.md`
- `artifacts/20260507_qa_review.md`
- `artifacts/20260507_findings_disposition.md`
