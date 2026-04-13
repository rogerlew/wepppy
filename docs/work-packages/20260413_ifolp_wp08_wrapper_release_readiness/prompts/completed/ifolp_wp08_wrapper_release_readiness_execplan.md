# Execute WP-08 IFOLP WBT Wrapper Exposure + Release Readiness

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this plan is executed, IFOLP is validated as release-ready at wrapper and packaging surfaces with contract-consistent behavior and retained parity preserved. This is the final readiness gate before downstream promotion.

## Progress

- [x] (2026-04-13 17:42Z) ExecPlan authored and activated.
- [x] (2026-04-13 20:41Z) Verified CLI + wrapper exposure and argument/help contract consistency.
- [x] (2026-04-13 20:43Z) Ran wrapper/packaging smoke checks and targeted IFOLP tests.
- [x] (2026-04-13 20:46Z) Ran parity spot checks against retained baseline artifacts.
- [x] (2026-04-13 20:47Z) Performed mandatory code review and findings disposition.
- [x] (2026-04-13 20:47Z) Updated WP-08 rows/docs and archived this ExecPlan.

## Surprises & Discoveries

- IFOLP was registered and callable via CLI, but wrapper exposure was missing in both `whitebox_tools.py` bindings.
- Initial parity compare invocation raced candidate generation when run concurrently; reran sequentially for valid evidence capture.

## Decision Log

- Decision: treat retained WP-05/WP-06/WP-07 behavior as release contract baseline.
  Rationale: WP-08 is validation/release-readiness scope, not semantics change scope.
  Date/Author: 2026-04-13 / Codex.
- Decision: resolve WP-08 by adding bounded wrapper exposure only (no Rust algorithm changes).
  Rationale: missing wrapper surface blocked release-readiness despite existing CLI/tool registration.
  Date/Author: 2026-04-13 / Codex.

## Outcomes & Retrospective

- Implemented wrapper exposure for IFOLP in both Python wrapper files:
  - `/workdir/weppcloud-wbt/whitebox_tools.py`
  - `/workdir/weppcloud-wbt/WBT/whitebox_tools.py`
- Validated release-facing contract behavior:
  - CLI discoverability (`--listtools`) includes `IterativeFirstOrderLinkPrune`.
  - Help contract (`--toolhelp=IterativeFirstOrderLinkPrune`) includes expected flags.
  - Required argument and threshold-pair contract checks return explicit `InvalidInput` errors.
  - Wrapper signature/call probe confirms expected tool name and argument emission.
- Required gates passed:
  - `cargo check -p whitebox_tools`
  - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` (`51 passed`, `0 failed`)
  - `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py`
- Parity spot checks on retained run roots (`run1`, `run2`) with fresh `candidate_wp08` outputs produced canonical hash `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83` in both runs, byte-identical to retained `parity-report.final_effective.canonical.json`.
- Review disposition complete: no unresolved high/medium findings.
- Closure artifacts updated:
  - WBT implementation-plan WP-08 row set to `done`.
  - WP-08 `package.md`, `tracker.md`, and `review_disposition.md` updated.

## Context and Orientation

Primary execution repository:
- `/workdir/weppcloud-wbt`

Governing docs:
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`
- `/workdir/wepppy/docs/work-packages/20260413_ifolp_wp07_optimization_pass/{package.md,tracker.md,review_disposition.md}`

Baseline contract:
- Canonical retained artifact hash: `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83`.
- No retained-state parity drift allowed for WP-08 closeout.

## Plan of Work

Milestone 1: Wrapper and interface validation.
- Verify IFOLP tool registration, CLI help contract, and wrapper surface availability.
- Confirm argument contracts and expected error messaging on invalid invocation.

Milestone 2: Release-readiness gates.
- Run required build/test/wrapper sanity commands.
- Capture parity spot-check evidence on retained run roots.

Milestone 3: Review/disposition and closure.
- Produce `review_disposition.md` with findings severity/disposition.
- Close only with no unresolved high/medium findings.

## Concrete Steps

Run from `/workdir/weppcloud-wbt` unless noted.

1. Validate wrapper/CLI exposure.
   - Verify tool discoverability and help text.
   - Verify Python wrapper import/call surface as applicable.

2. Run required gates.
   - `cargo check -p whitebox_tools`
   - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture`
   - `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py`

3. Run parity spot checks vs retained baseline.
   - Use retained run roots (`/tmp/ifolp_wp05_remediate/run1`, `run2`).
   - Confirm canonical outputs match retained baseline artifacts.

4. Mandatory review/disposition.
   - Record findings in `review_disposition.md` with severity and disposition.
   - Closure gate: no unresolved high/medium findings.

5. Update closure artifacts.
   - Update `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md` WP-08 row.
   - Update WP-08 `package.md` and `tracker.md` in `wepppy`.
   - Archive this ExecPlan to `prompts/completed/`.

## Validation and Acceptance

WP-08 is accepted when all are true:
- Wrapper/CLI exposure is validated and contract-consistent.
- Required build/test/wrapper sanity gates pass.
- Parity spot checks show no retained-state drift.
- Review disposition has no unresolved high/medium findings.
- WP-08 orchestration/docs are marked closed with evidence.

## Idempotence and Recovery

- Keep WP-08 changes validation-focused and reversible.
- If wrapper readiness reveals contract mismatch, fix in bounded patch and rerun all gates.
- If parity spot check drifts, stop closure and treat as blocker.

## Artifacts and Notes

- WP-08 governance tracker:
  - `docs/work-packages/20260413_ifolp_wp08_wrapper_release_readiness/tracker.md`
- WBT orchestration table:
  - `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`

## Interfaces and Dependencies

- Preserve IFOLP semantics from retained baseline.
- Preserve wrapper/CLI external contract stability.
- Keep review/disposition mandatory for release-readiness closure.

---
Revision Note (2026-04-13 / Codex): Initial WP-08 ExecPlan authored with wrapper validation, parity spot checks, and mandatory review/disposition closure gate.
