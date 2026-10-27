# Health responsiveness with the worker pool occupied

**PASS for local regression and private production-equivalent canaries.**
Implementation evidence by the patch author; independent final review remains
with the owning reviewers. No commit or production deployment.

The constant `/health` handler is now async, preserving plain `OK` and status 200.
It no longer needs a worker-pool token to report health. No production pool size
or other configuration changes were made.

`wctl run-pytest tests/query_engine --maxfail=1 -q`: **199 passed, 2 skipped**.
The added actual-handler test configures one token only inside its own event loop.
A schema request blocked on a separately held actual catalog guard occupies that
sole token; both `/` and `/health` must finish before guard release. The test also
checks that the pool is actually occupied, rather than inferring saturation from
a sleeping coroutine. Full output remains in `http-remediation-query-tests.log`.

The production-equivalent repeat uses the same private overlay isolation as
`http-production-canary.md`: actual uid 1002/gid 130, existing containers and NFS,
wepp2 holding the guard while wepp3 executes actual ASGI handlers. Only the private
canary interpreter's AnyIO pool is limited to one token. That token is verified
occupied before measuring unrelated requests. No live listener or service is
involved. Random process-local JWT signing and the single scratch slug mapping
remain explicitly canary configuration.

| Handler | Blocking lockf | Complete request | `/` during hold | `/health` during hold |
| --- | --- | --- | --- | --- |
| schema | 30.107 s | 30.439 s | 3.952 ms | 1.520 ms |
| mcp | 30.501 s | 31.420 s | 4.056 ms | 2.629 ms |

Both ordinary requests returned 200 while the guard was still held, despite the
sole worker token being occupied. Signed requests for an unbound run returned 404.
The freshness-sensitive requests later returned 200 with the actual Parquet entry
and zero pending receipts. Source asset contents, live module file hashes and
stable guard inode were unchanged; all four canary processes exited zero.

Exact candidate SHA256:

- wepppy.query_engine.app.mcp.router: `550642bebb640ce490124b71a2af5758e927cc34e6f1e203146a97f107d96d31`
- wepppy.query_engine.app.server: `3d7c18ad022d4e582fb6e74bc43ec96a1fe2c5ba9a2db9fe2185b77e7377a191`

Structured evidence: `http-health-canary-summary.json`. Scripts and raw logs:
`http-health-canary-{driver,probe}.py` and `http-health-canary-logs/`. The earlier
unsaturated canary and its original scripts/logs remain retained separately.

This demonstrates health and event-loop progress with no free worker token in the
bounded test. It does not reduce NFS latency, establish throughput under forty
concurrent requests, or close namespace/inventory/capacity gates. The ASGI
transport uses no production socket or proxy. The only production filesystem
writes are retained task scratch/private temporary files.
