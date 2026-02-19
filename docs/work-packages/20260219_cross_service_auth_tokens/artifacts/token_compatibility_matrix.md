# Cross-Service Token Compatibility Matrix

> Date: 2026-02-19  
> Package: `docs/work-packages/20260219_cross_service_auth_tokens/`  
> Purpose: document current cross-service token acceptance behavior and bind every matrix row to executable tests.

## Sources

- `wepppy/weppcloud/routes/weppcloud_site.py`
- `wepppy/weppcloud/utils/rq_engine_token.py`
- `wepppy/microservices/rq_engine/auth.py`
- `wepppy/microservices/rq_engine/session_routes.py`
- `wepppy/microservices/rq_engine/job_routes.py`
- `wepppy/microservices/browse/auth.py`
- `wepppy/query_engine/app/mcp/auth.py`

## Scope and Assumptions

- This matrix documents current implementation behavior.
- `ALLOW`/`CONDITIONAL` for bearer rows assumes the token can be decoded by the target service (signature/secret + audience checks pass).
- rq-engine and browse decode with WEPP auth token settings (default audience `rq-engine`).
- MCP decodes with MCP token settings (`WEPP_MCP_JWT_*`).
- In normal deployments, MCP tokens are signed with a different secret domain than rq-engine/browse.
- `No token` means no bearer token; cookie/login-session behavior is broken out separately.

## Legend

- `ALLOW`: accepted when presented.
- `CONDITIONAL`: accepted only when listed conditions pass.
- `DENY`: rejected by policy.
- `N/A`: token class is not the auth mechanism for that surface.

## Integrated Case Index

- `MX-A1`: `tests/integration/test_cross_service_auth_portability.py::test_portability__mx_a1_session_token_requires_active_marker`
- `MX-A2`: `tests/integration/test_cross_service_auth_portability.py::test_portability__mx_a2_user_token_portable_to_rq_engine_and_browse`
- `MX-A3`: `tests/integration/test_cross_service_auth_portability.py::test_portability__mx_a3_service_token_portable_to_rq_engine_and_browse`
- `MX-A4`: `tests/integration/test_cross_service_auth_portability.py::test_portability__mx_a4_wepp_signed_mcp_class_token_rejected_by_browse_policy`
- `MX-A5`: `tests/integration/test_cross_service_auth_portability.py::test_portability__mx_a5_wepp_signed_mcp_class_token_conditionally_allows_rq_engine`
- `MX-A6`: `tests/integration/test_cross_service_auth_portability.py::test_portability__mx_a6_mcp_token_is_accepted_on_mcp_and_denied_elsewhere`
- `MX-L1`: `tests/integration/test_cross_service_auth_lifecycle.py::test_lifecycle__mx_l1_browser_renewal_fallback_sequence`
- `MX-L2`: `tests/integration/test_cross_service_auth_lifecycle.py::test_lifecycle__mx_l2_revocation_denylist_propagates_across_surfaces`
- `MX-L3`: `tests/integration/test_cross_service_auth_lifecycle.py::test_lifecycle__mx_l3_wepp_secret_rotation_overlap_and_retirement`
- `MX-L4`: `tests/integration/test_cross_service_auth_lifecycle.py::test_lifecycle__mx_l4_grouped_cookie_round_trip_from_issue_to_browse`

## Token Profiles (Reference)

| Token profile | token_class | Typical audience | Typical issuance path | Notes |
|---|---|---|---|---|
| Run-scoped session token | `session` | `rq-engine` | `POST /rq-engine/api/runs/{runid}/{config}/session-token` | Includes `session_id`, `runid`, `config`; rq-engine enforces Redis session marker on use. |
| WEPPcloud UI fallback token | `user` | `rq-engine` | `POST /weppcloud/api/auth/rq-engine-token` | Short-lived browser recovery token; includes `roles`, `email`, `jti`; no explicit `runs` claim. |
| Service token | `service` | Varies (`rq-engine` for rq routes) | CLI/service issuance | Requires run scope claims on run-scoped routes. |
| MCP token | `mcp` | MCP audience (`WEPP_MCP_JWT_AUDIENCE`) | MCP-side issuance | MCP middleware requires `token_class=mcp`; browse policy rejects `mcp` token class. |

## Matrix A - Bearer Compatibility by Surface

| Surface | No token | session | user | service | mcp | Primary conditions | Case IDs / linked tests |
|---|---|---|---|---|---|---|---|
| rq-engine run mutation routes (`/api/runs/{runid}/{config}/...` requiring `rq:enqueue`) | DENY | CONDITIONAL | CONDITIONAL | CONDITIONAL | CONDITIONAL | Needs valid JWT, `rq:enqueue`, and `authorize_run_access`; session also needs live marker + matching `runid`; service/mcp need run scope claims. | `tests/microservices/test_rq_engine_auth.py::test_authorize_run_access_allows_service_with_matching_run_scope`, `tests/microservices/test_rq_engine_auth.py::test_authorize_run_access_rejects_service_with_wrong_run_scope`, `tests/weppcloud/routes/test_rq_engine_token_api.py::test_issue_rq_engine_token_uses_expected_claims` |
| rq-engine run export routes (require `rq:export`) | DENY | CONDITIONAL | CONDITIONAL | CONDITIONAL | CONDITIONAL | Same run authorization model as mutations, but scope is `rq:export`. | `tests/weppcloud/routes/test_rq_engine_token_api.py::test_issue_rq_engine_token_uses_expected_claims`, `tests/microservices/test_rq_engine_auth.py::test_authorize_run_access_allows_service_with_matching_run_scope`, `tests/microservices/test_rq_engine_auth.py::test_authorize_run_access_rejects_mcp_without_run_scope` |
| rq-engine session-token endpoint, bearer branch (`POST /api/runs/{runid}/{config}/session-token`) | CONDITIONAL | CONDITIONAL | CONDITIONAL | CONDITIONAL | CONDITIONAL | No bearer token can still work via cookie/public fallback path; bearer path requires `rq:status` and run authorization checks. | `MX-A1`, `MX-A2`, `MX-A3`, `MX-A5`, `tests/microservices/test_rq_engine_session_routes.py::test_session_token_rejects_service_token_without_run_scope` |
| rq-engine polling routes (`GET /api/jobstatus/{job_id}`, `GET/POST /api/jobinfo...`) | CONDITIONAL | CONDITIONAL | CONDITIONAL | CONDITIONAL | CONDITIONAL | Depends on `RQ_ENGINE_POLL_AUTH_MODE`: `open` allows no token; `token_optional` allows no token but validates bearer when present; `required` requires `rq:status`. | `tests/microservices/test_rq_engine_jobinfo.py::test_polling_mode_required_rejects_without_token`, `tests/microservices/test_rq_engine_jobinfo.py::test_polling_mode_token_optional_accepts_without_token`, `tests/microservices/test_rq_engine_jobinfo.py::test_polling_mode_required_accepts_valid_token` |
| rq-engine cancel route (`POST /api/canceljob/{job_id}`) | DENY | CONDITIONAL | CONDITIONAL | CONDITIONAL | CONDITIONAL | Requires scope `rq:status` or `culvert:batch:submit`; if job has `runid` and token class is `session`, session marker check is enforced for that run. | `tests/microservices/test_rq_engine_jobinfo.py::test_canceljob_requires_auth`, `tests/microservices/test_rq_engine_jobinfo.py::test_canceljob_accepts_valid_token`, `tests/microservices/test_rq_engine_jobinfo.py::test_canceljob_rejects_session_without_marker`, `tests/microservices/test_rq_engine_jobinfo.py::test_canceljob_accepts_session_with_marker` |
| browse run routes (`authorize_run_request`) | CONDITIONAL | CONDITIONAL | CONDITIONAL | CONDITIONAL | DENY | No-token allowed only for public run routes that permit anonymous access and non-root-only paths; bearer/cookie tokens must satisfy run access; allowed token classes are `session`, `user`, `service`. | `MX-A2`, `MX-A3`, `MX-A4`, `tests/microservices/test_browse_auth_routes.py::test_browse_allows_public_run_without_token` |
| browse group routes (`authorize_group_request`) | DENY | DENY | CONDITIONAL | CONDITIONAL | DENY | Allowed token classes are `user`/`service`; user requires role in `Admin|PowerUser|Dev|Root`; service may require `service_groups` depending on endpoint. | `tests/microservices/test_browse_auth_routes.py::test_group_routes_require_auth`, `tests/microservices/test_browse_auth_routes.py::test_group_user_token_with_privileged_role_is_allowed`, `tests/microservices/test_browse_auth_routes.py::test_group_routes_accept_scoped_service_token`, `tests/microservices/test_browse_auth_routes.py::test_group_routes_reject_session_token_class` |
| query-engine MCP routes (`/mcp/*`) | DENY | DENY | DENY | DENY | CONDITIONAL | Requires valid MCP JWT, `token_class=mcp`, allowed scopes, and issuer/audience/time claim validation. | `MX-A6`, `tests/query_engine/test_mcp_auth.py::test_non_mcp_token_class_is_rejected`, `tests/query_engine/test_mcp_auth.py::test_scope_validation` |

## Matrix B - Cookie/Login Session Compatibility

| Surface | Anonymous browser session | Authenticated Flask login session | Notes | Case IDs / linked tests |
|---|---|---|---|---|
| `POST /weppcloud/api/auth/rq-engine-token` | DENY (`401`) | CONDITIONAL | Requires same-origin request checks; issues `token_class=user` token for rq-engine fallback use. | `MX-L1`, `tests/weppcloud/routes/test_rq_engine_token_api.py::test_issue_rq_engine_token_requires_auth`, `tests/weppcloud/routes/test_rq_engine_token_api.py::test_issue_rq_engine_token_returns_token`, `tests/weppcloud/routes/test_rq_engine_token_api.py::test_issue_rq_engine_token_blocks_cross_origin` |
| `POST /rq-engine/api/runs/{runid}/{config}/session-token` (cookie branch) | CONDITIONAL | CONDITIONAL | Private runs require valid Flask session cookie and run authorization; public runs can fall back to anonymous session token issuance. | `tests/microservices/test_rq_engine_session_routes.py::test_session_token_issues_with_cookie`, `tests/microservices/test_rq_engine_session_routes.py::test_session_token_allows_public_run_without_cookie`, `tests/microservices/test_rq_engine_session_routes.py::test_session_token_private_run_requires_authenticated_cookie_session`, `MX-L1`, `MX-L4` |
| browse run routes via browse JWT cookie (`wepp_browse_jwt*`) | CONDITIONAL | CONDITIONAL | Cookie token is attempted first, then bearer fallback; invalid cookie can degrade to anonymous context when no bearer token is present. | `tests/microservices/test_browse_auth_routes.py::test_public_browse_ignores_invalid_cookie_without_bearer`, `tests/microservices/test_browse_auth_routes.py::test_private_browse_invalid_cookie_without_bearer_still_redirects`, `tests/microservices/test_browse_auth_routes.py::test_private_browse_falls_back_to_bearer_when_cookie_invalid`, `MX-L4` |

## Key Invariants Backed by Tests

1. MCP routes reject non-`mcp` token classes even if signatures and scopes are otherwise valid (`MX-A6`, `tests/query_engine/test_mcp_auth.py::test_non_mcp_token_class_is_rejected`).
2. Browse run routes reject `mcp` token class by policy (`MX-A4`), and browse group routes reject token classes outside the allowed user/service set (direct rejection coverage: `tests/microservices/test_browse_auth_routes.py::test_group_routes_reject_session_token_class`).
3. Session tokens fail closed on missing Redis session markers for rq-engine run-scoped checks (`MX-A1`, `tests/microservices/test_rq_engine_jobinfo.py::test_canceljob_rejects_session_without_marker`).
4. WEPPcloud fallback token endpoint requires authenticated login session plus same-origin checks (`MX-L1`, `tests/weppcloud/routes/test_rq_engine_token_api.py::test_issue_rq_engine_token_blocks_cross_origin`).
5. RQ-engine poll route behavior remains mode-driven (`tests/microservices/test_rq_engine_jobinfo.py::test_polling_mode_required_rejects_without_token`, `tests/microservices/test_rq_engine_jobinfo.py::test_polling_mode_token_optional_accepts_without_token`).

## Resolved Policy Notes

1. Keep rq-engine conditional acceptance of WEPP-signed tokens carrying `token_class=mcp` for now (`MX-A5`); no contract change requested.
2. Browse access for PUBLIC runs should remain permitted for anonymous-eligible, non-root-only paths; stale/invalid browse cookies should not block anonymous public browse access (`tests/microservices/test_browse_auth_routes.py::test_public_browse_ignores_invalid_cookie_without_bearer`).
3. Poll mode default remains `open`; required and optional behavior are exercised in `tests/microservices/test_rq_engine_jobinfo.py` poll-mode tests.
