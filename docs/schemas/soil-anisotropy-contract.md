# Soil anisotropy advanced options (SA-01)

Status: accepted contract checkpoint; implementation conformance pending.

## User inputs and eligibility

The Soil Options section of WEPP Advanced Options exposes optional dimensionless `soil_anisotropy_upper` and `soil_anisotropy_lower` numeric overrides. Blank means retain original values for that depth class. Missing legacy attributes read None; omitted request keys preserve saved settings; explicit null or blank clears that override. No override is enabled by default. Upper values must be finite numbers in [1,100], lower in [1,10]; reject booleans, malformed/multiple values, NaN and infinities without changing saved settings.

Editing requires both MOFE (`multi_ofe`) and hourly water balance/deep seepage (`run_wepp_ui`). The controls remain visible but disabled with an eligibility explanation otherwise. Existing read-only controls remain authoritative. The UI says “Values above 10 can cause numerical instabilities.” Enforce eligibility server-side before mutation; nonempty submitted overrides on an ineligible run fail using the existing validation error contract. Explicit clearing is safe even if the run is ineligible. Saved overrides remain stored when eligibility is turned off, but do not affect prepared soil files until eligibility returns. The existing routine-toggle request must succeed before inputs become editable; failure must not imply saved eligibility.

## Horizon and file semantics

Use cumulative horizon bottom depth in millimeters: <=500 is upper, >500 is lower. Do not split horizons; a horizon crossing 500 mm receives the lower override. Bottom-depth classification was presented to the operator as the minimal assumption; retain it unless the operator requests layer splitting. Apply classification after existing minimum-depth extension and maximum-depth clipping, in every OFE. Require positive finite, nondecreasing depths per OFE; tolerate repeated terminal depths produced by existing non-upload clipping at an exact horizon boundary. Do not change that historical clipping behavior. Unset classes retain original ratios, including admitted zero, without imposing new override bounds on source values. Override only the anisotropy field; preserve depths, OFE count, all other fields and existing saturation/kslast/depth precedence.

Support per-horizon anisotropy formats 7778 and 9001/9002/9003/9005. A requested active override on a format without per-horizon anisotropy fails explicitly before writing that prepared soil; never migrate uploaded 7777/2006 inputs or reinterpret profile anisotropy. Unset overrides preserve their existing preparation. Revalidate stored active override values and effective hourly enablement at preparation, including explicit preparation-time routine overrides; inactive settings never leak into a non-hourly or non-MOFE preparation.

## Native and persistence boundaries

WEPPpy owns requests, current eligibility, NoDb locking and file orchestration. A narrow Rust function in wepppyo3 owns finite range checks, depth validation and horizon value selection. Pass parsed depths and optional original ratios in memory, validate the whole request before returning values, then update the existing parsed soil object. No Python numerical fallback if the required native function is unavailable. Do not create a second soil-file transformation pass.

For advanced-option preparation, read each selected source once and write its prepared destination once. Native upload validation and parsing share the same source snapshot. Symbolic parameter resolution reuses the already-read source snapshot, preserving existing formulas and rounding; no second source open. File copies needed to materialize archives and separate consumers such as soil-version detection are not a new advanced-option pass. Prepared `wepp/runs/p*.sol` is the acceptance artifact; original `soils/*` inputs stay unchanged. Existing browse/download/archive visibility, error, locking and response contracts remain in force.

## Validation

Cover absent, cleared, populated, legacy, inactive and malformed saved/request states. Verify boundary depths below/at/above 500 mm and a crossing horizon, ranges/finite values, multiple OFEs, clipping order, unsupported native formats, disabled/read-only UI and failed routine toggles. Exercise real parser persistence/reload and current rebuilt Rust output. Count actual source reads/destination writes in ordinary, symbolic and uploaded-native preparation, compare all unrelated fields and original hashes, and retain actual generated files readable through normal project tools. Scientific stability beyond the stated warning is not claimed.
