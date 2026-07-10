# Management Rotation Synthesizer Hardening

**Status**: Closed after ADR-0016 ingestion milestone (2026-07-10)
**Timezone**: UTC

## Overview

This incident package fixes AgFields management synthesis after the real
`sacral-self-discipline` acceptance run generated WEPP management files with
34-50 plant scenarios. WEPP hillslope accepts at most 20 plant scenarios, so
all 119 attempted sub-field runs failed before simulation. The synthesizer was
prefixing and copying identical plant and operation definitions for every crop
year even though its class contract says those definitions are shared.

The first repair retained the existing `stack-and-merge`
timeline, including its spring/fall setup-year composition, while reusing
structurally identical scenario definitions and remapping every reference to
the retained definition. The package was reopened after the user identified
`L179_weed` as systematic output from Jim's plant-management interface and
authorized a narrow ingestion normalization for residue-only `hmax <= 0`.

## Objectives

- Preserve the chronological crop schedule and the existing setup-year merge
  behavior used by AgFields.
- Canonicalize structurally identical reusable management scenarios without
  conflating definitions whose serialized model inputs differ.
- Reject a synthesized rotation with more than WEPP's 20 plant scenarios before
  writing a run file, with an actionable error.
- Capture the real canola-plus-16-oats failure as hermetic test fixtures.
- Validate the repaired management with the repository tests and the current
  WEPP hillslope binary against copied run support files.

## Scope

### Included

- `wepppy/wepp/management/utils/rotation_stack.py` and its type stub.
- Regression tests and run-derived fixtures under
  `tests/wepp/management/fixtures/ag_fields_rotation_synth/`.
- The AgFields management synthesis contract in
  `wepppy/nodb/mods/ag_fields/README.md`.
- Incident, compatibility, review, QA, and validation artifacts in this package.
- AgFields ZIP ingestion normalization and additive plant-file provenance.
- Parameterization decision record `docs/adrs/ADR-0016-agfields-applied-residue-hmax-floor.md`.

### Explicitly Out of Scope

- Re-running or mutating the 6,626 sub-fields in the source project.
- Changing crop mappings, operation dates, active-crop parameters, or plant
  fields other than the narrowly authorized residue-only `hmax` floor.
- Changing RQ queue wiring or WEPP runner success detection.
- Deduplicating yearly or surface-effect scenarios that must remain isolated by
  simulation year.
- Normalizing residue-operation random roughness or patching the subsequently
  exposed `frcfac.for:184` divide-by-zero.

## Success Criteria

- [x] The 17-year run-derived fixture synthesizes exactly 17 simulation years.
- [x] Structurally repeated plant and operation definitions are reused and all
  serialized scenario references resolve.
- [x] The fixture's `ncrop` is at most 20 instead of 50.
- [x] A synthetic rotation with more than 20 distinct plants fails before write.
- [x] Existing `end-to-end` append behavior remains unchanged and residue plant
  references are correctly prefixed.
- [x] Targeted management tests pass.
- [x] A generated management from the fixture advances through the configured
  WEPP hillslope binary without the incident's `ncrop` error. The binary then
  reports the independent source-input `hmax=0` error documented in QA.
- [x] Work-package and durable documentation pass `wctl doc-lint`.
- [x] Jim-interface 2017.1 ZIP ingestion changes residue-only `hmax <= 0` to the
  ADR-0016 floor without modifying the archived original source.
- [x] Raw 98.4 ZIP ingestion applies the same rule and preserves header notes.
- [x] Inventory provenance reports every applied normalization additively.
- [x] An active crop with `hmax <= 0` is not silently normalized.
- [x] The p3733 binary replay advances beyond `HMAX <= 0`; any subsequent,
  independent input or numeric failure is recorded rather than masked.

## Compatibility and Parameterization

The synthesis portion is an additive correctness repair to generated run artifacts. Management
file section names and numeric indices may become more compact, but every
reference points to a definition with the same serialized model data. Simulation
years, crop order, operation dates, and scientific values are unchanged.
Historical `.man` files remain readable and are not rewritten. A parameterization
ADR is not required because no default, formula, threshold, unit conversion, or
fallback heuristic changes; the fixed WEPP limit is an existing binary input
contract, not a new model parameter. The reopened ingestion milestone is a
parameterization change governed by ADR-0016: residue-only plants with
`hmax <= 0` receive `0.00001 m`, the smallest positive value retained by the
management serializer. Existing projects are unchanged until their archive is
reprocessed or re-uploaded.

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Rationale**: The reopened milestone changes content processing inside an
  existing authenticated, quota/path-guarded upload workflow. It adds no route,
  auth, archive extraction, path, queue, secret, or external-egress surface.

## Hardening Contract

- **Failure signature**: `*** ncrop read as N. Must be between 1 and 20 ***`
  followed by a missing WEPP success marker, even though the binary returns zero.
- **Scope freeze**: Fix scenario duplication in `ManagementRotationSynth` and
  prove the exact AgFields failure path; do not broaden into rotation selection,
  RQ orchestration, or WEPP runner behavior.
- **Health signals**: `ncrop <= 20`, all scenario references serialize, 17 output
  years are retained, and the WEPP binary prints its successful-completion marker.
- **Danger signals**: operation dates or crop parameters change, years collapse,
  surface scenarios become shared across years, or deduplication uses names
  instead of serialized structure.
- **Observation window**: the repaired `sacral-self-discipline` retry and the
  next AgFields project with a repeated crop schedule.
- **Temporary calluses**: none.

## References

- Completed ExecPlan:
  `prompts/completed/management_rotation_synth_hardening_execplan.md`
- Incident inventory: `artifacts/2026-07-10_failure_inventory.md`
- Compatibility plan: `artifacts/2026-07-10_compatibility_regression_plan.md`
- Source run: `/wc1/runs/sa/sacral-self-discipline/wepp/ag_fields/runs/`
- Representative failure: `p3733.err`, sub-field 3733, field 1479.
- QA finding for the next input blocker:
  `artifacts/2026-07-10_qa_findings.md#qa-04---real-binary-replay`.

## Deliverables

- Patched management synthesizer and type surface.
- Run-derived fixtures and exact regression coverage.
- Durable AgFields synthesis documentation.
- Code-review, QA, validation, and package-closeout artifacts.

## Closure Notes

The `ncrop` failure is closed. The p3733 regression retains 17 simulation years
while reducing 50 plant and 136 operation definitions to 3 and 10. Residue plant
indices now participate in prefixing, canonicalization, reachability, and
round-trip serialization instead of remaining unsafe local integers.

The real-binary replay no longer contains the incident signature. It stops at a
new, independent validation boundary because the uploaded applied-residue plant
`L179_weed` has `hmax=0`. Correcting that value is a source-management task and
was deliberately not guessed in this parameterization-neutral repair.

The package was reopened at 2026-07-10 20:06 UTC by explicit maintainer request
to normalize the systematic Jim-interface residue placeholder during AgFields
ZIP ingestion. The prior closure evidence remained valid while ADR-backed
ingestion, replay, and updated reviews were completed.

The reopened milestone closed at 2026-07-10 20:24 UTC. Both archive formats now
apply ADR-0016 with visible provenance and conservative active-plant exclusion.
The real binary clears both original validation boundaries and then exposes a
separate zero-random-roughness SIGFPE; review and QA explicitly disposition that
finding for a separate incident rather than broadening parameter normalization.
