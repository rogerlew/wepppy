# OSR-01 validation evidence

Date: 2026-11-16 UTC. Contract ancestor: `67468cf86`. Candidate source and generated
bundle SHA256 values are in `candidate_hashes.json`. No production rollout.

## Scoped checks

| Check | Result | Evidence |
| --- | --- | --- |
| Original JS regressions | 2 fail before patch; dropped reference/display and multipart row index | `regression_js_before.log` |
| Backend association/recovery regressions | Fail before implementation | `regression_python_before.log` |
| Omni route, normal-reader routes, SBS freshness | 116 passed | `python_tests.log` |
| Real NoDb commit and intervening saved-state mutation | 2 passed | `persistence_tests.log` |
| Omni controller | 26 passed | `controller_tests.log` |
| Scoped ESLint | Passed | `eslint.log` |
| Generated controller bundle | Rebuilt in canonical container | `bundle_build.log` |
| Changed-route broad exceptions | No increase | `broad_exceptions.log` |
| Correctness/UX and security | Findings closed; code gates pass | Independent review artifacts |

No full repository or frontend suites were run, per operator scope. Commands:

    wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py tests/nodb/mods/test_omni_sbs_freshness.py --maxfail=2
    wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py -k real_nodb_commit --maxfail=1
    wctl run-python wepppy/weppcloud/controllers_js/build_controllers_js.py

Jest/ESLint used `wctl run-npm exec --call` with the repository's installed
executables and configuration, restricting paths to `omni.test.js` / `omni.js`.
The package's old `npm test -- ...` suggestion was not used: the npm script chains
additional node tests. Host Python lacks Jinja2; building through `wctl run-python`
resolved that local tooling issue without adding dependencies.

## Browser and live submission

`browser_acceptance.cjs` uses the existing dev-agent login and CAP flow without
retaining credentials/tokens. Actual dev URL:
`https://forest.tail305ec9.ts.net/weppcloud/runs/qa-omni-reload-20261116/config/`.
The normal saved-definition reader hydrated the real project. The control showed
`Current SBS map` and `qa_omni_reload.tif`, with zero selected Files. Clicking the
actual Run Omni button returned HTTP 202/job
`3dd9ac8f-b0ab-483d-aae8-dba1d946b45d`. Reload retained the same filename/reference.
See `browser_acceptance.json` and `browser_saved_map.png`.

The dev rq-engine API was restarted to load the candidate; existing workers and
production services were not restarted. The generated bundle was served by the
normal dev web stack. Parent-job completion is not proof of scenario/model success. The scenario job
failed at the same watershed stage; compile/finalize jobs remain deferred. See
`rq_job_status.json`, `rq_scenario_error.log`, and `rq_watershed_error.log`.
No acceptance job remains actively running; the failed/deferred tree is retained.

## Native input and generated-artifact chain

`prepare_runtime.py` reused the existing independent-copy utility. It copied
4,165 files (8,328,199,666 logical bytes), rebased only the disposable identity,
and checked source membership/versions. The original project was not hydrated or
mutated. `runtime_copy.log` records the manifest location. The fixture retained
its scientific settings, climate length, and WEPP binary.

Execution used the dev `weppcloud` container, UID 1000/GID 993, its existing mounts
and configuration, and `WEPPPY_NCPU=4`. The disposable run and copied project files
remain available at `/wc1/runs/qa/qa-omni-reload-20261116`.

The first execution copied/consumed the SBS input and completed all 217 hillslopes.
`runtime_followup.py` then invoked the real run admission/parser on the saved
reference with no upload, read the actual durable NoDb state, restored the
native-produced child raster, and forced a rerun by clearing only the disposable
scenario dependency record. The actual reset/copy/model path ran again.
`runtime_followup.json` verifies:

- Restored and consumed child main-file SHA256:
  `7d1ed360d8e639050cf3879293efcdbee216bd9a4faac4e03399442416d97405`.
- Real GDAL raster dimensions/bands/checksum readback, not just file existence.
- Generated management, soil, and run-file counts, sample contents, and digests.
- 217 fresh hillslope loss outputs created after the forced rerun began.
- Staging source consumed again after the verified copy into the reset child.

## Explicit environment limitation

Both native attempts stopped at the watershed stage with:

    Channel climate file beginning year 2007 is not equal
    to Hillslope\watershed pass file beginning year 1980
    *** SIMULATION STOPPED ***

The exact tail is retained in `runtime_followup.json`; model logs and inputs
remain in the disposable child. This is an input-date consistency failure after
successful SBS recovery and hillslope execution. No climate/default/model fix was
made. Native preparation initially needed the copied optional Treatments controller
initialized for page rendering; this was fixture setup only, not a production fix.

Highest supported claim: implementation and scoped validation passed; authenticated
browser submission/reload and native input restoration/reset/hillslope boundaries
validated in dev. Final watershed output/report, production deployment, and repair
of the user's affected project are **not** established. The package stays open for
final watershed/report acceptance on a climate-consistent project.

## Recovery and rollback

The checkpoint and candidate introduce no data migration, service, or new receipt
schema. Reverting candidate code and rebuilding the bundle restores previous code
behavior; old positional admission will again lack the corrected saved-map reuse.
Do not remove referenced staging files during rollback or claim model-output
rollback. No source project or production cleanup was performed. Retain the
isolated acceptance run until its evidence and outstanding fixture gate are resolved.

## Fixture repair and final acceptance — 2026-11-16 UTC

The preceding limitation is resolved for the disposable acceptance project. The
user authorized fixture repair; no production code or scientific settings changed.
The current Climate sources cover 2007–2024, while inherited prepared hillslope
climates/runfiles retained 1980 and 45 years. `repair_fixture.py` backed up 654
prepared climate/run/error files inside `fixture_repair_before/`, then ran normal
Wepp hillslope preparation/execution, interchange, watershed preparation/execution,
and cleanup. `fixture_repair.json` retains all 217 selected-source/prepared climate
digest comparisons and actual daily year sets, native baseline completion, and
unchanged source-project NoDb/climate/prepared-climate hash comparison. Earlier
failed receipts remain unchanged. Fixture-copy instructions now explicitly require
baseline regeneration before native acceptance.

Executed scoped acceptance commands:

    wctl run-python docs/work-packages/20261116_omni_sbs_reload/artifacts/repair_fixture.py
    wctl run-python docs/work-packages/20261116_omni_sbs_reload/artifacts/runtime_repaired.py
    node docs/work-packages/20261116_omni_sbs_reload/artifacts/browser_repaired.cjs
    wctl run-python docs/work-packages/20261116_omni_sbs_reload/artifacts/check_repaired_jobs.py
    OMNI_REPORT_READBACK_ONLY=1 node docs/work-packages/20261116_omni_sbs_reload/artifacts/browser_repaired.cjs

Results:

- `runtime_repaired.json`: actual consumed-child recovery, real persisted reload,
  forced reset/native execution, same raster SHA256 and GDAL checksum, 218 each
  management/soil/run inputs, 217 fresh hillslope outputs, and completed watershed.
- Baseline and scenario output year sets both equal 2007–2024. The 22-row native
  report is retained in `runtime_repaired.csv`.
- `browser_repaired.json` and `browser_repaired.png`: empty file chooser, current
  filename, saved reference, HTTP 202, and matching reload state.
- `browser_repaired_jobs.json`: root, compilation, and finalization jobs all
  finished; the unchanged scenario reused completed output rather than creating
  another scenario execution job. Report readback retained 22 rows.
- `browser_final_report.json` and `.html`: authenticated normal report endpoint
  returned HTTP 200 after job-tree completion, with the expected scenario and
  rendered outlet metrics; body digest retained.

Local implementation/validation is complete. These receipts do not establish
production rollout or repair of the original user's project. The source project
was not hydrated or changed; the disposable copy and prior failure evidence remain
available. Existing scoped code-test results remain applicable because this repair
changed only fixture/evidence scripts and documentation.
