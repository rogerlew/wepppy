# Cross-Service Auth Token Integration Hardening

**Status**: Closed (2026-02-19)

## Overview

Auth token behavior is mostly solid inside individual components, but cross-service behavior is still hard to reason about and easy to regress when contracts drift between WEPPcloud (Flask), rq-engine (FastAPI), browse (Starlette), and query-engine MCP (Starlette).

This package formalizes and tests the cross-service token contract as a single campaign so session fallback, revocation, rotation, and composite cookie behavior are validated as integrated flows instead of isolated unit assumptions.

## Objectives

- Publish an executable token compatibility matrix (token class x service x endpoint class) and keep it versioned with code.
- Add integration coverage for real cross-service token lifecycle paths (issue, use, fallback, revoke, rotate).
- Close auth primitive test gaps where policies exist but direct tests are missing.
- Prevent future contract drift by adding targeted guard tests and package-level acceptance checks.

## Scope

### Included

- Cross-service auth behavior spanning:
  - `wepppy/weppcloud/routes/weppcloud_site.py`
  - `wepppy/microservices/rq_engine/auth.py`
  - `wepppy/microservices/rq_engine/session_routes.py`
  - `wepppy/microservices/browse/auth.py`
  - `wepppy/query_engine/app/mcp/auth.py`
- Integration tests under `tests/` for token portability and lifecycle behavior.
- Direct unit tests for uncovered auth primitives in shared helpers.
- Documentation updates in:
  - `docs/dev-notes/auth-token.spec.md`
  - package artifacts for compatibility matrix and lifecycle traces.

### Explicitly Out of Scope

- Replacing the current JWT architecture or introducing OAuth refresh-token infrastructure.
- Reworking unrelated UI controllers beyond auth flow testability.
- Broad endpoint redesign outside what is needed to satisfy token contract tests.

## Stakeholders

- **Primary**: Roger, WEPPcloud maintainers, agent/API integrators
- **Reviewers**: Roger
- **Informed**: Teams touching rq-engine, browse, query-engine MCP, and auth docs

## Success Criteria

- [x] A checked-in compatibility matrix documents and tests allow/deny behavior for `session`, `user`, `service`, and `mcp` tokens across rq-engine, browse, and MCP routes.
- [x] Session-token fallback flow (`session-token` mint failure -> `/weppcloud/api/auth/rq-engine-token` -> retry) is validated end-to-end in integrated tests.
- [x] Revocation behavior is verified across rq-engine, browse, and MCP with shared expectations.
- [x] Secret rotation behavior is verified with acceptance of old+new secrets during overlap and rejection after retirement.
- [x] Composite runid cookie behavior is validated across issuance and browse consumption paths.
- [x] Targeted auth suites pass via `wctl run-pytest` and docs lint passes for all package docs.

## Dependencies

### Prerequisites

- Existing token contract baseline in `docs/dev-notes/auth-token.spec.md`.
- Existing canonical error contract in `docs/schemas/rq-response-contract.md`.
- Existing route-level auth tests in:
  - `tests/microservices/test_rq_engine_session_routes.py`
  - `tests/microservices/test_browse_auth_routes.py`
  - `tests/query_engine/test_mcp_auth.py`
  - `tests/weppcloud/routes/test_rq_engine_token_api.py`

### Blocks

- Hardening and rollout of agent workflows that depend on stable cross-service token semantics.
- Future auth simplification work until portability and lifecycle behavior are proven with integration tests.

## Related Packages

- **Related**: [20260208_rq_engine_agent_usability](../20260208_rq_engine_agent_usability/package.md)
- **Related**: [20260111_error_schema_standardization](../20260111_error_schema_standardization/package.md)
- **Follow-up candidate**: future auth observability and contract guard package if lifecycle tests expose repeated drift patterns

## Timeline Estimate

- **Expected duration**: 1-2 weeks
- **Complexity**: Medium
- **Risk level**: Medium-High (security and cross-service regression risk)

## References

- `docs/dev-notes/auth-token.spec.md` - normative token contract and renewal sequence.
- `wepppy/weppcloud/controllers_js/http.js` - browser fallback mechanics.
- `tests/weppcloud/test_auth_tokens.py` - shared JWT helper coverage baseline.
- `tests/microservices/test_rq_engine_auth.py` - rq-engine auth primitive baseline.
- `tests/microservices/test_rq_engine_session_routes.py` - session issuance and cookie behavior.
- `tests/microservices/test_browse_auth_routes.py` - browse auth modes and fallbacks.
- `tests/query_engine/test_mcp_auth.py` - MCP token validation rules.
- `tests/weppcloud/routes/test_run_0_nocfg_auth_bridge.py` - composite cookie bridge behavior.

## Deliverables

- New work-package tracker and ExecPlan for integrated auth campaign execution.
- Compatibility matrix artifact and lifecycle test artifact(s) in `artifacts/`.
- New/updated integration and unit tests for token portability, renewal fallback, revocation, and rotation.
- Documentation updates for any contract clarifications discovered during implementation.

## Follow-up Work

- Evaluate whether poll endpoint auth mode should remain open by default once lifecycle coverage and telemetry are in place.
- Consider promoting compatibility matrix checks into a dedicated CI guard command if drift repeats.

## Closure Notes

**Closed**: 2026-02-19

**Summary**: Delivered integrated cross-service auth hardening coverage across portability, lifecycle, grouped/composite cookie round-trip behavior, and primitive helper gaps. Added `tests/integration/` harness + suites, updated the compatibility matrix with linked test IDs for every row, and captured full validation evidence in `artifacts/lifecycle_validation_results.md`.

**Lessons Learned**: Integration fixtures must be autouse when they replace global infrastructure stubs (`redis.Redis`) or route-level behavior can silently drift between tests. Matrix-first test design reduced ambiguity and made policy mismatches explicit early.

**Archive Status**: Active package retained for future policy follow-ups (no remaining implementation blockers).
