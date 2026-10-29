# DM-02 local validation

Date: 2026-10-29 UTC. Contract ancestor: `2fb0a4dd245af6097c009612bccb15f98a729641`.
Implementation and all required gates are locally validated. No production deployment or real account-role changes occurred.

## Implementation and regression gates

Only the shared modal, report-context helper and PowerUser reload hint change production behavior. The existing controller supports sparse panels without production JS or bundle changes. No backend routes, NoDb schemas, model parameter generation or queues changed.

| Gate | Result |
| --- | --- |
| Focused template/routes/lookup Python tests | 326 passed |
| Final real-state policy tests, including corrupt/disabled state | 22 passed |
| Disturbed Jest | 18 passed |
| Full frontend Jest | 1,021 passed, 121 suites |
| Frontend lint | Passed |
| Test-stub check | Passed |
| Broad exception changed-file enforcement | Passed, +0 introductions |
| Full Python suite | 12,072 passed, 298 skipped, 5,830 warnings in 3,328.47 seconds |
| Scoped documentation lint and whitespace | Passed |
| Code-quality observability | Observe-only completed; radon unavailable and no committed-delta analysis before implementation commit |

Commands: `wctl run-pytest tests/weppcloud/routes/test_disturbed_panel_policy.py tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_disturbed_bp.py tests/nodb/mods/disturbed/test_lookup_contract.py --maxfail=1`; final policy file separately; `wctl run-npm test -- --runInBand controllers_js/__tests__/disturbed.test.js`; `wctl run-npm lint`; `wctl run-npm test`; `wctl check-test-stubs`; `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref 2fb0a4dd2`; `wctl run-pytest tests --maxfail=1`.

## Real application and artifacts

[Runtime receipt](runtime.json) was produced by [validate_runtime.py](validate_runtime.py), executed through `wctl exec weppcloud python` under UID 1000/GID 993. Three disposable public copies of the existing `sa-anisotropy-validation` project were used. The source was unchanged. Scoped synthetic POST identities exercise real authorization/CSRF without account changes; anonymous GETs use a preverified CAP test session. Report evidence renders the real shared shell and context processors without supplied Disturbed context, rather than a separately computed report endpoint.

The receipt proves normal Base and explicit Base-with-file render simple; selected Extended and missing-selector legacy Extended render full; Base/delete followed by rendering returns to simple. Base and Extended edits read back changed numeric cells and preserved row counts; Reset Base matches the default CSV. Authorized normal-mode Extended loading/selection/deletion succeeds. Missing CSRF is denied with unchanged tracked bytes. Rendering preserves all tracked NoDb/CSV/soil hashes. Activation changes only Ron among those tracked files, creates no extended table, and reveals full controls on the next render. Existing prepared `wepp/runs/p1.sol` bytes remain unchanged.

## Browser acceptance

[Browser receipt](browser.json) and screenshots ([Base](panel-base.png), [legacy Extended](panel-legacy.png), [developer Base](panel-developer.png)) were produced by [validate_browser.cjs](validate_browser.cjs) against the local HTTPS application. The existing smoke account logs in using stored credentials and the real CAP challenge; credentials are never retained here and no roles are changed. All three actual panels have the expected action/editor/radio counts. Base editor and both Help links return HTTP 200. The Base and developer screenshots were visually inspected.

The browser switches the disposable legacy project to Base: the current DOM retains full controls, then explicit reload shows the simple panel. Consequently that project's final state after browser acceptance is Base; `runtime.json` hashes describe the preceding runtime phase. The runtime script intentionally refuses to overwrite disposable projects on rerun; inspect/remove only those exact acceptance copies first.

## Reviews and limitations

Independent [correctness](implementation_correctness_review.md) and [security](implementation_security_review.md) reviews passed with no findings. No open operator decision remains. Runtime hashes cover NoDb, CSV and soil files, not logs/caches/sessions. This presentation change does not require a fresh model run, native rebuild or production deployment, and none is claimed. The local web service was restarted to load the context helper; deployment must likewise load the changed Python module through the established deployment workflow.

Harness corrections during validation addressed a synthetic GET principal incompatible with user preferences, the anonymous CAP session, blank numeric CSV cells, the actual lookup path property, a collapsed More menu and relative browser URLs. These were acceptance-harness issues; no production changes were needed to pass them.

The first broad run was interrupted by the local web restart; the complete restarted run above finished successfully. Test output is retained in `regression-results.txt`.
