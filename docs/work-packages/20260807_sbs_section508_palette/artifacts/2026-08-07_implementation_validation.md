# SBS-A11Y-01 Implementation Validation

**Date**: 2026-08-07 UTC

## Observable Contract

Synthetic GDAL fixtures verify the non-shifted palette entries:

| Class | RGBA |
| --- | --- |
| Unchanged / unburned (`0`) | `0,128,128,255` |
| Low (`1`) | `82,204,204,255` |
| Moderate (`2`) | `255,232,32,255` |
| High (`3`) | `168,0,0,255` |
| Masked / unmappable (`255`) | `255,255,255,0` |

The same fixtures verify that the default export retains the prior shifted
palette and that `export_palette="legacy"` selects the table above. Run-page
and GL Dashboard tests exercise both toggle directions. The shifted colors,
toggle DOM, persisted state key, and client recoloring remain unchanged.

Byte and Int16 fixtures cover band-declared, explicit, exact-white, and inferred
NoData. Model-facing data maps those cells to class `130`; coverage excludes
them; color-relief and four-class exports render them transparent; and the
interchange raster writes value `255`. The Int16 fixture uses NoData `-9999` to
prove that Python fallback classification does not truncate native values.

BAER-specific tests inspect the generated color-relief table and command line,
including the four canonical RGBA entries, transparent NoData, and `gdaldem
color-relief -alpha`. Disturbed uses the shared SBS RGBA exporter and its native
legend now matches the non-shifted table.

## Automated Evidence

- Full Python suite before the final localized NoData hardening: `5935 passed,
  61 skipped`.
- Post-hardening SBS regression set: `46 passed`.
- Full frontend suite: `105` suites and `758` tests passed.
- Focused two-mode frontend set: `5` suites and `53` tests passed.
- Companion Rust SBS unit tests: `3 passed`.
- `stubtest`, stub completeness, frontend lint, documentation lint,
  broad-exception enforcement, and diff checks passed.

The installed WEPPpy Rust extension predates the companion NoData correction.
Masked exports therefore intentionally retain the Python path until that Rust
source is released. Unmasked exports remain accelerated. The companion unit
test proves that its export classifier writes NoData as `255` while its
model-facing classifier retains the class-`130` fallback.

All raster evidence is generated in temporary test directories. It contains no
production run identifiers, paths, credentials, or raster metadata.
