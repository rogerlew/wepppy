# Integrate WATAR with Batch Runner retries and UI

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current
as work proceeds. Maintain it in accordance with
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, an operator can configure ash transport on a Batch Runner base
project, enable `Run WATAR`, and run the collection. Each eligible watershed
will finish WEPP before WATAR begins, produce current ash and AshPost artifacts,
and display WATAR completion in batch progress. Running the batch again will
skip completed leaves and rerun a leaf whose WATAR stage failed or is incomplete,
without requiring WATAR for configurations that do not have the ash mod.

This is faithful production integration, not scaffold-only behavior. Completion
requires generated-output evidence from the current Batch Runner and WATAR code
paths. Merely adding a directive or mocked call is not sufficient.

## Progress

- [x] (2026-08-03 01:33 UTC) Inspected Batch Runner execution, retry,
  runstate, UI, route, and queue contracts.
- [x] (2026-08-03 01:33 UTC) Inspected WATAR base configuration,
  `Ash.run_ash`, `run_ash_rq`, output, locking, and completion timestamp paths.
- [x] (2026-08-03 01:33 UTC) Scaffolded the package, tracker, plan, security
  review placeholder, and backlog entry.
- [ ] Complete and commit the contract-first checkpoint with operator approval
  and two independent review dispositions.
- [ ] Add focused failing tests before production implementation.
- [ ] Implement optional WATAR task registration, dependency enforcement,
  Ash/AshPost execution, retry classification, and UI integration.
- [ ] Update queue graph and job catalog if job wiring changes.
- [ ] Run focused and broad validation, generated-output acceptance, staging
  smoke, security review, and correctness review.
- [ ] Update living documents and close or hand off the package.

## Surprises & Discoveries

- Observation: Global task infrastructure already defines
  `TaskEnum.run_watar`, label `Run WATAR`, glyph, and Redis timestamp behavior;
  Batch Runner does not include it in `DEFAULT_TASKS`.
  Evidence: `wepppy/nodb/redis_prep.py` and
  `wepppy/nodb/batch_runner.py::DEFAULT_TASKS`.
- Observation: Submitting WATAR inputs for a batch base project persists the
  `Ash` state but deliberately returns without enqueueing WATAR.
  Evidence: `wepppy/microservices/rq_engine/ash_routes.py::run_ash` checks base
  project context after parsing and upload persistence.
- Observation: WATAR is not independent of WEPP. `Ash.run_ash` loads climate
  and WEPP hillslope interchange data, then performs AshPost aggregation.
  Evidence: `wepppy/nodb/mods/ash_transport/ash.py::run_ash` and the ash module
  `AGENTS.md` workflow.
- Observation: The existing Batch Runner retry classifier already supports
  optional tasks based on controller-file presence for RAP and OpenET.
  Evidence: `BatchRunner.OPTIONAL_TASK_NODB_FILENAMES` and
  `BatchRunner._completion_tasks`.
- Observation: `run_debris_flow_rq` currently timestamps
  `TaskEnum.run_watar`; this appears unrelated and could create false telemetry
  if that worker is ever part of acceptance setup.
  Evidence: `wepppy/rq/project_rq.py::run_debris_flow_rq`.

## Decision Log

- Decision: Model WATAR as an optional, directive-controlled leaf stage whose
  completion is required only when `ash.nodb` exists.
  Rationale: This matches current optional-task precedent and preserves old and
  non-WATAR batches.
  Date/Author: 2026-08-03 01:33 UTC / Codex.
- Decision: Prefer execution inside the existing per-leaf worker after WEPP and
  interchange completion, unless tests demonstrate a separate RQ job is needed.
  Rationale: Ordering is direct, leaf failure metadata remains authoritative,
  and no new dependency edge or finalizer race is introduced.
  Date/Author: 2026-08-03 01:33 UTC / Codex.
- Decision: Consume persisted `Ash` state and do not change parameterization.
  Rationale: The existing base-project route already captures WATAR inputs; new
  defaults or scientific changes are unnecessary and would require an ADR.
  Date/Author: 2026-08-03 01:33 UTC / Codex.
- Decision: Keep Ash hillslope simulation and AshPost as one atomic user-visible
  WATAR stage.
  Rationale: The current `Ash.run_ash` contract invokes `AshPost.run_post` and
  timestamps `run_watar` only afterwards. One terminal stage accurately reports
  whether usable aggregated/cataloged results exist and avoids exposing an
  internal recovery boundary as a second directive.
  Date/Author: 2026-08-03 01:40 UTC / Codex.
- Decision: Classify the planned production change as security impact high.
  Rationale: Repository policy treats queue wiring, worker execution, run-tree
  mutation, and locking changes as high impact.
  Date/Author: 2026-08-03 01:33 UTC / Codex.

## Outcomes & Retrospective

Discovery and planning are complete. The repository already contains most
primitives needed for a small integration, but the intended UI/NoDb/RQ behavior
must first be ratified under the contract-first standard. No production code has
been changed. Generated-output and staging outcomes remain pending.

## Context and Orientation

A Batch Runner project lives below the batch root and has an `_base` project
plus one cloned run directory per watershed under `runs/<leaf_runid>`. The
composite run id is `batch;;<batch_name>;;<leaf_runid>`. `BatchRunner` in
`wepppy/nodb/batch_runner.py` stores directives and executes the synchronous
portion of one leaf. `run_batch_rq` in `wepppy/rq/batch_rq.py` selects retry-
eligible leaves, enqueues one `run_batch_watershed_rq` job per selected leaf,
and creates a finalizer that tolerates failed dependencies so it can summarize
the whole collection.

`RedisPrep` is a Redis-backed timestamp ledger. A task is complete when
`prep[TaskEnum.<task>]` is not `None`. `BatchRunner._completion_tasks` combines
enabled directives with optional controller-file presence. Its classifier marks
a leaf missing, incomplete, failed, or complete and drives default retry
selection. The `Remove existing files` directive remains the explicit full
rerun path.

WATAR is the ash transport model implemented by `Ash` and `AshPost` under
`wepppy/nodb/mods/ash_transport/`. It is enabled when the project has
`ash.nodb`. The WATAR base-project form parses and persists inputs but does not
enqueue work. `Ash.run_ash` consumes climate, landuse/watershed, and WEPP
hillslope interchange data; it generates per-hillslope ash output, runs
post-processing, and timestamps `TaskEnum.run_watar` after post-processing.
The standalone `run_ash_rq` wrapper demonstrates current NoDir preflight and
locking behavior but should not be called as a nested RQ worker function.

The Batch Runner UI receives a snapshot whose `run_directives` list is generated
from `BatchRunner.DEFAULT_TASKS`. `batch_runner.js` renders that list generically,
so adding the task backend-side should expose it without a WATAR-specific widget;
tests must prove rendered label, slug, checked state, save payload, reload, and
progress glyph behavior.

Because this changes intended UI-coupled NoDb/RQ behavior, implementation cannot
begin until `docs/standards/contract-first-change-standard.md` is satisfied. The
package must contain an operator-approved contract-decision artifact, every
applicable canonical contract amendment, two independent reviews with findings
dispositioned, and a standalone ancestor commit recorded in the tracker.

## Plan of Work

Milestone 1 creates the normative checkpoint. Add
`artifacts/2026-08-03_contract_decision.md` with the starting revision,
applicable contracts, exact behavior, compatibility, security, and regression
evidence. Ratify that `run_watar` is visible and enabled by default only under
the chosen eligibility presentation; that execution requires `ash.nodb` and
completed WEPP watershed/interchange artifacts; that absent `ash.nodb` excludes
WATAR from completion proof; that completion means post-processing and the
timestamp succeeded; and how changes to base `Ash` inputs after a leaf was
created invalidate or resync the leaf. Obtain operator approval and two
independent reviews, amend any canonical domain intent matrix required by the
standard, disposition findings, and commit this checkpoint alone. Record the
revision in this plan and `tracker.md`. This milestone is accepted only when the
ancestor commit exists.

Milestone 2 adds characterization and regression tests. Extend
`tests/nodb/test_batch_runner.py` or add a focused WATAR module to prove
`run_watar` appears in directives, is skipped as an optional completion task
without `ash.nodb`, becomes required with `ash.nodb`, and participates in retry
classification. Test four leaf states: no ash controller, WATAR pending after
WEPP completion, WATAR plus AshPost complete, and interrupted/failed WATAR or
AshPost. Add a dependency
test that prevents WATAR invocation when WEPP watershed or required interchange
artifacts are incomplete. Add coverage for the ratified base-input
resync/invalidation policy. Extend route snapshot and Jest tests to prove the
generic UI exposes and persists the WATAR directive without special-case DOM.

Milestone 3 implements the leaf integration. Add `TaskEnum.run_watar` to
`BatchRunner.DEFAULT_TASKS` and `Ash.filename` to
`OPTIONAL_TASK_NODB_FILENAMES`. Load `Ash` only through `tryGetInstance` after
the WEPP stage. When the directive is enabled, `ash.nodb` exists, and the
timestamp is absent, validate the required WEPP/interchange state and invoke
the current `Ash.run_ash` path with persisted fire date and initial depths. This
call must include its existing `AshPost.run_post` phase; do not bypass it or set
the timestamp after hillslope simulation alone. Do
not invent defaults: normalize only the existing stored types needed by the
method signature. Do not duplicate the completion timestamp in Batch Runner;
retain `Ash.run_ash` as its owner unless the accepted checkpoint explicitly
changes that contract. If current NoDir projections require a lock boundary,
reuse the narrow root-lock pattern from `run_ash_rq` without nesting a worker
job or silently materializing archive roots.

Implement the accepted policy for base `Ash` input changes. If selective
resync is approved, list exact persisted input attributes in a Batch Runner
resync rule, copy only those values from `_base/ash.nodb`, and invalidate only
`run_watar`. Do not copy generated metadata or output paths. If clone-only
semantics are approved instead, document that existing leaves require explicit
workspace replacement and add UI/operator guidance; do not silently mix base
and leaf settings.

Milestone 4 completes integration evidence and documentation. Update
`wepppy/nodb/README.batch-runner.md`,
`wepppy/weppcloud/routes/batch_runner/README.md`, and the ash README where the
batch execution contract belongs. Rebuild the controller bundle after any
controller source change. If enqueue sites or dependency edges changed, update
`wepppy/rq/job-dependencies-catalog.md` and run the graph checker. Exercise a
small WATAR-enabled batch in the development/staging environment. Capture one
leaf's job ordering, RedisPrep timestamps, representative `ash/H*_ash.parquet`
and `ash/post/` files, generated post README/version metadata, catalog entry,
runstate completion, and retry behavior. Complete the
security artifact and one independent correctness review before closeout.

## Concrete Steps

Work from `/home/workdir/wepppy`.

1. Before implementation, create and ratify the checkpoint described in
   Milestone 1. Record the standalone commit SHA in this plan and the tracker.
2. Add focused tests first and observe failures:

       wctl run-pytest tests/nodb/test_batch_runner.py tests/nodb/test_batch_runner_grouped_updates.py --maxfail=1
       wctl run-pytest tests/rq/test_batch_rq_retry_selection.py tests/rq/test_project_rq_ash.py --maxfail=1
       wctl run-pytest tests/weppcloud/routes/test_batch_runner_snapshot.py tests/weppcloud/test_batch_runner_endpoints.py --maxfail=1
       wctl run-npm test -- batch_runner

3. Implement the accepted Batch Runner, WATAR, retry, and UI changes. Re-run
   the focused tests after each bounded edit.
4. If controller JavaScript changes, rebuild generated assets:

       python3 wepppy/weppcloud/controllers_js/build_controllers_js.py
       wctl run-npm lint
       wctl run-npm test

5. Validate Python, stubs, queue graph, and exception policy:

       wctl run-pytest tests/nodb tests/rq/test_batch_rq_retry_selection.py tests/rq/test_project_rq_ash.py tests/weppcloud/test_batch_runner_endpoints.py tests/weppcloud/routes/test_batch_runner_snapshot.py --maxfail=1
       wctl run-stubtest wepppy.nodb.batch_runner
       wctl check-test-stubs
       wctl check-rq-graph
       python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
       wctl run-pytest tests --maxfail=1

6. Run the generated-output/staging scenario and capture evidence in
   `artifacts/`. Then complete reviews and documentation validation:

       wctl doc-lint --path docs/work-packages/20260802_batch_runner_watar
       wctl doc-lint --path wepppy/nodb/README.batch-runner.md
       wctl doc-lint --path wepppy/weppcloud/routes/batch_runner/README.md

## Validation and Acceptance

Create or use a small batch with at least two watershed features and an `_base`
project containing `ash.nodb`. Configure WATAR through the normal base-project
UI, then run the batch. For every selected leaf, logs or job evidence must show
WEPP watershed completion and required interchange artifacts before WATAR
starts. Each completed leaf must contain representative per-hillslope ash
parquet and current `ash/post/` output, and its RedisPrep state must contain a
non-null `run_watar` timestamp. The Batch Progress panel must show the WATAR
glyph as complete.

Run the same batch again with `Remove existing files` disabled. Fully complete
leaves must be skipped. Remove only the test leaf's `run_watar` timestamp using
a test fixture or safe development-only operation while preserving WEPP
timestamps; the classifier must mark that leaf retry eligible and the next run
must execute WATAR without rerunning completed DEM, watershed, landuse, soils,
climate, or WEPP work. Also test a base config without `ash.nodb`; its leaves
must become complete without WATAR and must not loop in retry selection.

Force or simulate missing WEPP interchange input with WATAR pending. The leaf
must not report successful WATAR completion. It must fail with an explicit
diagnostic or run the already-approved interchange recovery path, and remain
retry eligible. A WATAR exception must produce failed leaf metadata and the
batch finalizer must include the leaf in failure/incomplete counts.

Also force `AshPost.run_post` to fail after representative per-hillslope ash
files exist. `run_watar` must remain unset, the leaf must remain retry eligible,
and retry must rebuild valid post outputs without rerunning completed WEPP.
Acceptance requires the current AshPost dataset/version metadata and catalog
entry, not only the presence of a hillslope ash file.

The implementation is accepted only when focused suites, frontend gates, queue
graph validation, broad tests, generated-output evidence, staging job-tree
inspection, dedicated security review, and independent correctness review are
complete. Record exact commands and results in `tracker.md`.

## Idempotence and Recovery

Task registration, classification, and UI snapshot changes are additive and can
be evaluated repeatedly. WATAR execution must remain guarded by both optional
controller presence and the `run_watar` timestamp. A failed attempt must not set
the timestamp before AshPost finishes. Retrying should reuse valid completed
WEPP products and overwrite/regenerate only WATAR-owned outputs according to the
existing `Ash` cleanup/version behavior.

Do not delete batch workspaces during development unless the explicit `Remove
existing files` directive is part of the test. Use disposable fixtures or a
small named development batch. Before clearing a RedisPrep timestamp manually,
resolve and record the exact composite run id and ensure no active batch or ash
job owns it. If an implementation with separate RQ jobs creates deferred jobs
after failure, stop and correct dependency/finalizer behavior before staging.

Rollback is to disable the `run_watar` directive for affected batches and revert
the bounded integration revision. Preserve generated ash artifacts for incident
analysis. Do not remove `TaskEnum.run_watar`, which predates this package and is
used by standalone WATAR.

## Artifacts and Notes

Create these artifacts as work proceeds:

- `artifacts/2026-08-03_contract_decision.md` for normative approval and
  compatibility policy.
- Two contract review artifacts and one review disposition before implementation.
- `artifacts/2026-08-03_security_review.md`, completed before closure.
- A generated-output/staging evidence note containing batch name, sanitized job
  ids, timestamp/order evidence, representative artifact paths, retry selection
  summary, and rollback result.
- One independent correctness review and disposition for production changes.

Do not place secrets, tokens, user data, or large generated outputs in these
artifacts.

## Interfaces and Dependencies

Preserve `TaskEnum.run_watar` in `wepppy/nodb/redis_prep.py`; it already owns the
stable slug, label, and glyph. `BatchRunner.DEFAULT_TASKS` must include that enum
after the accepted ordering point. `BatchRunner.OPTIONAL_TASK_NODB_FILENAMES`
must map it to `Ash.filename` so absent ash controllers do not affect completion.
`BatchRunner.state_dict` and `_build_batch_runner_snapshot` must continue to
produce entries shaped as `{"slug": str, "label": str, "enabled": bool}`.

Use `Ash.tryGetInstance(run_wd)` for eligibility and `Ash.run_ash(fire_date,
ini_white_ash_depth_mm, ini_black_ash_depth_mm)` for the current synchronous
execution interface. Values must come from the copied/resynced `Ash` state, not
new Batch Runner defaults. `Ash.run_ash` remains responsible for invoking
`AshPost.run_post` and setting the completion timestamp afterwards. Preserve the
standalone rq-engine `run-ash` request and `run_ash_rq` behavior.

The dependency invariant is: an eligible WATAR stage may begin only after the
same leaf's required WEPP watershed task and interchange artifacts are complete.
If this is represented as an RQ edge rather than synchronous ordering, the leaf
failure metadata and `_final_batch_complete_rq` must depend on the actual WATAR
terminal job with explicit failure propagation, and the dependency catalog must
record the edge.

Plan revision note, 2026-08-03 01:33 UTC: Initial plan authored after tracing
the current Batch Runner and WATAR execution, retry, UI, locking, and output
paths. The plan intentionally blocks production edits on the required
contract-first checkpoint.

Plan revision note, 2026-08-03 01:40 UTC: Clarified at operator request that
AshPost aggregation, versioned documentation/output, and catalog publication are
part of the single WATAR completion and retry contract.
