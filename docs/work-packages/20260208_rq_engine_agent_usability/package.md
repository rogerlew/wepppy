# RQ-Engine Agent Usability and Documentation Hardening

**Status**: Open (2026-02-08)

## Overview
RQ-engine now carries core agent-facing operations, but contract quality and documentation are still uneven across route modules and audiences. This package hardens the API contract, OpenAPI metadata, and supporting docs so agents and users can run Bootstrap and queue workflows without reverse-engineering implementation details.

## Objectives
- Define `rq-engine` as the canonical agent API surface for Bootstrap and queue operations.
- Standardize route documentation and OpenAPI quality (auth, schemas, examples, error contracts).
- Align token and authorization guidance across developer docs and user workflows.
- Close regression test gaps for auth, async lifecycle, lock contention, and canonical error shapes.

## Scope

### Included
- Agent-facing routes under `wepppy/microservices/rq_engine/*`.
- Bootstrap Phase 2 endpoint documentation and behavior alignment.
- OpenAPI metadata improvements for route discoverability and client generation.
- Documentation split by audience:
  - API contract docs for developers/agents.
  - workflow and conceptual docs for users.
- Regression tests covering documented auth and lifecycle behavior.

### Explicitly Out of Scope
- Building a separate external API gateway.
- Reworking unrelated WEPPcloud UI controls.
- Changing RQ execution internals beyond usability/documentation requirements.

## Stakeholders
- **Primary**: WEPPcloud/rq-engine maintainers, agent integrators
- **Reviewers**: Roger
- **Informed**: Bootstrap and API consumers using automation clients

## Success Criteria
- [ ] Agent-facing Bootstrap operations are available in `rq-engine` and represented in OpenAPI.
- [ ] Each agent-facing route has explicit auth requirements, schemas, and canonical error examples.
- [ ] Bootstrap async enable flow is documented and regression-tested for `queued`, `finished`, and `failed`.
- [ ] Token lifetime/audience/scope expectations are consistent across code and docs.
- [ ] A new engineer can execute documented workflows without reading source first.

## Dependencies

### Prerequisites
- Bootstrap Phase 2 endpoint baseline in `rq-engine`.
- Canonical response contract in `docs/schemas/rq-response-contract.md`.
- Current auth/token policy in `docs/dev-notes/auth-token.spec.md`.

### Blocks
- Agent onboarding improvements that depend on stable OpenAPI coverage.
- Any follow-on automation package that relies on generated client contracts.

## Related Packages
- **Depends on**: [20260111_error_schema_standardization](../20260111_error_schema_standardization/package.md)
- **Related**: [20260124_sbs_map_refactor](../20260124_sbs_map_refactor/package.md)
- **Related (mini, completed)**: [20260112_rq_api_migration](../../mini-work-packages/completed/20260112_rq_api_migration.md)
- **Related (mini, completed)**: [20260112_rq-engine-jwt-implementation](../../mini-work-packages/completed/20260112_rq-engine-jwt-implementation.md)
- **Related (mini, active)**: [20260201_rq_engine_route_agent_docs](../../mini-work-packages/20260201_rq_engine_route_agent_docs.md)

## Timeline Estimate
- **Expected duration**: 1-2 weeks
- **Complexity**: Medium
- **Risk level**: Medium

## References
- `wepppy/microservices/rq_engine/` - rq-engine route modules and OpenAPI surface
- `wepppy/weppcloud/routes/bootstrap.py` - Flask Bootstrap behavior and compatibility
- `docs/dev-notes/auth-token.spec.md` - token classes, lifetimes, scopes, revocation
- `docs/schemas/rq-response-contract.md` - canonical response and error payloads
- `wepppy/weppcloud/routes/usersum/weppcloud/bootstrap.md` - user-facing Bootstrap workflow
- `docs/weppcloud-bootstrap-spec.md` - Bootstrap implementation and phase planning

## Deliverables
- Work package artifacts and implementation notes under:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/`
  - Freeze artifact:
    `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - Contract checklist artifact:
    `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
- Route documentation and OpenAPI metadata updates in `wepppy/microservices/rq_engine/*`.
- Updated docs for auth and Bootstrap workflows:
  - `docs/dev-notes/auth-token.spec.md`
  - `docs/dev-notes/rq-engine-agent-api.md`
  - `docs/weppcloud-bootstrap-spec.md`
  - `wepppy/weppcloud/routes/usersum/weppcloud/bootstrap.md`
- Endpoint inventory drift guard:
  - `tools/check_endpoint_inventory.py`
  - `tests/tools/test_endpoint_inventory_guard.py`
- Route contract checklist drift guard:
  - `tools/check_route_contract_checklist.py`
  - `tests/tools/test_route_contract_checklist_guard.py`
- Regression coverage updates in:
  - `tests/microservices/*`
  - `tests/weppcloud/routes/*`
  - `tests/rq/*` (where queue behavior is exercised)

## Follow-up Work
- Evaluate whether read-only polling should remain open long-term or move to token-gated access if threat model changes.
- Consider generating and publishing agent SDK snippets from OpenAPI once route metadata is stable.

## Closure Notes

**Closed**: YYYY-MM-DD

**Summary**: [Fill in at closure]

**Lessons Learned**: [Fill in at closure]

**Archive Status**: [Fill in at closure]
