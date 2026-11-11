# Tracker - Status and preflight WebSocket run authorization

## Quick Status

**Timezone**: UTC  
**Last updated**: 2026-11-11 15:49 UTC  
**Current phase**: M4 validation and independent review
**Finding**: F4 / SEC-04 (Medium; high likelihood)  
**Change security impact**: high  
**Starting revision**: `b7c2e44d5947aabeda22f19e55b0b91d7f0baca1`  
**Dedicated security review**: `artifacts/20261111_security_review.md`

M0 is ratified in standalone ancestor `6a06ad49a`. M1-M3 are implemented;
focused checks pass and broad gates are running. Forest deployment and actual
browser acceptance remain mandatory. Production deployment is not authorized.

## Task Board

- [x] Map F4/SEC-04 and audit tasks W-01 through W-05 into this package.
- [x] Confirm current frontend connections carry no token and current services
      can accept before run authorization.
- [x] Scaffold the package, active ExecPlan, contract proposal, failure matrix,
      and independent review gates.
- [x] Record mandatory forest redeploy and browser proof for both status and
      preflight token handshakes.
- [x] M0 discovery and two independent read-only reviews; canonical draft,
      dependency evaluation and ADR-0141 prepared (not accepted).
- [x] M0: ratify token/public-run/message contracts, evaluate the Go JWT option,
      obtain two independent read-only reviews, and commit a standalone
      checkpoint ancestor.
- [x] M1: add the stream-token minting boundary and focused Python tests.
- [x] M2: add frontend credential transport, refresh/reconnect behavior,
      generated controller parity, and focused Jest tests.
- [x] M3: add status2/preflight2 pre-accept validation, Redis/session checks,
      exact Origin configuration, message redaction, and Go integration tests.
- [ ] M4: run focused gates, full pytest, npm lint, full npm tests, and close
      correctness, QA, and security review findings.
- [ ] M5: render and validate forest Compose; drain affected work safely;
      redeploy only affected services; check health and rollback readiness.
- [ ] M6: run actual forest browser E2E for both token-bearing handshakes,
      authorized messages, negative cases, secret non-retention, and cleanup.
- [ ] M7: update the audit board with evidence and close or disposition SEC-04.

## Confirmed Starting Evidence

- `wepppy/weppcloud/controllers_js/status_stream.js` constructs the status
  WebSocket URL and calls `new WebSocket(wsUrl)` without a credential.
- `wepppy/weppcloud/static/js/preflight.js` constructs the preflight URL and
  calls `new WebSocket(wsUrl)` without a credential.
- `services/status2/internal/server/server.go` and
  `services/preflight2/internal/server/server.go` perform method/path/Origin
  handling around the upgrade but do not establish run authorization first.
- The audit cites `docker/caddy/Caddyfile.wepp1:26`,
  `docker/docker-compose.prod.yml:718,743`, and
  `wepppy/rq/project_rq.py:3203` as adjacent configuration/message evidence.
- Origin validation is a defense-in-depth check, not proof that the caller may
  inspect the named run.

Line numbers are discovery aids, not durable contract references; re-read the
current source before implementation.

## Decisions

- Decision (operator, 2026-11-11): tests must include redeploying to forest and
  end-to-end validation that the frontend sends tokens to the status and
  preflight endpoints. This is a non-waivable package closeout gate.
- Decision: forest is the only authorized deployment target in this package.
  No forest1/wepp1/wepp2/wepp3/openwepp.org action is implied.
- Decision: use a contract-first checkpoint because the change spans browser,
  RQ/session, Go services, Redis, and Compose security boundaries.
- Ratified: mint a short-lived run-bound stream token and send
  it through `Sec-WebSocket-Protocol`, with a fixed negotiated protocol and the
  bearer value excluded from the selected protocol and all retained evidence.
- Ratified: a five-minute default lifetime, explicit status2
  and preflight2 audiences, `status:read`/`preflight:read` scopes, exact run and
  session binding, and live marker/revocation checks.
- Decision: no new JWT library or hand-written crypto may enter implementation
  until the dependency evaluation gate is satisfied.
- Decision: W-05 owns only confirmed status/preflight message disclosures;
  general HTTP traceback response work remains F5.

## Validation Matrix

| Boundary | Positive case | Negative/hostile cases | Evidence |
| --- | --- | --- | --- |
| Token mint | Authorized private owner/collaborator/admin; contracted public reader | Anonymous private, unrelated user, invalid config/run | Python route tests |
| Token claims | Exact run, audience, scope, class and live session | Forged, expired, future, wrong issuer/audience/scope/class, revoked or missing marker | Python and Go tests |
| status2 upgrade | Valid same-origin `status:read` token | Missing, malformed, cross-run, hostile Origin | Go integration test before Redis access |
| preflight2 upgrade | Valid same-origin `preflight:read` token | Missing, malformed, cross-run, hostile Origin | Go integration test before Redis access |
| Browser transport | Both clients send fixed protocol plus bearer-shaped protocol | Token in URL, selected protocol, storage, log or artifact | Jest and Playwright/CDP assertions |
| Reconnect | Expiry/auth failure causes bounded refresh and reconnect | Retry loop, stale-token replay, downgrade to unauthenticated | Fake-clock Jest and E2E |
| Messages | Intended progress/checklist fields render | Absolute path, exception detail, sensitive option leakage | Schema/redaction tests and sanitized samples |
| Forest | Redeployed services healthy; both authorized streams deliver | No-token and cross-run private connections denied | Actual browser E2E after redeploy |

## Required Forest Runbook Evidence

Before mutation, record host, repository path, branch/revision, installed `wctl`
preset, rendered Compose, affected container identities, health, and queue/job
state. Do not cancel active jobs; wait or drain within the existing operator
workflow. Resolve the exact canonical service-scoped command on forest rather
than inventing another deployment path.

Expected affected services are `rq-engine`, `weppcloud`, `status`, and
`preflight`; recreate `caddy` only if its rendered routing/origin configuration
actually changes. Record image IDs, container start times, health checks, and a
known-good rollback mapping. Use exact forest Origin
`https://forest.tail305ec9.ts.net`.

The Playwright smoke must authenticate using the gitignored
`docker/secrets/dev-agent.env`, create or open disposable private runs through
existing UI/test helpers, and inspect `Network.webSocketWillSendHandshakeRequest`
events in memory. It may decode only non-secret claims needed for assertions and
must not print or persist the raw protocol header/token. Prove:

- the status and preflight WebSocket URLs contain no token/query secret;
- each request carries the fixed protocol and a bearer-shaped credential;
- sanitized claims bind to the intended run, service audience/scope and a short
  validity window;
- preflight supplies its intended initial/update behavior;
- a unique harmless status marker published to the disposable run's existing
  Redis channel is observed by the browser without a public test backdoor;
- missing-token and run-A-token-to-private-run-B cases receive no message; and
- logs, artifacts, selected protocols, browser storage and cleanup receipts
  contain no raw credential.

Clean up disposable runs and Redis test markers. Retain the exact revision,
browser version, container identities/times, sanitized assertions, health/log
summary, negative results, and cleanup receipt.

## Review Gates

- [ ] Contract and valid-state matrices accepted.
- [ ] Two independent read-only contract reviews closed.
- [ ] Dependency evaluation and any required parameterization ADR accepted.
- [ ] Correctness review passed.
- [ ] QA review passed.
- [ ] Dedicated security review passed.
- [ ] Forest operations/deployment review passed.
- [ ] Audit board SEC-04 status updated from evidence, not from implementation
      intent.

## Timeline

- 2026-11-11 15:49 UTC: scaffold package and record the forest E2E requirement.
- Pending: M0 contract checkpoint and dependency disposition.
- Pending: M1-M3 implementation with focused tests.
- Pending: M4 complete local/broad validation and independent reviews.
- Pending: M5-M6 authorized forest redeploy and end-to-end acceptance.

## Handoff

Continue from `prompts/active/implementation_execplan.md`. Preserve unrelated
dirty work. Update this tracker and the active ExecPlan at every stopping point.
Do not describe F4 as fixed until the actual forest browser gate and independent
reviews pass. Production deployment remains separately authorized.

## Operator ratification (2026-11-11)

The operator explicitly approved all three proposed lifecycle policies and
instructed ratification and implementation. The canonical contract and ADR now
record that approval. Final independent confirmation and standalone ancestor
commit precede code edits; no further policy permission is required.

M0 completed: standalone ratified ancestor `6a06ad49a`; both independent reviews
approved. M1-M3 implemented; M4 broad validation ongoing; forest acceptance pending.
