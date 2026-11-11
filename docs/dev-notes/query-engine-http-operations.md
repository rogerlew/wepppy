# Query-engine HTTP access operations

Authority: [HTTP access contract](../schemas/query-engine-http-access-contract.md).
This guide describes the implementation; it is not a deployment receipt.

## Configuration and clients

Set `QUERY_ENGINE_ALLOWED_ORIGINS` on query-engine to comma-separated exact public
origins, including scheme and any nondefault port. Dev/prod Compose defaults to
`https://${EXTERNAL_HOST}`. Do not use a wildcard or include `/weppcloud` paths.
Standalone omission accepts requests without Origin but rejects supplied Origins.
WEPPcloud Gunicorn allows an 8190-byte request line to carry the existing
100-run JSON collection URL (the previous 4094-byte cap rejected the controlled
5537-byte acceptance URL). Query-engine Uvicorn uses an H11 incomplete-event
buffer of 131072 bytes instead of 16384: a real 100-cookie request measured
63600 bytes and otherwise failed before application admission. This bounds the
incomplete parser event, not total headers. The per-connection buffer can grow
by up to 112 KiB; Caddy and body limits are unchanged. Reverting either setting
restores its measured collection failure. Verify the actual runtime selects
`H11Protocol` and rerun browser acceptance after upgrades.
The existing JWT secret, account database, Redis/session marker configuration and
mounts must match WEPPcloud. No new service or credential store is introduced.

Private browser users sign in and open a run/dashboard/report or collection page.
Flask issues hashed, run/config-bound HttpOnly session cookies on
`/query-engine/runs/`, retaining the existing session lifetime. Cookies are never
embedded in HTML or passed to JavaScript. A stale session requires sign-in and
page reload. Public/ownerless collection entries need no cookie. Logout/revocation
uses the existing session markers and current account/ownership checks.

HTTP callers use `/query-engine/runs/{runid}/{config}` with `/schema`, `/query` or
`/activate`. Filesystem paths are not identifiers. Bearer callers require the
`query-engine` audience and contracted resource/scopes. Forced activation is POST;
cookie activation additionally requires a same-origin request and current human
resource authority. MCP keeps its separate bare-ID and token contracts.

## Diagnose and validate

A private anonymous request returns 401; insufficient authority/scope or disallowed
Origin returns 403. Invalid route grammar returns 400, missing/escaped targets 404,
and GET/HEAD activation 405. Account/session-store failures fail closed with a
bounded 503. Check service logs for operator diagnostics; do not copy credentials
into tickets or command transcripts.

Admission uses `get_wd(read_only=True)` and checked physical paths without cache
writes or Omni link repairs. Catalog/query work carries this checked resource
through synchronous worker calls. Existing native scans, external DEM skip rules,
parent-backed Omni inputs, catalog relocation and readonly behavior remain in
place. Denied requests must leave existing catalog/log bytes unchanged.

Before rollout, validate the exact candidate through Caddy with production-like
service identities, groups, mounts, umask, secrets and configuration. Check public
and owner query records, anonymous/unrelated denials, expired sessions, direct
page and collection cookie issuance, and a 100-private-run browser collection.
Read back catalog outputs and hash log/catalog artifacts around denials. Unit
and HTTP test-client results alone do not satisfy this gate.

Use the canonical `scripts/deploy-production.sh` and installed wctl preset for an
explicitly authorized production deployment. Do not roll back to a publicly
reachable vulnerable revision; retain separately authorized ingress containment
until a safe candidate passes acceptance. This package does not authorize changes
to ownership, public defaults, feature memberships or production containment.
