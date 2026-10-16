# Implementation validation — 2026-10-16

Checkpoint: `0dab11743` (ancestor of implementation). Read-only correctness
review: maca_contract_review; no production-code blockers. Its failed-state
evidence finding was closed by an actual replay-version validation failure after
PRN creation, with real exception logging/download/archive readback. Both final
artifact tests passed. Governance/contract approvals are in the checkpoint review.

## Checks

- Initial focused Python suite: 392 passed (client's 40 pairs, catalog/parser,
  facade, rendering and RQ routes).
- Updated rendering/RQ/native artifact suite: 237 passed.
- Helper/base persistence and artifact regression suite: 104 passed.
- Final real generated/completed and replay-validation-failure artifact cases:
  2 passed. The replay failure occurs before launching the native executable;
  the successful case executes native CLIGEN.
- Frontend: 119 suites / 987 tests passed; lint passed. Controller bundle rebuilt
  in the container, with no generated diff (production JavaScript unchanged).
- Climate stubtest and test-stub completeness passed. Broad-exception enforcement
  passed; existing client handler line locations were preserved, no new catches.
- Scoped documentation lint and whitespace checks passed.

The broad gate was started, then interrupted after 386 passed / 27 skipped when
its known browser prerequisite failure was independently reproduced. Exact test:
`tests/weppcloud/test_run_catalog_reader.py::test_real_file_sql_http_browser_chain`.
Playwright cannot find chromium_headless_shell-1194/chrome-linux/headless_shell
under static-src/.playwright-browsers. This is an incomplete broad gate, not a
pass. Prior baseline sweep in this session reached 10734 passes before the same
failure. Rendered HTML, jsdom submission/visibility, and HTTP download checks pass;
no real browser or deployed production identity is claimed.

## Live and generated evidence

`20261016_live_ccsm4_build.json` records CCSM4/r6i1p1/RCP4.5 at (-116, 47),
2030-01-01 through 2030-12-31. All seven live variables returned HTTP 200 with
matching member metadata. Actual CLIGEN produced 365 daily rows; native source
values were compared through the unchanged PRN rounding (0.254 mm rain, whole
Fahrenheit temperature), then CLI's decimal serialization. Maximum source-vs-CLI
differences: 0.160 mm rain, 0.322 C temperature. After expected PRN quantization,
all serialized CLI differences were <=0.051. The actual WeppPrepService copied
wepp/runs/p1.cli and its bytes/hash match climate/wepp.cli. No WEPP model run or
full-domain/full-period availability claim is made.

Live raw responses and climate files remain in the development container under
/tmp/maca-live-build; result hashes are retained in the package. The earlier
retained source-member probe covers all seven variables for both CCSM4 scenarios.
Deterministic tests additionally read actual PRN date/rain/temperature values,
CLI calendar/values, prepared CLI values, normal HTTP downloads, saved selection,
and canonical archive/restore bytes. The working-stage check runs after PRN
serialization but before replay; failed-stage checks use the actual exception
logger and preserved partial outputs, without simulating job success.

Initial live readback used an overly tight 0.2 C raw-source tolerance and exposed
the existing Fahrenheit rounding. Corrected acceptance computes the documented
quantization, without modifying source values or the generation pipeline.

## Scope and handoff

One combined 40-pair select precedes future years. New and legacy-absent values
retain GFDL-ESM2G/RCP8.5. Unsupported values fail explicitly and malformed saved
values render an empty selected placeholder. CCSM4 uses r6i1p1; others r1i1p1.
Authority and rationale: `docs/schemas/maca-cmip5-selection-contract.md`, sections
Selection, compatibility and presentation / Retrieval and scientific behavior;
ADR-0097. User guidance: Usersum climate-options.md, Future MACA CMIP5.
No production deployment or project migration performed.
