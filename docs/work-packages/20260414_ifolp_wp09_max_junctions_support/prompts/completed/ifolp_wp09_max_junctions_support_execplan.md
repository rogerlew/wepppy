# Execute WP-09 IFOLP Max Junctions Support (`--max_junctions`)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this plan is complete, IFOLP accepts `--max_junctions` as a first-class contract surface (CLI/help/wrappers/spec/tests), supports deterministic pruning behavior when `--max_junctions=3`, and preserves retained baseline behavior when the option is not set. WEPPpy integration planning is updated so the target cutover invocation explicitly includes `--max_junctions=3`.

## Progress

- [x] (2026-04-14 01:41 UTC) ExecPlan authored and activated.
- [x] (2026-04-14 02:18 UTC) Contract and semantics for `--max_junctions` finalized in IFOLP spec and parser contract (non-negative integer, omitted-path retention).
- [x] (2026-04-14 02:18 UTC) IFOLP implementation updated (Rust tool + wrappers + help/spec docs).
- [x] (2026-04-14 02:37 UTC) Max-junction tests added and passing (`77 passed`, `0 failed`).
- [x] (2026-04-14 02:56 UTC) Parity/regression campaign executed and dispositioned against retained baseline (`920cc161...` stable).
- [x] (2026-04-14 02:59 UTC) WEPPpy integration planning docs updated to require explicit `max_junctions=3`.
- [x] (2026-04-14 03:00 UTC) Mandatory review completed with no unresolved high/medium findings.
- [x] (2026-04-14 03:02 UTC) WP-09 docs/tracker updated; ExecPlan ready for archive to `prompts/completed/`.

## Surprises & Discoveries

- Initial parity evidence run was executed with a stale runtime binary; rebuilt runtime executable with `cargo build -p whitebox_tools` and reran parity.
- Fresh-runtime parity probes revealed pointer-`0` traversal failures on retained fixtures; resolved by keeping zero-pointer cells in output domain while excluding them from provisional stream qualification/traversal candidates.

## Decision Log

- Decision: Preserve retained IFOLP behavior when `--max_junctions` is omitted.
  Rationale: Avoid unintentional baseline drift for current consumers while adding explicit max-junction control.
  Date/Author: 2026-04-14 / Codex.

- Decision: WEPPpy integration planning target uses `--max_junctions=3`.
  Rationale: User requirement for rollout contract.
  Date/Author: 2026-04-14 / Codex.

- Decision: Require explicit runtime binary build before parity campaign evidence capture.
  Rationale: `cargo check`/`cargo test` do not guarantee `target/debug/whitebox_tools` refresh for runtime parity execution.
  Date/Author: 2026-04-14 / Codex.

- Decision: Keep pointer-`0` cells in valid output footprint but exclude them from stream traversal candidates.
  Rationale: Preserve output-domain contract while restoring retained parity campaign executability.
  Date/Author: 2026-04-14 / Codex.

## Outcomes & Retrospective

- Implemented IFOLP `--max_junctions` support across Rust parser/metadata/phase logic and both wrapper surfaces.
- Added deterministic phase regression for `--max_junctions=3` and parser/help contract tests for new flag behavior.
- Required gates passed:
  - `cargo check -p whitebox_tools`
  - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture` (`77 passed`, `0 failed`)
  - `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py`
- Parity/regression evidence:
  - omitted `--max_junctions` canonical hashes (run1/run2) matched retained baseline `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83`
  - explicit `--max_junctions=3` canonical hashes were deterministic across run1/run2 and matched retained hash for current fixtures.
- Review disposition closure: no unresolved high/medium findings.

## Context and Orientation

Primary implementation repo:
- `/workdir/weppcloud-wbt`

Primary governance repo:
- `/workdir/wepppy`

Key IFOLP code/docs in WBT:
- `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune.rs`
- `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_a.rs`
- `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune_phase_b.rs`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wepppy-integration-plan.md`
- `/workdir/weppcloud-wbt/whitebox_tools.py`
- `/workdir/weppcloud-wbt/WBT/whitebox_tools.py`

WP-09 governance artifacts:
- `docs/work-packages/20260414_ifolp_wp09_max_junctions_support/package.md`
- `docs/work-packages/20260414_ifolp_wp09_max_junctions_support/tracker.md`
- `docs/work-packages/20260414_ifolp_wp09_max_junctions_support/prompts/completed/ifolp_wp09_max_junctions_support_execplan.md`

Retained baseline identity contract:
- `920cc1612bd677a1f8dab935a521f6270e226bf961fd5f72ca770b32cd134c83`

## Plan of Work

Milestone 1 establishes the contract. Confirm intended `--max_junctions` semantics from TopAZ behavior and existing IFOLP spec language, then codify how omitted value behaves (baseline-preserving), valid ranges, and error handling.

Milestone 2 implements the argument surface and pruning logic changes in bounded IFOLP modules, including wrapper parity and help text.

Milestone 3 adds/updates tests for parser, phase-level behavior, deterministic ordering, and edge cases (`--max_junctions` omitted, `--max_junctions=1`, `--max_junctions=3`, invalid values).

Milestone 4 runs parity/regression campaigns against retained baseline and captures mismatch disposition for fixtures impacted by the new option.

Milestone 5 updates planning docs so WEPPpy cutover contract explicitly calls IFOLP with `--max_junctions=3`, completes mandatory review/disposition, and closes package artifacts.

## Concrete Steps

Run implementation and validation in `/workdir/weppcloud-wbt` unless noted.

1. Contract and spec alignment.
   - Inspect TopAZ-equivalent behavior and current IFOLP spec for junction handling.
   - Update spec sections for argument contract, deterministic behavior, and error paths.

2. Implement argument and behavior.
   - Add parser support for `--max_junctions` (non-negative integer contract; fail on malformed/invalid values).
   - Thread `max_junctions` into phase logic where junction pruning decisions are made.
   - Preserve existing behavior when argument is absent.
   - Expose in `whitebox_tools.py` and `WBT/whitebox_tools.py` with matching signatures/docstrings.

3. Add tests.
   - Parser tests for valid/invalid `--max_junctions` values and omission behavior.
   - Phase-level and/or integration tests for deterministic pruning with capped junctions.
   - Wrapper smoke assertions for emitted args and paired behavior consistency.

4. Run required gates.
   - `cargo check -p whitebox_tools`
   - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture`
   - `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py`

5. Run parity/regression evidence.
   - Reuse retained fixtures under `/tmp/ifolp_wp05_remediate/run1` and `run2`.
   - Capture canonical report hashes for:
     - no `--max_junctions` (must preserve retained baseline unless explicitly re-baselined)
     - `--max_junctions=3` candidate behavior.
   - Record mismatch disposition and rationale.

6. Update planning docs and package closure artifacts.
   - Update `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wepppy-integration-plan.md` to specify `--max_junctions=3` in WEPPpy target invocation.
   - Update `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md` with WP-09 row/status/notes.
   - Update WP-09 `tracker.md` and package deliverables.
   - Move this ExecPlan to `prompts/completed/` with outcomes summary.

## Validation and Acceptance

WP-09 is accepted when all are true:
- IFOLP CLI/help and both Python wrappers support `--max_junctions` with consistent contract.
- Omitted `--max_junctions` path maintains retained baseline behavior (or any drift is explicitly approved/re-baselined).
- `--max_junctions=3` behavior is deterministic and covered by tests.
- Required build/test/wrapper gates pass.
- Parity/regression evidence and mismatch disposition are documented.
- WEPPpy integration planning explicitly requires `--max_junctions=3`.
- No unresolved high/medium findings remain after mandatory review.

## Idempotence and Recovery

- Keep changes additive and narrowly scoped to IFOLP argument/logic/docs/tests.
- If parity baseline drifts unexpectedly in omitted-arg path, stop closure and treat as blocker.
- If `--max_junctions` behavior is ambiguous, resolve in spec first, then implement.

## Artifacts and Notes

- Expected evidence artifacts include canonical parity report hashes, review disposition notes, and tracker timeline updates.

## Interfaces and Dependencies

- Preserve IFOLP external contracts unless explicitly changed and documented.
- Keep wrapper interfaces symmetric between `whitebox_tools.py` and `WBT/whitebox_tools.py`.
- Treat retained baseline hash `920cc161...` as authoritative for no-arg path.

---
Revision Note (2026-04-14 / Codex): Initial WP-09 ExecPlan authored for `--max_junctions` implementation, parity/regression, and WEPPpy planning integration with `--max_junctions=3`.
