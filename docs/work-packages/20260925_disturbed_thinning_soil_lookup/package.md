# Disturbed thinning soil lookup and mulch audit

Status: Completed code delivery and local validation 2026-09-25. Timezone: UTC.

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

Completed [ExecPlan](prompts/completed/thinning_soil_lookup_execplan.md) and
[tracker](tracker.md). Highest supported claim: locally validated, including
actual local-project input acceptance. Implementation `9a5eb0813` follows the
reviewed contract ancestor `b63e738d0`.

198 real-artifact tests and 123 focused tests pass. A supported fork of the local
choice-feminist copy rebuilt 455 hillslopes, applied thinning_30_90 to hill 71,
and produced matching corrected soils in intermediate and prepared p10.sol.
All five OFEs pass; twelve source NoDb hashes are unchanged. Evidence and exact
candidate/identity are in [validation summary](artifacts/validation-summary.md)
and [project result](artifacts/local-project-result.json). Independent correctness
and QA reviews pass with no open findings. Three final archive/restore tests pass.
The broad suite stopped after 5,286 passes and 54 skips on one independently
confirmed preexisting timeout assertion (60 expected versus 120 implemented).
Later tests were not executed; full-suite success is not claimed. Repository
maintainers own that unrelated test-expectation follow-up.

Production-equivalent host/mount acceptance, deployment, rebuild/rerun and fresh
report validation remain operator-owned release/recovery gates. The local source
is an older copy, not the current wepp1 scenario. The production incident remains
unresolved until deployment and affected-resource recovery are verified.
