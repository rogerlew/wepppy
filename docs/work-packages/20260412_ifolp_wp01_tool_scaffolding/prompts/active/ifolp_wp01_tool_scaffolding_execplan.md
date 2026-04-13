# Execute WP-01 Tool Scaffolding and Registration in weppcloud-wbt

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this plan is executed, `iterative_first_order_link_prune` exists as a discoverable WhiteboxTools command with a stable CLI argument contract and registration wiring in `/workdir/weppcloud-wbt`. The algorithm itself is not implemented yet, but WP-01 gives the team a concrete invocation surface, parser behavior tests, and a clean handoff into WP-02 topology implementation.

## Progress

- [x] (2026-04-13 04:31Z) ExecPlan authored and activated.
- [ ] Create tool skeleton file with metadata/parameter definitions.
- [ ] Register tool in stream-network and global registries.
- [ ] Implement `run` parser scaffolding and placeholder phase hooks.
- [ ] Add tests for required args/defaults/help contract behavior.
- [ ] Run WP-01 validation gates and update orchestration row to `done`.
- [ ] Move ExecPlan to `prompts/completed/` with outcome summary.

## Surprises & Discoveries

- Observation: WP-00 parity harness artifacts are complete and available, so WP-01 can proceed without additional fixture setup.
  Evidence: `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/` contains all required outputs.

## Decision Log

- Decision: Keep WP-01 strictly scaffolding-focused; no Phase A/B pruning behavior implementation in this package.
  Rationale: Preserve package boundaries and avoid coupling parser/wiring work with algorithmic risk.
  Date/Author: 2026-04-13 / Codex.

## Outcomes & Retrospective

Pending execution. At closure summarize:
- files added/changed,
- parser/help validation results,
- review findings and fixes,
- recommendations before WP-02.

## Context and Orientation

Primary execution repository:
- `/workdir/weppcloud-wbt`

Required governing docs:
- `/workdir/weppcloud-wbt/AGENTS.md`
- `/workdir/weppcloud-wbt/DEVELOPING_TOOLS.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`

WP-01 target files in WBT repo:
- `whitebox-tools-app/src/tools/stream_network_analysis/iterative_first_order_link_prune.rs` (new)
- `whitebox-tools-app/src/tools/stream_network_analysis/mod.rs`
- `whitebox-tools-app/src/tools/mod.rs`

WP-01 completion status target:
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md` row `WP-01`

## Plan of Work

Milestone 1 creates the command surface. Add a new tool module implementing the standard WBT `WhiteboxTool` trait shape with metadata, toolbox path, and parameter definitions that reflect the IFOLP specification contract (required/optional params and defaults).

Milestone 2 wires registration and parser behavior. Register the tool in stream-network and root tool registries, implement `run` argument parsing with explicit required-argument errors, and keep execution body as explicit placeholders for phase logic to be implemented in WP-02+.

Milestone 3 validates command contract and closes WP-01. Add parser/default/help behavior tests, run compile/test gates, perform focused code review, and mark WP-01 row as `done` with review/test fields completed.

## Concrete Steps

Run from `/workdir/weppcloud-wbt`.

1. Read governing docs.
   - `sed -n '1,220p' AGENTS.md`
   - `sed -n '1,260p' DEVELOPING_TOOLS.md`
   - `sed -n '1,260p' docs/iterative-first-order-link-prune/specification.md`
   - `sed -n '1,360p' docs/iterative-first-order-link-prune/implementation-plan.md`

2. Implement tool skeleton and registration wiring.
   - Add new tool module file under `stream_network_analysis`.
   - Register module exports in `stream_network_analysis/mod.rs`.
   - Register command in `tools/mod.rs` construction map/list.

3. Implement parser scaffolding.
   - Parse required params: `--d8_pntr`, `--upstream_area`, `--output`, `--csa`, `--mscl`.
   - Parse optional params: `--threshold_code_raster`, `--threshold_table`, `--esri_pntr`, `--epsilon`, `--fail_if_only_channel_pruned`.
   - Apply spec defaults (`epsilon=1e-5`, `fail_if_only_channel_pruned=true`).
   - Keep execution body as explicit `not implemented`/placeholder flow for phase hooks.

4. Add parser and command-contract tests.
   - Required-arg failure behavior.
   - Default-value behavior.
   - Help/usage metadata includes all parameters.

5. Validation gates.
   - `cargo check -p whitebox_tools`
   - `cargo test -p whitebox_tools iterative_first_order_link_prune`

6. Documentation/state updates.
   - Update WP-01 row in `docs/iterative-first-order-link-prune/implementation-plan.md`:
     - `Status=done`
     - `Owner=<executor>`
     - `Code Review=done`
     - `Test Gate=done`
     - fill `Started`, `Completed`, `Notes`

## Validation and Acceptance

This ExecPlan is accepted when all of the following are true:

- Tool module exists and compiles.
- Tool is registered in both required mod registries.
- CLI parser enforces required args and applies defaults per spec.
- Parser/help tests pass for WP-01 scope.
- `cargo check -p whitebox_tools` passes.
- WP-01 row in WBT implementation plan is marked `done` with gate fields complete.

## Idempotence and Recovery

- Edits are file-local and safe to rerun.
- If registration wiring fails compilation, keep tool file and fix registry imports/references incrementally.
- If parser tests fail, correct contract behavior without expanding into WP-02 algorithm work.

## Artifacts and Notes

- WP-01 governance tracker:
  - `docs/work-packages/20260412_ifolp_wp01_tool_scaffolding/tracker.md`
- WBT implementation plan for status transitions:
  - `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`

## Interfaces and Dependencies

- This package must preserve the future contract described in IFOLP specification while avoiding premature algorithm implementation.
- No WEPPpy integration changes are allowed in WP-01.
- Keep `RemoveShortStreams` untouched in this package.

---
Revision Note (2026-04-13 / Codex): Initial WP-01 ExecPlan authored for execution-agent handoff.
