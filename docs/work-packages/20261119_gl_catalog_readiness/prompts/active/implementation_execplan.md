# Load GL query-backed layers after the catalog is ready

Maintain this ExecPlan under the [repository ExecPlan template](../../../../prompt_templates/codex_exec_plans.md) and update the package tracker at each milestone.

## Purpose / Big Picture

Open a GL dashboard whose dataset catalog needs preparation. The map loads, the Layers panel explains the background work, and the main WEPP section appears automatically once results can be queried. Two tabs waiting on the same watershed share a refresh.

## Progress

- [x] (2026-11-20 00:40 UTC) Draft the contract decision and scoped regression plan.
- [x] Ratify the HTTP, authorization and UI behavior and record two independent reviews.
- [ ] Commit the reviewed contract checkpoint.
- [ ] Implement and validate bounded server admission and query waiting.
- [ ] Gate GL result requests and connect the UI status and Retry action.
- [ ] Verify browser and artifact evidence and close review findings.

## Surprises & Discoveries

GL queries can enter catalog freshness handling during both run-context preparation and execution. Coordinating startup alone leaves a late invalidation race. The Nov. 19 proxy timeouts preceded a successful catalog publication. The exact timing within each request was unavailable.

## Decision Log

2026-11-20 00:40 UTC. The operator specified the readiness handshake so GL can wait visibly before requesting results. The draft uses existing RQ admission and polling, with a pending response at the query boundary to handle new invalidations.

## Outcomes & Retrospective

The scaffold records an intended behavior change and a testable acceptance target. Runtime code, executable regressions and canonical promotion are pending.

## Context and Orientation

Query Engine catalogs identify queryable files and their schemas. Producers write refresh receipts after outputs change. `wepppy/query_engine/catalog_refresh.py` publishes metadata and tracks which receipts were incorporated. `wepppy/rq/query_catalog_rq.py` coalesces background admission on the default queue. Query Engine prepares and runs SQL through `wepppy/query_engine/app/server.py`, `app/access.py`, `context.py`, and `core.py`. GL sends most queries through `wepppy/weppcloud/static/js/gl-dashboard/data/query-engine.js` and renders the Layers panel from `wepppy/weppcloud/templates/gl_dashboard.htm`.

## Plan of Work

**M0. Ratify the contract.** Read the [draft decision](../../artifacts/20261120_contract_decision.md) and [scoped tests](../../artifacts/scoped_tests.md). Read applicable nested repository instructions. Record approval of the exact normative matrix, obtain two independent read-only reviews, disposition findings, and commit the reviewed canonical amendments with the checkpoint. Record the ancestor SHA in the tracker before runtime edits.

**M1. Add server readiness and wait behavior.** Add focused failing tests for HTTP access, publication, and admission. Wire the readiness routes through existing authorization and admission. Use a shared scope resolver and distinguish pending metadata work from absent optional data. Make the opt-in query mode stop at either freshness boundary before inline repair. Keep dependency and source validation when handing off to the worker and serving results. The admission and access tests should prove one durable intent for concurrent first use and no side effects on denial.

**M2. Gate GL queries.** Extend the shared client and cover each standard-dashboard call site that can enter the refresh path. Bind status and retry in the Layers panel. Confirm that switching targets discards stale callbacks and keeps the map usable. Rerun the GL client tests including scenario and comparison routing.

**M3. Prove the workflow.** Run the scoped commands and served two-tab replay in the test matrix on a disposable run. Read the published catalog and selected Parquet data, compare the SQL result, and check the rendered overlay. Retain measurements and sanitized request ordering. Obtain separate correctness and security reviews against the bound access and artifact evidence and run the applicable pre-handoff repository gates.

## Concrete Steps and Acceptance

Run commands from the task worktree using the paths and fixture requirements in the [scoped tests](../../artifacts/scoped_tests.md). The first browser trace should show a quick ready or preparing response, no SQL during preparation, and one refresh admission for the same target. The final trace should show successful query responses and the same expected WEPP layer value in both tabs. A late invalidation should return the clients to preparation without creating an inline refresh storm.

## Idempotence and Recovery

Repeated prepares join existing work. Polling reads state. A late receipt survives an earlier job, and Retry rechecks the current scope. Legacy synchronous APIs remain available through their existing contract. Keep authored runtime changes independently revertible from producer and worker fleet changes. Rerun acceptance with fresh disposable fixtures. Production runs are outside replay scope.
