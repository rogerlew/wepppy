# Ordering Contract Matrix

Evidence class: `Static` + `Ran`

## Scope

Public map-returning APIs in `wepppyo3.raster_characteristics`:

- `count_intersecting_raster_key_pairs`
- `identify_mode_single_raster_key`
- `identify_mode_intersecting_raster_keys`
- `identify_median_single_raster_key`
- `identify_median_intersecting_raster_keys`

## Baseline and Hardened Contract

Baseline runtime probe and post-change probe both used the same synthetic raster fixture and repeated each API call 40 times.

| API | Pre-change boundary container/iteration risk | Pre-change observed order variants (40 calls) | Hardened boundary container | Post-change observed order variants (40 calls) | Contract after hardening |
| --- | --- | --- | --- | --- | --- |
| `count_intersecting_raster_key_pairs` | Already `BTreeMap<String, BTreeMap<String, usize>>` | outer: 1, inner: 1 | unchanged | outer: 1, inner: 1 | Deterministic outer and nested key order for identical inputs |
| `identify_mode_single_raster_key` | `HashMap<String, i32>` populated from `HashSet` traversal | outer: 6 | `BTreeMap<String, i32>` | outer: 1 | Deterministic outer key order for identical inputs |
| `identify_mode_intersecting_raster_keys` | `HashMap<String, HashMap<String, i32>>` with `HashMap`+`HashSet` traversal | outer: 6, inner: 2 per outer key | `BTreeMap<String, BTreeMap<String, i32>>` | outer: 1, inner: 1 | Deterministic outer and nested key order for identical inputs |
| `identify_median_single_raster_key` | `HashMap<String, f64>` populated from `HashMap` traversal | outer: 6 | `BTreeMap<String, f64>` | outer: 1 | Deterministic outer key order for identical inputs |
| `identify_median_intersecting_raster_keys` | `HashMap<String, HashMap<String, f64>>` populated from `HashMap` traversal | outer: 6, inner: 2 per outer key | `BTreeMap<String, BTreeMap<String, f64>>` | outer: 1, inner: 1 | Deterministic outer and nested key order for identical inputs |

## Evidence Snippets

Pre-change repeated-call probe (selected output):

- `identify_mode_single_raster_key`: `outer_order_variants= 6`
- `identify_mode_intersecting_raster_keys`: `outer_order_variants= 6`, inner order variants per key = `2`
- `identify_median_single_raster_key`: `outer_order_variants= 6`
- `identify_median_intersecting_raster_keys`: `outer_order_variants= 6`, inner order variants per key = `2`

Post-change repeated-call probe (selected output):

- All five public APIs: `outer_order_variants= 1`
- Nested-map APIs: inner order variants per key = `1`

## Semantic-Parity Guard

`tests/raster_characteristics/test_deterministic_ordering_contract.py` asserts deterministic order and expected mode/median/pair-count values in the same fixture used for ordering probes.
