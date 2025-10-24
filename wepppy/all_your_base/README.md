# all_your_base

> Cross-cutting utilities and helper functions for the wepppy erosion modeling stack.

> **See also:** [AGENTS.md](../../AGENTS.md) for testing patterns and type hint conventions.

![ALL YOUR BASE ARE BELONG TO US](https://github.com/rogerlew/all_your_base/raw/main/Aybabtu.png)

## Overview

`wepppy.all_your_base` is a foundational utility library that provides the glue holding together the WEPP cloud stack. It collects commonly needed functionality that doesn't fit cleanly into domain-specific modules, enabling other packages to share implementations without introducing heavyweight dependencies.

The module provides:
- **Numeric helpers**: Parsing, clamping, type detection, and unit conversion
- **Data utilities**: JSON serialization, nested iteration, range compression
- **Color manipulation**: RGBA/CMYK conversion and random color generation
- **Domain-specific subpackages**: Date/time, geospatial, hydrologic, and statistical tools

This library serves as the lowest-level dependency in the wepppy stack, intentionally kept lightweight and focused on reusable primitives that higher-level modules can compose into domain logic.

## Components

### Core Module (`all_your_base.py`)

The main module exports general-purpose helpers and constants:

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

### Subpackages

- **`dateutils/`**: Timezone-aware date arithmetic, formatting helpers, and calendar utilities for climate data processing.
- **`geo/`**: Geospatial tooling including GDAL wrappers, raster transformers, coordinate system utilities, and web service clients.
- **`hydro/`**: Hydrologic calculations, flow routing helpers, and calibration objective functions for model validation.
- **`stats/`**: Statistical summaries, probability distributions, and data analysis helpers for generating report outputs.
- **`sys/`**: System-level utilities and platform detection helpers.

See individual subpackage READMEs for detailed API documentation.

## Quick Start

### Basic Numeric Helpers

```python
from wepppy.all_your_base import clamp, clamp01, isint, isfloat, try_parse

# Constrain values to ranges
temperature = clamp(105.7, minimum=0.0, maximum=100.0)  # → 100.0
opacity = clamp01(1.5)  # → 1.0

# Type detection
isint("42")       # → True
isfloat("3.14")   # → True
isint("3.14")     # → False

# Safe parsing with fallback
try_parse("42")       # → 42 (int)
try_parse("3.14")     # → 3.14 (float)
try_parse("invalid")  # → "invalid" (original)
```

### Unit-Aware Data Parsing

```python
from wepppy.all_your_base import RowData, parse_name, parse_units

# Extract units from column headers
name = parse_name("Sediment Yield (tons/acre)")   # → "Sediment Yield"
units = parse_units("Sediment Yield (tons/acre)") # → "tons/acre"

# Work with unit-aware row data
row = RowData({"Sediment Yield (tons/acre)": 0.42, "Year": 2023})
for name, value, units in row:
    print(f"{name}: {value} {units}")
# Output:
# Sediment Yield: 0.42 tons/acre
# Year: 2023
```

### Range Compression

```python
from wepppy.all_your_base import find_ranges

# Compress sorted integers into ranges
topaz_ids = [1, 2, 3, 8, 10, 11, 12, 15]
ranges = find_ranges(topaz_ids, as_str=True)  # → "1-3, 8, 10-12, 15"

# Get range tuples for programmatic use
range_tuples = find_ranges(topaz_ids)  # → [(1, 3), (8, 8), (10, 12), (15, 15)]
```

### Color Utilities

```python
from wepppy.all_your_base import RGBA, cmyk_to_rgb

# Create RGBA colors
red = RGBA(255, 0, 0, 255)
hex_color = red.tohex()  # → "#FF0000FF"

# Generate random colors
random_color = RGBA.random()

# Convert CMYK to RGB
rgb = cmyk_to_rgb(0.0, 1.0, 1.0, 0.0)  # → (1.0, 0.0, 0.0) (red)
```

### JSON Serialization

```python
import json
import numpy as np
from wepppy.all_your_base import NumpyEncoder

data = {
    "values": np.array([1.5, 2.7, 3.9]),
    "count": np.int32(42),
    "mean": np.float64(2.7)
}

# Standard json.dumps would fail on NumPy types
json_str = json.dumps(data, cls=NumpyEncoder)
# Successfully serializes NumPy arrays and scalars
```

## Integration Patterns

### Using in NoDb Controllers

```python
from wepppy.all_your_base import isint, try_parse
from wepppy.nodb.base import NoDbBase

class MyController(NoDbBase):
    def validate_topaz_id(self, value):
        if not isint(value):
            raise ValueError(f"Invalid topaz_id: {value}")
        return int(value)
    
    def parse_user_input(self, raw_value):
        # Safely parse numeric input with fallback
        return try_parse(raw_value)
```

### Working with Report Data

```python
from wepppy.all_your_base import RowData, parse_name, parse_units

def process_wepp_output(csv_path):
    """Process WEPP output CSV with unit-aware parsing."""
    with open(csv_path) as f:
        headers = next(f).strip().split(',')
        for line in f:
            values = line.strip().split(',')
            row = RowData(dict(zip(headers, values)))
            
            for name, value, units in row:
                print(f"{name}: {value} {units}")
```

## Developer Notes

### Type Hints

The module includes comprehensive type hints via `all_your_base.pyi` stub file. Use mypy for type checking:

```bash
wctl run-mypy wepppy/all_your_base
```

### Testing

Run the test suite to validate numeric parsing and serialization:

```bash
wctl run-pytest tests/test_all_your_base.py
```

Individual subpackages have their own test modules:
- `tests/test_all_your_base_dateutils.py` - Date/time utilities
- `tests/test_all_your_base_hydro.py` - Hydrologic calculations
- `tests/test_all_your_base_stats.py` - Statistical helpers

### Common Patterns

**Always use predicates before coercion:**
```python
# Good
if isint(value):
    int_value = int(value)
else:
    # Handle non-integer case

# Better
int_value = try_parse(value)  # Returns original on failure
```

**Unit parsing in report generation:**
```python
# Extract clean column names for database storage
raw_header = "Sediment Yield (tons/acre)"
clean_name = parse_name(raw_header)  # "Sediment Yield"
units = parse_units(raw_header)      # "tons/acre"
```

**Range compression for UI display:**
```python
# Convert large ID lists into compact strings
selected_ids = [1, 2, 3, 5, 7, 8, 9, 15]
display = find_ranges(selected_ids, as_str=True)  # "1-3, 5, 7-9, 15"
```

### Infrastructure Requirements

The runtime environment should provide:
- **Geospatial data mount**: `/geodata` (or `GEODATA_DIR` environment variable)
- **Shared memory**: `/dev/shm` tmpfs mount with sufficient capacity for temporary artifacts
- **NumPy**: Required for `NumpyEncoder` and numeric operations

These requirements are typically satisfied by the Docker development and production environments.

## Further Reading

- [AGENTS.md](../../AGENTS.md) - Development guidelines and testing patterns
- [all_your_base.pyi](all_your_base.pyi) - Type stub definitions
- [tests/](tests/) - Test suite examples
- Subpackage READMEs:
  - `dateutils/README.md` - Date/time utilities
  - `geo/README.md` - Geospatial tools
  - `hydro/README.md` - Hydrologic calculations
  - `stats/README.md` - Statistical helpers

## Credits

Original "ALL YOUR BASE ARE BELONG TO US" reference from the 1991 video game *Zero Wing*.

License: BSD-3 Clause (see [LICENSE](LICENSE))
