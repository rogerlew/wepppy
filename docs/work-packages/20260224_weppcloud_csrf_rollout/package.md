# WEPPcloud CSRF Rollout with rq-engine API Compatibility

**Status**: Closed (2026-02-24)

## Overview

Implement the CSRF strategy defined in `docs/schemas/weppcloud-csrf-contract.md`: enforce CSRF on cookie-authenticated Flask mutation routes while preserving bearer-token API behavior for rq-engine, browse, files, and agent/third-party clients. The outcome must harden browser flows without breaking external API consumers.

## Objectives

- Enable global Flask CSRF enforcement for WEPPcloud cookie-auth mutation routes.
- Publish a shared CSRF token source in base templates so controller JS can attach `X-CSRFToken` consistently.
- Inventory and classify Flask mutation routes, then keep only narrowly justified CSRF exemptions.
- Preserve rq-engine/browse/files bearer-token workflows so third-party and agent APIs remain unaffected.
- Add regression coverage for CSRF accept/reject paths and bridge endpoint behavior.
- Complete required correctness review and code quality review before closure.

## Scope

### Included

- WEPPcloud CSRF middleware/configuration wiring.
- Base template CSRF token discoverability updates.
- Flask mutation route classification and exemption register.
- Same-origin/CSRF alignment for bridge endpoints that rely on browser cookies.
- Targeted route/unit/integration tests for CSRF behavior.
- Package artifacts and tracker synchronization.

### Explicitly Out of Scope

- Requiring CSRF headers on bearer-token rq-engine, browse, files, or query-engine endpoints.
- Redesigning JWT scopes, token classes, or run authorization semantics.
- Broad authentication architecture changes beyond CSRF boundary hardening.

## Success Criteria

- [x] Global CSRF protection is active for WEPPcloud cookie-auth mutation routes.
- [x] Base templates expose a CSRF token source consumed by existing JS fetch/form helpers.
- [x] Non-browser/bridge exemptions are minimal, documented, and covered by tests.
- [x] Browser mutation requests without valid CSRF token fail; valid token requests succeed.
- [x] rq-engine third-party bearer workflows continue to work without CSRF headers.
- [x] Correctness review and code quality review findings are resolved or explicitly accepted.
- [x] Required validation and documentation gates executed, including broad-exception changed-file enforcement.

## Dependencies

### Prerequisites

- Normative CSRF contract: `docs/schemas/weppcloud-csrf-contract.md`.
- Existing auth/session contracts:
  - `docs/schemas/weppcloud-session-contract.md`
  - `docs/dev-notes/auth-token.spec.md`
  - `docs/dev-notes/rq-engine-agent-api.md`

### Blocks

- Full closure of CSRF-related security debt for WEPPcloud browser mutation routes.
- Clean handoff for future auth-hardening initiatives relying on stable CSRF boundaries.

## Related Packages

- **Related**: [docs/work-packages/20260208_rq_engine_agent_usability/](../20260208_rq_engine_agent_usability/)
- **Related**: [docs/work-packages/20260219_cross_service_auth_tokens/](../20260219_cross_service_auth_tokens/)
- **Follow-up candidate**: targeted rq-engine cookie-path same-origin hardening package if gap remains after this rollout.

## Timeline Estimate

- **Expected duration**: 2-4 days
- **Complexity**: Medium
- **Risk level**: Medium-High (security + compatibility)

## References

- `docs/schemas/weppcloud-csrf-contract.md`
- `wepppy/weppcloud/app.py`
- `wepppy/weppcloud/configuration.py`
- `wepppy/weppcloud/templates/base_pure.htm`
- `wepppy/weppcloud/routes/weppcloud_site.py`
- `wepppy/weppcloud/routes/bootstrap.py`
- `wepppy/weppcloud/routes/_security/oauth.py`
- `wepppy/microservices/rq_engine/session_routes.py`
- `tests/weppcloud/routes/test_rq_engine_token_api.py`
- `tests/microservices/test_rq_engine_session_routes.py`

## Deliverables

- `docs/work-packages/20260224_weppcloud_csrf_rollout/package.md`
- `docs/work-packages/20260224_weppcloud_csrf_rollout/tracker.md`
- `docs/work-packages/20260224_weppcloud_csrf_rollout/prompts/active/weppcloud_csrf_rollout_execplan.md`
- `docs/work-packages/20260224_weppcloud_csrf_rollout/artifacts/route_classification.md`
- `docs/work-packages/20260224_weppcloud_csrf_rollout/artifacts/csrf_exemptions_register.md`
- `docs/work-packages/20260224_weppcloud_csrf_rollout/artifacts/final_validation_summary.md`
- `docs/work-packages/20260224_weppcloud_csrf_rollout/artifacts/reviewer_findings.md`
- `docs/work-packages/20260224_weppcloud_csrf_rollout/artifacts/code_quality_review.md`
