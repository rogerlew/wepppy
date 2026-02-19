# Cross-Service Auth Token Integration Hardening ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This campaign makes cross-service token behavior explicitly testable across WEPPcloud (Flask), rq-engine (FastAPI), browse (Starlette), and query-engine MCP (Starlette) using one compatibility contract and one integrated test slice. After completion, a maintainer can answer "will this token work on this endpoint?" without reading service internals.

The user-visible proof is deterministic green runs for new integration tests plus existing targeted suites, where failures identify a specific matrix row or lifecycle stage (renewal, revocation, rotation) instead of a generic unauthorized response.

## Progress

- [x] (2026-02-19 02:42Z) Created work-package scaffold under `docs/work-packages/20260219_cross_service_auth_tokens/`.
- [x] (2026-02-19 02:42Z) Authored initial ExecPlan in `docs/work-packages/20260219_cross_service_auth_tokens/prompts/active/integrated_auth_token_campaign_execplan.md`.
- [x] (2026-02-19 02:42Z) Published compatibility matrix artifact in `docs/work-packages/20260219_cross_service_auth_tokens/artifacts/token_compatibility_matrix.md`.
- [x] (2026-02-19 02:42Z) Expanded this ExecPlan into an end-to-end implementation playbook with concrete milestones, edit targets, commands, and acceptance evidence.
- [x] (2026-02-19 02:54Z) Milestone 0 complete: added shared integration harness fixtures in `tests/integration/conftest.py` with deterministic JWT env, integration Redis double, app/client builders, and helper token issuers.
- [x] (2026-02-19 02:56Z) Milestone 1 complete: landed matrix-driven cross-service portability tests in `tests/integration/test_cross_service_auth_portability.py` and validated with `wctl run-pytest ... -q`.
- [x] (2026-02-19 02:57Z) Milestone 2 complete: landed lifecycle tests (renewal fallback, revocation propagation, rotation overlap/retirement) in `tests/integration/test_cross_service_auth_lifecycle.py`.
- [x] (2026-02-19 02:58Z) Milestone 3 complete: closed auth primitive unit-test gaps in `tests/weppcloud/test_auth_tokens.py` and `tests/microservices/test_rq_engine_auth.py`.
- [x] (2026-02-19 03:01Z) Milestone 4 complete: ran full validation gates and synchronized package docs (`tracker.md`, matrix, lifecycle validation artifact, and package closure notes).
- [x] (2026-02-19 04:04Z) Post-closeout follow-up complete: added grouped/composite runid cookie round-trip integration test (`MX-L4`) and synchronized matrix/tracker/evidence docs.

## Surprises & Discoveries

- Observation: The browser fallback renewal sequence is already contractually defined; it is not an inferred behavior.
  Evidence: `docs/dev-notes/auth-token.spec.md:211`, `docs/dev-notes/auth-token.spec.md:229`.

- Observation: Front-end behavior for fallback renewal is already covered in JavaScript unit tests, but there is no backend cross-service integration assertion that the same sequence succeeds end-to-end.
  Evidence: `wepppy/weppcloud/controllers_js/__tests__/http.test.js:303`, `wepppy/weppcloud/controllers_js/__tests__/http.test.js:355`.

- Observation: MCP explicitly requires `token_class=mcp`; acceptance of `user`, `service`, or `session` on MCP routes would be a policy change, not a test gap.
  Evidence: `wepppy/query_engine/app/mcp/auth.py:215`, `tests/query_engine/test_mcp_auth.py:213`.

- Observation: The shared test Redis stub in `tests/conftest.py` does not expose all operations needed for lifecycle integration assertions (notably `setex`, `exists`, and TTL-aware behavior).
  Evidence: `tests/conftest.py:103` to `tests/conftest.py:143`, `wepppy/microservices/rq_engine/session_routes.py:134`, `wepppy/weppcloud/_scripts/revoke_auth_token.py:166`.

- Observation: There is currently no `tests/integration/` directory, so this campaign must create one and document marker usage.
  Evidence: repository scan from `/workdir/wepppy` returned no `tests/integration` paths.

- Observation: The first portability run failed because the integration Redis fixture was not autouse, so tests that did not request it fell back to the session-wide `RecordingRedis` stub without `setex`.
  Evidence: `wctl run-pytest tests/integration/test_cross_service_auth_portability.py -q` output (`AttributeError: 'RecordingRedis' object has no attribute 'setex'`), followed by passing rerun after fixture change.

- Observation: rq-engine currently accepts WEPP-signed tokens carrying `token_class=mcp` when run scope and required scopes pass; browse rejects the same token class by policy.
  Evidence: `tests/integration/test_cross_service_auth_portability.py::test_portability__mx_a5_wepp_signed_mcp_class_token_conditionally_allows_rq_engine` and `...::test_portability__mx_a4_wepp_signed_mcp_class_token_rejected_by_browse_policy`.

## Decision Log

- Decision: Start implementation from the compatibility matrix and treat it as the source of truth for allow/deny expectations.
  Rationale: Prevents contradictory assumptions while writing integration tests.
  Date/Author: 2026-02-19 / Codex.

- Decision: Keep MCP token-class enforcement unchanged (`token_class=mcp` only) unless an explicit policy request is made.
  Rationale: Maintains scope discipline and avoids speculative auth broadening.
  Date/Author: 2026-02-19 / Codex.

- Decision: Add a dedicated integration Redis double fixture instead of mutating the global session-scoped Redis stub in `tests/conftest.py`.
  Rationale: Avoids regressions in unrelated tests while enabling lifecycle semantics (`setex`, revocation keys, marker existence checks).
  Date/Author: 2026-02-19 / Codex.

- Decision: Rotation lifecycle tests target WEPP auth-token consumers (WEPPcloud, rq-engine, browse). MCP rotation is not included because MCP currently loads a single secret via `WEPP_MCP_JWT_SECRET`.
  Rationale: Matches current implementation contracts and avoids writing impossible assertions.
  Date/Author: 2026-02-19 / Codex.

- Decision: Make the integration Redis fixture autouse for all integration tests.
  Rationale: Guarantees `setex`/TTL/revocation behavior is always available and prevents accidental fallback to the global stub.
  Date/Author: 2026-02-19 / Codex.

- Decision: Preserve rq-engine conditional acceptance of WEPP-signed `token_class=mcp` tokens and document/test it explicitly instead of changing policy in this package.
  Rationale: Scope discipline: no production auth contract broadening/narrowing without explicit policy request.
  Date/Author: 2026-02-19 / Codex.

- Decision: Keep `token_class=mcp` handling unchanged for now.
  Rationale: Explicit follow-up policy direction requested no contract change at this time.
  Date/Author: 2026-02-19 / Codex.

- Decision: Keep PUBLIC browse access permissive for anonymous-eligible, non-root-only paths.
  Rationale: Explicit follow-up policy direction confirmed permissive public browse access within existing root-only protections.
  Date/Author: 2026-02-19 / Codex.

- Decision: Add explicit grouped/composite runid cookie round-trip integration coverage.
  Rationale: Addresses review feedback that composite cookie behavior previously relied on per-service tests without an integration-level issuance-to-consumption assertion.
  Date/Author: 2026-02-19 / Codex.

## Outcomes & Retrospective

Campaign completed end-to-end. The package now includes a shared integration harness, matrix-driven portability tests, lifecycle integration flows, auth primitive unit-gap tests, and synchronized artifacts linking every matrix row to concrete test IDs.

Validation outcomes captured in `docs/work-packages/20260219_cross_service_auth_tokens/artifacts/lifecycle_validation_results.md` are green after one early harness fix:

- `wctl run-pytest tests/integration/test_cross_service_auth_portability.py -q` -> pass (`6 passed`)
- `wctl run-pytest tests/integration/test_cross_service_auth_lifecycle.py -q` -> pass (`3 passed`)
- `wctl run-pytest tests/weppcloud/test_auth_tokens.py tests/microservices/test_rq_engine_auth.py -q` -> pass (`35 passed`)
- `wctl run-pytest tests/weppcloud/routes/test_rq_engine_token_api.py tests/microservices/test_rq_engine_session_routes.py tests/microservices/test_browse_auth_routes.py tests/query_engine/test_mcp_auth.py` -> pass (`120 passed`)
- `wctl run-npm test -- http` -> pass (`13 passed`)
- `wctl doc-lint --path docs/work-packages/20260219_cross_service_auth_tokens` -> pass
- `wctl doc-lint --path docs/dev-notes/auth-token.spec.md` -> pass

Retrospective note for next contributor: the remaining work is policy-level, not implementation-level. If rq-engine should reject `token_class=mcp` on run routes, treat that as a separate contract change package with coordinated code + matrix + test updates.

## Context and Orientation

This repository uses a shared JWT utility for WEPPcloud/rq-engine/browse and a separate MCP JWT implementation for query-engine MCP. "Cross-service token portability" means a token minted for one service can be validated by another service exactly when policy allows. "Fallback renewal" means the browser requests a run-scoped session token first and falls back to `/weppcloud/api/auth/rq-engine-token` when needed. "Session marker" means Redis key `auth:session:run:{runid}:{session_id}` that rq-engine requires for `token_class=session`. "Revocation denylist" means Redis key `auth:jwt:revoked:{jti}` checked by rq-engine, browse, and MCP.

Primary production files to read before editing tests:

- `wepppy/weppcloud/utils/auth_tokens.py` for JWT issue/decode/time-claim logic and rotation via `WEPP_AUTH_JWT_SECRETS`.
- `wepppy/weppcloud/routes/weppcloud_site.py` for fallback mint endpoint `POST /weppcloud/api/auth/rq-engine-token`.
- `wepppy/microservices/rq_engine/auth.py` for `require_jwt`, `require_roles`, `_authorize_user_claims`, `authorize_run_access`, and session-marker/revocation checks.
- `wepppy/microservices/rq_engine/session_routes.py` for `POST /api/runs/{runid}/{config}/session-token` issuance behavior and cookie scoping.
- `wepppy/microservices/rq_engine/job_routes.py` for polling auth mode (`RQ_ENGINE_POLL_AUTH_MODE`) and `canceljob` scope checks.
- `wepppy/microservices/browse/auth.py` for run/group route authorization and cookie-to-bearer fallback handling.
- `wepppy/query_engine/app/mcp/auth.py` for MCP JWT validation and token-class enforcement.

Existing tests that should be reused instead of duplicated:

- `tests/weppcloud/test_auth_tokens.py`
- `tests/weppcloud/routes/test_rq_engine_token_api.py`
- `tests/microservices/test_rq_engine_auth.py`
- `tests/microservices/test_rq_engine_session_routes.py`
- `tests/microservices/test_rq_engine_jobinfo.py`
- `tests/microservices/test_browse_auth_routes.py`
- `tests/query_engine/test_mcp_auth.py`
- `tests/weppcloud/routes/test_run_0_nocfg_auth_bridge.py`
- `wepppy/weppcloud/controllers_js/__tests__/http.test.js`

Environment assumptions for all milestones:

- Working directory is `/workdir/wepppy`.
- Commands are run with `wctl` wrappers (`wctl run-pytest`, `wctl run-npm`, `wctl doc-lint`).
- Tests remain hermetic and in-process (no real network calls).
- New tests must include pytest markers (`integration`, `unit`, `microservice`, or `routes` as appropriate).

## Plan of Work

Milestone 0 establishes shared fixtures for the integration campaign. Create `tests/integration/` with one fixture module and two placeholder test modules so subsequent milestones can focus on behavior instead of repeated setup. The fixture module must provide a Redis double that supports session markers and denylist semantics and must centralize environment/cache reset for JWT settings (`get_jwt_config.cache_clear()` and `get_auth_config.cache_clear()`).

Milestone 1 implements matrix-driven portability tests. The tests should be parameterized by case ID and verify both positive and negative routes across rq-engine, browse, and MCP surfaces. Each case should map back to a row in `docs/work-packages/20260219_cross_service_auth_tokens/artifacts/token_compatibility_matrix.md`. When a case is intentionally conditional, the test name should encode the condition, for example `test_portability__session_requires_marker`.

Milestone 2 implements lifecycle tests that prove full flows, not isolated checks. The renewal test must show `session-token` failure followed by WEPPcloud fallback token mint and successful retry. The revocation test must show the same `jti` being denied by rq-engine, browse, and MCP after denylist insertion. The rotation test must validate overlap acceptance and retirement rejection for WEPP auth tokens by controlling `WEPP_AUTH_JWT_SECRETS`.

Milestone 3 closes direct unit-test gaps. Add explicit time-claim tests in `tests/weppcloud/test_auth_tokens.py` for `exp`, `nbf`, `iat`, and leeway behavior; add direct helper tests in `tests/microservices/test_rq_engine_auth.py` for `require_roles`, `_authorize_user_claims`, and `_sanitize_auth_actor` edge cases. These tests prevent future regressions from being hidden behind route mocks.

Milestone 4 is closeout and evidence capture. Run targeted pytest and npm commands, then update package docs with exact pass/fail results, residual risk, and any required spec wording adjustments. If behavior differs from the matrix, resolve by either code fix or explicit documented contract update, never by silent test expectation drift.

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Create integration suite scaffolding and fixture utilities.

    mkdir -p tests/integration

    Add files:
    - `tests/integration/conftest.py`
    - `tests/integration/test_cross_service_auth_portability.py`
    - `tests/integration/test_cross_service_auth_lifecycle.py`

    In `tests/integration/conftest.py`, define:
    - `class IntegrationRedisDouble` with `set`, `setex`, `get`, `exists`, `delete`, `ttl`, `close`, and context-manager methods.
    - `@pytest.fixture` for deterministic JWT env (`WEPP_AUTH_JWT_SECRET`, `WEPP_AUTH_JWT_ISSUER`, `WEPP_AUTH_JWT_DEFAULT_AUDIENCE`, `WEPP_MCP_JWT_SECRET`, `WEPP_MCP_JWT_ISSUER`, `WEPP_MCP_JWT_AUDIENCE`).
    - `@pytest.fixture` that monkeypatches `redis.Redis` in auth modules (`rq_engine.auth`, `browse.auth`, `query_engine.app.mcp.auth`, `rq_engine.session_routes`) to the shared Redis double.
    - cache cleanup in fixture teardown for `auth_tokens.get_jwt_config.cache_clear()` and `mcp_auth.get_auth_config.cache_clear()`.

2. Implement matrix-driven portability cases in `tests/integration/test_cross_service_auth_portability.py`.

    Required assertions:
    - session token accepted by rq-engine run-scoped endpoint when marker exists.
    - session token rejected by rq-engine when marker is missing.
    - user token accepted on rq-engine and browse run routes when role/run authorization passes.
    - service token with run scope accepted on rq-engine and browse.
    - WEPP-signed tokens carrying `token_class=mcp` are rejected on browse run routes and remain conditionally accepted on rq-engine run routes when scope/run claims satisfy checks.
    - MCP-signed tokens are accepted on MCP routes when scope/audience/issuer are valid, and rejected by non-MCP services due to signature domain and/or token-class policy.

    Implementation notes:
    - Use real app objects where practical (`rq_engine.app`, browse `create_app`, Starlette app with `MCPAuthMiddleware`, Flask test app for WEPPcloud routes).
    - Keep per-case setup local and deterministic (no dependency on `/wc1/runs`).
    - Use `pytest.mark.integration` module marker and descriptive case IDs.

3. Implement lifecycle tests in `tests/integration/test_cross_service_auth_lifecycle.py`.

    Renewal flow assertions:
    - initial `POST /api/runs/{runid}/{config}/session-token` fails with invalid session token.
    - `POST /weppcloud/api/auth/rq-engine-token` succeeds for authenticated same-origin request.
    - retry to session-token endpoint with fallback token succeeds and returns token payload.
    - anonymous fallback call returns `401`; cross-origin fallback call returns `403`.

    Revocation flow assertions:
    - token with JTI initially succeeds on rq-engine/browse/MCP representative routes.
    - after writing `auth:jwt:revoked:{jti}`, all three surfaces reject.

    Rotation flow assertions:
    - token signed with old secret validates while `WEPP_AUTH_JWT_SECRETS=new,old`.
    - newly minted token uses new secret and validates.
    - old token fails after retiring old secret from `WEPP_AUTH_JWT_SECRETS`.

4. Add primitive auth unit tests.

    Edit `tests/weppcloud/test_auth_tokens.py`:
    - add direct tests for expired token, not-before in future, issued-at in future, and leeway success path.
    - add numeric-type validation tests for malformed `exp`/`nbf`/`iat`.

    Edit `tests/microservices/test_rq_engine_auth.py`:
    - add direct `require_roles` pass/fail tests with mixed role payload shapes.
    - add `_authorize_user_claims` tests for admin/root bypass, public run bypass, owner-match by `sub`, owner-match by email, and forbidden path.
    - add `_sanitize_auth_actor` tests for each token class and malformed claims.

5. Keep the matrix and tracker synchronized with implemented behavior.

    Edit docs:
    - `docs/work-packages/20260219_cross_service_auth_tokens/artifacts/token_compatibility_matrix.md`
    - `docs/work-packages/20260219_cross_service_auth_tokens/tracker.md`
    - `docs/work-packages/20260219_cross_service_auth_tokens/artifacts/lifecycle_validation_results.md` (create if missing)

    For each matrix row, link at least one test case ID.

6. Run validation gates after each milestone and once at closeout.

    Fast milestone loop:

        wctl run-pytest tests/integration/test_cross_service_auth_portability.py -q
        wctl run-pytest tests/integration/test_cross_service_auth_lifecycle.py -q
        wctl run-pytest tests/weppcloud/test_auth_tokens.py tests/microservices/test_rq_engine_auth.py -q

    Broader auth slice:

        wctl run-pytest tests/weppcloud/routes/test_rq_engine_token_api.py tests/microservices/test_rq_engine_session_routes.py tests/microservices/test_browse_auth_routes.py tests/query_engine/test_mcp_auth.py

    Front-end fallback check:

        wctl run-npm test -- http

    Docs quality:

        wctl doc-lint --path docs/work-packages/20260219_cross_service_auth_tokens

    Expected terminal shape for each successful command:

        ... passed
        ... failed=0

7. Close out the package documents when tests are green.

    Update:
    - `Progress` in this file with completion timestamps.
    - `Outcomes & Retrospective` in this file with what passed and what remains.
    - `docs/work-packages/20260219_cross_service_auth_tokens/tracker.md` task board and progress notes.
    - `docs/work-packages/20260219_cross_service_auth_tokens/package.md` closure notes if campaign is complete.

## Validation and Acceptance

The campaign is complete when all conditions below are true.

- New integration tests exist and pass in `tests/integration/` for portability and lifecycle flows.
- Compatibility matrix rows are backed by concrete test case IDs.
- Renewal fallback behavior is proven across WEPPcloud and rq-engine in one end-to-end test.
- Revocation denylist behavior is proven consistent across rq-engine, browse, and MCP.
- Rotation overlap/retirement behavior is proven for WEPP auth-token consumers.
- New direct unit tests cover auth primitives that were previously only indirectly tested.
- Targeted auth pytest suites, npm fallback tests, and docs lint all pass with no new regressions.

## Idempotence and Recovery

All steps are additive and repeatable. The plan intentionally uses test-local fixtures and monkeypatching, so reruns should not require manual cleanup.

If a lifecycle test fails due to stale cached JWT configuration, clear caches inside the failing test setup before retrying (`auth_tokens.get_jwt_config.cache_clear()` and `mcp_auth.get_auth_config.cache_clear()`). If a failure appears only when running the full set, verify that environment variables are reset per test and that Redis double state is not shared across tests unless explicitly intended.

If a matrix expectation and implementation disagree, do not silently edit expected status codes. First determine whether the matrix is wrong or the implementation drifted; then update code and docs in one commit with a Decision Log entry.

## Artifacts and Notes

Required artifact and tracking files for this campaign:

- `docs/work-packages/20260219_cross_service_auth_tokens/artifacts/token_compatibility_matrix.md`
- `docs/work-packages/20260219_cross_service_auth_tokens/artifacts/lifecycle_validation_results.md`
- `docs/work-packages/20260219_cross_service_auth_tokens/tracker.md`

At each milestone boundary, record short evidence in `lifecycle_validation_results.md` using concise command/result snippets. Example format:

    2026-02-19 Milestone 2 renewal flow:
    command: wctl run-pytest tests/integration/test_cross_service_auth_lifecycle.py -k renewal -q
    result: 1 passed, 0 failed

## Interfaces and Dependencies

No production API contract change is planned in this package. This is a test and contract-hardening campaign.

Required interfaces and helper targets:

- `wepppy.weppcloud.utils.auth_tokens.issue_token` and `decode_token` for WEPP token issuance/validation.
- `wepppy.microservices.rq_engine.auth.require_jwt`, `require_roles`, `_authorize_user_claims`, `authorize_run_access`, and `_sanitize_auth_actor`.
- `wepppy.microservices.rq_engine.session_routes` session-token route and marker storage semantics.
- `wepppy.microservices.browse.auth.authorize_run_request` and `authorize_group_request`.
- `wepppy.query_engine.app.mcp.auth.MCPAuthMiddleware` and `decode_bearer_token`.
- `wepppy.weppcloud.routes.weppcloud_site` fallback endpoint behavior and same-origin enforcement.

Integration fixtures introduced by this plan should provide stable helper functions with explicit names (for example `issue_user_token`, `issue_session_token`, `issue_service_token`, `issue_mcp_token`) so test intent stays readable and matrix mapping remains obvious.

No speculative fallback wrappers or silent dependency masking are allowed. Tests should fail explicitly when required auth dependencies are missing or behavior drifts.

---
Revision Note (2026-02-19, Codex): Initial integrated auth campaign ExecPlan authored during package setup.
Revision Note (2026-02-19, Codex): Marked compatibility matrix publication complete and linked artifact path in `Progress`.
Revision Note (2026-02-19, Codex): Expanded to a detailed end-to-end implementation plan with milestone-level file edits, fixture contracts, validation commands, and closeout criteria.
Revision Note (2026-02-19, Codex): Executed milestones 0-4 end-to-end, recorded validation evidence, and synchronized tracker/matrix/lifecycle artifacts with final outcomes.
Revision Note (2026-02-19, Codex): Recorded post-closeout policy confirmations (`token_class=mcp` unchanged for now; PUBLIC browse remains permitted for anonymous-eligible, non-root-only paths).
Revision Note (2026-02-19, Codex): Added `MX-L4` grouped/composite runid cookie round-trip integration coverage and synced related artifacts.
