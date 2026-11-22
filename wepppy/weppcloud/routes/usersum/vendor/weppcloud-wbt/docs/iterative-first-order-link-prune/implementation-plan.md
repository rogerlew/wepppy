# Iterative First-Order Link Prune Implementation Plan (WBT Only)

## Objective

Implement `iterative_first_order_link_prune` in `weppcloud-wbt` per:
- [specification.md](/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md)

This plan is explicitly scoped to `weppcloud-wbt` implementation and validation.

## Scope

In scope:
- Rust tool implementation, registration, and WBT wrappers in this repo.
- TopAZ parity testing as a black-box oracle.
- Determinism, error-contract, and performance optimization (including multithreading).

Out of scope:
- WEPPpy integration and WEPPpy pipeline refactors.

## Global Quality Gates

Required for every work-package handoff:
1. Code review completed (findings dispositioned).
2. Tests for the package scope pass.
3. No regression in prior package tests.
4. `cargo check -p whitebox_tools` passes.

## Source and Test File Organization Strategy (Maintainability)

Goal:
- Keep IFOLP implementation readable and reviewable as scope grows from WP-01 through WP-09.

Source organization rules:
1. Keep the command entry file lightweight:
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune.rs`
- Responsibilities: tool metadata, parameter definitions, top-level orchestration, and calls into focused helpers.
2. Move complexity into concern-specific companion modules once logic grows:
- parser/contract handling,
- topology primitives,
- phase A qualification,
- phase B pruning,
- shared error/report utilities.
3. Prefer single-responsibility modules over large mixed files; avoid embedding full phase logic and parser internals in one monolithic file.

Test organization rules:
1. Keep parser/contract tests in companion test modules (pattern established in WP-01):
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_parser_tests.rs`
2. Add phase-focused test modules as implementation expands:
- `*_phase_a_tests.rs`,
- `*_phase_b_tests.rs`,
- `*_determinism_tests.rs`,
- `*_error_contract_tests.rs` (names may vary, intent must remain split by concern).
3. Keep each test module scoped to one behavior family (parser, topology, phase transitions, error paths, parity adapters).

Monolith prevention gate (apply each WP review):
1. If a source or test file becomes difficult to review due mixed concerns, split before WP closeout.
2. Require code review sign-off that file structure still reflects clear concern boundaries.
3. Record structural split decisions in WP tracker/execution notes when performed.

## Work-Package Sequence

## WP-00: Baseline and Parity Harness Design

Goal:
- Establish parity-oracle datasets, comparison method, and success criteria before implementation.

Implementation tasks:
1. Select representative DEM + flow-direction + threshold fixtures.
   Required real-world anchor fixture:
   - `/wc1/runs/cl/clueless-aftertaste/dem/wbt`
2. Produce reference outputs from TopAZ runs (black-box outputs only).
3. Define comparison metrics:
- exact binary raster equality (primary),
- stream-cell count delta,
- connected-component count,
- junction count,
- outlet reachability.
4. Build reusable parity harness scripts for repeated execution.

Code review phase:
- Review harness methodology for clean-room compliance and reproducibility.

Test phase:
- Run harness against fixed fixtures and verify deterministic re-run behavior.

Exit criteria:
- Versioned parity fixture catalog + runnable harness command set committed.

WP-00 execution-ready deliverables:
1. Artifact directory:
   - `docs/iterative-first-order-link-prune/wp-00/`
2. Required WP-00 documents:
   - `docs/iterative-first-order-link-prune/wp-00/fixture-catalog.md`
   - `docs/iterative-first-order-link-prune/wp-00/topaz-oracle-manifest.md`
   - `docs/iterative-first-order-link-prune/wp-00/parity-metrics-spec.md`
   - `docs/iterative-first-order-link-prune/wp-00/determinism-report.md`
3. Required harness utilities:
   - `tools/ifolp_wp00_prepare_fixtures.py` (or shell equivalent)
   - `tools/ifolp_wp00_run_topaz_oracle.sh` (or documented external oracle step)
   - `tools/ifolp_wp00_compare_outputs.py`

WP-00 E2E completion checklist:
1. Anchor fixture `/wc1/runs/cl/clueless-aftertaste/dem/wbt` is included in fixture catalog.
2. All fixture inputs and TopAZ oracle outputs are checksum-pinned.
3. Harness command set runs end-to-end from a clean working directory.
4. At least two consecutive reruns produce identical comparison outputs.
5. Code review findings are dispositioned and documented in WP-00 artifacts.
6. Test-phase evidence and pass/fail summary are recorded in `determinism-report.md`.

## WP-01: Tool Scaffolding and Registration

Goal:
- Add tool skeleton with full parameter contract and dispatch wiring.

Implementation tasks:
1. Create tool file:
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune.rs`
2. Register in:
- `whitebox-tools-app/src/tools/stream_network_analysis/mod.rs`
- `whitebox-tools-app/src/tools/mod.rs`
3. Implement argument parsing and metadata/help output.
4. Add placeholders for phase A/B execution and error paths.
5. Establish companion parser test module (non-monolithic pattern).

Code review phase:
- Verify interface exactly matches spec contract and naming.

Test phase:
- Unit tests for argument parsing, default values, and required-arg failures.

Exit criteria:
- Tool discoverable and invokable from CLI with expected usage/help output.

## WP-02: Core Data Model + Deterministic Topology Kernel

Goal:
- Implement deterministic topology primitives used by both phases.

Implementation tasks:
1. Implement pointer decoding (`whitebox` + `esri`) and neighbor traversals.
2. Implement topology classification states and receiver detection.
3. Implement first-order-link discovery with deterministic encounter ordering.
4. Implement candidate validity checks for intra-pass stale-candidate skip.
5. Extract topology helpers from entry file into dedicated companion module(s) if entry file begins mixing parser + topology concerns.

Code review phase:
- Validate determinism rules and ordering logic against spec.

Test phase:
- Unit tests on synthetic mini-grids for:
- inflow counts,
- state classification,
- link discovery order,
- tie behavior under epsilon.

Exit criteria:
- Deterministic kernel stable across repeated runs.

## WP-03: Phase A Source-Area Qualification

Goal:
- Implement source-area qualification with parity-critical traversal semantics.

Implementation tasks:
1. Provisional mask from minimum active CSA threshold.
2. Single row-major source scan with inline mutation.
3. Receiver handling for junction collapse and terminal-with-one-inflow recheck.
4. Topology reclassification after stabilization.

Code review phase:
- Focused parity review of traversal/update cadence and state transitions.

Test phase:
- Fixture tests targeting:
- source rejection/promotion,
- junction collapse behavior,
- terminal one-inflow branch behavior,
- no-channel failure conditions.

Exit criteria:
- Phase A outputs match expected behavior on designed fixtures.

## WP-04: Phase B First-Order-Link Pruning (Parity Path)

Goal:
- Implement full pruning pass semantics per spec.

Implementation tasks:
1. Receiver-group shortest-link selection (strict epsilon improvement).
2. Immediate prune mutation with receiver-preserving normal case.
3. Self-receiver terminal special case.
4. Degeneration-flag-driven repass cadence.
5. Parity guard for single-link prune failure condition.

Code review phase:
- Deep review of pass cadence, guard semantics, and deletion boundaries.

Test phase:
- Fixture tests for:
- adjacent/chained tributary pruning,
- single-incoming-link receiver prune,
- receiver preservation,
- parity guard trigger,
- termination behavior (repass only on degeneration).

Exit criteria:
- Phase B behavior stable and deterministic on targeted fixtures.

## WP-05: TopAZ Parity Validation Package

Goal:
- Prove parity against TopAZ oracle outputs for approved fixture suite.

Implementation tasks:
1. Run WBT tool on parity fixtures.
   Required fixture inclusion:
   - `/wc1/runs/cl/clueless-aftertaste/dem/wbt`
2. Compare outputs using WP-00 harness.
3. Record mismatches with categorized root causes.
4. Iterate fixes until parity acceptance criteria are met.

Code review phase:
- Independent parity review of mismatch handling and final claims.

Test phase:
- Full parity suite run in CI-friendly mode.

Exit criteria:
- Parity report committed with pass/fail matrix and signed-off verdict.

## WP-06: Error Contract + Robustness Hardening

Goal:
- Lock explicit failure behavior and defensive guarantees.

Implementation tasks:
1. Implement explicit errors for all spec-defined failure states:
- geometry mismatch,
- invalid pointer values,
- missing threshold code mappings,
- cycle detection,
- no-network conditions,
- parity guard violations.
2. Add property tests / fuzz-like randomized small-grid tests for panic safety.
3. Ensure no broad silent recovery paths.

Code review phase:
- Robustness/security-style review for hidden failure masking.

Test phase:
- Negative-case test suite with message/contract checks.

Exit criteria:
- Failure behavior is explicit, deterministic, and tested.

## WP-07: Optimization Pass (Multithreading + Performance)

Goal:
- Optimize runtime/memory while preserving parity and determinism.

Implementation tasks:
1. Profile baseline hot paths on representative large fixtures.
   Required benchmark fixture inclusion:
   - `/wc1/runs/cl/clueless-aftertaste/dem/wbt`
2. Parallelize safe regions first (candidate examples):
- inflow counting,
- provisional mask construction,
- independent per-row/per-tile scans where ordering is not parity-critical.
3. Preserve serial execution in parity-critical ordered stages unless a provably equivalent ordered parallel strategy is implemented.
4. Add optional threading controls (env/parameter if needed), defaulting to safe deterministic behavior.
5. Additional optimizations:
- allocation reuse,
- cache-friendly data layout,
- reduced temporary structures,
- branch pruning of stale candidates.

Code review phase:
- Performance review + determinism audit (single-thread vs multi-thread equivalence).

Test phase:
1. Correctness:
- full functional and parity suites under 1-thread and N-thread modes.
2. Performance:
- benchmark report vs baseline (runtime, memory, CPU utilization).

Exit criteria:
- Documented speedup on target fixtures with no correctness/parity regressions.

## WP-08: WBT Wrapper Exposure + Release Readiness

Goal:
- Expose tool via Python wrappers in `weppcloud-wbt` and finalize release artifacts.

Implementation tasks:
1. Add wrapper method to:
- `whitebox_tools.py`
- `WBT/whitebox_tools.py`
2. Ensure help docs and argument docs are consistent with tool contract.
3. Add smoke tests for wrapper invocation.
4. Prepare release notes (WBT scope only).

Code review phase:
- API/usability review of wrapper signatures and docs.

Test phase:
- `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py`
- `python -m unittest discover -s tests -p 'test_ifolp_wrapper_smoke.py'`
- wrapper smoke invocation in packaged build.

Exit criteria:
- Tool is callable via CLI and both Python wrappers in packaged artifacts.

## WP-09: Max Junctions Support (`--max_junctions`)

Goal:
- Add explicit IFOLP support for `--max_junctions` while preserving retained omitted-argument baseline behavior.

Implementation tasks:
1. Add parser/help/metadata surface for optional `--max_junctions` (non-negative integer).
2. Thread `max_junctions` into Phase B pruning inputs.
3. Implement deterministic receiver-group fan-in cap behavior when `max_junctions` is set:
- shortest-link selection remains strict-epsilon + first encounter,
- prune repeatedly within receiver group until live incoming candidate count `<= max_junctions`.
4. Keep omitted `--max_junctions` path behavior equivalent to retained baseline.
5. Add parser and phase-level tests for contract and deterministic `--max_junctions=3`.

Code review phase:
- Independent review with findings disposition; closure requires no unresolved high/medium findings.

Test phase:
- `cargo check -p whitebox_tools`
- `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture`
- `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py`

Exit criteria:
- Contract/docs/wrappers include `--max_junctions`.
- Omitted-arg parity hash remains retained baseline.
- `--max_junctions=3` behavior is deterministic and covered by tests.

## Critical Items Beyond Core Implementation

1. Clean-room compliance:
- Use TopAZ only as behavior oracle, not as source template.
- Preserve independent naming/structure in Rust implementation.

2. Reproducibility and fixtures:
- Pin fixture inputs and expected outputs with checksums.
- Include deterministic run metadata (tool version, thread setting, epsilon).

3. CI strategy:
- Split fast unit gates and slower parity/perf gates.
- Ensure parity suite runs at least on pre-release branch policy.

4. Observability:
- Add optional verbose diagnostics for pass counts, deletions, degeneration events, and timing.

5. Backward compatibility in WBT repo:
- Keep `RemoveShortStreams` available until explicitly deprecated in a separate work item.

## Suggested Execution Order and Parallelism

Primary order:
1. WP-00 -> WP-01 -> WP-02 -> WP-03 -> WP-04 -> WP-05 -> WP-06 -> WP-07 -> WP-08 -> WP-09

Parallel opportunities:
- Wrapper work (WP-08 prep) can start after WP-01 contract is stable.
- Robustness test scaffolding (WP-06 prep) can start during WP-03/04.
- Benchmark harness setup can begin before WP-07.

## Definition of Done

Implementation is complete when:
1. Tool and wrappers are implemented and registered.
2. Parity suite passes accepted TopAZ-oracle fixtures.
3. Error-contract negative tests pass.
4. Optimization pass shows measured benefit with deterministic parity preserved.
5. Code review and test gates completed for every work-package.

## Work-Package Orchestration Table

Status values:
- `backlog`
- `in_progress`
- `review`
- `blocked`
- `done`

| WP | Title | Status | Owner | Depends On | Code Review | Test Gate | Parity Gate | Perf Gate | Started | Target Finish | Completed | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| WP-00 | Baseline and Parity Harness Design | done | Codex | none | done | done | done | n/a | 2026-04-13 | 2026-04-13 | 2026-04-13 | Artifacts: `docs/iterative-first-order-link-prune/wp-00/*`; harness: `tools/ifolp_wp00_{prepare_fixtures.py,run_topaz_oracle.sh,compare_outputs.py}`; protocol updated for apples-to-apples parity via staged basin mask (`bound.tif`) and default `--comparison-domain basin_mask`; determinism canonical hash (v2 report): `f5dd0c560bb766278526f15100efe33faade5a4fc7485510058246bc10276f9d`. |
| WP-01 | Tool Scaffolding and Registration | done | Codex | WP-00 | done | done | n/a | n/a | 2026-04-13 | 2026-04-13 | 2026-04-13 | Tool + registry wiring added (`iterative_first_order_link_prune.rs`, `stream_network_analysis/mod.rs`, `tools/mod.rs`); parser contract covered for defaults/required/optional forms, missing-value guards, quote preservation, bool forms, threshold-pair enforcement, signed numeric parity, placeholder path, and registration discoverability via `cargo test -p whitebox_tools iterative_first_order_link_prune` (`13 passed`); parser tests split to companion module `iterative_first_order_link_prune_parser_tests.rs` to keep tool source non-monolithic. |
| WP-02 | Core Data Model + Deterministic Topology Kernel | done | Codex | WP-01 | done | done | n/a | n/a | 2026-04-13 | 2026-04-13 | 2026-04-13 | Added deterministic topology companion module `iterative_first_order_link_prune_topology.rs` (pointer decode/traversal, topology classification, receiver discovery, deterministic first-order-link ordering, stale-candidate checks) plus companion synthetic tests `iterative_first_order_link_prune_topology_tests.rs`; review findings dispositioned (terminal-head half-cell length, non-negative epsilon guard, mask-geometry validation for `inflow_count`) and coverage expanded for decode mapping/error, receiver edge cases, exact-epsilon ties, stale rewiring, and repeatability; gates: `cargo check -p whitebox_tools` (pass), `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` (pass, `28 passed`). ExecPlan archived at `/workdir/wepppy/docs/work-packages/20260412_ifolp_wp02_topology_kernel/prompts/completed/ifolp_wp02_topology_kernel_execplan.md`. |
| WP-03 | Phase A Source-Area Qualification | done | Codex | WP-02 | done | done | n/a | n/a | 2026-04-13 | 2026-04-13 | 2026-04-13 | Implemented Phase A in companion module `iterative_first_order_link_prune_phase_a.rs` with minimum-CSA provisional mask, row-major inline source walk mutation, receiver transitions (junction collapse + terminal recheck), and stabilization reclassification; wired Phase A into tool orchestration while keeping WP-04 Phase B explicit unsupported; added focused WP-03 tests in `iterative_first_order_link_prune_phase_a_tests.rs` for rejection/promotion, receiver transitions, no-channel failure, and deterministic traversal cadence; gates: `cargo check -p whitebox_tools` (pass), `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` (pass, `33 passed`); review findings disposition: M1 run-path test regression after Phase A I/O wiring -> fixed (parser test now asserts Phase B placeholder directly), M2 missing terminal receiver removal coverage -> fixed (dedicated test added), no unresolved high/medium; ExecPlan archived at `/workdir/wepppy/docs/work-packages/20260413_ifolp_wp03_source_area_qualification/prompts/completed/ifolp_wp03_source_area_qualification_execplan.md`. |
| WP-04 | Phase B First-Order-Link Pruning (Parity Path) | done | Codex | WP-03 | done | done | n/a | n/a | 2026-04-13 | 2026-04-13 | 2026-04-13 | Implemented companion module `iterative_first_order_link_prune_phase_b.rs` with receiver-group strict-epsilon shortest-link selection, immediate prune mutation (receiver-preserving normal case + self-receiver terminal special case), stale-candidate skip, degeneration-flag repass cadence, deterministic termination, and single-link parity guard behavior; wired orchestration in `iterative_first_order_link_prune.rs` to execute Phase A -> Phase B and emit final binary output/metadata; added companion tests `iterative_first_order_link_prune_phase_b_tests.rs` for adjacent/chained pruning, receiver transitions, guard behavior, self-receiver prune behavior, no-channel entry failure, and termination cadence; gates: `cargo check -p whitebox_tools` (pass), `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` (pass, `39 passed`); review findings disposition: M1 local MSCL from threshold table was not propagated into phase execution -> fixed (populate `local_mscl_m` during preparation), M2 no-channel state after in-pass pruning needed explicit guard path -> fixed (hard fail with explicit message), no unresolved high/medium; ExecPlan archived at `/workdir/wepppy/docs/work-packages/20260413_ifolp_wp04_first_order_link_pruning/prompts/completed/ifolp_wp04_first_order_link_pruning_execplan.md`. |
| WP-05 | TopAZ Parity Validation Package | done | Codex | WP-04 | done | done | done | n/a | 2026-04-13 | 2026-04-13 | 2026-04-14 | Iterative remediation cycle closed with retained IFOLP state (H-002 + H-009 + H-010 + H-011) and deterministic basin-masked canonical hash `07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1` across `/tmp/ifolp_wp05_remediate/run1` + `run2`; anchor fixture reached exact parity and non-anchor residuals were accepted as effective parity after provenance-aligned probe evidence (`cd013e16c16f14ac00e4c8b1b2b4cf9c325449bd54a74cd6fd640f37f183beb5`, low FP-only deltas). Closure artifacts: `/workdir/wepppy/docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/{hypothesis_log.md,mismatch_disposition.md,tracker.md}`; closure execplan archived at `/workdir/wepppy/docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/prompts/completed/ifolp_wp05_pruning_drift_remediation_execplan_closure_20260414.md`. |
| WP-06 | Error Contract + Robustness Hardening | done | Codex | WP-04 | done | done | done | n/a | 2026-04-13 | 2026-04-14 | 2026-04-13 | Hardened error contracts without pruning-semantic changes: finite numeric guards (`epsilon`, cell sizes, threshold-table values) plus duplicate threshold-code rejection; added companion tests across parser/Phase A/Phase B/topology. Gates: `cargo check -p whitebox_tools` (pass), `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` (pass, `50 passed`). Parity regression reran `/tmp/ifolp_wp05_remediate/run1` + `run2`; canonical hash `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83` in both runs and identical to retained `parity-report.final_effective.canonical.json` artifacts (no retained-state drift). Review disposition: no unresolved high/medium findings. ExecPlan archived at `/workdir/wepppy/docs/work-packages/20260413_ifolp_wp06_error_contract_robustness_hardening/prompts/completed/ifolp_wp06_error_contract_robustness_hardening_execplan.md`. |
| WP-07 | Optimization Pass (Multithreading + Performance) | done | Codex | WP-05, WP-06 | done | done | done | done | 2026-04-13 | 2026-04-15 | 2026-04-13 | Optimized topology hot path in `iterative_first_order_link_prune_topology.rs` with bounded multithreaded inflow counting for large grids (`rows >= 1024`), allocation reduction in `inflow_count`, and downstream-classification micro-optimization; added concurrency regression test `iterative_first_order_link_prune_topology_parallel_inflow_counts_match_manual_reference`. Gates: `cargo check -p whitebox_tools` (pass), `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` (pass, `51 passed`). Benchmarks vs WP-07 baseline (`run1`, 5 repeats): `blackwood_60_5` `0.046s -> 0.042s` (-8.70%), `clueless_aftertaste_anchor_10_100` `0.020s -> 0.020s` (0.00%), `gatecreek_10m_30_2` `0.750s -> 0.706s` (-5.87%); artifacts in `/workdir/wepppy/docs/work-packages/20260413_ifolp_wp07_optimization_pass/benchmarks/`. Parity regression reruns on `/tmp/ifolp_wp05_remediate/run1` + `run2` produced canonical hash `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83` identical to retained `parity-report.final_effective.canonical.json` artifacts (no retained-state drift). Review disposition: no unresolved high/medium findings. ExecPlan archived at `/workdir/wepppy/docs/work-packages/20260413_ifolp_wp07_optimization_pass/prompts/completed/ifolp_wp07_optimization_pass_execplan.md`. |
| WP-08 | WBT Wrapper Exposure + Release Readiness | done | Codex | WP-05, WP-06, WP-07 | done | done | done | n/a | 2026-04-13 | 2026-04-15 | 2026-04-13 | Added IFOLP wrapper surface to both Python bindings (`whitebox_tools.py`, `WBT/whitebox_tools.py`) and validated CLI/wrapper contract (`--listtools`, `--toolhelp=IterativeFirstOrderLinkPrune`, required-arg and threshold-pair error checks). Required gates passed: `cargo check -p whitebox_tools`, `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` (`51 passed`, `0 failed`), `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py`. Parity spot checks rerun on retained run roots (`/tmp/ifolp_wp05_remediate/run1`, `run2`) with fresh `candidate_wp08` outputs and compare harness produced canonical hash `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83` in both runs, byte-identical to retained `parity-report.final_effective.canonical.json` artifacts (no retained-state drift). Mandatory review disposition completed with no unresolved high/medium findings. ExecPlan archived at `/workdir/wepppy/docs/work-packages/20260413_ifolp_wp08_wrapper_release_readiness/prompts/completed/ifolp_wp08_wrapper_release_readiness_execplan.md`. |
| WP-09 | Max Junctions Support (`--max_junctions`) | done | Codex | WP-08 | done | done | done | n/a | 2026-04-14 | 2026-04-14 | 2026-04-14 | Added IFOLP `--max_junctions` contract support end-to-end: parser/help metadata, Phase B fan-in cap pruning when explicitly set, and wrapper exposure updates in both Python bindings. Omitted-argument behavior retained by design; fresh parity regression on `/tmp/ifolp_wp05_remediate/run1` + `run2` produced canonical hash `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83`, byte-identical to retained `parity-report.final_effective.canonical.json` artifacts. Added deterministic `--max_junctions=3` phase test and rerun parity compare reports (`parity-report.wp09_maxj3*.json`) showed deterministic canonical stability across run1/run2. Required gates passed: `cargo check -p whitebox_tools`, `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` (`77 passed`, `0 failed`), `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py`. Mandatory review disposition closed with no unresolved high/medium findings. |
