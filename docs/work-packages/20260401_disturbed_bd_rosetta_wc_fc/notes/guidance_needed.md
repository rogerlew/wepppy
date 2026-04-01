# Guidance Needed Before Implementation

Confirmed guidance:

## 1) Moisture field terminology (Confirmed)
- Request text says both `wc/fc` and `wc/fs`.
- Confirmed interpretation: recompute WEPP horizon `wp` (wilting point water content) and `fc` (field capacity).

## 2) Recompute scope (Confirmed)
- Confirmed scope: top horizon only.
- Rationale: parameterization is intended to model pre-vs-post wildfire effects on soil.

## 3) Invalid bd content handling (Confirmed)
- Empty `bd` cells are valid and treated as no override.
- Content that is not numeric (for example `10.0.0`) is a hard error.

## 4) BD validation bounds (Confirmed)
- Precedent found in WEPPpy docs: realistic Rosetta bulk-density range `0.8-2.0 g/cm^3`.
- Precedent found in WEPP-Forest source (`src/scon.for`): computed consolidated BD clamped to `1.0-1.8 g/cm^3` (`1000-1800 kg/m^3`).
- Confirmed policy: enforce developer-oriented disturbed lookup `bd` bounds `0.6-2.2 g/cm^3` (margin on both ends).
