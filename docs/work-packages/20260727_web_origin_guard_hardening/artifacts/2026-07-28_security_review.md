# Security Review - Web-origin guard hardening

## Metadata

- **Package**: `docs/work-packages/20260727_web_origin_guard_hardening/`
- **Reviewer**: Codex independent security reviewer (`rem04_final_security`)
- **Date**: 2026-07-28
- **Scope reviewed**: Flask, rq-engine, and query-engine same-origin guards;
  Flask CSRF layering and browser-state reset; rq-engine cookie authentication;
  query-engine bandwidth abuse controls; diagnostics copied-report disclosure
- **Commit/branch context**: working tree reviewed against checkpoint ancestor
  `736198ce8a4b68b83a9c77860a52da574f2cc98d`
- **Related artifacts**:
  - Contract decision:
    `artifacts/2026-07-28_contract_decision.md`
  - Checkpoint security/governance review:
    `artifacts/2026-07-28_checkpoint_security_governance_review.md`
  - Checkpoint correctness/compatibility review:
    `artifacts/2026-07-28_checkpoint_correctness_compatibility_review.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: The change modifies browser-origin authorization on
  cookie-authenticated mutations, CSRF-adjacent session/token routes, an
  unauthenticated bandwidth endpoint, cookie deletion scope, and a
  user-copyable disclosure boundary.
- **Threat model assumptions**:
  - Flask is reachable only through the final trusted proxy; that proxy replaces
    inbound forwarding headers before the one-hop `ProxyFix`.
  - rq-engine and query-engine do not obtain origin authority from raw
    forwarded host/proto headers.
  - Browser Fetch Metadata is an origin signal, not authentication or a
    substitute for Flask-WTF CSRF or rq-engine session validation.
  - The query-engine bandwidth limiter's right-most `X-Forwarded-For` value is
    trustworthy only when the final proxy appends/replaces that hop and direct
    service access is prevented.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Shared same-origin parsing | All three `_normalized_origin` implementations reduce syntactically non-origin URLs to an allowed `(scheme, host, port)` tuple. User information, a path, or a fragment is silently discarded, so values the canonical contract declares invalid can authorize when the remaining tuple matches. The shared matrix has no hostile userinfo/path/fragment vectors. This is fail-open parsing at a browser security boundary even though conforming browsers do not normally emit these forms. | `wepppy/weppcloud/routes/weppcloud_site.py:307`; `wepppy/microservices/rq_engine/session_routes.py:208`; `wepppy/query_engine/app/server.py:160`; manual probe returned `('https', 'guard.test', 443)` in all three implementations for `https://attacker@guard.test`, `https://guard.test/unexpected-path`, and `https://guard.test#fragment`; `docs/schemas/weppcloud-csrf-contract.md` states user information and malformed origins do not produce a tuple. | Reject credentials, paths other than empty, query strings, and fragments in the shared origin parser behavior; add the same hostile vectors to `tests/web_origin_vectors.py` and execute them across all three adapters. | Open |

No other high, medium, or low findings were identified.

## Verdict

- **Gate status**: `fail`
- **Unresolved findings**:
  - High: 0
  - Medium: 1
  - Low: 0
- **Release recommendation**: hold until SEC-01 is resolved and independently
  rereviewed. High-triage package closure requires zero unresolved medium/high
  findings.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Changed Flask routes retain authenticated-session checks where required.
- [x] rq-engine bearer authentication remains distinct from the cookie path.
- [x] rq-engine cookie issuance retains session existence, identity, and
  run-authorization checks after the origin gate.
- [x] Flask-WTF rejects missing/invalid CSRF before the same-origin predicate;
  valid CSRF does not override a conflicting origin.
- [ ] Origin input validation is not contract-conformant (SEC-01).
- [x] Error responses do not disclose tokens or session contents.

### 2) Secrets and Credential Handling

- [x] No new secrets, secret defaults, query-string credentials, or credential
  logging were introduced.
- [x] Existing required-secret failures remain explicit.

### 3) Input Validation and Output Safety

- [ ] Origin URL grammar validation is incomplete (SEC-01).
- [x] Origin host, scheme, effective port, opaque origin, explicit-port
  conflict, subdomain conflict, and cross-site Fetch Metadata cases otherwise
  have regression coverage.
- [x] Conflicting present Origin is not overridden by
  `Sec-Fetch-Site: same-origin`.
- [x] Copied diagnostics are rebuilt from a fixed catalog and fixed status
  messages; hostile runtime titles, severities, evidence, URLs, timestamps,
  prefixes, duplicate IDs, and unknown IDs are excluded by tests.

### 4) File System and Run-Tree Boundaries

- [x] No file-system or run-tree behavior changed.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] No queue wiring, worker, subprocess, or retry behavior changed.

### 6) Agentic Tooling and MCP Surfaces

- [x] No agentic tooling or MCP surface changed.

### 7) Network and External Integrations

- [x] Raw forwarded host/proto headers do not add allowed origins; the legacy
  rq-engine forwarded-origin switch is inert.
- [x] The Flask bridge depends on the documented one-hop `ProxyFix` and
  final-proxy-only deployment assumption.
- [x] Query bandwidth responses retain bounded size, streaming upload cap,
  read timeout, concurrency semaphore, bounded rate-limit buckets, and
  per-path rate limiting.
- [x] No new outbound integration was introduced.
- [x] The right-most forwarded-client rate-limit key remains a deployment trust
  assumption, not a newly widened origin authority.

### 8) CI/CD and Supply Chain

- [x] No workflow, runner permission, build dependency, or third-party
  dependency changed.

### 9) Data Integrity, Locking, and Concurrency

- [x] No NoDb, Redis persistence, or project-data contract changed.
- [x] Query bandwidth concurrency and rate-limit state remain bounded.

### 10) Logging, Monitoring, and Incident Readiness

- [x] No new broad exception swallowing or sensitive-value logging was found.
- [x] Origin denials remain explicit 403 responses.
- [x] Package rollback scope is documented in the active ExecPlan.

## Validation Evidence

- Automated checks run:
  - `wctl run-pytest tests/weppcloud/routes/test_csrf_rollout.py tests/weppcloud/routes/test_rq_engine_token_api.py tests/microservices/test_rq_engine_session_routes.py tests/query_engine/test_server_routes.py --maxfail=1`
    - 133 passed, 30 warnings.
  - `wctl run-npm test -- --runInBand wepppy/weppcloud/controllers_js/__tests__/diagnostics_report.test.js`
    - 1 suite passed, 2 tests passed.
  - `git diff --check 736198ce8a4b68b83a9c77860a52da574f2cc98d`
    - passed.
- Manual checks run:
  - Compared implementation and tests with the checkpoint ancestor and
    canonical CSRF, session, and diagnostics contracts.
  - Probed all three origin normalizers with userinfo, path, and fragment
    payloads; all three incorrectly returned the matching authoritative tuple.
  - Traced rq-engine cookie-token issuance to confirm same-origin evaluation
    precedes session-cookie validation and that successful issuance still
    requires session/run authorization (apart from the documented public-run
    fallback).
  - Traced query bandwidth download/upload boundaries and confirmed byte caps,
    timeout, semaphore, rate-limit bucket bound, and `no-store` responses.
  - Compared exact reset deletion calls with configured session and remember
    tuples; no generic CSRF or synthesized parent-domain deletion remains.

## Residual Risk

- **Accepted residual risks**:
  - None. SEC-01 is not accepted risk.
- **Follow-up packages/issues**:
  - None recommended; SEC-01 is a bounded correction inside REM-04.

## Sign-off

- **Security reviewer**: Codex independent security reviewer
  (`rem04_final_security`), 2026-07-28 — **FAIL**
- **Package owner**: pending after finding disposition and rereview

## Post-fix Rereview - 2026-07-28

SEC-01 is resolved. All three `_normalized_origin` implementations now reject
URLs containing user information, a non-root path, parameters, a query, or a
fragment before producing an origin tuple. They also handle an invalid port as
an explicit rejection. Referer fallback remains subject to the same strict
authority parsing.

The shared matrix now includes hostile Origin values containing userinfo, path,
query, and fragment components, plus a Referer containing userinfo. The matrix
executes against Flask, rq-engine, and query-engine adapters.

Post-fix evidence:

- `wctl run-pytest tests/weppcloud/routes/test_csrf_rollout.py tests/weppcloud/routes/test_rq_engine_token_api.py tests/microservices/test_rq_engine_session_routes.py tests/query_engine/test_server_routes.py --maxfail=1`
  - 157 passed, 30 warnings.
- Manual probes of all three normalizers returned `None` for:
  - `https://attacker@guard.test`
  - `https://guard.test/unexpected-path`
  - `https://guard.test?x=1`
  - `https://guard.test#fragment`
- Read-only review confirmed that the strict checks occur before tuple
  comparison and before the constrained upstream-TLS bridge.

Post-fix finding counts:

- High: 0
- Medium: 0
- Low: 0

Post-fix verdict:

- **Gate status**: `pass`
- **Release recommendation**: ship, subject to the package's remaining
  correctness, QA, and closeout gates.
- **Security reviewer**: Codex independent security reviewer
  (`rem04_final_security`), 2026-07-28 — **PASS**
