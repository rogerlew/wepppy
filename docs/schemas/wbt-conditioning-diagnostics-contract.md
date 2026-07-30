# WBT Conditioning Diagnostics Contract

## Scope and Status

This schema governs successful DEM-conditioning sidecars produced by
`FillDepressions`, `BreachDepressions`, `BreachDepressionsLeastCost`, and
`TopazConditionDem`, plus the reduced payload WEPPcloud publishes for channel
delineation. DOM-05B implementation conformance is pending.

## Sidecar Schema Version 1

The UTF-8 JSON document is at most 64 KiB. Duplicate keys, non-finite numbers,
unknown keys, and trailing non-whitespace data are invalid. Every sidecar has
exactly these top-level keys:

| Key | Type | Rule |
| --- | --- | --- |
| `schema_version` | integer | exactly `1` |
| `tool` | string enum | one of the four tool names above |
| `status` | string enum | exactly `success` |
| `operation_id` | string | exactly 32 lowercase hexadecimal characters |
| `input_name` | string | basename only, 1-255 printable characters |
| `output_name` | string | basename only, 1-255 printable characters |
| `units` | object | exact keys below |
| `terrain_change` | object | exact keys below |
| `conditioning` | object | method-specific exact keys below |
| `parameters` | object | method-specific exact keys below |

`units` has exactly `elevation`, `horizontal`, `area`, and `volume`. Values are
respectively `m|unknown`, `m|unknown`, `m2|unknown`, and `m3|unknown`.
WEPPcloud accepts only metre-based values because its prepared DEM contract is
projected horizontal metres with elevation metres.

`terrain_change` has exactly `valid_cell_count`, `raised_cell_count`,
`lowered_cell_count`, `raised_area`, `lowered_area`, `maximum_raise`,
`maximum_cut`, `fill_volume`, and `cut_volume`. Counts are nonnegative integers;
the remaining values are finite nonnegative numbers. Raised/lowered counts do
not exceed valid cells and are mutually exclusive source-to-output comparisons.
Areas are count times cell area; volumes are summed signed elevation deltas
times cell area.

### FillDepressions

`conditioning` has exactly `detected_low_point_count`,
`filled_depression_count`, `skipped_depression_count`, and
`flat_gradient_applied` (boolean). Counts are nonnegative integers; filled plus
skipped does not exceed detected. `parameters` has exactly `fix_flats` (boolean),
`flat_increment` (finite nonnegative number), and `max_depth` (finite
nonnegative number or `null`).

### BreachDepressions

`conditioning` has exactly `breached_depression_count`,
`longest_breach_path_cells`, `longest_breach_path`,
`single_cell_pits_filled`, `residual_fill_used` (boolean), and
`residual_depression_count`. Counts are nonnegative integers, path length is a
finite nonnegative number, and residual count is zero when residual fill is
false. `parameters` has exactly `fill_pits` (boolean), `flat_increment`
(finite nonnegative number), `max_depth` (finite nonnegative number or `null`),
and `max_length_cells` (finite nonnegative number or `null`).

### BreachDepressionsLeastCost

`conditioning` has exactly `detected_low_point_count`,
`resolved_low_point_count`, `unresolved_low_point_count`,
`longest_breach_path_cells`, `longest_breach_path`, `fallback_fill_used`
(boolean), and
`fallback_filled_low_point_count`. Counts are nonnegative integers; resolved
plus unresolved equals detected; fallback count is zero when fallback is
false. `parameters` has exactly `search_distance_cells` (positive integer),
`search_distance` (finite positive number), `max_cost` (finite nonnegative
number or `null`), `minimize_distance` (boolean), `flat_increment` (finite
nonnegative number), `fill` (boolean), and `fail_on_unresolved` (boolean).

WEPPcloud requires `fill=false`, `fail_on_unresolved=true`, and
`fallback_fill_used=false`. Fallback fields serve standalone WBT callers only.

### TopazConditionDem

`conditioning` has exactly `depression_count`, `flat_count`,
`filled_cell_count`, `lowered_cell_count`, `synthetic_relief_cell_count`,
`obstruction_adjustments_width_1`, `obstruction_adjustments_width_2`,
`maximum_fildep_fill`, `maximum_fildep_cut`, and
`maximum_synthetic_relief`. Counts are nonnegative integers and measures are
finite nonnegative numbers. `parameters` has exactly
`max_obstruction_width`, integer `0`, `1`, or `2`.

TOPAZ stage measures use TOPAZ-rounded input; common `terrain_change` always
uses the original source raster.

## Integrity and Atomicity

The caller supplies `operation_id`. The producer writes a same-directory
temporary file named from it, flushes and `fsync`s, atomically renames it over
the requested sidecar, and propagates every write/sync/rename failure. The
final raster is written before the sidecar; successful exit requires both.

WEPPcloud resolves the fixed sidecar parent beneath the run root, rejects
symlinked parents/targets, removes a stale target before invocation, and
accepts only the expected operation id and basenames. Another attempt, tool,
input, or output is invalid.

## Reduced Payload and Transport

The worker stores `conditioning_diagnostics` in RQ metadata and emits compact
canonical JSON as unpadded URL-safe base64:

```text
rq:<job_id> TRIGGER DIAGNOSTICS_V1:<base64url> channel_delineation BUILD_CHANNELS_TASK_COMPLETED
```

Decoded content is at most 4 KiB and has exactly `schema_version` (`1`),
`root_job_id`, `producer_job_id`, `operation_id`, `method`
(`fill|breach|breach_least_cost|topaz`), `elevation_unit` (`m`), finite
nonnegative `maximum_raise` and `maximum_cut`, and printable plain-text
`summary` (1-1,000 characters, no control characters).

The open `jobstatus` response from
`get_wepppy_rq_job_status` adds top-level `conditioning_diagnostics` when the
tree contains exactly one finished `build_channels_rq` descendant with valid
diagnostics. It is the same reduced object. `root_job_id` equals the submitted
and polled aggregate root; `producer_job_id` equals the build-channel child.
For a directly submitted build job both values are equal. The existing
top-level `job_id` equals `root_job_id`. Zero matching descendants omits the
field only while nonterminal or for non-WBT jobs; a terminal successful WBT
tree without exactly one valid matching object is
`wbt_conditioning_diagnostics_invalid`, not successful. More than one matching
descendant is inconsistent and fails likewise.

Live/poll payloads require `root_job_id` to equal the active submission and
`producer_job_id` to equal that root or one registered descendant; malformed,
oversized, unsupported, or cross-job payloads are ignored and logged.
For a terminal WBT success, ignored/missing diagnostics instead convert client
completion to a visible controlled error rather than a success event. Same-job
replay is idempotent. Controllers render only `summary` as text.

## Controlled Consumer Failure

Invalid diagnostics after native success produce:

- `error.code="wbt_conditioning_diagnostics_invalid"`;
- message `Channel delineation stopped because terrain-conditioning diagnostics could not be verified. No successful channel result was published. Build channels again; if the problem continues, contact support with the Error ID.`;
- `error.details.reason`: `missing|oversized|path|malformed|schema|identity|inconsistent`;
- correlation `error_id`.

Completion, trigger, and timestamp publication are suppressed. The worker
removes the invalid sidecar and new conditioning raster and invalidates
downstream channel artifacts under the existing watershed lock. Raw sidecar
content never enters job metadata; internal detail is logged by `error_id`.

## Release and Rollback

Install and execute-verify the new WBT binary on every worker before deploying
WEPPpy. Retain the previous binary and SHA-256. Roll back WEPPpy first, then
WBT. Mixed-version tests prove old WEPPpy/new WBT compatibility and controlled
new WEPPpy/old WBT failure.
