# WEPPcloud WebSocket authorization contract

Status: operator-ratified 2026-11-11; implementation pending. The operator
explicitly approved the three lifecycle policies and instructed ratification
and implementation. No fail-open compatibility exception is authorized.

## Scope and authority

Govern browser status and preflight streams, their rq-engine credential bridge,
and the two Go service validators. Preserve existing run inspection authority,
feature inspection checks, and lifecycle workflows. Do not grant RQ enqueue,
export, file access, or unrelated HTTP authority. Related contracts are
[session](weppcloud-session-contract.md), [CSRF](weppcloud-csrf-contract.md),
[RQ responses](rq-response-contract.md), and
[token issuance](../dev-notes/auth-token.spec.md).

## Ordinary-run credential

`POST /rq-engine/api/runs/{runid}/{config}/stream-token` accepts JSON
`{"service":"status"}` or `{"service":"preflight"}`. Reject unknown services
and unknown fields with canonical 400 errors. Browser requests use the existing
same-origin session bridge, including the migration-aware cookie selector and
current user/role lookup. Bearer and cookie credentials must not be mixed into
an alternate authorization path. Reject any supplied Authorization header on this
cookie-only browser bridge with 400; never ignore a bad bearer. No general RQ token is minted as a side effect.

Issue a single-service token, not combined audiences. Success is HTTP 200 with
`token`, `expires_at` (Unix seconds), `expires_in` (seconds), `service`, and resolved `config`;
responses carry `Cache-Control: no-store`. No token cookie is set.

| Claim | Required contract |
| --- | --- |
| `iss` | `weppcloud-stream` |
| `aud` | `wepp-status` for status; `wepp-preflight` for preflight |
| `token_class` | `session` |
| `stream` | `status` or `preflight`, matching the audience |
| `scope` | Exactly `status:read` or `preflight:read` |
| `runid` | Exact decoded requested run identity, including composite suffix |
| `config` | Exact resolved configuration slug |
| `sub`, `session_id` | Same nonempty server-selected session ID |
| `jti` | Fresh random token identifier |
| `iat`, `nbf`, `exp` | Required integral seconds; `nbf=iat`, `exp=iat+300` |

Use HS256 only and the existing configured signing-key file/ring; the first key
signs, configured validation keys verify. Never infer the algorithm from the
header. Stream issuer/audience/scope must not inherit the general RQ helper's
optional issuer, default audience injection, or configurable scope separator.
Do not add stream audience to any general RQ/API accepted-audience set.

Clock leeway is zero; reject future `iat`/`nbf`, expired tokens, inverted times,
and lifetime exceeding 300 seconds. Verification also requires `nbf=iat` and
`0 < exp-iat <= 300`. Reject missing, wrongly typed or ambiguous
claims. Required strings cannot be empty. A general session token is not a
stream token, and a stream token cannot authorize unrelated RQ operations.

## Access and valid states

| State | Required outcome |
| --- | --- |
| Existing private run, owner or collaborator in the run-owner association | Allow with a live browser session and workflow inspect authority |
| Existing private run, current Admin/Root | Allow subject to existing workflow inspect checks |
| Existing private run, unrelated user or anonymous | Deny |
| Explicitly public existing run, anonymous or authenticated reader | Allow; a sessionless public reader gets a short-lived random SID and marker |
| Ownerless ordinary existing run, live anonymous session | Preserve existing session bridge access; do not label ownership absence as an explicit public flag |
| Ownerless ordinary run, no browser session | Allow after authoritative existing run/config resolution and workflow inspect checks |
| Composite Omni/contrast run | Resolve authorization through its parent; credential still names exact child and actual config |
| Private Batch/Culvert workflow | Existing workflow inspect authority still required; Admin/Root role alone is not a substitute |
| Never-used/empty/populated preflight state | Same authorized stream; retain normal empty checklist behavior |
| Working/failed/completed run | Same run inspection authority; failure does not remove progress visibility |
| Archived/restoring run | Resolve canonical archived identity without requiring an active tree; no implicit restoration |
| Deleted/missing ordinary run or config mismatch | Deny; an unknown run must not become public by having no owners |
| Admin run-sync before destination registration | Allow only the job/channel-bound operation authority below |
| Diagnostics synthetic `diag-*` identity | Use selected accessible project below; never treat as a public run |
| Revoked SID/JTI, missing marker or auth-store failure | Deny before upgrade or run Redis access |

Existing access checks and current canonical feature policy remain authoritative;
this table does not give every role access to every specialized workflow.
Issuance must resolve actual identity/config before authorizing ordinary runs.
Normalize config by trimming whitespace, lowercasing, and removing a terminal
`.cfg`. The existing `cfg` routing alias resolves to the stored config stem;
other mismatches reject. Return that resolved slug to clients, which use it in
the socket query and cache identity. Do not load unrelated model controllers to
resolve identity. Archived identity follows the existing canonical run resolver.
Fork streams bind to the existing source run, not the new destination.

## Transport, validation and connection lifetime

Retain the existing service paths and add exactly one non-secret `config` query
value. Reject missing, duplicate, malformed or mismatched config values. Tokens
never appear in a URL. Clients offer exactly `wepp-stream.v1` and
`bearer.<compact-JWT>` in `Sec-WebSocket-Protocol`. Reject duplicate or ambiguous
credentials and protocol input exceeding 8192 bytes before token parsing. Negotiate only
`wepp-stream.v1`; never echo the bearer protocol.

Validate method/path/config, exact Origin, protocol syntax, signature and all
claims, then live authorization state, before `websocket.Accept` and before
subscription or run-hash access. Origin is an exact scheme/host/port allowlist;
missing/null/hostile Origin rejects, empty configuration fails startup. No
local-development bypass is proposed. Health endpoints remain token-free.

Redis DB 11 must contain `auth:session:run:<runid>:<sid>` and must not contain
`auth:session:revoked:<sid>`. Redis DB 0 must not contain
`auth:jwt:revoked:<jti>`. Connection errors/timeouts fail closed. Stream issuance
must not shorten an existing four-day RQ marker: retain its remaining lifetime
or extend only when shorter. A revocation fence always wins over a marker.
Cookie issuance must check SID revocation even outside cookie migration mode.
Public fallback cannot turn an invalid/revoked supplied session into a new SID;
only a truly absent session may use that path.

Unauthorized upgrade returns generic 401; Origin/authority denial returns 403;
malformed request returns 400; auth-store unavailable returns 503. Use canonical
JSON errors at the mint route. Never include claims, tokens, stack traces or
secret values in denial bodies/logs. Close an established socket at token expiry
with application code 4001 and a fixed safe reason. Expiry must not emit the
terminal `hangup` frame that disables current frontend reconnect; test actual
frame ordering as well as the close code. This bounds stale access to
five minutes; authorization changes after mint are not instantly propagated.

Browser cache is memory-only and keyed by run/config/service plus operation/job
binding when present. Run-sync credentials must never satisfy an ordinary status
or command request, including concurrent requests. Refresh 30 seconds
before expiry; coalesce concurrent requests. Stop on mint 401/403. An unexplained
upgrade failure permits one fresh-token retry with backoff; repeated failure
stops visibly. Successful connections reset that retry budget. Disconnect must
cancel pending mint/connect/retry work. Never fall back to an anonymous socket.

## Message boundary

Retain status lifecycle/progress and controller TRIGGER messages, including
command-bar consumers. Remove absolute paths, raw exception/traceback details,
argument/option maps and credentials from outbound messages and service logs.
Producer inventory must define field/category transformations and prove the
existing browser consumers still function; a blanket discard of free-form
progress is not an accepted compatibility repair.

Preflight retains typed `checklist`, `lock_statuses`, optional `last_modified`,
and current control frames. Do not log the raw prep hash; lock keys require a
bounded known-controller vocabulary rather than reflecting arbitrary Redis
field names. The browser-visible lock vocabulary is the existing
`LOCKABLE_FILES` map in `static/js/preflight.js`: ron, topaz, watershed, landuse,
shrubland, rangeland_cover, soils, climate, treatments, rhem, rhempost, wepp,
wepppost, observed, unitizer, baer, disturbed, rred, lt, ash, ashpost, debris_flow,
roads, omni and rusle, each with `.nodb` suffix. Unknown fields are omitted from
the browser payload, without changing Redis locking behavior.

Known compatibility categories are:

| Category | Required retained behavior |
| --- | --- |
| Status | String `data` inside `type=status`; ping/hangup controls; ordinary progress text |
| RQ lifecycle | `rq:<jobid>` and STARTED/ENQUEUED/STATUS/COMPLETE/COMPLETED; run-sync completion run/config tokens |
| Trigger | Final controller/event tokens and validated channel-delineation `DIAGNOSTICS_V1` structured payload |
| Exception | EXCEPTION marker and job ID for the existing authorized job-info fetch; safe summary instead of raw traceback |
| Structured failure | Sanitized EXCEPTION_JSON shape, scheme/field/sub-field identifiers, safe filename and message |
| Command | Manifest/interchange progress and completion semantics |

Confirmed disclosure producers include `rq/land_and_soil_rq.py` workspace
messages, `rq/project_rq.py` paths and option-map logging, `nodb/base.py` setter
argument logging, and `rq/batch_rq.py` exception messages (all under `wepppy/`).
Preflight `internal/checklist/checklist.go` logs raw hashes unconditionally.
Tests must exercise these concrete sources, not just fabricated safe strings.
The checkpoint's `20261111_message_inventory.md` maps confirmed producer
categories to required transformation fixtures. Implement and independently
review those fixtures before claiming disclosure repair. Unknown arbitrary text
cannot be claimed free of sensitive values merely because one path regex passes.

## Ratified lifecycle policies

Run-sync policy: only a current Admin/Root with a live browser
session may mint a status-only credential for an existing canonical run-sync job
whose canonical server-side job arguments bind the destination run/config and `run_sync`
channel. No preflight or arbitrary channel authority; no grant for arbitrary
missing run IDs. The mint request adds optional `job_id` only when `service=status`.
Require current database-backed Admin OR Root role for stream inspection,
including Root-only users. This does not alter the existing Admin-only enqueue
policy. Resolve
that job in canonical RQ DB 9, require the default queue and exact
`wepppy.rq.run_sync_rq.run_sync_rq` function, and read run/config from its bound
arguments (not metadata populated only after worker start). Missing config uses
the existing run-sync `cfg` default. Never expose the other job arguments.
Require the job's destination to equal the route run ID and its config to equal
the submitted normalized config. Pending/active/finished/failed jobs with a
retained canonical record are inspectable by that administrator; unknown jobs
reject. Mint additional claims `job_id`, `operation=run-sync`, and
`channel=run_sync`. The status service enforces that channel and the preflight
service rejects operation tokens. The response supplies the exact config for
the URL. This neither adds queue edges nor changes enqueue behavior.

Diagnostics policy: run stream diagnostics against an explicitly
selected existing accessible run using normal stream credentials. On the global
page without a run, report that stream authorization needs a selected project;
retain service health checks without claiming they prove WebSocket delivery.
Do not create synthetic public-run grants or a diagnostics auth bypass.

Ownerless policy: retain anonymous inspection of existing ordinary
ownerless runs, including readers without a cookie, while preserving feature
inspection restrictions. This resolves the page/token-bridge discrepancy without
making nonexistent or private owned runs public. Ownerless status must come from
successful authoritative lookup, never lookup failure.

These policies resolve previously unspecified boundaries. Complete the
two independent reviews and standalone ancestor checkpoint before
implementation. Deployment is authorized on forest only after all local gates;
closure requires real browser proof for both streams and lifecycle consumers.
