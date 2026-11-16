# Omni MOFE Disturbed Soil Repair

**Status**: Closed - locally validated (2026-11-16)
**Timezone**: UTC

## Overview

Repair the shared Disturbed multiple-overland-flow-element (MOFE) soil producer
so ordinary Disturbed builds and Omni treatment scenarios both parameterize
ordered segments from stable, single-OFE source soils. The incident currently
causes thinning and prescribed-fire Omni jobs to fail when an already-generated
`hill_*.mofe.sol` file is reused as one stack member.

This is a conformance fix to the accepted MOFE input identity and Disturbed
treatment lookup contracts. It does not introduce a second Omni-specific soil
implementation or change scientific lookup values.

## Objectives

- Make `Disturbed.modify_mofe_soils()` safe when `soils.domsoil_d` already points
  at generated MOFE artifacts.
- Preserve the existing per-segment management-class and soil-texture lookup.
- Prove ordinary Disturbed and Omni treatment calls share the same producer.
- Validate generated and prepared soil artifacts with focused tests only; do not
  run the full repository test suite.

## Scope

### Included

- Stable source-soil resolution for the existing shared MOFE producer.
- Backward-compatible handling of populated legacy controller state.
- Direct, unmocked regression coverage for repeated parameterization and
  generated soil readback.
- Focused Disturbed, Treatments, Omni, and WEPP preparation tests.
- Developer documentation and incident correctness evidence.

### Explicitly Out of Scope

- A separate Omni soil parameterization implementation.
- Changes to lookup values, formulas, thresholds, defaults, or fallback policy.
- RQ queue wiring, route contracts, UI behavior, deployment, or production-run
  recovery.
- The full Python test suite, per explicit operator direction.

## Complexity Budget

- **Existing mechanisms reused**: `Soils.ssurgo_domsoil_d`, `SoilSummary`,
  `Disturbed.modify_mofe_soils()`, `WeppSoilUtil`, and
  `SoilMultipleOfeSynth`.
- **New mechanisms permitted**: one narrow source-resolution helper and focused
  tests; no new persistence key unless retained evidence proves existing source
  state is insufficient.
- **Simplest plausible change tested first**: select the stable pre-disturbance
  soil assignment when the published assignment points to `hill_*.mofe`.
- **Real acceptance condition**: an ordinary MOFE Disturbed build followed by a
  changed treatment assignment regenerates a valid combined soil whose OFEs
  contain the expected class-specific parameters.
- **Evidence required before escalation**: a supported soil mode where
  `ssurgo_domsoil_d` and retained `SoilSummary` entries cannot recover the
  original source.
- **Explicitly prohibited expansion**: new queues, services, datastores,
  daemons, dependencies, privileges, protocols, or deployment topology.

## Generated Artifact Validation Gate

- **Applicable**: yes; the repair changes a generated soil producer.
- **User-visible failure/outcome**: treatment scenarios no longer fail with
  `Each soil stack member must contain exactly one OFE` and produce valid soil
  inputs with ordered segment parameterization.
- **Intent evidence**: populated `landuse.domlc_mofe_d` with distinct segment
  management classes.
- **Persisted-state evidence**: reloaded source and published soil assignments.
- **Generated-intermediate evidence**: parsed component and combined `.sol`
  files with exact OFE counts and parameter values.
- **Prepared/consumed-input evidence**: parsed `wepp/runs/p*.sol` created by the
  normal preparation function.
- **Execution/output evidence**: N/A for local code delivery; native execution is
  not needed to prove the serializer failure boundary and deployment is excluded.
- **User-facing result evidence**: N/A; no report/UI contract changes.
- **Direct unmocked boundary**: real `WeppSoilUtil` and
  `SoilMultipleOfeSynth` writers and readers in a focused regression.
- **Actual-project/environment gate**: production `innovative-tailor` supplied
  diagnosis; candidate validation uses a disposable local reproduction and does
  not mutate the production run.
- **Highest completion claim currently supported**: diagnosed.

## Stakeholders

- **Primary**: WEPPcloud Disturbed and Omni users and maintainers.
- **Reviewers**: correctness review required before local closure.
- **Security Reviewer**: N/A.
- **Informed**: WEPPcloud production operators; deployment and recovery remain
  separate.

## Success Criteria

- [x] The shared producer resolves original single-OFE sources after a prior
      MOFE publication.
- [x] Mixed segment management classes retain ordered, class-specific soil
      parameters in combined and prepared artifacts.
- [x] Repeated invocation does not nest MOFE inputs or compound parameterization.
- [x] Focused tests and documentation lint pass without running the full suite.
- [x] Correctness review has no unresolved high or medium finding.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no.
- **ADR link(s)**: N/A.
- **Decision provenance captured**: yes; operator directed one shared
  implementation and per-segment parameterization in this conversation.

## Dependencies

### Prerequisites

- `docs/schemas/mofe-input-identity-contract.md`
- `docs/schemas/disturbed-mofe-mapping-contract.md`
- `docs/schemas/disturbed-treatment-soil-lookup-contract.md`

### Blocks

- Safe regeneration of affected Omni treatment scenarios.

## Related Packages

- **Related**:
  [MOFE input producer audit](../20261102_mofe_input_producer_audit/package.md)
- **Related**:
  [MOFE scenario artifact integrity](../20260917_mofe_scenario_artifact_integrity/package.md)

## Timeline Estimate

- **Expected duration**: one focused implementation session.
- **Complexity**: Medium.
- **Risk level**: Medium.

## Security Impact and Review Gate

- **Security impact triage**: none.
- **Dedicated security review required**: no.
- **Triage rationale**: internal source selection and generated-soil composition;
  no route, authorization, secret, subprocess, queue, or external-input boundary
  changes.
- **Security review artifact**: N/A.

## Hardening and Callus Softening

- **Failure signature(s)**: `ValueError: Each soil stack member must contain
  exactly one OFE.` from `run_omni_scenario_rq` treatment scenarios.
- **Related prior hardening efforts**: the November 2 MOFE producer audit added
  the correct single-OFE stack-member guard.
- **Health signals**: repeated shared-producer invocation produces parseable
  component, combined, and prepared soils with matching OFE counts.
- **Danger signals**: an Omni-only branch, relaxed validation, duplicated lookup
  logic, or reparameterization from already-disturbed outputs.
- **Observation window**: focused local validation now; production observation
  begins only after separately authorized deployment.
- **Temporary calluses introduced**: none.
- **Callus softening hypothesis**: N/A.

## References

- `wepppy/nodb/mods/disturbed/disturbed.py` - shared Disturbed soil producer.
- `wepppy/nodb/core/soils.py` - source and published soil assignments.
- `tests/nodb/mods/disturbed/test_modify_soils_mofe.py` - focused producer tests.
- `tests/nodb/mods/disturbed/test_treatment_soil_artifacts.py` - real artifact
  propagation tests.

## Deliverables

- Shared producer repair and focused regression coverage.
- Updated Disturbed developer documentation.
- Active ExecPlan, tracker, validation evidence, and correctness review.

## Follow-up Work

- Separately authorize deployment and regeneration of affected production runs.

## Closure Notes

The shared Disturbed producer now resolves a stable single-OFE source before
ESDAC quality validation and component planning. Final affected-boundary
validation reported 34 passes; an earlier adjacent focused run reported 134
passes. Changed-file broad-exception enforcement, diff checking, and scoped
documentation lint passed. The full suite was intentionally not run.

See
`artifacts/20261116_correctness_review.md` for the state matrix, failure-class
assessment, generated-artifact evidence, and bounded verdict. This closure
claims local code delivery only, not deployment, production-run recovery, model
execution, or fresh reports.
