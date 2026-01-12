# Error Schema Standardization (RQ API Migration)

**Status**: Closed 2026-01-12

## Overview
The rq/api surface mixes `success` and `Success` payloads with inconsistent error semantics between weppcloud and rq-engine. This package scopes a comprehensive inventory of response schemas and client callsites to support a future migration of rq/api routes into rq-engine with consistent, status-code-first behavior.

## Objectives
- Inventory response schemas and semantic meanings across rq/api routes in weppcloud and rq-engine.
- Map frontend and backend callsites that interpret `success`/`Success` or related job-status fields.
- Produce a report artifact that documents observed patterns and inconsistencies.
- Outline a migration plan (phases, deprecations, risks) without implementing code changes.

## Scope

### Included
- rq/api responses in weppcloud and rq-engine (JSON payloads, status codes).
- Frontend callsites in `controllers_js` and `static-src` (and any server-side clients).
- Job-status semantics where responses refer to RQ job lifecycle.
- Documentation of redundant success flags and candidates for removal.

### Explicitly Out of Scope
- Implementing response schema changes.
- Migrating routes from weppcloud to rq-engine.
- Client code rewrites beyond documentation/proposals.

## Stakeholders
- **Primary**: weppcloud/rq-engine maintainers
- **Reviewers**: Roger
- **Informed**: Culvert integration stakeholders

## Success Criteria
- [x] `observed-error-schema-usages-report.md` artifact authored with endpoint + callsite inventory.
- [x] Redundant `success`/`Success` usages identified and categorized (status-code vs job-status semantics).
- [x] Proposed standard response schema and migration outline documented.
- [x] Tracker updated with decisions and risks.

## Dependencies

### Prerequisites
- None.

### Blocks
- Future rq/api migration package depends on this inventory.

## Related Packages
- **Related**: [Culvert Integration Plan Phase 6a](../../culvert-at-risk-integration/weppcloud-integration.plan.md)

## Timeline Estimate
- **Expected duration**: 2-3 days
- **Complexity**: Medium
- **Risk level**: Medium

## References
- `wepppy/microservices/rq_engine/responses.py` - rq-engine response helpers
- `wepppy/microservices/rq_engine/` - rq-engine endpoints
- `wepppy/weppcloud/routes/` - weppcloud rq/api endpoints
- `wepppy/weppcloud/controllers_js/` - frontend callsites
- `wepppy/weppcloud/static-src/` - bundled frontend callsites
- `docs/culvert-at-risk-integration/weppcloud-integration.plan.md` - Phase 6a context

## Deliverables
- `docs/work-packages/20260111_error_schema_standardization/artifacts/observed-error-schema-usages-report.md`
- `docs/schemas/rq-response-contract.md` (canonical keys + error shapes)
- Status-code-first responses across rq-engine/rq/api with canonical error payloads
- Jobstatus/jobinfo 404 behavior with polling updates
- Updated tests and docs for canonical responses

## Follow-up Work
- Content/message refactor for response copy (separate initiative)

## Closure Notes

**Closed**: 2026-01-12

**Summary**: Standardized rq-engine and rq/api response payloads around canonical keys and status-code-first semantics, removed legacy aliases, and aligned clients/tests/docs.

**Lessons Learned**: Explicitly tracking contract changes and prompt outcomes reduces drift across frontend/backends and documentation.

**Archive Status**: Closed; prompts archived under `prompts/completed/`.
