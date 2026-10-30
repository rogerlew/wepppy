# Validation record

2026-10-30 UTC, unchanged implementation revision
`29716c1bd9a24dacf1cb45e05a11b2aa44a5378e`, installed `wctl` development container.

## Executed baseline

Command:

    wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_bootstrap_routes.py --maxfail=1

Result: **135 passed, 7 warnings in 3.20s**. Python 3.12.16, pytest 9.0.3,
container `/workdir/wepppy`, `/opt/venv/bin/pytest`. Existing tests do not assert
unchanged persisted inputs on admission conflict; passing baseline is not proof
of the requested correction.

## Checkpoint-era pending work (superseded by results below)

At checkpoint preparation, failing regression, direct NoDb/Redis/file-fence tests,
controlled A/B preparation readback, webhook integration, lifecycle exclusion,
full pytest and implementation reviews had not run. Current results follow below. No new tests or production edits were made before checkpoint.
No production jobs, deployment, branch changes or dependency installs occurred.

## Documentation checks

Package (8 Markdown files), PROJECT_TRACKER and three amended schemas: `wctl doc-lint --path <path>` passes
with zero errors/warnings. Repeated package/tracker checks after review disposition passed. `git diff --check`
passed. Spelling preview completed for canonical schemas and core package docs;
normalized the sole ExecPlan suggestion (`preexisting`).

## Implementation sequence and initial evidence

Checkpoint `525e78c9f` committed after operator's explicit “yes”, before any
implementation or test edit. New mutation assertion failed before the patch:
`test_wepp_endpoints_return_409_when_singleflight_conflict[.../run-wepp]`
observed `parse_payload={'kslast': 0.25}` after HTTP 409 (1 failed, 80 deselected).
After patch, the two existing route modules pass: 135 passed, 7 warnings.

Initial real NoDb/Redis tests passed all five active and busy rejection variants
(10 passed). Expanded route/coordination/webhook selection: 58 passed, 3 skipped;
those skipped webhook tests need an external disposable Redis socket in this
container, which has no redis-server executable. The host has an installed binary.
A port-disabled disposable server was started on `.pytest_cache/wam-admission.sock`
and marked with the existing fixture's required guard key. No dependencies or
containers installed/started; tests run through `wctl exec` with
`RQ212_TEST_REDIS_SOCKET=/workdir/wepppy/.pytest_cache/wam-admission.sock`.

The first socket run exposed a test-only webhook queue cleanup omission; a second
exposed invalid synthetic batch identity (group without group_name). Both were
corrected: remove only each test's owned queued jobs and assert queue delta;
construct actual batch Wepp with both persisted identity components. Neither
failure was a production-route regression. Rerun in progress.

Broad exception enforcement passes for both changed production files (net +0).
Code-quality observability command exited 0; report retained in `/tmp/wam-quality.log`.

## Final focused evidence

Executed through the installed `wctl exec` wrapper using the same development
container/Python runtime and the disposable Unix socket above:

    /opt/venv/bin/python -m pytest tests/microservices/test_wepp_admission_persistence.py tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_bootstrap_routes.py tests/microservices/test_rq_engine_webhooks.py tests/rq/test_submission_recovery.py tests/rq/test_wepp_singleflight_tracking.py tests/nodb/test_wepp_run_payload_grouped_updates.py --maxfail=1

Result: **237 passed, 7 warnings in 18.57s**, no skips. Includes 38 new direct
admission tests using real NoDb files, real Redis locks and file lifecycle fence,
actual RQ job records and callback publication. They isolate auth/raster readiness
and RedisPrep bookkeeping. No live model worker receives a test job. Source-only
endpoint tests additionally cover existing auth/prerequisite and payload mappings.

The missing-hint teardown fixture initially tried deleting its already-deleted
job; fixed by removing that job from the owned cleanup list. Final result above
includes that correction. Successor-token tests verify lease-loss cleanup leaves
successor ownership intact and publishes no replacement receipt/timestamp/enqueue.

Prepared evidence: real `prep_soil` writer with reloaded accepted NoDb fields,
not the entire `_prep_soils_rq`/WeppPrepService dispatcher. See
`prepared-input-evidence.json`: accepted 0.03, rejected 0.9, parsed `p1.sol` 0.03.
No scientific-output, full-model, production recovery or universal immutability
claim. The disposable Redis server was shut down with `SHUTDOWN NOSAVE`; its socket
was removed by the server. No test writes remain on a live worker queue.

Compatibility command:

    wctl run-pytest tests/rq/test_project_rq_archive.py tests/microservices/test_browse_routes.py --maxfail=1

Result: **72 passed, 52 warnings in 30.96s**. Canonical archive restoration and
browse/raw/download paths remain covered locally; no live production browser test.
Queue functions, arguments, IDs, queues, dependency edges and enqueue sites are
unchanged; graph/catalog/live-tree wiring checks are not applicable. No frontend
code changed. No parameterization ADR or schema migration required.

Observability limitation: the code-quality tool's output reported no changed-file
analysis for the uncommitted production diff and no available radon. Its observe-only
execution passed, but it is not claimed as a complexity-delta measurement. Generated
root report files were restored to their initially clean content; unrelated work
was not modified. `git diff --check` passes.

`wctl check-test-stubs`: **all stubs complete** (one existing invalid-escape
SyntaxWarning). Candidate production/test SHA-256 hashes and container/runtime
identity are retained beside prepared input semantics in the JSON receipt.

## Final normal-writer fixture refinement

An author consistency check found the original soil fixture used uploaded-input
preservation despite a normal project context. Replaced it with persisted
single-OFE state, the existing generated forest 9002 soil from
`tests/omni/fixtures/honeyed_marathoner_sediment_inversion/run_root/wepp/runs/p118.sol`,
and reloaded soil preparation options with preservation disabled. An intermediate
7777 fixture failed normal serialization explicitly (1 failed, 10 passed); it was
not used for final evidence. No production code or serializer behavior changed.

Reran all final boundary tests through the disposable-socket `wctl exec` command:
**38 passed, 6 warnings in 17.31s**. Refreshed retained soil and JSON receipt;
SHA-256 `75431adbedee9bb4bfa611f684e3080959fb2144586b18511047b1535643f7a4`.
Independent correctness reviewer confirmed normal single-OFE arguments and actual
restrictive record `1 10000.0 0.03` plus initial saturation 0.4. The final receipt
supersedes the earlier uploaded-format artifact. The second disposable server
was shut down without saving. Production hashes are unchanged during the broad run;
final test-only refinements are covered by this additional 38-test run.

## Full repository gate and final disposition

    wctl run-pytest tests --maxfail=1

**12,210 passed, 334 skipped, 5,830 warnings in 3,729.76s (1:02:09)**; exit 0.
The ordinary container run skips disposable-Redis cases because it lacks
redis-server; final direct coverage was executed separately with the external
socket, not inferred from skips. Production source remained unchanged throughout
this broad run. Final test-only fixture refinements and the two added successor
cases were covered by the separate final 38-test run; no skipped boundary is
represented as passed.

No required governance or local-validation gate remains blocked. Independent
correctness and QA approve; contract checkpoint `525e78c9f` is committed, and the
implementation is review-ready in the working tree. No branch change, dependency
installation, production job submission, deployment or affected-run repair.
Local evidence ends at real persisted-state/coordination and prepared-soil writer
readback; full dispatcher/model/report and live production-browser validation are
not claimed. No late-failure rollback or universal concurrent-edit protection.

Final shared-workspace HEAD is `22dc9184d0886cdc17ac56d9e9881d9523ffcb7f`:
an unrelated Roads documentation commit advanced HEAD during validation.
Checkpoint `525e78c9f` remains an ancestor. The two production files and final
boundary-test file match all SHA-256 values in the retained evidence receipt.
Unrelated edits and artifacts were left alone.

Publication check: staged diff whitespace validation flags the real soil writer's
trailing spaces on comment lines in `accepted-after-rejection.p1.sol`. Preserve
those exact evidence bytes and their recorded hash; all other staged paths pass
`git diff --cached --check` with that one generated artifact excluded.
