# Security Review - Anonymous Project Creation Policy

## Findings

No production authorization/configuration vulnerability found. One medium tooling finding arose while inspecting the retained browser validation script and was remediated before final sign-off.

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Browser validation credential logging | `browser_canary.cjs` filled the real agent password, then printed `error.message` on failure. Playwright embeds raw fill values in timeout call logs, so a password-fill failure could disclose the password to terminal/artifact output. No disclosure was observed in the successful runs. | `browser_canary.cjs` password fill and final catch; installed `playwright-core/lib/server/dom.js:496` logs the fill value. | Replace outer error reporting with a fixed sanitized message or safe stage identifier; never print the raw Playwright exception message/stack from this credential-bearing flow. | Resolved; 21:12 UTC source recheck confirms a fixed error message and explanatory comment, with no raw exception output |
| SEC-EVIDENCE | Evidence gate | Runtime boundaries | Initial runtime evidence lacked explicit no-allocation snapshots and final gate/cleanup results. Final artifacts establish all 16 unchanged run-directory/Run-row snapshots, cross-origin and missing-origin cookie denial, full-suite success, and cleanup/restoration. This was an incomplete gate, not an observed vulnerability. | `20260907_runtime_denial_snapshots.json`, `20260907_browser_final.json`, `20260907_cleanup_final.json`, `20260907_restoration_final.json`, validation report and full-suite log. | Independently review the strengthened script/results and final correctness/UX disposition before security sign-off. | Closed at 21:26 UTC after final runtime/validation inspection and correctness/UX PASS recheck |

Checkpoint finding SEC-CP-01 is closed: Docker README now explicitly explains that builder can accept a session token without an account, and does not claim a site-wide prohibition.

## Metadata

- **Package**: `docs/work-packages/20260907_anonymous_project_creation/`.
- **Reviewer**: independent dedicated security reviewer `/root/checkpoint_security`.
- **Date**: 2026-09-07 20:58 UTC source review; 21:10 UTC initial runtime-evidence review; 21:24 UTC final runtime/validation review; 21:26 UTC final security sign-off after correctness/UX PASS.
- **Scope reviewed**: shared creation-policy parser, rq-engine create handler and alias, Flask configuration/interfaces route/template, dev/prod Compose, related tests and operator documentation.
- **Commit context**: standalone checkpoint `fb67f32fccb00410b561e4f331f0b89a815a487e`, parent `a64c39f8523ba7efab0e13c4973026700f1d780d`; implementation `935d96220222adaab065e96980de4d3efeda3e30`; OpenAPI description-budget fix `43be30d313cc92ba7125c376e43f5026549a1c23`.
- **Checkpoint verification**: `git merge-base --is-ancestor fb67f32fc HEAD` passed; checkpoint commit timestamp is 2026-09-07 20:52:22 UTC, after the independent amendment rechecks and before this implementation review.
- **Related artifacts**: [contract decision](20260907_contract_decision.md), [checkpoint correctness](20260907_checkpoint_correctness.md), [checkpoint security](20260907_checkpoint_security.md), [correctness/UX review](20260907_correctness_review.md), [validation](20260907_validation.md), default/restricted/final runtime and browser JSON artifacts, identity/cleanup/restoration evidence, `runtime_canary.py`, `browser_canary.cjs`, and `cleanup_canaries.py`.

## Security Triage Decision

- **Security impact level**: high.
- **Dedicated security review required**: yes.
- **Rationale**: changes public creation authorization, signed-token class acceptance, browser credential precedence, and configuration propagated across two services.
- **Threat model assumptions**: attackers can submit direct JSON/forms, replay solved CAPTCHA and issued session tokens, supply hostile token classes and origins, and retain stale UI pages. Attackers cannot forge valid user/service/mcp signatures or edit server environment/session storage. Existing JWT validation, revocation, trusted-origin handling, and active-account lookup remain required boundaries.
- **Valid states to preserve**: unset/default anonymous CAPTCHA creation; authorized user/cookie/service/mcp creation; expired rq_token recovery; stale CAPTCHA attached to a valid browser session; optional idempotency absent under existing writer contracts; supported presets/legacy interfaces; role-filtered authenticated UI. Explicit invalid configuration and disallowed credentials deny as contracted.

## Verdict

- **Gate status**: pass.
- **Unresolved findings**: high 0, medium 0, low 0.
- **Release recommendation**: ship the reviewed implementation. Source, configured-development runtime, validation, and cleanup evidence satisfy this package's security gate. Production deployment remains a separate operator action with its normal preflights.

## Surface Checks

### 0) Valid-State Non-Interference and User Experience

The checkpoint matrix distinguishes absent, empty, populated, legacy, and hostile states. Source preserves default behavior and existing valid credential paths, with contracted rejection of every session-token class in restricted mode. `test_interfaces_creation_policy_renders_all_launch_surfaces` renders the real template in four identity/policy states. The inline script returns when the omitted context menu is absent. Retained Chromium scripts/results establish default 15 versus restricted 0 anonymous forms, working sign-in, 15 authenticated forms, absent restricted CAPTCHA asset requests, and no page exceptions. The real HTTP script verifies expected account ownership. The final correctness/UX artifact independently passes after its source, QA/validation, runtime, cleanup, and restoration rechecks; this security sign-off follows that disposition.

### 1) Auth, Session, and Authorization

- `project_routes.py:336-388` preserves explicit rq_token/Bearer validation, scopes, revocation, and existing expired rq_token cookie recovery before the new policy gate.
- `project_routes.py:390-436` uses CAPTCHA only when anonymous creation is allowed. Restricted requests resolve the cookie even when CAPTCHA is present, then reject absent/disallowed classes before payload-derived mutation, idempotency, or allocation.
- `project_routes.py:430` compares stripped token classes case-sensitively against `user`, `service`, `mcp`. This matches `user_preferences.py:265` exactly: uppercase `USER` cannot pass the new gate and then evade active-user resolution by being treated as ownerless. Signed-token tests exercise `USER`, missing/unknown classes, and session tokens with and without user_id in both credential transports.
- Session tokens are rejected regardless of user_id; no run-scoped token is promoted into global user authority. Service/mcp are intentional existing API exceptions. User and cookie claims retain `resolve_creation_actor` active-account/email-conflict checks before allocation and ownership registration.
- `_claims_from_session_cookie` still invokes the existing same-origin guard and migration-aware session selector. No CSRF/origin/token-issuance code changes. Final real HTTP evidence verifies hostile/missing-origin cookie denial and current/missing/inactive/conflicting account behavior.

### 2) Secrets and Credential Handling

No new secret, credential transport, secret mount, or token issuance is introduced. The policy is a nonsecret boolean. Parser errors and new API responses identify the setting without echoing its supplied value, cookies, CAPTCHA tokens, or JWTs. Existing secret-file contracts are unchanged.

### 3) Input Validation and Output Safety

`creation_policy.py` uses a finite allowlist with absence-only true default; blank and unrecognized values raise ValueError. Flask config loading uses the same parser; rq-engine catches that narrow exception and returns canonical 503 before parsing or authorization. UI availability comes from server configuration/current_user and is not derived from request input. No new HTML interpolation of user content, path parser, URL fetch, unsafe deserialization, or shell invocation is added.

### 4) File System and Run-Tree Boundaries

The new API gate precedes `_create_run_blocking`, current-owner resolution, idempotency reservation, and `_create_run_dir`. Existing `/wc1/runs` path construction, NoDb initialization, ownership registration, and cleanup paths are unchanged. Tests install side-effect sentinels for CAPTCHA verification and idempotency in restricted requests. Real successful creation records run IDs, NoDb/config/README artifacts, and database ownership. Final real denial evidence compares exact before/after sets of root directories, sharded run directories, and Run primary keys, with 16 unchanged snapshots; it also verifies absent idempotency state and CAPTCHA preservation. Cleanup confirms all ten named canary directories and Run rows are absent.

### 5) Queue, Worker, and Subprocess Surfaces

No queue edge, worker, subprocess, cancellation, retry, or job metadata change. Creation remains synchronous; queue graph validation is not applicable to this diff. New errors use the existing canonical response helper.

### 6) Agentic Tooling and MCP Surfaces

The change retains existing signed mcp creation credentials and does not add scopes, permissions, or token issuance. This review made documentation-only edits and did not perform deployment, external publication, or credential-bearing operations. Retained browser-canary failure reporting now emits a fixed sanitized message: SEC-01 is closed by independent source recheck. This prevents Playwright password fill values from reaching its exception output.

### 7) Network and External Integrations

No new outbound call or exposure is introduced. Restricted anonymous creation avoids the existing CAPTCHA verification call. Other CAPTCHA consumers remain enabled; operator documentation expressly says not to disable the Cap service. Existing creation cost/rate controls are unchanged.

### 8) CI/CD and Supply Chain

No new dependency, build system, workflow permission, image source, or runner change. Dev/prod Compose pass `${WEPPCLOUD_ALLOW_ANONYMOUS_PROJECT_CREATION-true}` to both web/API services; using `-` preserves explicit empty values for rejection. Docker documentation uses the canonical targeted deployment entry point and identifies restart versus recreation semantics. Rendered/running service agreement and restoration to true are recorded; independent restored-service readback agrees with the retained evidence.

### 9) Data Integrity, Locking, and Concurrency

No run schema, NoDb lock, Redis key, idempotency algorithm, or ownership persistence change. Restricted denial is inserted before those operations. Existing user-actor lookup continues to fail explicitly on missing/inactive/conflicting accounts or database errors, rather than returning an anonymous actor.

### 10) Logging, Monitoring, and Incident Readiness

Malformed configuration emits a fixed server error message and observable canonical HTTP 503. Anonymous/disallowed creation returns fixed HTTP 403 `anonymous_creation_disabled`; existing authorization failures retain their current errors. No new broad exception catch or silent fallback is added. Docker README provides both-service verification and reversal to true without a data migration.

## Validation Evidence

- **Performed by reviewer**: source/test/doc diff review; token-class comparison against the existing account resolver; same-origin/cookie branch tracing; Compose interpolation inspection; checkpoint ancestry/timestamp verification; retained HTTP/Chromium script inspection against the completed JSON results.
- **Test coverage inspected**: `tests/microservices/test_rq_engine_project_routes.py`, `tests/weppcloud/test_configuration.py`, `tests/weppcloud/routes/test_weppcloud_site_interfaces_route.py`, and `test_pure_controls_render.py`. Tests include signed disallowed classes, both route aliases and payload transports, both writer modes, malformed setting values, cookie plus CAPTCHA, service/mcp preservation, and rendered UI omission.
- **Runtime evidence accepted**: real solved-CAPTCHA anonymous creation; default/restricted account-owned cookie creation; stale CAPTCHA ignored for restricted cookie identity; both aliases deny solved CAPTCHA without consuming it or reserving idempotency; hostile/missing-origin cookie rejection; actual JWT decoder/Redis/DB rejection for session/uppercase classes and missing/inactive/conflicting user accounts in both explicit credential transports; real signed service and mcp creation. `runtime_canary.py` uses the configured HTTPS proxy, real login, and real database/artifact checks; no changed boundary is mocked. Its exact set-equality assertions passed all 16 denied-request snapshots.
- **Independent restored-environment readback, 21:10 UTC**: `wctl exec` in both weppcloud and rq-engine reported creation policy `true`, UID 1000, GID 993, supplemental groups `[993]`, and existing `/wc1/runs`. Only these nonsecret values were printed. This confirms the actual restored service environments, not a production deployment.
- **Automated results reviewed**: validation report records focused 296 passes; frontend lint and 108 suites/835 tests pass; stub completeness, changed broad-exception enforcement, and docs checks pass. OpenAPI description-length failure was corrected by shortening the description; 12 OpenAPI tests pass. Reviewer read `/tmp/creation-broad-final.log`: **7,721 passed, 72 skipped**, in 779.85 seconds.
- **Identity, cleanup, and restoration**: retained runtime identity evidence records real UID 1000/GID 993/groups 993, umask 0022, `/wc1` and repository mounts. `cleanup_canaries.py` checks the ten explicit run IDs, deletes only matching account-owned records through the existing receipt helper, asserts absent paths and Run rows, and removes only idempotency entries tied to those canary IDs. Final cleanup JSON reports all ten removed. Final restoration JSON confirms both actual service values true, anonymous forms restored, and the existing CAPTCHA-required API denial restored. The sanitized browser script reran successfully.
- **Documentation check**: `wctl doc-lint --path` for this artifact passed, zero errors/warnings; uk2us spelling preview was unchanged.

## Residual Risk

The explicitly scoped flag leaves anonymous fork, JWT-gated builder allocation, deployment-enabled test support, and location-page controls unchanged. Docker documentation exposes these limitations. Default true deliberately preserves existing session-token creation behavior. Service configuration drift remains possible operationally; the activation procedure requires agreement in both processes before sign-off. These are stated scope/compatibility constraints, not new risk acceptances or a site-wide anonymous-allocation guarantee.

No security risk acceptance is requested. SEC-01 remediation and SEC-EVIDENCE verification are complete. Real coverage is bounded to the named auth/creation/UI boundaries and does not claim every preset, role, optional writer state, or production host was exercised.

## Sign-off

- **Security reviewer**: `/root/checkpoint_security`, 2026-09-07 21:26 UTC; **PASS**, no unresolved findings. Final evidence and correctness/UX disposition independently rechecked.
- **Package owner**: primary executing agent; record the security verdict in package closure. No risk-acceptance acknowledgment is required.
