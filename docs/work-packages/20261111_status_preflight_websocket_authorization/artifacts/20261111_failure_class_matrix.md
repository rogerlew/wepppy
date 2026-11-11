# F4 failure-class and consumer matrix

**Status**: M0 discovery expanded; policy ratification and producer fixtures pending  
**Date**: 2026-11-11 UTC

This matrix applies the hardening lifecycle requirement to all confirmed
consumers of the broken assumption that naming a run and passing Origin checks is
sufficient to subscribe to status/preflight data.

| Surface/consumer | Current trust input | Failure class | Required repair/evidence | Disposition |
| --- | --- | --- | --- | --- |
| StatusStream browser client | Run-derived WebSocket URL | Sends no identity | Acquire/refresh token; token-free URL; Jest and forest CDP proof | In scope |
| Preflight browser client | Run-derived WebSocket URL | Sends no identity | Acquire/refresh token; token-free URL; Jest and forest CDP proof | In scope |
| status2 upgrade handler | Path plus Origin | Missing run authorization | Validate token/session/run before accept and Redis; Go integration matrix | In scope |
| preflight2 upgrade handler | Path plus Origin | Missing run authorization | Validate token/session/run before accept and Redis; Go integration matrix | In scope |
| Caddy status/preflight routes | Network path | Routing mistaken for identity | Preserve routing; prove services enforce identity behind proxy | In scope evidence |
| Forest/prod Compose | Optional allowed-origin values | Empty/permissive Origin policy and missing auth config | Exact origins, secret-file and auth Redis config; rendered checks | In scope |
| RQ token/session boundary | General RQ credential | Excess privilege/lifetime if reused unchanged | Dedicated least-privileged mint or retained contrary evidence | In scope |
| RQ Redis DB 11 session state | Session marker/revocation | Signed token may outlive revoked session if ignored | Live marker and revoked-key checks | In scope |
| Status publishers | Free-form message fields | Absolute path/exception/option leakage | Inventory producers; narrow schema/redaction tests | In scope W-05 |
| Preflight publishers | Free-form checklist/error fields | Path/exception/option leakage | Inventory producers; narrow schema/redaction tests | In scope W-05 |
| Public-run readers | Public run state | Silent compatibility break or fail-open anonymous access | Explicit public valid-state contract and tests | In scope decision |
| Frontend reconnect loops | Cached credential | Expired replay, anonymous downgrade or retry storm | Bounded refresh/backoff and fake-clock tests | In scope |
| Browser/proxy/service logs | URL/protocol/header diagnostics | JWT leakage in retained evidence | Sanitized structured logging and secret scans | In scope |
| Command-bar direct socket | Run-derived `:command` URL | Bypasses StatusStream | Same token helper/refresh and progress compatibility tests | In scope confirmed |
| Diagnostics realtime probes | Synthetic `diag-*` IDs | Cannot prove real run access | Proposed selected authorized run; owner decision pending | In scope decision |
| Generated controllers-gl bundle | Embedded StatusStream | Stale generated transport | Canonical builder and bundle parity | In scope confirmed |
| Run-sync dashboard | Destination not registered yet | Ordinary-run mint would break valid workflow | Proposed job/channel-bound admin status token | In scope decision |
| Fork console | Source run status | Missing explicit config context | Resolve source config; no destination exception needed | In scope confirmed |
| Archive/restore consoles | Archived identity | Active-tree-only lookup would break inspection | Canonical archive identity resolution | In scope confirmed |
| General HTTP traceback responses | HTTP error body | Separate information disclosure class | F5 package | Out of scope |
| Query-engine/RQ mutation endpoints | Their own endpoint auth | Different authorization boundary | F1 or canonical endpoint packages | Out of scope |

## Negative Corpus

Each Go service must exercise these states before WebSocket acceptance and before
per-run Redis subscription:

- missing, empty and malformed protocol credentials;
- forged signature and disallowed algorithm;
- wrong issuer, service audience, scope or token class;
- expired token, future `nbf`, invalid issued time and excessive lifetime;
- absent/malformed run/config claim and run mismatch;
- missing session marker and revoked session/token;
- hostile or absent Origin under the ratified policy; and
- token for private run A presented to private run B.

Positive cases include exact-origin owner access, any ratified collaborator/admin
states and the exact public-run state if public streams are retained.

## Message Producer Inventory Gate

Before implementing W-05, enumerate every publisher and every browser-consumed
field for both channels. Classify fields as allowed, redacted/transformed, or
prohibited. Retain focused cases containing absolute paths, exception strings,
newlines, option maps and token-shaped values. Do not claim general exception
redaction outside these streams.

## Completion Rule

The failure class closes only when all in-scope rows have implementation,
focused regression and actual forest evidence where applicable. A green socket
connection or Origin test alone cannot close the finding.

## Discovery receipt

Read-only source review confirmed canonical JTI revocation in DB 0 and SID
revocation/run markers in DB 11. The short marker SETEX proposal would truncate
four-day RQ markers and is rejected. Fork destination concern was retracted:
`fork_console.js` connects the submitted source `runId`, while `newRunId` is
separate; `project_rq.py` publishes the source `:fork` channel.

The producer boundary is `wepppy/nodb/status_messenger.py`: direct publish,
`publish_command`, and `StatusMessengerHandler.emit` (which forwards arbitrary
NoDb logger text). Inventory includes RQ project, land/soil, batch, run-sync,
Omni, WEPP stage, SWAT, roads, features/export, interchange, migration, ag-fields,
postfire, PATH-CE, worker, and WEPPcloudR publishers; microservice fork/archive,
migration and run-sync publishers; NoDb base/climate/SWAT logging; soil builders,
Daymet, and interchange writers. All share that boundary. Raw Redis publication
by operators is also possible, so producer-only filtering cannot replace the
service outbound guard. Exact compatibility fixtures remain pending, explicitly
blocking the completed M0 claim.

Preflight derives output from RedisPrep rather than forwarding its raw hash.
Confirmed disclosure is unconditional raw-hash debug logging and unbounded
`locked:*` field-name reflection. Preserve checklist booleans/timestamps; remove
raw input logging and validate supported lock names.
