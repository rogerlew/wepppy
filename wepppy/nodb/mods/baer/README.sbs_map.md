# SBS Map Utilities (`sbs_map.py`)

> Classifies Soil Burn Severity (SBS) rasters into canonical WEPP burn classes, whether the source raster uses numeric breaks or a color table.

> **See also:** [`../../AGENTS.md`](../../AGENTS.md) for NoDb controller conventions and test expectations.

## Overview

`wepppy/nodb/mods/baer/sbs_map.py` is the canonical SBS raster normalization module used by BAER and disturbed-land workflows. It accepts source rasters with or without color tables, validates map readiness, and produces stable class outputs used by WEPP pipelines and map clients.

The module supports two ingestion paths:
- Numeric-class rasters (4-class or BARC-like 0-255 ranges) using breakpoint classification.
- Palette rasters using GDAL color-table lookup mapped to SBS severities (`unburned`, `low`, `mod`, `high`).

The output contract is stable across both paths:
- Internal/export classes use the canonical ordering `0..3`.
- Runtime map-class mapping uses `130..133` (`130=unburned`, `131=low`, `132=moderate`, `133=high`).
- Unknown color-table indices map to `255` (NoData sentinel in classification contexts).
- `export_4class_map` writes the shifted (Okabe-Ito) palette by default for classes `0..3`.
- `export_4class_map(..., export_palette="legacy")` is available as an explicit transition mode when legacy RGB output is required.

## API

| Symbol | Purpose |
| --- | --- |
| `sbs_map_sanity_check(fname)` | Fast validity gate for uploads and batch ingestion. |
| `get_sbs_color_table(fn, color_to_severity_map=None)` | Reads GDAL color table and resolves severity index buckets. |
| `classify(v, breaks, nodata_vals=None, offset=0)` | Numeric breakpoint classification path. |
| `ct_classify(v, ct, offset=0, nodata_vals=None)` | Color-table index classification path. |
| `SoilBurnSeverityMap` | Main wrapper with class maps, counts, and export helpers. |

## Color Tables And Palette Contracts

**Source of truth:** This section is the canonical SBS color mapping contract for WEPPpy. If code and docs diverge, update code to match this mapping (or update this section in the same change when intentionally revising the contract).

The default RGB-to-severity lookup is defined in:
- `wepppy/nodb/mods/baer/data/sbs_color_map.json`
- Fallback constant `_DEFAULT_COLOR_TO_SEVERITY` in `wepppy/nodb/mods/baer/sbs_map.py`

Both lookup sources now treat the shifted SBS palette as first-class, not an exception path.

| Severity | Canonical class | Legacy RGB | Shift RGB (Okabe-Ito) |
| --- | --- | --- | --- |
| Unburned | `130` | `0,115,74` (`#00734A`) | `0,158,115` (`#009E73`) |
| Low | `131` | `77,230,0` (`#4DE600`) | `86,180,233` (`#56B4E9`) |
| Moderate | `132` | `255,255,0` (`#FFFF00`) | `240,228,66` (`#F0E442`) |
| High | `133` | `255,0,0` (`#FF0000`) | `204,121,167` (`#CC79A7`) |

### Okabe-Ito Details

The shifted SBS palette uses an Okabe-Ito-style set selected for universal design in data graphics:

- Strong hue separation between adjacent classes (`Unburned`, `Low`, `Moderate`, `High`).
- Better distinguishability across common color-vision differences than red/green-forward legacy schemes.
- Better robustness in mixed viewing conditions (projectors, screenshots, print, and field displays).
- Stable interpretation when combined with non-color cues (ordered classes and explicit labels).

### Why Accessible Palettes Should Be Preferred

Prefer accessible palettes over institutional legacy palettes for operational SBS products:

- They reduce misclassification risk when users cannot reliably separate legacy class colors.
- They improve consistency across agencies, contractors, and public-facing products with unknown display settings.
- They make map interpretation more reliable under stress, which is critical for post-fire planning and communication.
- They preserve inclusivity without changing model semantics or backend contracts.

Validation rule used by sanity checks:
- A color table is considered valid when at least one of `low`, `mod`, or `high` is recognized.

## Quick Start

```python
from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap, sbs_map_sanity_check

status, message = sbs_map_sanity_check("/path/to/sbs.tif")
if status != 0:
    raise RuntimeError(message)

sbs = SoilBurnSeverityMap("/path/to/sbs.tif")

# Raw value -> canonical class code strings ("130".."133", or "255")
pixel_map = sbs.class_pixel_map

# Human-facing grouped counts
counts = sbs.burn_class_counts

# Export normalized 4-class GeoTIFF
sbs.export_4class_map("/tmp/sbs_4class.tif")
```

Override lookup map (for controlled ingest experiments):

```python
custom_map = {
    (0, 158, 115): "unburned",
    (86, 180, 233): "low",
    (240, 228, 66): "mod",
    (204, 121, 167): "high",
}
sbs = SoilBurnSeverityMap("/path/to/sbs.tif", color_map=custom_map)
```

## Accessibility Guidance: Color-Shifted SBS Maps

Use this checklist when implementing or reviewing Color Shift behavior for universal design:

- Keep severity semantics stable. Color Shift must only change display color, never class meaning (`130..133`).
- Keep text labels present and explicit (`Unburned`, `Low`, `Moderate`, `High`) in legends and tooltips.
- Keep one-to-one class mapping across all surfaces: raster swatches, legend chips, tooltip chips, and exported screenshots.
- Keep unknown colors explicit. Unrecognized color-table entries should remain unmapped (`255`) rather than silently coerced.
- Prefer toggle wording that is neutral and universal-design oriented (for example `Apply Color Shift`).
- Ensure color is not the only channel. Always pair color with ordering, text labels, and/or numeric codes.

Recommended review cases before shipping:
- Shifted-palette GeoTIFF with all four classes.
- Mixed/partial color table with unknown indices.
- No-color-table raster path (breakpoint classification) to confirm no regression.

## Developer Notes

- Rust acceleration is used when available (`wepppyo3.sbs_map`); Python fallback remains authoritative for behavior.
- `_SBS_COLOR_MAP_PATH` is passed into Rust helpers so Python and Rust share the same palette contract.
- When updating color lookup behavior:
  - Update `sbs_map.py` fallback defaults.
  - Update `data/sbs_color_map.json`.
  - Update SBS tests that mirror lookup dictionaries.

Targeted tests:

```bash
wctl run-pytest tests/nodb/mods/baer/test_sbs_map_extended.py tests/sbs_map/test_sbs_map.py
```

## Further Reading

- `wepppy/nodb/mods/baer/sbs_map.py`
- `wepppy/nodb/mods/baer/sbs_map.pyi`
- `wepppy/nodb/mods/baer/data/sbs_color_map.json`
- `docs/ui-docs/ui-style-guide.md` (Color Shift universal-design guidance for UI controls)
