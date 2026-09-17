# C08 water-balance CSV runtime disposition

Independent bounded disposition: **confirmed existing CSV adapter defect,
separate from the implemented C08 cache-currentness correction**. Do not label
the CSV request passed or silently remove its failed status.

The live HTTP request for `avg_annual_watbal/?format=csv` returned500.
`runtime_report_failure_server.log` traces the failure through
`wepp_bp.py:_render_report_csv` → `ReportBase.to_dataframe` →
`ReportBase.__iter__`, which raises `NotImplementedError`. The route explicitly
offers a hillslope CSV path, so “existing unimplemented adapter” describes the
defect more precisely than “an unsupported user request.”

[Retained source comparison](runtime_watbal_csv_baseline_qa.json) uses accepted
pre-report-implementation checkpoint `7d78e9810`. `report_base.py` and the entire
`routes/nodb_api/wepp_bp.py` are byte-for-byte unchanged. Both baseline and
current `HillslopeWatbalReport` inherit `ReportBase`, define `avg_annual_iter`
and `yearly_iter`, and define neither `__iter__` nor `to_dataframe`. Thus after
successful report construction the failing method dispatch already existed
before the freshness changes. This is static baseline attribution plus the
actual current traceback, not a claimed baseline HTTP replay.

C08 acceptance may remain **scoped to actual cached Parquet content/provenance,
successful report HTML, and its real browse/download response**, once those
statuses and bytes are retained. The CSV500 must appear alongside those passes
in final runtime evidence and in the package's known-issue disposition. C09's
successful landuse HTML/CSV response does not make C08 CSV pass. Parent's revised
HTTP harness should continue collecting independent responses after this500
without translating it into success.

The smallest separate follow-up is a water-balance-specific CSV adapter that
selects the documented average-annual or yearly iterator/header and validates
project-unit conversion and channel/hillslope table semantics. A generic base
class fallback would be a broader behavior change and is not justified by this
finding. No runtime, test, or canonical contract edits were made for this review.
