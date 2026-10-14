# SBS metadata test failure disposition

Date: 2026-10-14 UTC. Operator request: disposition the test failure holding EDDE feasibility closeout. Starting revision: `ddd62ac22`.

## Finding and authority

Resolved unrelated stale test expectation, not an EDDE regression or production defect. The failing SBS parameter of `test_upload_schema_and_defaults_routes_include_hardened_file_metadata` expected `optional_but_if_present_must_map_known_severity`. Runtime returns `optional_unknown_colors_unassigned`, matching [the authoritative upload contract](../../../schemas/upload-endpoint-contract.md#sbs-palette-admission): readable unknown palette colors are accepted for explicit class assignment.

Contract decision `b4be200b4` and implementation `69cfd68aa` preceded EDDE planning commit `03435abc5`. `git blame` identifies the runtime value at schema_defaults_routes.py:4924 with `69cfd68aa`; `git merge-base --is-ancestor 69cfd68aac 03435abc5` succeeds. The retained isolated failure and original broad-run failure show exactly this string mismatch. Source eligibility, acquisition, CLIGEN and PRISM paths do not participate in this assertion.

## Correction and validation

Updated only the obsolete expected string in `tests/microservices/test_rq_engine_geospatial_upload_metadata_routes.py`. Production SBS behavior, upload constraints, validation and EDDE code are unchanged. The test still checks the actual schema and defaults endpoints and their metadata; it is not skipped, weakened to accept either string, or marked xfail.

Command: `wctl run-pytest tests/microservices/test_rq_engine_geospatial_upload_metadata_routes.py -q`.

Result: **21 passed**, six dependency deprecation warnings, 1.19 seconds. Full output: [pytest-sbs-disposition.txt](validation/pytest-sbs-disposition.txt). This exercises all four upload variants and the surrounding metadata-route tests.

## Gate disposition

Close the EDDE feasibility hold for this identified failure: the existing contract is correct, the stale test is repaired, and its complete module passes. Together with retained EDDE scientific/artifact evidence, independent correctness/security reviews and the operator's accepted raw-EDDE/hybrid policy, this supports feasibility closure with conditional-go to application integration.

The original full suite remains **failed** (1,265 passed, 28 skipped before this assertion); its earlier continuation remains **incomplete**. The PRISM package separately reproduced the same failure after 1,280 passes. No complete full-suite pass is claimed. A full rerun is not required for this one-line test correction; its remaining coverage gap is disclosed here and the successor integration package retains its normal full-suite gate. This disposition is bounded to the identified stale assertion, not a waiver of future failures.

No production deployment, service restart or project mutation occurred. Actual U.S./Canadian application acceptance, live supported choices and operational acquisition policy remain integration work.
