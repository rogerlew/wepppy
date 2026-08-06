# Complete and prove Batch Runner WATAR-only retries

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to
date as work proceeds. Maintain it in accordance with
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

An operator who selects only `Run WATAR` for an existing Batch Runner leaf must
be able to reuse completed climate and WEPP work when the only base-to-leaf
difference is the station resolution that Batch Runner performs at runtime.
The retry must run WATAR and AshPost without rebuilding climate or WEPP. If
climate really changed or WEPP prerequisites are absent, it must fail with a
specific diagnostic and the final batch summary must show the application
failure.

The incident was production batch `nasa-roses-202606-psbs`, job
`4fae6b30-709b-49b8-bd4e-f177b03344e7`: 93 leaf RQ jobs reached RQ's finished
state, but each returned application failure after resynchronization removed
the WEPP timestamps needed by WATAR. Production deployment and rerunning that
batch are outside this plan and require separate operator authorization.

## Progress

- [x] (2026-08-06 20:18 UTC) Review the package and current implementation.
- [x] (2026-08-06 20:18 UTC) Identify commit `70f74fef6` as an existing partial
  fix and make the plan evidence-first.
- [x] (2026-08-06 20:31 UTC) Reproduce the exact incident serialization and
  establish the baseline from read-only production state, logs, and the prior
  durability artifact.
- [x] (2026-08-06 20:37 UTC) Add an incident-shaped WATAR-only reuse regression
  and a caught-failure metadata regression.
- [x] (2026-08-06 20:37 UTC) Confirm no production-code correction is needed;
  the existing narrow comparison passes the complete leaf path.
- [x] (2026-08-06 20:50 UTC) Produce disposable generated-leaf evidence with
  real Ash and AshPost execution, then trash the disposable batch.
- [x] (2026-08-06 21:18 UTC) Update operator documentation and pass focused,
  NoDb, full Python, broad-exception, compilation, documentation, and diff
  validation.
- [x] (2026-08-06 21:18 UTC) Complete final correctness review with no findings
  and close the package.

## Surprises & Discoveries

- Observation: The narrow runtime-station comparison is already implemented in
  commit `70f74fef6`, including current, legacy, raw, foreign, and explicit
  station-change tests.
  Evidence: `_base_project_resync_attributes` in
  `wepppy/nodb/batch_runner.py` recognizes only base `None` plus
  `FindClosestAtRuntime` against a leaf non-empty station plus `Closest`.
- Observation: An RQ job marked `finished` is not necessarily an application
  success in this orchestration.
  Evidence: `run_batch_watershed_rq` writes `status: failed` metadata and
  returns `(False, elapsed)`; `_final_batch_complete_rq` classifies durable
  state and publishes `BATCH_RUN_COMPLETED_WITH_FAILURES`.
- Observation: The failed production retry overwrote the leaf station state
  back to the base representation, so current `climate.nodb` alone cannot show
  the pre-failure derived station.
  Evidence: On `wepp1`, OR-18 now contains the base `null`/`-1` pair; its log at
  `2026-08-04 19:16:17` records resync of both station fields, while the prior
  durability plan records the pre-resync concrete station/`Closest` pair for
  all 93 leaves.
- Observation: Local interchange repair attempted to inspect the configured
  `wepp_260727` binary even though the required parquets already existed.
  Evidence: The first disposable run stopped with `FileNotFoundError` for
  `/workdir/wepppy/wepp_runner/bin/wepp_260727`. The evidence retry bypassed
  only regeneration helpers, retained `_run_watar_stage` required-file checks,
  and ran real WATAR/AshPost successfully.

## Decision Log

- Decision: Preserve the runtime-station equivalence from commit `70f74fef6`
  unless the exact incident state fails against it.
  Rationale: It is narrow, fail-closed, and already has negative coverage for
  explicit station changes and unsupported serialized enum shapes.
  Date/Author: 2026-08-06 / Codex.
- Decision: Preserve failure-tolerant leaf RQ behavior.
  Rationale: Raising the caught application exception would alter established
  orchestration semantics. Durable failed metadata and the final failure event
  are the authoritative application result while siblings continue.
  Date/Author: 2026-08-06 / Codex.
- Decision: Require both fixture-level and generated-output evidence.
  Rationale: The defect crosses persisted NoDb state, RedisPrep timestamps,
  interchange artifacts, and WATAR execution; unit tests alone cannot prove
  downstream propagation.
  Date/Author: 2026-08-06 / Codex.

## Outcomes & Retrospective

Completed successfully. The existing runtime-station comparison required no
production change. Two regressions now prove complete leaf-path WATAR reuse and
durable caught-failure reporting. A disposable three-hillslope leaf produced
three WATAR and five AshPost parquets while preserving climate/WEPP hashes and
timestamps. Focused, NoDb, and full tests passed. Deployment and the production
batch retry remain separately authorized follow-up operations.

## Context and Orientation

Batch Runner stores a reusable base project in a batch `_base/` directory and
each watershed leaf under `runs/<leaf-runid>/`. A NoDb file is a JSON document
containing controller state. `RedisPrep` timestamps are durable stage-completion
markers; later stages use them to decide whether prerequisites exist and
whether work should rerun.

`wepppy/nodb/batch_runner.py` owns leaf execution. `run_batch_project` calls
`resync_base_project_attributes` before loading controllers. The resync rules
copy selected base NoDb attributes into the leaf and remove timestamps for all
downstream tasks when a material attribute changes. For a base configured with
`ClimateStationMode.FindClosestAtRuntime`, station lookup necessarily changes
the leaf representation to a concrete station and `ClimateStationMode.Closest`.
That pair is a derived runtime result, not new climate intent.

The helper `_base_project_resync_attributes` currently omits
`_climatestation` and `_climatestation_mode` from synchronization only for that
exact pair. `_base_project_attribute_drift` uses the same helper for retry
classification, so classification and mutation must remain consistent.

`_run_watar_stage` requires completed hillslope and watershed WEPP timestamps,
rejects single-storm climate, repairs or verifies the required interchange
parquets, and invokes `Ash.run_ash`. In this repository, WATAR is the ash
transport calculation and AshPost is its post-processing output path.

`wepppy/rq/batch_rq.py` owns orchestration. `run_batch_watershed_rq` catches a
leaf exception, writes `runs/<leaf>/run_metadata.json` with `status: failed`,
publishes failure status, and returns `(False, elapsed)`. This lets sibling jobs
and the failure-tolerant finalizer continue. `_final_batch_complete_rq` derives
the application summary from leaf state and emits
`BATCH_RUN_COMPLETED_WITH_FAILURES` when any leaf is not complete.

The primary tests are `tests/rq/test_batch_rq_retry_selection.py` for persisted
state, retry classification, metadata, and finalization, and
`tests/nodb/test_batch_runner_watar.py` for WATAR prerequisites and execution.
Use temporary directories and test doubles for unit coverage. Do not read or
mutate the production batch during implementation.

## Plan of Work

Milestone 1 characterizes the exact production state. Obtain the already
captured base and representative leaf values from incident evidence or, if
read-only production verification is explicitly authorized for the executing
session, inspect only the necessary `climate.nodb` fields and RedisPrep state.
Record the JSON serialization shapes in this plan's Artifacts section without
copying unrelated run data. Compare them with `_set_climate_station_state` and
the existing runtime-station tests in
`tests/rq/test_batch_rq_retry_selection.py`. Add a fixture case only if the
incident shape is not already exact. The milestone is complete when the exact
shape is named and the current behavior is known before production-code edits.

Milestone 2 adds an incident-shaped WATAR-only regression. Configure a
temporary BatchRunner so only `TaskEnum.run_watar` is enabled, create completed
climate and WEPP timestamps plus the minimum persisted artifacts expected by
the stage, and represent the base and leaf station state exactly as observed.
Fingerprint the climate file, WEPP timestamps, and representative WEPP output
before execution. Run the leaf path and assert that base resynchronization does
not remove prerequisite timestamps, climate and WEPP builders are not called,
the fingerprints stay unchanged, and the Ash/WATAR collaborator runs. Keep
direct `_run_watar_stage` prerequisite tests in
`tests/nodb/test_batch_runner_watar.py`; put orchestration and state-sync
coverage in `tests/rq/test_batch_rq_retry_selection.py`.

Milestone 3 closes only demonstrated gaps. If Milestones 1 or 2 fail because an
incident serialization is semantically the existing supported pair, extend
the narrow decoder or comparison in `wepppy/nodb/batch_runner.py`. Do not ignore
arbitrary metadata differences and do not generalize station equivalence beyond
evidence. Retain negative tests for explicit station changes, foreign enum
types, malformed serialized values, missing station names, and material climate
attributes such as observed years. If the baseline passes, make no redundant
production change.

In the same milestone, verify result reporting in
`tests/rq/test_batch_rq_retry_selection.py`: a caught leaf exception must yield
`(False, elapsed)`, write failed metadata with error type and message, and lead
the finalizer to publish both the failure-specific event and the ordinary
completion/end-broadcast events. Do not change queue dependencies unless a
failing test proves the current finalizer cannot observe the durable failure.

Milestone 4 creates generated-output evidence in a disposable local batch leaf.
Start from a locally generated, completed continuous-climate WEPP leaf with an
Ash controller. Disable every directive except `run_watar`, retain the runtime-
resolved station pair, and record checksums and timestamps for climate inputs,
WEPP run outputs, and interchange parquets. Execute the leaf through the Batch
Runner path. Acceptance is an unchanged climate/WEPP evidence set, a new
`run_watar` timestamp, and expected Ash/AshPost outputs. Record the disposable
run ID, commands, and concise before/after evidence here. Remove only the
disposable run created for this milestone.

Milestone 5 updates `wepppy/nodb/README.batch-runner.md` with the WATAR-only
reuse and application-result contract, runs all validation, requests an
independent correctness review, and resolves every medium/high finding. Update
this plan and `tracker.md` after each milestone. At closure, move this file to
`prompts/completed/`, add its outcome at the top, close `package.md`, and move
the package from In Progress to Done in `PROJECT_TRACKER.md`.

## Concrete Steps

Run commands from `/home/workdir/wepppy` using the repository wrappers:

    git status --short --branch
    git show --stat 70f74fef6
    wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1
    wctl run-pytest tests/nodb/test_batch_runner_watar.py --maxfail=1

After implementing the regression and any evidence-driven correction, rerun
the two focused modules. If enqueue sites or dependency edges changed, update
`wepppy/rq/job-dependencies-catalog.md` and run:

    wctl check-rq-graph

Validate the complete code change with:

    wctl run-pytest tests/nodb --maxfail=1
    wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    git diff --check

Validate affected documentation with:

    wctl doc-lint --path docs/work-packages/20260806_batch_runner_watar_only_retry
    wctl doc-lint --path wepppy/nodb/README.batch-runner.md

Expected focused and full pytest output ends with no failures. Record exact
pass, skip, warning, and duration counts in Progress and the tracker rather
than predicting fixed counts here.

## Validation and Acceptance

Acceptance requires observable behavior, not merely a helper implementation.
The incident-shaped test must fail if station resynchronization is forced back
to the base representation and pass with the supported runtime pair. It must
prove no climate or WEPP builder ran and no prerequisite timestamp disappeared.
A paired material-change test must still show downstream invalidation.

Missing hillslope or watershed WEPP timestamps and missing interchange artifacts
must each produce an actionable `RuntimeError` naming what is absent. The RQ
test must prove that the error is persisted as failed leaf metadata and counted
by the finalizer even though the leaf function returns normally to RQ.

The generated disposable leaf must provide before/after checksums or equivalent
fingerprints for climate and WEPP inputs, plus the new WATAR/AshPost artifacts
and completion timestamp. Unit-only mocks do not satisfy this criterion.

All focused tests, the NoDb suite, the full Python suite, broad-exception gate,
diff check, documentation lint, and independent correctness review must pass.
The RQ graph gate is required only if queue wiring changes. Deployment and
production rerun are explicitly not acceptance criteria for this package.

## Idempotence and Recovery

Unit tests use `tmp_path` and are safe to repeat. The generated evidence run
must use a unique disposable batch and leaf ID under the local run root. Record
the exact resolved directory before cleanup and never use a broad glob or an
unresolved environment variable as a deletion target. If execution fails after
WATAR begins, preserve logs and fingerprints, remove the WATAR timestamp and
only WATAR-owned disposable outputs, then retry; do not delete or rebuild the
climate or WEPP evidence being tested.

Do not modify production state. If a later authorized production rerun fails,
preserve its run metadata and logs for diagnosis and use the wepp1 operator
runbook rather than applying ad hoc timestamp edits.

## Artifacts and Notes

Record the exact incident station JSON shapes, focused test transcripts,
generated run ID, before/after fingerprints, WATAR/AshPost output paths, and
independent review disposition here as milestones complete. Keep excerpts
short and omit secrets or unrelated production data.

Milestone evidence captured on 2026-08-06:

- Production host `wepp1` and batch path were verified read-only. OR-18 failed
  metadata contains `RuntimeError: WATAR requires completed WEPP tasks:
  run_wepp_hillslopes, run_wepp_watershed`; its batch log records both station
  fields being resynchronized and all climate-dependent timestamps removed.
- The incident's pre-resync shape is current jsonpickle format: base station
  `null`, mode `FindClosestAtRuntime (-1)`; leaf concrete station, mode
  `Closest (0)`. This is exactly the existing positive regression shape.
- Focused regression result: `42 passed, 8 warnings in 17.78s`.
- Disposable run
  `batch;;codex-watar-retry-evidence-20260806;;evidence` produced
  `ash/H1_ash.parquet` through `H3_ash.parquet` plus five AshPost parquets.
  The `build_climate`, `run_wepp_hillslopes`, and `run_wepp_watershed`
  timestamps stayed at `1786049357`; `run_watar` changed from null to
  `1786049377`.
- SHA-256 stayed unchanged for `climate.nodb` (`9967bfd6...6777ec`),
  `climate/wepp.cli` (`ff4538a7...81de4e`), `H.pass.parquet`
  (`4e2b4c87...a4edb`), `H.wat.parquet` (`acef05cb...139b8`), and
  `totalwatsed3.parquet` (`08f3af50...1917`). Full digests are reproducible via
  `artifacts/run_generated_watar_evidence.py`.
- The explicitly named 19 MiB disposable batch was moved to the desktop trash
  after its Redis hash and NoDb instances were cleared. The source leaf and
  production state were not mutated.

## Interfaces and Dependencies

No new external dependency is expected. Preserve these interfaces unless a
failing characterization requires the smallest compatible correction:

    _serialized_climate_station_mode_value(value: Any) -> Optional[int]

    _base_project_resync_attributes(
        filename: str,
        attributes: Sequence[str],
        base_state: Mapping[str, Any],
        run_state: Mapping[str, Any],
    ) -> Tuple[str, ...]

    BatchRunner.resync_base_project_attributes(
        run_wd: str,
        prep: RedisPrep,
        logger: logging.Logger,
    ) -> Dict[str, Any]

    BatchRunner._run_watar_stage(
        runid_wd: str,
        prep: RedisPrep,
        ash: Ash,
        wepp: Wepp,
        climate: Climate,
        logger: logging.Logger,
    ) -> None

    run_batch_watershed_rq(
        batch_name: str,
        watershed_feature: WatershedFeature,
    ) -> Tuple[bool, float]

Preserve `run_metadata.json` as the durable per-leaf application result and
`_final_batch_complete_rq` as the failure-tolerant aggregator. Do not add a new
state ledger, scheduler, dependency, or automatic WEPP rerun.

Revision note (2026-08-06): Created this ExecPlan after an execution-readiness
review found the runtime-station fix already present. The plan starts with
incident characterization, preserves existing RQ failure-tolerance, and
requires generated WATAR-only evidence before closure.

Revision note (2026-08-06): Completed all milestones. No production comparison
change was necessary; added regression, generated-output, documentation, and
review evidence and recorded the local WEPP-binary regeneration friction.
