# Outcome - Peridot Side-Hillslope Length Capping ExecPlan

**Closed**: 2026-04-23 03:00 UTC
**ExecPlan**: `prompts/completed/peridot_side_hillslope_length_capping_execplan.md`

## Completed Outcomes
- Implemented side-hillslope length capping (`L_final = min(L_area, L_edge)`) for side hillslopes (`topaz_id % 10 in {2,3}`) in both non-representative and representative abstraction flows.
- Preserved top/source hillslope behavior (`topaz_id % 10 == 1`).
- Added additive provenance fields to hillslope outputs:
  - `length_estimate_mode`
  - `length_area_over_channel`
  - `length_edge_median`
- Updated Peridot watershed schema/manifest surfaces and WEPPpy output-contract docs.
- Added regression coverage for cap activation, fallback/no-edge behavior, area preservation, and representative/non-representative side-mode parity.

## Validation Summary
- Targeted Peridot test suite for this change passed:
  - `cargo test --test hillslope_slope_scalar -- --nocapture`
  - `cargo test representative_hillslope_length_modes_follow_selection_contract -- --nocapture`
  - `cargo test --test watershed_parquet_manifest -- --nocapture`
  - `cargo test side_length_selection -- --nocapture`
- Package and touched contract docs passed `wctl doc-lint`.

## Residuals / Follow-up
- A dedicated run-level before/after artifact for the exact screenshot case (`topaz_id=11132`) was left as optional follow-up and is now superseded by the new MOFE segmentation performance package requested by the user.
