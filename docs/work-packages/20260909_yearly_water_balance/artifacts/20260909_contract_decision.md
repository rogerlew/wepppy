# Contract decision — yearly water balance

Starting revision: `157b4c2e7`. Operator approval: "add runoff and fix the
include all years bug" on 2026-09-09. Active scope is this bounded package.

Applicable authorities: output-scope-contract.md (dataset isolation and yearly
presentation), rq-response-contract.md (unchanged error envelope), and shared
controller-contract.md (unchanged runtime behavior). The exact normative delta
is the new yearly-presentation section in the output-scope contract. Existing
route access, column names, unit conversion, filtering defaults, and model
parameterization are unchanged. Implementation conformance is pending.

Compatibility plan: add Surface Runoff (mm) from required existing Runoff data;
preserve prior columns and scope isolation. CSV consumers using positional
columns must account for the added column. No parquet/NoDb/generated model-file
mutation. Recompute report artifacts from real production data in a temporary
local directory and compare aggregation to the source.

Valid states: populated and empty datasets; no excluded years; default first
two exclusions; custom lists, duplicates and out-of-range indexes; both scopes.
Missing Runoff columns in nonempty dataframes or parquet sources are exceptional
and must fail rather than claim zero. Null/NaN cells retain existing zero-fill.
Empty injected frames may omit schemas; empty parquet retains required columns.
Supported legacy sources with Runoff remain readable; a missing dataset or a
legacy parquet without Runoff fails explicitly, without rebuilding or mutation.
Malformed filter tokens keep existing parser behavior. Invalid scope/auth
continue existing rejection contracts. No new filesystem or execution boundary.

Regression plan: real parquet aggregation/statistics/CSV; empty and missing
runoff; scoped parity; rendered all-years/CSV URLs and route filter round-trip.
No new parameterization formula, threshold, unit conversion, or fallback.
Independent contract reviews: `watbal_contract_1` passed; `watbal_contract_2`
passed after clarifying missing-column versus null/empty-frame handling.
Both were read-only reviews before implementation. Findings are closed.
No implementation files changed yet.
