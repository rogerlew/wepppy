# Downloader investigation and bounded load test

## Friday failure

Mariana supplied `dressy-kiss`: authenticated wget GET of
`/weppcloud/runs/dressy-kiss/cfg/aria2c.spec` started October 23 at
14:28:34 and returned HTTP 500 at 14:28:36 (client timezone not supplied).
This fast error is not evidence of a fresh request exhausting the 30-second
worker-silence budget. The batch subsequently said "No files to download".
No traceback establishing the exception was recovered.

Run-local exception logs last changed in March. Browse's
BROWSE_WRITE_RUN_EXCEPTIONS_LOG defaults false and was unset in the inspected
container. Its exception handler logs to stderr; Docker stores that in
container-local json-file logs. Browse and Caddy containers were recreated
October 26 around 10:44–10:45 UTC. No retained Friday container logs were found;
legacy Apache/nginx/Redis logs predate this incident. Gunicorn accesslog is
None and Caddy has no request log directive. Deployment force-recreates
containers; this is an observability shortcoming, not an explanation of the 500.

Assuming PDT for the supplied time, the surviving host journal has NFSv4
ID-mapping warnings at 14:25:33 PDT, but no causal traceback or kernel NFS error
at the request. Do not attribute the 500 to these warnings. Today's 32 Redis
BusyLoadingError traces occurred during 10:44 UTC startup, not Friday's request.
Production checkout reflog indicates 052019426 before Monday and 813d912be after;
Friday's removed container image was not independently recovered. Auth route
source did not change between those revisions. Expected credential failures
map to 401/403; unexpected database/Redis/filesystem exceptions can still become
500. Selecting among those possibilities requires the missing traceback.

## Monday HTTP replay and load test

Read-only requests used Roger's existing JWT, not Mariana's identity. This does
not reproduce her exact non-admin authorization context. No token was printed
or saved in evidence. Production services/configuration were not changed.

At 21:45 UTC a native Windows blarhg manifest GET timed out after 55.32 seconds
without an HTTP status. Bounded probes from the operator workspace followed at
21:48–21:50 UTC, with a 5-second connect and 45-second read timeout:

| Route | Requests | Concurrency | Result | Duration |
| --- | ---: | ---: | --- | --- |
| download/README.md | 2 | 1 | all 200, 286 bytes | 0.134–0.164 s |
| browse/ | 2 | 1 | all 200 | 4.725–12.435 s |
| browse/ | 4 | 2 | all 200 | 4.939–7.301 s |
| browse/ | 8 | 4 | all 200 | 5.181–21.563 s |
| aria2c.spec | 1 | 1 | client ReadTimeout, no HTTP status | 45.112 s |

All fourteen listing responses had the same 18,891-byte content hash. No 500,
matching traceback or WORKER TIMEOUT appeared in browse logs during this bounded
load interval. Slow-listing warnings appeared. Initial browse CPU was 115% and
memory 2.726 GiB; a later sample was 231% and 2.736 GiB on the 251.9 GiB host.
Manifest concurrency was not increased after its single-request failure.
HTTP cancellation does not prove its offloaded filesystem scan was canceled.
The native Windows replay and HTTP probes are not before/after timeout tests:
production remained at 30 seconds throughout.

## Current manifest performance lead

The exact historical `_collect_file_specs` function from 052019426 was executed
read-only in the current browse container against dressy-kiss, using current
imported helpers. It enumerated 155,573 entries in 2.679 seconds. This is a
collector comparison, not a full replay of Friday's image or authorization.

Commit e4d28c9ad added `visible(file_path)` to every enumerated file. That helper
uses both lexical and `os.path.realpath` paths to prevent aliases from exposing
unavailable current Roads results. Sampling its first 1,000 real project files
took 1.514 seconds; all were visible. Repeated path resolution is a concrete
additional cost and a likely contributor to Monday's manifest latency. The
sample is not a complete current-collector benchmark. This new check cannot be
assigned as Friday's root cause from the recorded deployment chronology.

Follow-up: preserve Roads admission/alias behavior while reducing repeated
filesystem resolution; validate large non-Roads projects as well as Roads
states. Increasing Gunicorn timeout alone does not remove this per-file cost.
Persistent host-local error logs and sanitized request logs need rotation,
retention and a demonstrated survival check across container recreation.

## Local reversal readback

After the contract checkpoint, the revised collector was executed in a separate
read-only Python process inside the existing production browse container, using
the actual project and runtime identity without replacing loaded service code.
It returned 155,573 entries in 2.192 seconds. Sorted manifest SHA-256:
`95dc887b68297658a669fab8e67211b88aae640700e4d111bed16b2600014a0b`.
This validates collector behavior/performance, not deployment or Friday's cause.

## Culvert correlation follow-up

The culvert worker on wepp2 retained the exact SSLEOFError message at
2026-10-24 18:40:37 UTC and 21:27:20 UTC (11:40:37 and 14:27:20 PDT).
These are worker log emission times. They are October 24, whereas Mariana's
supplied wget transcript explicitly says October 23 at 14:28. Time-of-day
proximity alone does not establish a simultaneous incident.

The closed [JWT renewal package](../../20261026_culvert_jwt_renewal/package.md)
records an expired submit JWT during the October 24 failure and restored
authentication after October 26 rotation. Current deployed client source shows
status polling catches every RequestException, including 401, and retries with
the same token. Its upload function issues one requests.post and raises on a
non-200 response; installed Requests DEFAULT_RETRIES is zero. The error wording
"Max retries exceeded" alone is not a request-count measurement. User-reported
repeated requests can include higher-level retries; their causal connection to
the TLS termination or browse error is not established by the retained logs.

The retained rq-engine culvert-submit log has three 401s on October 26, including
a pair at 16:47:52 UTC during the token-validation work window; these must not be
misidentified as the October 24 incident. No matching culvert path appeared in
retained Caddy error records. No kernel NFS/OOM event appeared in wepp1's October
24 14:20–14:35 PDT window. Client retry policy and persistent server logging are
follow-ups; neither was modified in this filesystem-transparency package.
