# User runs catalog performance on wepp1

## Finding

Measured September 30, 2026, approximately 21:03–21:09 UTC
(14:03–14:09 America/Los_Angeles). The account identified by the operator maps
to user ID 11 and has 805 associated run records. Its catalog data build took
169.56 seconds inside the production web container. Per-run filesystem work
dominates; PostgreSQL queries account for less than one second.

This supports investigating a PostgreSQL catalog projection covering all list
fields. It does not establish a schema or authorize a migration.

## Environment and method

- Host identity: `wepp1`; repository `/workdir/wepppy`, commit `50495bfee`.
- Container: `docker-weppcloud-1`, healthy, UID 1002 / GID 130, matching
  Gunicorn workers. Diagnostics used the installed `wctl` preset.
- Container `/wc1/runs` maps to host `/geodata/wc1/runs`. Legacy run paths
  remain possible through `get_wd`.
- `/geodata` is NFSv4.2 on `nas.rocket.net:/wepp`, with `hard`, 64 KiB
  read/write sizes, `acregmin=3`, `acregmax=30`, `acdirmin=5`, `acdirmax=60`.
  The old zero-directory-cache configuration is not present.
- Local and deployed SHA-256 hashes matched for `routes/user.py`,
  `utils/helpers.py`, `nodb/base.py`, and `templates/user/runs2.html`.
- A separate Python process imported the deployed Flask app and invoked the
  catalog's actual query, row, metadata, sorting, and serialization functions
  under an application context. App import time is excluded.
- Timed one complete 805-run build using the existing ten-worker collector.
  Profiled its second path-resolution pass and a separate sequential sample
  of the account's 20 most recent database run IDs with `cProfile`.
- No cache flush, deployment, service restart, mount change, or database
  migration. Existing helpers retain their normal cache/version behavior;
  `load_detached` calls `ensure_version`, so it is not guaranteed write-free.

Operational entry points:

```bash
ssh wepp1 'hostname; pwd; command -v wctl; uptime'
ssh wepp1 'cd /workdir/wepppy && wctl ps'
ssh wepp1 'findmnt -T /geodata/wc1/runs -o TARGET,SOURCE,FSTYPE,OPTIONS'
ssh wepp1 'cd /workdir/wepppy && wctl exec -T weppcloud timeout 240 python -' \
  < /tmp/profile_user_runs_wepp1.py
ssh wepp1 'cd /workdir/wepppy && wctl exec -T weppcloud timeout 180 python -' \
  < /tmp/profile_user_runs_sample.py
```

Session scripts and raw outputs remain on the diagnostic workstation at
`/tmp/profile_user_runs_wepp1.{py,out}` and
`/tmp/profile_user_runs_sample.{py,out}`; these are temporary, not repository
artifacts. The retained measurements and method are recorded here.

To reproduce the phases, query `_runs_query_for_user(11).all()`, call
`_owner_email_map(runs)`, build each row with `_run_row_from_run`, remove the
database session, then call `_collect_metas_for_runs(rows)`,
`_sort_metas(metas, 'last_modified', True)`, and `app.json.dumps(...)`.
Measure each operation with `time.perf_counter`. The collector supplies its
normal ten threads. For a serial function profile, select 20 runs using
`order_by(Run.id.desc()).limit(20)` and profile `_build_meta` calls in one
thread. Do not start a separate `cProfile` instance for every worker task;
that diagnostic attempt failed as described below.

## Measurements

### Complete account catalog build

| Phase | Wall time |
| --- | ---: |
| PostgreSQL: 805 run records | 0.277 s |
| PostgreSQL: owner records | 0.569 s |
| Row construction / serial `get_wd` calls | 60.487 s |
| Ron and TTL metadata, existing ten-worker pool | 108.203 s |
| Sorting | 0.001 s |
| JSON serialization | 0.018 s |
| Sum | 169.556 s |

The output contained 615 metadata records and approximately 201 KB of JSON.
The collector omitted 190 records under its existing missing/unloadable-Ron
behavior. One captured warning reports a legacy Ron decode failure:
`AttributeError: 'Ron' object has no attribute 'logger'`. The precise missing
versus unloadable breakdown was not separately measured; do not treat all
190 omissions as corruption.

An immediate second row-construction pass took 2.828 seconds. Its profile
contained 1,369 `stat` calls consuming 2.210 seconds and 805 Redis GET calls
consuming 0.545 seconds. This demonstrates strong cache/workload sensitivity;
the first pass was not a controlled cold-cache benchmark.

### Twenty recent runs

Sequential metadata assembly took 16.028 seconds:

| Operation | Cumulative time |
| --- | ---: |
| `Ron.load_detached` | 9.814 s |
| `ensure_version`, included in Ron loading | 8.210 s |
| TTL metadata, separate from Ron loading | 6.211 s |
| File opens, across both paths | 7.499 s |
| File context exits / closes, across both paths | 5.933 s |
| `stat`, across both paths | 2.420 s |

These rows overlap and must not be added together. File open, close, and
stat self-time account for approximately 99% of this sample's wall time.

A subsequent TTL-only pass still took 5.859 seconds for 20 runs. Redis path
GETs took 0.0063 seconds for all 20, and already-cached directory existence
checks took 0.00026 seconds. Small-file operations remain costly even when
directory checks are warm.

### NFS corroboration

A five-second difference of `/proc/self/mountstats` counters during the
investigation showed:

| Operation | Calls | Mean RPC round-trip time | Mean execution time |
| --- | ---: | ---: | ---: |
| OPEN | 28 | 429.6 ms | 429.7 ms |
| CLOSE | 85 | 290.5 ms | 290.6 ms |
| GETATTR | 590 | 20.4 ms | 20.6 ms |
| LOOKUP | 66 | 123.0 ms | 123.2 ms |
| READ | 649 | 408.5 ms | 1,150.4 ms |

READ also averaged 741.9 ms queued; these operations showed no retransmission
delta. Counters cover all users of this host mount, not just the catalog.
They corroborate storage latency but do not isolate a NAS, network, or
competing-job root cause. A short `vmstat` sample showed 84–87% CPU idle.

## Why the page incurs this cost

1. `templates/user/runs2.html`, `buildRunsCatalogUrl`, always sends
   `include_ron_meta=1`. This bypasses the route's 200-run shortcut.
2. `routes/user.py`, `runs_catalog`, retrieves the entire account catalog;
   pagination and filtering happen after the browser receives it. Rendering
   25 rows does not bound server-side metadata work to 25 runs.
3. `_collect_run_rows` resolves every working directory serially before the
   metadata pool starts. `utils/helpers.py`, `get_wd`, checks filesystem
   existence even on Redis cache hits and probes primary/legacy locations
   when necessary.
4. `_build_meta` loads Ron for name, scenario, and readonly status, then reads
   TTL. `nodb/base.py`, `load_detached`, checks READONLY and Ron existence and
   invokes `ensure_version` before checking the cached Ron payload. A Ron
   cache hit therefore does not eliminate filesystem access.
5. `nodb/version.py`, `read_version`, opens `nodb.version`;
   `utils/run_ttl.py`, `_load_payload`, checks and opens `TTL`. `ron.readonly`
   also checks the READONLY marker. NFS open/close latency multiplies across
   the full account.
6. The nominal large-catalog shortcut still resolves directories and reads
   TTL for every row. Disabling `include_ron_meta` alone would also substitute
   run IDs/configs for project names/scenarios and set readonly false.

## Follow-up implications and limits

The evidence supports a database-backed list projection containing project
name, scenario, readonly state, TTL expiration, and an explicit run
availability policy, alongside existing run/config/owner/timestamp fields.
The list request must avoid `get_wd`, Ron loading, and TTL file reads to
remove the measured storage dependency. Moving only names/scenarios leaves
two confirmed expensive paths intact. Map center/zoom merit coverage if the
map endpoint is included later; that endpoint was inspected but not timed.

Before implementation, define updates/backfill/reconciliation for that
projection, TTL freshness, authorization, and treatment of the 190 omitted
records. No choice about exposing missing projects or changing readonly/TTL
semantics was made here. Investigating current NFS latency is a separate
operational follow-up; the measurements do not justify a mount change.

These are application-phase timings, not authenticated HTTPS TTFB or browser
render timings. They exclude proxy/worker queuing, authentication, admin user
directory loading, and the optional map request. The 20-run sample overlapped
part of the full run, adding one serial reader to normal production traffic.
There was one complete full-account observation, not a latency distribution.

The second full-account metadata profiling attempt failed in the diagnostic
process with `ValueError: Another profiling tool is already active` when
concurrent task-level `cProfile` instances were started. Its metadata timings
are discarded; the complete first-pass timings, second-pass path profile,
and sequential sample remain valid. The planned second account was never
profiled. No production code was changed.
