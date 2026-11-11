# Query-engine HTTP access contract

Status: accepted QE-AUTH-F1-20261110 amendment, explicitly approved by the
operator on 2026-11-11. Implementation conformance is pending. This contract does
not claim that the current HTTP service enforces these boundaries.

## Scope and rationale

The HTTP surface behind `/query-engine` must authorize a canonical run before
reading its catalog/data or modifying its files. Route text is never a filesystem
path. This closes the missing ordinary-run guard while preserving direct browser
queries, public retained-result sharing, and existing MCP authentication.

The [feature-access contract](feature-access-governance-contract.md) continues
to govern private grouped-resource admission. This amendment changes query HTTP
admission only; it does not change browse/RQ policies, project ownership,
publicity, model outputs, restricted-feature rights, or service registrations.

## Routes and parsing

External routes are `/query-engine/runs/<runid>/<config>` (summary),
`.../schema` (catalog/schema), `.../query` (GET console, POST query), and
`.../activate` (POST forced catalog refresh). One optional trailing slash is
accepted for each. GET and HEAD activation return 405 without resolving a run.
The README's former `/catalog` and `/console` examples are documentation errors;
this amendment does not introduce those aliases.

Exactly one run identifier and one nonempty configuration slug are required.
Run identifiers follow [composite runid slugs](../composite-runid-slugs.md).
Reject empty, dot, slash, backslash, NUL, control-character, absolute,
root-relative, and extra-segment forms. Config is one portable slug containing
only ASCII letters, digits, underscore, dot or hyphen, excluding `.` and `..`.
Reject encoded separators and NUL before resolution; do not repeatedly decode
percent-escaped text. Missing config, malformed identifiers and unknown composite
forms return 400; no filesystem path fallback is permitted.

## Resolution and side effects

Resolve using canonical `get_wd` layouts with `prefer_active=False`, through a
side-effect-free mode that preserves other callers' defaults. Resolution MUST NOT
create/remove Omni links or write/invalidate a WD cache before authorization.
Validate cached paths against the identifier's exact expected location before
probing the cached location. A sibling run under the same mount is not valid.
Canonical configured root directories may themselves be mounted/symlinked;
resolve the trusted root first, then reject descendant symlinks escaping the
identifier's own expected directory. Root, parent, and child checks are distinct.

| Identifier class | Expected location and authorization resource |
| --- | --- |
| Ordinary | `/wc1/runs/<first-two-characters>/<runid>` or existing legacy `/geodata/weppcloud_runs/<runid>`; authorize the ordinary ID |
| Ordinary playback clone | Configured `PROFILE_PLAYBACK_RUN_ROOT/<runid>` only with clone mode enabled; authorize the same ID |
| Profile tmp/fork/archive | Matching configured playback root and leaf from the composite specification; no anonymous publicity inference |
| Batch base/child | Exact configured batch directory, `_base` or `runs/<leaf>`; batch sharing and private workflow admission apply |
| Culvert | Exact configured culvert batch `runs/<leaf>`; existing private group/service admission applies |
| Omni scenario/contrast | Exact parent's `_pups/omni/scenarios/<leaf>` or `contrasts/<leaf>`; authorize parent, then constrain child |
| Batch Omni | Same child suffix under the exact batch parent; authorize that batch parent |

Unknown nested composite forms are rejected. Root selection order follows the
canonical resolver; a cache entry cannot override it to select another run.
Missing/non-directory targets and containment failures return a generic 404.
Minimal path metadata and canonical public/ownership state reads are permitted
for admission; catalog/dataset reads and all run-file writes are not.

The POST body `scenario` selector is also a filesystem boundary. Resolve and
check its documented scenario location beneath the admitted run before context
resolution or automatic activation. Preserve existing WEPP/RHESSys scenario
selection; reject symlink escapes. Catalog entries and linked inputs must stay
within the admitted resource. Preserve canonical parent-backed source selection,
including `climate`, `dem`, `watershed`, `landuse` and `soils`, under the catalog
refresh contract. Bind these sources to the checked authorization parent, not
the first `_pups` substring in a path. This does not authorize sibling/private
run data.

Every public, ownership and workflow decision, including downstream rechecks,
must consume the same checked authorization parent/root. Shared helpers must not
independently re-resolve an unchecked mutable WD cache to decide authority.
Pass the checked target through threadpool calls and exception handling. Never
re-resolve unchecked route text to locate `exceptions.log`. Denials leave catalog,
log and Omni shared-input links absent or unchanged. Authorized read preparation
may create catalog caches under the admitted target, subject to the existing
[catalog refresh contract](query-engine-catalog-refresh-contract.md), including
readonly handling. It does not execute restricted scientific features.

## Principal and operation matrix

| Principal/state | Summary/schema/console/query | Forced activation |
| --- | --- | --- |
| Anonymous, public ordinary run | Allow | 401 |
| Anonymous, private ordinary run | 401 | 401 |
| Current private owner, Admin or Root | Allow with valid credential and scopes | Allow under controls below |
| Unrelated authenticated human, private run | 403 | 403 |
| Existing ownerless ordinary run, including PCV-01 legacy runs | Preserve anonymous retained-result reads | Authenticated controls below |
| PCV-01 catalog run, current PortlandGroup member | Preserve catalog-bound read grant; check live membership | No activation grant from collection membership |
| Bound service credential | Allow with resource and operation scopes | Require `runs:activate` |
| Public Batch | Preserve existing public Batch inspection exception | Authenticated admission plus controls below |
| Private Batch/Culvert | Existing resource binding and current feature admission; roles alone grant no exception | Same plus activation controls |
| Profile playback | Bound service credential or current owner/Admin/Root; no inferred anonymous grant | Same plus activation controls |
| Missing/empty/populated catalog | Authorize first; prepare absent/empty cache as allowed by refresh contract | Authorized refresh |
| Malformed catalog | Authorize first; retain existing automatic repair under refresh contract, with bounded error if repair fails or readonly prevents it | Authorized refresh, subject to readonly |

The [PCV-01 contract](../ui-docs/contracts/combined-watershed-viewer-contract.md)
preserves existing ownerless ordinary resources and catalog-bound collection read
grants. Private ordinary in this matrix means a run with owners and no PUBLIC
marker. Do not turn ownerless legacy data into private data. Owner lookup failure
is an error, never an empty owner list. Missing/empty directories are not proof
of a valid ownerless run. Require a regular existing `ron.nodb` that the canonical non-creating reader
can load, together with a successful empty ownership lookup, before that
exception. Missing metadata returns 404; malformed metadata is an explicit
operational error. Never create a Ron controller to manufacture anonymous access. Grouped and profile roots
do not inherit this ordinary ownerless exception. Session markers prove
session/run binding, not current ownership. Private human session requests also
require the current owner/Admin/Root or exact PCV-01 collection read decision. Existing issued credentials do not
retain removed private ownership or protected group membership. A valid
run-bound service grant remains a separate authorized access path.

Tokens require signature, issuer, expiry, jti revocation, exact audience
`query-engine`, and class `user`, `service` or `session`. MCP tokens remain on MCP
routes under their existing contract. Session tokens additionally require live
run marker and SID tombstone checks. Shared browse/RQ helper defaults stay intact.

Authenticated discovery/console requires `runs:read`; query POST requires both
`runs:read` and `queries:execute`. Anonymous public queries are an explicit scope
exception. Explicit bearer credentials take precedence over cookies; an invalid
bearer returns 401 and cannot fall back to public access. Invalid/stale cookies
may be treated as anonymous for public reads; private reads return 401 and never
redirect automatically. Valid credentials lacking scope/resource rights return
403. A supplied unrelated credential does not gain private rights through a
public ancestor outside the canonical sharing policy.

A parent-bound credential may inspect that parent's Omni children. An exact
child-bound credential may inspect only that child, not its parent or siblings.
For sessions validate the marker for the credential's admitted resource, then
apply the parent's current sharing/ownership policy. Batch-group and Culvert
batch UUID grants retain existing group binding; a bare matching name never
confers a new resource grant.

## Browser transport and lifecycle

Reuse the existing issuer, signing configuration, revocation and session marker
protocol. Mint a separate HttpOnly query credential only after the corresponding
Flask entry route has authorized the resource. Cover normal run pages, direct
dashboards/reports and multi-run viewers; the no-config redirect bridge alone is
insufficient. Multi-run views receive credentials only for individually
admitted resources, never an unchecked list supplied by the browser.

The cookie base name is `wepp_query_jwt`. Use the existing SHA-256 name helper
with `runid + "\n" + config`, truncated to 16 hex characters, for ALL run IDs.
Path is `/query-engine/runs/`, with no Domain, HttpOnly, Secure on HTTPS production,
and SameSite=Lax. An explicit local HTTP test profile may omit Secure. Each
cookie's signed run/config binding, exact lookup and resource checks supply
isolation; the wider path supplies parent-to-Omni and multi-run browser transport.
Do not use a global unscoped cookie-name fallback. Consumers check the exact
child key, eligible Omni parent key, and the exact Batch `_base` alias key
where existing group policy authorizes that batch child. No other key is tried. A wrong-config cookie never authorizes.

This deliberately replaces the draft's ordinary per-run cookie path: browsers
do not send that path's cookie to an Omni composite URL. Preserve the existing
four-day (345600 second) bridge JWT/marker lifetime; no new shorter TTL or refresh
service is introduced. Credentials use distinct jti values, audience
`query-engine`, and only `runs:read queries:execute`. Carry trusted human origin
metadata where available. Never put query credentials in HTML, JavaScript,
URLs, response JSON, or logs. Existing browse cookies keep their names/paths.
Logout/reset tombstones invalidate derivative query credentials. A reload of an
authorized page renews them. Private stale-tab errors show reload/sign-in recovery,
without automatic redirect loops or repeated token retries. The existing maximum
100-run collection must pass real browser cookie limits and ingress header-size
limits; public/ownerless reads need no credential issuance. Do not raise proxy
limits or redesign token transport without retained failing acceptance evidence.

## Explicit activation and browser request origin

Forced activation is POST-only and is a cache operation, not a restricted model
execution grant. Bearer clients require `runs:read runs:activate` plus resource
admission. Cookie clients require `runs:read queries:execute`, verified current
human owner/Admin/Root (or current private grouped inspection authorization),
and the existing Browser Same-Origin Guard contract. Anonymous-derived session
cookies cannot force activation even on public runs. This is an explicit,
bounded cookie activation exception; it does not add `runs:activate` to page
cookies or grant any RQ/feature execution scope.

The [CSRF contract](weppcloud-csrf-contract.md#browser-same-origin-guard-contract)
defines the guard, including missing-header rejection, hostile/null Origin,
alternate-port handling, and the narrow trusted upstream-TLS scheme bridge.
Apply it to cookie-authenticated POST query and activation. Anonymous public
POST queries remain allowed without browser headers for existing non-browser
clients. When Origin is present on any run HTTP request it must match a
configured exact public origin; otherwise return 403 before run processing.
Bearer calls without Origin need no browser CSRF signal.

CORS allows only explicitly configured HTTP(S) origin tuples from
`QUERY_ENGINE_ALLOWED_ORIGINS` (comma-separated); no wildcards or origin regex.
When unset, allow no cross-origin access; same-origin requests without Origin
remain functional, but browser POST rollout requires the exact public origin
configured. Permit GET, HEAD, POST, OPTIONS and Authorization, Content-Type.
Credentialed CORS is allowed only for the exact configured set. Preflights do
not resolve runs or access files. Raw forwarded headers cannot extend authority.
Render the correct public origin configuration in the production-equivalent
Compose/Caddy acceptance gate before rollout.

## Errors, verification and limits

Admission errors use bounded JSON: 400 malformed route; 401 absent/invalid
required credentials; 403 insufficient authority/scope or rejected origin;
404 missing target/containment violation; 405 unsupported method. Keep existing
409 lifecycle/readonly conflicts. Configuration/store failures are explicit 5xx,
never anonymous/public fallback. Error bodies must omit filesystem paths, owner
identities, tokens, private records and traceback text. Denied requests must not
append run exception logs.

Required direct tests cover every route and trailing slash, every supported run
class, empty/absent/populated/legacy/hostile state, poisoned WD cache, actual
symlinks, scenario selection, parent/child binding, real signed JWTs,
revocation/tombstones, current ownership, origin vectors, credential precedence,
and before/after catalog/log/link readback. Browser tests cover direct private
entry, Omni selection, multi-run views, public reads and stale credentials.
Independent MCP, browse and RQ regressions prove defaults unchanged. MCP calls
the shared resolver with bare IDs: introduce separate HTTP parsing or an explicit
mode rather than requiring config in every resolver call. Existing SQL external
access/extension restrictions remain enabled and their canary tests must pass.

Local tests are not production evidence. Preserve exact candidate revisions,
real Caddy/Compose workflow evidence, independently reviewed findings and
operator-authorized rollout/rollback receipts in the active package. Other
security findings and SQL expression containment remain under their existing
contracts; this amendment alone does not certify the entire service secure.
