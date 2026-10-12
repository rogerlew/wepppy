# SA-01 validation

Native commit: `822b6fe`. Contract ancestor: `a94028e78`. WEPPpy implementation: `a20089d63` plus the supported-input catalog correction below. Final broad Python result is pending.

## Completed checks

| Check | Result |
| --- | --- |
| `PYO3_PYTHON=/usr/bin/python3.12 cargo test -p wepp_interchange_rust` | 107 unit + 17 integration passed; includes three new kernel tests. |
| `wctl run-pytest tests/nodb/test_soil_anisotropy.py tests/docker/unit/test_wepppyo3_interchange_startup_contract.py` | 44 passed, 44.01s. |
| Corrected Jinja eligibility/read-only tests | 4 passed, 203 deselected. |
| `wctl run-npm test` | 968 tests, 118 suites passed. |
| `SMOKE_SOIL_ANISOTROPY=true wctl run-npm smoke soil-anisotropy.spec.js` | 1 passed, 17.5s; retained browser receipt, log and screenshot. |
| `wctl run-stubtest wepppy.wepp.soils.utils.wepp_soil_util` | Passed. |
| `wctl check-test-stubs` | Passed. |
| Controller build via `wctl exec weppcloud python /workdir/wepppy/wepppy/weppcloud/controllers_js/build_controllers_js.py` | Passed; generated bundle contains the new eligibility controller. |
| Forest native startup preflight | Passed; exact release origin and SHA agree with `native-build.json`. |
| Changed broad-exception enforcement | Passed; existing prep-service allowlist line numbers moved by three, no new catch. |
| Package/contract/ADR/user/developer documentation lint | Passed. |

## Generated artifact and live behavior

`forest-validation.py` invokes real locked Wepp persistence, the actual `_prep_multi_ofe` method and worker, Rust kernel and soil writer using bounded synthetic terrain/climate descriptors on a disposable forest project. `forest-validation.json` records two OFEs with 25/25/3 at 100/500/800 mm, exactly one source read and one destination write, and unchanged source SHA. `prepared-p1.sol` is the output. Regression tests additionally cover ordinary/uploaded/symbolic preparations, formats 7778/9001/9002/9003/9005, clipping, unsupported formats, clearing, invalid values and effective-hourly overrides.

The browser uses the existing dev-agent account without role changes. It proves visible/editable eligible inputs, actual Run-form serialization, specific HTTP 400 rejection of out-of-range/inactive overrides through the shared prep-only payload handler, unchanged saved values after reload, real hourly saves and reload, real asynchronous READONLY jobs, non-MOFE disabled controls, and normal project download whose SHA equals the preparation artifact. The Run enqueue request is intercepted: this does not claim a model execution or full hydrologic validation. Original project inputs and production runs are untouched.

## Limits and resolved validation friction

`wctl run-npm lint` remains blocked by the preexisting `controllers_js/__tests__/climate.test.js:300` conditional-expect error. The changed controller/tests produce no lint error. Core stubtest cannot complete because of existing NoDb/third-party typing errors; the new fixed-length tuple error was corrected, and the final core run reports no anisotropy helper error. Do not represent either broad gate as passing.

The first full Python run stopped after 425 passes because it collected the old literal native-pin assertion before the paired pin edit; the final 44-test run passes the new assertion, and the full gate was restarted against the final code. The initial combined focused run had 444 passes before exposing the numeric macro's dropped read-only class; the macro and its regression were corrected.

The next broad run stopped after 2,103 passes/28 skips at the existing advanced-options contract check: `SUPPORTED_WEPP_RUN_FORM_FIELDS` omitted the two anisotropy keys. Both catalog entries were added; request handling already passes the keys to the implemented parser. The full gate was restarted after this correction.

Optional test-isolation executions both passed and the new file passed alone. The state scanner nevertheless exits 1 for import initialization (`pyexpat.errors` and added PINT/GDAL/PROJ environment defaults); no randomization plugin is installed, so the two executions are not evidence of shuffled order. The observe-only quality tool completed but reported unavailable changed-file deltas and no Radon; it does not constitute a complexity gate.

Initial forest restart correctly refused the refreshed native binary until the required SHA pin was updated; all four affected services were restored after pairing the pin. Browser retries exposed stale generated JS (host Python lacked Jinja; rebuild succeeded through wctl), a closed More menu in the test, and an attempted READONLY reversal before its manifest job finished. Final smoke opens/closes the menu and polls actual job completion. These are retained as resolved failures, not successful first attempts. Scientific stability is outside this software acceptance; the requested warning remains visible.
