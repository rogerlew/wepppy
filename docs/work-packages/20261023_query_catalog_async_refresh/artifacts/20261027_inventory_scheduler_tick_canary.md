# Full-batch scheduler runtime canary

Disposition: **PASS for the measured 25-scope scheduler boundaries**. This is
metadata/admission overhead evidence, not a production fleet service benchmark
or proof of the complete-cycle target. [Exact evidence](20261027_inventory_scheduler_tick_canary.json)
contains candidate/harness hashes, actual tick results, queue counts, catalog
hashes, source metadata readbacks and cleanup checks.

## Method and measurements

Executed on `wepp1`, `docker-rq-worker-batch-1`, UID 1002/GID and groups 130.
Each wave used a unique private queue/configured namespace and 25 owned tiny
CSV projects below `/wc1/query-catalog-validation/20261026/`. Candidate modules
were process-local imports from `/tmp`; their hashes match the workspace.
Installed sources, live configuration, real projects and production `batch`
were untouched. Normal forking RQ workers executed discovery; job timeouts
remained 3600 seconds. Admission and discovery-drain limits remained 25 and 100.

Tick timers surround `reconcile_query_catalogs` only. They **exclude worker
execution and the 30-second scheduling cadence**; ticks were invoked directly
for this bounded diagnostic. Each admission, recheck and readonly-skip row below
considered 25 scopes; the completed-cycle no-op considered none.

| Wave and tick | Seconds | Pending scopes after | Queue after | Outcome |
| --- | ---: | ---: | ---: | --- |
| First: new admission | 11.668846 | 25 | 25 | 25 new refresh jobs |
| First: completion recheck | 0.623231 | 0 | 0 | 25 completed scopes retired |
| First: completed-cycle no-op | 0.002755 | 0 | 0 | No new work |
| Second: new admission | 6.716834 | 25 | 25 | 25 new refresh jobs |
| Second: queued recheck | 0.790840 | 25 | 25 | Existing 25 jobs coalesced |
| Second: readonly skip | 0.135262 | 0 | 0 | 25 readonly scopes excluded |

The queued recheck's `admitted=25` is the existing return convention for
coalesced job identifiers; queue readback stayed at the same 25 jobs. It does
not mean 25 additional jobs were created. The first wave's separate sequential
25-job worker phase took 132.111483 seconds and is not included in the tick
numbers or offered as a representative scientific-project service rate.

The second wave measured the actual pending-list JSON at **3375 bytes for 25
items**; the complete cursor was 3815/3816 bytes around admission/recheck.
Readonly retirement reduced the pending list to 2 bytes and cursor to 477
bytes. These values describe these scratch path lengths and a 25-item backlog,
not the cost of serializing a full-fleet pending list. First-wave pending-list
size was not captured before retirement. Differences between the two admission
samples are retained; neither is a worst-case latency bound.

## Output correctness and readonly distinction

The first wave completed all 25 refresh jobs. Direct readback verified each
catalog indexed `values.csv`, source size and modification time matched its
catalog entry, the source's fixture value matched the project number, and all
25 scopes had zero pending receipts. All 26 jobs including inventory finished.

The second wave deliberately avoided another service benchmark: after measuring
the queued recheck, the harness wrote owned `READONLY` markers and used normal
RQ cancellation for the 25 private queued jobs. The readonly tick skipped these
scopes. **All 25 receipts remain retained and no catalogs were generated.** Its
inventory-cycle completion state is readonly exclusion, not reconciliation or
an acknowledgment of those receipts. This evidence is distinct from the first
wave's successful catalogs.

## Retention and cleanup

Protected scratch directories are `qcat-admission25-20261027T020802Z` and
`qcat-recheck25-20261027T021200Z` below the validation root. Each retains
`result.json`, `run.log`, exact candidate modules, its harness and `finalize.py`.
Host paths use `/geodata/wc1` in place of `/wc1`.

Both workers registered death; both private queues had zero queued/started jobs
and were unregistered. Independent process readback found both diagnostic parent
PIDs absent. Only each wave's owned configuration, scratch-scope, queue/worker
and job keys received one-day expiry. Scratch artifacts and the second wave's
unacknowledged receipts remain available for review. External diagnostic
deadlines were 300 seconds for the first wave and 180 for the second; neither
fired. No production job timeout or cadence was changed.
