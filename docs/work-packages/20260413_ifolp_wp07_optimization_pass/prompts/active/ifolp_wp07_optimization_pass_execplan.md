# Execute WP-07 IFOLP Optimization Pass in weppcloud-wbt

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this plan is executed, IFOLP runs faster on representative fixtures through bounded optimization changes (including multithreading where justified) while preserving retained WP-05/WP-06 behavior verified by parity-regression checks.

## Progress

- [x] (2026-04-13 17:05Z) ExecPlan authored and activated.
- [ ] Capture baseline benchmark and parity evidence for retained implementation.
- [ ] Implement bounded optimization changes and targeted tests.
- [ ] Capture post-change benchmark and parity-regression evidence.
- [ ] Execute mandatory code review and disposition findings by severity.
- [ ] Run final gates and update WBT/WEPPpy status artifacts.
- [ ] Archive this ExecPlan to `prompts/completed/` with closure outcomes.

## Surprises & Discoveries

- Pending.

## Decision Log

- Decision: Preserve retained WP-05/WP-06 parity baseline as non-negotiable optimization guard.
  Rationale: WP-07 scope is performance only.
  Date/Author: 2026-04-13 / Codex.

## Outcomes & Retrospective

- Pending.

## Context and Orientation

Primary execution repository:
- `/workdir/weppcloud-wbt`

Governing docs:
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`
- `/workdir/wepppy/docs/work-packages/20260413_ifolp_wp06_error_contract_robustness_hardening/{package.md,tracker.md}`

Core IFOLP modules:
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune.rs`
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_a.rs`
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_b.rs`
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_topology.rs`
- Companion tests in same directory.

Retained parity baseline contract:
- Canonical retained artifact hash: `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83`.
- Do not retain optimizations that alter parity metrics unless explicitly approved by a superseding package.

## Plan of Work

Milestone 1: Baseline measurement and guardrails.
- Record baseline runtime metrics for target fixtures and current parity outputs.
- Define acceptance thresholds for performance gain and parity preservation.

Milestone 2: Implement bounded optimizations.
- Apply one optimization cluster at a time (e.g., thread partitioning, allocation reductions, traversal caching).
- Add targeted tests for any new concurrency-sensitive behavior.

Milestone 3: Validate and compare.
- Re-run benchmark suite and compare against baseline.
- Re-run parity-regression checks and verify no retained-state drift.

Milestone 4: Review/disposition and closeout.
- Perform correctness-focused review.
- Disposition findings by severity and close only with no unresolved high/medium findings.

## Concrete Steps

Run from `/workdir/weppcloud-wbt` unless noted.

1. Capture baseline benchmark and parity artifacts.
   - Use fixed fixture set and explicit thread settings.
   - Record commands and outputs in WP-07 tracker.

2. Implement one bounded optimization increment.
   - Edit only required IFOLP modules.
   - Add/update targeted tests.

3. Run required gates.
   - `cargo check -p whitebox_tools`
   - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture`

4. Run parity regression against retained baseline.
   - Re-run WP-00/WP-05 comparison workflow on retained run roots.
   - Compare canonical outputs to retained baseline artifacts.

5. Run post-change benchmarks and compare.
   - Capture repeated timings and summarize per-fixture deltas.

6. Mandatory code review/disposition.
   - Classify findings by severity.
   - Closure gate: no unresolved high/medium findings.

7. Update artifacts and close.
   - Update `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md` WP-07 row.
   - Update WP-07 `package.md`/`tracker.md`.
   - Archive this ExecPlan to `prompts/completed/`.

## Validation and Acceptance

WP-07 is accepted when all are true:
- Performance improvement is evidenced and reproducible.
- Parity-regression checks show no retained-state drift.
- Determinism and targeted IFOLP tests remain passing.
- Code review/disposition is complete with no unresolved high/medium findings.
- Required cargo gates pass.

## Idempotence and Recovery

- Keep optimization changes incremental and reversible.
- If an optimization improves speed but changes parity unexpectedly, reject or isolate behind explicit non-default gating for follow-up review.
- If benchmark noise prevents clear acceptance, rerun with fixed settings and document uncertainty before retention.

## Artifacts and Notes

- WP-07 governance tracker:
  - `docs/work-packages/20260413_ifolp_wp07_optimization_pass/tracker.md`
- WBT orchestration table:
  - `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`

## Interfaces and Dependencies

- Preserve IFOLP CLI/wrapper behavior.
- Preserve retained WP-05/WP-06 semantics while optimizing.
- Keep source/test organization non-monolithic using companion modules.

---
Revision Note (2026-04-13 / Codex): Initial WP-07 ExecPlan authored with mandatory benchmark + parity + review/disposition closure gates.
