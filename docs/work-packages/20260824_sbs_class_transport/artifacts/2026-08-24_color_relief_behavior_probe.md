# `gdaldem color-relief` Behavior Probe

**Date**: 2026-08-24  
**Author**: Claude Code  
**Evidence class**: **executional** - GDAL 3.10.1 was actually invoked on
synthetic rasters. Inputs retained in `gdal_probe/`.

## Why

Revision 3 specifies two producer changes: make the color table total, and pass
`-exact_color_entry`. Both rest on assumptions about undocumented-in-practice
`gdaldem` behavior. Those assumptions were tested rather than reasoned about.

## Method

Tiny AAIGrid rasters converted to GTiff, run through
`gdaldem color-relief -alpha` with and without `-exact_color_entry`, sampled with
`gdallocationinfo -valonly`.

## Results

### 1. `nv` is honored in exact mode

NoData renders `(0,0,0,0)` in both modes. Adding `-exact_color_entry` does not
break NoData handling. **Assumption confirmed.**

### 2. A value with no entry renders transparent in exact mode

In exact mode any unmatched value becomes `(0,0,0,0)`, not black. A hole in the
table therefore fails visibly-as-absent rather than as a wrong color.
**Assumption confirmed.**

### 3. Default mode interpolates BETWEEN entries

Table entries at `1` and `10` only; value `5` renders `(75,71,71)` - a color in
neither entry. **Confirms the revision-2 reviewer's interpolation finding.**

### 4. Default mode CLAMPS outside the entry range - and this was not anticipated

With the same table, value `12` (above the top entry) renders `(168,0,0)` and
value `0` (below the bottom entry) renders `(0,128,128)`. Both are **legitimate
severity colors**.

This is materially worse than interpolation. An unassigned palette index whose
raster value falls outside the recognized range is baked as a real severity
color, indistinguishable - visually and to any client-side decoder - from a
pixel the user actually classified.

### 5. Float rasters match exactly, given full-precision table keys

Float32 values including non-binary-exact ones (`0.1`, `0.3`) match under
`-exact_color_entry`, because `_normalize_count_value` yields a Python float
whose default repr round-trips. The table writer must keep full precision; a
truncated format string would silently transparent-out every pixel of a float
raster.

## Consequence: a correction to the revision-3 contract

Contract clause 6 says any opaque pixel outside the decode domain is unassigned.
That remains true, but it does **not** make client decoding a complete remedy for
historical artifacts, and revision 3 said or implied it did.

**Clamped pixels are inside the decode domain.** They decode as a valid severity
and will keep rendering as that severity. No client-side rule can detect them,
because there is nothing to detect: the stored pixel is a legitimate palette
color.

Therefore:

- The producer fix is **load-bearing**, not defense in depth. It is the only
  thing that corrects clamped pixels, and only on re-validation.
- `-exact_color_entry` is likewise load-bearing: it converts the clamp/interpolate
  failure modes into a visible-absent failure mode.
- The claim that existing runs render correctly through client decoding must be
  **withdrawn** for clamped pixels and restated precisely.

## Residual, unquantified

How many existing runs contain clamped pixels is unknown. It requires an
unassigned index whose value lies outside the recognized range - plausible when a
raster carries legend, annotation, or mask colors at the high or low end of its
palette. Quantifying this needs an inventory pass over run artifacts and is not
attempted here.
