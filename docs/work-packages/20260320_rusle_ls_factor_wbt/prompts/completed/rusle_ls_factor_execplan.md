# RusleLsFactor E2E Implementation

> Outcome (2026-03-20): Completed. Implemented and registered `RusleLsFactor` in `weppcloud-wbt`, added Python bindings, added WEPPpy LS integration + tests, and closed validation/documentation gates.

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `/workdir/wepppy/docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, WEPPcloud-WBT exposes a production `RusleLsFactor` tool that computes locked v1 RUSLE topographic factors (`L`, `S`, `LS`) with explicit routing/mask/cap controls and auditable metadata, and WEPPpy has a runnable integration path that executes the tool and writes run artifacts (`ls.tif`, diagnostics, `manifest.json`).

## Progress

- [x] (2026-03-20 18:20Z) Created and activated this ExecPlan; wired root `AGENTS.md` to this active plan.
- [x] Implemented `RusleLsFactor` Rust tool in `weppcloud-wbt` with CLI, outputs, metadata, and stop-mask behavior.
- [x] Registered tool in WBT module exports and tool manager dispatch.
- [x] Added Python wrappers in `whitebox_tools.py` and `WBT/whitebox_tools.py`.
- [x] Added WBT unit tests for argument parsing and output-path helpers.
- [x] Added WEPPpy integration module for LS execution and manifest writing.
- [x] Added WEPPpy tests for LS integration contract and metadata propagation.
- [x] Ran validation gates in both repos and recorded outcomes.
- [x] Moved this ExecPlan from `prompts/active/` to `prompts/completed/` at closeout.

## Surprises & Discoveries

- Observation: `wepppy/nodb/mods/rusle` initially contained only specification/docs and no executable controller code.
  Evidence: Directory listing showed only `specification.md` and references.
- Observation: `weppcloud-wbt` root `AGENTS.md` still pointed to a completed RaiseRoads plan.
  Evidence: `/workdir/weppcloud-wbt/AGENTS.md` lists `prompts/RAISE_ROADS_EXECPLAN.md` as active.
- Observation: `rustfmt`/`cargo fmt --check` in this repo can fail due preexisting trailing whitespace outside change scope.
  Evidence: formatter errors in `whitebox-tools-app/src/tools/math_stat_analysis/principal_component_analysis.rs`.

## Decision Log

- Decision: Deliver LS E2E as a first executable integration path (module + tests) rather than a full multi-factor RUSLE controller.
  Rationale: Scope was LS-specific and there is no existing production `rusle` NoDb controller to extend safely in one pass.
  Date/Author: 2026-03-20 / Codex

- Decision: Keep default science locked to spec (`Desmet-Govers L`, `McCool S`, `DInf` default, `304.8 m` cap) and surface optional controls as explicit parameters with manifest provenance.
  Rationale: Minimizes science drift and aligns with tightened specification language.
  Date/Author: 2026-03-20 / Codex

- Decision: Use targeted formatting and avoid repo-wide formatting churn for unrelated files.
  Rationale: `cargo fmt --check` is currently blocked by unrelated baseline formatting debt; scope discipline required isolated LS edits.
  Date/Author: 2026-03-20 / Codex

## Outcomes & Retrospective

- Implemented new WBT tool file: `whitebox-tools-app/src/tools/terrain_analysis/rusle_ls_factor.rs`.
- Registered command and dispatch wiring in WBT tool manager and terrain-analysis exports.
- Added Python wrappers for `rusle_ls_factor(...)` in both wrapper files.
- Added WEPPpy LS integration module + package exports:
  - `wepppy/nodb/mods/rusle/ls_integration.py`
  - `wepppy/nodb/mods/rusle/__init__.py`
- Added unit tests for WEPPpy LS integration:
  - `tests/nodb/mods/test_rusle_ls_integration.py`

Validation evidence:
- `cargo check -p whitebox_tools` passed.
- `cargo build -p whitebox_tools` passed.
- `cargo test -p whitebox_tools rusle_ls_factor -- --nocapture` passed (`6 passed`).
- `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py` passed.
- `./target/debug/whitebox_tools --listtools` includes `RusleLsFactor`.
- `wctl run-pytest tests/nodb/mods/test_rusle_ls_integration.py --maxfail=1` passed (`3 passed`).
- `wctl run-pytest tests --maxfail=1` passed (`2385 passed, 34 skipped`).
- Docs checks passed:
  - `wctl doc-lint` on updated docs
  - `diff -u <file> <(uk2us <file>)` on updated docs
- Real-run acceptance check (Claude) passed on 5 `/wc1/runs/*` DEMs after breached preprocessing, with:
  - valid LS artifact set outputs
  - `LS = L * S` max absolute error `< 2e-5`
  - effective slope-length cap enforced at `304.8 m`
  - expected fail-fast behavior on unconditioned raw DEM pits

Residual follow-up:
- Add fixture-style scientific-parity tests for LS surfaces/mask-routing scenarios in `weppcloud-wbt` as a follow-on hardening task.

## Context and Orientation

There are two repositories in scope:

1. `/workdir/weppcloud-wbt` hosts the WhiteboxTools fork where the new command was implemented.
   - Tool file: `whitebox-tools-app/src/tools/terrain_analysis/rusle_ls_factor.rs`
   - Toolbox exports: `whitebox-tools-app/src/tools/terrain_analysis/mod.rs`
   - Global registry: `whitebox-tools-app/src/tools/mod.rs`
   - Python bindings: `whitebox_tools.py` and `WBT/whitebox_tools.py`

2. `/workdir/wepppy` hosts NoDb orchestration and docs where LS execution was integrated.
   - LS spec: `wepppy/nodb/mods/rusle/specification.md`
   - LS integration module: `wepppy/nodb/mods/rusle/ls_integration.py`
   - Tests: `tests/nodb/mods/test_rusle_ls_integration.py`
   - Work package tracker: `docs/work-packages/20260320_rusle_ls_factor_wbt/tracker.md`

“E2E” in this plan means users can run `RusleLsFactor` via WBT and via WEPPpy integration code with verified output contract and metadata.

## Milestones

### Milestone 1: WBT Core Tool

Implement `RusleLsFactor` in Rust with required CLI parameters, output raster set (`ls`, `l`, `s`, `sca`, `effective_slope_length`), and metadata keys/types required by the locked spec.

Status: Complete.

### Milestone 2: WBT Registration and Bindings

Register the tool in terrain-analysis module and global tool manager; add Python wrapper methods to both binding files.

Status: Complete.

### Milestone 3: WEPPpy LS Integration

Add a focused WEPPpy LS integration module that invokes WBT and writes LS provenance into `rusle/manifest.json`.

Status: Complete.

### Milestone 4: Validation and Closeout

Run compile/tests/lint validation in both repos; update tracker and this ExecPlan sections with evidence and outcomes.

Status: Complete.

## Plan of Work

In `weppcloud-wbt`, implement a new terrain-analysis tool that accepts `dem`, optional `sca` and `slope_deg`, optional `channel_mask` and `blocking_mask`, routing mode (`dinf` default, optional `fd8`/`d8`), and `max_slope_length_m` defaulting to `304.8`. The tool computes local `S` with McCool piecewise equations, computes `m` from the locked beta expression (plus optional `m_regime` scaling), derives or consumes SCA, enforces stop-mask semantics, produces `effective_slope_length`, computes `L`, then `LS`, and emits required metadata.

In `wepppy`, add a lightweight LS integration module under `wepppy/nodb/mods/rusle` that stages inputs and calls WBT `rusle_ls_factor`, then writes/merges LS provenance into `rusle/manifest.json`.

## Concrete Steps

From `/workdir/weppcloud-wbt`:

1. Add tool source and tests.
2. Register module and tool manager entries.
3. Add Python wrappers.
4. Run:
   - `cargo check -p whitebox_tools`
   - `cargo test -p whitebox_tools`
   - `python -m py_compile whitebox_tools.py WBT/whitebox_tools.py`

From `/workdir/wepppy`:

1. Add `rusle` integration module(s) and exports.
2. Add tests under `tests/nodb/mods/`.
3. Run:
   - `wctl run-pytest tests/nodb/mods/test_rusle* --maxfail=1`
   - `wctl run-pytest tests --maxfail=1`
4. Run doc checks for updated docs/tracker/spec:
   - `wctl doc-lint --path <file>`
   - `diff -u <file> <(uk2us <file>)`

## Validation and Acceptance

Behavior acceptance is satisfied when:

- WBT CLI command `rusle_ls_factor` runs and emits all required outputs.
- Output metadata includes required keys and enum spellings from spec.
- Stop-mask and cap controls are reflected in output behavior and manifest metadata.
- WEPPpy integration function produces `rusle/ls.tif` + diagnostics + `rusle/manifest.json` on synthetic data.

## Idempotence and Recovery

All steps are additive and rerunnable. If build/test fails, fix forward and rerun the same commands. If a generated artifact under temporary test paths is stale, remove that temp directory and rerun tests; do not reset repository state with destructive git commands.

## Artifacts and Notes

- Primary implementation artifacts are code diffs in both repos plus command outputs from validation gates.
- Tracker updates capture milestone-level completion and residual follow-up risks.

## Interfaces and Dependencies

Required interfaces at completion:

- WBT command: `rusle_ls_factor` (snake-case invocation) with Python wrapper methods named `rusle_ls_factor(...)` in both wrapper files.
- Rust tool struct: `terrain_analysis::RusleLsFactor`.
- WEPPpy integration entrypoint: callable function under `wepppy/nodb/mods/rusle/` that accepts workspace paths and LS controls and writes LS outputs + manifest fields.

No new external dependency was introduced.
