# ESDAC soil source sufficiency

## Acceptance

Build when the available source data produce a valid WEPP profile. Missing descriptive data is an observable warning, not a reason to reject usable physical data. `valid` has no warnings; `degraded` is accepted with warnings; `rejected` has physical/structural errors. Authority: [ADR-0139](../adrs/ADR-0139-esdac-missing-metadata.md), amending [ADR-0043](../adrs/ADR-0043-eu-esdac-soil-quality-contract.md).

## Field policy

| Source | Role | Missing-data behavior |
| --- | --- | --- |
| `fao90lev1` | Soil name and key | Warning, explicit unknown label/key component |
| `dgh`, `dimp`, `dr` | Descriptive groundwater/rooting classes and keys; unused in physical derivation | Warning, unknown metadata |
| `usedom` | Forest switch | Warning; existing non-forest/code-zero albedo 0.15 and saturation 0.75; forest codes 5/22 retain 0.06/0.5 |
| `textdepchg`, `il` | Horizon depths | Reject missing/unsupported values; no guessed depths |
| `cec_top`, `cec_sub` | Horizon CEC | Require top CEC; require sub CEC only for emitted subsoil |
| STU texture, density, organic carbon, gravel | Emitted physical profile | Require finite usable values for emitted materials; zero individual texture/gravel values remain valid; reject empty/unbalanced texture and invalid density |
| HydroGrids conductivity | Restrictive-layer calculation | Existing partial-missing warnings accepted; all-missing/invalid coverage rejected |

## Diagnostics and compatibility

Optional absent, empty and malformed payloads are diagnosed with field and raw value before normalization. Unavailable optional raster lookups are warnings, but required provider errors remain failures. Serialization uses explicit unknown metadata rather than indexing absent tuples. Preserve known source values and existing successful keys. Keep `soil_quality.json` schema version 1 and its valid/degraded/rejected vocabulary. Single-OFE and MOFE disturbed consumers accept degraded inputs only when their actual generated files pass downstream validation.

## Artifacts and failure behavior

Retain raw diagnostics in the normal soils directory report and metadata warnings in generated soil comments. A rejected batch must not publish partial new soils. Keep content-collision detection when keys coincide. Retry through the normal builder after source correction; no manual editing of derived files is required. Existing physical output validation and 200 mm boundary handling remain authoritative.

## Availability evidence

The reproducible study builds every location in a seeded, spatially stratified manifest and all incident hillslopes. Report sampling frame, excluded nodata cells, accepted/degraded/rejected counts, reason counts and per-stratum availability. Parse actual generated files; file existence alone is insufficient. Results describe installed dataset coverage for the sampled frame, not universal European availability.

## Soil identity and retry

The legacy key rounds selected physical values and cannot uniquely identify all
profiles. Ignore volatile build-date and additive source-warning comments when comparing
generated content; normalize line endings. When distinct content shares a key, use the legacy prefix plus a full
SHA-256 suffix of stable content, and propagate that identity to dominant-soil
mappings, summaries and quality reports. Preserve existing files; identical
retries reuse them. Unexpected conflict at a resolved identity remains fatal.
Partial metadata preserves any available short class (including forest 5/22);
normalize only unavailable components and report their loss.

## Consumed horizons

When the mapped impermeable depth is at or above the mapped texture-change
boundary, emit only top material to that impermeable depth. A shallower total
profile does not require a second material below the soil boundary. Record both
source depths in `source.profile.single_horizon`; require subsoil STU and CEC
only for profiles that actually emit subsoil. Missing topsoil, unknown total or
texture-change depths and missing conductivity remain failures. The existing
200 mm material-preserving subdivision may split that single material into
multiple serialized rows. This changes previously rejected profiles, not
successful two-material parameterization.

Required categorical short codes are strings under the raster provider contract.
Missing pixel/description metadata preserves a usable short code and records a
warning, including for depth and CEC categories. Arbitrary non-string short-code
provider payloads are not a supported recovery input.
