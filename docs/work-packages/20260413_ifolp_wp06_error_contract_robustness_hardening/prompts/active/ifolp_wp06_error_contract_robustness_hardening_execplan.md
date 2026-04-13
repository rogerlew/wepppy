# Execute WP-06 IFOLP Error Contract + Robustness Hardening in weppcloud-wbt

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this plan is executed, IFOLP failure behavior is hardened for invalid and degenerate states while preserving the retained WP-05 pruning semantics. Users gain more predictable error contracts and robustness under edge conditions without losing established parity behavior.

## Progress

- [x] (2026-04-13 16:40Z) ExecPlan authored and activated.
- [ ] Identify and classify targeted error-contract/robustness gaps (parser, input prep, Phase A, Phase B).
- [ ] Implement bounded hardening changes and companion tests.
- [ ] Run parity-regression checks against retained WP-05 baseline.
- [ ] Execute mandatory code review and disposition findings by severity.
- [ ] Run final gates and update WBT/WEPPpy status artifacts.
- [ ] Archive this ExecPlan to `prompts/completed/` with closure outcomes.

## Surprises & Discoveries

- Pending.

## Decision Log

- Decision: Treat retained WP-05 IFOLP state as baseline contract for all WP-06 parity checks.
  Rationale: WP-05 closure accepted this state as effective parity; WP-06 is hardening-only.
  Date/Author: 2026-04-13 / Codex.

## Outcomes & Retrospective

- Pending.

## Context and Orientation

Primary execution repository:
- `/workdir/weppcloud-wbt`

Governing docs:
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`
- `/workdir/wepppy/docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/{hypothesis_log.md,mismatch_disposition.md,tracker.md}`

Core IFOLP modules:
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune.rs`
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_a.rs`
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_b.rs`
- Companion test modules in same directory.

Baseline parity contract (must preserve unless explicitly superseded):
- Retained canonical hash: `07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1`.
- Retained hypothesis state: H-002 + H-009 + H-010 + H-011.

## Plan of Work

Milestone 1: Contract inventory and target selection.
- Enumerate current negative/failure paths and expected error contracts in parser, input preparation, Phase A, and Phase B.
- Select bounded hardening targets that do not alter pruning semantics.

Milestone 2: Implement hardening changes and tests.
- Add explicit contract checks and deterministic failure behavior.
- Add targeted tests that fail before and pass after hardening.

Milestone 3: Baseline-preservation validation.
- Re-run targeted IFOLP tests and parity-regression checks.
- Confirm retained baseline hash/metrics are preserved (or document justified variance).

Milestone 4: Review/disposition and closeout.
- Perform code review focused on regressions and contract drift.
- Disposition findings with severity and close only with no unresolved high/medium items.

## Concrete Steps

Run from `/workdir/weppcloud-wbt` unless noted.

1. Inventory targeted error-contract gaps.
   - Read IFOLP modules and tests.
   - Record candidate gaps in WP-06 tracker notes.

2. Implement bounded hardening changes.
   - Edit only required IFOLP files.
   - Add/extend companion tests for each hardened path.

3. Run required test/build gates.
   - `cargo check -p whitebox_tools`
   - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture`

4. Run parity-regression check using WP-00/WP-05 harness.
   - Reuse fixture manifest including anchor fixture.
   - Compare retained outputs against oracle and prior retained baseline evidence.
   - If canonical hash changes, explain root cause and severity in disposition.

5. Mandatory code review/disposition.
   - Review changes for correctness, behavior regressions, and contract drift.
   - Record findings in WP-06 tracker with severity and disposition.
   - Closure gate: no unresolved high/medium findings.

6. Update docs and close package state.
   - Update `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md` WP-06 row (`Status`, `Code Review`, `Test Gate`, dates, notes).
   - Update WP-06 `tracker.md` and `package.md`.
   - Archive this ExecPlan to `prompts/completed/` with outcomes.

## Validation and Acceptance

WP-06 is accepted when all are true:
- Targeted error-contract hardening is implemented and tested.
- Robustness changes do not introduce unintended pruning-semantic drift.
- Retained WP-05 baseline remains the parity reference for follow-on work.
- Code review/disposition is complete with no unresolved high/medium findings.
- Required cargo gates pass.

## Idempotence and Recovery

- Keep hardening changes bounded and additive.
- If a hardening change alters parity unexpectedly, revert or supersede with explicit rationale.
- If baseline parity cannot be preserved, document blocker and stop closure.

## Artifacts and Notes

- WP-06 governance tracker:
  - `docs/work-packages/20260413_ifolp_wp06_error_contract_robustness_hardening/tracker.md`
- WBT orchestration table:
  - `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`

## Interfaces and Dependencies

- Preserve IFOLP CLI and wrapper contracts.
- Preserve retained WP-05 pruning semantics unless a follow-on package explicitly changes baseline.
- Keep source/test organization non-monolithic using companion modules.

---
Revision Note (2026-04-13 / Codex): Initial WP-06 ExecPlan authored with mandatory review/disposition and retained-baseline parity-preservation gate.
