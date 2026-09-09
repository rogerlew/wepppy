# Correctness review — yearly water balance

- Reviewer: independent `watbal_contract_1`, 2026-09-09.
- Scope: report adapter, yearly template, regression tests and user guide.
- Authority: output-scope-contract.md, Yearly water-balance presentation;
  checkpoint `9fe98a133` precedes all implementation edits.
- Goal: show existing runoff and preserve explicit all-years selection in HTML/CSV.
- Security: existing run access and scope validation unchanged; no write boundary.

| State | Required behavior | Evidence |
| --- | --- | --- |
| Missing dataset/Runoff column | Explicit failure; no zero synthesis | Missing dataframe and real parquet-column tests |
| Empty injected frame | Empty rows, including runoff header | Empty-frame test |
| Populated/legacy parquet with Runoff | Aggregate existing depths | Real parquet tests and production copy parity |
| Null runoff cells | Existing zero-fill policy | Null-normalization test |
| Invalid scope | Existing explicit rejection | Existing invalid-scope test |

Input coverage: baseline/roads, omitted/default year exclusions, explicit empty
exclusions, and first-year/two-year selections. New links retain scope and CSV
format. Existing duplicate/out-of-range handling is unchanged. Missing columns
are exceptional under the amended report contract; report failures do not
mutate source artifacts or create partial model output.

Validation: 8 report tests and 239 route/template tests passed; 835 JavaScript
tests, npm lint, docs lint, test-stub checks and broad-exception checks passed.
Broad gate: `wctl run-pytest tests --maxfail=1
--ignore=tests/disturbed/test_disturbed_matrix.py` completed with 7,953 passed,
72 skipped in 568.98 seconds. The excluded matrix runs unrelated 100-year
WEPP simulations; this is not a claim of an unfiltered full-suite pass.
Real Flask `url_for_run` preserves `exclude_yr_indxs=` with baseline scope and
CSV format. A read-only copy of the reported production parquet yielded all 10
water years (2016–2025), runoff total 115.82637440591618 mm and mean
11.582637440591618 mm; yearly values, mean, population deviation and ratio
matched independent pandas aggregation. Generated HTML and CSV are under
`/tmp/yearly-watbal-parity/`; production files were not modified.

No blocking review findings. Initial coverage observations for null cells and
missing parquet runoff were closed with tests. Real-browser navigation was not
exercised; rendered URLs, route semantics and the real URL helper were checked.
Gate: pass for the bounded change; production deployment remains separate.

Local test friction: this report test module already installs process-global
geospatial stubs, which break collection when it precedes the UI suite. Focused
report/UI suites were run in separate processes; stub cleanup is a separate
maintenance task, not an implementation fallback.
