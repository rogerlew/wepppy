# Output Parity (2026-04-27)

## Gate Result

`confirmed`: Output parity is blocked. The Python comparator failed before producing complete native outputs, so runtime comparisons are not valid.

`confirmed`: Peridot completed on the same copied TOPAZ fixture and produced current watershed outputs.

## Required File Presence

| Output | Python Comparator | Peridot Comparator | Parity Status |
| --- | --- | --- | --- |
| `watershed/hillslopes.parquet` | missing; comparator failed before table output | present | blocking mismatch |
| `watershed/channels.parquet` | missing; comparator failed before table output | present | blocking mismatch |
| `watershed/flowpaths.parquet` | missing; comparator failed before table output | present | blocking mismatch |
| Hillslope slope files | partial: six `hill_*.slp` files before failure | present: eight files under `watershed/slope_files/hillslopes/` | blocking mismatch |
| Channel slope files | missing | present: `watershed/slope_files/channels.slp` | blocking mismatch |
| Flowpath slope files | missing | present: eight bundled `fps_*.slps` files | blocking mismatch |
| Network/structure output | missing | present: `watershed/network.txt` | blocking mismatch |

## Peridot Table Schemas

`confirmed`: Peridot `hillslopes.parquet` rows: `8`.

```text
topaz_id int32
slope_scalar float64
length float64
width float64
direction float64
aspect float64
length_estimate_mode object
length_area_over_channel float64
length_edge_median float64
area int32
elevation float64
centroid_px int32
centroid_py int32
centroid_lon float64
centroid_lat float64
```

`confirmed`: Peridot `channels.parquet` rows: `3`.

```text
topaz_id int32
slope_scalar float64
length float64
width float64
direction float64
order int32
aspect float64
area float64
elevation float64
centroid_px int32
centroid_py int32
centroid_lon float64
centroid_lat float64
```

`confirmed`: Peridot `flowpaths.parquet` rows: `614`.

```text
topaz_id int32
fp_id int32
slope_scalar float64
length float64
width float64
direction float64
aspect float64
area float64
elevation float64
order int32
centroid_px int32
centroid_py int32
centroid_lon float64
centroid_lat float64
```

## ID Coverage

`confirmed`: Expected input TOPAZ hillslope IDs are `22, 23, 31, 32, 33, 41, 42, 43`.

`confirmed`: Expected input TOPAZ channel IDs are `24, 34, 44`.

`confirmed`: Peridot output coverage:

- `hillslopes.parquet`: `22, 23, 31, 32, 33, 41, 42, 43`
- `channels.parquet`: `24, 34, 44`
- `flowpaths.parquet`: parent `topaz_id` coverage `22, 23, 31, 32, 33, 41, 42, 43`

`confirmed`: Python output coverage is incomplete because the smoke run failed after writing only these partial files:

```text
hill_22.slp
hill_23.slp
hill_31.slp
hill_32.slp
hill_33.slp
hill_41.slp
```

## Network and Structure Consistency

`confirmed`: Peridot wrote `watershed/network.txt` with:

```text
24|34,44,24
```

`confirmed`: Python did not reach `abstract_structure()` completion, so no Python network or structure output was available for comparison.

## Conclusion

`confirmed`: Parity is not adequate for timing claims.

`inference`: The observed Peridot output appears internally complete for the smoke fixture because required tables, slope bundles, and network output exist with expected TOPAZ ID coverage.

`hypothesis`: After fixing the Python comparator failure, the next parity pass should compare normalized Python summary objects against Peridot parquet rows because the legacy Python path does not natively emit the same table contract.
