# Validation Summary - Peridot Side Hillslope Length Capping

**Timestamp (UTC)**: 2026-04-23 01:47 UTC
**Author**: Codex

## Scope
Validated implementation of side-hillslope (`topaz_id % 10 in {2,3}`) length selection cap and additive provenance fields across non-representative and representative watershed abstractions.

## Behavior Contract Confirmed
- Side hillslopes now compute:
  - `L_area = area / channel_length`
  - `L_edge = median edge/source flowpath length` (if available)
  - `L_final = min(L_area, L_edge)` when `L_edge` is valid, else `L_area`
- Width is recomputed from selected length in both paths: `width = area / L_final`.
- Top/source hillslopes (`topaz_id % 10 == 1`) remain on pre-existing behavior paths.
- Additive hillslope provenance fields are emitted:
  - `length_estimate_mode`
  - `length_area_over_channel`
  - `length_edge_median`

## Targeted Test Commands and Results
Working directory: `/workdir/peridot`

1. `cargo test --test hillslope_slope_scalar -- --nocapture`
   - Result: PASS (`2 passed; 0 failed`)
2. `cargo test representative_hillslope_length_modes_follow_selection_contract -- --nocapture`
   - Result: PASS (`1 passed; 0 failed`)
3. `cargo test --test watershed_parquet_manifest -- --nocapture`
   - Result: PASS (`3 passed; 0 failed`)
4. `cargo test side_length_selection -- --nocapture`
   - Result: PASS (`3 passed; 0 failed`)

## Documentation Updates Validated
- Peridot watershed manifest/schema and README updated for new additive hillslope fields.
- WEPPpy output contract docs updated:
  - `docs/dev-notes/data_tables_standardization.spec.md`
  - `docs/schemas/output-scope-contract.md`

## Residual Risk
- Full run-level before/after evidence for the exact `topaz_id=11132` case is not included in this validation artifact.
- Unit/integration tests cover selection semantics and area invariants; optional follow-up is to record a watershed-run diagnostic table for analyst review.
