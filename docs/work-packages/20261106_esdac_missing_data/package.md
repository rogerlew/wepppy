# ESDAC soils with incomplete source data

**Status**: Closed 2026-11-06 (local implementation and availability study)
**Timezone**: UTC

## Overview

Build usable ESDAC soils when enough physical information exists, even when descriptive source metadata is absent. The production run `preservative-coercion` rejected all 35 hillslopes because FAO soil-group labels were blank. The operator explicitly requested robust missing-data handling and a substantial location study to establish availability.

## Scope and complexity budget

Reuse the existing ESDAC sampler, quality diagnostics, batch publisher and WEPP soil parser. Correct metadata admission and normalization; construct shallow profiles from existing mapped depths and require only consumed material inputs. Retain physical output validation and existing parameter formulas. No new dependency, service, infrastructure, generic replacement soil or geographic nearest-neighbor imputation. Test the smallest correction before considering further physical-data recovery rules. Production deployment and in-place run recovery are separate from this code-delivery package.

## Success criteria

- Missing optional fields yield explicit degraded results, without stopping a physically valid build.
- Mandatory physical defects remain actionable errors; valid existing profiles preserve numerical inputs.
- All 35 incident coordinates are rebuilt and generated soil content is parsed.
- At least 1,000 deterministic, geographically distributed ESDAC locations are built; availability, warning/failure reasons, geographic bounds and denominator are retained.
- Focused tests, broad-suite disposition, independent correctness review and durable contract are retained.

## Compatibility and regression plan

Keep the public builder return tuple, soil-quality schema version 1, existing keys for valid populated inputs, batch atomic publication and disturbed transformation contract. Existing report readers already accept degraded results. Normalize previously unusable optional fields to explicit unknown metadata and retain raw source evidence in diagnostics. Compare actual parsed physical rows for metadata variants, exercise mandatory-data failure and retry, and read downstream disturbed artifacts.

## Generated artifact validation gate

Intent is recorded here and in ADR-0139. Incident coordinates and original failures are retained in `artifacts/incident_soil_quality.json`. Rebuild in isolated directories using real installed rasters; parse base `.sol` through `WeppSoilUtil` and validate downstream disturbed output. Retain manifests, per-location diagnostics, aggregate counts, candidate source hashes and environment identity. Never overwrite the original project for validation. Full watershed/model execution is outside this soil-builder delivery scope. Current claim: implemented and locally validated using generated artifacts; production deployment and original-run repair remain outstanding.

## Security impact and review gate

Security impact: none. No route, permission, execution boundary or path construction mechanism is added. Dedicated security review is not required. Independent correctness review is required under the work-package standard.

## Parameterization and authority

ADR required: yes, [ADR-0139](../../adrs/ADR-0139-esdac-missing-metadata.md). The operator's 2026-11-06 instruction authorizes building from sufficient information rather than rejecting absent metadata. Preserve existing missing-landuse parameter behavior; do not invent physical inputs.

## Failure-class assessment and observation

Audit FAO classification, unused groundwater/rooting metadata, landuse metadata, required depth/CEC, STU continuous inputs, HydroGrids coverage, direct and batch builders, and disturbed single/MOFE consumers. Retain dispositions in the correctness artifact. Related precedent: `20260819_eu_disturbed_soil_hardening` (historical only). Health signals are usable generated soils plus visible warnings; danger signals are silently fabricated physical values, accepted invalid outputs or regressions among prior successes. Observe the first post-deployment builds and quality reports; no temporary mitigation is introduced.

## Deliverables

[Execution plan](prompts/completed/implementation_execplan.md), [tracker](tracker.md), canonical contract, implementation, regression tests, availability artifacts and independent review.

## Study-driven scope refinement

The first complete paired run accepted 657/1,000 versus baseline 446/1,000,
with 211 recoveries and no physical regressions. It exposed 72 inverted/equal
horizon failures from known shallow impermeable boundaries. Under the same
sufficiency rule, the final candidate emits only the supported top material
there and does not require unused subsoil. ADR-0139 records this evidence-led
extension; the first checkpoint remains retained and the final study is complete.

## Closure and follow-ups

Delivered robust metadata handling, consumed-material validation, shallow-profile
construction and collision-safe batch retries. The [availability report](artifacts/availability-report.md)
retains 1,000 paired locations: 446 to 733 accepted, 287 recovered, no regressions;
all 35 incident locations and disturbed readbacks pass. Durable decisions live in
[ESDAC source sufficiency](../../schemas/esdac-soil-source-contract.md), especially
Field policy, Soil identity and retry, and Consumed horizons, with rationale in ADR-0139.
Independent correctness review has no open medium/high findings.

[Validation disposition](artifacts/validation.md): 123 focused tests pass; final
broad partitions have 13,289 distinct passes, 424 skips and one independently
reproduced pre-existing Runs-template assertion failure. The broad gate is not
fully green. Follow-ups: baseline template/test maintenance, operational deployment
and original-run rebuild. Remaining 267 sampled physical/provider failures are
retained for future evidence-led work; no physical inputs were invented.
