# Production scientific integration runtime contract

Status: intended behavior approved for execution 2026-09-14; conformance pending.
This specifies the runtime details of [production M3](production_m3.md),
ADR-0066 common support and accepted ADR-0067 recorded-depth policy. It amends
production M1 aggregation and shared rainfall/publication behavior for new
version-2 predictor manifests. Offline version-1 products remain unchanged.

## Prepared source boundary

M3 reads existing `soils/ssurgo.tif`, its retrieval metadata, and
`soils/ssurgo_tabular_cache.sqlite`. It never initializes or refreshes that cache,
builds Soils, or substitutes WEPP donor keys. A missing optional primary source
is scientific absence; a present corrupt source, unsafe path or incompatible
schema is an explicit error. All source paths use existing project containment.

Collection evidence is prepared locally in
`postfire_debris_flow/inputs/soil_sources.json` (schema_version 1). Its optional
`primary` object contains `collection: SSURGO`, `mukeys` (unique positive key
strings), `evidence` (project-relative regular JSON file), and `evidence_sha256`.
The evidence records per-key collection association and its provenance; the
adapter must not infer collection from cache or mosaic names. Its optional
`fallback` object contains `path`, `sha256`, `source_id` and `units: inch`,
identifying a prepared GeoTIFF window of original USGS THICK. Paths are explicit
project-relative files, with no symlinks, parent traversal, network or VRT.
Source metadata is bounded to 1 MiB. Missing primary lineage does not make
existing WEPP soils invalid; it means primary M3 eligibility is unverified.
Evidence has schema_version 1, `collection_by_mukey` mapping numeric keys to
`SSURGO`, a nonempty `source` attribution string and `retrieved_at` timestamp.
Every primary key must have an explicit SSURGO association. No evidence path
is followed beyond this one named, hash-pinned local JSON file.
Fallback source_id is exactly `USGS-675721b9d34e5c5dfd05c575-THICK`; also require
`evidence` and `evidence_sha256` for a local preparation record linking that
window's sha256, native grid and bounds to the original object's identity.
Absent metadata, `{}`, or `{"schema_version":1}` means no verified sources.
Zero-byte files, non-object JSON, unknown schema versions and malformed populated
objects are errors. Only `schema_version`, `primary`, `fallback` are allowed;
null source entries are treated as absent. Populated primary/fallback entries
must supply every field named above; extra provenance fields are not path inputs.
An empty `{}` primary/fallback entry is malformed, not absent.

Source vintage and current collection association are separate. Retain raw
cache retrieval metadata and snapshot hashes; unknown historical survey version
stays unknown. Newly prepared source metadata cannot claim retroactive version
proof. No source acquisition is implicit or authorized by this contract.
Missing optional source entries remain unavailable; zero usable support is an
explicit unavailable result, not a successful numerical estimate.

## Soil policy and stable snapshots

Use `recorded_depth_v1`: admitted ordinary O/A/E/B/C, documented H numbered
layers and weathered Cr, excluding explicit terminal R; representative endpoint
differences in cm, no extension. Report separate thickness disagreement.
Keep missing/invalid depths, gaps, unexplained overlaps and stable-ID conflicts
unavailable. Recognize only the accepted bounded legacy combination pairs from
ADR-0067, preserving both source records/IDs and counting their depth once.
Normalize positive usable component percentages; individual nonfinite/out-of-range
weights reject the map-unit estimate, totals above 100 alone do not. Explicit
all-R components remain nonsoil, excluded from usable primary weight. Zero
original THICK is eligible; negative/nonfinite THICK is unavailable.

Read canonical core columns within one explicit read-only SQLite transaction
including committed WAL content. Disable extension loading and trusted schemas.
Require real tables and expected columns. Do not checkpoint, change journal
mode, or mark a live WAL database immutable. Retain visible canonical component
and horizon CSV snapshots, schema and logical hashes sufficient to reproduce
depth derivation. Bound source files to 512 MiB and selected serialized rows to
64 MiB per table; oversize data fails explicitly. No broad source refresh.

Record source stat identities including main DB and existing WAL/SHM companions
for admission/finalization; conservative invalidation from journal housekeeping
is permitted. Recheck the consistent logical core identity after preparation
and before publication outside the NoDb lock. Locked finalizers check the
previously verified stat identities. A source change fails the attempt rather
than publishing an older logical snapshot. Retain the failed snapshot/artifacts.
Every logical read is bracketed by source main/WAL/SHM stat observations before
opening its read transaction and after completing it. They must match before
that logical identity is eligible for later finalization. Never attach a stat
baseline captured only after reading an older snapshot. Compare the post-read
identity again at the locked finalizer; persistent drift fails, not retries into
an unrelated source revision.

## Predictors and exact support

Use existing raster admission (10 million cells, aligned projected square meter
grid) and the unchanged 96 MiB per-predictor artifact limit. Process bounded
blocks where feasible. Do not relax admission to fit an artifact.
Nearest-neighbor sampling applies to source labels, SBS and original THICK;
missing cells stay missing. Convert THICK inches × 2.54 to cm.

M1 support is watershed AND determined raw WBT intersection AND valid dNBR AND
valid provenance-backed K. Recompute all T/F/S over that same mask. Preserve
raw WBT outputs and their all-basin counts/bounds. M3 support is watershed AND
valid SBS AND usable selected thickness. F is the fraction moderate/high;
S is mean cm / 254. Valid unburned cells are included. T remains full-upstream
raw-elevation relief / sqrt(full upstream area), using installed D8UpstreamRelief
with existing routing and outlet. Validate upstream area against the authoritative
watershed; incomplete terrain coverage cannot be repaired by shrinking support.

Write `valid_mask.tif`, UInt8: used 1, excluded inside 0, outside 255 NoData.
Coverage is `{total_cells, valid_cells, excluded_cells, valid_fraction,
policy, mask: valid_mask.tif}`; fraction is unrounded valid / total. Zero
support makes F/S (and M1 T) unavailable with `zero_valid_support`; M3 full-basin
T remains independently auditable. No minimum percentage gate.

New predictors use `schema_version: 2`, explicit `model: M1|M3`,
`support_policy: common_valid_v1`, `coverage` and model-specific `soil_policy`.
Retain existing grid/outlet/area/source/tool/predictor fields. M3 predictor units
are T `dimensionless`, F `fraction`, S `thickness_cm_div_254`; do not impose
M1's S<=1 bound on M3. Scalar coefficient tables and rainfall equations do not
change. Readers accept unchanged legacy version 1 as M1, but predictor reuse
requires exact model/policy/source/tool identity and rejects version-1 reuse
for new common-support execution.
Version-2 predictors omit point `lower`/`upper`; raw M1 bounds remain only in
`T.wbt_summary`, unchanged, and need not equal the common-support point T.
Example: raw 10 true / 90 false gives raw T=0.1; support limited to those ten
true cells gives the production T=1. Each M1 predictor's support is
`{total_cells:full_basin_count,valid_cells:common_count,coverage_fraction:common/full}`.
M3 F/S have that same common support, while M3 T support has full basin counts
and fraction 1 only when full terrain is valid. Predictor availability is
complete/partial/unavailable for 3/1–2/0 available predictors, independent of
coverage percentage. Available point values require positive relevant support;
unavailable values are null with a nonempty reason. T/F/S ranges are M1:
T and S within [0,1], F finite; M3: T and S nonnegative finite, F within [0,1].

## Artifacts and publication

Attempt `predictors/` retains prepared input maps, raw WBT outputs/logs,
`valid_mask.tif`, manifest and M3 `soil/` artifacts: `components_source.csv`,
`horizons_source.csv`, `components.csv`, `mapunits.csv`, `thickness_cm.tif`,
`source.tif` (0 unavailable, 1 primary, 2 fallback, 255 outside), and soil manifest
with schema, policy, snapshot hashes and source contributions. Component weights
are never spatial coverage. Pair IDs and warning/rejection reasons stay visible.

Immutable prepared sources are copied under attempt `predictors/soil/sources/`:
`soil_sources.json`, `primary_evidence.json`, `cache_retrieval.meta.md`,
`fallback_native.tif`, `fallback_evidence.json` when present. Copy and verify
their expected hashes before deriving; original mutable inputs participate in
freshness but copied sources establish historical reproducibility. Record absent
optional inputs explicitly in the soil manifest. Preparation evidence binds
the native THICK window hash/grid/bounds to the approved original dataset;
an arbitrary label is insufficient provenance.

Fixed version-2 predictor artifact inventories are M1: `valid_mask.tif`,
`wbt/intersection.tif`, `wbt/slope.tif`, `wbt/support.tif`, `wbt/summary.json`;
M3: `valid_mask.tif`, `wbt/relief.tif`, `wbt/area.tif`, `wbt/coverage.tif`,
`wbt/summary.json`, `soil/thickness_cm.tif`, `soil/source.tif`, `soil/manifest.json`.
M3 wbt/summary.json records tool/version/hash, grid, outlet row/column,
full_upstream_cells, area_m2, relief_m, terrain_valid and reason; point
T = relief_m / sqrt(area_m2) only for valid full terrain. The module writes
this summary from inspected native outputs, not from asserted source metadata.
Readers verify only these fixed inventory paths; other recorded source paths
are provenance, never instructions to open arbitrary files.

Soil `source_cells` counts partition the full watershed by usable selected
thickness before SBS intersection, with outside counted separately. Predictor
coverage additionally records `primary_valid_cells` and `fallback_valid_cells`
for M3 only, summing to its final common valid_cells after SBS intersection.
No component percentages enter either cell count denominator.

Canonical CSV headers, in order:

- `components_source.csv`: mukey,cokey,compname,comppct_r.
- `horizons_source.csv`: cokey,chkey,hzname,hzdept_r,hzdepb_r,hzthk_r,desgnmaster.
- `components.csv`: mukey,cokey,compname,comppct_r,thickness_cm,status,reason_codes,
  horizon_count,source_row_count,interval_sum_cm,interval_union_cm,deepest_bottom_cm,
  reported_thickness_conflicts,pair_reductions.
- `mapunits.csv`: mukey,mean_cm,known_percentage,valid_percentage,
  nonsoil_percentage,rejected_percentage,unreported_percentage,status,reason_codes.

Missing numeric CSV values are empty; reasons sorted and semicolon-separated;
pair_reductions is a JSON array with source_chkeys, top_cm, bottom_cm and reason.
Source keys are canonical positive decimal strings; source tables sort by stable
keys. Component status is valid/unavailable/nonsoil; map-unit status is
available/unavailable. Known weight sums valid individual percentages; rejected
weight is known minus usable minus nonsoil; unreported is max(0,100-known).
Invalid individual weights reject the map-unit estimate and remain diagnosed.

Soil manifest fields: `schema_version:1`, `status:complete`,
`policy:recorded_depth_v1`, `units:cm`, `source_schema` (selected table columns),
`source_state` (main/WAL/SHM stat identities), `logical_sha256` (selected
component/horizon canonical row identities), `artifacts_sha256` (relative
fixed artifact names), `counts` (components, horizons, mapunits). Raster-composed
soil manifests additionally carry `grid` and `source_cells` with primary,
fallback, unavailable and outside counts. A failed preparation retains
incomplete.json and any source snapshots, without a complete manifest.

Shared results retain event/design/inverse schemas, 15/30/60 minutes, 1/2/5/10
years, CLI or available NOAA, and 50% inverse target. Dispatch the explicit
predictor model to the existing scalar engine. Results retain schema version 1
with explicit model and validated predictor snapshot; add coverage and copy
its exact mask into results. Legacy outputs need no mask and are not rewritten.

Add `valid_mask.tif` to accepted-file publication/download only for results
whose recorded inventory contains it. The four legacy filenames remain valid;
manifest is installed last. Preserve ordinary authenticated browse/download,
visible attempts/publication work, and canonical archive/restore. No hidden
records, alternate route or broad directory downloads. Failed replacements
preserve accepted pointers and files; existing explicit publication repair applies.

NoDb state keeps schema version 1; add coverage to accepted result records.
Public state displays Valid coverage with counts, a precision that reveals any
exclusion, the existing explanatory text and mask link. Missing legacy coverage
is “Not recorded for this result.” Existing model/frequency selection transport,
Status/Details/job IDs, themes and SI/English behavior stay compatible. 🌋 follows
the latest accepted result's own dependencies. M3 never requires K/dNBR.

## State and compatibility evidence

Absent or empty optional source metadata gives unavailable source inventory;
it never creates or repairs upstream Soils. Populated verified primary and/or
fallback sources follow cellwise selection. Legacy accepted results retain
downloads and explicit missing-coverage display. Malformed populated metadata,
unsafe paths and corrupt DB/raster files fail before acceptance. Empty common
support is scientific unavailability. Source changes during work, publication
failures and retries retain observable attempts and previous accepted results.

Required evidence includes full-support M1 parity, partial/disjoint/zero support,
source snapshot/WAL concurrency, soil-builder/generated-WEPP-input parity,
real installed WBT output, live RQ/browser/download and archive round trips.
Missing prepared lineage/THICK prevents the corresponding acceptance case;
unit tests and a source-free unavailable result do not close the package.
