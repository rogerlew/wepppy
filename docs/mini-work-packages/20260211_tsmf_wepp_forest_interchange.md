# Mini Work Package: TSMF Output in `wepp-forest` + Soil Interchange Compatibility
Status: Implemented
Last Updated: 2026-02-11
Primary Areas: `/workdir/wepp-forest/src/watbal.for`, `/workdir/wepp-forest/src/watbal_hourly.for`, `/workdir/wepp-forest/src/outfil.for`, `wepppy/wepp/interchange/hill_soil_interchange.py`, `wepppy/wepp/interchange/watershed_soil_interchange.py`, `tests/wepp/interchange/test_soil_interchange.py`, `tests/wepp/interchange/test_watershed_soil_interchange.py`

## Objective
- Add a true full-profile soil moisture fraction (`TSMF`) to WEPP soil text outputs.
- Ensure WEPPpy soil interchange accepts new `TSMF` outputs without breaking legacy and existing modern layouts.

## Problem Summary
- `wepp-forest` soil output exposed:
  - `Saturation` and `TSW` for the top 0.1 m layer.
- `wepp-forest` water output already exposed full-profile storage terms:
  - `Total-Soil Water` (unfrozen profile water),
  - `frozwt` (frozen profile water).
- Users needed a model-produced full-profile fraction in daily soil output, not only top-layer fraction.
- Interchange parsers previously required exact 12-column (legacy) or 14-column (modern) soil headers and would reject a new `TSMF` column.

## Scope
- `wepp-forest`:
  - Compute `TSMF` in both daily balance paths (`watbal.for`, `watbal_hourly.for`).
  - Extend soil output header and row format in `outfil.for`.
- WEPPpy interchange:
  - Add nullable `TSMF` field to hillslope and watershed soil schemas.
  - Parse three soil layouts:
    - legacy (`... Tauc`)
    - modern (`... Tauc Saturation TSW`)
    - modern + `TSMF` (`... Tauc Saturation TSW TSMF`)
  - Preserve legacy compatibility by filling missing fields as null.

## Non-goals
- No change to WEPP water balance equations beyond exposing a derived profile fraction.
- No backfill/rewrite of historical soil text files.
- No immediate Rust parser implementation for `TSMF`; Python fallback covers schema mismatch.

## Implementation Details

### 1) `wepp-forest`: `TSMF` generation
Formula implemented in both `watbal.for` and `watbal_hourly.for`:
- `por_profile = sum_i( por(i,iplane) * dg(i,iplane) )`
- `profile_total_water = watcon(iplane) + frozwt`
- `TSMF = profile_total_water / por_profile`
- Clamp: `TSMF` to `[0.0, 1.0]`
- Guard: if `por_profile <= 1e-12`, emit `TSMF = 0.0`

Files:
- `/workdir/wepp-forest/src/watbal.for`
- `/workdir/wepp-forest/src/watbal_hourly.for`
- `/workdir/wepp-forest/src/outfil.for`

Output changes:
- Soil header now includes `TSMF` with `frac` units.
- Soil row format now writes one additional trailing float (`f7.4`).

### 2) Hillslope soil interchange (`H*.soil.dat` -> `H.soil.parquet`)
File:
- `wepppy/wepp/interchange/hill_soil_interchange.py`

Changes:
- Added `TSMF` to schema metadata.
- Added `TSMF_HEADER`, `TSMF_UNITS`, and layout dispatch for the new header variant.
- Kept modern and legacy parsing intact.
- Missing `TSMF` is populated as null for modern and legacy files.

### 3) Watershed soil interchange (`soil_pw0.txt` -> `soil_pw0.parquet`)
File:
- `wepppy/wepp/interchange/watershed_soil_interchange.py`

Changes:
- Added `TSMF` to schema metadata.
- Added 3-layout parsing support.
- Added Rust-output schema check:
  - If Rust parser output schema does not match expected Python schema (`TSMF` included), code raises and falls back to Python parser path.

### 4) Tests and stubs
Tests:
- `tests/wepp/interchange/test_soil_interchange.py`
  - Added explicit `TSMF` layout parse test.
  - Updated compatibility expectations: legacy missing `Saturation`, `TSW`, `TSMF`; modern missing `TSMF`.
- `tests/wepp/interchange/test_watershed_soil_interchange.py`
  - Added explicit `TSMF` layout parse test.
  - Updated expected schema columns and compatibility expectations.

Type stubs:
- `stubs/wepppy/wepp/interchange/hill_soil_interchange.pyi`
- `stubs/wepppy/wepp/interchange/watershed_soil_interchange.pyi`

## Validation
- `wepp-forest` compile sanity (local tool availability):
  - `gfortran -c -ffixed-form -ffixed-line-length-none watbal.for watbal_hourly.for outfil.for` passed.
  - `make` with `ifx` was not runnable in this environment (`ifx` unavailable).
- WEPPpy tests:
  - `wctl run-pytest tests/wepp/interchange/test_soil_interchange.py tests/wepp/interchange/test_watershed_soil_interchange.py`
  - Result: `8 passed, 1 skipped`.

## Compatibility Contract
- Legacy soil files continue to parse and produce null for `Saturation`, `TSW`, and `TSMF` as applicable.
- Existing modern soil files continue to parse and produce null for `TSMF`.
- New `TSMF` soil files parse and emit populated `TSMF`.
- Watershed interchange remains robust if Rust parser lags schema updates (automatic Python fallback on schema mismatch).

## Follow-ups
1. Update Rust soil interchange parsers to emit `TSMF` in both hillslope and watershed paths.
2. Regenerate soil schema snapshot fixtures used by local parity flows once Rust schema is aligned.
3. Update user-facing interchange docs (`docs/dev-notes/wepp_interchange.spec.md`, interchange README tables) to include `TSMF`.
