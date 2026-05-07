# Findings Disposition - RUSLE K CFVO Integration

**Date**: 2026-05-07

## Reviewer/QA Findings and Disposition

1. **High** - CFVO normalization may mis-scale low values (`<=100`) by 10x.
- **Disposition**: Fixed.
- **Changes**:
  - CFVO normalization now supports source-aware policy with explicit SoilGrids per-mille conversion path.
  - For run-scoped SoilGrids CFVO sources, conversion is always `/10`, then clipped to `[0, 100]`.
  - Added regression test for low-value permille path to prove no false class shifts.
- **Evidence**:
  - `tests/nodb/mods/test_rusle_k_integration.py` (`test_run_rusle_k_factors_cfvo_permille_values_below_100_do_not_shift_classes`) passes.

2. **Medium** - Optional CFVO processing could fail whole run on malformed CFVO files.
- **Disposition**: Fixed.
- **Changes**:
  - Added narrow optional-boundary exception handling (`RasterioError`, `OSError`, `ValueError`) in CFVO load path.
  - Failures now downgrade to `not_applied` with `cfvo_layer_processing_failed` reason in manifest.
- **Evidence**:
  - `tests/nodb/mods/test_rusle_k_integration.py` (`test_run_rusle_k_factors_cfvo_processing_failure_is_optional_skip`) passes.

3. **Medium** - Invalid mode validation occurred after side-effectful CFVO staging.
- **Disposition**: Fixed.
- **Changes**:
  - Moved `selected_modes`/`default_k_mode` validation ahead of optional CFVO loading/alignment.
  - Added regression asserting no `polaris/cfvo_mean_*` staging on invalid mode.
- **Evidence**:
  - `tests/nodb/mods/test_rusle_k_integration.py` (`test_run_rusle_k_factors_invalid_mode_does_not_stage_cfvo_side_effects`) passes.

4. **Medium (coverage gap)** - Missing branch tests for CFVO edge states.
- **Disposition**: Fixed.
- **Changes**:
  - Added branch tests for:
    - `available_no_change` status,
    - aligned CFVO reuse path,
    - processing-failure optional fallback,
    - invalid-mode side-effect guard.

## Final Disposition Summary

- High findings: fixed
- Medium findings: fixed
- Open blocker findings: none
