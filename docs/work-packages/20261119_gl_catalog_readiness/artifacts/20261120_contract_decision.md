# Draft contract decision for GL-CATALOG-01

The operator specified the ready-or-wait handshake and requested this scaffold. The operator instructed execution on 2026-11-20 UTC in response to the scaffold. The canonical amendments define the bounded HTTP, catalog, and UI behavior for implementation. Starting source revision is `a45b7689ebad9574b6ec6860402edf6b1578363a`. This is an intended behavior change following a production incident. The checkpoints for existing synchronous readers currently permit inline refresh.

## Proposed HTTP contract

Requests target `/query-engine/runs/<runid>/<config>`. Reuse canonical run parsing, the query scenario selector and the checked authorization parent. Resolve the same scope for preparation, status and SQL. Use the existing query access rules for automatic preparation and the existing activation rules for a forced refresh. Select the scenario through the POST body and the equivalent GET query parameter. Bind status and admission to the authorized target and current catalog incarnation. Require existing same-origin proof for browser prepare and wait-mode query, including anonymous public readers. Explicit bearer requests retain existing origin and credential checks. Limit automatic preparation to recognized managed layouts. Responses are non-cacheable and expose only the state and a stable safe code.

| Request | Ready | Needs background work | Unavailable |
| --- | --- | --- | --- |
| `POST .../catalog/prepare` | `200` with `state: ready` | `202` with `state: preparing` and `Retry-After` | Typed error for a readonly repair requirement, failed preparation, or unavailable dispatch |
| `GET .../catalog/status` | Same ready body | Same preparing body while work is pending or active | Same typed error when current state fails or cannot progress |
| `POST .../query` with proposed `catalog_mode: wait` | Existing successful query shape | Same `202` response when either freshness check encounters required refresh | Existing auth, Roads, dataset, and query errors retain their meanings |

Proposed safe codes are `catalog_preparing`, `catalog_readonly`, `catalog_refresh_failed`, and `catalog_refresh_unavailable`. Use 409 for readonly repair and 503 for refresh failure or unavailable dispatch. A pending retry remains preparing while bounded backoff can make progress. Existing auth and input status codes take precedence. Finalize the response matrix, polling limits, and recovery semantics during contract review.

## Publication and admission

Preparation observes the current catalog and pending receipts. It joins existing work or records a durable repair request only where necessary. Recheck under the existing nonblocking coordination guard before recording. Register pending scope through bounded Redis dirty-index I/O. The existing scheduler performs RQ admission. This avoids backlog and worker enumeration in HTTP. Polls only read state. Complete tree discovery and refresh run in the worker with source containment anchored to the canonical parent for browser-preparable managed scopes. For managed projects without async capacity, surface the pending or unavailable reason. A readonly scope with a usable catalog can serve queries.

Readiness requires a readable catalog consistent with the relevant publication and receipt state. A valid legacy catalog without a status sidecar can be used subject to normal targeted source checks. A receipt removed after publication, a job marked finished, or a stale status sidecar alone cannot establish readiness. Recheck source path, schema, and identity at the point of query execution. Expected absent optional overlays retain their missing-dataset outcome. Proven stale metadata with no receipt creates or coalesces targeted durable intent for the authorized logical entry before the API returns preparing. Unreadable required sources follow explicit error handling.

Both query barriers must honor wait mode. A query that sees a late invalidation returns preparing before a synchronous repair begins. The client rejoins the shared handshake and replays the query once readiness is confirmed within its wait budget. Legacy query, console, explicit activation, report, and CLI callers retain their synchronous contracts.

## Proposed GL contract

The shared GL query client maintains one preparation and polling sequence per canonical target. All dependent queries for that target wait through it. Cancel superseded UI waiters on scenario change or teardown and discard their late responses. A comparison can wait independently for its other target. Keep the basemap, navigation, and independent layers usable. Announce “Preparing watershed results…” in the Layers panel using a status region. Resume queries automatically when ready. For a terminal failure or exhausted wait, offer a Retry action and keep the status distinct from absent results. Retry rejoins existing maintenance.

## Canonical checkpoint

Promote the wire, authorization, and error rules into the [Query Engine HTTP access contract](../../../schemas/query-engine-http-access-contract.md). Promote background admission, readiness evidence, and wait-mode freshness rules into the [catalog refresh contract](../../../schemas/query-engine-catalog-refresh-contract.md). Put the user-visible state transitions and scope rules in a GL domain contract under `docs/ui-docs/contracts/` and link it from the [GL guide](../../../ui-docs/gl-dashboard.md). Amend the [CSRF contract](../../../schemas/weppcloud-csrf-contract.md) for the new write-capable browser operations and apply existing [RQ response rules](../../../schemas/rq-response-contract.md).

The proposal avoids sending multiple requests into inline refresh and preserves current callers through opt-in query semantics. It adds no scientific data or result schema. Review the new admission surface for unauthorized inspection, scope substitution, resource amplification and refresh-guard contention. Ratify the exact delta, disposition two independent read-only contract reviews, and commit the checkpoint and canonical amendments before runtime edits. Use the [scoped tests](scoped_tests.md) as the regression evidence plan.
