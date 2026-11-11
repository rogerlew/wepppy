# Require run authorization for status and preflight WebSockets

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current, and update
this plan and `tracker.md` at every stopping point.

## Purpose / Big Picture

After this work, a browser can receive status or preflight messages for a run
only after presenting a short-lived credential bound to that run and the
specific stream authority. Both Go services validate identity and live session
state before accepting the WebSocket and before touching a run-specific Redis
channel. Existing owner/collaborator/admin access and only the explicitly
ratified public-run behavior continue to work.

Success is observable in three layers. Focused tests prove each claim, transport,
upgrade, Origin, Redis and message-redaction rule. Full pytest, npm lint and npm
tests prove the wider application remains intact. Finally, the affected services
are actually rebuilt and redeployed on forest, where Playwright observes in
memory that the real frontend sends a token to both status and preflight
handshakes, receives intended messages, rejects missing/cross-run authorization,
and leaves no token in URLs, logs, storage, selected protocols or artifacts.

## Progress

- [x] (2026-11-11 15:49 UTC) Confirm F4/SEC-04 scope and current unauthenticated
      browser/service paths.
- [x] (2026-11-11 15:49 UTC) Scaffold package, tracker, proposed contract,
      failure matrix and pending review artifacts.
- [x] (2026-11-11 15:49 UTC) Record the operator-required forest redeploy and
      browser proof for both status and preflight as mandatory closeout gates.
- [x] (2026-11-11) Execute M0 discovery and two independent read-only reviews;
      prepare canonical draft, dependency assessment and proposed ADR-0141.
- [ ] M0: write/ratify the canonical contract and valid-state matrices; complete
      dependency evaluation; obtain two independent read-only reviews; commit a
      standalone checkpoint ancestor.
- [ ] M1: implement stream-token issuance and focused Python tests.
- [ ] M2: implement browser token acquisition/transport/refresh, generated
      controller parity, and focused Jest tests.
- [ ] M3: implement pre-accept status2/preflight2 validation, Redis session
      checks, exact Origins, bounded message redaction, and Go integration tests.
- [ ] M4: pass focused and broad validation; close correctness, QA and security
      review findings.
- [ ] M5: perform the authorized, service-scoped forest redeploy with health and
      rollback evidence.
- [ ] M6: pass real forest browser E2E and cleanup; update the audit board from
      retained sanitized evidence.

## Surprises & Discoveries

- Execution discovery: command-bar direct sockets and diagnostics probes are
  additional consumers; run-sync connects before destination registration.
  Ownerless page access and sessionless token issuance differ. See the expanded
  failure matrix and `artifacts/20261111_m0_reviews.md`.
- Security discovery: JTI fences live in DB 0, SID fences/markers in DB 11.
  Short SETEX would shorten RQ markers; terminal hangup would disable expiry
  reconnect. These are now explicit contract and regression requirements.

- Observation: the standard browser WebSocket constructor cannot set an
  `Authorization` header. Credential transport must use a browser-supported
  handshake mechanism and avoid URL/query leakage.
  Evidence: current `new WebSocket(wsUrl)` call sites and the WebSocket API.

- Observation: Origin validation already exists but does not establish whether
  the caller may inspect the named run. Empty configured allowlists can also be
  permissive in current service behavior.
  Evidence: `services/status2/internal/server/server.go` and
  `services/preflight2/internal/server/server.go` discovery.

- Observation: the current RQ session-token contract is broad and long-lived
  relative to an ephemeral status/preflight stream. Reusing it unchanged would
  increase exposure and make service-specific least privilege unclear.
  Evidence: `wepppy/microservices/rq_engine/session_routes.py` and
  `docs/dev-notes/auth-token.spec.md` discovery.

- Observation: neither Go service module establishes a JWT library precedent.
  A dependency evaluation is required before implementation; hand-written
  cryptographic parsing is not a safe substitute.
  Evidence: service Go module inspection at scaffold time.

## Decision Log

- Decision: make an actual forest redeploy and browser-level proof for both
  status and preflight mandatory package acceptance.
  Rationale: Roger explicitly requested this environment validation; unit tests
  cannot prove generated frontend code, Caddy routing, Compose secrets, Go
  configuration and browser handshake behavior agree.
  Date/Author: 2026-11-11, Roger; recorded by Codex.

- Decision: limit deployment authority to forest. Production remains unchanged
  until separately authorized.
  Rationale: the request names forest as the validation target and does not
  authorize wepp1, wepp2, wepp3 or openwepp.org deployment.
  Date/Author: 2026-11-11, Codex.

- Decision: start from a dedicated short-lived stream token transported in
  `Sec-WebSocket-Protocol`, with a fixed negotiated application protocol and the
  bearer value never echoed or retained. This remains proposed until M0.
  Rationale: browsers cannot attach an Authorization header; query parameters
  commonly leak through logs/history, and a dedicated credential allows narrow
  audience, scope and lifetime.
  Date/Author: 2026-11-11, Codex.

- Decision: require live session marker and revocation checks before upgrade and
  Redis subscription, not signature validation alone. This remains proposed
  until M0.
  Rationale: the existing RQ token model includes server-side session state;
  preserving it prevents a signed but revoked session from continuing to read.
  Date/Author: 2026-11-11, Codex.

## Outcomes & Retrospective

M0 execution produced a canonical proposed contract, ADR-0141, dependency
assessment and two independent reviews. No reviewer has approved M0. Three
concrete lifecycle policy decisions need operator ratification; message-fixture confirmation,
post-decision review and the standalone checkpoint remain. No implementation,
service deployment or vulnerability closure is claimed.

No implementation outcome exists yet. The package and its acceptance boundary
are scaffolded. Populate this section with observed security behavior,
compatibility, forest evidence, unresolved risk and lessons at each milestone.

## Context and Orientation

WEPPcloud's status client lives in
`wepppy/weppcloud/controllers_js/status_stream.js`; its generated browser output
is `wepppy/weppcloud/static/js/status_stream.js`. Preflight currently lives in
`wepppy/weppcloud/static/js/preflight.js`. Both derive a run-specific WebSocket
URL and construct a socket without credentials.

The services are separate Go applications under `services/status2` and
`services/preflight2`. Each service parses a run identity from the WebSocket
path, applies Origin handling and then uses Redis for the run stream. The repair
must establish authorization before `websocket.Accept` and before any
run-specific Redis operation. The exact code may move; the behavioral ordering
is the contract.

RQ-engine already mints signed session tokens and tracks live/revoked sessions
in Redis DB 11. `wepppy/weppcloud/controllers_js/http.js` provides the browser's
current token helper. The new minting path should reuse canonical run access and
session state without broadening the existing multi-day RQ token. The same-origin
cookie/CSRF bridge applies to minting; the bearer-authenticated WebSocket
handshake is a separate boundary.

Compose and Caddy route the services. Forest is a development Compose deployment
at `https://forest.tail305ec9.ts.net/weppcloud/`, operated through the installed
`wctl` dev preset. Before any forest mutation, inspect the canonical deployment
entry points and rendered configuration. Do not invent a parallel image,
registry, or Compose workflow.

## Plan of Work

### Milestone 0: Ratify the security contract

Create `docs/schemas/weppcloud-websocket-auth-contract.md` and update
`docs/dev-notes/auth-token.spec.md` and
`docs/schemas/weppcloud-csrf-contract.md`. Specify issuer, token class, exact
audiences, scopes, run/config binding, session and token IDs, issued/not-before/
expiry rules, public-run states, transport syntax, negotiated protocol, error/
close behavior, Origin policy, Redis session checks, and non-logging rules.

Complete the valid-state matrix in `artifacts/20261111_contract_decision.md` and
the consumer/failure inventory in `artifacts/20261111_failure_class_matrix.md`.
Decide whether one token may name both audiences/scopes or clients receive
service-specific tokens. Decide lifetime and refresh skew from threat and UX
evidence. If these are configurable defaults, create the required ADR. Evaluate
any proposed Go JWT library under the dependency standard.

Obtain two independent read-only contract reviews. Resolve their findings and
commit the contract, artifacts and package as a standalone checkpoint that is an
ancestor of implementation. Do not proceed on an unratified token shape.

### Milestone 1: Implement least-privileged token issuance

Add a dedicated mint route at the established rq-engine/session boundary. Reuse
canonical run authorization for private owner, collaborator and admin access,
and implement only the ratified public-run policy. Require the existing
same-origin session and CSRF behavior. Mint only the ratified stream claims and
create/reuse the server-side session marker needed for validation. Never return
the token in a URL.

Add focused route/auth tests for authorized private and public states plus
anonymous private, unrelated user, malformed identifiers, revoked session and
invalid configuration. Update OpenAPI/docs and stubs if the public surface
changes. Preserve canonical error contracts.

### Milestone 2: Implement browser transport and refresh

Add a short-cache `WCHttp` stream-token helper. Update StatusStream and preflight
to acquire a credential before connection and pass the fixed application
protocol and bearer-shaped value in the WebSocket protocol list. On auth-related
failure or expiry, refresh once under bounded backoff; do not downgrade to an
anonymous socket or create a retry storm.

Add Jest coverage for URL construction, protocol values without printing the
token, claim-independent caching/expiry behavior, reconnect refresh, and denial.
Build the generated status controller using the canonical builder and verify
source/generated parity. Add a focused preflight JS test module if none exists.

### Milestone 3: Authenticate both Go services before Redis

Add common, owned validation behavior to status2 and preflight2. Load signing
material from a secret file, not a raw environment secret. Configure Redis DB 11
for session-marker/revocation checks without changing the existing stream Redis
contract. Validate algorithm, signature, issuer, audience, class, required
service scope, issued/not-before/expiry times, exact run/config, live marker and
revocation state before accepting the WebSocket or subscribing to a run channel.

Parse the bearer protocol but select/echo only the fixed application protocol.
Use exact Origin allowlists. Empty origins fail closed unless an explicitly
named, default-off local development mode is ratified; that mode must be absent
from rendered forest and production configuration.

Add direct Go integration tests with Redis for every negative claim/state and
assert rejection happens before per-run subscription. Preserve health behavior
and non-sensitive diagnostics. Inventory status/preflight payload producers and
replace confirmed absolute paths, exception details and sensitive options with a
narrow documented message schema/redaction rule. Do not absorb F5's general HTTP
error-envelope scope.

### Milestone 4: Complete local validation and independent review

Run the focused Python route tests, both Go unit/integration suites, focused Jest
tests, generated-controller build/parity, rendered Compose/config checks and
secret-leak scans. Then run the exact broad gates:

    wctl run-pytest tests --maxfail=1
    wctl run-npm lint
    wctl run-npm test

Run stub/API checks when touched. Obtain independent correctness, QA and security
reviews. Resolve every blocking finding before forest deployment. Record exact
commands, revision, counts, durations and failures in a validation artifact; do
not convert an interrupted/segmented run into a full-suite claim.

### Milestone 5: Redeploy affected services on forest

On forest, record host, repository path, branch/revision, installed `wctl`
preset, rendered Compose, health, active jobs/queues, container IDs and start
times. Do not cancel active jobs; wait or drain through established procedures.
Validate the rendered configuration, secret-file mounts, Redis DB configuration
and exact allowed Origin before mutation.

Resolve and record the canonical service-scoped build/recreate command from the
installed forest workflow. Expected services are rq-engine, weppcloud, status
and preflight; include Caddy only if its effective configuration changed. After
redeploy, record image/container identities, health, sanitized logs and rollback
mapping. Stop and recover to the known-good mapping on health or configuration
failure. This milestone authorizes forest only.

### Milestone 6: Prove the real frontend sends both tokens

Run Playwright against the redeployed
`https://forest.tail305ec9.ts.net/weppcloud/` using credentials read from the
gitignored `docker/secrets/dev-agent.env`. Use existing helpers to create/open
disposable private runs. Attach Chromium CDP
`Network.webSocketWillSendHandshakeRequest` before the connections. Inspect the
two handshake headers only in memory. Assert the fixed protocol and a
bearer-shaped value are present; decode only the selected non-secret claims
needed to prove run, audience/scope and short expiry. Do not print the raw token
or header in assertions, traces, videos, screenshots or retained logs.

Assert both WebSocket URLs have no token/query secret. Receive an actual
preflight initial/update message. Publish a unique harmless status marker through
the existing operator-side Redis channel for the disposable run and prove the
browser receives it; do not add a public test route/backdoor. Prove a missing
token and a token for private run A used on private run B do not receive data.
Hostile Origin is mandatory in Go integration and may be repeated in browser
acceptance when reliable.

Search sanitized service/browser output, selected protocols, browser storage and
retained artifacts for credential-shaped leakage. Clean up disposable runs and
the status marker. Retain exact commit, container IDs/times, browser version,
sanitized assertions, health/log summary, negative outcomes and cleanup receipt.
Update package, tracker, review artifacts and audit board only after evidence.

## Concrete Steps

Work from `/home/workdir/wepppy` and preserve unrelated dirty files.

Inspect current boundaries before M0:

    rg -n "new WebSocket|session-token|websocket.Accept|ALLOWED_ORIGINS" \
      wepppy/weppcloud services/status2 services/preflight2 \
      wepppy/microservices/rq_engine docker
    git status --short

During implementation, use the repository wrappers rather than direct ad hoc
test environments. Expected focused commands must be refined to actual changed
test files and recorded in the validation artifact:

    wctl run-pytest tests/microservices/test_rq_engine_session_routes.py
    wctl run-status-tests
    wctl run-status-tests -tags=integration ./internal/server
    wctl run-preflight-tests
    wctl run-preflight-tests -tags=integration ./internal/server
    wctl run-npm test -- --runInBand <focused-test-paths>
    python3 wepppy/weppcloud/controllers_js/build_controllers_js.py

After focused checks and reviews, run the exact broad commands from Milestone 4.
Before forest deployment, inspect `docs/infrastructure/homelab-tailscale.md`, the
installed `wctl` preset and rendered Compose on forest. Record the resolved
service-scoped deployment and E2E commands in this plan before executing them.

## Validation and Acceptance

Acceptance requires all of the following, with sanitized retained receipts:

- The minting valid-state matrix passes for authorized private/public states and
  denies anonymous private and unrelated callers.
- Both services reject missing, malformed, forged, expired, future, wrong
  issuer/audience/scope/class, cross-run, missing-marker and revoked credentials
  before upgrade/per-run Redis access.
- Exact same-origin requests succeed and hostile Origin fails without treating
  Origin as identity.
- Frontend tests prove token acquisition, transport, bounded refresh/reconnect,
  token-free URLs and no anonymous fallback.
- Message tests prove confirmed paths, exceptions and sensitive options are
  redacted while intended progress/preflight fields remain.
- Generated status JS matches its source and no raw token pattern is retained.
- Focused tests, full pytest, npm lint and full npm tests exit zero.
- Independent correctness, QA and security reviews pass.
- The actual forest stack is redeployed, healthy and rollback-ready.
- Playwright against that redeployed stack proves both frontend handshakes send
  valid run-bound authorization, receive intended messages, and deny no-token
  and cross-run access without retaining credentials.

HTTP 101, service health, job success, persisted state, or unit tests alone do
not satisfy environment acceptance.

## Idempotence and Recovery

Token/config migrations must be additive until all clients and services agree;
do not leave a fail-open compatibility mode. Re-running focused and broad tests
must not create persistent sessions or fixtures outside their scoped cleanup.
Forest browser tests use unique disposable run IDs/markers and remove them on
success or failure.

Before forest mutation, retain the known-good image/container mapping and
rendered configuration. If a service fails health or the browser cannot connect,
capture sanitized diagnostics and restore only the affected forest services to
the known-good mapping. Do not delete shared volumes, reset Redis, cancel active
jobs, or broaden allowed Origins. A rollback restores availability but does not
close SEC-04; keep the package open and record the failure.

## Artifacts and Notes

- `package.md`: normative scope, threat model, acceptance and authority.
- `tracker.md`: live board and environment gate status.
- `artifacts/20261111_contract_decision.md`: proposed/ratified security contract
  and valid-state matrix.
- `artifacts/20261111_failure_class_matrix.md`: consumer and failure inventory.
- `artifacts/20261111_correctness_review.md`: independent correctness gate.
- `artifacts/20261111_security_review.md`: dedicated security gate.
- `artifacts/20261111_qa_review.md`: independent test/evidence quality gate.
- Add dependency evaluation, validation and forest acceptance artifacts as
  milestones execute. Retain only sanitized evidence; never raw JWTs or secrets.

## Interfaces and Dependencies

The final contract must define, at minimum:

- the mint route and response envelope;
- `iss`, token class, audiences, scopes, run/config, `session_id`, `jti`, `iat`,
  optional `nbf`, `exp`, and permitted clock skew;
- private/public authorization states and HTTP denial status;
- WebSocket protocol syntax and the single negotiated protocol;
- secret-file, Redis DB/session marker and revocation requirements;
- pre-accept validation order and safe close/error/log behavior;
- exact Origin configuration and default-off development exception, if any;
- token refresh/reconnect behavior and cache lifetime; and
- allowed/redacted status/preflight message fields.

Prefer no new dependency. If robust JWT verification requires one, complete the
repository's precedent/capability/dependency-tax/maintenance evaluation first,
pin it in both service modules as appropriate, and record why owned existing code
could not safely satisfy the standard. Do not implement cryptography by hand.

## Revision Note

2026-11-11: Initial ExecPlan created for F4/SEC-04. It records the proposed
short-lived subprotocol credential, pre-accept Redis/session validation, exact
Origin behavior, bounded message-redaction scope, full regression requirements,
and the operator-mandated forest redeploy plus actual browser proof for both
status and preflight. No runtime or deployment work has occurred.

2026-11-11 execution update: retained discovery/review evidence, expanded consumer
scope and prepared concrete lifecycle proposals; stopped before implementation
because the required exact contract remains unratified.

## Operator ratification (2026-11-11)

The operator explicitly approved all three proposed lifecycle policies and
instructed ratification and implementation. The canonical contract and ADR now
record that approval. Final independent confirmation and standalone ancestor
commit precede code edits; no further policy permission is required.
