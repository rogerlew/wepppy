# Execute Geneva HRU Peak Runoff and Choropleth Measure Package

## Outcome Note (2026-04-30)

- Status: Completed.
- Required implementation order executed end-to-end (Rust -> PyO3 -> WEPPpy -> query/UI/docs).
- Validation and review artifacts:
  - `artifacts/20260430_validation_summary.md`
  - `artifacts/20260430_code_review.md`
  - `artifacts/20260430_qa_review.md`
  - `artifacts/20260430_security_review.md`

You are executing the work package:

- `docs/work-packages/20260429_geneva_hru_peak_event_erosion/package.md`
- `docs/work-packages/20260429_geneva_hru_peak_event_erosion/tracker.md`
- `docs/work-packages/20260429_geneva_hru_peak_event_erosion/prompts/completed/geneva_hru_peak_event_erosion_execplan.md`

Start by reading those three files completely, then keep the ExecPlan and tracker current as living documents while you work.

## Objective

Implement HRU-local peak runoff estimates in the Rust Geneva kernel and expose the new HRU-scoped measure as `hru_peak_runoff` in the Geneva Interactive Summary HRU Choropleth Map.

The implementation must not compute HRU peak runoff by area-splitting watershed `peak_discharge`. It must derive each HRU peak from that HRU's own incremental excess series, HRU area, selected `uh_method`, selected `tc_hours`, and the existing Geneva unit-hydrograph convolution path.

## Required Implementation Order

1. Rust first in `/workdir/wepppyo3`:
   - Extend `geneva_core/src/cn.rs` run-batch HRU response fields with HRU-local peak runoff.
   - Reuse `geneva_core/src/convolution.rs::convolve_excess_to_hydrograph` and the already-built unit hydrograph.
   - Persist only scalar HRU peak summary fields, not full per-HRU hydrograph time series.
   - Add one-HRU parity and multi-HRU non-area-split tests.

2. PyO3 bridge next:
   - Update `/workdir/wepppyo3/cli_revision/src/geneva` tests so `geneva_run_batch` JSON exposes the new HRU peak field.
   - Rebuild and sync `cli_revision_rust` shared objects into WEPPpy runtime import locations.
   - Record SHA-256 hashes in a package validation artifact.

3. WEPPpy materialization:
   - Update `wepppy/nodb/mods/geneva/collaborators/hru_event_measure_service.py` to write `measure_id=hru_peak_runoff`, unit `m3_s`, from the Rust HRU peak field.
   - Keep existing `runoff_depth` and `runoff_volume` behavior unchanged.
   - Keep `peak_discharge` rejected for HRU map rows.

4. Query/report/UI:
   - Add `hru_peak_runoff` to HRU-mapable measure validation.
   - Update route/query tests for `POST /query/geneva/hru_map_rows`.
   - Add the HRU Choropleth Map measure option label `HRU peak runoff` in the Geneva Interactive Summary.
   - Do not add `hru_peak_runoff` to watershed summary chart/table measures unless the spec is explicitly updated with a separate watershed meaning.

5. Docs and package lifecycle:
   - Update `wepppy/nodb/mods/geneva/specification.md` Section 12.4 and Section 12.5 to describe implemented `hru_peak_runoff` behavior.
   - Update package tracker progress, decisions, surprises, and validation artifacts.
   - Add a dedicated security review artifact because the package is triaged `high`.

## Required Validation

Run and record results in `docs/work-packages/20260429_geneva_hru_peak_event_erosion/artifacts/<date>_validation_summary.md`.

From `/workdir/wepppyo3`:

```bash
cargo test -p geneva_core
cargo test -p cli_revision_rust geneva
cargo fmt --check
```

From `/workdir/wepppy`:

```bash
wctl run-pytest tests/nodb/mods/geneva --maxfail=1
wctl run-pytest tests/weppcloud/routes/test_geneva_bp.py tests/weppcloud/routes/test_geneva_wp08_routes.py --maxfail=1
wctl run-npm test -- geneva
wctl run-npm lint
python3 wepppy/weppcloud/controllers_js/build_controllers_js.py
wctl doc-lint --path docs/work-packages/20260429_geneva_hru_peak_event_erosion --path wepppy/nodb/mods/geneva/specification.md
python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
git diff --check
```

If a gate fails for a pre-existing unrelated reason, document the exact failure and why it is unrelated in the validation artifact. Do not hide or omit failures.

## Review Gates

Before closure, complete and document:

- code review focused on Rust response compatibility, HRU-local peak correctness, and Python materialization/query regressions;
- QA review focused on one-HRU parity, multi-HRU non-area-split behavior, legacy artifact behavior, and UI measure selection;
- security review using `docs/prompt_templates/security_review_template.md`, focused on route auth stability, query-engine dataset restrictions, and input validation.

All medium/high findings must be fixed or explicitly accepted with rationale before closing the package.

## Closure

When complete:

- move active prompts to `prompts/completed/` with outcome notes;
- update `package.md` closure notes;
- update `tracker.md` final status;
- move the package entry in `PROJECT_TRACKER.md` from Backlog/In Progress to Done as appropriate;
- summarize changed files, validation, reviewer findings, and residual risks in the final handoff.
