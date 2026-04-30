# Geneva HRU Peak Runoff and Choropleth Measure Implementation

## Outcome Note (2026-04-30)

- Status: Completed.
- Final runtime behavior: HRU-local `peak_runoff_m3_s` is produced in Rust run-batch output, materialized as `measure_id=hru_peak_runoff` (`unit=m3_s`), queryable via HRU map rows, and selectable in Geneva Interactive Summary HRU map controls.
- Full validation and review evidence is recorded in package artifacts under `docs/work-packages/20260429_geneva_hru_peak_event_erosion/artifacts/`.

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`. It is self-contained so a new contributor can continue from this file plus the current working tree.

## Purpose / Big Picture

After this work, a Geneva run that has completed `run_batch` will provide an HRU-local peak runoff estimate for every completed storm and HRU. Users viewing the Geneva Interactive Summary will be able to select `HRU peak runoff` in the HRU Choropleth Map and see where each storm's local HRU peak runoff is highest.

This matters because future event-erosion estimates need `qpeak_m3_s` per HRU, and area-splitting the watershed peak discharge is not scientifically acceptable. The observable result is a new HRU map measure named `hru_peak_runoff`, unit `m3_s`, computed from each HRU's own excess series and area using the same Geneva unit-hydrograph method selected for the storm.

## Progress

- [x] (2026-04-30 06:04 UTC) Created this implementation-ready ExecPlan while preparing the work package.
- [x] (2026-04-30 06:21 UTC) Inspected current Rust `geneva_core` run-batch response structs and PyO3 JSON serialization before editing.
- [x] (2026-04-30 06:26 UTC) Added Rust HRU-local peak summaries and Rust tests.
- [x] (2026-04-30 06:28 UTC) Updated PyO3 Geneva bridge tests and rebuilt/synced runtime bindings.
- [x] (2026-04-30 06:31 UTC) Materialized `hru_peak_runoff` in WEPPpy HRU event-measure rows.
- [x] (2026-04-30 06:31 UTC) Added WEPPpy query validation and route/report tests.
- [x] (2026-04-30 06:31 UTC) Added Geneva Interactive Summary HRU Choropleth Map measure option and JS tests.
- [x] (2026-04-30 06:34 UTC) Updated Geneva specification and package artifacts.
- [x] (2026-04-30 06:34 UTC) Ran required validation and review gates.
- [x] (2026-04-30 06:34 UTC) Prepared this ExecPlan for move to `prompts/completed/` with closure notes.

## Surprises & Discoveries

- Observation: The initial package-scoping pass found that `/workdir/wepppyo3/geneva_core/src/convolution.rs` already exposes `convolve_excess_to_hydrograph`, which returns `summary_metrics.peak_discharge` and `summary_metrics.time_to_peak`.
  Evidence: `rg -n "convolve_excess_to_hydrograph|peak_discharge" /workdir/wepppyo3/geneva_core/src`.

- Observation: The initial package-scoping pass found that WEPPpy already materializes HRU rows for `runoff_depth` and `runoff_volume` in `wepppy/nodb/mods/geneva/collaborators/hru_event_measure_service.py`.
  Evidence: `GenevaHruEventMeasureService.materialize_from_batch` appends two measure rows from each completed storm's `hru_excess` rows.

- Observation: Geneva summary UI currently hard-codes HRU map measure options in controller/template (`runoff_depth`, `runoff_volume`) independent of watershed summary `filter_options.measures`.
  Evidence: `wepppy/weppcloud/controllers_js/geneva_summary_report.js` `MAP_MEASURE_IDS` and `wepppy/weppcloud/templates/reports/geneva/summary.htm` map measure `<select>` options.

- Observation: One-HRU parity and multi-HRU non-area-split behavior can be proven entirely in Rust without Python scaffolding by asserting against `RunBatchResponse` fields.
  Evidence: Added tests in `/workdir/wepppyo3/geneva_core/src/cn.rs`:
  `one_hru_peak_runoff_matches_watershed_peak_discharge` and `multi_hru_local_peaks_are_not_area_split_watershed_peak`.

## Decision Log

- Decision: Use `hru_peak_runoff` as the new HRU map measure ID.
  Rationale: `peak_discharge` is already watershed-scoped and intentionally unsupported for HRU map queries. A distinct ID prevents silent scope drift.
  Date/Author: 2026-04-30 / Codex

- Decision: Compute HRU peak runoff by applying Geneva unit-hydrograph convolution to each HRU's own incremental excess series and area.
  Rationale: This preserves Geneva runtime assumptions and avoids the scientifically weak shortcut of multiplying watershed peak discharge by HRU area fraction.
  Date/Author: 2026-04-30 / Codex

- Decision: Persist only scalar HRU peak summaries in v1, not full HRU hydrograph time series.
  Rationale: The immediate user-visible need is a choropleth measure and future MUSLE input. Full per-HRU hydrographs would increase artifact size and UI complexity without being required for this package.
  Date/Author: 2026-04-30 / Codex

- Decision: Defer full MUSLE erosion rows to a follow-on package.
  Rationale: Full event erosion requires RUSLE factor aggregation, source-hash invalidation, unavailable diagnostics, and additional UI semantics. This package should produce the missing peak-runoff substrate first.
  Date/Author: 2026-04-30 / Codex

- Decision: Treat missing `hru_excess[].peak_runoff_m3_s` as a contract violation during materialization.
  Rationale: This package requires kernel-derived HRU-local peak runoff. Silently falling back (for example to area-split watershed peak) would violate the scientific and API contract.
  Date/Author: 2026-04-30 / Codex

## Outcomes & Retrospective

Completed.

- Rust kernel now emits per-HRU `peak_runoff_m3_s` and `time_to_peak_minutes` using per-HRU convolution with the selected unit hydrograph and HRU area.
- One-HRU parity and multi-HRU non-area-split regressions are in `geneva_core` and passing.
- PyO3 bridge tests confirm `geneva_run_batch` JSON includes the new HRU peak field.
- WEPPpy materializes `measure_id=hru_peak_runoff` (`unit=m3_s`) while keeping watershed summary measures unchanged.
- HRU map validation/query paths accept `hru_peak_runoff` and still reject `peak_discharge` at HRU scope.
- Geneva Interactive Summary HRU map selector now exposes `HRU peak runoff` and requests `measure_id=hru_peak_runoff`.
- Validation gates passed except known unrelated frontend lint baseline (`landuse_map_inline.test.js`), documented in package validation artifact.

## Context and Orientation

Geneva is a WEPPpy NoDb module under `wepppy/nodb/mods/geneva/`. It prepares hydrologic response units, called HRUs, then runs event rainfall through a Curve Number excess calculation and a unit hydrograph. A unit hydrograph is a simple routing shape that turns rainfall excess over an area into a runoff hydrograph, which is a time series of discharge.

The Rust implementation lives in `/workdir/wepppyo3/geneva_core`. WEPPpy calls it through the PyO3 bridge in `/workdir/wepppyo3/cli_revision/src/geneva`. The runtime Python service that calls the kernel is `wepppy/nodb/mods/geneva/collaborators/batch_run_service.py`.

Current behavior before this package:

- Rust `run_batch_cn_excess` computes per-HRU excess series and one watershed-composite hydrograph.
- WEPPpy persists per-HRU `runoff_depth` and `runoff_volume` in `geneva/hru_event_measure_rows.parquet`.
- The Geneva Interactive Summary HRU map can show `runoff_depth` and `runoff_volume`.
- `peak_discharge` is available in watershed summary charts/tables but is intentionally rejected for HRU map rows.

Target behavior after this package:

- Rust `run_batch_cn_excess` also returns HRU-local peak runoff for each HRU.
- WEPPpy persists `hru_peak_runoff` rows in `geneva/hru_event_measure_rows.parquet` with unit `m3_s`.
- The HRU map row query accepts `measure_id=hru_peak_runoff`.
- The Geneva Interactive Summary HRU Choropleth Map exposes a user-facing measure label `HRU peak runoff`.
- `peak_discharge` remains watershed-only and remains rejected for HRU map rows.

The important scientific constraint is that HRU peak runoff must be local to the HRU. Do not compute it by multiplying watershed peak discharge by HRU area fraction. The implementation must include a regression that would fail if someone used area apportionment.

## Plan of Work

Start in Rust. In `/workdir/wepppyo3/geneva_core/src/cn.rs`, inspect the response structs around `HruExcessSeries` and `RunBatchResponse`. Add fields to each HRU excess row for local peak runoff, likely `peak_runoff_m3_s` and `time_to_peak_minutes`, or add a nested summary object if that is more idiomatic for current serialization. Keep the field names stable for Python consumption.

Use the existing `build_unit_hydrograph` result already created in `run_batch_cn_excess`, and call `convolve_excess_to_hydrograph` for each HRU using that HRU's `incremental_excess_mm` and `area_m2`. Extract only scalar summary values from the result. Do not store full HRU hydrograph arrays in the response. For zero-runoff HRUs, return `peak_runoff_m3_s = 0.0` and a null or zero time-to-peak value according to the current JSON conventions; record the chosen behavior in the Decision Log.

Add Rust tests in `cn.rs` or a focused test module. One test must build a one-HRU request and assert the HRU peak equals the watershed `summary_metrics.peak_discharge` within tolerance. Another test must build a multi-HRU request where HRUs have different CN or excess response, then assert the HRU peak values are not the same as naive area fractions of the watershed peak. The exact fixture can reuse existing test helpers in `cn.rs`.

Update the PyO3 bridge tests in `/workdir/wepppyo3/cli_revision/src/geneva/mod.rs` so `geneva_run_batch` JSON includes the new HRU peak fields. Build the Rust package and sync the shared objects into WEPPpy as existing Geneva kernel packages do. Record the copied binary hashes in a validation artifact.

Move to WEPPpy. In `wepppy/nodb/mods/geneva/collaborators/hru_event_measure_service.py`, add `hru_peak_runoff` to the materialized measure IDs. Read `peak_runoff_m3_s` from each `hru_excess` row. Append a row with `measure_id = "hru_peak_runoff"`, `value = peak_runoff_m3_s`, and `unit = "m3_s"`. Keep existing columns unchanged because the row format is already generic: `measure_id`, `value`, and `unit`.

Update measure validation. The existing helper `validate_hru_map_measure_id` is imported by `hru_event_measure_service.py`; inspect `wepppy/nodb/mods/geneva/schemas/query_schema.py` and add `hru_peak_runoff` to the HRU-mapable set. Do not add `peak_discharge` to the HRU-mapable set. Existing tests should continue to prove `peak_discharge` fails with `unsupported_measure_scope` for HRU map rows.

Update query/report payloads. Inspect `wepppy/nodb/mods/geneva/collaborators/report_payload_service.py` for `filter_options.measures` and HRU-map measure metadata. If the HRU map measure list is separate from watershed summary measures, add `hru_peak_runoff` there only. If no separate list exists, add an explicit field such as `hru_map_measures` or extend the existing map-control payload in the least invasive way used by current JavaScript.

Update the Geneva Interactive Summary UI. Inspect `wepppy/weppcloud/templates/reports/geneva/summary.htm` and `wepppy/weppcloud/controllers_js/geneva_summary_report.js`. Add `HRU peak runoff` to the HRU Choropleth Map measure selector. The selector should request `measure_id=hru_peak_runoff` from `POST /query/geneva/hru_map_rows`. The watershed summary chart/table measure selector should remain unchanged unless the current UI uses a shared measure source; if shared, split the HRU map options to avoid offering `hru_peak_runoff` as a watershed chart metric.

Update docs. In `wepppy/nodb/mods/geneva/specification.md`, update Section 12.4 to include `hru_peak_runoff` as an HRU choropleth measure and update Section 12.5 to state the HRU peak substrate is implemented. Also update the artifact catalog note if needed. Keep the wording clear that this package does not implement erosion mass/yield.

## Concrete Steps

Work in two repos: `/workdir/wepppyo3` for Rust and `/workdir/wepppy` for Python/UI/docs.

First inspect the current code:

    cd /workdir/wepppyo3
    rg -n "struct HruExcessSeries|struct RunBatchResponse|run_batch_cn_excess|convolve_excess_to_hydrograph" geneva_core/src cli_revision/src/geneva

    cd /workdir/wepppy
    rg -n "hru_event_measure|validate_hru_map_measure_id|hru_map_rows|runoff_depth|runoff_volume|peak_discharge|geneva_summary" wepppy/nodb/mods/geneva wepppy/weppcloud tests/nodb/mods/geneva tests/weppcloud

Implement and test Rust first:

    cd /workdir/wepppyo3
    cargo test -p geneva_core
    cargo test -p cli_revision_rust geneva

If the package name or test selector differs, inspect `Cargo.toml` and use the closest focused test command. Run `cargo fmt` after Rust edits.

Rebuild and sync the PyO3 shared object after Rust bridge changes. Use the existing release target and copy pattern from recent Geneva package artifacts:

    cd /workdir/wepppyo3
    cargo build -p cli_revision_rust --release
    cp /workdir/wepppyo3/target/release/libcli_revision_rust.so /workdir/wepppyo3/release/linux/py312/wepppyo3/climate/cli_revision_rust.so
    cp /workdir/wepppyo3/target/release/libcli_revision_rust.so /workdir/wepppy/cli_revision_rust/cli_revision_rust.abi3.so
    sha256sum /workdir/wepppyo3/release/linux/py312/wepppyo3/climate/cli_revision_rust.so /workdir/wepppy/cli_revision_rust/cli_revision_rust.abi3.so

Then implement WEPPpy materialization and query support:

    cd /workdir/wepppy
    wctl run-pytest tests/nodb/mods/geneva --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_geneva_bp.py tests/weppcloud/routes/test_geneva_wp08_routes.py --maxfail=1

Then implement UI tests and rebuild controllers:

    cd /workdir/wepppy
    wctl run-npm test -- geneva
    wctl run-npm lint
    python3 wepppy/weppcloud/controllers_js/build_controllers_js.py

Finally update docs and package artifacts:

    cd /workdir/wepppy
    wctl doc-lint --path docs/work-packages/20260429_geneva_hru_peak_event_erosion --path wepppy/nodb/mods/geneva/specification.md
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    git diff --check

## Validation and Acceptance

Acceptance is behavioral. A completed Geneva batch should produce an HRU event-measure artifact with rows like these, one per storm and HRU:

    measure_id = hru_peak_runoff
    unit = m3_s
    value = <finite non-negative local HRU peak runoff>

A query against the existing HRU map rows endpoint should work:

    POST /runs/<runid>/<config>/query/geneva/hru_map_rows
    {"storm_id":"<completed storm id>","measure_id":"hru_peak_runoff"}

Expected response behavior:

- `availability.status` is `available` for modern completed runs with the artifact.
- `records` contains one row per mapped HRU with `measure_id=hru_peak_runoff`.
- `row_count` matches the number of returned HRU records.
- `measure_id=peak_discharge` still fails validation for HRU map rows.

UI acceptance:

- Open the Geneva Interactive Summary for a run with completed Geneva batch output.
- The HRU Choropleth Map measure selector includes `HRU peak runoff`.
- Selecting it fetches `measure_id=hru_peak_runoff` and colors HRU geometries using returned values.
- The watershed summary chart/table measure selector remains limited to existing watershed measures unless explicitly changed by spec.

Test acceptance:

- Rust one-HRU test passes and proves local HRU peak equals watershed peak.
- Rust or Python multi-HRU test passes and proves local HRU peak is not naive watershed peak area apportionment.
- Existing `runoff_depth` and `runoff_volume` HRU map tests still pass.
- Route tests for legacy missing artifact behavior still pass.
- JavaScript test proves the new measure option exists and sends the correct query value.

## Idempotence and Recovery

All code changes should be additive. Re-running `run_batch` should overwrite `geneva/hru_event_measure_rows.parquet` with the same deterministic row set for the same inputs. Existing completed runs that lack `hru_peak_runoff` rows must not crash report/query routes.

If Rust/PyO3 changes are made but WEPPpy cannot import the new field, rebuild and re-copy the shared object using the commands in `Concrete Steps`. If copied shared objects break imports, restore the previous shared objects from version control or rebuild from the last known good commit, then rerun the import smoke test.

Do not delete or rewrite existing user run artifacts outside the active run under test. Do not remove existing measure IDs or columns from `hru_event_measure_rows.parquet`.

## Artifacts and Notes

Create these package artifacts during implementation:

- `artifacts/<date>_validation_summary.md` with every command run and result.
- `artifacts/<date>_security_review.md` because security impact is high.
- Optional `artifacts/<date>_manual_smoke.md` if a real run is used for UI/report validation.

Record binary provenance if Rust shared objects are rebuilt:

    sha256sum /workdir/wepppyo3/release/linux/py312/wepppyo3/climate/cli_revision_rust.so /workdir/wepppy/cli_revision_rust/cli_revision_rust.abi3.so

## Interfaces and Dependencies

Rust response contract at completion:

- Each `hru_excess` row in `geneva_run_batch` JSON must include a finite non-negative `peak_runoff_m3_s` field.
- A time-to-peak field is recommended for QA, named `time_to_peak_minutes`, but the required choropleth measure consumes only `peak_runoff_m3_s`.
- Existing fields `hru_id`, `area_m2`, `cumulative_excess_mm`, and `incremental_excess_mm` must remain backward-compatible.

WEPPpy measure contract at completion:

- `HRU_EVENT_MEASURE_COLUMNS` remains unchanged unless implementation discovers a strong reason to add columns. The row-oriented `measure_id/value/unit` design already supports `hru_peak_runoff`.
- `GenevaHruEventMeasureService.materialize_from_batch` writes measure IDs `runoff_depth`, `runoff_volume`, and `hru_peak_runoff`.
- `validate_hru_map_measure_id("hru_peak_runoff")` succeeds.
- `GenevaHruEventMeasureService._validate_measure_scope("peak_discharge")` continues to raise `unsupported_measure_scope`.

UI contract at completion:

- User-facing label: `HRU peak runoff`.
- Measure ID sent to the API: `hru_peak_runoff`.
- Unit displayed where applicable: `m3/s` or `m3_s`, matching existing report unit formatting conventions.

## Required Review Gates

Before closure, run or request these review gates and record findings in package artifacts:

- Code review focused on Rust response compatibility, HRU-local peak correctness, and Python materialization/query regressions.
- QA review focused on one-HRU parity, multi-HRU non-area-split behavior, legacy artifact behavior, and UI measure selection.
- Security review using `docs/prompt_templates/security_review_template.md`, focused on route auth stability, query-engine dataset restrictions, and input validation.

All medium/high findings must be fixed or explicitly accepted with rationale before closing the package.
