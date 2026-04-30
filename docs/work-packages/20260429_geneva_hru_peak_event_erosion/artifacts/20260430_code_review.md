# Code Review - Geneva HRU Peak Runoff and Choropleth Measure

Date: 2026-04-30 (UTC)
Reviewer: Codex
Scope:
- `/workdir/wepppyo3/geneva_core/src/cn.rs`
- `/workdir/wepppyo3/cli_revision/src/geneva/mod.rs`
- `wepppy/nodb/mods/geneva/collaborators/hru_event_measure_service.py`
- `wepppy/nodb/mods/geneva/schemas/query_schema.py`
- Geneva route/UI integration files and tests

## Focus Areas

- Rust response compatibility and backward-safe additive fields.
- Correct HRU-local peak derivation path (no watershed area split).
- Python materialization/query regressions.

## Findings

No medium/high correctness findings.

### Closed checks

- `HruExcessSeries` contract was extended additively with scalar fields only:
  - `peak_runoff_m3_s`
  - `time_to_peak_minutes`
- HRU-local peak computation is derived from per-HRU incremental excess + area via existing `convolve_excess_to_hydrograph` and selected unit hydrograph.
- One-HRU parity and multi-HRU anti-area-split tests were added and passing.
- PyO3 bridge test now asserts new fields in `geneva_run_batch` JSON.
- WEPPpy materialization reads `peak_runoff_m3_s` directly and writes `measure_id=hru_peak_runoff` (`unit=m3_s`), preserving existing `runoff_depth` and `runoff_volume` behavior.
- HRU map scope validation now admits `hru_peak_runoff` while still rejecting `peak_discharge`.

## Residual Risks

- Existing repo-wide frontend lint baseline remains unrelated to this package and was documented in validation artifact.
- Runs created before this feature may not include `hru_peak_runoff` rows; current query path returns an empty available record set for that measure in those artifacts.
