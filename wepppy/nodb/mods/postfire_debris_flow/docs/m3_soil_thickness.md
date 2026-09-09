# Offline thickness contract, version 1

This is the executable version 1 study contract. The subsequent owner decision
approves SSURGO primary and original STATSGO THICK fallback for production
direction; the existing offline helper does not implement that fallback.
ADR-0053 records both decisions and the remaining implementation details.

## Original reference

The [1995 archive metadata and embedded SAS](https://www.sciencebase.gov/catalog/item/631405c5d34e36012efa3187)
uses `laydeph-laydepl`, sums by component, then weights by component percentage
and divides by total nonmissing component percentage. The SAS extraction has
no horizon designation or explicit bedrock exclusion. It explicitly sets WATER
component attributes, including THICK, to missing before aggregation. This confirms the
transformation, not what layers the original surveys included or whether their
endpoints were censored by survey depth. No bedrock-depth claim is supported.
The [2025 COG release](https://www.sciencebase.gov/catalog/item/675721b9d34e5c5dfd05c575)
identifies its origin as that archive, inches, nominal 30 m, EPSG:5069, Float32,
NaN outside coverage, and -0.1 water/missing sentinel. All negative values are
excluded, without inferring all missing pixels are water.

## Component intervals

`derive_component(horizons, *, policy="strict_soil") -> dict` accepts explicit
raw records with stable `chkey`, `hzdept_r`, `hzdepb_r`, `hzthk_r`,
`desgnmaster`, `hzname`. Numeric depths are cm. Deduplicate identical stable IDs;
conflicting duplicate IDs reject the component. Identical depth ranges with
different IDs are retained in the sum diagnostic but flagged as overlap.
Negative, missing, nonfinite, reversed or zero-length intervals reject thickness;
a zero-thickness interval is not evidence of a measured zero-soil profile.
Report conflicting provided `hzthk_r`; do not substitute it for endpoints.

The strict candidate requires a zero start, contiguous nonoverlapping soil
intervals, unambiguous designations, and consistent thickness fields. Explicit
R master layers are excluded as hard bedrock, but all-record topology must still
be valid: embedded/overlapping R cannot silently bridge a soil gap. A profile
consisting of R starting at zero is classified `nonsoil` with measured zero
soil thickness; it remains outside valid-soil coverage. No-horizon miscellaneous
areas or rock-outcrop names alone do not prove numeric zero.

Cr/soft-weathered rock, mixed R designations, legacy H and unknown masters are
`ambiguous_material`; strict thickness is unavailable. Ordinary O/A/E/B/C and
their transitions are accepted; C alone is not automatically bedrock. This
conservative study selection avoids adjudicating uncertain material as soil.
`all_layers` is a labeled sensitivity retaining all valid recorded intervals,
including R/Cr, to approximate the legacy extraction; it still rejects topology
or thickness conflicts. Neither policy is approved production parameterization.
For every component report raw interval sum, interval union, deepest endpoint,
gaps/overlaps and reasons independently of selected thickness. No gap fill,
150/200 cm extension, or inference that the endpoint is bedrock.

[NRCS Fundamental Query](https://sdmdataaccess.nrcs.usda.gov/documents/FundamentalQuery.pdf)
establishes keys, cm units and potential duplicate depth intervals.
[NRCS Soil Survey Manual chapter 3](https://www.nrcs.usda.gov/sites/default/files/2022-09/SSM-ch3.pdf)
distinguishes C from R and weathered rock. Exact R exclusion is source-backed;
how to map weathered material to the calibrated THICK remains unresolved.

## Components, map units and catchments

`derive_mapunits(components, horizons, *, policy="strict_soil",
substituted_mukeys=()) -> (component_rows, mapunit_rows)` joins original keys.
Positive integer source IDs are mandatory (zero is reserved for outside-survey
raster cells). Normalize numeric key strings before joining; reject null,
nonpositive, malformed, duplicate component IDs or cross-component horizon IDs.
Unique component IDs are mandatory; conflicting duplicates or orphan horizons
are source errors. Missing or invalid percentages reject the map-unit estimate;
finite weights must be 0–100. Totals above 100 reject; below 100 expose missing
support. Mean cm = sum(valid cm * percentage) / valid percentage. Report known,
valid, nonsoil and omitted percentages separately. Missing components never
become zero or disappear from full support denominators. Substituted map units
are unavailable even if replacement records exist. Unknown raster keys are
unavailable; outside-survey nodata remains separate. No donor/fallback joins.

`build_artifacts(cache_path, mukey_raster, catchments, output_dir, *,
source_id, policy="strict_soil", substituted_mukeys=()) -> list[dict]` consumes
an explicit read-only SQLite source with `component` and `chorizon` tables.
Require canonical core columns; optional `compkind` is descriptive only.
Absent files, incompatible schemas, malformed DBs and empty tables fail
explicitly. Empty horizon data for an individual component is an unavailable
record. Encode the file URI; set `query_only`, disable extension loading, and
close connections. Source acquisition is never implicit.

Catchments are `{id: mask_path}` with raster value 1 denoting full upstream
support, including channels and outlet. Require identical projected meter
square grids. Count map-unit/mask intersections using owned wepppyo3 Rust;
Python combines modest tabular counts. Each cell contributes its component
valid fraction: mean cm = sum(cell_count * valid_fraction * mean_cm) /
sum(cell_count * valid_fraction). Fractional component coverage represents
unlocated components, not known subpixel geometry. Map-unit boundaries use
nearest-neighbor source labels. Full area includes all mask cells. No dNBR or
channel exclusion. No minimum coverage acceptance threshold.

`complete` means valid support equals full support and no source-rejection
reason; `partial` means positive but incomplete support; `unavailable` means
none. Only complete support supplies `full_mean_cm`/`full_S`. Known-support
means and S remain labeled diagnostics on partial catchments. `S=mean_cm/254`;
English display is cm/2.54 and never feeds rounded values back into S.

## Additive artifacts and boundary behavior

Create a new output directory; never overwrite input paths, live caches or
existing study outputs. GeoTIFF input only (no VRT/network reader in evaluation),
regular resolved files, with grid checks before cross-raster operations.
Artifacts: `components.csv`, `mapunits.csv`, `thickness_cm.tif` (Float32, NaN),
`valid_fraction.tif` (Float32, zero unsupported), `catchments.csv`, and
`manifest.json` with source ID, policy, units and SHA-256 for every input.
CSV reason codes are sorted, semicolon-separated; missing numbers are empty.
Raster NaN means unavailable thickness, never measured zero. Check input hashes
after generation. Failed builds may leave an explicitly incomplete output
folder without a success manifest; rerun in a fresh directory.

Reason vocabulary includes `missing_horizons`, `invalid_depth`,
`duplicate_id_conflict`, `overlap`, `gap`, `nonzero_start`, `thickness_conflict`,
`ambiguous_material`, `bedrock_excluded`, `nonsoil`, `invalid_percentage`,
`overfull_percentage`, `incomplete_components`, `substituted_key`,
`unknown_mukey`, `outside_survey`, and `partial_support`. Source structural
errors raise explicit exceptions; scientific unavailability is returned in rows.

## Source recommendation and scientific limits

The archived three-site, 12-outlet study recommended retaining original
STATSGO pending owner review. The owner subsequently selected **SSURGO as
primary and original STATSGO THICK as fallback**, preferring detailed soil
information while retaining broad geographic coverage. This supersedes the
study's source-selection recommendation, not its numerical findings.

The comparison measures sensitivity, not which source predicts debris flows
more accurately. Original STATSGO processing renormalizes over nonmissing
components; complete raster coverage is not complete component observation.
The version 1 complete-only outputs and strict-material policy remain offline
study behavior, not ratified production usability requirements.

Before runtime integration, specify material inclusion, incomplete-component
handling, fallback granularity/triggers, and source freshness. Report source
identity and fallback contributions without silently treating missing depth
as zero. Validate STATSGO coverage and sentinels; if neither source is usable,
report unavailable. Source-priority approval does not authorize live Soils
rebuilds or implicit network acquisition. Explicit nonfinite arithmetic and
Float32 representation errors still abort the offline builder.

See [measured evidence](../../../../../docs/work-packages/20260908_staley_m3_soils/artifacts/soil_decision.md)
for historical findings and ADR-0053 for the subsequent owner decision.
