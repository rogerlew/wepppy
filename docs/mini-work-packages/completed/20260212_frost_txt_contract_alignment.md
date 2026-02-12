# Mini Work Package: `frost.txt` Contract Alignment and Advanced Control Exposure
Status: Completed
Last Updated: 2026-02-12
Primary Areas: `/workdir/wepp-forest/src/infile.for`, `wepppy/nodb/core/wepp.py`, `wepppy/nodb/core/wepp.pyi`, `wepppy/nodb/configs/_defaults.toml`, `wepppy/nodb/configs/legacy/_defaults.toml`, `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/frost.htm`, `tests/wepp/test_wepp_frost_opts.py`, `tests/weppcloud/routes/test_pure_controls_render.py`

## Objective
- Align WEPPpy `frost.txt` writing with the WEPP parser contract.
- Expose frost parameters in WEPPcloud advanced controls using WEPP variable names plus concise type/range hints.
- Record WEPP internal defaults used when `frost.txt` is absent.

## WEPP Source-of-Truth Contract
From `/workdir/wepp-forest/src/infile.for`:
- `open(..., file='frost.txt', err=301)` at `infile.for:1601`
- Required line 1 read: `wintRed, fineTop, fineBot` at `infile.for:1602`
- Required line 2 read: `ksnowf, kresf, ksoilf, kfactor(1), kfactor(2), kfactor(3)` at `infile.for:1604`
- Bounds/normalization checks at `infile.for:1610` through `infile.for:1618`

Required shape:
- Line 1: 3 integers
- Line 2: 6 floats

## Previous Incorrect WEPPpy State
Prior `_prep_frost()` wrote:
- `1  1  1`
- `1.0   1.0  1.0   0.5`

That second line only had 4 values, not the 6-value WEPP contract at `infile.for:1604`.

## WEPP Internal Defaults When `frost.txt` Is Missing
If `frost.txt` is not written/opened, WEPP branches to label `301` and sets:
- `fineTop = 10`
- `fineBot = 10`
- `wintRed = 1`
- `kresf = 1.0`
- `ksnowf = 1.0`
- `ksoilf = 1.0`
- `kfactor(1) = 1e-5`
- `kfactor(2) = 1e-5`
- `kfactor(3) = 0.5`

Reference: `/workdir/wepp-forest/src/infile.for:1621` through `/workdir/wepp-forest/src/infile.for:1629`.

## Revised WEPPpy Implementation

### 1) Typed frost option model
- Added `FrostOpts` in `wepppy/nodb/core/wepp.py` (+ stub in `wepppy/nodb/core/wepp.pyi`).
- `FrostOpts.contents` now writes compliant two-line output:
  - line 1: `wintRed fineTop fineBot`
  - line 2: `ksnowf kresf ksoilf kfactor1 kfactor2 kfactor3`

### 2) New default config section
- Added `[frost_opts]` defaults to:
  - `wepppy/nodb/configs/_defaults.toml`
  - `wepppy/nodb/configs/legacy/_defaults.toml`
- Defaults match WEPP internal defaults from `infile.for` (including `kfactor1=1e-5`, `kfactor2=1e-5`, `kfactor3=0.5`).

### 3) File writing behavior
- `_prep_frost()` now writes `self.frost_opts.contents` (contract-compliant shape).
- New `_mint_default_frost_file()` creates `runs/frost.txt` for new projects when absent.
- `Wepp.__init__()` now calls `_mint_default_frost_file()` during project setup.
- Minting is idempotent (does not overwrite an existing `frost.txt`).

### 4) Input validation and bounds
- Added guard constants and `_guard_frost_bounds()` in `wepppy/nodb/core/wepp.py`.
- Bounds mirror WEPP `infile.for` constraints:
  - `wintRed`: `0..1`
  - `fineTop`/`fineBot`: `1..10`
  - `ksnowf`/`kresf`/`ksoilf`: `0.1..10.0`
  - `kfactor*`: `(0..1]` with explicit `> 0` validation (no app-level epsilon floor)

## Advanced Control UI Changes
File: `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/frost.htm`

Implemented:
- Intro copy now states:
  - expected `frost.txt` shape (line 1: 3 ints, line 2: 6 floats)
  - if not written, WEPP uses internal defaults
- Added numeric fields for:
  - `wintRed`, `fineTop`, `fineBot`
  - `ksnowf`, `kresf`, `ksoilf`
  - `kfactor(1)`, `kfactor(2)`, `kfactor(3)`
- Labels use WEPP variable names.
- Help text includes concise type/range hints (`int` / `float`).
- `kfactor*` inputs keep `max=1.0` and rely on backend `> 0` validation instead of a hard HTML minimum.

Unitizer note:
- Frost controls are counts or dimensionless coefficients, so no unit conversion UI is needed.
- Numeric bounds and server-side guards enforce WEPP-aligned safe ranges.

## Validation
- `wctl run-pytest tests/wepp/test_wepp_frost_opts.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- Result: `13 passed`.

Key assertions covered:
- `FrostOpts.contents` emits 3+6 token structure.
- `FrostOpts.contents` preserves second-line value order expected by WEPP.
- `_prep_frost()` writes compliant `frost.txt`.
- `_mint_default_frost_file()` is idempotent.
- `_guard_frost_bounds()` resets invalid frost values (including NaN/inf and non-positive `kfactor*`) to WEPP defaults.
- `_guard_frost_bounds()` preserves tiny positive `kfactor*` values.
- Frost advanced template renders WEPP variable labels and does not impose a hard HTML minimum on `kfactor*` fields.
