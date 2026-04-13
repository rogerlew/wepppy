# Execute WP-02 Core Topology Kernel in weppcloud-wbt

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this plan is executed, IFOLP has a deterministic topology kernel in `/workdir/weppcloud-wbt` that can decode D8 pointers (Whitebox and ESRI), classify local stream-topology states, discover first-order links in deterministic row-major order, and reject stale candidates safely. WP-03 and WP-04 can then consume these primitives without re-solving core topology mechanics.

## Progress

- [x] (2026-04-13 05:35Z) ExecPlan authored and activated.
- [x] (2026-04-13 06:15Z) Implemented pointer decode + traversal primitives.
- [x] (2026-04-13 06:15Z) Implemented topology-state classification + receiver detection primitives.
- [x] (2026-04-13 06:15Z) Implemented deterministic first-order-link discovery ordering kernel.
- [x] (2026-04-13 06:15Z) Implemented stale-candidate validity checks.
- [x] (2026-04-13 06:15Z) Added and passed synthetic-grid determinism tests.
- [x] (2026-04-13 06:15Z) Ran WP-02 validation gates and updated WBT orchestration row to `done`.
- [x] (2026-04-13 06:15Z) Prepared ExecPlan closure summary and archival move to `prompts/completed/`.

## Surprises & Discoveries

- Observation: WP-01 completed with companion parser tests split into a dedicated file, establishing a non-monolithic pattern for WP-02.
  Evidence: `iterative_first_order_link_prune_parser_tests.rs` exists and is referenced in WP-01 notes.
- Observation: Rust submodule resolution from `iterative_first_order_link_prune.rs` required explicit `#[path = "..."]` to locate sibling companion files instead of nested directory defaults.
  Evidence: compile failure `E0583` resolved by path-qualified module declarations in `iterative_first_order_link_prune.rs`.

## Decision Log

- Decision: Keep WP-02 strictly primitive-focused; no source-area qualification decisions and no pruning/degeneration decisions in this package.
  Rationale: Preserve package boundaries and make WP-03/WP-04 behavior reviews independent.
  Date/Author: 2026-04-13 / Codex.
- Decision: Keep new topology kernel in dedicated companion source/tests and leave run-path placeholders unchanged.
  Rationale: Satisfies non-monolithic requirement while avoiding scope creep into WP-03/04 phase execution behavior.
  Date/Author: 2026-04-13 / Codex.

## Outcomes & Retrospective

- Code structure choices:
  - Added `iterative_first_order_link_prune_topology.rs` for deterministic kernel primitives.
  - Added `iterative_first_order_link_prune_topology_tests.rs` for synthetic topology behavior tests.
  - Kept parser tests and run placeholders in existing files to preserve WP boundaries.
- Deterministic test evidence:
  - `cargo check -p whitebox_tools` passed.
  - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` passed with `28 passed; 0 failed`.
  - New tests cover Whitebox/ESRI decode/traversal, inflow/state classification, deterministic source/receiver order, epsilon tie behavior, and stale-candidate validity checks.
- Findings/fixes:
  - Fixed Rust submodule path discovery using explicit `#[path = "..."]` annotations.
  - Scoped `#[allow(dead_code)]` to the new topology module import because WP-03/04 will consume the primitives while WP-02 keeps run-path placeholders.
- Gaps before WP-03:
  - Phase A source-area qualification and receiver mutation semantics remain intentionally unimplemented in this package.

## Context and Orientation

Primary execution repository:
- `/workdir/weppcloud-wbt`

Required governing docs:
- `/workdir/weppcloud-wbt/AGENTS.md`
- `/workdir/weppcloud-wbt/DEVELOPING_TOOLS.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`

Primary implementation file from WP-01:
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune.rs`

Recommended WP-02 module organization (non-monolithic):
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_topology.rs`
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_topology_tests.rs`

Existing parser tests remain separate:
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_parser_tests.rs`

## Plan of Work

Milestone 1 establishes pointer and traversal primitives. Add typed helpers for Whitebox/ESRI D8 decoding and safe neighbor traversal, including explicit handling of out-of-grid and non-stream destinations.

Milestone 2 implements topology-state and deterministic link discovery primitives. Add reusable classification helpers (head/mid/junction/terminal roles per spec intent) and deterministic row-major discovery sequencing for first-order-link candidates.

Milestone 3 implements stale-candidate checks and hardens tests. Add candidate-alive validation to support later immediate-mutation passes and verify deterministic behavior with synthetic fixtures including tie cases under epsilon.

Milestone 4 closes WP-02 package state. Run compile/tests, perform review fixes, update WBT WP-02 row to `done`, and move this ExecPlan to completed with outcomes.

## Concrete Steps

Run from `/workdir/weppcloud-wbt`.

1. Read governing docs.
   - `sed -n '1,220p' AGENTS.md`
   - `sed -n '1,260p' DEVELOPING_TOOLS.md`
   - `sed -n '1,320p' docs/iterative-first-order-link-prune/specification.md`
   - `sed -n '1,360p' docs/iterative-first-order-link-prune/implementation-plan.md`

2. Implement WP-02 primitives in companion module(s).
   - Add/extend topology module(s) for:
     - pointer decode (`whitebox` + `esri`),
     - neighbor traversal,
     - topology classification,
     - receiver detection,
     - deterministic discovery ordering,
     - stale-candidate validation.

3. Wire module usage from IFOLP entry file.
   - Keep entry file orchestration-focused.
   - Avoid moving parser tests back into entry file.

4. Add targeted synthetic tests.
   - Inflow-count correctness.
   - State-classification correctness.
   - Deterministic discovery order (row-major encounter behavior).
   - Epsilon tie behavior (first encountered wins under strict improvement rule intent).
   - Stale-candidate skip validity behavior.

5. Run validation gates.
   - `cargo check -p whitebox_tools`
   - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture`

6. Update package/plan state.
   - Update `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md` WP-02 row:
     - `Status=done`
     - `Owner=<executor>`
     - `Code Review=done`
     - `Test Gate=done`
     - fill `Started`, `Completed`, `Notes`.

## Validation and Acceptance

This ExecPlan is accepted when all of the following are true:

- Kernel primitives for pointer decode, traversal, classification, discovery order, and stale-candidate validity are implemented.
- Synthetic tests cover inflow/state/order/tie/stale-candidate behavior and pass.
- Tool build/check gates pass.
- File organization remains non-monolithic with concern-specific source/test modules.
- WBT WP-02 row is marked `done` with required gate fields completed.

## Idempotence and Recovery

- Changes are module-local and rerunnable.
- If deterministic tests fail intermittently, capture failing seed/case in test fixtures before additional refactor.
- If scope creep into WP-03/04 occurs, revert that portion and keep WP-02 primitives only.

## Artifacts and Notes

- WP-02 governance tracker:
  - `docs/work-packages/20260412_ifolp_wp02_topology_kernel/tracker.md`
- WBT status table:
  - `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`

## Interfaces and Dependencies

- Preserve WP-01 parser/interface contract.
- Do not change WEPPpy integration behavior in this package.
- Maintain companion-module structure for source and tests to prevent monolithic growth.

---
Revision Note (2026-04-13 / Codex): Initial WP-02 ExecPlan authored for execution-agent handoff.
Revision Note (2026-04-13 / Codex): WP-02 execution completed; deterministic topology kernel delivered with passing gates and documentation updates.
