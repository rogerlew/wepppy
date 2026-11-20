# GL Dashboard catalog readiness handshake

**Status:** Implemented and locally validated. Fleet rollout pending.

**Amendment:** GL-CATALOG-01

**Started:** 2026-11-20 00:40 UTC

When the catalog of available datasets needs a refresh, GL should show that results are being prepared, keep the map usable, and load query-backed layers when Query Engine confirms readiness. On Nov. 19, 2026, wepp1 logged 21 GL query requests for one watershed hitting the 180-second proxy timeout. A catalog published two seconds after the last timeout. The WEPP Parquet outputs already existed, and a direct runoff aggregation took 48 ms. Later Query Engine errors confirmed overlapping refresh attempts. The original requests lack stage timings.

The package covers the run-scoped readiness handshake, the GL client wait and status message, and the opt-in query response that handles invalidation after readiness. The supported targets are ordinary runs, Omni scenarios/contrasts, and batch paths that use the same GL query client. Audit direct GL Query Engine calls, including the base-event path and combined viewer, against the same failure signature. Route confirmed peers in the standard dashboard through the shared client. Record confirmed peers in separate surfaces and bring any scope expansion through the contract review. Flow-duration provenance and its existing stale-session behavior retain their own contract.

Reuse Query Engine HTTP, existing RQ/default-queue admission, scheduler recovery, and catalog filesystem coordination. The complexity budget covers the small HTTP handshake and GL changes. Scientific outputs, roles, queue topology, proxy timeout, and explicit activation are outside the change scope. The [asynchronous catalog package](../20261023_query_catalog_async_refresh/package.md) provides prior evidence and owns fleet-level refresh rollout.

Security impact is **high** because browser-reachable endpoints can inspect and enqueue work for a run. Query Engine access and RQ maintenance reviewers must verify scope binding, same-origin handling, public read-triggered preparation limits, and sanitized status. A dedicated security review and independent correctness review are required before closure.

Success means two GL tabs share one refresh for the same run, send no result queries while waiting, and display WEPP overlays backed by the newly published catalog. Browser, HTTP, and artifact evidence must also show recovery from late invalidation and a bounded, recoverable failure state. Retain preparation latency, refresh attempts, query fan-out, and pending or failure duration for the controlled replay. Repeated 504s, multiple admissions per scope, or silent disappearance of available layers fail acceptance. Production rollout and observation require separate evidence.

- [Draft contract decision](artifacts/20261120_contract_decision.md)
- [Scoped test matrix](artifacts/scoped_tests.md)
- [Execution plan](prompts/active/implementation_execplan.md)
- [Correctness review](artifacts/20261120_correctness_review.md)
- [Security review](artifacts/20261120_security_review.md)
- [Tracker](tracker.md)
