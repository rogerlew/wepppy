# Refactor Roads into a stable facade and focused collaborators

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective current, together with the package tracker. This plan is scoped for implementation; creating it does not mean implementation has occurred.

## Purpose / Big Picture

Make the Roads controller easier to change and review without changing the scientific model or user workflow. After execution, users still upload roads, prepare segments, run WEPP, and inspect the same reports. Developers can trace each phase through a small cohesive module instead of a 2,069-line execution method. Prove this through the public facade and comparisons of fresh generated and consumed artifacts.

## Progress

- [x] (2026-11-17 22:37 UTC) Inspected source, dependencies, test anchors, and canonical guidance.
- [x] (2026-11-17 22:37 UTC) Measured baseline and prepared package/extraction map.
- [ ] M1: Establish characterization tests and baseline native/project evidence.
- [ ] M2: Extract input parsing and preparation orchestration.
- [ ] M3: Extract native input writers and mode-specific execution stages.
- [ ] M4: Extract routing/publication and query presentation.
- [ ] M5: Complete final validation, reviews, documentation, and quality assessment.

## Surprises & Discoveries

The current source is 5,907 SLOC (6,447 physical lines), not the earlier 5,834 count. The host quality analyzer cannot measure cyclomatic complexity because its optional radon support is unavailable. Existing `_unrutted` and parameterization collaborators should be extended or reused rather than duplicated. Native-suite documentation still names old non-positive-upstream expected failures, while the current contract supports top placement; establish actual baseline outcomes first.

## Decision Log

2026-11-17, Codex: Faithful extraction with facade compatibility, not new model behavior. This keeps scientific changes independently reviewable and avoids invalidating established input/output evidence.

2026-11-17, Codex: Follow input parsing, orchestration, mode-specific builders, accounting, artifact export, and query resolution order from the NoDb collaborator standard. Roads has no station resolver or new scaling phase; do not invent one. Modules belong beside this controller under `wepppy/nodb/mods/roads/`, rather than `nodb/core/`.

2026-11-17, Codex: Adapt the module-quality workflow to root AGENTS: quality bands remain observe-only. Aim below red for every extracted file, retain numeric deltas and reviewer rationale, and avoid metric-driven fragmentation. The template's automatic red-band merge block does not override root instructions.

## Outcomes & Retrospective

Execution authorized on 2026-11-17. M1 mapping is retained; baseline tests are running in an isolated checkout-verified container. Production extraction has not started.

## Context and Orientation

`wepppy/nodb/mods/roads/roads.py` defines `Roads(NoDbBase)`. NoDb persists controller state in `roads.nodb` and coordinates mutation with locks. Public import paths and saved class identity must remain stable. The facade is the object routes and RQ jobs call; collaborators are private implementation helpers and must not become persisted controller attributes.

`run_roads_wepp` handles prepared features, source retention, status transitions, native inputs, per-design execution, PASS routing, watershed execution, accounting, and publication. PASS files carry hillslope contributions into watershed routing. An OFE is an ordered overland flow element in a native hillslope profile; soil, management, slope, and execution role order must agree.

Read `wepppy/nodb/AGENTS.md`, `tests/AGENTS.md`, the module README/specification, and `docs/standards/nodb-facade-collaborator-pattern.md` before edits. Current scientific authorities include `docs/schemas/roads-settings-contract.md`, `roads-parameterization-baseline-contract.md`, `roads-unrutted-strip-contract.md`, `roads-validation-suite-contract.md`, and `output-scope-contract.md` in that same schemas directory. Persistence follows `docs/schemas/nodb-persistence-concurrency-contract.md`. Artifact evidence follows `docs/standards/generated-artifact-validation-standard.md`. Existing contracts remain unchanged; conflicts require resolution before affected implementation.

Use `artifacts/baseline.md` in this package for method anchors, module proposals, and hazards. Baseline commit is `96555f2f95326350d2d7007c19327378ea831ab0`. Recheck drift before work; preserve later accepted scientific changes, refreshing the baseline rather than reverting them.

## Plan of Work

### M1: Establish the behavior oracle

Inventory callers with `rg` across production and tests, including direct private-method imports and monkeypatches of runner/geospatial symbols in `roads.py`. Capture signatures, saved-state keys, mutation/lock ordering, status transitions, failure summaries, and current/historical admission. Read each of the 19 broad exception sites before deciding whether it can be narrowed. Retain a concise compatibility matrix in `artifacts/characterization.md`.

Run existing focused suites before changing source. Add only missing meaningful characterization for absent/empty/populated/supported-legacy/malformed states; disabled and stale preparation; explicit/default attribute mapping; all four designs; no eligible contributors; native failure, cancellation rollback, partial publication, and supported retry. Preserve baseline project outputs, climate, templates, binary hashes, and exact input intent in disposable run copies. Include mixed designs, RUPC top placement with two/three OFEs, ordinary four-OFE strips, width compression, and explicit road/fill fit rejection. Record which cases require project fixtures versus deterministic unit coverage. This milestone is complete when the baseline itself is reproducible and differences can be diagnosed without assuming refactored code is correct.

### M2: Extract parsing and preparation orchestration

Create `_inputs.py` for cohesive normalization, validation, and attribute mapping logic around `_validated_params_payload` and `_resolve_segment_run_inputs`. Keep `set_params`, `set_enabled`, and `set_uploaded_geojson` facade entry points and existing transaction scopes. Delegate pure calculations first; do not consolidate locks, reorder validation versus mutation, or change rollback semantics as incidental cleanup.

Create `_prepare.py` for preparation stages around `prepare_segments`, reusing `monotonic_segments.py` and `_unrutted.py`. Preserve geometry membership, CRS resolution, warning examples, signatures, persisted provenance, and invalidation. Retain thin facade adapters wherever callers require compatibility. Verify old serialized controllers load without collaborator objects or changed class paths. Each extraction must be wired through the facade and pass targeted characterization before the next responsibility moves.

### M3: Decompose native writers and execution

Extract cohesive slope, soil, and management builders into `_slope_inputs.py`, `_soil_inputs.py`, and `_management_inputs.py`. Preserve argument lists, formatting, markers, horizon policy, template selection, OFE ordering, parameterization overrides, and readback. Compare exact bytes where deterministic; parse semantics wherever known volatile path content prevents byte equality.

Build `_execution.py` as a bounded stage coordinator, with `_point_source.py` and `_unrutted_execution.py` for the existing design branches. Extract one branch at a time from `run_roads_wepp`, retaining the order of source retention, running-state persistence, workspace setup, execution, final publication, and failure recording. Keep explicit inputs/results per stage. A small internal record is acceptable only for demonstrated shared stage data; do not introduce a generic mutable context containing the whole controller. Preserve facade runner symbols that existing callers patch through explicit callable parameters where necessary. Do not introduce module import cycles or dynamic dispatch machinery.

Native tests must open emitted inputs and invoke the same installed binary as baseline. A successful mocked runner does not complete this milestone. Preserve zero-contributor behavior, diagnostics, native failures, and all current unrutted provenance/policy markers.

### M4: Separate routing, publication, and queries

Extract PASS header normalization, combination, and relevant workspace assembly into `_pass_routing.py`. Preserve copy-versus-link semantics and protection of baseline diagnostics. Extract accounting and `_regenerate_roads_report_resources` into `_reporting.py`, reusing existing lifecycle and loss-summary modules. Preserve publication order, catalog refresh boundaries, source-resource selection, retained historic artifacts, and output scope.

Move query/detail and parameterization presentation into `_queries.py` where cohesive, leaving public query methods on `Roads`. Verify queries report the same current or historical results after success, failure, retries, and legacy state loads. Compare consumed PASS inputs, native watershed output, summary/parquet schema and values, and result admission. Do not silently regenerate scientifically stale committed reports merely to satisfy source hashes; follow the validation-suite publication contract and retain candidate evidence separately.

### M5: Review, validate, and document

Run focused and broad gates against the candidate checkout actually consumed by the container. Obtain independent correctness, QA, and security review artifacts covering the entire facade and extracted modules. Resolve medium/high findings; preserve exact review revision and test identity. Update module README with responsibility ownership and user/operator docs only where explanatory text is affected. Correct confirmed stale test-runner guidance with baseline evidence. Update plan/tracker and package completion claims.

Capture before/after SLOC, maximum function span, complexity, broad-handler inventory, and a reviewer assessment of coupling/readability for every in-scope module. Aim for file SLOC < 1,200, function span < 150, and complexity < 30, without artificial splitting or moving the original monolith wholesale. Record residual hotspots and justified tradeoffs under the root observe-only rule. Missing metrics cannot be represented as green.

## Concrete Steps

Run commands from the task worktree, initially `/home/workdir/wepppy-roads-code-quality`. Confirm the container mounts this exact checkout before tests. The wrapper should refuse a mismatched checkout; do not bypass that guard or recreate another task's stack. Record an environment blocker if an appropriate runtime is unavailable.

    git status --short --branch
    git rev-parse HEAD
    python3 tools/code_quality_observability.py --base-ref 96555f2f95326350d2d7007c19327378ea831ab0 --md-out /tmp/roads-quality.pre.md --json-out /tmp/roads-quality.pre.json
    wctl run-pytest tests/nodb/mods/test_roads_*.py --maxfail=1
    wctl run-pytest tests/rq/test_roads_rq.py tests/microservices/test_rq_engine_roads_routes.py tests/weppcloud/routes/test_roads_bp.py tests/wepp/interchange/test_roads_*.py --maxfail=1
    wctl run-pytest tests/roads/test_roads_contracts.py tests/roads/test_roads_matrix.py --basetemp=/tmp/roads-quality-native-UNIQUE --maxfail=1

Choose a new basetemp each time to retain prior evidence. The native matrix has 516 declared profile cases, but do not infer controller lifecycle parity from that matrix alone. After verifying the source project exists, execute the opt-in project suite with the source setting forwarded into the test container using the existing wctl environment mechanism; inspect that mechanism before invoking it. `ROADS_VALIDATION_SOURCE=/wc1/runs/cl/clogging-starch` is the existing fixture setting. If unavailable, document an equivalent approved disposable fixture and its provenance or leave project acceptance open. Reconcile old negative-case expectations against current RUPC contracts first.

For each milestone rerun the impacted tests and update the paired tracker. At final acceptance:

    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref 96555f2f95326350d2d7007c19327378ea831ab0
    python3 tools/code_quality_observability.py --base-ref 96555f2f95326350d2d7007c19327378ea831ab0 --md-out /tmp/roads-quality.post.md --json-out /tmp/roads-quality.post.json
    wctl doc-lint --path docs/work-packages/20261117_roads_code_quality_refactor
    wctl doc-lint --path wepppy/nodb/mods/roads

Also retain the standard `origin/master` quality comparison required by root guidance, distinguishing unrelated accepted changes from this package. If deleting dead helpers, use the configured `.venv/bin/vulture` gate and investigate findings; do not blindly delete public compatibility seams. Run stubtest/check-test-stubs if a stub-exposed surface changes. RQ wiring and frontend changes are excluded; if scope is explicitly expanded, apply their additional canonical gates.

## Validation and Acceptance

All four road designs must retain baseline output semantics and error behavior. Native prepared inputs must preserve template binding, overrides, geometry, OFE order, and scientific numeric values; derived outputs must preserve schema, segment membership, modeled-area accounting, and baseline/roads isolation. Preserve the absolute unrutted area bound and current top-placement policy exactly, including failed and zero-contributor attempts. Compare identical binary/input configurations; floating tolerances require existing contractual justification, not newly invented thresholds.

Exercise real persistence reload and generated artifact writers without mocks at those boundaries. Test failure before execution, during a native segment, and during publication, then the supported retry. Failed runs must not admit stale output as current. Existing facade tests and new collaborator tests complement this direct evidence. Test skips, file existence, and job success alone do not satisfy acceptance.

This is a code-delivery package, not production deployment or incident repair. Local acceptance requires the candidate's focused/broad tests, direct native and project evidence, documentation, and independent reviews. Record missing external evidence as a remaining gate with owner and exact command, never as a passed stage.

## Idempotence and Recovery

Use a task branch/worktree and one integrator. Commit reversible responsibility-sized changes. Never reset shared master or remove unrelated WIP. Run native checks only in new disposable destinations, preserving the original source and baseline manifests. Roll back an extraction by reverting its task commit and rerunning its focused tests; do not repair parity by editing generated results. Preserve failed-run evidence and explicit diagnostics.

## Artifacts and Notes

Retain compact baseline/final metrics, characterization matrix, candidate/source/binary identities, commands and test outcomes, normalized-comparison rules, artifact manifests, and review findings under this package's artifacts directory. Keep large native inputs/outputs in identified disposable run storage and record their hashes/paths. No secrets or serialized sensitive projects belong in Git. Document any later remote integration using a fresh receipt; local tests do not establish remote integration or deployment.

## Interfaces and Dependencies

`wepppy.nodb.mods.roads.Roads` and `wepppy.nodb.mods.roads.roads.Roads` remain the public class. Preserve `set_enabled`, `validate_initial_params`, `set_params`, `set_uploaded_geojson`, `prepare_segments`, `run_roads_wepp`, `query_status`, `query_inputs`, `query_summary`, `query_map_segments_geojson`, `query_segment_detail`, `query_parameterization`, and `initial_parameterization_preview` signatures and behavior. Preserve any additional inventoried caller-facing helpers/properties. Collaborators do not acquire new locks or own serialized state. Keep dependencies on existing owned native/geospatial and NoDb mechanisms; add no runtime dependencies.

Revision note (2026-11-17): Initial plan, based on measured source and current contracts, prepared for staged implementation.
