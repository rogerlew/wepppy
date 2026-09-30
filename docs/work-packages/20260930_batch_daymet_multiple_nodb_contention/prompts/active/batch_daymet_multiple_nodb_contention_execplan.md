# Eliminate batch Daymet Multiple stale NoDb writes

This ExecPlan is a living document. Maintain `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` as work proceeds.
Follow `docs/prompt_templates/codex_exec_plans.md`. Update this plan and the
package `tracker.md` at every stopping point.

## Purpose / Big Picture

Large observed-Daymet batch projects must be able to use all Kubernetes RQ
workers without corrupting or rejecting `climate.nodb` persistence. The change
will extend WEPPpy's existing collect-then-finalize ownership model to the
legacy `ClimateSpatialMode.Multiple` route exposed by job
`a7d21ee5-49e6-480f-9658-b825c8be6150`. A user can see the correction working
when the same production-equivalent leaf finishes, its climate files parse and
feed downstream preparation, and a deliberate unrelated controller edit
survives finalization.

Implementation and local validation occur on `forest`. The final file-backed
integration test occurs on the open-wepp.org cluster only after the local and
review gates pass. Do not equate implementation, wiring, forest validation,
cluster integration, deployment, run repair, or incident resolution.

## Progress

- [x] (2026-09-30 19:00Z) Capture the live incident signature and deployed
  revision.
- [x] (2026-09-30 19:00Z) Scaffold the package, tracker, and ExecPlan.
- [x] (2026-09-30 19:12Z) Reproduce both Daymet and PRISM stale writes with
  real files through the observed/Multiple router; two pre-fix failures retained.
- [ ] Attribute incident writer and cross-node lock identity (source inventory
  complete; cluster access pending).
- [x] (2026-09-30) Implement Daymet/observed PRISM bounded finalization and
  climate leaf ownership before startup/reset/resync.
- [x] (2026-09-30) Real CLIGEN and GDAL/PRISM parity, source parquet/PRN
  semantics, and exact WEPP hillside CLI copy validated on forest.
- [x] (2026-09-30) Final focused 117 passed; full repository 10015 passed,
  99 skipped in 2433.36 seconds. Final additions covered by targeted run.
- [x] (2026-09-30) Independent correctness and security reviews cleared local
  findings; production identity and cluster release gates remain open.
- [ ] Pass the open-wepp.org integration gate and retain exact evidence.
- [x] (2026-09-30) Documentation and retained artifacts state forest validated;
  external integration and incident attribution remain open.

## Surprises & Discoveries

- Observation: full Climate.build previously cleared Daymet artifacts before
  collection. Correcting only the builder would leave failure behavior broken.
  Full builds now defer replacement until commit; direct builders retain sidecars.
- Observation: reset of a managed projection changes effective-root lock identity.
  Existing lexical and effective maintenance guards, acquired in stable order,
  exclude a duplicate on both sides of reset. The callback is outside acquisition
  retry handling, preventing a nested lock error from replaying startup.
- Observation: destructive staging and rollback would lose failed work products.
  Visible Daymet/observed PRISM attempts retain working/failed status and numerical
  files; existing publication operates on redundant copies. Interrupted recovery
  backups now use a visible prefix. Canonical inventory is in the Daymet source
  preservation section of docs/schemas/climate-parquet-lineage-contract.md.

- Observation: observed PRISM still selects the legacy builder; the bounded
  finalizer was gated exclusively on GridMetPRISM. Batch base resynchronization
  and startup bypass climate-directory ownership. They are source-level competing
  writers, not an attributed cluster cause.

- Observation: collect/finalize support exists but does not cover the entire
  live path. The observed-Daymet single build still holds `with self.locked()`
  across expensive collection before `ClimateSpatialMode.Multiple` invokes
  PRISM revision.
  Evidence: revision `ce09d3a`,
  `wepppy/nodb/core/climate.py::_build_climate_observed_daymet`, and the live
  exception stacks.

- Observation: the parent reports 40 failures, while the expanded job tree
  contains 38 stale-write child failures, one unrelated WBT terrain exception,
  and the parent job-order failure roll-up.
  Evidence: RQ job dashboard for the incident job.

## Decision Log

- Decision: preserve one durable commit per finalized stage. A successful Daymet
  stage remains committed if PRISM fails; incomplete Multiple climate remains
  unavailable to WEPP preparation and receives no completion/export/event hook.
  Rationale: the existing plan and NoDb contract require PRISM to consume fresh
  finalized Daymet state. Combined-build atomicity would be a new behavior.
  Date/Author: 2026-09-30, Codex; independent correctness review confirmed this
  reading and the full-router failure regression passes.

- Decision: extend the existing climate directory ownership over hillslope
  startup and execution, using lexical/effective guards where they differ;
  retain live Climate tokens and use locked fresh controller resynchronization.
  Rationale: real duplicate/reset and controller-token tests prove the simpler
  build-only guard misses these writers. This reuses existing maintenance locks;
  no queue, protocol, lease extension, or topology is added. The later watershed
  phase and non-climate cleanup are outside this correction.
  Date/Author: 2026-09-30, Codex; independent reviewers confirmed the boundary.

- Decision: retain visible attempted outputs and publish redundant copies.
  Rationale: the unchanged artifact-observability standard requires preserving
  failed scientific work and recovery evidence; auto-deleting temporary stages
  violate it. Success removes only redundant copies; real browser/archive/restore
  tests cover working, failed and unknown-commit recovery records.
  Date/Author: 2026-09-30, Codex; correctness/security review findings.

- Decision: extend the existing observed builder finalization to Daymet and
  route Observed/ObservedPRISM PRISM revision through its existing finalizer.
  Rationale: both real-file stages fail under the unchanged persistence contract;
  preserve numerical calls and Daymet sidecar behavior.
  Date/Author: 2026-09-30, Codex.

- Decision: treat this as conformance repair and faithful extraction, not a new
  queue or persistence design.
  Rationale: the repository already defines and implements the required
  snapshot/collect/finalize contract on adjacent climate paths.
  Date/Author: 2026-09-30, Roger/Codex.

- Decision: execute on forest, then perform the decisive file integration test
  on open-wepp.org.
  Rationale: forest is the implementation environment; only the multi-node NFS
  Kubernetes environment exercises the original acceptance condition.
  Date/Author: 2026-09-30, Roger.

## Outcomes & Retrospective

The local implementation and scientific/artifact validation are complete.
Both pre-fix stages reproduce actual serializer stale-write errors. Initial
focused suites passed 84 tests; the final 35-case regression module covers
numerical parity, concurrency, failure/readiness, legacy resynchronization,
and actual browser/archive/restore. Independent correctness and security
reviews cleared all local findings. The full repository suite passed 10015 tests with 99 skips in 2433.36 seconds.
Incident writer attribution and cross-node production identity remain unproven;
cluster integration, deployment, affected-run repair and incident closure are
not claimed. See the retained artifacts and tracker.

## Context and Orientation

`NoDbBase` serializes a controller such as `Climate` into a `.nodb` JSON file.
It records the file identity loaded by an object and raises
`NoDbStaleWriteError` if that file changes before the object later dumps. This
guard prevents a stale in-memory object from silently overwriting another
writer.

`wepppy/nodb/batch_runner.py::_build_climate_at_mutation_boundary` clears the
scoped cache, loads `Climate`, and calls `build()` inside a climate
directory-root maintenance lock. `wepppy/nodb/core/climate_mode_build_services.py`
routes an observed climate. For non-interpolated observed Daymet it first calls
`Climate._build_climate_observed_daymet()`. When spatial mode is `Multiple`, it
then calls `Climate._prism_revision()`.

The first function currently performs expensive Daymet work within
`with self.locked()`. Adjacent paths use a safer model: capture relevant inputs,
collect derived files without retaining controller mutation authority, acquire
the controller lock, rehydrate durable state, reject changed relevant inputs,
publish explicit derived outputs, and dump once. The executor must establish
whether the live competing write is duplicate leaf execution, batch base
resynchronization, nested controller persistence, or another known writer. Do
not infer the writer solely from the exception.

Canonical behavior is defined by
`docs/schemas/nodb-persistence-concurrency-contract.md`. Read the prior packages
`docs/work-packages/20260820_climate_finalize_lock`,
`docs/work-packages/20260904_batch_culvert_climate_rehydration_b`, and
`docs/work-packages/20260906_batch_climate_rap_contention`, plus
`docs/dev-notes/batch-climate-rap-finalization.md`, before editing code.

## Plan of Work

Begin on forest by constructing a production-shaped fixture with observed
Daymet and `ClimateSpatialMode.Multiple`. Add narrowly scoped instrumentation or
test seams that record process identity, RQ job identity when present, run
directory, controller root, lock identity, loaded file signature, and each
write. Do not log secrets or whole controller payloads. Reproduce a same-size
intervening rewrite against a real `.nodb` file and retain the before/after
trace in the package artifacts.

Use that evidence to enumerate writers from batch base resynchronization through
Daymet collection and PRISM finalization. Verify whether two processes agree on
the same directory-root lock identity. If the existing lock should exclude the
observed writer but does not, repair that smallest boundary first. If the lock
is behaving and an internal stage persists independently, move that stage into
the existing collect/finalize contract. Stop for a contract checkpoint if the
fix changes public behavior rather than restoring the canonical contract.

Refactor observed Daymet so expensive acquisition/calculation produces an
explicit result without dumping a long-lived controller. Finalization must lock
and rehydrate current durable state, compare a documented relevant-input
snapshot, preserve unrelated fields, publish only an explicit derived-output
set, and dump once. Ensure PRISM revision consumes the freshly finalized state
rather than the pre-collection object. Reuse existing climate result and
finalizer types where their semantics match; do not force unlike paths into a
generic abstraction.

Add tests for success, collection failure, relevant-input supersession,
unrelated concurrent edits, same-size rewrites, malformed or supported legacy
state, duplicate invocation, and the Daymet-to-PRISM sequence. Generated-output
tests must parse the produced climate files and read the exact artifact used by
downstream WEPP preparation. Preserve timestamps and retry classification.

After focused tests, run the broad suite and the independent correctness and
security reviews on forest. Only after those gates pass, prepare an
open-wepp.org integration artifact that declares the exact candidate image,
fixture/run, intended writes, rollback, and stop conditions. Execute one
bounded file-backed integration, inspect the complete RQ tree, reload
`climate.nodb`, parse generated artifacts, read the downstream-consumed input,
and confirm no stale-write recurrence. Do not replay or repair the original
batch without a separate operator decision.

## Concrete Steps

Work from the WEPPpy repository root on forest.

    git status --short
    sed -n '1,260p' docs/schemas/nodb-persistence-concurrency-contract.md
    sed -n '1,240p' docs/dev-notes/batch-climate-rap-finalization.md
    rg -n "_build_climate_observed_daymet|run_prism_revision|finalize_multiple_build|_build_climate_at_mutation_boundary|resync_base_project_attributes" wepppy tests

Create the real-file reproduction and run the narrowest test first. Record the
exact new test path in this plan once selected.

    wctl run-pytest tests/nodb/test_batch_daymet_multiple_contention.py -x -vv

After implementation, run the affected suites and contract checks.

    wctl run-pytest tests/nodb --maxfail=1
    wctl run-pytest tests/rq --maxfail=1
    wctl run-stubtest wepppy.nodb.core.climate
    wctl check-test-stubs
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl run-pytest tests --maxfail=1

If RQ enqueue or dependency edges change unexpectedly, stop and reassess scope;
if retained, update `wepppy/rq/job-dependencies-catalog.md` and run:

    wctl check-rq-graph

Before the cluster integration, add an artifact containing the exact safe
commands and target identity. Do not place credentials, kubeconfig contents,
or full sensitive run payloads in the repository.

## Validation and Acceptance

The pre-fix real-file regression must fail specifically with the same-size
`NoDbStaleWriteError`, not an artificial assertion. After the change, the same
interleaving must either finalize while preserving an unrelated edit or raise
the canonical superseded-input error for a relevant edit. No stale object may
be blindly dumped or retried.

For an unchanged fixture, compare semantic climate content rather than mtimes
or mere existence. Parse the CLI and any PRN/parquet/PRISM-derived files, record
their relative paths and meaningful dimensions or summaries, and open the
exact downstream input used by WEPP preparation. The current scientific output
must remain equivalent unless an independently authorized parameterization ADR
changes it.

Forest acceptance requires focused tests, the broad suite, generated-artifact
evidence, and independent reviews. Cluster acceptance additionally requires the
candidate's exact revision/image digest, all expected workers healthy, the
bounded leaf's complete RQ tree, zero target stale-write exceptions, fresh
controller readback, generated/consumed artifact checks, and user-facing job
status. A successful helper test or RQ status alone is insufficient.

## Idempotence and Recovery

Tests must create isolated temporary run directories and be safely repeatable.
Instrumentation must be disabled or removed before closure unless it is an
intentional, reviewed observability feature. Failed collection must leave the
previous durable controller and published artifacts valid. A failed cluster
integration must stop further mutation, retain the job and file evidence, and
use the predeclared Git/image rollback; it must not trigger automatic replay or
repair of other runs.

## Artifacts and Notes

Create artifacts for writer attribution, forest validation, correctness review,
security review, and open-wepp.org integration. Keep concise transcripts with
exact revisions and command outcomes. Never commit credentials or mutable run
trees.

## Interfaces and Dependencies

Use existing WEPPpy NoDb and climate collaborators. The final interface should
retain `Climate.build()` and batch caller behavior. Any new internal result
type must explicitly separate collected files/derived values from mutable
controller state, and its finalizer must accept the captured relevant inputs
and collected result. No new external dependency, queue, datastore, daemon, or
protocol is permitted without stopping and expanding the package through the
recorded complexity-budget gate.

Plan revision note: created 2026-09-30 to turn the live full-fleet batch
recurrence into a self-contained forest implementation plan with a distinct
open-wepp.org file-integration acceptance gate.

Plan revision note: 2026-09-30 execution recorded both serializer reproductions,
source-level ownership bypasses, initial implementation and cluster-access gap.

Plan revision note: execution expanded ownership only after real reset/token
reproductions and retained failed artifacts to satisfy existing observability.
The numerical replay uses real CLIGEN/GDAL/PRISM and the actual WEPP copy boundary.

Plan revision note: final forest handoff records 117 focused passes, full-suite
10015 passes/99 skips, completed independent reviews and exact generated artifact
manifest. Cluster gate is blocked on missing approved access/fixture; no deployment,
incident repair or environment-validation claim is made.
