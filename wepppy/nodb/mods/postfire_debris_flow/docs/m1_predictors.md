# M1 prepared predictor integration contract

Status: accepted local backend contract, 2026-09-09.

Reuse the [slope/SBS contract](slope_sbs.md), [dNBR contract](dnbr_upload.md),
and [scalar engine](staley2017_engine.md). Write only a fresh caller-owned
local bundle; no NoDb/UI/RQ, upstream rebuild, acquisition or publication.

## Frozen interface and behavior

Accepted 2026-09-09 after owner approval of P02/P03; ADR-0059 governs K policy.
This section froze the local interface before implementation.

`integration.M1Inputs` is a frozen dataclass with required paths `dem`, `mask`,
`outlet` (Point, Feature or single-feature FeatureCollection), `sbs`, required `expected_sha256` path-to-digest mapping,
`wbt_sha256` executable digest, and explicit `source_kind` (`real`, `synthetic`,
`mixed`). Optional paths: `k`, `k_manifest`, `dnbr`, `dnbr_manifest`.
`lineage_sources` is a tuple of explicitly authorized dNBR source paths.
`elevation_units` is `m`; `sbs_alignment` is `exact` (default) or `nearest`.
`build_m1_predictors(inputs, output_dir, *, wbt_executable)` returns the version-1
manifest dictionary. `M1Error.code` carries expected boundary failure reasons.

Inputs are regular nonsymlink trusted local GeoTIFF/JSON files, with expected
SHA-256 for every supplied file, including external `.tif.msk` masks. Internal
masks are honored. A regular `.tif.aux.xml` of at most 64 KiB may contain only
one PAMDataset/PAMRasterBand (band 1)/Metadata tree of nonempty, unique known
STATISTICS_* entries (minimum, maximum, mean, standard deviation, valid percent,
and approximate flag). Reject declarations/entities, unexpected attributes,
other elements, references, georeferencing, NoData, encoding and units. Numeric
statistics must be finite; the approximate flag is YES/NO. An absent sidecar is
valid; empty/malformed sidecars fail explicitly. PAM is disabled during raster
reads, so this validated inert cache never influences samples, support or grid.
This exception applies to trusted local M1 GeoTIFFs, not uploaded source rasters.
Validated statistics caches are excluded from expected SHA-256 and scientific
freshness: appearance, removal or valid statistics refresh cannot alter raster
decoding. Validate a present cache each time the local raster boundary is used;
malformed or meaningful metadata is never treated as inert.
All other auxiliary metadata/overviews and sidecars are rejected. This admits
standard project DEM statistics without weakening meaningful-metadata checks.
The statistics-only exception is implemented under checkpoint `7447e6243`.
JSON is capped at 1 MiB, rasters at 512 MiB and 10 million cells. Decode only
single-band GeoTIFF with identity encoding and pixel-area metadata. The target
DEM/mask/K/dNBR grid is WGS84 UTM with square meter cells; opt-in nearest SBS
preparation admits other finite georeferenced source grids. Reject contradictory vertical units. Unmasked nonfinite DEM/SBS/mask
samples are invalid. Palette SBS uses indices, only 0–3. Lossless WBT copies
use Float64 DEM/mask, Int16 SBS, finite collision-free sentinels, explicit
SampleFormat, classic uncompressed untiled grayscale TIFF. Verify samples,
masks and exact grid after writing. A separate positive-valid binary mask
adapts the existing domain to `summarize_dnbr`. Only explicit nearest SBS
alignment is permitted; K/dNBR never warp. NumPy/GDAL compiled reductions are
existing precedents; owned Rust alone computes Horn and intersections.

S uses the named `k_polaris_nomograph.tif`, multiplier 1, finite [0,1] full
coverage only. K metadata must select Nomograph and name its artifact, retaining
statistic, depth weights, mode/fragment contract and gap-fill policy/summary.
Preserve the whole K section. Missing fields yield unavailable S with
`missing_provenance`; malformed/contradictory metadata fails explicitly.
F requires version-1 normalization manifest, matching raster hash and target
grid, finite positive scale/finite offset, and input hashes checked against
explicit lineage paths. Do not follow arbitrary embedded paths. Unprovided
lineage yields unavailable F; mismatched lineage is an error. Missing optional
raster paths yield `missing_input`. Source hashes prove identity, not controller
freshness. Record production Soils readiness as `not_checked_local`.

Top-level fields: `schema_version` (1), `status` (`complete`, processing only),
`availability` (`complete`, `partial`, `unavailable` by point availability),
`source_kind`, `readiness`, `grid`, `outlet`, `area_km2`, `warnings`, `predictors`
(T/F/S with value, units, status, reason and independent support),
`sources_sha256`, `prepared_sha256`, `tool`, `k_provenance`, `artifacts_sha256`.
T retains WBT summary and lower/upper bounds; its `support.valid_cells` counts
determined intersections, while raw slope/SBS/joint support remains in the WBT
summary. Unknown T uses
`unknown_intersection`; incomplete K uses `incomplete_k_coverage`; empty F uses
`empty_dnbr`. Partial F remains an observed-support estimate. Area warning is
`area_outside_study_range`, outside inclusive 0.2–8 km².

Expected errors: `invalid_input`, `invalid_grid`, `invalid_sbs`,
`invalid_encoding`, `resource_limit`, `missing_provenance`,
`provenance_mismatch`, `source_changed`, `output_exists`, `tool_unavailable`,
`tool_failed`, `invalid_tool_output`, `preparation_failed`. Native filesystem
errors are preserved; malformed JSON is invalid input.

Exclusively reserve a caller-owned visible fresh directory. Retain `incomplete.json` and
partial files on failure; retry elsewhere. `manifest.json` is the final marker,
written after complete readable grid-matching WBT products, consistent summary
counts/bounds, and source/binary hash rechecks. Existing output is never replaced.
Pin binary hash and validate capability; invoke without shell or global cwd
changes, with 300-second timeout and stdout/stderr written to local log files.
Trusted immutable directory ownership is required; this is not hostile-owner
concurrency protection or active run publication.

`evaluate_m1_scenarios(bundle, scenarios)` accepts explicit `(duration_minutes,
rainfall_mm)` pairs and validates through the scalar engine. Return null
probability with `missing_predictors` when any point predictor is unavailable.
Retain source kind/area warnings. No climate default, frequency claim, M3
fallback or probability bounds. Authentic dNBR absence blocks full real-project
acceptance, not independently labeled controlled testing.


## Assessment identity and acceptance evidence

Match the dNBR assessment dates to the selected severity source and record source
lineage explicitly. A project rebuild creates a new source snapshot and fresh
bundle; preserve older results as historical evidence instead of relabeling them.
This prevents pairing a final June 23 assessment with an earlier project's July 1
preliminary imagery. Validate uploaded severity classes and masks against the
prepared SBS when retaining reproduction evidence.

Local complete-source acceptance is demonstrated on rebuilt Wallow: all 12,973
basin cells support T/F/S, with zero unknown intersections. The 11.6757 km² area
warning remains applicable. This validates local composition; live preparation,
publication, upstream freshness and climate ingestion require their own contracts.

Production upload does not request image dates and unknown dates do not block
M1. Compare assessment metadata when available; the user is responsible for
choosing dNBR and soil burn severity from the same fire assessment, as stated
beside the upload. Never infer imagery dates from upload timestamps.
