# Disturbed thinning soil lookup and mulch audit

Status: Open 2026-09-25. Timezone: UTC.

## Overview and scope

Correct thinning soil selection in the two Disturbed soil generation paths and verify
mulch retains the burned base class. Execute code delivery and local artifact
validation; production deployment and choice-feminist repair remain separate
operator actions. No production mutation is part of this package.

## Complexity budget

Reuse the soil lookup sites, lookup reader, soil converters, MOFE synthesizer and
WEPP preparation. Permit one bounded prefix rule and regression evidence.
No new dependencies, queues, services, schemas, privilege or recovery machinery.
Escalation requires retained evidence the direct fix fails real acceptance.

## Acceptance and generated artifact gate

The source incident is `/wc1/runs/ch/choice-feminist/_pups/omni/scenarios/thinning_30_90/wepp/runs/p10.sol`
on wepp1, inspected 2026-09-25 15:31 UTC. All five OFEs have `kr=3e-5`, upper
conductivity 50 and zero recovery metadata; the effective thinning loam row
requires `kr=4e-5`, conductivity 40, metadata 1.3/0.3.

Tests must exercise real soil conversion, MOFE synthesis and prepared soil
readback, preserving burned classes for mulch 15/30/60. Cover absent, empty,
populated, supported legacy and unsupported class states separately from formats.
Run focused regressions and the required broad suite; retain results and reviews.
Actual-project isolated validation is a release gate because the incident
escaped earlier management-only validation. A missing gate limits the completion
claim; it must not be hidden by broad-suite success. Fresh model reports and
production repair are not claimed by local input-generation tests.

## Compatibility and regression plan

No columns, saved IDs, management classes, filenames or soil formats are renamed.
Only the lookup class for strings starting with `thinning` changes. Preserve
operator row values, genuine misses, explicit soil overrides and mulch suffixes.
Existing artifacts need supported rebuild rather than cache reuse. Regression
tests will assert semantic values in intermediates and `wepp/runs` copies.

## Governance and review

Canonical authority: [treatment soil contract](../../schemas/disturbed-treatment-soil-lookup-contract.md).
Parameterization ADR: [ADR-0073](../../adrs/ADR-0073-disturbed-thinning-soil-lookup.md).
Security impact: none; no attack surface, auth, paths or execution boundaries
change. No dedicated security review required. Two independent contract reviews,
an ancestor checkpoint commit, independent correctness and QA review are required.

## Incident signals and precedent

Health: generated thinning soils match effective lookup rows and mulch soils
match their burned bases. Danger: zero metadata plus inherited forest `kr`/Ksat
in a rebuilt thinning artifact, or lost severity for mulch. Observation is
recurrence-triggered after deployment; operator owns rollout readback and any
new incident. No temporary mitigation is introduced.

Related: `20260920_omni_thinning_30_50` supplied cover assets;
`20260917_mofe_scenario_artifact_integrity` established generated-input checks.
Reuse that direct-readback standard, extend evidence to soils rather than infer
soil correctness from management coverage.

## Deliverables and follow-up

Active [ExecPlan](prompts/active/thinning_soil_lookup_execplan.md) and
[tracker](tracker.md). Highest supported claim: diagnosed.
Deployment, isolated actual-project release acceptance and production rebuild/
rerun ownership remain explicit at handoff; the incident is not resolved by a
source edit alone.
