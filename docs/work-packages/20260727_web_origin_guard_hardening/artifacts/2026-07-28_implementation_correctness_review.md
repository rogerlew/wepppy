# REM-04 implementation correctness and compatibility review

## Review scope

Independent read-only review of the REM-04 working-tree implementation against:

- checkpoint ancestor `736198ce8a4b68b83a9c77860a52da574f2cc98d`;
- the active web-origin guard hardening ExecPlan and WP01-WP04 prompts;
- `docs/schemas/weppcloud-csrf-contract.md`; and
- `docs/ui-docs/diagnostics-page.spec.md`.

The review covered predicate parity, the HTTP:80 to HTTPS:443 bridge, URL
parsing, reset-cookie tuples, copied diagnostics, shared vectors, per-surface
tests, compatibility, and closure evidence. It did not modify implementation,
tests, contracts, prompts, or trackers.

## Verdict

**FAIL.**

Counts: **0 critical, 0 high, 3 medium, 1 low**. There are three unresolved
medium findings, so the package does not meet its closure rule requiring all
medium/high findings to be resolved. The focused tests are green but do not
exercise the failing cases below.

## Findings

### MEDIUM-1: configured public-origin behavior is not shared by query-engine

The canonical contract says rq-engine and query-engine use both their ASGI
request URL/authoritative Host and configured public host/scheme values. Flask
and rq-engine add configured `OAUTH_REDIRECT_HOST`/`EXTERNAL_HOST` origins, but
`wepppy/query_engine/app/server.py::_request_allowed_origins` adds only the
request URL and Host. Its bridge likewise compares the browser host only with
the request host, not a configured public host.

Consequently, an exact configured public Origin can pass Flask and rq-engine
but fail query-engine when the internal authoritative Host differs. This is a
cross-service predicate divergence and a direct violation of the authoritative
input contract. It also leaves no test proving configured-origin parity: the
shared vectors contain request-host cases only, while the rq-engine configured
external-origin case is surface-specific.

Required disposition: make query-engine consume the same explicit public
host/scheme configuration contract (without consulting raw forwarded
headers), cover a configured-public-host vector on all applicable guards, and
define/test bridge behavior when the configured public host differs from the
internal Host.

### MEDIUM-2: all three origin parsers accept contract-invalid user information

The CSRF contract states that user information does not produce an origin
tuple. All three `_normalized_origin` implementations call `urlparse` and use
`parsed.hostname` without rejecting `parsed.username` or `parsed.password`.
Thus, for example, `https://attacker@guard.test` normalizes to
`("https", "guard.test", 443)` and can match the allowed origin. The same issue
affects Referer extraction because each guard rebuilds an origin from
`parsed.netloc`, retaining user information that the normalizer then ignores.

Browsers should not emit user information in an Origin header, which limits
practical browser exploitability, but these are security-boundary predicates
and the implementation explicitly contradicts the reviewed invalid-URL
contract. The shared vector set omits both user-information and general
malformed-origin cases despite WP04 and the canonical matrix requiring malformed
input coverage.

Required disposition: reject user information identically in all three
normalizers and add shared Origin and Referer vectors proving rejection.
Consider rejecting non-origin components in Origin values as part of the same
strict parser rather than silently reducing arbitrary URLs to tuples.

### MEDIUM-3: cookie path normalization can target a different cookie

The cookie contract owns the configured session and remember tuples and says
only that an **unset** path normalizes to `/`. `_normalized_cookie_path` also
removes every trailing slash from a configured non-root path. A cookie set with
configured path `/weppcloud/` is distinct from one at `/weppcloud`; deleting
the latter does not reliably clear the former. The new exact-target test
expects this stripping and therefore codifies behavior contrary to the
configured tuple rather than detecting the regression.

There is a second untested tuple edge: `_clear_reset_browser_state_cookies`
deduplicates by cookie name alone. If session and remember cookies intentionally
share a name but have distinct paths or domains, the second owned tuple is not
deleted. The contract enumerates both tuples and does not authorize name-only
deduplication.

Required disposition: preserve a configured path byte-for-byte (normalizing
only unset/empty paths to `/`), deduplicate complete `(name, path, domain)`
tuples if deduplication is needed, and test trailing-slash plus same-name,
different-tuple configurations.

### LOW-1: malformed Host ports can escape as `ValueError`

The changes correctly catch `ValueError` from `parsed.port` inside each
`_normalized_origin`, but rq-engine `_request_origin` reads
`request.url.port` directly and query-engine `_request_allowed_origins` does the
same. A malformed authoritative Host port can therefore raise before the
predicate reaches its fail-closed normalization path, producing a server error
instead of a deterministic rejection.

Required disposition: make request-origin construction fail closed on invalid
ports and add malformed Host/port cases. This should use the same behavior
across both ASGI services.

## Positive evidence

- The narrow bridge implementations require application `http:80`, browser
  `https:443`, `Sec-Fetch-Site: same-origin`, and the same request host. The
  shared vector proves this principal topology and proves a conflicting
  explicit port and subdomain reject.
- `cross-site` wins over an otherwise exact Origin on all three predicates.
  Raw forwarded host/proto aliases were removed as allowed-origin inputs, and
  the rq-engine legacy switch is exercised as inert.
- Missing all signals now rejects consistently; exact Origin and Referer
  fallback pass consistently in the shared cases.
- Reset no longer targets generic `csrf_token` or `csrftoken` names and keeps
  an unset remember domain host-only instead of borrowing the session domain.
- The diagnostics report implementation uses an immutable fixed catalog,
  catalog ordering, fixed status text, unknown-ID omission, first-occurrence
  duplicate handling, recomputed overall status, locally generated timestamp,
  and constrained path-only site prefix. The hostile-value test covers runtime
  title, severity, evidence, fix hint, overall, timestamp, URL/hostname,
  duplicate ID, unknown ID, and site-prefix disclosure.
- Flask-WTF tests prove valid CSRF succeeds and missing/invalid CSRF rejects
  before the route-level origin guard. Existing rq-engine authentication and
  query-engine rate-limit/boundary tests remain in the focused suites.

## Validation evidence

Executed:

```text
wctl run-pytest tests/microservices/test_rq_engine_session_routes.py \
  tests/query_engine/test_server_routes.py \
  tests/weppcloud/routes/test_rq_engine_token_api.py \
  tests/weppcloud/routes/test_csrf_rollout.py --maxfail=1
```

Result: **133 passed**, 30 warnings, 15.53 seconds.

Executed the focused diagnostics report Jest suite through `wctl run-npm test`.
Result: **1 suite passed, 2 tests passed**.

These green results establish the implemented happy paths and current shared
vector parity, but they do not negate the uncovered contract cases in
MEDIUM-1 through MEDIUM-3.

## Closure assessment

The working tree still has WP01-WP04 prompts active and the ExecPlan progress
and outcomes are not closed. That is appropriate while the findings above
remain unresolved. After remediation, rerun the focused suites, the complete
shared matrix on all three guards, JavaScript gates, full Python gate, and both
independent final reviews before retiring prompts or marking REM-04 complete.

## Post-fix rereview

Rereviewed the remediated working tree on 2026-07-28 against the same checkpoint,
ExecPlan, prompts, and canonical contracts.

### Finding dispositions

- **MEDIUM-1 resolved.** Query-engine now adds explicitly configured
  `OAUTH_REDIRECT_HOST`/`EXTERNAL_HOST` with the resolved public scheme to its
  allowed-origin set. The bridge accepts only the exact `http:80` application
  to `https:443` browser pair and requires the Origin host to be among the
  authoritative request or configured allowed hosts. Shared vectors exercise
  both an exact configured public Origin and a configured-public-host bridge on
  all three guards.
- **MEDIUM-2 resolved.** All three normalizers reject user information,
  non-origin paths, parameters, queries, fragments, unsupported schemes, and
  malformed ports. The shared matrix now covers Origin user information, path,
  query, and fragment cases plus Referer user information on every guard.
- **MEDIUM-3 resolved.** Cookie deletion preserves a configured trailing slash,
  normalizes only an unset/empty path to `/`, and deduplicates the complete
  `(name, path, domain)` tuple. Tests prove both the trailing-slash/host-only
  case and same-name cookies with distinct owned tuples.
- **LOW-1 resolved.** Both ASGI request-origin paths catch malformed URL-port
  access and fail closed. rq-engine and query-engine each have a direct
  malformed-Host-port regression test.

### Rereview validation

Executed:

```text
wctl run-pytest tests/microservices/test_rq_engine_session_routes.py \
  tests/query_engine/test_server_routes.py \
  tests/weppcloud/routes/test_rq_engine_token_api.py \
  tests/weppcloud/routes/test_csrf_rollout.py --maxfail=1
```

Result: **157 passed**, 30 warnings, 15.21 seconds.

### Final rereview verdict

**PASS.**

Remaining counts: **0 critical, 0 high, 0 medium, 0 low**. All four original
findings are resolved with implementation and regression evidence. This
correctness/compatibility review has no remaining objection to REM-04 closure,
subject to the package's other required gates and independent security review.
