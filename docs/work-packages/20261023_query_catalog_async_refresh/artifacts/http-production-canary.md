# Private production-equivalent HTTP contention canary

**PASS for the bounded canary.** Executed 2026-10-27 00:30–00:31 UTC
(2026-10-26 local date). This is implementation/acceptance evidence produced by
the patch author, not independent final review or production deployment approval.

The candidate HTTP/MCP source ran in fresh private Python interpreters inside
wepp3's existing fork/archive container, uid 1002/gid 130, supplementary group 130.
A separate interpreter in wepp2's existing batch container held the actual shared
catalog guard for 12 seconds per trial. Both use the retained NFS scratch scope
`/wc1/query-catalog-validation/20261026/async-preflight-1719` and existing guard
inode. This is the directed topology previously exhibiting long handoff waits.

| Actual handler | Initial blocking lockf | Complete request | `/` during hold | `/health` during hold |
| --- | --- | --- | --- | --- |
| Web schema | 30.409 s | 31.922 s | 2.826 ms, 200 | 2.585 ms, 200 |
| Authenticated MCP catalog | 30.333 s | 30.861 s | 2.925 ms, 200 | 2.998 ms, 200 |

All unrelated responses occurred before the holder began releasing ownership;
this is HTTP event-loop progress, not merely a separate Python heartbeat thread.
Both blocked requests subsequently returned 200 and the actual `probe.parquet`
entry (`value:int64`, 518 bytes). Pending receipts were drained. A correctly
signed token requesting an unbound MCP run received 404 during each hold.
Source Parquet content, guard inode and live module file hashes were unchanged.

## Isolation and exact source

Candidate files were copied only to an owned private `/tmp/qcat-http-canary-*`
directory (0700 directory, 0600 files), retained for evidence. The private
interpreter executes their compiled code into its imported module dictionaries
using canonical source filenames, preserving `__file__` and template/resource
locations. No live module file was replaced. No service, listener, restart, real
user-project write, queue admission, permission or mount change occurred.

Candidate SHA256:

- server.py: `68f94495468b67069093a6a27adff2f1494bb301b328b360d88b558a65484797`
- mcp/router.py: `550642bebb640ce490124b71a2af5758e927cc34e6f1e203146a97f107d96d31`

Only the private process's slug resolver maps a single canary run ID to scratch;
other names fail. Actual handlers, middleware, JWT validation, native metadata
operations and filesystem guard run normally. Signing configuration uses an
in-memory random test secret only in that process; no secret or token is retained.
Production signing settings were not modified. MCP revocation checks retain the
existing read-only Redis lookup. The web schema endpoint keeps its ordinary
access behavior; authenticated MCP is tested separately.

Retained commands/scripts, staging path, source hashes, per-process events and
stderr are in `http-production-canary-{driver,probe}.py` and
`http-production-canary-logs/`. Consolidated evidence is
`http-production-canary-summary.json`. Both trials and both holders exited zero;
there were no failed attempts in this canary. Earlier local negative-control
failure remains separately retained and deliberately expected.

## Limits

This runs actual ASGI apps in production containers with production identity and
mounts, through an in-process HTTP transport. It does not exercise a live socket,
reverse proxy, deployed worker replacement or existing live traffic. It does not
establish response latency under thread-pool saturation, shorten the NFS wait,
or close namespace/inventory/capacity gates. Within the tested unsaturated case,
it demonstrates the intended correction: unrelated HTTP requests progress while
a freshness-sensitive request still waits for guarded, verified completion.
