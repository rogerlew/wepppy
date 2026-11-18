# Refactor Roads into a stable facade and focused collaborators

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective current, together with the package tracker. This plan is scoped for implementation; creating it does not mean implementation has occurred.

## Purpose / Big Picture

Make the Roads controller easier to change and review without changing the scientific model or user workflow. After execution, users still upload roads, prepare segments, run WEPP, and inspect the same reports. Developers can trace each phase through a small cohesive module instead of a 2,069-line execution method. Prove this through the public facade and comparisons of fresh generated and consumed artifacts.

## Progress

- [x] (2026-11-17 22:37 UTC) Inspected source, dependencies, test anchors, and canonical guidance.
- [x] (2026-11-17 22:37 UTC) Measured baseline and prepared package/extraction map.
- [x] (2026-11-17 UTC) M1: Characterization, 527-test native baseline and five immutable project controls complete. Mixed-design coverage gap tracked in M5.
- [x] (2026-11-17 UTC) M2: Input extraction validated (305 passed, one skipped); preparation extraction validated (31 passed).
- [x] (2026-11-17 UTC) M3: Writers/spatial extraction (251 passed) and execution-stage decomposition (390 passed, one skipped) wired; final parity/review gates tracked in M5.
- [x] (2026-11-17 UTC) M4: Routing/reporting/query extraction wired; 390 focused tests passed, one skipped.
- [x] (2026-11-18 UTC) M5 evidence: five project controls match across 4,577 comparisons; all 516 native profiles and parsed scientific summaries match baseline. Final-source v3 native output independently repeats 6,192/6,192 byte-identical files.
- [x] (2026-11-18 UTC) M5 environment qualification: canonical focused Roads selection passes 413 tests, one skipped; all 537 environment-sensitive prefix items have complete current-source receipts (508 passed, 29 skipped).
- [x] (2026-11-18 UTC) M5 observer qualification: independent post-exit snapshot confirms all 2,836 v2 source entries unchanged; ordinary and buffered-observer runs each pass the full eight-test derived-signature module. QA accepts only complete v2/v3 segments before their respective restart modules.
- [x] (2026-11-18 UTC) M5 fixture isolation: reviewed private batch-queue fixture passes two real-Redis recovery tests; baseline-reproduced ordinary batch-deletion fixture passes all five cases after local environment cleanup. Production source is unchanged.
- [x] (2026-11-18 UTC) M5 diagnostic: v5 completed all 6,853 remaining suffix items; pytest reported 6,365 passed, 208 failed, 273 skipped and eight errors. Baseline probes attribute the parser and non-shape failure classes; original evidence is retained.
- [x] (2026-11-18 UTC) M5 bounded repairs: two ordinary deletion fixtures at `5812caa02` pass all 50 module tests, including unchanged dedicated retention cases. The import-generated management JSON drift was recorded, reproduced on copied input and restored to exact HEAD/baseline bytes.
- [x] (2026-11-18 UTC) M5 replacement qualification: all 391 tests across 17 modules pass in 55.79 seconds, with 1,173 phase records, no runtime skips and one separate collection skip. Source hashes are unchanged and source/runtime/environment checks are clean.
- [x] (2026-11-18 UTC) M5 reconciliation: all 15,104 unique nodes accounted for: 14,582 passed, 505 runtime skipped, nine failed and eight setup errors; one collection skip is separate. All 17 unsuccessful nodes remain explicit.
- [ ] M5: Complete final broad-gate disposition, reviews, documentation and integrator acceptance. Baseline generated-bundle, Jinja-global, browser-dependency and PostgreSQL-schema limitations plus load-sensitive latency prevent a broad-green claim; keep this milestone open.

## Surprises & Discoveries

The current source is 5,907 SLOC (6,447 physical lines), not the earlier 5,834 count. The default python3 and container lack optional Radon support; final QA discovered an existing /usr/bin/python with Radon 6.0.1 and measured complexity without installing dependencies. Existing `_unrutted` and parameterization collaborators should be extended or reused rather than duplicated. The original native-suite documentation named old non-positive-upstream expected failures while the current contract supported top placement. Operator-approved RUPC-02 reconciliation and fresh positive/negative controls resolved that mismatch; historical outputs remain explicitly stale.

The first broad run exposed inherited archive-fixture environment coupling, reproduced on the immutable baseline. A bounded test-only environment reset passes 73 archive tests. No production archive behavior changed. Default wctl test execution correctly refused the task checkout mismatch; isolated one-off containers use the canonical nonce guard and read-only shared Git metadata.

The v2 observer performed file IO while a derived-signature test patched `Path.open`, causing an observer interruption rather than a failing application assertion. The complete module passes under ordinary pytest and the revised buffered observer. A separate post-exit process confirms 2,836 unchanged source entries; only complete pre-interruption items are reusable.

The v3 test suite exposed an existing integration test on the shared real `batch` queue, where four active workers could consume its test jobs. The baseline test bytes were identical. A private real queue plus a narrowly scoped logical-origin adapter preserves actual Redis WATCH/cancel/registry behavior without shared-queue mutation. The subsequent ordinary batch-deletion fixture inherited `/wc1` for its disposable `/tmp` workspace; baseline reproduced the mismatch and local environment cleanup passed all five cases. These test-only repairs do not alter Roads output or production retention behavior.

V5 exposed missing ignored runtime artifacts in isolated worktrees: the shape parser and sidecar, generated `controllers-gl.js`, and Node browser dependencies. Baseline probes reproduce those availability failures. Four feature-access cases also reproduce an incomplete Jinja fixture (`account_display_email` missing), and all eight PostgreSQL setup errors lack the existing model's `user.account_kind` column. Thirteen non-shape failures reproduce on baseline; the remaining catalog-latency case passes in isolation, which does not resolve its full-suite failure. Two additional ordinary deletion fixtures inherited `/wc1`; their bounded local environment corrections pass all 50 module cases. A long qualification basetemp also exceeds the AF_UNIX socket path limit before the relevant assertion. These observations are recorded in artifacts/nonshape_failure_class_assessment.md.

The v5 source receipt found one changed management JSON file. The recursive import sweep imports a module that changes the working directory and another that writes JSON for local management files. Its added `_pmet_plant_names: null` field is reproduced byte-for-byte using a copied input. Original and changed bytes were retained, then exact HEAD/baseline bytes were restored at the integrator's direction; artifacts/management_sidecar_drift_receipt.json binds that evidence.

## Decision Log

2026-11-17, Codex: Faithful extraction with facade compatibility, not new model behavior. This keeps scientific changes independently reviewable and avoids invalidating established input/output evidence.

2026-11-17, Codex: Follow input parsing, orchestration, mode-specific builders, accounting, artifact export, and query resolution order from the NoDb collaborator standard. Roads has no station resolver or new scaling phase; do not invent one. Modules belong beside this controller under `wepppy/nodb/mods/roads/`, rather than `nodb/core/`.

2026-11-17, Codex: Adapt the module-quality workflow to root AGENTS: quality bands remain observe-only. Aim below red for every extracted file, retain numeric deltas and reviewer rationale, and avoid metric-driven fragmentation. The template's automatic red-band merge block does not override root instructions.

2026-11-17, operator: Use RUPC-02 as authority for current project validation, retaining explicit road-plus-fill overflow rejection. Exact scope and rationale are in artifacts/contract_reconciliation.md. Historical outputs remain unchanged and stale; independently reviewed source drift is acknowledged in the staleness ledger with provenance and fresh refactor evidence linked separately.

2026-11-17, integrator with independent QA: Qualify broad coverage as a retained prefix plus an explicitly inventoried continuation after repeated baseline-reproduced archive-fixture failures. The full `tests --maxfail=1` gate was run three times; v3 completed 3,341 passes before the third unrelated fixture failure. Rerun the entire failed module and every subsequent collected item after bounded fixture repairs. Reconcile the original progress and collection skips, retain ordered inventories and source/config hashes before and after, and deduplicate overlap. This avoids repeating the unchanged 29-minute prefix. Report composite broad evidence, never an uninterrupted all-green run; cross-process session/order interactions remain a stated limitation. No skips, markers or production behavior are changed to obtain acceptance.

2026-11-18 UTC, integrator with independent QA: Correct the broad harness's global retention-root override. Controlled baseline/candidate Omni tests pass with canonical `dev-wc1,/wc1` and fail when the driver globally substitutes `/tmp`. Upload test fixtures now declare their own temporary retention filesystems. A canonical rerun replaces all 537 environment-sensitive prefix items (508 passed, 29 skipped), including four repaired prefix fixture modules. The final union is 2,947 unchanged v3-prefix items plus those 537 canonical items plus the 11,620-item canonical suffix. Keep the mixed-environment and separate-process limitations explicit. The exact runner, source freeze, baseline reproductions and phase inventories are retained in the review/evidence artifacts.

2026-11-18 UTC, integrator with independent QA: Buffer observer records while tests run, then persist through captured original IO after teardown. Reuse only completed modules/items with exact phase reconciliation and independently verified source equivalence; the interrupted v2 module is rerun in full. Preserve observer-failure logs and distinguish a subsequent source check from an in-process closing receipt.

2026-11-18 UTC, integrator with independent QA: Isolate the real batch-recovery tests on UUID queues; do not rerun the shared-queue race or stop active workers. The original association predicate still checks function, arguments and metadata using an unsaved logical-origin copy; actual jobs and Redis operations keep private origins. This fixture does not qualify literal production queue-name selection. Clear inherited retention settings only for the separately confirmed ordinary batch-deletion fixture.

2026-11-18 UTC, integrator with independent QA: Run the complete remaining 6,853-item suffix once with maxfail zero and frozen source rather than stopping at each fixture failure. Discard partial v4 outcomes from the final union. Any further correction requires confirmed attribution, independent review, full affected-module replay and exact source/node substitution; unresolved or cascading failures keep M5 open.

2026-11-18 UTC, integrator with independent QA: After baseline reproduction, restrict additional source repairs to ordinary deletion fixture environment cleanup, committed as `5812caa02`; preserve dedicated retention cases. Restore the import-generated management JSON only after retaining and reproducing its delta. For parser availability, reuse both existing source-matched parser binaries and their sidecars through read-only one-off mounts with before/after hashes; do not build dependencies or alter shared services. QA owns the complete 391-test, 17-module replacement and exact outcome substitution; the replacement now passes, with clean source/runtime/environment receipts. Baseline attribution is diagnostic evidence, not broad acceptance; leave unrelated production/schema work outside this refactor and retain all unresolved gates.

## Outcomes & Retrospective

Implementation is complete at 5ef264810. The facade fell from 5,907 to 1,888 SLOC and its execution method from 2,069 to 269 lines. Aggregate source grew 31% because compatibility adapters and explicit stage parameters were retained. Source reviews have no medium/high findings. All 516 native profiles have byte-identical files and exact parsed scientific summaries; all five project controls match across 4,577 artifact comparisons. The v3 final-source native comparison independently reconfirms all 6,192 byte-identical input/output files.

V5 completed with 6,365 passes, 208 failures, 273 skips and eight errors reported by pytest; exact item/phase reconciliation remains the observer's authority. All 391 tests across 17 complete replacement modules now pass in 55.79 seconds, with 1,173 phase records, no runtime skips and one separate collection skip. Before/after source is identical and source/runtime/environment checks are clean. All 194 shape failures, including five GeoParquet cases, resolve in this replay. Broad acceptance remains pending with 17 failure/error nodes unresolved: one generated-bundle failure, four Jinja fixture failures, three browser-dependency failures, one latency failure and eight PostgreSQL setup errors. The required 15,104-item inventory remains 2,947 retained original-prefix, 537 canonical-prefix, 2,521 completed v2, 2,246 completed v3 and 6,853 v5 items; replacements must substitute complete reviewed modules without duplicates, and partial v4 results remain excluded. Baseline generated-bundle, Jinja-global, browser-dependency and PostgreSQL-schema limitations and inconclusive load-sensitive latency prevent broad-green acceptance.

The integrator's disposition is incomplete broad acceptance: leave M5 and this plan open. Exact reconciliation is retained in artifacts/broad_final_reconciliation.json. Resolve baseline runtime/fixture/schema prerequisites in their owning scope and investigate the latency assertion under representative load before a later acceptance decision. Any later environment qualification must replay affected modules with retained evidence; unrelated production changes are outside this package. Separate-process and mixed-environment limitations remain explicit, and no uninterrupted full-suite pass or M5 completion is claimed. See artifacts/nonshape_failure_class_assessment.md and artifacts/shape_parser_environment_diagnostic.md for baseline attribution, artifacts/quality_metrics.md for residual hotspots, artifacts/qa_review.md for tradeoffs, and artifacts/broad_continuation_review.md for observer/fixture boundaries.

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

Revision note (2026-11-17): Execution started; preserved immutable baseline, approved contract reconciliation at `efc0f642b`, and recorded initial extraction evidence.

Revision note (2026-11-18): Updated living progress, discoveries, decisions and remaining acceptance after observer qualification, repeated final-source native parity and bounded queue/deletion fixture repairs. At that checkpoint v5 was running; M5 remained open with source frozen until its closing receipt.

Revision note (2026-11-18): Recorded completed v5 diagnostics, baseline attribution, two bounded fixture repairs at `5812caa02`, and preserved/restored import-generated JSON drift. QA's 391-test, 17-module replacement passes with unchanged source and clean runtime/environment checks; M5 remains open for exact reconciliation and explicit disposition of 17 unresolved broad failure/error nodes.

Revision note (2026-11-18): Exact final reconciliation is complete. The integrator retains all 17 unsuccessful nodes and leaves broad acceptance and M5 open; no deployment or integration is attempted.
