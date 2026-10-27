# HTTP/MCP responsiveness implementation receipt

Implemented by `/root/science_review`; this is implementation evidence, not an
independent review of this agent's own patch. No commit or production deployment.

`server.py` and `mcp/router.py` now await catalog loading/preparation, context
resolution, activation and query execution through Starlette's existing
`run_in_threadpool`. Visibility checks also move because they can acquire Roads
readiness guards. Two private helpers keep each explicit Roads readiness guard's
acquisition, body and release on one worker thread. Complete query execution,
including its second freshness barrier, final authorization and DuckDB executor,
remains one synchronous worker operation.

Authorization ordering, exception handlers, response schemas and synchronous
freshness semantics are preserved. No pool-size, timeout, queue, dependency,
permission or storage changes were added. Public signatures are unchanged.

Validation: `wctl run-pytest tests/query_engine --maxfail=1 -q` reports **199 passed,
2 skipped**. Full output: `http-remediation-query-tests.log`. Existing denied-scope
cases now also assert catalog preparation is never entered.

Six real-handler contention cases cover web schema, MCP catalog, MCP validation,
MCP activation and the web query executor's second freshness barrier. A separate
bounded process owns the actual catalog guard; authenticated MCP requests wait,
an unrelated HTTP request completes before holder release, and the original
request subsequently returns fresh artifact metadata. The sixth case exhausts a test-local AnyIO pool of one token and proves both `/`
and `/health` respond while the guarded request holds that sole token. The
trivial health handler is async and still returns plain `OK` with status 200;
production pool defaults remain unchanged. Activation specifically
retains outstanding receipts, preserving its existing acknowledgment contract.
These are local ASGI/process-lock regressions, not production NFS latency tests.

`http-inline-negative-control.py` deliberately substitutes inline execution for
thread offload and invokes the same schema-handler regression. Its expected exit1
is retained in `http-inline-negative-control.log`: **guard wait blocked the event
loop** after the bounded holder expires. It is a negative-control artifact outside
the normal test tree, not an unresolved product test failure. The ordinary suite
passes with the actual implementation.

Thread offload permits event-loop progress; it neither shortens NFS waits nor
establishes request latency under pool saturation. Independent correctness/security
review and the owning rollout gates remain with the parent/other reviewer.
