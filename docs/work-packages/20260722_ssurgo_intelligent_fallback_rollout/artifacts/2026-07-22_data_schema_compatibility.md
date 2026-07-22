# Additive SSURGO Fallback Schema Compatibility

**Status**: Implemented contract; M3 propagation evidence pending
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

`ssurgo_candidate_preparation` is a separate additive NoDb status record. It
is `{ "status": "not_attempted", "affected_hillslopes": 0 }` for all-valid
primary builds; it does not alter substitution semantics or require a Parquet
column.

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

## Implementation Checkpoint (2026-07-22 UTC)

The implementation writes the nine provenance fields additively through
`Soils._subs_summary_gen()` and records `ssurgo_candidate_preparation` on the
NoDb controller. Targeted legacy/root-creation tests pass. M3 still must prove
the complete generated NoDb, Parquet, and `.sol` agreement on a real fixture;
this checkpoint does not claim that release evidence.
