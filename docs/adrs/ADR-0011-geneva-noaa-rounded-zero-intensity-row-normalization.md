# ADR: Geneva NOAA Rounded-Zero Intensity Row Normalization

Status: Accepted
Date: 2026-06-30

## Context

Geneva frequency-panel builds consume NOAA Atlas 14 partial-duration intensity
exports from `climate/atlas14_intensity_pds_mean_metric.csv`. The Rust kernel
requires every parsed NOAA intensity to be finite and greater than zero before
materializing the requested duration/ARI cells.

The run `incomparable-gracefulness` failed in the
`geneva_build_frequency_panel` task because the source NOAA CSV contained
rounded zero intensities in long-duration rows:

- `7-day:, 0,0,1,...`
- `10-day:, 0,0,0,0,1,...`
- longer rows with all zeros.

The default Geneva frequency panel requests durations from 5 minutes through
24 hours. The failing 7-day row was outside the default requested duration set,
but the kernel validates the full source matrix before filtering to requested
cells.

## Decision

Geneva will normalize NOAA Atlas 14 intensity CSVs before calling the kernel.
When the NOAA frequency table contains a duration row with any non-finite or
non-positive intensity value, the Python service will omit that entire duration
row from a kernel-specific normalized copy:

`geneva/normalized_sources/atlas14_intensity_pds_mean_metric_kernel.csv`

The original NOAA file remains unchanged. Valid NOAA rows and metadata are
preserved in the normalized copy.

## Decision Provenance (Required for Parameterization Changes)

Decision Venue: Codex task from operator report, 2026-06-30 America/Los_Angeles  
Participants Present: WEPPcloud operator/user, Codex coding agent  
Decision Owner(s): WEPPcloud operator/user  
Implementer(s): Codex coding agent

## Change Summary

Old behavior:

- The kernel parsed every NOAA frequency row in the source CSV.
- Any rounded zero or non-finite NOAA intensity caused the whole
  frequency-panel build to fail, even when that duration was not requested.

New behavior:

- `GenevaFrequencyPanelService` creates a kernel-specific NOAA copy when it
  detects invalid intensity rows.
- The copy omits duration rows containing any non-finite or non-positive
  intensity value.
- Requested cells for omitted durations use the existing unavailable-cell
  contract, such as `duration_unavailable`, instead of aborting the full panel.

## Rationale

Rounded zero NOAA intensity values do not satisfy Geneva's positive-intensity
contract and should not be converted to artificial epsilon values. Omitting the
unusable duration row keeps the source strict, preserves positive NOAA values
unchanged, and lets the existing frequency-panel availability contract represent
the missing duration.

The normalization belongs in the Python source adapter because it is specific
to the NOAA export shape and run-scoped artifact management. The Rust kernel can
continue enforcing a simple invariant: parsed available cells must be positive
and finite.

## Alternatives Considered

1. Replace zero intensities with a small positive value - rejected because it
   would invent rainfall intensity and could silently affect model results.
2. Relax the Rust kernel to accept zero intensities - rejected because zero
   intensity cannot produce an available positive-depth event under the current
   frequency-panel contract.
3. Filter only rows outside the requested duration set - rejected because a row
   with mixed invalid and positive ARI values cannot be represented partially by
   the current NOAA CSV/kernel contract.
4. Leave behavior unchanged - rejected because valid default Geneva workflows
   can fail on irrelevant long-duration NOAA rows.

## Consequences

Geneva frequency-panel builds will proceed when NOAA exports contain rounded
zero long-duration rows. Panels that explicitly request an omitted duration
will mark those NOAA cells unavailable rather than available.

The normalized source artifact is run-scoped and reproducible from the original
NOAA CSV. Existing completed Geneva artifacts are unchanged until the
frequency-panel task is rebuilt.

## Evidence

- Failed job:
  `6b69a952-ae87-4e58-b463-9876e58dc627`.
- Workflow correlation:
  `94b6932c-fafe-4c56-9690-972f56cd9301`.
- Run:
  `/wc1/runs/in/incomparable-gracefulness`.
- Source:
  `/wc1/runs/in/incomparable-gracefulness/climate/atlas14_intensity_pds_mean_metric.csv`.
- Regression tests:
  `tests/nodb/mods/geneva/test_geneva_schema_contracts.py::test_noaa_normalization_omits_non_positive_intensity_rows_for_kernel`.
  `tests/nodb/mods/geneva/test_geneva_collaborators.py::test_frequency_panel_service_passes_normalized_noaa_source_to_kernel`.

## Risk and Rollback Notes

Risk: A user requesting a long NOAA duration with mixed zero and positive ARI
values will see the whole duration marked unavailable, including positive ARI
cells in the omitted row.

Rollback: remove the NOAA normalization call and delete this ADR. Use rollback
only if the kernel contract is extended to represent per-cell missing values in
NOAA source rows or if NOAA source generation stops emitting rounded zero rows.

## Implementation Notes

The service intentionally does not alter the original NOAA file. The normalized
copy is only passed to `geneva_build_frequency_panel`; it is safe to regenerate
on every rebuild.
