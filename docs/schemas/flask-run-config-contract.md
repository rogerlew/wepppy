# Flask Run Config Authority

## Scope and decision

Implementation is wired in Flask and covered by focused tests; deployment is
pending. The operator approved the Flask-only
hook on 2026-09-06. Other services, including browse, download and rq-engine,
are deferred even when Caddy exposes them under `/weppcloud/runs/`.

All matched Flask `/runs/<runid>/<config>/...` endpoints MUST use the active
run's stored `ron.nodb` `_config` token. Resolve composite run IDs and contained
`?pup=` paths using the existing run-context resolver. Children do not consult
their current batch `_base`: they may have diverged legitimately. Builder runs
retain `config`; legacy named presets retain their stored token.

Read only the JSON metadata, without deserializing NoDb objects, creating
controllers, updating run files or clearing caches. Missing run/ron and
malformed JSON or missing/empty/unsafe identity receive the same generic 404,
before endpoint guards, with details only in server diagnostics. Optional manifests
are unnecessary, whether absent, empty or populated. No requested-token fallback
is allowed. Strip inline `?` overrides and an optional `.cfg` suffix to obtain
a safe single route token. Extensionless legacy identities are supported.

## Dispatch and compatibility

An application URL-value preprocessor MUST normalize the `config` view argument
before blueprint preprocessing and handlers. The stored RunContext and generated
links MUST agree. Preserve the original requested token for diagnostics.

For valid resolved identity, existing authentication, authorization, CAP, CSRF and token checks
MUST execute normally. Do not replace endpoint-specific guards with a generic
authorization check. After a mismatched GET/HEAD successfully returns a 2xx
response, replace it with a temporary 302 to the same matched rule using the
canonical token. Preserve other path arguments, deployment prefix and raw query
string (including repeated keys). Never redirect errors or existing redirects.
This response-stage policy retains each endpoint's own guards; it may execute
the normal handler before redirecting. Some legacy GET handlers generate reports;
following a stale URL can therefore generate that report twice. This bounded
cost is accepted to preserve existing endpoint guards. Close discarded response resources.

POST/PUT/PATCH/DELETE dispatch once with the canonical argument, preserving body,
files and existing response contracts. OPTIONS keeps existing behavior without
config lookup. Unmatched and non-run routes remain unchanged. The hook does not
authorize any action, alter claims, or replay a mutation.

## Validation and operations

Tests MUST cover real JSON files, legacy/Builder identities, composite and PUP
resolution, malformed and missing state, suffix/prefix/repeated-query preservation,
single mutation dispatch with intact body, denied requests, and registration
independent of the existing blueprint allowlist. Keep CSRF coverage passing under
`docs/schemas/weppcloud-csrf-contract.md`; session and token policies remain those
of `docs/schemas/weppcloud-session-contract.md` and endpoint contracts.

Users can keep old Flask bookmarks; successful reads redirect to their saved
project identity. Operators should inspect server diagnostics for identity-related
404 responses, not repair them by guessing a preset. No run migration is required.
Deploy the web application to activate; rollback the application change to
restore prior URL behavior. Services bypassing Flask remain deferred.
