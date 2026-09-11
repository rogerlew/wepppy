# Local rainfall adapters and M1 results

Status: accepted local contract; R02 explicitly approved by the operator.
The [work package](../../../../../docs/work-packages/20260909_staley_rainfall_results/package.md)
scopes local roadmap stage 4. Production UI/NoDb/RQ composition and Climate
readiness notifications are separately implemented in [production_m1.md](production_m1.md).

## Scientific identity and ownership

Consume completed predictor and Climate snapshots only; never rebuild inputs or
follow embedded source paths. The [M1 contract](m1_predictors.md) and
[scalar engine](staley2017_engine.md) remain authoritative. Apply the same fixed
postfire predictors to all event/design scenarios; do not simulate recovery,
combine duration probabilities, reconstruct storms, propagate probability bounds,
or convert PDS recurrence intervals into annual debris-flow probabilities.

Preserve independent predictor support, unavailable T/F/S, assessment identity,
source kind and area warnings outside inclusive 0.2–8 km². NOAA is a design
frequency source, never an event catalog. Inverse equality thresholds depend on
predictors and explicit targets, independently of frequency source. Presentation
unit changes must not recompute probabilities. Snapshot identity does not prove
live controller freshness; production invalidation/publication is stage 5.

## Execution contract: local file boundary

Frozen for the authorized local implementation, with explicit R02 approval.
Compatibility is additive; no existing project artifact is mutated.

`RainfallInputs` requires `predictor_manifest`, `cli_parquet`,
`expected_sha256` (absolute local path to lowercase SHA-256), `project_id`,
`climate_mode`, `date_semantics` (`simulation_labels` or `calendar`) and
`assessment_id`. Optional `cli_frequency_csv` and `noaa_csv` are explicit paths.
Identity strings are caller assertions preserved with hashes; the adapter cannot
prove a live controller association. Acceptance reproduction separately verifies
project source overlap. Supplied missing files are errors; omitted NOAA yields
unavailable NOAA scenarios. No embedded provenance path is reopened.

Regular files and every parent must be nonsymlink local paths, under trusted
immutable ownership. Files are capped at 64 MiB (JSON/CSV at 1 MiB), parquet at
200,000 input rows, 64 primitive numeric columns and 128 MiB declared decoded
row-group bytes. Reject duplicate field names, nested/string input columns,
external column chunks and contradictory schemas before decoding. JSON rejects
duplicate keys and nonfinite constants. Validate pinned hashes before decoding
and recheck all consumed files before final publication. Resource bounds limit
this trusted local interface; they do not sandbox hostile native decoders.

The predictor manifest must have version 1, complete processing status, valid
T/F/S units, finite values or explicit unavailable reasons, consistent independent
support counts/fractions and availability. Preserve its entire metadata as
assessment provenance. Verify only the fixed four `wbt` artifact names and
hashes; no raster decoding or reconstruction is performed. Check source/prepared/
tool hash mappings for shape without following their paths. This validates a
pinned completed snapshot, not upstream scientific truth or current freshness.

CLI input requires numeric `prcp` and `year`. Canonical duration columns are
`peak_intensity_15/30/60`; no legacy intensity aliases are interpreted. Optional
`month`, `day_of_month`, `sim_day_index` retain original numeric values. Finite
nonnegative precipitation is required; wet means strictly positive. Each wet row
produces every requested duration. Zero intensity is valid event rainfall under
the scalar intercept contract; missing, nonfinite or negative intensities produce
`missing_duration`, `missing_intensity`, `nonfinite_intensity` or
`negative_intensity` respectively. Dates do not control wet-event inclusion.
Invalid/missing integral date components are flagged `invalid_or_missing`; valid
simulation labels never become observed ISO dates. Duplicate dates remain rows.
Event ID is the full parquet SHA-256, colon, original zero-based row ordinal.
Record all finite integral year labels and wet-year count; no inferred years for
missing dates. CLI design is unavailable with invalid wet-year labels.

Both CSV formats must match the actual Climate-owned text exports: exact units,
partial-duration header, one unique ARI header, unique duration labels, finite
nonnegative numeric cells and matching row lengths. Preserve metadata, require
finite latitude/longitude in range and recognizable source title. NOAA only
accepts the metric intensity export, never depth or confidence-bound tables.
Zero design cells are unavailable `zero_placeholder`. Missing duration/interval
is `unsupported_combination`. CLI CSV is optional rounded parity evidence, never
the numerical input. A disagreement with the same rank/clamp precedent is
`provenance_mismatch`; do not quietly accept a different snapshot.

## Execution contract: result and query schemas

`build_m1_results(inputs, output_dir, *, frequency_source, return_intervals,
durations, target_probabilities)` requires every keyword. Source is `cli` or
`noaa`; unique requested intervals are in {1,2,5,10}, durations in {15,30,60},
and at most 100 unique finite inverse targets strictly between zero and one.
Sequences must be nonempty. Normalize durations/intervals/targets ascending.
No frequency source substitution. Each inverse target uses scalar equality
semantics and preserves all three statuses and reasons.

Fresh private output directory contains `incomplete.json`, `events.parquet`,
`design.parquet`, `inverse.parquet`, and final `manifest.json`. Never replace an
existing directory. Failure retains incomplete files for diagnosis; retry at a
new path. The final marker follows table readback/schema/hash verification and
input rechecks. A successful bundle retains the initial marker as build history;
only `manifest.json` means complete. Output manifest schema_version=1, model=M1,
status=complete, units, identity, full predictor snapshot, source digests,
frequency diagnostics, request parameters, table row counts and SHA-256.

All tables have `duration_minutes` int64, `intensity_mm_per_hour`, `rainfall_mm`
and `probability` float64 (nullable), `status`, `reason` strings (nullable reason).
Events additionally have `event_id` string, `row_ordinal` int64, `year`, `month`,
`day_of_month`, `sim_day_index`, `precipitation_mm` float64 (nullable date fields),
`date_status` string. Design adds `return_interval_years` int64, `source` string,
`rank_index` and `positive_samples` nullable int64. Inverse adds
`target_probability` float64; probability is null (target is a separate column).
Table units and assessment/warning provenance are in the mandatory manifest;
every query returns that context with rows. No orphan table is a result bundle.
Unavailable forward rows have null probability. Missing predictors use
`missing_predictors` while preserving valid rainfall; invalid rainfall reasons
remain primary and complete predictor diagnostics stay in the context.

Materialize scalar results once: the genuine catalog prototype evaluates 30,936
rows in 0.230 seconds. `open_results(path, *, expected_manifest_sha256)` verifies
fixed table names/hashes/schema/row counts and returns a local `ResultCatalog`.
No untrusted manifest filenames, SQL or remote readers. Bounded result files
use the same byte limits, at most 600,000 event rows, 12 design rows and 300
inverse rows. `list_events(catalog, *, duration_minutes, min_probability=None,
max_probability=None, year=None, sort='row_ordinal', descending=False, limit=100,
offset=0)` returns context, total matching event count and rows for the selected
duration. Sort allowlist: row_ordinal, rainfall_mm, probability; nulls last,
ordinal ascending breaks ties. Limit 1–1000, offset 0–200000; explicit duration
avoids accidental aggregation across durations. Year filter matches original
label. `get_event(catalog, event_id)` returns context and all duration rows;
unknown ID raises KeyError, malformed ID is invalid_input. Query state is an
in-memory validated snapshot; reopening verifies later disk changes.

Boundary failures use `RainfallError.code`: invalid_input, resource_limit,
missing_provenance, provenance_mismatch, source_changed, output_exists,
incomplete_output. Native filesystem errors and scalar numerical exceptions
remain explicit. The accepted scientific unavailable reasons remain unchanged.

## Local acceptance and sample-support policy

The genuine Wallow catalog produces 30,936 event rows, 12 design rows for each
selected source and six explicit inverse rows. Final local reproduction is in
`artifacts/reproduce.py` in the work package; use `--frequency-source cli` or
`--frequency-source noaa`. Source inventory pins the predictor manifest and
predecessor evidence, with matching original project DEM/mask/outlet/SBS/K.

CLI ranking uses the complete supported 1/2/5/10/25/50/100 request then selects
the caller subset. Missing record support is `unsupported_record_length`; an
empty positive-duration series is `no_positive_samples`. A positive infinity
makes the duration's design scenarios `nonfinite_intensity`, preserving finite
event durations without silently reranking the remaining design samples.

Under approved R02, a zero-based requested rank at least the positive sample
count returns `unavailable` / `insufficient_positive_samples`. Preserve the rank
and count, with null intensity, accumulation and probability. Other ranks and
durations remain available; zero positive samples retain `no_positive_samples`.
The optional rounded CSV is still checked against Climate’s clamped export,
which is provenance evidence rather than rainfall input. This avoids presenting
last-observation substitution as a supported estimate. See
[ADR-0062](../../../../../docs/adrs/ADR-0062-staley-local-rainfall-results.md).

On open, result rows must be semantically consistent with manifest units,
request combinations, date labels and predictor state. Reevaluate scalar
forward/inverse values to detect inconsistent pinned tables; hashing alone
does not establish those invariants. This adds about 1.2 seconds when opening
the genuine catalog; subsequent list/detail queries are approximately 18/2 ms.
