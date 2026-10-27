# Independent HTTP/MCP remediation review

## Findings and verdict

**PASS for the bounded HTTP/MCP implementation.** No unresolved correctness or
security finding was identified in the reviewed diff. This does not clear the
inventory, fleet capacity, legacy-role or production enablement gates.

Reviewer: `/root/inventory_security_review`, 2026-10-27 UTC. The reviewer did not
author the implementation or tests. Security triage remains **high** because
public handlers now execute filesystem/query work across a thread boundary.
The [implementation receipt](http-remediation-implementation.md) is author
evidence; the independent focused rerun below corroborates its principal claim.

## Scope and source identity

Reviewed `wepppy/query_engine/app/server.py`,
`wepppy/query_engine/app/mcp/router.py`, their underlying freshness/query/feature
access/Roads guard code, and `tests/query_engine/test_mcp_router.py`.

| File | Reviewed SHA256 |
| --- | --- |
| `server.py` | `3d7c18ad022d4e582fb6e74bc43ec96a1fe2c5ba9a2db9fe2185b77e7377a191` |
| `mcp/router.py` | `550642bebb640ce490124b71a2af5758e927cc34e6f1e203146a97f107d96d31` |
| `test_mcp_router.py` | `c3fac6a93e2564f9a0f153b7ca1c3cbc31b38f9d1bdb393b95afdd8949cff1c2` |

## Boundary checks

- **Authorization before work:** MCP scope and run binding precede offloaded
  catalog work. Root checks preserve existing ordering; `_resolve_run_entry`
  performs its root check before metadata loading within the same worker call.
  Validation/execution retain dataset checks before targeted freshness work.
  Denied validation/execution scope tests explicitly fail if preparation runs.
- **Fresh authorization:** `run_query` refreshes its context, invokes the retained
  authorization callback against the refreshed catalog, then plans and reads
  data. Both web and MCP callers preserve this callback. Thread offload does not
  replace refreshed source authorization with a previously checked locator.
- **Guard ownership:** Each explicit Roads preflight enters, validates and exits
  `current_read` within one synchronous helper. Visibility filtering holds its
  own complete guard lifetime on a worker thread. No guard is acquired on the
  event loop and released on another thread. Core query execution retains its
  complete Roads source guards while rows are read.
- **DuckDB and context:** The whole `run_query` operation, including its second
  freshness barrier, authorization, plan construction, connection creation/use
  and result materialization, executes in one worker call. `DuckDBExecutor`
  creates a context-scoped connection inside `execute`; the patch introduces no
  shared connection or concurrent use of one request's context. Sequential
  awaited preparation/resolution calls do not share a held connection or guard.
- **Exceptions and disclosure:** Awaits stay inside the existing exception
  handlers. HTTP authorization exceptions remain distinct; Roads 409/no-store,
  MCP first-use/catalog-missing behavior and existing response/error fields are
  preserved. No new raw error, path, token or job payload is added. Existing
  defensive broad handlers were not widened by this change.
- **Scope containment:** No new endpoint, queue, dependency, pool size, timeout,
  credential, mount or privilege is introduced. Native GIL release remains a
  prerequisite; thread offload is not claimed to fix a GIL-holding scanner.

Valid states considered: existing/current catalog, pending receipt, never-indexed
MCP catalog, absent run, invalid payload, denied scope/run binding, inaccessible
physical dataset source, and unavailable Roads results. Existing query-engine
coverage supplies the broader behavior matrix; the independent rerun targets the
changed concurrency and denied-scope boundaries. No exhaustive state claim is made.

## Independent validation

Using the `wepppy-tester` skill and canonical Docker wrapper:

```text
wctl run-pytest tests/query_engine/test_mcp_router.py -q \
  -k 'catalog_contention_keeps_http_loop_responsive or validate_query_requires_scope or execute_query_requires_scope' \
  --maxfail=1
```

Final-source result: **8 passed, 36 deselected**, 13.96 seconds. Retained output:
[http-remediation-independent-tests-final.log](http-remediation-independent-tests-final.log).
The earlier seven-case run remains separately retained.

The six contention cases invoke actual web schema/query and authenticated MCP
catalog/validation/activation handlers. A separate bounded process holds the
actual catalog guard; an unrelated HTTP request completes while the original
request remains blocked. After release, the request succeeds and actual catalog
metadata reflects the Parquet source. Activation preserves its preexisting
receipt acknowledgment semantics. Auth uses test JWT configuration; the fixture
stubs revocation Redis, so this is not live identity-provider/revocation parity.

The retained author negative control was inspected: deliberately inline
execution fails specifically at `guard wait blocked the event loop`, rather than
an import or fixture error. It demonstrates that the regression can detect the
original scheduling failure. The author's broader `tests/query_engine` result
is separately recorded as 198 passed/2 skipped; it was not repeated here.

## Residual limits and sign-off

The final follow-up changes the pure `OK` health handler to `async def`, retaining
its response while avoiding use of the shared worker pool. The added real-guard
case limits only its test event loop to one worker token, proves that token is
occupied, then verifies both `/` and `/health` return before guard release. This
closes the identified health/pool starvation exposure without changing production
pool size. The test does not shorten NFS waits or establish broad request latency
under production saturation.

No medium/high risk acceptance is requested. No production operation or
implementation edit was performed by this reviewer. Independent security and
correctness disposition for this bounded patch: **PASS**; production release
sign-off remains with the package owner after the other gates.

## Production-equivalent evidence readback

Independently inspected both author canaries, their probe/driver code and
structured results. The initial [canary](http-production-canary.md) remains
evidence for its original source version. The final
[one-token canary](http-health-canary.md) and
[structured readback](http-health-canary-summary.json) match the final server
`3d7c18ad022d4e582fb6e74bc43ec96a1fe2c5ba9a2db9fe2185b77e7377a191`
and router `550642bebb640ce490124b71a2af5758e927cc34e6f1e203146a97f107d96d31`
reviewed here.

Actual ASGI schema and authenticated MCP handlers ran under uid 1002/gid 130 on
wepp3 while wepp2 held the real NFS guard. The canary interpreter verified its
sole worker token was borrowed. During 30.11/30.50-second guard waits, `/health`
returned 200 in 1.52/2.63 ms and `/` returned 200 in 3.95/4.06 ms. The original
requests subsequently returned the actual Parquet entry with zero pending
receipts. Unbound-run requests returned 404; stable guard inode, live module
hashes and source contents remained unchanged. The production pool size was
unchanged. This closes the scoped production-equivalent responsiveness check
for the final source hashes.

Private interpreter overlays, one scratch-only resolver, an in-memory JWT
secret and no listener correctly limit this claim. It proves behavior under the
production identity and shared mount; it does not test the deployed listener,
reverse proxy, normal production worker-pool saturation or fleet capacity.
No additional test or production action was performed by this reviewer during
the final evidence readback.
