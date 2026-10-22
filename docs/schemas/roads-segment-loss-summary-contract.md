# Roads segment loss summary

Status: implemented after independent contract checkpoint `bac3042b1` (2026-10-22).

## Scope and attribution

`wepp/roads/output/interchange/roads_segment_loss_summary.parquet` is a continuous
simulation diagnostic with one row per completed manifest `segment_run_id`.
Use original segment/profile PASS records in native-generated `H.pass.parquet`,
selected by that ID, and stationary local OFE areas in `H.wat.parquet`.
Never join or substitute receiving-hillslope `loss_pw0.hill.parquet` values.
`target_hillslope_wepp_id` is routing context only. Multiple profiles belonging
to one uploaded segment remain distinct rows. Replacement remainder profiles
remain visible and explicitly labeled; this is not an incremental road-effect
or watershed-outlet table. Single-storm behavior remains unchanged (no summary).

## Annual values and units

Let N be the persisted climate `input_years` used by Roads profile execution.
For populated summaries require a positive N, exactly N distinct source years,
and agreement with `calendar_start_year` when that persisted value is available.
For supported legacy climates without a calendar start, use the first source
year as start while still requiring the persisted N; never infer N from event
years or silently admit missing execution duration. Empty manifests need no
source calendar. Include NO EVENT days and zero-export years. Each selected profile must
have the same unique date sequence; missing/duplicate dates or unequal record
coverage fail. Each year must contain 365 or 366 daily records with julian 1 through that year's record count,
years must be consecutive, and global sim_day_index must be contiguous starting
at 1. Selected WAT and PASS date tuples must agree. Honor native/CLI calendars;
do not reconstruct Gregorian leap rules to reject supported native calendars. Do not divide by event years only. These are mean annual values:

- `runoff_volume_m3`: sum(runvol)/N.
- `subrunoff_volume_m3`: sum(sbrunv)/N.
- `baseflow_volume_m3`: sum(gwbfv)/N, the profile's native PASS groundwater output,
  not the watershed TotalWatSed reservoir or routed channel baseflow.
- `soil_loss_kg`: sum(tdet)/N, native profile detachment.
- `sediment_deposition_kg`: sum(tdep)/N, native profile deposition (native sign).
- `sediment_yield_kg`: sum(runvol * sum(sedcon_1..5))/N.
- `hillslope_area_ha`: full modeled profile WAT OFE area sum / 10000.
- `runoff_depth_mm`: annual runoff volume / modeled area * 1000.
- `soil_loss_density_kg_m2`, `sediment_yield_density_kg_m2`: corresponding annual
  mass / modeled profile area; not road-prism area for MOFE profiles.
- `sediment_delivery_ratio`: yield/detachment when detachment > 0; otherwise NULL.
  Do not clamp native rounding or physically anomalous ratios into [0,1].

Retain all existing column names. `road_prism_erosion_kg` equals detachment only
for a single-OFE inslope road profile; it is NULL for mixed MOFEs and remainders.
`sediment_leaving_buffer_kg` is NULL: this table does not independently establish
buffer-specific delivery. Full-profile export is always `sediment_yield_kg`.
This corrects misleading aliases without deleting downstream fields.

Add `summary_policy=roads_segment_pass_v1`, `simulation_years`, `modeled_area_m2`,
`profile_scope` (`road`, `mixed_profile`, `replacement_remainder`,
`unclassified_profile`),
`source_pass_relpath`, and `source_wat_relpath` (the consumed Parquet paths;
segment_run_id identifies rows). Hash both source Parquets and the manifest. `loss_match_key=segment_run_id`
and `loss_row_missing=false` on valid rows. Scope precedence: design
`outslope_unrutted_remainder` means replacement_remainder; otherwise multiple
WAT OFEs mean mixed_profile; otherwise designs inslope_bd/inslope_rd mean road;
other or absent legacy designs mean unclassified_profile. Only proven road scope
receives the prism alias. A completed record requires a positive integer
segment_run_id; optional descriptive fields may be absent. Target IDs remain
optional context, but a source ID colliding with a manifest target ID is invalid.
Attach schema metadata identifying
annual units, the policy, source hashes and unavailable alias semantics. Keep
annual-unit descriptions at schema level; field-unit metadata must not rename
existing CSV headers through the shared download converter.

## Valid and invalid states

Excluding failed records from this diagnostic never changes the existing whole-run
failed-segment policy or authorizes a partially successful Roads execution.
An existing empty manifest or one containing only skipped/failed records produces
a typed empty summary without requiring PASS/WAT. Missing manifest is an explicit
preparation error. Legacy records with omitted status remain completed; unknown
status, malformed completed records, duplicate IDs, NULL/NaN/infinite required PASS metrics (validate before SUM),
nonpositive/stationarity-invalid area, missing source IDs or incomplete calendars
fail explicitly. Finite native signed detachment/deposition are retained rather
than silently clipped. No missing source is represented by fabricated zero loss.
Supported old artifacts remain historical until explicit regeneration; no in-place
migration or certification on read. Existing columns and on-demand CSV remain.

## Publication, visibility and recovery

Keep the existing visible interchange path, browser/download authorization and
archive behavior; no CSV shadow file, hidden output or new endpoint. Validate
source identity/contents before replacing the summary and check source hashes
again after reading. Reject destination aliases before writing. Publish via
same-directory atomic replacement with existing mode preserved (new files honor
umask). An invalid input/write failure preserves the previous summary and fails
the regeneration; it must not publish a ready resource. Candidate files use visible
`roads_segment_loss_summary.pending-<unique>.parquet` names in the same directory;
on failure retain any written candidate for inspection and identify it in the
raised error/log. Successful replacement consumes its candidate. Diagnostic failure stays
in the existing Roads lifecycle log; no useful generated source is removed.
Required producer inputs remain ordinary archived project artifacts. Verify
Parquet and on-demand CSV values, browser visibility, archive bytes/modes and
retry after failure. Original project model outputs and aggregate accounting
must remain unchanged during isolated validation.

## Rationale and limits

The old target-first join replicated 14 hillslope result vectors across 34 UM1
roads; summing corrected-scenario rows overstated sediment by about tenfold.
Source-qualified PASS records already expose segment exports through the owned
native interchange. DuckDB aggregation reuses the existing summary substrate;
no hydrology rerun, Python numerical model, native release, or dependency is
needed. Very short segments and dominant long-road geometry remain separate
scientific questions. See ADR-0103 for the source/formula decision.
