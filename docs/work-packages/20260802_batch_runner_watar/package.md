# Batch Runner WATAR Integration

**Status**: Open (2026-08-03 UTC)
**Timezone**: UTC

## Overview

Add ash transport (WATAR), including required AshPost aggregation and catalog
publication, as an optional Batch Runner leaf stage. A batch whose base project
enables and configures the ash transport mod will run WATAR after WEPP completes
for each watershed, expose that stage in the Batch Runner UI, and use the same
RedisPrep timestamp-based retry selection as existing stages.

This package is implementation scope, not a surrogate or research spike. It is
not complete until a generated batch leaf contains WATAR outputs and a retry
skips a completed WATAR stage while selecting a leaf whose WATAR timestamp or
required output is missing.

## Objectives

- Add `run_watar` to the Batch Runner directive, status, and retry contracts.
- Run WATAR only for leaves with the ash transport mod initialized and only
  after the required WEPP watershed/interchange work is complete.
- Treat AshPost as part of WATAR completion: `run_watar` is not complete until
  per-hillslope ash simulation, watershed aggregation, documentation/version
  output, and query-engine catalog update all succeed.
- Reuse persisted `Ash` inputs from the batch base project without changing ash
  formulas, defaults, units, or calibration parameters.
- Preserve old batches and non-WATAR configurations without requiring an
  `ash.nodb` file or a `run_watar` timestamp.
- Integrate the directive and progress state with the existing Batch Runner UI.
- Add focused NoDb, RQ, route/snapshot, controller, and generated-output tests.

## Scope

### Included

- `wepppy/nodb/batch_runner.py` task registration, optional-task detection,
  dependency validation, execution, retry classification, and status output.
- `wepppy/rq/batch_rq.py` only if WATAR needs worker orchestration beyond the
  existing per-leaf execution boundary.
- Batch Runner snapshot, directive UI, progress rendering, and tests under
  `wepppy/weppcloud/routes/batch_runner/` and
  `wepppy/weppcloud/controllers_js/`.
- Existing `Ash`, `AshPost`, ash output-versioning/catalog, and
  `TaskEnum.run_watar` interfaces; no new model implementation.
- RQ dependency catalog updates and live job-tree validation if enqueue or
  dependency edges change.
- User, operator, and developer documentation for the Batch Runner workflow.

### Explicitly Out of Scope

- Ash science, formulas, defaults, units, thresholds, calibration, output
  schema redesign, or parameter tuning.
- Adding WATAR to projects whose base configuration does not initialize
  `ash.nodb`.
- Running WATAR before, instead of, or independently of WEPP.
- General Batch Runner refactoring, a new queue framework, or unrelated retry
  hardening.
- Changing the standalone WATAR form and rq-engine payload contract except for
  a confirmed compatibility defect required by batch execution.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful integration of the current WATAR execution path.
- **Authoritative source paths**:
  `wepppy/nodb/mods/ash_transport/ash.py`,
  `wepppy/rq/project_rq.py::run_ash_rq`, and
  `wepppy/microservices/rq_engine/ash_routes.py`.
- **Cutover proof required**: a current Batch Runner leaf with `ash.nodb` runs
  after WEPP, receives `TaskEnum.run_watar`, produces current `ash/` and
  `ash/post/` artifacts, and appears complete in batch runstate.
- **Acceptance evidence type**: both focused fixtures and generated output.

## Stakeholders

- **Primary**: Batch Runner operators and WATAR users.
- **Reviewers**: NoDb/Batch Runner maintainer, WATAR maintainer, RQ maintainer,
  frontend maintainer, and one independent correctness reviewer.
- **Security Reviewer**: independent reviewer for queue, worker, run-tree, and
  concurrency surfaces.
- **Informed**: WEPPcloud operators responsible for staging and production job
  trees.

## Success Criteria

- [ ] The accepted contract checkpoint defines WATAR eligibility, ordering,
  retries, backward compatibility, and UI behavior before production edits.
- [ ] A WATAR-enabled base project exposes a `Run WATAR` directive in the Batch
  Runner UI; non-WATAR leaves do not become permanently retry eligible.
- [ ] WATAR cannot execute unless required WEPP work and interchange artifacts
  are complete, and an explicit diagnostic identifies dependency failure.
- [ ] A leaf is not timestamped complete when `Ash.run_ash` succeeds only through
  hillslope simulation but `AshPost.run_post` fails; retry regenerates or
  resumes WATAR-owned post outputs without rerunning completed WEPP work.
- [ ] A completed WATAR stage is skipped on retry; failed, interrupted, stale,
  or missing WATAR work is selected and rerun without repeating unrelated
  completed upstream stages.
- [ ] WATAR input changes made in the base project before leaf initialization
  propagate through cloning; policy for changes after leaf initialization is
  explicitly ratified and regression-tested.
- [ ] Generated leaf evidence includes `TaskEnum.run_watar`, per-hillslope ash
  output, post-processing output, and runstate completion.
- [ ] Focused Python and JavaScript tests, full applicable quality gates, queue
  graph validation, security review, and independent correctness review pass.
- [ ] Batch Runner, ash transport, route, and operator documentation are current.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no. Any change to ash defaults, formulas, thresholds, units,
  transport mode, or fallback heuristics leaves this package and requires an
  ADR under `docs/standards/parameterization-adr-standard.md`.
- **ADR links**: existing scientific context remains in
  `docs/adrs/ADR-0022-alex-static-ash-transport-increment.md`; this package does
  not amend it.
- **Decision provenance captured**: pending contract-decision checkpoint.

## Dependencies

### Prerequisites

- Existing Batch Runner durability/retry behavior in
  `docs/work-packages/20260630_batch_runner_durability/`.
- Existing WATAR controller contract evidence in
  `docs/work-packages/20260727_watar_ui_contract_pilot/`.
- Existing `TaskEnum.run_watar`, `Ash.run_ash`, `AshPost.run_post`, and base
  project configuration behavior.
- An operator-approved, independently reviewed contract checkpoint committed as
  a standalone ancestor revision per
  `docs/standards/contract-first-change-standard.md`.

### Blocks

- Supported production batch execution of WATAR across watershed collections.

## Related Packages

- **Depends on**:
  `docs/work-packages/20260630_batch_runner_durability/`.
- **Related**:
  `docs/work-packages/20260727_watar_ui_contract_pilot/` and
  `docs/projects/nasa-roses-utility-watersheds/watar-integration-plan.md`.
- **Follow-up**: none planned; scientific or output-schema changes must use a
  separate package and the applicable ADR/schema process.

## Timeline Estimate

- **Expected duration**: 3-5 focused sessions plus staging verification.
- **Complexity**: medium-high.
- **Risk level**: high because this changes batch queue/worker completion and
  retry classification around an expensive model.

## Security Impact and Review Gate

- **Security impact triage**: high.
- **Dedicated security review required**: yes.
- **Triage rationale**: the implementation changes worker orchestration,
  completion/retry decisions, run-scoped file generation, locking, and possibly
  RQ dependency edges. Existing admin/JWT authorization must not be widened.
- **Security review artifact**:
  `docs/work-packages/20260802_batch_runner_watar/artifacts/2026-08-03_security_review.md`.

## References

- `wepppy/nodb/batch_runner.py` - leaf pipeline, directives, runstate, retry
  classifier, optional tasks, and base-project resync.
- `wepppy/rq/batch_rq.py` - parent/leaf/finalizer orchestration.
- `wepppy/nodb/redis_prep.py` - existing `TaskEnum.run_watar` label, glyph, and
  completion timestamp storage.
- `wepppy/nodb/mods/ash_transport/ash.py` - WATAR hillslope execution and the
  required call into AshPost.
- `wepppy/nodb/mods/ash_transport/ashpost.py` and
  `ashpost_versioning.py` - aggregation, output/version lifecycle,
  documentation, and query-engine catalog integration.
- `wepppy/rq/project_rq.py::run_ash_rq` - standalone worker behavior and NoDir
  root locking precedent.
- `wepppy/microservices/rq_engine/ash_routes.py` - base-project configuration
  behavior and standalone enqueue contract.
- `wepppy/weppcloud/routes/batch_runner/README.md` - operator-facing Batch
  Runner workflow and retry semantics.
- `docs/schemas/rq-response-contract.md` and
  `docs/schemas/nodb-persistence-concurrency-contract.md` - cross-cutting
  response, persistence, and locking contracts.

## Deliverables

- Accepted contract-decision artifact and reviews.
- Production integration and regression tests.
- Generated-output and live staging job-tree evidence.
- Updated dependency catalog, Batch Runner/WATAR documentation, security
  review, and closeout records.

## Follow-up Work

Record only discoveries that are outside the bounded integration. Do not absorb
scientific parameter changes or general Batch Runner refactors into this package.
