# WEPP Output Scope Contract
> Authoritative contract for report `output_scope` selection and baseline-vs-roads output isolation.
> **See also:** `docs/schemas/rq-response-contract.md`, `docs/schemas/weppcloud-browse-parquet-filter-contract.md`, `wepppy/nodb/mods/roads/specification.md`

## Normative Status
- This document is normative and authoritative for `output_scope` behavior.
- Requirement keywords `MUST`, `MUST NOT`, `SHOULD`, and `MAY` are interpreted per RFC 2119.
- If implementation and this contract diverge, either:
  - implementation MUST be corrected, or
  - this contract MUST be updated in the same change set.

## Scope
- Defines canonical `output_scope` values and normalization.
- Defines dataset path mapping and run-output isolation rules.
- Defines route-level `output_scope` support and invalid-input behavior.
- Defines Runs-page link discovery rules for Roads run results.
- Does not replace auth/capability requirements for those routes.

## Canonical Values
- Allowed values: `baseline | roads`.
- Default when query parameter is missing or empty: `baseline`.
- Value matching is case-insensitive (`ROADS` normalizes to `roads`).
- Invalid values MUST fail explicitly; silent fallback is forbidden.

Implementation reference:
- `wepppy/wepp/reports/output_scope.py::normalize_output_scope`

## Path Mapping Contract
- Baseline output root: `wepp/output`
- Roads output root: `wepp/roads/output`
- Interchange root: `<output_root>/interchange`

`scoped_dataset_path(...)` rules:
- For `baseline`, return the input path unchanged.
- For `roads`, rewrite only paths rooted at `wepp/output` to `wepp/roads/output`.
- Paths outside `wepp/output` MUST remain unchanged.

Examples:
- `wepp/output/interchange/H.wat.parquet` + `roads` -> `wepp/roads/output/interchange/H.wat.parquet`
- `watershed/hillslopes.parquet` + `roads` -> unchanged

Implementation references:
- `wepppy/wepp/reports/output_scope.py::resolve_output_scope_paths`
- `wepppy/wepp/reports/output_scope.py::scoped_dataset_path`

## Storage Isolation Contract
- Roads-scoped report resource regeneration MUST write only under `wepp/roads/output/interchange/*`.
- Roads flows MUST NOT mutate baseline `wepp/output/*`.
- Required Roads resources MUST be checked after regeneration; missing required resources MUST fail explicitly with `FileNotFoundError`.
- Successful regeneration persists `roads_report_resources.output_scope = "roads"`.

Implementation reference:
- `wepppy/nodb/mods/roads/roads.py::_regenerate_roads_report_resources`

## Route Support Matrix
| Route | `output_scope` Query Param | Default | Invalid Value Behavior | Notes |
| --- | --- | --- | --- | --- |
| `/runs/<runid>/<config>/report/wepp/summary` | Yes | `baseline` | `400` + JSON error payload | Scope passed to outlet/hill/channel summary reports. |
| `/runs/<runid>/<config>/report/wepp/yearly_watbal` | Yes | `baseline` | `400` + JSON error payload | Scope passed to `TotalWatbalReport`. |
| `/runs/<runid>/<config>/report/wepp/avg_annual_watbal` | Yes | `baseline` | `400` + JSON error payload | Scope passed to hillslope/channel watbal reports. |
| `/runs/<runid>/<config>/plot/wepp/streamflow` | Yes | `baseline` | `400` + JSON error payload | Uses scope-aware `totalwatsed3.parquet` relpath. |
| `/runs/<runid>/<config>/report/wepp/return_periods` | Yes | `baseline` | `400` + JSON error payload | Scope passed to return-period postprocess service. |
| `/runs/<runid>/<config>/gl-dashboard` | Yes | `baseline` | `400` + JSON error payload | Scope-aware WEPP dataset relpaths injected into template context. |
| `/runs/<runid>/<config>/storm-event-analyzer` | Yes | `baseline` | `400` + JSON error payload | Scope-aware WEPP dataset relpaths injected into template context. |
| `/runs/<runid>/<config>/report/wepp/results` | No | N/A | N/A | Baseline Run Results panel. |
| `/runs/<runid>/<config>/report/roads/results` | No | N/A | N/A | Roads Run Results panel; links are generated as roads-scoped where applicable. |

## Runs-Page Trigger and Discovery Contract
### Baseline WEPP Run Results panel
- Served by `/report/wepp/results`.
- Link set is template-driven (`controls/wepp_reports.htm`) with conditional visibility for baseline artifacts:
  - `totalwatsed3.parquet` and `totalwatsed2.parquet` download links appear only when those files exist.
  - interchange README link appears only when `wepp/output/interchange/README.md` exists.

### Roads Run Results panel
- Served by `/report/roads/results` and rendered from `controls/roads_reports.htm`.
- Panel visibility condition:
  - `run_summary_state == "completed"`
  - `roads_report_resources.status == "ready"`
  - `roads_report_resources.missing_relpaths` is empty
- Links are discovered from `roads_report_resources` and emitted by `_roads_run_results_report_links(...)`.

Roads link gating by required resources:
- `Watershed Loss Summary`: requires `loss_pw0.out.parquet`, `loss_pw0.hill.parquet`, `loss_pw0.chn.parquet`.
- `Return Periods`: requires `ebe_pw0.parquet`, `totalwatsed3.parquet`.
- `Yearly Water Balance`: requires `totalwatsed3.parquet`.
- `Daily Streamflow`: requires `totalwatsed3.parquet`.
- `Average Annual Water Balance`: requires `H.wat.parquet`.
- `GL Dashboard` and `Storm Event Analyzer`: included in Roads link set when the panel is ready.
- `Road Segment Loss Summary (Parquet/CSV)`: requires non-empty `roads_segment_loss_summary_relpath`.

Client trigger behavior:
- Roads controller JS fetches `/report/roads/results/` on initialization and after prepare/run completion to refresh the panel in place.

Implementation references:
- `wepppy/weppcloud/routes/nodb_api/wepp_bp.py::report_wepp_results`
- `wepppy/weppcloud/routes/nodb_api/roads_bp.py::_roads_run_results_report_links`
- `wepppy/weppcloud/templates/controls/wepp_reports.htm`
- `wepppy/weppcloud/templates/controls/roads_reports.htm`
- `wepppy/weppcloud/controllers_js/roads.js::renderRoadsResultsPanel`

## Format Contract
- Canonical persisted report resources in scoped output directories SHOULD be Parquet.
- `roads_segment_loss_summary` MUST be persisted only as:
  - `wepp/roads/output/interchange/roads_segment_loss_summary.parquet`
- CSV export MUST be runtime conversion from Parquet via:
  - `/download/{subpath}?as_csv=1`
- No on-disk CSV shadow artifact is allowed for roads segment loss summary.

## Error Contract
- Library-level scope validation (`normalize_output_scope`) raises:
  - `ValueError("Invalid output_scope '<value>'. Expected one of: baseline|roads.")`
- Route-level invalid scope handling MUST return:
  - HTTP `400`
  - JSON payload containing `error.message` with the invalid-scope text.
- Roads resource regeneration missing required artifacts MUST raise `FileNotFoundError` with missing relpaths listed.

## Compliance Checklist
When adding or modifying scope-aware report surfaces:
1. Validate `output_scope` using `normalize_output_scope`.
2. Use `scoped_dataset_path` or `resolve_output_scope_paths` for all scoped dataset paths.
3. Preserve `output_scope` in rendered template links/forms/selectors.
4. Add/maintain route tests for:
   - default scope behavior,
   - `output_scope=roads`,
   - invalid scope (`400`).
5. Keep roads-only writes under `wepp/roads/output/*`; never mutate `wepp/output/*` in roads flows.
6. Update this contract in the same change set when scope behavior changes.
