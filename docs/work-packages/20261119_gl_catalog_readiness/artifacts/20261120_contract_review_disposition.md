# GL-CATALOG-01 contract review disposition

Both independent reviewers accepted the amended checkpoint on 2026-11-20 UTC. This records design acceptance. Runtime evidence remains due under the execution plan.

| Review | Finding | Disposition |
| --- | --- | --- |
| Correctness | High. Receipt-free stale data could loop between ready and pending. | Record or coalesce a verified targeted receipt before returning pending, or return an explicit failure. The tests change an actual Parquet source and check the replayed query. |
| Correctness | Medium. Pending status, missing worker capacity, and old failures needed precise handling. | Polls are read-only. Published state and viable current work control the result. Managed repair without capacity has a typed result and the browser uses a finite wait. |
| Correctness | Medium. Retry could leave startup discovery stopped. | Retry reloads the affected discovery and results. The two-tab test includes recovery on the same page. |
| Correctness | Medium. Lock contention and disabled deployment settings needed coverage. | Use a nonblocking guard, define valid current catalog behavior even without async capacity, and prove worker/configuration parity before deployment. |
| Security | High. A worker could lose the HTTP request's source scope. | Require the worker to resolve the exact managed authorization parent and apply the same source policy. Exercise permitted inherited inputs and sibling rejection with a real worker. |
| Security | Medium. General scenario selectors could schedule arbitrary descendant scopes. | Limit asynchronous repair to recognized managed scopes, authorize first, and require same-origin proof for anonymous and cookie browser writes. |
| Security | Medium. Existing RQ admission can traverse the queue and locks can wait. | HTTP registers intent through bounded Redis dirty-index I/O. The existing scheduler performs admission. The request uses a nonblocking catalog guard. |
