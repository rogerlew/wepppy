# Batch and Culvert Climate Rehydration Hardening

**Status**: Conditional closeout - implementation and Forest batch accepted;
culvert evidence limited by fixture completeness

**Started**: 2026-09-05 00:29 UTC

**Timezone**: UTC

## Overview

The openWEPP Kubernetes canary exposed repeated `NoDbStaleWriteError` failures
when batch watershed jobs built climate. Both the batch runner and culvert
runner hydrate `Climate` near the beginning of a long workflow, execute
watershed, landuse, and soils work, and only later call `climate.build()`. If
`climate.nodb` advances during that interval, the retained controller is a
stale mutation base and the NoDb guard correctly rejects its eventual dump.

This package updates those two orchestration paths to use the safer pattern
already established by `wepppy/rq/project_rq.py::build_climate_rq`: after the
climate directory-root precondition is accepted and while that root is locked,
clear the exact `climate.nodb` cache entry, hydrate a fresh `Climate`
controller, and invoke `build()` on that fresh instance. Downstream consumers
must also receive current climate state without weakening stale-write
detection.

## Production Incident

- **Environment**: `wc.openwepp.org` Kubernetes canary.
- **Parent batch job**: `30edcfbe-297a-4326-a048-a5397410d69e`.
- **Leaf job**: `ddc253a4-e30b-46dc-a819-3d2f3ec85064`.
- **Batch and leaf**: `nasa-roses-202608-psbs`, `OR-10`.
- **Observed interval**: leaf started at 2026-09-05 00:18:39 UTC and reached
  climate build at approximately 00:21:09 UTC.
- **Failure signature**: `NoDbStaleWriteError: stale NoDb write rejected for
  /wc1/batch/nasa-roses-202608-psbs/runs/OR-10/climate.nodb: expected
  (mtime=1788567519.6239834, size=1864), observed
  (mtime=1788567558.374864, size=1864)`.
- **Validated state**: the leaf climate file was present and populated; the
  RQ registry showed no duplicate `OR-10` job for this batch. The retained
  controller generation became stale during the same long-running leaf job.
- **Impact**: climate and downstream tasks for affected leaves do not complete;
  `run_batch_watershed_rq` catches the exception and returns `(False,
  elapsed)`, so RQ records the leaf job as `finished` even though run metadata
  and the status stream report failure.

## Scope Boundary

Fix the confirmed early-hydration stale Climate mutation in batch and culvert
run orchestration without redesigning NoDb persistence, climate generation,
queue topology, or batch retry semantics.

## Objectives

- Rehydrate `Climate` immediately before mutable climate work in
  `BatchRunner.run_batch_project`.
- Apply the same scoped cache-clear and fresh-hydration pattern in
  `wepppy/rq/culvert_rq.py::_process_culvert_run`.
- Ensure later RAP, OpenET, WEPP preparation, and interchange consumers use a
  controller representing the successful climate generation.
- Preserve strict stale-write rejection and existing directory-root locking.
- Add deterministic tests that advance `climate.nodb` between orchestration
  startup and climate build, proving neither runner dumps an early stale
  controller.
- Capture Forest validation and independent review evidence before closeout.

## Scope

### Included

- `wepppy/nodb/batch_runner.py::BatchRunner.run_batch_project`.
- `wepppy/rq/culvert_rq.py::_process_culvert_run`.
- Exact-scope `clear_nodb_file_cache(..., pup_relpath="climate.nodb")`
  placement inside the existing climate directory-root lock callbacks.
- Fresh Climate state for downstream readers after a successful build.
- Focused batch and culvert regression tests, including a real filesystem
  generation advance at the persistence boundary.
- Developer/operator documentation required to keep the orchestration and
  NoDb concurrency contracts aligned.
- Forest test-production execution and recurrence evidence.

### Explicitly Out of Scope

- Disabling, catching-and-ignoring, or weakening `NoDbStaleWriteError`.
- Retrying by dumping the same stale controller instance.
- Generic whole-object merge or changes to `wepppy/nodb/base.py` cache
  semantics.
- Changes to climate algorithms, parameter defaults, generated filenames, or
  scientific outputs.
- Changes to RQ queue names, dependency edges, status events, retry-selection
  policy, or the `(False, elapsed)` leaf result contract.
- Repairing historical production run directories or deploying beyond Forest.
- Treating the stale serialized logger/runid label observed in canary logs as
  part of this fix; investigate that separately unless it is proven to affect
  controller identity or persistence correctness.

## Contract and Precedent

This is incident-driven conformance work under:

- `docs/schemas/nodb-persistence-concurrency-contract.md`, especially the rule
  that stale mutation bases must be discarded and operations reapplied to
  freshly loaded durable state.
- `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`, especially
  exact file scope and guard placement inside an existing directory-root lock.
- `docs/standards/hardening-lifecycle-standard.md`.

The implementation model is
`wepppy/rq/project_rq.py::build_climate_rq`, which clears the exact cache entry
and hydrates Climate inside the climate lock callback. Related packages are:

- `docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups/` - the
  original contract rollout for project RQ mutation paths.
- `docs/work-packages/20260630_batch_runner_durability/` - batch retry, stale
  lock cleanup, and base-climate resynchronization precedent.
- `docs/work-packages/20260805_culvert_nodb_writer_hardening/` - culvert
  writer-ownership and fresh-state transaction precedent.
- `docs/work-packages/20260820_climate_finalize_lock/` - long-lived Climate
  mutation and fresh finalization precedent.

This package differs by correcting orchestration-level early hydration in two
run-local workflows. It does not alter the internal collect/finalize behavior
of a particular climate builder.

## Success Criteria

- [ ] Batch climate mutation clears only `climate.nodb` and hydrates Climate
  inside the existing climate root-lock callback immediately before build.
- [ ] Culvert climate mutation uses the same placement and exact cache scope.
- [ ] Neither workflow calls `build()` on the Climate instance hydrated during
  orchestration startup; unnecessary early mutable hydration is removed.
- [ ] RAP/OpenET and WEPP/interchange consumers use current post-build climate
  state and preserve existing successful output behavior.
- [ ] A deterministic same-size `climate.nodb` generation advance between
  startup and climate stage no longer produces the incident failure.
- [ ] Absent, empty, populated, supported legacy, and malformed climate states
  retain their contractually appropriate success or explicit-failure behavior.
- [ ] Existing status messages, timestamps, skip/retry classifications, and RQ
  dependency graph remain unchanged.
- [ ] Focused tests, repository sanity, documentation lint, broad-exception,
  code-quality, correctness, QA, and security gates pass with no unresolved
  medium/high findings.
- [ ] Forest runs representative batch and culvert workflows without the
  target stale-write signature; evidence and rollback steps are recorded.

## Hardening Hypothesis and Signals

- **Hypothesis**: if each runner clears the exact Climate cache entry and
  hydrates under the climate root lock immediately before `build()`, then
  intervening file generations from earlier workflow activity will be
  incorporated rather than rejected as stale, while true concurrent mutations
  remain protected by the existing lock and stale-write guard.
- **Primary health signals**: the deterministic interleaving regressions pass;
  representative Forest batch and culvert runs complete climate; the target
  `NoDbStaleWriteError` signature does not recur.
- **Guardrail signals**: no extra run-wide cache clears, no lost climate input
  fields, no duplicate builds, no status/timestamp or queue-graph drift, and no
  change in generated climate/WEPP artifact compatibility.
- **Valid-state guardrails**: normal absent optional RAP/OpenET state remains a
  no-op; populated and supported legacy Climate state still builds; missing or
  malformed required Climate state fails explicitly rather than being masked.
- **Danger signals**: stale-object dump retry, cache clearing outside the root
  lock, broad exception suppression, changed scientific output, downstream use
  of a pre-build controller, or recurrence on Forest.
- **Observation model**: use a stateless recurrence-triggered model. Capture a
  bounded pre/post Forest snapshot in this package and promote the exact
  recurrence signature and response into current operator documentation. Any
  recurrence opens a new incident package citing this record.
- **Temporary calluses introduced**: none planned. Scoped invalidation and
  fresh hydration are the canonical mutation pattern.

## Security Impact and Review Gate

- **Security impact triage**: `high`.
- **Dedicated security review required**: `yes`.
- **Triage rationale**: the change affects RQ worker persistence, lock/cache
  ordering, and run-tree writes. It adds no route, credential, subprocess,
  filesystem root, or authorization capability.
- **Required artifact**:
  `artifacts/2026-09-05_security_review.md`.
- **Correctness artifact**:
  `artifacts/2026-09-05_correctness_review.md`.
- **QA artifact**: `artifacts/2026-09-05_qa_review.md`.

## Parameterization ADR Gate

- **Parameterization change present**: `no`.
- **ADR required**: `no`.
- **ADR links**: N/A.
- **Decision provenance captured**: `yes` - Roger Lew requested the batch and
  culvert adoption of the `project_rq` pattern on 2026-09-05 UTC.

## Rollout and Rollback

Implementation and local validation precede Forest deployment. Forest is the
only authorized live target for this package. Record the deployed commit and
image digest, run one representative batch workflow and one representative
culvert workflow, and inspect leaf metadata plus worker logs.

Rollback is an ordinary revert of the implementation commit followed by the
existing Forest deployment procedure. A rollback restores the old
early-hydration behavior and therefore restores the incident risk; it must not
disable the NoDb guard or edit run files manually. Production deployment needs
separate operator authorization after Forest evidence is accepted.

## Deliverables

- Regression-backed batch and culvert implementation.
- Updated canonical or subsystem documentation if implementation discovers an
  unstated invariant.
- Correctness, QA, and security review artifacts with dispositions.
- Forest before/after, deployment, rollback, and recurrence evidence.
- Completed ExecPlan, tracker, and `PROJECT_TRACKER.md` lifecycle updates.

## Dispatch

Execute
`docs/work-packages/20260904_batch_culvert_climate_rehydration_b/prompts/active/batch_culvert_climate_rehydration_execplan.md`
end to end on Forest. Keep the ExecPlan and tracker current at every stopping
point. Do not deploy to production as part of this package.
