# RUSLE Static R and Hyetograph API Migration (Breakpoint Parity)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This package delivers production static-`R` (`cligen_static`) and shared hyetograph/intensity helpers in `wepppyo3.climate`, then migrates WEPPpy callsites away from duplicated Python routines. After completion, WEPPpy climate exports and reporting paths use one canonical implementation for non-breakpoint and breakpoint storms, with parity anchored to WEPP Fortran behavior.

User-visible outcome: breakpoint climates produce real intensity windows (not sentinel placeholders), static `R` values are available through a stable public API, and downstream consumers read consistent storm-shape-derived metrics.

## Progress

- [x] (2026-03-20 03:40Z) Scoped package goals, references, and current WEPPpy callsites.
- [x] (2026-03-20 03:45Z) Reviewed WEPP internals in `/workdir/wepp-forest` (`stmget.for`, `brkpt.for`, `disag.for`) and recorded parity direction.
- [x] (2026-03-20 03:50Z) Authored package brief and this active ExecPlan.
- [x] (2026-03-20 04:35Z) Resolved fallback-policy decision (legacy-only temporary fallbacks; no new Python-only fallback paths) and release-tree scope decision (`py312` only).
- [x] (2026-03-20 05:20Z) Resolved remaining Milestone-0 contract decisions: static-`R` energy/units equation, hyetograph API surface, and breakpoint backward-compatibility policy.
- [x] (2026-03-21 06:20Z) Milestone 1 complete: implemented Rust hyetograph primitives (non-breakpoint + breakpoint) with tests.
- [x] (2026-03-21 06:35Z) Milestone 2 complete: implemented static `R` API and tests in `wepppyo3.climate`.
- [x] (2026-03-21 07:00Z) Milestone 3 complete: migrated WEPPpy callsites and removed in-scope sentinel breakpoint behavior.
- [x] (2026-03-21 07:15Z) Milestone 4 complete: dedicated correctness review pass captured in `artifacts/milestone4_review.md` with no unresolved high/medium findings.
- [x] (2026-03-21 07:20Z) Milestone 5 complete: dedicated QA-review pass captured in `artifacts/milestone5_qa_review.md` with no unresolved high/medium findings in changed scope.
- [x] (2026-03-21 07:30Z) Milestone 6 complete: final validation + docs synchronization + ExecPlan archival.

## Surprises & Discoveries

- Observation: Existing breakpoint artifact export path currently writes placeholder/sentinel intensity values despite deriving peak intensities for non-breakpoint rows.
  Evidence: `wepppy/climates/cligen/cligen.py` sets breakpoint intensity fields to `-1` during dataframe materialization.

- Observation: WEPP breakpoint handling derives intensity from differences in cumulative depth and cumulative time across breakpoints.
  Evidence: `/workdir/wepp-forest/src/brkpt.for` computes interval intensity from `r(i)-r(i-1)` over `t(i)-t(i-1)` and sums duration from intervals.

- Observation: Current Python helper routines are used by multiple downstream paths beyond one report/export route.
  Evidence: callsites in `wepppy/nodb/core/climate_artifact_export_service.py`, `wepppy/wepp/interchange/_utils.py`, and `wepppy/wepp/reports/return_periods.py`.

## Decision Log

- Decision: Keep this package bounded to static `R` + hyetograph helper migration and exclude broader RUSLE factor/controller buildout.
  Rationale: Scope discipline for a high-risk cross-repo API migration.
  Date/Author: 2026-03-20 / Codex.

- Decision: Treat review pass and QA-review pass as explicit milestones, not implicit closeout checks.
  Rationale: User requested both passes; explicit milestones prevent accidental omission.
  Date/Author: 2026-03-20 / Codex.

- Decision: Use WEPP Fortran behavior as parity oracle for breakpoint intensity semantics.
  Rationale: WEPP runtime behavior is authoritative for interpretation of breakpoint storm tables.
  Date/Author: 2026-03-20 / Codex.

- Decision: Permit temporary migration fallback only where legacy Python behavior already exists; do not add new Python-only fallback paths.
  Rationale: Preserves migration safety without extending long-term dual-implementation debt.
  Date/Author: 2026-03-20 / User + Codex.

- Decision: Restrict phase-1 cross-repo release synchronization to canonical WEPPpy runtime artifacts under `/workdir/wepppyo3/release/linux/py312/`.
  Rationale: Keeps package scope bounded to production runtime needs for WEPPpy.
  Date/Author: 2026-03-20 / User + Codex.

- Decision: Static-`R` v1 uses WEPP/AH537-aligned SI energy relation with cap:
  `e(i_mm_hr) = min(0.119 + 0.0873*log10(i_mm_hr), 0.283)`, `e = 0` for `i <= 0`.
  Rationale: Aligns static `R` with WEPP storm-shape energy behavior for this stack.
  Date/Author: 2026-03-20 / User-delegated review + Codex.

- Decision: Public hyetograph API is dual-layer (segment builders + peak-intensity helpers) with peak helpers as canonical WEPPpy callsite surface.
  Rationale: Matches current WEPPpy usage while preserving reusable low-level primitives for static `R` and parity tests.
  Date/Author: 2026-03-20 / User-delegated review + Codex.

- Decision: Breakpoint artifact compatibility contract is fixed to real `peak_intensity_*`, nullable `tp/ip`, and derived breakpoint duration semantics.
  Rationale: Removes sentinel placeholder behavior and stabilizes exported schema without synthesizing non-canonical breakpoint inputs.
  Date/Author: 2026-03-20 / User-delegated review + Codex.

## Outcomes & Retrospective

Delivered outcomes:

- Implemented new `wepppyo3.climate` API surface:
  - `build_hyetograph_non_breakpoint`
  - `build_hyetograph_breakpoint`
  - `compute_peak_intensities_from_hyetograph`
  - `compute_peak_intensities_non_breakpoint`
  - `compute_peak_intensities_breakpoint`
  - `compute_static_r_from_cli`
- Added Rust unit coverage for non-breakpoint peaks, breakpoint interval semantics, and static-`R` annual totals.
- Migrated WEPPpy callsites to canonical API outputs and removed breakpoint sentinel intensity behavior in exported artifacts.
- Added regression tests for breakpoint dataframe/parquet contracts and canonical `peak_intensity_60` materialization.
- Completed dedicated correctness and QA-review artifact passes:
  - `artifacts/milestone4_review.md`
  - `artifacts/milestone5_qa_review.md`
- Final validation summary captured in `artifacts/final_validation_summary.md`.

Validation retrospective:

- Targeted migration tests and changed-file quality gates passed.
- Full-suite sanity gate (`wctl run-pytest tests --maxfail=1`) passed after final test hardening updates.
- Package closeout completed with all planned validation gates passing.

## Context and Orientation

Repositories and key files in scope:

- `wepppy/nodb/mods/rusle/specification.md` (locked `R` requirements, open contract questions)
- `wepppy/climates/cligen/cligen.py` (current Python hyetograph and peak-intensity logic)
- `wepppy/nodb/core/climate_artifact_export_service.py` (artifact export consumer)
- `wepppy/wepp/interchange/_utils.py` (CLI parquet fallback consumer)
- `wepppy/wepp/reports/return_periods.py` (report fallback consumer)
- `/home/workdir/wepppyo3/cli_revision/src/lib.rs` (Rust climate API implementation target)
- `/workdir/wepppyo3/release/linux/py312/wepppyo3/climate/__init__.py` (canonical release path used by WEPPpy)
- `/workdir/wepp-forest/src/stmget.for`, `/workdir/wepp-forest/src/brkpt.for`, `/workdir/wepp-forest/src/disag.for` (parity references)

The migration goal is to centralize storm-shape and erosivity logic in `wepppyo3`, then update WEPPpy users to consume that API directly.

## Plan of Work

Milestone 0 is complete. Decision-checkpoint contracts are now locked in `package.md`, `tracker.md`, and `wepppy/nodb/mods/rusle/specification.md` for:

- static-`R` equation/units
- public hyetograph API shape
- fallback/release policies
- breakpoint artifact backward-compatibility

No further Milestone-0 decisions are blocking implementation.

Milestone 1 implements shared Rust hyetograph primitives that reconstruct segment arrays for non-breakpoint storms (`prcp/dur/tp/ip`) and breakpoint storms (`nbrkpt` + cumulative table). Add tests for shape reconstruction and interval/intensity semantics, including edge cases for degenerate durations and minimum timestep handling where relevant.

Milestone 2 adds static `R` computation API(s) in `wepppyo3.climate`, consuming segment outputs and calculating event energy, event `I30`, event `EI30`, annual erosivity totals, and mean annual `R`. Tests must validate formula implementation, units, and aggregation behavior across synthetic and fixture climates.

Milestone 3 migrates WEPPpy callsites to the new `wepppyo3` APIs. Remove or demote in-scope Python helper logic that duplicates migrated behavior. Ensure breakpoint exports populate real intensity windows and that report/interchange paths continue to produce expected outputs.

Milestone 4 is a dedicated correctness review pass. Run a reviewer-style audit against changed files, capture findings artifact(s), and resolve all high/medium issues before moving on.

Milestone 5 is a dedicated QA-review pass focused on tests, fixture hygiene, and regression coverage. Resolve all high/medium findings and update tests/docs accordingly.

Milestone 6 runs final validation gates, syncs `package.md`/`tracker.md`/ExecPlan progress, updates project tracking artifacts, and archives this plan to `prompts/completed/` with outcome notes.

## Concrete Steps

Run commands from `/workdir/wepppy` unless noted otherwise.

1. Decision checkpoint docs updates.

    wctl doc-lint --path docs/work-packages/20260320_rusle_r_static_hyetograph_api

2. Implement and test `wepppyo3` climate APIs from `/home/workdir/wepppyo3`.

    cargo test -p cli_revision
    maturin develop --release

3. Sync release artifacts as required by selected release policy.

    rsync -a /home/workdir/wepppyo3/target/wheels_or_site_packages/... /workdir/wepppyo3/release/linux/py312/

4. Migrate WEPPpy callsites and run targeted tests.

    wctl run-pytest tests/climates --maxfail=1
    wctl run-pytest tests/nodb/core/test_climate_artifact_export_service.py --maxfail=1
    wctl run-pytest tests/wepp/reports/test_return_periods.py --maxfail=1

5. Run quality and full sanity gates.

    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    wctl run-pytest tests --maxfail=1

6. Lint package docs before handoff/closeout.

    wctl doc-lint --path PROJECT_TRACKER.md
    wctl doc-lint --path docs/work-packages/20260320_rusle_r_static_hyetograph_api

## Validation and Acceptance

The work is accepted when all of the following are true:

- `wepppyo3.climate` exposes documented, tested APIs for hyetograph segments and static `R` outputs.
- Non-breakpoint and breakpoint test fixtures show expected intensity-window behavior, with parity checks grounded in WEPP semantics.
- WEPPpy callsites in scope consume the new API and produce equivalent or contract-improved outputs.
- Breakpoint intensity fields in exported climate artifacts are no longer sentinel placeholders.
- Dedicated review and QA-review milestones are completed with all high/medium findings resolved.
- Full WEPPpy suite passes, and package/tracker/plan artifacts are synchronized and archived.

## Idempotence and Recovery

- Implement migrations in small, additive commits by callsite so failed steps can be retried without broad rollback.
- Keep temporary compatibility shims only when explicitly justified by an approved backward-compatibility decision.
- If parity tests reveal mismatch, stop forward migration and correct shared `wepppyo3` semantics first before continuing callsite updates.

## Artifacts and Notes

Record milestone artifacts under `docs/work-packages/20260320_rusle_r_static_hyetograph_api/artifacts/`:

- `milestone4_review.md` (correctness review pass)
- `milestone5_qa_review.md` (QA-review pass)
- `final_validation_summary.md`
- optional parity notes (`breakpoint_parity_notes.md`) with WEPP references and sample calculations

## Interfaces and Dependencies

Target interface shape to finalize in Milestone 0 (names may be adjusted by decision log, but contracts must be explicit):

- `wepppyo3.climate.compute_hyetograph_segments(...) -> segments`
- `wepppyo3.climate.compute_peak_intensities(segments, windows=[5,10,15,30,60]) -> dict`
- `wepppyo3.climate.compute_static_r_from_cli(...) -> {mean_annual_r, annual_ei30, event_metrics?}`

Dependencies:

- No new external libraries expected.
- Keep WEPPpy runtime contract aligned with `/workdir/wepppyo3/release/linux/py312/` packaging expectations.

---
Revision Note (2026-03-20, Codex): Initial active ExecPlan created for static `R` + hyetograph API implementation/migration with explicit review and QA-review milestones.
Revision Note (2026-03-20, Codex): Milestone-0 decision checkpoint closed (Q1-Q5) using user directives and delegated literature/code reviews; implementation milestones now unblocked.
Revision Note (2026-03-21, Codex): Milestones 1-6 completed, artifacts recorded, and plan archived to `prompts/completed/` with full validation gates passing.
