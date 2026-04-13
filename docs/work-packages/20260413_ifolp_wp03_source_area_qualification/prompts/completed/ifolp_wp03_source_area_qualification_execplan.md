# Execute WP-03 Phase A Source-Area Qualification in weppcloud-wbt

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this plan is executed, IFOLP Phase A source-area qualification behavior is implemented in `/workdir/weppcloud-wbt` with deterministic row-major inline mutation semantics and receiver transition handling per specification. This delivers the qualification stage required before Phase B pruning (WP-04) can be implemented safely.

## Progress

- [x] (2026-04-13 06:05Z) ExecPlan authored and activated.
- [x] (2026-04-13 07:04Z) Implemented provisional stream mask generation from minimum active CSA.
- [x] (2026-04-13 07:07Z) Implemented Phase A source walk qualification with row-major inline mutation.
- [x] (2026-04-13 07:10Z) Implemented receiver handling for junction collapse and terminal recheck semantics.
- [x] (2026-04-13 07:11Z) Implemented topology reclassification after qualification stabilization.
- [x] (2026-04-13 07:16Z) Added and passed targeted WP-03 tests.
- [x] (2026-04-13 07:17Z) Completed code-review findings/disposition with no unresolved high/medium issues.
- [x] (2026-04-13 07:28Z) Ran validation gates and updated WBT WP-03 row to `done`.
- [x] (2026-04-13 07:28Z) Archived ExecPlan to `prompts/completed/` with closure outcomes.

## Surprises & Discoveries

- Observation: WP-02 delivered deterministic topology primitives and companion tests; WP-03 should consume those helpers rather than duplicating topology logic.
  Evidence: `iterative_first_order_link_prune_topology.rs` and companion tests exist from WP-02.
- Observation: Once Phase A was wired into the tool run-path, parser test expectations changed because run now attempts real raster I/O before hitting the Phase B placeholder.
  Evidence: initial WP-03 test run returned `NotFound` for synthetic parser test paths.
- Observation: `cargo fmt --all` could not be used as a safe closure step because unrelated pre-existing trailing whitespace caused rustfmt failure and partial unrelated edits.
  Evidence: rustfmt error in `whitebox-tools-app/src/tools/math_stat_analysis/principal_component_analysis.rs` and temporary unrelated file modifications, which were restored.

## Decision Log

- Decision: Keep WP-03 strictly Phase A qualification behavior; no first-order-link pruning decisions in this package.
  Rationale: Preserve WP boundary clarity and isolate regressions to qualification semantics.
  Date/Author: 2026-04-13 / Codex.
- Decision: Keep Phase B as explicit unsupported placeholder after successful Phase A execution in WP-03.
  Rationale: Avoid ambiguous partial tool behavior before WP-04 pruning semantics are implemented.
  Date/Author: 2026-04-13 / Codex.

## Outcomes & Retrospective

Implementation outcomes:
- Added non-monolithic Phase A companion module:
  - `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_a.rs`
- Implemented:
  - provisional mask from minimum active CSA,
  - row-major source scanning with inline mutation,
  - receiver transitions (junction collapse + terminal recheck),
  - stabilization cadence with topology reclassification.
- Wired Phase A execution from IFOLP entry orchestration in:
  - `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune.rs`
- Added targeted WP-03 tests in:
  - `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_a_tests.rs`

Review findings and disposition:
- `M1` (fixed): parser run-path test failed (`NotFound` vs `Unsupported`) after Phase A I/O wiring; fixed by asserting Phase B placeholder contract directly in parser tests.
- `M2` (fixed): terminal receiver transition removal path lacked explicit regression coverage; fixed by adding dedicated terminal recheck-removal test.
- `L1` (accepted): workspace-wide `cargo fmt --all` remains blocked by unrelated pre-existing trailing whitespace outside WP-03 scope.
- Closure status: no unresolved high/medium findings.

Validation outcomes:
- `cargo check -p whitebox_tools` -> pass.
- `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` -> pass (`33 passed`, `0 failed`).

Remaining risks before WP-04:
- Phase B pruning semantics are still intentionally unimplemented; WP-04 must define and validate pruning-pass behavior against the existing Phase A baseline.

## Context and Orientation

Primary execution repository:
- `/workdir/weppcloud-wbt`

Required governing docs:
- `/workdir/weppcloud-wbt/AGENTS.md`
- `/workdir/weppcloud-wbt/DEVELOPING_TOOLS.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`

Relevant source modules:
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune.rs`
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_topology.rs`

Recommended WP-03 companion modules/tests:
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_a.rs`
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_a_tests.rs`

## Plan of Work

Milestone 1 implements Phase A qualification mechanics. Add provisional-mask generation from minimum active CSA threshold, then implement source qualification walks for head/terminal-head classes using row-major traversal and inline mutation semantics.

Milestone 2 implements receiver-state transitions and stabilization behavior. Add junction-collapse handling and terminal-with-one-inflow recheck behavior, then reclassify topology after qualification changes stabilize.

Milestone 3 hardens tests and review disposition. Add targeted tests for source rejection/promotion and receiver transition edge cases. Run focused code review, disposition findings with code/test updates, and verify no unresolved high/medium findings remain.

Milestone 4 closes WP-03 package state. Run compile/test gates, update WBT WP-03 row to `done`, and archive this ExecPlan to completed with outcome summary.

## Concrete Steps

Run from `/workdir/weppcloud-wbt`.

1. Read governing docs.
   - `sed -n '1,220p' AGENTS.md`
   - `sed -n '1,260p' DEVELOPING_TOOLS.md`
   - `sed -n '1,340p' docs/iterative-first-order-link-prune/specification.md`
   - `sed -n '1,380p' docs/iterative-first-order-link-prune/implementation-plan.md`

2. Implement WP-03 source-area qualification logic.
   - Add/extend Phase A module(s) for:
     - provisional mask by active CSA threshold,
     - row-major source scan,
     - inline mutation during walk,
     - receiver transitions,
     - stabilization + topology reclassification.

3. Wire Phase A execution from IFOLP entry orchestration.
   - Preserve parser contract from WP-01.
   - Preserve topology helper reuse from WP-02.
   - Do not implement WP-04 pruning logic.

4. Add targeted tests.
   - Source rejection/promotion behavior.
   - Junction collapse transition behavior.
   - Terminal one-inflow recheck behavior.
   - No-channel failure behavior after qualification.
   - Deterministic row-major traversal/update cadence behavior.

5. Mandatory code-review and disposition phase.
   - Run a focused review pass for correctness/regression risks.
   - Record findings with severity (high/medium/low).
   - Disposition each finding as fixed/accepted/deferred with rationale.
   - Closure gate: no unresolved high/medium findings.

6. Run validation gates.
   - `cargo check -p whitebox_tools`
   - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture`

7. Update status artifacts.
   - Update `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md` WP-03 row:
     - `Status=done`
     - `Owner=<executor>`
     - `Code Review=done`
     - `Test Gate=done`
     - fill `Started`, `Completed`, `Notes` with review disposition summary.

## Validation and Acceptance

This ExecPlan is accepted when all of the following are true:

- Phase A qualification behavior is implemented per spec semantics.
- Targeted WP-03 tests pass and cover source/receiver transition edge cases.
- Deterministic row-major inline mutation behavior is demonstrated by tests.
- Review findings are dispositioned with no unresolved high/medium items.
- `cargo check` and targeted IFOLP tests pass.
- WBT WP-03 row is marked `done` with review/test gates complete.

## Idempotence and Recovery

- Keep changes modular; avoid large mixed refactors.
- If a qualification rule is ambiguous, add an explicit test before adjusting behavior.
- If review surfaces major regression risk, halt WP closeout until findings are resolved or explicitly accepted.

## Artifacts and Notes

- WP-03 governance tracker:
  - `docs/work-packages/20260413_ifolp_wp03_source_area_qualification/tracker.md`
- WBT status table:
  - `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`

## Interfaces and Dependencies

- Preserve WP-01 CLI/parser contract and WP-02 topology helper behavior.
- Keep source/test file organization non-monolithic.
- No WEPPpy integration changes in WP-03.

---
Revision Note (2026-04-13 / Codex): Initial WP-03 ExecPlan authored with mandatory code-review/disposition closure gate.
