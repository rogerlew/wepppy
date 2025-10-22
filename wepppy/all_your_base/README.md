# all_your_base

![ALL YOUR BASE ARE BELONG TO US](https://github.com/rogerlew/all_your_base/raw/main/Aybabtu.png)

## Overview

`wepppy.all_your_base` collects the cross-cutting utilities that glue together
the WEPP cloud stack. The module exposes constants, numeric helpers, unit
parsing, light-weight color manipulation, and JSON serialization support that
other packages import without needing heavier dependencies.

## Module Organization

- `all_your_base.py` – general-purpose helpers and constants (detailed below).
- `dateutils/` – timezone-aware date arithmetic and formatting helpers.
- `geo/` – geospatial tooling (GDAL wrappers, raster transformers, web clients).
- `hydro/` – hydrologic calculations and calibration objective functions.
- `stats/` – statistical summaries and probability helpers for report outputs.
- `tests/` – regression coverage for numeric, parsing, and serialization paths.
- `Aybabtu.png` – the canonical “ALL YOUR BASE” banner kept for posterity.

## Function Catalog

| Symbol | Type | Summary |
| --- | --- | --- |
| `NCPU` | `int` constant | Worker count reserved for CPU-bound fan-out utilities. |
| `RGBA` | Named tuple | RGBA color helper with `tohex()` and random color generation. |
| `NumpyEncoder` | `json.JSONEncoder` subclass | Serializes NumPy scalars and arrays during JSON dumps. |
| `cmyk_to_rgb` | Function | Converts CMYK components into normalized RGB triples. |
| `flatten` | Generator | Yields scalars from arbitrarily nested iterables. |
| `find_ranges` | Function | Compresses sorted integers into inclusive range tuples or strings. |
| `clamp` | Function | Restricts a numeric value to an arbitrary inclusive range. |
| `clamp01` | Function | Specialized clamp that bounds values between 0.0 and 1.0. |
| `cp_chmod` | Function | Copies a file then applies a target permission mask. |
| `splitall` | Function | Breaks a path down into each filesystem component. |
| `isint` | Predicate | Detects values that round-trip cleanly to integers. |
| `isfloat` | Predicate | Detects values that can be coerced to floats. |
| `isbool` | Predicate | Accepts canonical boolean representations (0/1/True/False). |
| `isnan` | Predicate | Checks for `math.nan` while tolerating coercible inputs. |
| `isinf` | Predicate | Identifies positive or negative infinity candidates. |
| `try_parse` | Function | Best-effort coercion to `int` or `float`, returning the original on failure. |
| `try_parse_float` | Function | Gracefully converts to `float` with a configurable default. |
| `parse_name` | Function | Strips trailing unit metadata from column headings. |
| `parse_units` | Function | Extracts unit strings embedded in column headings. |
| `RowData` | Utility class | Row wrapper enabling prefix lookups and unit-aware iteration. |
| `c_to_f` | Function | Converts Celsius values to Fahrenheit. |
| `f_to_c` | Function | Converts Fahrenheit values back to Celsius. |

## Usage Notes

```python
from wepppy.all_your_base import RowData, clamp, find_ranges

value = clamp(1.7, minimum=0.0, maximum=1.0)
ranges = find_ranges([1, 2, 3, 8, 10, 11])

row = RowData({"Sediment Yield (tons/acre)": 0.42})
sediment, units = next(iter(row))
```

Pair the base helpers with the specialized subpackages (`dateutils`, `geo`,
`hydro`, `stats`) for domain-specific features—the catalog above stays focused
on the light-weight utilities re-used throughout the stack.

### Infrastructure Contract

The runtime environment must bind-mount shared geospatial assets at `/geodata`
(or set `GEODATA_DIR` appropriately). This contract lives outside
`wepppy.all_your_base`; service-specific modules are responsible for reading
the environment variable and resolving dataset paths. Temporary scratch
artifacts now write directly to `/dev/shm`, so ensure the container exposes
that tmpfs mount with sufficient capacity.
