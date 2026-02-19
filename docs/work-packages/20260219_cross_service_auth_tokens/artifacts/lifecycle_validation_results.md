# Lifecycle Validation Results

> Package: `docs/work-packages/20260219_cross_service_auth_tokens/`  
> Date: 2026-02-19

## Milestone 0 - Harness Bring-Up

- command: `wctl run-pytest tests/integration/test_cross_service_auth_portability.py -q`
  result: failed (`3 failed, 3 passed`) because `RecordingRedis` lacked `setex` outside the integration fixture scope.
- command: `wctl run-pytest tests/integration/test_cross_service_auth_portability.py -q`
  result: passed (`6 passed, 0 failed`) after making the integration Redis fixture autouse.

## Milestone 1 - Matrix Portability

- command: `wctl run-pytest tests/integration/test_cross_service_auth_portability.py -q`
  result: passed (`6 passed, 0 failed`).

## Milestone 2 - Lifecycle Flows

- command: `wctl run-pytest tests/integration/test_cross_service_auth_lifecycle.py -q`
  result: passed (`3 passed, 0 failed`).
- command: `wctl run-pytest tests/integration/test_cross_service_auth_lifecycle.py -q`
  result: passed (`4 passed, 0 failed`) after adding grouped/composite runid cookie round-trip coverage (`MX-L4`).

## Milestone 3 - Auth Primitive Unit Gaps

- command: `wctl run-pytest tests/weppcloud/test_auth_tokens.py tests/microservices/test_rq_engine_auth.py -q`
  result: passed (`35 passed, 0 failed`).

## Milestone 4 - Full Validation Gates

- command: `wctl run-pytest tests/weppcloud/routes/test_rq_engine_token_api.py tests/microservices/test_rq_engine_session_routes.py tests/microservices/test_browse_auth_routes.py tests/query_engine/test_mcp_auth.py`
  result: passed (`120 passed, 0 failed`).
- command: `wctl run-npm test -- http`
  result: passed (`13 passed, 0 failed`).
- command: `wctl doc-lint --path docs/work-packages/20260219_cross_service_auth_tokens`
  result: passed (`5 files validated, 0 errors, 0 warnings`).
- command: `wctl doc-lint --path docs/dev-notes/auth-token.spec.md`
  result: passed (`1 files validated, 0 errors, 0 warnings`).

## Post-Closeout Follow-Up

- command: `wctl run-pytest tests/integration/test_cross_service_auth_portability.py -q`
  result: passed (`6 passed, 0 failed`) after grouped fixture refactor.
- command: `wctl run-pytest tests/integration/test_cross_service_auth_portability.py tests/integration/test_cross_service_auth_lifecycle.py -q`
  result: passed (`10 passed, 0 failed`) including grouped/composite runid cookie integration case (`MX-L4`).
- command: `wctl doc-lint --path docs/work-packages/20260219_cross_service_auth_tokens`
  result: passed (`6 files validated, 0 errors, 0 warnings`).
