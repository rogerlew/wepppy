# MRS-01 local validation

## Environment and authority

Development Compose container through installed `wctl`; Python 3.12.16, pytest
9.0.3, existing Flask/Starlette/GDAL/native libraries. Host static tooling used
Python 3.14.6. No dependencies installed and no deployment or production jobs.
Contract ancestors: `3ab204e9c`, `ca28085ac`. Implementation is uncommitted.
Concurrent unrelated Roads/release edits exist; this is a shared working-tree test.

## Executed evidence

Logs in [validation](validation/) retain commands, counts and warning summaries.
Counts overlap and must not be added into a unique-test total.

| Command / suite | Result | Evidence |
| --- | --- | --- |
| `wctl run-pytest tests/microservices/test_malformed_route_matrix.py` | 83 passed | `rq-matrix.log`; route list in `rq-route-coverage.json` |
| `wctl run-pytest tests/weppcloud/routes -k 'malformed_payload_route_matrix or malformed_body_before' -rP` | 18 passed, 1671 deselected | `flask-matrix.log`, including concrete paths |
| Recorder registered route malformed tests | 2 passed | `recorder.log` |
| Focused treatment/GDAL/upload/RQ boundaries | 220 passed | `focused-boundaries.log` |
| Follow-on agent/batch/optional persistence/project/parser regressions | 175 passed | `followup.log` |
| WAM-01 real admission/persistence suite | 63 passed, no skips | `wam-persistence.log` |
| Real multipart landuse/soils persistence suite | 8 passed, no skips | `input-persistence.log` |
| Combined final WAM/input persistence rerun | 71 passed, no skips | `persistence-final.log` |
| Session-token suite after actual-body fix | 59 passed | `session-final.log`, both mint and marker spies with valid follow-up |
| AgFields routes after staging-aware fixture correction | 58 passed | `agfields-final.log` |
| Treatments controller fixtures and real-GDAL persistence | 8 passed | `treatments-final.log` |
| `wctl run-stubtest wepppy.nodb.core.landuse` | Pass | `stubtest.log` |
| `wctl check-test-stubs` | Pass | `stubs.log` |
| `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` | Pass after exact location refresh and reviewed cleanup entries | `broad-exceptions-final.log`; historical drift in `broad-exceptions.log` |
| Same inventory with `--no-allowlist --base-ref 3ab204e9c` | Pass: net -4 handlers | `broad-exceptions-unsuppressed.log` |
| `python3 tools/code_quality_observability.py --base-ref origin/master` | Completed, observe-only | `quality.log`; radon absent and changed-file analysis unavailable in generated report |
| `wctl run-pytest tests/microservices tests/weppcloud` | 4,017 passed, 74 skipped | `routes-final.log` |
| `wctl run-pytest tests --maxfail=1` | Environmental lock collision after 4,117 passed / 125 skipped; isolated continuations completed | `full-attempt-3.log`, isolation below |

The broad-exception allowlist is keyed by exact line number. Existing deliberate
handlers shifted after imports/typed rethrows, losing suppression. Refreshed 34
existing locations without changing policy or expiry; [proof map](allowlist-line-refresh.json)
records identical handler AST and enclosing scope (one duplicate-body match was
manually disambiguated by order). QA independently verified the refresh. Two new
explicit entries inventory reviewed multipart/form cancellation cleanup boundaries;
both close temporary resources and re-raise unchanged. The canonical gate now
passes (net -37 with its line-based comparison). The earlier unsuppressed comparison
also passed with four fewer broad handlers. Counts reflect different suppression
modes and must not be interpreted as deleting 37 exception handlers.

Earlier full run stopped at one obsolete invalid-raster fixture: 2,274 passed,
36 skipped. Focused real-raster tests now pass. Earlier broader route run had
3,940 passes, 74 skips and three failures subsequently fixed and focused-tested.
The next full attempt stopped after 1,163 passes and 36 skips on an AgFields
stub expecting a final filename at the pre-promotion validation boundary. The
corrected stub verifies staging directory and bytes; all 58 AgFields tests pass.
`full-attempt-2.log` retains this failure. Those historical attempts are not
passing full-suite claims.

## Direct boundary evidence and limits

WAM/input persistence tests use an explicitly disposable Redis Unix socket,
`RQ212_TEST_REDIS_SOCKET=/workdir/wepppy/.pytest_cache/mrs-admission.sock`, with a
test-server guard. Files and controllers use disposable test roots. Assertions
include actual serialized bytes, reload, same-process valid follow-up, prepared
inputs and retained source/output sentinels. Auth/queue/external execution are
controlled at their boundaries; no production destructive request is needed.

Optional PATH/Geneva tests cover absence and populated state. WATAR/Ash, Ron and
BatchRunner tests cover real save/reload/cache behavior. Real GDAL upload tests
exercise readable raster/VRT content and relative dependencies before source
promotion. RHEM invokes its real cleanup against disposable output only on valid
accepted worker-boundary cases. Parser cancellation/disconnect tests assert
resource cleanup and preserve operational failure classification.

Independent [correctness](correctness-final-review.md), [QA](qa-final-review.md)
and [security](security-final-review.md) reviews cover the implementation.
Production observation remains a separate rollout obligation. No new scientific
parameterization, auth policy, queue topology or frontend code changed; frontend
and queue graph/live-tree gates are therefore not applicable.

## Shared test-runtime collision and isolated continuation

The third canonical full attempt stopped at
`test_postfire_debris_flow_runtime_m3.py::test_fresh_basin_run_prepares_sources_and_reuses_them[western-key7]`:
`NoDbAlreadyLockedError`, owner `c43e684eaa16:1001876`. Read-only process inspection
confirmed PID 1001876 was an active unrelated release-validation pytest process
under `out/261029-r2-isolated`. The tested controller and test file are unchanged
by MRS-01. No shared lock, Redis key or other process was modified.

The two parameter cases pass with a unique temporary run basename (2 passed,
66 deselected), retaining real NoDb/filesystem/native behavior. The retained
`validation/isolated_tmp_plugin.py` only supplies unique `tmp_path` directory names
and, when explicitly requested, selects the collection suffix beginning at one
exact node. It fails if that node is absent/ambiguous. Earlier tests are reported
as deselected, not passed. The continuation runs through `wctl exec weppcloud`
with the same environment and source tree; only disposable fixture names change.

This does not turn the original canonical command into a passing run. Record both
its environmental failure and the continuation result. The smallest follow-up for
test maintainers is unique NoDb run basenames in real-Redis fixtures (the lock key
uses run identity, so separate pytest roots alone do not prevent collisions).

The first isolated continuation passed 502 cases, then reached two Treatments
unit-test GDAL doubles that lacked the newly exercised band checksum interface.
The doubles now implement `GetRasterBand(1).Checksum()` while retaining their
original mapping/nodata assertions. The controller and real-raster persistence
suites pass together (8 tests). `continuation-attempt-1.log` retains the failure.
The next suffix begins at that exact test and runs without a first-failure stop,
using the same unique-directory plugin. Its outcome is 7,832 passed / 245 skipped / 4,743 deselected; see `validation/continuation-final.log`.

## Final accounting and disposition

Independent QA verified non-overlapping collection segments: 4,117 + 502 + 7,832
passes = **12,451**, and 124 + 244 executed skips = **368**, accounting for all
**12,819 collected tests**. One collection-time skip is reported separately.
Repeated diagnostic/focused tests are not added to these totals. Skip reasons for
the final suffix are retained in `validation/continuation-final.log`; they include
opt-in integrations, unavailable fixture datasets, and optional dependencies.
The 71 WAM/input cases pass separately against the disposable Redis server.

The original plain full invocation remains failed; split processes do not establish
uninterrupted suite-order compatibility. All observed task-related fixture failures
were repaired and independently reviewed; no confirmed MRS-01 production finding
remains open. Static/stub/documentation gates pass. No live deployment or production
incident-resolution claim follows from local tests.

To reproduce the retained continuation plugin directly, put this package's
`artifacts/validation` directory on `PYTHONPATH`, use `-p isolated_tmp_plugin`, and
set `MRS_CONTINUE_FROM` to the exact node recorded in the corresponding command log.
Without that variable, the plugin changes only default temporary run names.

Cleanup: verified the dedicated Redis socket guard and shut down only that
disposable server; shared Redis and other pytest processes were untouched. Removed
the temporary plugin copy; the exact plugin is retained with the validation logs.
