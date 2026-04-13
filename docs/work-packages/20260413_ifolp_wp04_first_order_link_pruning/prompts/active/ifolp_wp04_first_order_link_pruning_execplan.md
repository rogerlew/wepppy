# Execute WP-04 Phase B First-Order-Link Pruning in weppcloud-wbt

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this plan is executed, IFOLP Phase B pruning behavior is implemented in `/workdir/weppcloud-wbt` with deterministic first-order-link selection and prune mutation semantics that align with the IFOLP specification. This enables WP-05 parity validation to run against a complete pruning path instead of the current WP-04 placeholder boundary.

## Progress

- [x] (2026-04-13 07:34Z) ExecPlan authored and activated.
- [ ] Implement receiver-group shortest-link selection with strict epsilon-improvement semantics.
- [ ] Implement immediate prune mutation path, including receiver-preserving normal case and self-receiver terminal special case.
- [ ] Implement degeneration-flag-driven repass cadence and stable termination behavior.
- [ ] Implement parity guard behavior for single-link prune outcomes.
- [ ] Add and pass targeted WP-04 tests.
- [ ] Complete code-review findings/disposition with no unresolved high/medium issues.
- [ ] Run validation gates and update WBT WP-04 row to `done`.
- [ ] Archive ExecPlan to `prompts/completed/` with closure outcomes.

## Surprises & Discoveries

- Observation: WP-03 now executes real raster I/O before entering the WP-04 placeholder path; run-path tests must remain explicit about this boundary.
  Evidence: `iterative_first_order_link_prune_parser_tests.rs` now asserts Phase B placeholder behavior directly.
- Observation: Deterministic topology and Phase A helper modules already exist and should be reused rather than duplicated.
  Evidence: companion modules `iterative_first_order_link_prune_topology.rs` and `iterative_first_order_link_prune_phase_a.rs` are present with targeted tests.

## Decision Log

- Decision: Keep WP-04 constrained to deterministic Phase B pruning behavior plus tests and review disposition; no parity-campaign scope in this package.
  Rationale: Preserves package boundaries and keeps WP-05 focused on oracle parity evidence.
  Date/Author: 2026-04-13 / Codex.
- Decision: Require explicit findings severity/disposition as a closure gate (fixed/accepted/deferred, no unresolved high/medium).
  Rationale: Pruning cadence and mutation rules are regression-prone and parity-critical.
  Date/Author: 2026-04-13 / Codex.

## Outcomes & Retrospective

- Pending execution.

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
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_a.rs`

Recommended WP-04 companion modules/tests:
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_b.rs`
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_b_tests.rs`

## Plan of Work

Milestone 1 implements deterministic Phase B candidate selection. Build receiver-group candidate discovery and shortest-link selection with strict epsilon-improvement semantics, preserving deterministic encounter order and avoiding non-deterministic tie behavior.

Milestone 2 implements prune mutation and cadence semantics. Apply immediate prune mutation after each accepted candidate, enforce receiver-preserving behavior in normal cases, handle self-receiver terminal special case explicitly, and execute degeneration-flag-controlled repasses until termination.

Milestone 3 hardens behavior with targeted tests and review disposition. Add synthetic-grid tests for adjacent/chained pruning, receiver transitions, guard behavior, and termination cadence. Run focused review, disposition findings by severity, and close only when no unresolved high/medium findings remain.

Milestone 4 closes package state. Run compile/test gates, update WBT WP-04 row to `done`, and archive this ExecPlan with closure outcomes.

## Concrete Steps

Run from `/workdir/weppcloud-wbt`.

1. Read governing docs.
   - `sed -n '1,220p' AGENTS.md`
   - `sed -n '1,260p' DEVELOPING_TOOLS.md`
   - `sed -n '1,380p' docs/iterative-first-order-link-prune/specification.md`
   - `sed -n '170,260p' docs/iterative-first-order-link-prune/implementation-plan.md`

2. Implement WP-04 Phase B module(s).
   - Add/extend companion modules for:
     - receiver-group shortest-link selection,
     - strict epsilon-improvement acceptance logic,
     - immediate prune mutation semantics,
     - receiver-preserving normal-case logic,
     - self-receiver terminal special-case logic,
     - degeneration-flag repass cadence and termination.

3. Wire Phase B execution from IFOLP entry orchestration.
   - Preserve parser contract from WP-01 and Phase A behavior from WP-03.
   - Keep source/test file organization non-monolithic.

4. Add targeted tests.
   - Adjacent/chained tributary pruning behavior.
   - Single-incoming-link receiver prune behavior.
   - Receiver-preservation behavior for non-terminal cases.
   - Parity guard trigger behavior and message contract.
   - Termination behavior (repass only when degeneration occurs).

5. Mandatory code-review and disposition phase.
   - Run focused review for correctness/regression risks.
   - Record findings with severity (high/medium/low).
   - Disposition each finding as fixed/accepted/deferred with rationale.
   - Closure gate: no unresolved high/medium findings.

6. Run validation gates.
   - `cargo check -p whitebox_tools`
   - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture`

7. Update status artifacts.
   - Update `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md` WP-04 row:
     - `Status=done`
     - `Owner=<executor>`
     - `Code Review=done`
     - `Test Gate=done`
     - fill `Started`, `Completed`, `Notes` with review disposition summary.

## Validation and Acceptance

This ExecPlan is accepted when all of the following are true:

- Phase B pruning behavior is implemented per specification.
- Targeted WP-04 tests pass and cover pruning/receiver/guard/termination behavior.
- Deterministic selection and prune mutation behavior is demonstrated by tests.
- Review findings are dispositioned with no unresolved high/medium items.
- `cargo check` and targeted IFOLP tests pass.
- WBT WP-04 row is marked `done` with review/test gates complete.

## Idempotence and Recovery

- Keep changes modular; avoid broad refactors outside IFOLP modules.
- If a pruning rule is ambiguous, add a failing test that documents expected behavior before changing logic.
- If review surfaces unresolved high/medium regression risk, stop closeout and update this ExecPlan with the blocker and mitigation.

## Artifacts and Notes

- WP-04 governance tracker:
  - `docs/work-packages/20260413_ifolp_wp04_first_order_link_pruning/tracker.md`
- WBT status table:
  - `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`

## Interfaces and Dependencies

- Preserve WP-01 CLI/parser contract, WP-02 topology kernel behavior, and WP-03 Phase A semantics.
- Keep source/test organization non-monolithic using concern-specific companion modules.
- No WEPPpy integration changes in WP-04.

---
Revision Note (2026-04-13 / Codex): Initial WP-04 ExecPlan authored with mandatory code-review/disposition closure gate.
