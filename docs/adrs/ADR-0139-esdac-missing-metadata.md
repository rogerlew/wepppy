# ADR-0139: ESDAC missing descriptive metadata

Status: Accepted  
Date: 2026-11-06

## Context

All 35 hillslopes in `preservative-coercion` fail solely because FAO group labels are empty despite available physical inputs. The mandatory categorical list also includes unused descriptive depth classes. Missing landuse currently has inconsistent empty versus code-zero handling.

## Decision

Amend ADR-0043's required-categorical interpretation: require fields consumed by physical derivation (`textdepchg`, `il`, top/sub CEC), while `fao90lev1`, `dgh`, `dimp`, `dr` are optional descriptive metadata. Missing, empty or malformed optional tuples and unavailable optional lookups generate field-qualified warnings and explicit unknown metadata. `usedom` absence uses the existing code-zero non-forest branch with a warning (albedo 0.15, initial saturation 0.75); known forest values retain 0.06 and 0.5. No generic physical soil, nearest-neighbor substitution or new numerical formula is introduced. See the [source contract](../schemas/esdac-soil-source-contract.md).

## Decision Provenance

Decision Venue: Codex operator session, 2026-11-06, America/Los_Angeles.  
Participants Present: Roger (operator), Codex.  
Decision Owner: Roger; instruction to build whenever sufficient data exist and establish availability with a large test set.  
Implementer: Codex.

## Change Summary

Previously blank FAO/other descriptive fields and malformed or absent landuse caused batch rejection. They now yield degraded, usable profiles if all physical and serialization checks pass. Existing populated fields and numerical transfer functions remain unchanged. Previously unusable metadata uses explicit `unknown` identity components; raw data are retained in diagnostics.

## Rationale and Alternatives

Descriptions do not establish physical sufficiency. Rejecting them discards usable numerical evidence. A silent generic physical fallback was rejected because it changes scientific inputs without evidence; removing physical validation was rejected because malformed profiles cannot be used safely. Unavailable landuse follows the already supported code-zero behavior with visible provenance.

## Consequences

More locations can build, with visible degraded outcomes. Missing physical inputs still fail. Availability must be measured over a declared spatial sampling frame; 1,000 points do not prove universal coverage.

## Evidence

[Work package](../work-packages/20261106_esdac_missing_data/package.md) retains the incident report, availability study and reviews.

## Risk and Rollback Notes

Unknown metadata can reduce key differentiation; retain batch content-collision rejection. Monitor warning reasons and prior-success regressions. Revert this bounded admission change if physical parity fails, retaining diagnostics and study evidence.

## Batch identity amendment — 2026-11-06

Actual incident replay exposed rounded legacy keys shared by distinct profiles,
and timestamp-only conflicts between equivalent artifacts. Ignore the
volatile `#  Build Date:` and additive `# Source warning:` comments for identity. Preserve unsuffixed legacy keys
when unambiguous; append the SHA-256 of stable artifact content when a batch
contains different content for one key or an existing legacy file differs.
Update both dominant-soil mappings and quality-report keys before publication.
Never overwrite a different existing artifact; keep the final collision guard.
This additive identity repair is necessary to build the operator's actual
watershed after metadata admission. Physical values and historical files remain
unchanged. Same-input retries must reuse equivalent artifacts.

## Physical sufficiency amendment — 2026-11-06

The first paired availability study exposed 72 profiles rejected because the
existing texture-change depth exceeded or equaled the existing impermeable
layer depth. These source classes define top material extending to the known
soil boundary; they do not require an inverted second horizon. Limit the top
horizon to the known impermeable depth and omit the nonexistent subhorizon.
Require subsoil CEC/STU only when that subhorizon is actually emitted. Record
`source.profile.single_horizon` with both source depths and preserve any
available subsoil descriptive key class. Existing depth-class mappings remain
unchanged; no depth, density, texture or conductivity value is guessed.
The operator's sufficiency instruction covers this confirmed peer defect.
Output depth-order, finite-value and water-content checks still apply to every
emitted layer. Re-run the paired study and preserve the first checkpoint.
