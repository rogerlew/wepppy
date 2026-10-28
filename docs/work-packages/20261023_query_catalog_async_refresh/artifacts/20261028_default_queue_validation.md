# Default-worker routing validation, 2026-10-28

Contract checkpoint: `0e6302905`, standalone ancestor before runtime edits.
Source baseline: `2fff37a75`. Production deployment/general async unchanged.

## Implementation and compatibility

Refresh, inventory, retry and pilot paths select default. Worker capability
includes queue identity; admission watches default registrations and execution
checks the default origin. The pilot expects the existing twelve default workers.
The seven-job cap and all other bounds are unchanged.

Historical ledger/pause keys remain intact, including uncertain/active permits.
Missing-ledger bootstrap checks both queues and their active registries. Legacy
batch pilot manifests remain readable; resume/new admission rejects them.
The new configuration's inventory recovers durable old receipts without deleting
old Redis discovery history. No project schema or model-output changes.

## Focused validation

Via `wctl exec weppcloud env`, with a disposable, no-TCP/no-persistence Redis
server exposed through an owned Unix socket (never Compose/production Redis):

```text
BATCH_BOUNDARY_TEST_REDIS_SOCKET=/workdir/wepppy/.git/qcat-default-test/redis.sock
PYTHONPATH=/workdir/wepppy /opt/venv/bin/pytest
  tests/rq/test_query_catalog_rq.py tests/rq/test_query_catalog_inventory.py
  tests/rq/test_query_catalog_pilot.py tests/rq/test_query_catalog_disclosure.py
  tests/tools/test_query_catalog_pilot_cli.py -q --maxfail=1
```

Final source: **129 passed**, no skips, 36.91 seconds. This includes real Redis
backlog isolation/default deferral, missing-ledger checks for both queues, old
configuration rejection and receipt rediscovery, legacy permit retention, actual
worker rejection of invalid queue/configuration authority before catalog publication,
and existing kill/retry/cancellation/disclosure/artifact tests.
Initial test attempts exposed missing container redis-server and stale test
worker-count/queue doubles; corrected harness, not bypassed failures.

## Live local job-tree and artifact acceptance

A separate manual check used the normal forking `WepppyRqWorker`, the disposable
server's independent DB 2 and a temporary owned project. Both inventory and
refresh executed on default while an ordinary batch job remained queued.
`wepppy.rq.job_info.recursive_get_job_details` reported finished sanitized trees;
raw catalog entries included the source CSV and zero receipts remained.
[Retained readback](20261028_default_queue_live_readback.json).

The harness explicitly disabled project-commit database integration with matching
legacy/timestamp-only modes; it did not access production projects or databases.
An initial harness run lacked those matching modes and stopped before worker
startup; the corrected run passed. This is local workflow evidence, not production
identity/mount/fleet parity or whole-fleet capacity acceptance.

## Independent review

- Correctness reviewer: PASS, no blocking runtime findings. Two CLI queue doubles
  updated to include default name/key before final focused validation.
- Security reviewer: [PASS](20261028_default_queue_security_review.md), no blocking source findings. Suggested legacy execution
  rejection regression added and passed. Its independent invocation skipped 12
  tests without the socket; that is not counted as runtime passing evidence.

## Broad validation, gates and rollout

RQ graph, changed broad-exception enforcement, documentation lint and whitespace
checks passed. Code-quality observation completed; before commit it reported no
committed changed-file deltas (not evidence of a complexity improvement).

Full Python command used the same disposable Redis environment and
`PLAYWRIGHT_BROWSERS_PATH=/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers`
through `wctl exec weppcloud env`, with `/opt/venv/bin/pytest tests --maxfail=1`.
Result: **1 failed, 6,810 passed, 61 skipped**, 2,733.31 seconds. It stopped at
`tests/roads/test_roads_publication.py::test_published_results_and_sources_are_current_or_explicitly_stale`
with `Unreviewed source drift`. This is not a full-suite pass, and the unexecuted
remainder is not claimed covered by this sweep.

The failed assertion compares retained Roads staleness metadata to the Roads
source hash. Recorded expected current hash is
`25cbde5447e20110b52e3781a3046b4dda5bc026bc10f64fed68bba150a42201`; actual
`roads.py` hash is `bc58f90258044a34bf4614887276735f98256a8cfc5d7d868b68523d01d16978`.
`git show` confirms the actual hash is identical at starting revision `2fff37a75`,
checkpoint `0e6302905`, and the working tree. The failing test/evidence were not
modified here. The earlier Roads input-form commit therefore already has this
provenance mismatch; this task does not rewrite its scientific evidence.
The full 129-test catalog-focused suite completed separately before the sweep.

The disposable Redis server was shut down with NOSAVE after validation; all
manual scratch project directories were removed by their owning harness.
Production migration requires old maintenance drain, full canonical participant
deployment and default-worker artifact/delay acceptance; no production action
was taken in this task. Unrelated concurrent webhook documentation is excluded.
