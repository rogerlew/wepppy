# F1 failure-class assessment

**Status**: Local implementation validated; environment and production dispositions below

**Broken shared assumption**: a value that resolves to a run directory is not
proof that the caller may access that run or that the directory came from an
approved identifier/root.

## Search Boundary

Reviewed query-engine HTTP route registration and handlers, route-to-path
resolution, feature/root guards, shared browse/RQ authorization, run-session
cookie minting, wepp1 Caddy ingress, production Compose mounts, canonical
composite-runid rules, and current query-engine route tests. MCP was inspected as
an adjacent independently authenticated surface.

Excluded from this F1 class: browse file rendering, D-Tale, status/preflight
WebSockets, error-body traceback disclosure, Bootstrap, dependency advisories,
and test-support routes. They correspond to separate audit findings.

## Endpoint Consumers

| Consumer | Current dependency path | Current state | Required evidence | Disposition |
| --- | --- | --- | --- | --- |
| `GET /runs/{target}` | resolver -> group-only guard -> context/catalog | Ordinary private run not authorized | Private/public HTTP matrix and no-write hashes | Confirmed defect |
| `GET /runs/{target}/schema` | resolver -> group-only guard -> context/catalog | Same | Schema denial/content tests | Confirmed defect |
| `GET /runs/{target}/query` | resolver -> group-only guard -> auto-activate/template | Same | Console denial and owner browser test | Confirmed defect |
| `POST /runs/{target}/query` | resolver -> group-only guard -> query | Same; can expose records | Query result and denial matrix | Confirmed defect |
| `GET /runs/{target}/activate` | resolver -> group-only guard -> force refresh | State-changing GET | 405 and no-write evidence | Confirmed defect |
| `POST /runs/{target}/activate` | resolver -> group-only guard -> force refresh | Missing ordinary-run auth | Auth/scope/origin/CSRF matrix | Confirmed defect |
| `_log_exception_details` | resolver -> append `exceptions.log` | Can follow untrusted target after failure | Denied-request hash/absence test | Confirmed defect |
| `/mcp/*` routes | MCP middleware and scoped route guards | Separate token layer observed | Existing MCP suite plus focused non-regression | Unresolved |

## Run and Deployment Variants

| Variant | Resolution/authorization dependency | Risk | Evidence needed | Disposition |
| --- | --- | --- | --- | --- |
| Ordinary primary run | `/wc1/runs/<prefix>/<runid>` plus DB/public state | Direct F1 exposure | Anonymous/unrelated/owner/public cases | Confirmed defect |
| Legacy ordinary run | `/geodata/weppcloud_runs/<runid>` | Fix may false-deny or cross root | Direct legacy fixture | Unresolved |
| Playback clone override | configured playback run root | Broad root may escape production run policy | Real configured fixture | Unresolved |
| Batch base/run | batch root plus feature access | Existing special guard may be retained/regressed | Public base and entitled/denied tokens | Unresolved |
| Culvert run | culvert root plus feature access | Existing special guard may be retained/regressed | Entitled/denied tokens | Unresolved |
| Simple Omni child | parent run plus `_pups/omni` | Child must inherit parent, not become separate tenant | Scenario/contrast parent matrix | Unresolved |
| Batch Omni child | batch parent plus `_pups/omni` | Nested identifier and feature policy | Direct nested matrix | Unresolved |
| Profile tmp/fork/archive | configured profile roots | Service workflow may lack browser owner | Actual service-token workflow | Unresolved |
| wepp1 Caddy route | public `handle_path /query-engine*` | Makes source defect reachable | Rendered config and controlled HTTP | Confirmed defect |
| Dev/forest Caddy route | equivalent public prefix in test environment | Required production-equivalent gate | Real Caddy matrix | Unresolved |

## Hostile Target Variants

| Input/state | Expected disposition | Direct evidence |
| --- | --- | --- |
| Absolute path | Reject before existence/read | Pending |
| Root-relative path synthesized by prefix | Reject before existence/read | Pending |
| `.` / `..` / traversal | Reject before resolution | Pending |
| Encoded slash/backslash/NUL | Reject at route/parser boundary | Pending |
| Extra path segments | Reject unless canonical config grammar allows | Pending |
| Symlinked run root outside approved root | Reject after realpath containment | Pending |
| Symlinked dataset outside authorized run sharing contract | Reject before query | Pending |
| Redis WD cache points outside identifier root | Reject after cache result | Pending |
| Missing run | Safe non-disclosing not-found | Pending |
| Empty/catalog-absent valid run | Preserve ratified preparation behavior | Pending |

## Failure-Class Closure Rule

Every confirmed endpoint defect must be repaired in the same authorized change.
Every run/deployment variant must end as `confirmed defect`, `verified unaffected`,
or `unresolved`, with a named test or retained runtime artifact. An unexecuted
case cannot become `verified unaffected`. Local implementation, environment
validation, deployment, and incident resolution remain separate claims.

## M0 review additions (2026-11-11)

All cases below are unresolved runtime acceptance obligations, not passing tests.

| Boundary/state | Required direct evidence |
| --- | --- |
| Uncached Omni resolution | Denial preserves shared-input links as well as catalog/log hashes |
| Cache changes between target and auth lookup | Every decision uses the same checked resource; foreign and same-root sibling targets rejected |
| Body-selected scenario symlink | No catalog activation/read outside checked parent before denial |
| Direct dashboard/report entry | Query cookie issued without first visiting no-config bridge |
| Parent-to-Omni and Batch base-to-child | Cookie transport, correct key/alias, marker binding, no sibling grant from child credential |
| Ownerless ordinary/PCV catalog | Legacy retained reads preserved; DB failure or empty arbitrary directory never becomes public |
| Actual private PCV catalog member | Current exact membership read works; revoked membership and activation denied |
| Multi-run viewer, maximum 100 | Browser domain-cookie and real ingress header-size acceptance |
| Readonly/malformed cache | Existing read/no-write and authorized auto-repair semantics retained |
| Parent landuse/soils | Canonical parent-backed data remains queryable, with checked parent identity |
| MCP bare identifier | Unmocked resolver test plus existing scoped MCP suite |
| Existing SQL external access restriction | Existing direct private-canary tests continue passing |


## Implementation disposition (2026-11-11 UTC)

The preceding tables retain the initial failure-class inventory. Current closure:

| Consumers/variants | Disposition and evidence |
| --- | --- |
| All six primary route/method consumers and log boundary | Confirmed defects repaired locally; `test_http_access_boundary.py` denial matrix covers both slash forms and populated artifact bytes |
| Primary/legacy/playback/composite roots and poisoned caches | Repaired resolver; real directory tests in boundary suite cover all named layouts and no repair side effects |
| Public/ownerless/owner/Admin/Root/PCV, Batch and Culvert | HTTP policy matrix passes, including current grant removal and forced-activation restrictions |
| Profile tmp/fork/archive | All resolver forms covered; authenticated profile tmp HTTP flow passes; production service acceptance remains unresolved |
| Parent inputs, relocated catalogs, external DEM and archived inputs | Native query and pending-refresh regressions pass with source admission before schema reads |
| MCP consumers | Verified regression suite passes with canonical bare-ID resolution; independent auth retained |
| Readonly/catalog repair | Existing query suite passes; no scientific outputs/interchange are generated by HTTP preparation |
| Hostile route/scenario/source/symlink/cache variants | Direct HTTP and pre-read-spy tests pass; denials preserve artifacts |
| Direct Flask page and Caddy public/private queries | Real browser checks pass on disposable forest fixtures; final environment receipt pending |
| 100-run collection/browser headers | Confirmed existing request-line and incomplete-event capacity failures; bounded limit corrections under validation |
| wepp1 ingress/rollout | Unresolved; no deployment authorization or live probing performed |

Evidence: `focused_release.txt` (478 passed, 2 skipped),
`boundary_viewer_final.txt` (110 passed), and independent review dispositions.
The separate SQL-expression/private-canary work is not closed by this package.
