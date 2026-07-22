# Additive SSURGO Fallback Schema Compatibility

**Status**: Required M1 contract; implementation pending
**Authority**: ADR-0025 and `wepppy/soils/ssurgo/fallback.md`

## Compatibility Rule

This rollout adds evidence only. It must not rename, remove, or change the
meaning of `raw_ssurgo_domsoil_d`, `domsoil_d`, `ssurgo_domsoil_d`, or existing
`ssurgo_substitution_d` keys. The global donor remains a mode of valid primary
collection outcomes; added candidate outcomes never enter that calculation.

## Additive Fields

| Field | NoDb representation | Parquet representation | Legacy hydration |
| --- | --- | --- | --- |
| `selection_policy` | nullable string | nullable string | `null` |
| `global_mukey` | nullable string/integer MUKEY | nullable string | `null` |
| `source_location_wgs84` | nullable `[longitude, latitude]` JSON value | nullable JSON string | `null` |
| `candidate_raster` | nullable JSON object | nullable JSON string | `null` |
| `search_radius_m` | nullable number | nullable floating-point value | `null` |
| `candidate_support` | nullable JSON list | nullable JSON string | `null` |
| `source_profile` | nullable JSON object | nullable JSON string | `null` |
| `selected_profile` | nullable JSON object | nullable JSON string | `null` |
| `fallback_reason` | nullable string | nullable string | `null` |

JSON Parquet values must round-trip without changing object/list shape. Empty
is permitted only where the policy has no evidence to report; it is not a
replacement for a required scalar. Existing consumers that do not read these
columns must continue unchanged.

## Required Propagation Evidence

The M1/M3 test helper must assert for every final hillslope assignment that:

1. the raw assignment is unchanged from the primary raster determination;
2. the final MUKEY mapping, NoDb state, and Parquet row agree;
3. the final soil file exists as a generated `.sol` artifact;
4. a local selection carries its source location and persisted candidate-raster
   identity; and
5. an unselected added candidate has no final mapping, Parquet output, or
   generated soil artifact.

Legacy fixtures must load missing fields as the values in the table. A
disconnected same-MUKEY fixture must demonstrate that separate source locations
can retain separate local donor evidence.
