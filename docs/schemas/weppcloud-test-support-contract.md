# WEPPcloud test-support contract

Implementation conformance pending F7. This is the durable authority for
`/tests/api/*`; the execution record is
`docs/work-packages/20261111_test_support_production_guardrails/`.

## Runtime states

`WEPPCLOUD_DEPLOYMENT_PROFILE` is trimmed and lowercased. Missing, empty, or
whitespace means `production`. Only `production`, `development`, and `test`
are accepted. `configuration.config_app` raises `ValueError` with
`WEPPCLOUD_DEPLOYMENT_PROFILE must be production, development, or test`
for any other value, before secret resolution or service initialization.
`TEST_SUPPORT_ENABLED` retains its existing boolean parser and false default.

| Profile | Support flag | Startup | Test routes |
| --- | --- | --- | --- |
| absent/empty/production | false | allowed | absent (404) |
| absent/empty/production | true | ValueError | never registered |
| development/test | false | allowed | absent (404) |
| development/test | true | allowed | registered, bearer required |
| unknown | either | ValueError | never registered |

Production with support enabled raises `ValueError` with
`TEST_SUPPORT_ENABLED requires development or test deployment profile`.
Registration independently requires both the explicit non-production profile
and enabled flag. Production Compose pins literal `production` and literal
`false`; development Compose explicitly selects `development`. Host overlays
must preserve production literals. Unsupported HPC starts default to production;
HPC smoke activation is not introduced by this change.

## Bearer and authority

All three routes require an Authorization header containing exactly one Bearer
credential (scheme case-insensitive), validated by existing WEPP_AUTH signing,
issuer, time, and audience validation. Audience is `weppcloud-test-support` and
required scope is `test:support`; scope parsing uses the configured WEPP_AUTH
separator. Tokens must contain finite numeric `iat` and `exp` claims, with
`0 < exp - iat <= 3600`, and must not be expired at request time. No expiry
leeway extends support authority. Missing/malformed/invalid/expired tokens,
invalid lifetime, or wrong audience return 401. Valid tokens without the scope
return 403. Responses use JSON `{"error": "Unauthorized"}` or
`{"error": "Forbidden"}`, without token, claims, or verification diagnostics.
Server signing configuration errors remain explicit server failures.

Authentication precedes payload parsing, run resolution and all filesystem
operations. A valid bearer grants environment-wide create/delete authority:
any resolvable run in that development/test environment may be deleted. This
is the operator-selected privileged support capability; no ownership checks,
smoke markers, registry, session login or Root-role requirement are added.
Successful paths/payloads remain ping 200, create 201, delete 200; missing run
remains 404. Existing payload/path validation remains in force.

The three views are explicitly CSRF-exempt under the bounded exception in
[the CSRF contract](weppcloud-csrf-contract.md#test-support-bearer-exemption).
Cookies grant no support authority. Audit logs contain only route identity and
outcome; never credentials, claims or private payloads.

## Agent workflow and token non-retention

`wctl run-playwright` mints inside its configured WEPPcloud container using
existing WEPP_AUTH keys, subject `wctl-playwright`, audience
`weppcloud-test-support`, scope `test:support`, lifetime exactly 3600 seconds.
Before minting, reject URL userinfo and require HTTPS with normal certificate
verification for remote origins; HTTP is permitted only for localhost or
loopback IP addresses. The shared helper enforces the same transport rule.
This prevents the newly introduced privileged credential crossing plaintext
remote transport; documented local HTTP presets remain supported.
It captures token output in memory and fails before ping/npm if issuance fails.
The existing mandatory preflight ping remains mandatory, including
`--no-create-run`, so all invocations mint and authenticate. Production smoke
using this support wrapper is intentionally unsupported.

The bearer is passed only to the support ping and the Playwright test child via
`SMOKE_TEST_SUPPORT_TOKEN`. It must not reach report-viewer subprocesses or
persist in argv, URLs, logs, profiles, traces, reports, or retained artifacts.
A shared support helper confines headers to ping/create/delete at the configured
origin and support path, rejects redirects, and keeps error output token-free.
The Python preflight ping also rejects redirects before forwarding credentials.
Do not use Playwright context-wide headers. Support requests must run outside
traced Playwright request contexts so authorization cannot enter trace archives.
Direct npm invocations require a transient injected token or use the canonical
wrapper; no anonymous fallback or additional static token is permitted.

## Compatibility and acceptance

Raw development starts must now select a profile explicitly. Existing anonymous
support callers must adopt the automatic wrapper or scoped helper. These are
intentional changes: a default production boundary and a privileged bearer
replace accidental activation and anonymous destructive authority. Reusing
WEPP_AUTH avoids new secrets; rejecting markers preserves deterministic cleanup.

Prove every runtime row through configuration and actual Flask URL maps; exercise
real signature/expiry/scope checks and CSRF middleware. Denied create must leave
a bounded temporary root unchanged; denied delete must preserve its fixture.
Valid delete must remove the fixture. Verify mint failure stops before network
or npm, unrelated requests lack the header, and emitted artifacts contain no
exact minted token. Unmocked create/load/delete requires an explicitly configured
local non-production runtime and direct filesystem readback. Render production
Compose with attempted env overrides and observe literal disabled production.
See [runtime startup contract](../infrastructure/weppcloud-web-runtime-contract.md#test-support-startup-invariants).
