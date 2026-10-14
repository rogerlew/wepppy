# ADR-0091: EDDE v2 experimental daily replay and PRISM spatial revision

Status: Accepted for feasibility and future-method scientific policy; application implementation/acceptance and deployment remain separate
Date: 2026-10-13

## Context

The operator requested EDDE v2 feasibility before WEPPcloud integration. Source daily files contain `PRECIP` in `kg m-2` (daily mm), `T2MAX` and `T2MIN` in K. Published grids have coastal cells marked ocean even when a requested hillslope is on land. EDDE is not bias corrected. This ADR authorizes explicit experimental transformations, not a new production climate default.

## Decision and change summary

Add an isolated EDDE adapter with no UI/NoDb/RQ wiring. Previously no EDDE workflow existed. Native projected-cell selection now checks cell-face bounds and requires `LANDMASK == 1`; reject outside/ocean cells rather than relocating to a neighboring land cell. No extra boundary buffer or distance cutoff is introduced; expose edge distance for assessment.

Convert precipitation `kg m-2` to mm with numerical factor 1, and temperature K to Celsius by subtracting 273.15. Require finite nonnegative precipitation and ordered temperature extrema, complete Gregorian daily years, and matching variable metadata. Do not bias correct. Use existing `df_to_prn` and `Cligen.run_observed` with an explicit station and seed; EDDE data are simulated even though the executable interface is named observed. Retain PRN rounding: 0.01 inch precipitation and integer Fahrenheit temperature. Expected CLI differences from source are bounded by 0.1771 mm and 0.3279 degrees C (half PRN quantum plus half CLI 0.1-unit quantum, with small floating-point allowance). These are format-parity bounds, not scientific accuracy thresholds.

Leave CLIGEN station-derived storm structure, radiation, wind, and dewpoint explicitly attributed to the station. Do not infer future change for these fields from daily precipitation/temperature alone. Do not change MX .5 P parameters or bypass CLIGEN quality guards. Retain source station location in the CLIGEN header and separately record requested point/native-cell location in the manifest; this limitation must be visible before any production use.

Multiple PRISM uses the existing `prism_revision` equations with explicit, retained 12-month reference and target normals: `P_target = P_source * normal_P_target / normal_P_reference`; `T_target = T_source + normal_T_target - normal_T_reference`. Require finite normals and strictly positive reference precipitation. Use identical normal pairs for historical and future runs. No adjustment to wet-day occurrence and no second bias correction. This adapter accepts saved normals to make acquisition identity inspectable and reproducible; the arithmetic follows `wepppy/climates/prism/__init__.py`. Exclude Multiple Interpolated initially.

The study defines a diagnostic wet day as precipitation >=1 mm for climatological frequency/spell statistics. This definition does not alter source values or CLIGEN input and differs from the positive-precipitation count used to measure PRN rounding losses.

An auxiliary diagnostic compares mean hourly-sampled shortwave W/m² with CLIGEN Langleys/day using `86400 / 41840`; it is an approximate daily-energy comparison, not a production radiation conversion. Dewpoint K is compared after subtracting 273.15.

## Decision provenance

Decision Venue: user/Codex conversation, 2026-10-13 (UTC).
Participants Present: repository operator and Codex.
Decision Owner: operator for package scope and Multiple PRISM requirement; Codex for bounded experimental implementation choices under authorized execution.
Implementer: Codex.
Initial acceptance covered experiments only. The subsequent operator decision below accepts the raw-projection and station-hybrid policy for the future application method.

## Rationale and alternatives

Daily replay preserves the modeled precipitation and temperature sequence with known existing format quantization. Fitting a new stochastic station distribution would introduce additional untested assumptions and discard temporal sequences. Restoring tiny precipitation after PRN rounding can create wet records without generated storm duration, so it is not performed. New bias correction, subhourly storm inference, nearest-land relocation, and finer-grid interpolation remain unapproved alternatives.

## Evidence and consequences

See [feasibility package](../work-packages/20261013_edde_v2_feasibility/package.md) and its `artifacts/` for native-grid rejection, daily extraction, source-unit metadata, historical quality, generated climate, PRISM parity, and WEPP execution evidence as execution proceeds. The operator accepts raw future EDDE with station-generated auxiliary fields as the intended hybrid method. Historical bias, grid-scale elevation limitations, station mismatch, finite ensemble, and unmodeled auxiliary-field climate responses remain disclosures, not requirements to invent corrections. This does not establish locally unbiased or fully projected future weather.

## Risk and rollback

All additions are isolated and existing methods/defaults remain unchanged. Do not enable WEPPcloud integration without an explicit disposition that addresses the station-field limitations, geography, period availability, and bias assessment. Revert the additive client/adapter if provenance, units, or generated-input parity fails. Retain failed experiment logs and manifests.

## Amendment: introduced PRISM inversions

ADR-0092 supersedes rejection/no-correction policy only for finite temperature inversions introduced by independent PRISM offsets: replace both adjusted extrema with their midpoint before serialization, following the [temperature-ordering contract](../schemas/prism-spatialization-temperature-contract.md). Development-stack conformance is verified in the [dedicated package report](../work-packages/20261013_prism_temperature_ordering/report.md). Preserve source validation, CLIGEN guards, other weather fields, and all unrelated rejection behavior. This is not a bias correction.

## Amendment: accepted future-method policy

Decision venue: operator/Codex conversation, 2026-10-13 Pacific (2026-10-14 UTC), after PRISM repair completion. Decision owner: repository operator. The operator directed using EDDE as provided with limitations, excluded correction of elevation effects, and accepted the hybrid as precedented.

Use EDDE future precipitation and temperature as provided, with source bias and the 12 km grid's limited representation of local elevation effects disclosed. Bias correction and additional elevation/lapse-rate correction are outside scope. Retain the established CLIGEN hybrid: station-generated storm structure/intensity, radiation, wind and dewpoint, with explicit field attribution. The operator accepts this precedented approach; deriving projected auxiliary fields is not an entry requirement. Existing unit conversion, PRN/CLI quantization, quality guards and optional Multiple PRISM spatialization (including ADR-0092 ordering repair) remain in scope and unchanged.

Rationale: correcting model bias and unresolved elevation effects would expand this bounded source integration into a separate scientific method. Reuse the existing daily-replay hybrid rather than require a new source-derived storm or auxiliary-weather method. Disclose that station-generated fields are not EDDE projections; precedent is the basis for method acceptance, not evidence that their future response has been validated. Locale/project eligibility, actual Canadian-project acceptance, operational contracts and regression gates remain integration work.
