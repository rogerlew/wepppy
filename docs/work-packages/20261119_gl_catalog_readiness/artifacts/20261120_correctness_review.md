# GL catalog readiness correctness review

Independent reviewer `contract_correctness` accepted the reviewed fixes on
2026-11-20 UTC. The scope is GL-CATALOG-01 on `task/gl-catalog-readiness`
after contract checkpoint `fdba3295c`. The canonical contracts define ready,
preparing, unavailable, and required source verification.
[GL contract](../../../ui-docs/contracts/gl-catalog-readiness-contract.md) ·
[HTTP contract](../../../schemas/query-engine-http-access-contract.md#gl-catalog-readiness-handshake)

| Finding | Resolution and evidence |
| --- | --- |
| First-open contention could fail the second tab | Nonblocking busy response carries polling guidance and the shared browser check retries preparation. Real lock test, Redis two-request test and two-tab browser smoke passed. |
| Scheduler could remove a racing registration | Recheck durable receipts after removing a dirty index entry. Real Redis regression injects the interleaving. |
| Query could report ready JSON when a publisher won the race | Both readiness outcomes use typed 202 for a waiting SQL request. Real stale-Parquet query returns 202, then SQL returns the updated values after publication. |
| Old scenario responses or errors could affect the new view | Scenario generation rejects superseded work, and scoped failures clear on Retry or target switch. Client regression and direct reviewer replay passed. |
| Retry could leave discovery stopped, reuse empty graph results, or miss saved scope | Retry reloads affected layers and graphs through the normal paths. Catalog errors bypass empty graph caches. Saved scope waits for usable data. Same-page browser recovery passed. |

## Scope and readback

The [scoped test matrix](scoped_tests.md) distinguishes runtime state from input
coverage, including missing and malformed catalogs, usable older catalogs,
absent optional data, contention, and unavailable preparation. Expected pending
work is visible while the map stays usable. A terminal or timed-out wait offers
Retry. Ordinary dataset absence retains its prior behavior.

Two concurrent HTTP prepares against disposable Redis coalesced one durable
receipt and one RQ refresh. The actual scheduler, worker, catalog reader, and
DuckDB query ran. SQL returned 17 from the existing fixture and 23 and 24
after a Parquet replacement without a producer receipt. The consumer verified
the selected dataset before execution.

The served Playwright fixture used actual Flask GL, Query Engine, Redis, NFS
storage, and a background publication triggered after both tabs received 202.
Both tabs held queries during the visible wait, then read 10 mm for hillslope
11 and drew the runoff layer. The Retry test injected one unavailable response
and then used actual readiness and query responses. Admission and worker
execution were exercised in the separate real RQ regression. The browser
fixture provided synthetic hillslope geometry and summary files. Missing
optional channel and other outputs were outside the fixture.

The standard dashboard's base-event query now uses the shared client. The
standalone combined viewer uses its own HTTP client and retains its separate
synchronous discovery path. Flow-duration session provenance retains its
existing contract. The highest supported claim is locally validated with a
disposable NFS browser replay. Fleet rollout and incident-run acceptance are open.
