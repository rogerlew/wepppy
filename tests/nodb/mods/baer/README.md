# BAER Module Tests

Tests for the Burned Area Emergency Response (BAER) module components.

## Test Suites

### test_sbs_map.py

Comprehensive unit test suite for `sbs_map.py` (Soil Burn Severity Map classification).

**Coverage: 27 tests across 6 test classes**

#### Test Classes

1. **TestSBSMapHelpers** (6 tests)
   - Tests core classification functions (`classify`, `ct_classify`)
   - Validates break-based and color-table-based classification
   - Tests offset application and nodata handling

2. **TestColorTableMaps** (4 tests)
   - Tests SBS maps with GDAL color tables
   - Sequential values (0, 1, 2, 3)
   - Non-sequential values (0, 1, 3)
   - Unknown colors not in standard lookup
   - Color table extraction

3. **TestNonColorTableMaps** (4 tests)
   - Tests SBS maps without color tables
   - 4-class maps (sequential and non-sequential)
   - BARC-style 0-255 range maps
   - Maps with nodata values

4. **TestSBSMapProperties** (3 tests)
   - Tests `class_map` property (pixel→severity label mapping)
   - Tests `burn_class_counts` aggregation
   - Tests `export_4class_map` output

5. **TestSBSMapSanityCheck** (4 tests)
   - Validates `sbs_map_sanity_check` function
   - Tests valid color table maps
   - Tests valid non-color-table maps
   - Tests error conditions (missing files, invalid projections)

6. **TestEdgeCases** (4 tests)
   - Single-value maps
   - Missing severity classes
   - Large gaps in pixel values
   - `ignore_ct` flag behavior

7. **TestClassificationConsistency** (2 tests)
   - Verifies color-table vs breaks produce same results
   - Tests classification result caching

#### Key Features

**Synthetic GeoTIFF Generation:**
- `GeoTiffTestHelper` class creates test rasters with:
  - Optional GDAL color tables
  - Configurable nodata values
  - Valid UTM projection
  - Proper TIFF compression

**Color Table Scenarios:**
- Standard SBS colors (aquamarine, yellow, red)
- Custom color mappings
- Unknown/unrecognized colors (default to nodata=255)

**Non-Color Table Scenarios:**
- 4-class maps (0-3 values)
- BARC-style continuous (0-255 range)
- Non-sequential pixel values (e.g., 0, 1, 3)
- Automatic break inference

**Classification Logic:**
- Break-based: `classify(value, breaks, nodata_vals, offset=130)`
- Color-table-based: `ct_classify(value, ct_dict, offset=130)`
- Both methods produce burn class codes: 130 (unburned), 131 (low), 132 (moderate), 133 (high)

#### Running Tests

```bash
# Run full suite
wctl run-pytest tests/nodb/mods/baer/test_sbs_map.py -v

# Run specific test class
wctl run-pytest tests/nodb/mods/baer/test_sbs_map.py::TestColorTableMaps -v

# Run specific test
wctl run-pytest tests/nodb/mods/baer/test_sbs_map.py::TestColorTableMaps::test_color_table_with_unknown_colors -v
```

#### Test Data

All tests use synthetic GeoTIFFs created in temporary directories (cleaned up after each test). No external data files required.

#### Key Assertions

- Color table presence/absence detection
- Correct break inference for different value distributions
- Proper classification: pixel values → burn class codes
- `class_pixel_map` structure: `{'pixel': 'burn_class_code'}`
- is256 flag for BARC-style vs 4-class detection
- Classification consistency between methods
- Result caching behavior

## Related Documentation

- `wepppy/nodb/mods/baer/sbs_map.py` - Implementation
- `docs/dev-notes/uniform_sbs_fix_2025-01-05.md` - Recent color table preservation fix
- `tests/nodb/mods/test_disturbed_uniform_sbs.py` - Integration tests for uniform SBS generation
