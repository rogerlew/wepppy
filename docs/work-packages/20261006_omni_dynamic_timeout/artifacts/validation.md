# WRT-02 validation

## Revisions

- Contract checkpoint: `3c8c9c622ce722180c837e641b6d3bfbe9d67df3`
- Implementation candidate: `adff42d6d9e38f561d41cc681e89f3386ef888c0`
- Deployment revision: not applicable; this package does not deploy.

## Automated gates

| Gate | Result |
| --- | --- |
| `wctl run-pytest tests/rq/test_watershed_timeout.py tests/rq/test_omni_rq.py -q` | Pass: 97 tests |
| Related RQ dependency/boundary tests | Pass: 331 tests, 26 skipped |
| `wctl run-stubtest wepppy.rq.omni_rq` | Pass |
| `wctl check-test-stubs` | Pass |
| `wctl check-rq-graph` | Pass; generated changes are source-line-only |
| Changed broad-exception enforcement against checkpoint | Pass; one file scanned, net delta `+0` |
| Package, contract, ADR, README, and catalog documentation lint | Pass |
| `git diff --check` | Pass |
| `wctl run-pytest tests --maxfail=1` | Qualified: 10,122 passed and 126 skipped before unrelated catalog latency failure |
| Isolated failing catalog benchmark | Pass: 1 test in 153.90 seconds |
| Unexecuted functional tail, catalog latency tests deselected | Pass: 143 tests; 4 deselected |

## Real Redis serialization

The package-local `verify_live_rq.py` harness ran with candidate
`adff42d6d9e38f561d41cc681e89f3386ef888c0`. It used a UUID-scoped disposable
queue and fetched the jobs back through RQ plus `get_wepppy_rq_job_info`.
`live_rq.json` records:

- four continuous scenario/contrast leaves at 50,400 seconds for the
  production-shaped 500-year, 1,908-hillslope workload;
- exact WRT-01 metadata on those leaves;
- compile/finalizer jobs remaining at 43,200 seconds without WRT metadata;
- unchanged scenario/contrast dependency order and parent `job_info` lineage;
- `graphs_executed: false` and `cleanup_verified: true` after deleting all nine
  disposable jobs and their queue.

## State and failure coverage

Focused tests cover continuous and single-storm helpers, scenario and contrast
leaf wiring, empty and fully skipped work, malformed required workload before
parent/Redis/rerun mutation, fixed non-leaf allowances, batching, and dependency
lineage. Existing queued jobs are not mutated.

## Evidence boundary

The live harness manually assembles the expected graph. Together with the
coordinator tests this is accepted split proof of coordinator wiring and real
RQ serialization/topology. It does not execute model leaves or validate
scientific outputs. Production-equivalent execution, subprocess behavior,
queue observation, and output review remain gates for the separately authorized
wepp1 deployment and retry.

## Completion claim

Implementation is locally validated with a qualified broad gate. The full suite
did not pass cleanly: `test_actual_save_notification_latency_and_database_refusal`
failed when baseline/catalog p95 timings were already 1.70/2.43 seconds, passed
alone, and failed again after neighboring catalog tests at 2.18/3.03 seconds.
`test_marker_notification_latency_without_prior_sql_mirror[readonly]` then
showed a 2.59-second catalog p95 against the same 50 ms delta threshold. The
remaining functional slice passed with four latency benchmarks deselected. This
test-isolation/performance exception is unrelated to changed WRT-02 files and is
not a clean full-suite pass. No deployment, production recovery, or
incident-resolution claim is made.
