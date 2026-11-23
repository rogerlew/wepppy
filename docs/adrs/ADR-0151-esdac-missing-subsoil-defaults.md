# ADR-0151: Editable defaults for missing ESDAC subsoil

Status: Accepted, implementation conformance pending
Date: 2026-11-20

## Context

The Es Fangar ESDAC build rejects 37 of 58 hillslopes because the source represents required subsoil with zero texture and bulk density. The same-unit study found candidate material from two nearby cells. Their upper-material profiles differ from the targets, and the mapped dominant soil typological unit represents 35% of the broader soil mapping unit. The study does not establish which soil typological unit the property rasters allocated to an individual target or donor cell. The operator requested a visible, editable default if source-backed recovery cannot be established.

## Decision

Provide one editable six-field profile in Soil Options → Advanced options for gridded ESDAC. Prefill 25% clay, 40% sand, 35% silt, 1.4 g/cm³ bulk density, 0.5% organic carbon, and 5% gravel. These are fixed application values and are available on the first page load. They require no raster sample, prior build, or run-specific computation. Persist edits as one profile per project after validation.

Apply the profile as a whole only where a required subsoil has the confirmed ESDAC missing-data signature, all six source material fields present, finite, and zero. This includes organic carbon and gravel, so a profile with usable source values in either field does not enter this initial recovery path. A rejected profile with another independent physical or structural error remains subject to that validation. Keep topsoil, depth, CEC, valid native subsoil, and applicable target-site conductivity unchanged. Shallow profiles without subsoil do not consume the defaults. Store the raw source diagnostics, default provenance, and all substituted values in the soil quality report and generated artifact provenance. The fallback material and method participate in stable artifact identity and survive equivalent-file reuse. Report affected hillslope counts in the soil panel.

Validate texture and gravel as finite percentages between 0 and 100 and organic carbon as a finite percentage between 0 and 100. The three texture fractions must sum to 100% within the existing numerical tolerance. Bulk density must be finite and positive. All generated and disturbed soil invariants still apply.

## Decision provenance

Decision venue: Operator and Codex conversation, 2026-11-20 UTC.
Participants: WEPPcloud operator and Codex.
Decision owner: WEPPcloud operator directed a single prefilled profile per project, active across eligible hillslopes, and selected fixed application values instead of source-derived defaults.
Implementer: Codex selected rounded, physically plausible values for review.

## Rationale and alternatives

The fixed values describe a plausible mineral loam and keep the texture composition balanced. They are a modeling assumption, not a prediction about the project site. Editing and provenance let the operator replace them with project knowledge. A blanket change to the raster pixel selector recovered six profiles in the incident and regressed five. A same-unit replacement alone is unverified at the property pixel level. A whole-watershed soil override would discard valid spatial variation.

## Evidence and rollback

The [same-unit and fallback study](../work-packages/20261120_eu_run_recovery/artifacts/20261120_esdac_same_unit_study.md) records fields, counts, candidate distances, and unmodified and experimental writer results. The original diagnostic profile generated and reparsed all 37 previously rejected base soils. The [fixed preset readback](../work-packages/20261120_eu_run_recovery/artifacts/20261120_esdac_fixed_preset_builds.json) also generated and reparsed all 37. Real request persistence, downstream format-aware validation, and a full deployed replay on forest are required before closing the work package.

Stop a release if a valid source profile changes or if fallback use cannot be reconstructed from retained provenance. Restore the prior ESDAC rejection behavior if fallback must be withdrawn. Preserve saved settings and previously built artifacts for comparison and rebuild.
