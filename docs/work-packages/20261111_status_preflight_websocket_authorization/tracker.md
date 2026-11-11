# Tracker - Status and preflight WebSocket run authorization

## Quick Status

**Timezone**: UTC  
**Last updated**: 2026-11-11 20:30 UTC
**Current phase**: Closed — forest acceptance complete
**Finding**: F4 / SEC-04 (Medium; high likelihood)  
**Change security impact**: high  
**Starting revision**: `b7c2e44d5947aabeda22f19e55b0b91d7f0baca1`  
**Dedicated security review**: `artifacts/20261111_security_review.md`

M0-M7 complete for forest. Full regression, five-service cutover, 27 browser
assertions and scoped cleanup recovery are verified. See the combined acceptance
receipt; production deployment remains separately authorized.

## Task Board

- [x] Map F4/SEC-04 and audit tasks W-01 through W-05 into this package.
- [x] Confirm current frontend connections carry no token and current services
      can accept before run authorization.
- [x] Scaffold the package, active ExecPlan, contract proposal, failure matrix,
      and independent review gates.
- [x] Record mandatory forest redeploy and browser proof for both status and
      preflight token handshakes.
- [x] M0 discovery and two independent read-only reviews; canonical draft,
      dependency evaluation and ADR-0141 accepted at `6a06ad49a`.
- [x] M0: ratify token/public-run/message contracts, evaluate the Go JWT option,
      obtain two independent read-only reviews, and commit a standalone
      checkpoint ancestor.
- [x] M1: add the stream-token minting boundary and focused Python tests.
- [x] M2: add frontend credential transport, refresh/reconnect behavior,
      generated controller parity, and focused Jest tests.
- [x] M3: add status2/preflight2 pre-accept validation, Redis/session checks,
      exact Origin configuration, message redaction, and Go integration tests.
- [x] M4: run focused gates, full pytest, npm lint, full npm tests, and close
      correctness, QA, and security review findings.
- [x] M5: render and validate forest Compose; drain affected work safely;
      redeploy only affected services; check health and rollback readiness.
- [x] M6: run actual forest browser E2E for both token-bearing handshakes,
      authorized messages, negative cases, secret non-retention, and cleanup.
- [x] M7: update the audit board with evidence and close or disposition SEC-04.

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

- [x] Contract and valid-state matrices accepted.
- [x] Two independent read-only contract reviews closed.
- [x] Dependency evaluation and any required parameterization ADR accepted.
- [x] Correctness review passed.
- [x] QA review passed.
- [x] Dedicated security review passed.
- [x] Forest operations/deployment review passed.
- [x] Audit board SEC-04 status updated from evidence, not from implementation
      intent.

## Timeline

- 2026-11-11 15:49 UTC: scaffold package and record the forest E2E requirement.
- 2026-11-11: M0 ratified at `6a06ad49a`.
- 2026-11-11: M1-M3 implemented; code reviews approved; focused suites pass.
- Completed: M4 full regression and independent reviews.
- Completed: M5-M6 forest redeploy, browser assertions and scoped cleanup recovery.

The third full pytest attempt stopped after 9,803 passed and 429 skipped
(3,491.79 seconds) because the new browser-only route was missing from the
endpoint inventory. Promoted the unchanged existing table from its closed
package to `docs/schemas/rq-engine-endpoint-inventory.md`, added the stream-token
row, and switched the three readers, canonical pointers and generated CI path
filters. Both inventory/checklist guards pass. A focused pass over the remaining
test directories precedes another unsegmented full run; neither partial result
is a full-suite pass. This exposed a maintenance gap: route onboarding should
name the inventory guard before the expensive full suite.

QA tightened the forest harness before deployment: wait for Redis subscribers,
require a fresh preflight frame after renewal, log out explicitly, and clear the
disposable run cache before deletion. Cleanup supports already-absent runs; NFS partial deletion required the scoped recovery recorded below.

Remaining-directory precheck found one additional integration omission after
3,704 passes: diagnostics needed the standard deferred stale-controller check
immediately after its new controller bundle. Added that companion script;
all 2,370 web and OpenAPI checks pass (205.58 seconds), and QA approved the fix.
The fourth unsegmented full suite started at revision `fadc8847b`; forest cutover
was held until it passed. No partial run is counted as full-suite proof.
## Handoff

Forest scope is complete. Read the completed ExecPlan and
`artifacts/20261111_forest_acceptance.json`; the original browser aggregate failed
only NFS cleanup and is retained alongside verified recovery. SEC-04 production
rollout remains pending separately authorized deployment. Preserve unrelated
worktree changes.

## Operator ratification (2026-11-11)

The operator explicitly approved all three proposed lifecycle policies and
instructed ratification and implementation. The canonical contract and ADR now
record that approval. Final independent confirmation and standalone ancestor
commit precede code edits; no further policy permission is required.

M0 completed: standalone ratified ancestor `6a06ad49a`; both independent reviews
approved. M1-M6 are now implemented and verified; final forest evidence is retained.

M4 completed: full pytest passed (13,568 passed / 435 skipped, 3,785.08 seconds) at `fadc8847b`. Local gates and independent code reviews pass. Proceeding to authorized forest cutover and browser acceptance.

M5 completed: five forest containers recreated, all running with zero restarts;
login and rq-engine/status/preflight health return HTTP 200. Caddy header filter
is verified active. Canonical candidate web build and image/stability gates
passed. M6 browser assertions and scoped cleanup recovery subsequently passed; see combined acceptance.

Final closeout: M0-M7 complete for forest; all three final evidence reviews
approved. SEC-04 remains READY FOR REVIEW on the production audit board pending
a separately authorized rollout; W-01 through W-05 are VERIFIED on forest.
