# Batch Runner WATAR-Only Retry Correctness

**Status**: Closed (2026-08-06)
**Timezone**: UTC

## Overview

Correct the Batch Runner path used when an operator selects only `Run WATAR`.
Existing, valid climate and WEPP results must remain valid when base-to-leaf
climate synchronization changes only stored station metadata or representation;
WATAR must then consume those results without rerunning WEPP.

This package follows the production failure of batch
`nasa-roses-202606-psbs`, job
`4fae6b30-709b-49b8-bd4e-f177b03344e7`. All 93 leaf jobs were reported by RQ
as finished but returned application failure because climate resynchronization
cleared the WEPP timestamps before WATAR checked its prerequisites.

## Objectives

- Prove that the runtime-station equivalence shipped in commit `70f74fef6`
  makes a WATAR-only batch run reuse semantically unchanged, completed climate
  and WEPP work.
- Preserve that narrow equivalence rather than introducing a second climate
  comparison policy.
- Preserve invalidation when a climate input that can change modeled output
  genuinely changes.
- Prove that caught leaf failures remain visible through failed
  `run_metadata.json`, the final run-state summary, and
  `BATCH_RUN_COMPLETED_WITH_FAILURES` even though the RQ transport job finishes
  normally so sibling work and the finalizer can continue.
- Add focused regression and generated-run evidence for the exact incident.

## Scope

### Included

- Characterization and, only if evidence exposes a gap, the smallest correction
  to climate base-to-leaf comparison or invalidation in
  `wepppy/nodb/batch_runner.py`.
- WATAR prerequisite validation and WATAR-only retry behavior.
- Batch RQ result/finalization status where required to prevent a failed leaf
  from appearing successful.
- Focused NoDb and RQ tests, Batch Runner documentation, and one disposable
  generated leaf proving WATAR reuses existing WEPP outputs.

### Explicitly Out of Scope

- Rerunning WEPP automatically when the operator selected only WATAR and the
  existing prerequisites are genuinely stale or incomplete; that case must
  fail clearly and tell the operator what must be selected.
- Changes to climate generation, WEPP, WATAR science, parameters, formulas, or
  output schemas.
- A new scheduler, queue topology, state ledger, or generalized dependency
  framework.
- Reprocessing the production batch or deploying code; those require separate
  explicit authorization after implementation is accepted.

## Required Behavior

1. With only `Run WATAR` selected, a leaf with valid completed climate,
   hillslope WEPP, watershed WEPP, and interchange artifacts runs WATAR without
   rebuilding climate or WEPP.
2. The supported runtime-resolution pair—base station `None` with
   `FindClosestAtRuntime`, leaf non-empty station with `Closest`—must not be
   synchronized back to the base representation and must not clear downstream
   timestamps. Other station or mode differences remain material unless new
   evidence establishes semantic equivalence.
3. A material climate-input change still invalidates affected downstream work.
4. Missing or genuinely stale WEPP prerequisites produce one actionable error;
   WATAR does not silently use invalid data.
5. A caught leaf application failure writes `status: failed` metadata and
   contributes to the final failed/incomplete summary and
   `BATCH_RUN_COMPLETED_WITH_FAILURES`. The leaf RQ function may return
   `(False, elapsed)` by design; RQ's `finished` state alone is not the
   application-success contract.

## Success Criteria

- [x] Existing runtime-station tests are audited against the exact incident
  serialization; any missing shape is added as a regression fixture.
- [x] The fixture passes with only `run_watar` enabled and proves climate and
  WEPP timestamps and artifacts were not regenerated.
- [x] A material-climate-change test still invalidates WEPP and WATAR.
- [x] Missing/stale prerequisite tests fail with an actionable diagnostic.
- [x] RQ tests prove a caught failure writes failed metadata and the finalizer
  publishes a failure summary while remaining failure-tolerant.
- [x] A disposable generated WATAR leaf produces Ash/AshPost results using
  preexisting WEPP outputs.
- [x] Focused tests, full applicable Python tests, documentation lint, and final
  correctness review pass. No RQ graph check was needed because wiring did not
  change.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Decision provenance captured**: yes; operator requirement recorded in this
  package on 2026-08-06.

## Dependencies and Related Packages

- **Depends on**: [Batch Runner WATAR Integration](../20260802_batch_runner_watar/package.md)
- **Related**: [Batch Runner durability](../20260630_batch_runner_durability/package.md)

## Stakeholders

- **Primary**: Batch Runner operators retrying WATAR across completed leaves.
- **Reviewers**: NoDb/Batch Runner maintainer and an independent correctness
  reviewer.
- **Security reviewer**: Not required by the low-impact triage.
- **Informed**: WEPPcloud production operators responsible for a later,
  separately authorized deployment or production rerun.

## Timeline Estimate

- **Expected duration**: one focused implementation session
- **Complexity**: medium
- **Risk level**: medium

## Security Impact and Review Gate

- **Security impact triage**: low
- **Dedicated security review required**: no
- **Triage rationale**: This corrects internal state comparison, prerequisite,
  and result semantics without changing authentication, public input, path,
  subprocess, secret, or queue-topology boundaries.

## Hardening and Callus Softening

- **Failure signature**: 93 leaf results returned `False` with
  `RuntimeError: WATAR requires completed WEPP tasks: run_wepp_hillslopes, run_wepp_watershed`.
- **Root condition**: base resynchronization treated non-material station-field
  differences as material climate drift and removed valid downstream
  timestamps.
- **Health signals**: WATAR-only retries reuse valid WEPP work; genuine climate
  changes remain retry-ineligible until prerequisites are rebuilt; failed leaf
  counts are visible.
- **Danger signals**: broad suppression of climate invalidation, implicit WEPP
  reruns, or new orchestration/state machinery.
- **Observation window**: the focused generated run plus the next authorized
  WATAR-only batch execution.
- **Temporary calluses introduced**: none planned.
- **Related prior hardening efforts**: commit `70f74fef6` and
  [Batch Runner durability](../20260630_batch_runner_durability/package.md).

## References

- `wepppy/nodb/batch_runner.py` — climate resynchronization and WATAR stage.
- `wepppy/rq/batch_rq.py` — leaf result and batch finalization behavior.
- `tests/nodb/test_batch_runner.py` — Batch Runner state regressions.
- `tests/rq/test_batch_rq_retry_selection.py` — retry and aggregate-status tests.
- `wepppy/nodb/README.batch-runner.md` — operator-facing execution contract.
- `prompts/completed/batch_runner_watar_only_retry_execplan.md` — completed
  executable plan and evidence.

## Deliverables

- Incident-shaped regression coverage for WATAR-only reuse in
  `tests/rq/test_batch_rq_retry_selection.py`.
- Generated-leaf evidence proving that WATAR/AshPost completes without rebuilding
  climate or WEPP.
- Reproducible evidence script in
  `artifacts/run_generated_watar_evidence.py`.
- Updated Batch Runner documentation and correctness disposition in
  `artifacts/2026-08-06_correctness_review.md`.

## Follow-up Work

- Production deployment and rerunning `nasa-roses-202606-psbs` remain separate,
  explicitly authorized operational actions.

## Closure Notes

**Closed**: 2026-08-06

**Summary**: The incident shape exactly matches the runtime-station equivalence
already shipped in commit `70f74fef6`, so no duplicate production fix was
added. This package supplies the missing complete leaf-path regression,
durable-failure regression, real WATAR/AshPost generated evidence, and operator
documentation. The generated run produced three hillslope and five AshPost
parquets without changing climate or WEPP inputs or prerequisite timestamps.

**Lessons learned**: Current persisted state after a failed resync cannot prove
the pre-resync leaf representation; logs and prior captured evidence are needed
to reconstruct it. Local interchange regeneration also depends on the leaf's
configured WEPP binary even when valid parquets already exist, so generated
evidence must distinguish artifact verification from regeneration.

**Archive status**: The completed ExecPlan, evidence script, and correctness
review are retained in this package. The 19 MiB disposable batch was moved to
trash after local Redis and NoDb cleanup.
