# Status and preflight WebSocket run authorization

**Status**: Closed 2026-11-11 (forest scope); production rollout pending separate authorization

**Timezone**: UTC

## Overview

Remediate security audit finding F4/SEC-04 by requiring run-bound authorization
for the status2 and preflight2 WebSocket services. At discovery, the browser opened both streams without a token and the services
could accept after method, path and Origin checks alone. The implemented
contract now requires run authorization before acceptance and run-specific Redis access.

This package defines a short-lived stream credential, sends it from the existing
WEPPcloud frontend without placing it in a URL, validates it before WebSocket
acceptance or Redis access, and preserves an explicitly reviewed public-run
policy. Exact Origin allowlists remain defense in depth. Published stream
messages also receive a bounded redaction review for paths, exception details,
and sensitive options.

The operator requires an actual redeploy to the **forest** development stack and
an end-to-end browser check proving that the frontend sends tokens to both the
status and preflight handshakes. That environment gate is mandatory for package
closure. It does not authorize deployment to forest1, wepp1, wepp2, wepp3,
openwepp.org, or any other production system.

## Threat Model

- **Assets**: private run identity and progress, preflight results, Redis channel
  contents, run paths and options, authenticated browser sessions, and signing
  material.
- **Adversaries/failures**: an anonymous or unrelated user who guesses a run ID;
  a cross-run token replay; a hostile Origin; a leaked credential in URLs or
  logs; and frontend reconnect behavior that silently drops authorization.
- **Trust boundaries**: browser session to token minting endpoint; browser to
  Caddy to the two Go WebSocket services; JWT validation to Redis-backed session
  state; run-specific WebSocket paths to run-specific Redis subscriptions.
- **High-value paths**: private run status disclosure, preflight disclosure,
  cross-run subscription, message data leakage, and signing-secret exposure.
- **Assumptions to prove**: authorization completes before WebSocket acceptance
  and before run-channel Redis access; tokens bind to one run and service scope;
  public access is explicit; the browser sends credentials without putting them
  in URLs or persistent storage; forest uses exact allowed origins.

## Objectives

- Ratify a canonical WebSocket authorization contract for status2 and
  preflight2, including token class, issuer, audience, scopes, run binding,
  lifetime, public-run behavior, transport, and error behavior.
- Mint the least-privileged short-lived credential through an existing
  authenticated and same-origin WEPPcloud/RQ boundary.
- Send the credential from both browser clients using a transport supported by
  the WebSocket API without query-string or cookie token leakage.
- Validate signature and claims, session marker/revocation state, run equality,
  required service scope, and exact Origin before accepting the socket.
- Reject missing, malformed, forged, expired, future, revoked, wrong-audience,
  wrong-scope, and cross-run credentials before per-run Redis access.
- Inventory and redact sensitive fields from status/preflight messages while
  preserving legitimate progress and checklist behavior.
- Rebuild and redeploy only the affected forest services, then retain sanitized
  browser evidence that both frontend handshakes carry the expected run-bound
  authorization.

## Scope

### Included

- A new canonical `docs/schemas/weppcloud-websocket-auth-contract.md` and
  corresponding amendments to token, CSRF, service, frontend, and deployment
  documentation.
- The rq-engine/WEPPcloud minting boundary required for a short-lived stream
  credential, reusing current private/public run authorization and Redis-backed
  session revocation semantics.
- `WCHttp`, `StatusStream`, and preflight browser code, including generated
  status controller output and reconnect/refresh behavior.
- status2 and preflight2 configuration and server validation before socket
  acceptance and Redis subscription.
- Exact `STATUS_ALLOWED_ORIGINS` and `PREFLIGHT_ALLOWED_ORIGINS` configuration
  for forest and production Compose sources. Empty allowlists must fail closed
  outside an explicitly named, default-off local-development mode.
- A bounded message-field inventory and redaction repair for confirmed status
  and preflight disclosures. General HTTP traceback-envelope work remains F5.
- Focused Python, Go, Jest, and Playwright coverage; full canonical Python and
  frontend gates; rendered Compose checks; and actual forest deployment and
  browser acceptance.

### Explicitly Out of Scope

- Changing the authorization policy of unrelated HTTP, query-engine, RQ, file,
  or report endpoints.
- A general authentication redesign, long-lived browser token, local-storage
  credential, URL/query credential, or token-bearing cookie for the Go services.
- New public access beyond the existing canonical public-run inspect policy.
- A public test bypass, debug credential endpoint, Redis backdoor, or logging of
  bearer material to prove the browser handshake.
- General error-envelope remediation owned by F5, or unrelated status/preflight
  feature and UI changes.
- Deployment to production. Forest validation is a release prerequisite, not
  production authorization.

## Ratified Contract

The [canonical WebSocket authorization contract](../../schemas/weppcloud-websocket-auth-contract.md)
and ADR-0141 were ratified in standalone ancestor `6a06ad49a` after operator
approval and two independent reviews. Tokens are service-specific, expire after
five minutes, bind the exact run/config and live session, and use only the fixed
plus bearer subprotocol transport. The negotiated protocol is always the fixed
value; URLs and retained diagnostics contain no credential.

The approved lifecycle policies permit no-cookie inspection only for verified
existing ownerless/public projects, restricted Admin/Root job/channel-bound
status inspection for pending run-sync, and selected-project diagnostics. The
owned `services/streamauth` component uses the evaluated `jwt/v5` dependency;
custom cryptography and anonymous fallback are excluded.

## Complexity Budget

- **Existing mechanisms reused**: current run-access checks, RQ JWT signing and
  Redis DB 11 session markers/revocation, `WCHttp`, WebSocket service paths,
  Caddy routing, Compose secrets, Playwright smoke infrastructure, and `wctl`.
- **New mechanisms permitted**: one short-lived stream-token route; one shared
  owned Go validator; one vetted JWT dependency only if the dependency gate
  approves it; focused browser handshake instrumentation.
- **Simplest plausible path**: add authentication to the two existing services
  and clients without a new service, datastore, daemon, or network boundary.
- **Evidence required before escalation**: retained proof that the shared
  validator or existing session store cannot meet a contract requirement.
- **Prohibited expansion**: a second identity system, token proxy, durable token
  store in the browser, public debug route, or service-topology redesign.

## Generated Artifact Validation Gate

- **Applicable**: no for durable application artifacts. The changed products
  are ephemeral authenticated streams and generated frontend code.
- **Generated-code requirement**: rebuild `static/js/status_stream.js` from its
  controller source and verify source/generated parity.
- **Runtime evidence**: retain exact source revision, container image IDs/start
  times, rendered configuration hashes, sanitized CDP handshake assertions,
  observed authorized messages, denial cases, and cleanup receipt.
- **Direct unmocked boundary**: an actual browser against the redeployed forest
  stack, plus real status/preflight services and Redis; success codes alone are
  insufficient.
- **Sensitive-evidence rule**: raw JWTs, protocol headers, credentials, private
  message bodies, and secret values remain in memory and must not be persisted.
- **Highest completion claim supported**: implementation, full regression, three
  independent final reviews and deployed forest browser acceptance pass. NFS
  cleanup recovery is verified separately. Production rollout is not claimed.

## Stakeholders

- **Decision owner**: WEPPpy maintainer and forest operator.
- **Primary implementers**: rq-engine, WEPPcloud frontend, status2, preflight2,
  and Compose maintainers.
- **Reviewers**: independent correctness, QA, security, and forest operations
  reviewers.
- **Security reviewer**: required and independent of the implementation author.

## Success Criteria

- [ ] The WebSocket auth contract and valid-state matrix are ratified before
      implementation, independently reviewed, and committed as a standalone
      ancestor checkpoint.
- [ ] The minting endpoint preserves private owner/collaborator/admin access and
      only the explicitly approved public-run behavior.
- [ ] Both browser clients obtain, cache only briefly, refresh, and send the
      stream credential without placing it in a URL or persistent storage.
- [ ] status2 and preflight2 validate all required claims and live session state
      before WebSocket acceptance and before run-channel Redis access.
- [ ] Missing, malformed, forged, expired, future, revoked, wrong-issuer,
      wrong-audience, wrong-scope, wrong-class, and cross-run cases fail closed.
- [ ] Exact Origin checks pass for configured same-origin requests and reject a
      hostile Origin; Origin is not treated as authorization.
- [ ] Confirmed sensitive status/preflight message fields are removed or
      redacted without breaking legitimate progress/checklist behavior.
- [ ] Focused Python, Go, Jest, Playwright, secret-leak, and generated-code gates
      pass, followed by full pytest, npm lint, and full npm tests.
- [ ] A service-scoped forest redeploy succeeds with rendered configuration,
      health, container identity, rollback, and sanitized log evidence.
- [ ] Browser E2E proves the frontend sends a correctly scoped, run-bound token
      to both status and preflight handshakes and receives intended messages.
- [ ] Browser and service evidence proves no token appears in URLs, selected
      protocols, logs, persisted artifacts, or retained test output.
- [ ] Independent correctness, QA, security, and operations reviews pass.

## Parameterization ADR Gate

- **Parameterization change present**: a token lifetime and any explicit local
  development Origin bypass are security thresholds rather than scientific
  parameters.
- **ADR required**: determine at the M0 contract checkpoint. If the selected
  values are configurable defaults or thresholds, author the required ADR under
  `docs/standards/parameterization-adr-standard.md` before implementation.
- **Decision provenance**: retain the value, threat rationale, alternatives,
  and owner approval in the contract decision artifact.

## Dependencies

### Prerequisites

- Ratify the token and public-run valid-state matrices.
- Complete dependency evaluation before adding a Go JWT library.
- Confirm forest operator access and gitignored `docker/secrets/dev-agent.env`
  without copying credentials into tracked or retained evidence.
- Capture pre-change service/frontend baselines and exact forest deployment
  topology before modifying runtime state.

### Blocks

- Closure of security audit finding F4/SEC-04.

## Related Contracts and Evidence

- `docs/dev-notes/auth-token.spec.md`
- `docs/schemas/weppcloud-csrf-contract.md`
- `docs/standards/contract-first-change-standard.md`
- `docs/standards/dependency-evaluation-standard.md`
- `docs/standards/hardening-lifecycle-standard.md`
- Security audit board Phase 4 at the gitignored
  `out/security-audit-20261110/wepp1-security-audit-orchestration-board.md`
- Initial contract proposal:
  [artifacts/20261111_contract_decision.md](artifacts/20261111_contract_decision.md)
- Failure-class inventory:
  [artifacts/20261111_failure_class_matrix.md](artifacts/20261111_failure_class_matrix.md)

## Timeline Estimate

- **Expected duration**: 4-8 focused working days, including review and forest
  acceptance.
- **Complexity**: high because one identity contract crosses Python, browser
  JavaScript, two Go services, Redis, Caddy/Compose, and an actual environment.
- **Finding severity**: Medium with high likelihood in the audit model.
- **Change security impact**: high.

## Security Impact and Review Gate

- **Security impact triage**: high.
- **Dedicated security review required**: yes.
- **CWE/OWASP mapping**: CWE-862 (Missing Authorization), CWE-639
  (Authorization Bypass Through User-Controlled Key), CWE-922 (Insecure Storage
  of Sensitive Information); OWASP Top 10 2021 A01 Broken Access Control and A02
  Cryptographic Failures where credential handling leaks.
- **Triage rationale**: the change defines new credential issuance, transport,
  signature validation, session revocation, and cross-run authorization at two
  internet-facing upgrade boundaries.
- **Security review artifact**:
  [artifacts/20261111_security_review.md](artifacts/20261111_security_review.md).
- **QA review artifact**:
  [artifacts/20261111_qa_review.md](artifacts/20261111_qa_review.md).

## Hardening and Observation Model

- **Failure signature**: a connection is accepted or a run Redis channel is
  touched without a valid run-bound credential and explicit run access; or a
  token is exposed through a URL, log, selected protocol, or retained artifact.
- **Scope boundary**: repair status/preflight identity, Origin, and confirmed
  message-disclosure paths without redesigning unrelated endpoint auth.
- **Hypothesis**: claim and live-session validation before upgrade/Redis access,
  paired with frontend token transport and exact origins, prevents anonymous and
  cross-run subscription while preserving intended streams.
- **Removal evidence**: focused negative matrices, direct Go integration tests,
  frontend unit tests, full regression gates, and actual forest browser evidence
  for both services.
- **Rollback**: restore prior images/configuration only if necessary to recover
  forest; rollback does not constitute a safe production state for SEC-04. Keep
  the package open and preserve denial/health evidence.
- **Failed-attempt recording**: log sanitized HTTP status, close/error class,
  service and test identity, never bearer material or private message bodies.

## Testing Scope Decision

No focused-only waiver applies. The implementation must run affected Python,
Go, Jest, Playwright, generated-source, and Compose checks during iteration,
then the canonical broad gates:

```bash
wctl run-pytest tests --maxfail=1
wctl run-npm lint
wctl run-npm test
```

Environment acceptance must then redeploy the affected services on forest and
run the browser E2E against `https://forest.tail305ec9.ts.net/weppcloud/`. The
test must observe both WebSocket handshake requests in memory, verify their
sanitized claims, confirm token-free URLs, receive intended status and preflight
messages, and prove no-token/cross-run denial. The exact command, commit,
container IDs, start times, browser version, health evidence, and cleanup must be
recorded without raw tokens or credentials.

## Outcome

Ratified ancestor `6a06ad49a`; implementation and broad regression revision
`fadc8847b`; forest browser revision `bae13ff84`. Full pytest passed 13,568 tests
(435 skipped), npm passed 126 suites / 1,076 tests, and Go/focused gates passed.
Five forest services were redeployed and the real browser proved both streams,
renewal, message rendering, denial and credential non-retention. All 27 browser
assertions passed. NFS delayed fixture deletion; the retained failed aggregate
receipt and supplemental recovery receipt disclose that separately.

See [combined forest acceptance](artifacts/20261111_forest_acceptance.json),
[validation](artifacts/20261111_validation.md), and the completed ExecPlan.
Production SEC-04 exposure remains pending a separately authorized rollout.
Canonical policy lives in `docs/schemas/weppcloud-websocket-auth-contract.md`
and ADR-0141; this closed package is historical evidence.
