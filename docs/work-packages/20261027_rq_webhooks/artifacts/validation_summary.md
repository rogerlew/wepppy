# Implementation validation

Approved ancestor: `6ba2d8d9d`; runtime implementation: `62b272a6c`.
Admission and dispatch remain disabled by default. No production deployment occurred.

## Regression evidence

| Check | Result |
| --- | --- |
| `wctl run-pytest tests/microservices tests/rq tests/profile_recorder` | 3,020 passed, 223 skipped, 219 warnings on final runtime source |
| Disposable Redis/process/API/HTTP/settlement boundary suite | 109 passed; real Redis, worker processes and HTTP boundaries on final runtime source |
| Final admission/recovery/claim regressions | 8 passed |
| Thread/fork lifetime regressions | 6 passed |
| Immediate WATCH without MULTI | 2 passed; ordinary errors and repeated saves preserved |
| Final batched-start/exit/helper/WATCH boundary selection | 10 passed after final worker changes |
| Shared evaluator slice, principal rotation and stale scheduler | 3 passed |
| Worker run ID, directory lock cleanup and startup contract | 31 passed after final worker changes |
| Worker stubtest and test-stub hygiene | Passed |
| RQ dependency graph | Regenerated after line changes; consistency passed |
| Broad exception enforcement and root AGENTS size | Passed |
| Real query-catalog queue regressions | 39 passed |
| `wctl run-pytest tests --maxfail=1` | 6,826 passed, 64 skipped, one preexisting roads provenance failure |

The full-suite blocker is
`tests/roads/test_roads_publication.py::test_published_results_and_sources_are_current_or_explicitly_stale`.
Isolated reproduction also fails. Current `roads.py` SHA-256 is
`bc58f90258044a34bf4614887276735f98256a8cfc5d7d868b68523d01d16978`
and the unchanged checkpoint source has the same digest. The existing evidence expects
`25cbde5447e20110b52e3781a3046b4dda5bc026bc10f64fed68bba150a42201`.
No unrelated scientific provenance was refreshed to conceal this failure.

## Actual workflow and boundary artifacts

- [WEPP submissions](workflow_v6_probe.json) and [readback](workflow_readback_v6.json):
  three actual API submissions, 18 finished jobs and 388 fresh artifacts each;
  exact input/output comparisons, path-normalized logs, typed parquet schemas and
  row multisets; healthy HTTP 204 and three-attempt HTTP 503 exhaustion.
- [Mixed culvert readback](culvert_mixed_parallel_probe.json): 38 finished RQ jobs,
  one successful model and 35 caught domain failures; fresh model parquet and exact
  persisted/received `finished` event bytes. Both workflows deliver after token expiry.
- [TLS/network probes](https_probe.json): actual sender, controlled HTTPS receiver,
  deadline, DNS/IP, certificate, redirect, status, header and retry behavior.
- [Redis restart barrier](restart_restore_probe.json): persisted reservation,
  process-identity change, rejected stale publication and zero stale-armed sends.

The fixture uses owned writable roots, read-only original projects, UID 1000,
GID 993 and umask 022. Final acceptance records six default and four batch workers,
matching the canonical development Compose counts. Earlier one-slot isolation and
failed fixtures remain historical diagnostics; the final parallel mixed case passed.
This is local acceptance, not production deployment or universal configuration coverage. Reproduction and cleanup:
[probe instructions](probes/README.md).

## Performance and review

The [verified-sender backlog measurement](backlog_performance.json) passed both
approved limits: 1,000 transitions per group; p95 75.064 ms disabled versus
75.701 ms tracked, a 0.849% / 0.637 ms increase. The fixture verified four initial
active senders, 11 actual receiver observations during the measured window and
15 persisted attempt audits. Four 5,000-member active evaluation roots exercised
shared Redis pressure. Earlier zero-attempt artifacts are explicitly evaluator-only
diagnostics; idle-only success and failed measurements are not acceptance evidence.

Final real-boundary command (109 passed):

```sh
.venv/bin/python docs/work-packages/20261027_rq_webhooks/artifacts/probes/run_container_tests.py tests/rq/test_webhook_tracking.py tests/rq/test_webhook_http.py tests/rq/test_webhook_settlement.py tests/microservices/test_rq_engine_webhooks.py -q --maxfail=1
```

Host logs: `/tmp/rq-webhook-final-boundaries-generation.log`,
`/tmp/rq-webhook-targeted-complete.log`, `/tmp/rq-webhook-backlog-canonical-pools.log`.
The retained JSON evidence and probe sources are the durable records.

[Correctness review](20261028_correctness_review.md) and [security review](20261028_security_review.md)
report no unresolved high/medium source findings, including the final metadata/start
transaction and containment observation changes. They do not override acceptance.

## Cleanup and scope

[Fixture cleanup](fixture_cleanup.json) confirms no remaining disposable containers,
owned copied data or private fixture credentials. Original projects were read-only
and remain untouched. Runtime source is committed; production deployment and shared
admission/dispatch activation were not performed.
