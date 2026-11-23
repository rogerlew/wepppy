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
| STU texture, density, organic carbon, gravel | Emitted physical profile | Require finite usable values for emitted materials; zero individual texture/gravel values remain valid; reject empty/unbalanced texture and invalid density, with the [six-zero subsoil exception](#project-defaults-for-a-missing-subsoil-material) |
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

## Project defaults for a missing subsoil material

[ADR-0151](../adrs/ADR-0151-esdac-missing-subsoil-defaults.md) defines the fixed starting profile and its provenance. Conformance to this amendment is pending.

A gridded ESDAC project has one editable subsoil profile. Before any soil build, show the persisted profile or the fixed default when the persisted profile is absent or empty in Soil Options → Advanced options, with units and a description of where it applies. Eligibility follows actual soil dispatch, not the previous output's `soil_source`. Render this control for eligible ESDAC projects only, including fresh and failed projects. Submit its values only for gridded ESDAC. A malformed nonempty persisted profile fails explicitly with correction guidance. A request without the profile retains the saved setting or uses the fixed defaults. The six fields otherwise form one validated unit. Reject partial, blank, duplicate, Boolean, nonfinite and malformed fields before any mutation, and reject explicit active profile fields when a different soil builder applies.

Use the profile on every hillslope whose required subsoil has all six finite source material values equal to zero. Reject independent physical or structural errors. A profile with usable native subsoil or without a consumed subsoil interval bypasses the fallback. Preserve the source topsoil, depth and CEC categories, and target hydraulic inputs. Derive and validate the generated soil through the standard builder and downstream paths.

Bind the fully validated profile to its admitted attempt. A queued worker must consume that profile even if another request edits the project's settings. Failed enqueue or rejected admission preserves the prior settings and completion markers. Old jobs without a snapshot and direct callers resolve the applicable project setting at build time. A batch settings save without a job retains the same validated project setting. Keep explicit source identity through batch publication. The quality report distinguishes fallback as degraded, with the original missing-source observations, applied values and method. Include fallback provenance in the stable generated soil content so equivalent-file reuse preserves it. The Soils summary places a persistent `wc-alert wc-alert--warning` directly above the coverage table when its accepted artifacts used defaults. Use a visible heading, “Subsoil defaults applied,” and state the affected hillslope count and total. Link to details for that accepted build and identify where to edit the project profile. Announce the warning politely when the summary is refreshed. A count of zero shows no warning. Preserve the association on reload. A failed rebuild may show its own diagnostics. If it invalidates the last accepted soil release, clear that release’s summary and warning. A failed attempt’s quality report cannot supply a successful warning count.

## Format-aware Disturbed readback

Validate actual physical records and required provenance for the native format selected by the project. When a transformed ESDAC 7778 member has expected land-use and texture values, read exactly one occurrence of each required value from the final recognized Disturbed migration block in the pre-body writer comments. Missing, malformed, duplicate and mismatched entries fail with rebuild guidance. An invalid final block cannot fall back to an earlier one. For formats with native land-use and texture metadata, including 9001, 9002, 9003 and 9005, keep native parsed-field checks. Retain format, physical and version checks for base copies and final stacks, and verify transformed members before stacking.

A repeated MOFE member key in one build reuses the pending generation plan. The member must exist and pass validation before assembly. Validate existing reusable members before accepting them. The final stack keeps its normal physical and format readback.
