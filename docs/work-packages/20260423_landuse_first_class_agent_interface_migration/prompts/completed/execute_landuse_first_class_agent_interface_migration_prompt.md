# Execute: Landuse First-Class Agent Interface Migration (Phased)

Execute the active work package end-to-end:

- Package: `/home/workdir/wepppy/docs/work-packages/20260423_landuse_first_class_agent_interface_migration/`
- ExecPlan (completed): `/home/workdir/wepppy/docs/work-packages/20260423_landuse_first_class_agent_interface_migration/prompts/completed/landuse_first_class_agent_interface_migration_execplan.md`
- Security gate artifact: `/home/workdir/wepppy/docs/work-packages/20260423_landuse_first_class_agent_interface_migration/artifacts/2026-04-24_security_review.md`

Required outcomes:
1. Landuse machine/state APIs are migrated to first-class rq-engine interfaces in phases with explicit go/no-go gates.
2. WEPPcloud render routes remain in WEPPcloud (`/report/landuse`, `/landuse-user-defined`, `/landuse-map`).
3. Gate 0 decisions are finalized before migration work starts:
   - PUP/active-root strategy
   - token-class/scope policy
   - browser transport strategy (`requestWithSessionToken` for moved routes)
4. Phase 1 delivers rq-engine replacements for:
   - `tasks/set_landuse_mode/`
   - `tasks/set_landuse_db/`
   - `tasks/modify_landuse_coverage/`
5. Phase 2 delivers read/discovery parity:
   - `GET /api/runs/{runid}/{config}/controllers/landuse/state`
   - endpoint catalog coverage for migrated landuse operations
6. Phase 3 moves map/catalog/file surfaces only after hardening parity and security gates pass.
7. Legacy Flask compatibility/deprecation policy is documented with explicit sunset criteria.

Execution scope:
- WEPPcloud:
  - `wepppy/weppcloud/routes/nodb_api/landuse_bp.py`
  - `wepppy/weppcloud/controllers_js/landuse.js`
  - `wepppy/weppcloud/controllers_js/landuse_modify_gl.js`
  - `wepppy/weppcloud/templates/controls/landuse_map.htm`
  - `wepppy/weppcloud/templates/controls/landuse_user_defined.htm`
  - `wepppy/weppcloud/routes/_run_context.py`
  - `wepppy/weppcloud/utils/helpers.py`
- rq-engine:
  - `wepppy/microservices/rq_engine/landuse_routes.py`
  - `wepppy/microservices/rq_engine/schema_defaults_routes.py`
  - `wepppy/microservices/rq_engine/auth.py`
- Contracts/docs:
  - `docs/schemas/rq-engine-agent-api-contract.md`
  - `docs/schemas/rq-response-contract.md`
  - `docs/schemas/weppcloud-csrf-contract.md`

Non-negotiable constraints:
- Do not move UI-render routes from WEPPcloud in this package.
- Do not bypass security gates for high-risk map/catalog/file endpoints.
- Do not introduce cookie-mutation fallback for migrated rq-engine mutators.
- Preserve explicit error contracts; do not add silent fallbacks.

Required gate checks before phase advancement:
- Gate 0: strategy decisions recorded in ExecPlan + tracker + security artifact.
- Gate 1: Phase 1 route/auth/transport tests pass.
- Gate 2: discovery/openapi parity tests pass.
- Gate 3: hardening parity and abuse/concurrency tests pass; no unresolved medium/high security findings for moved surfaces.

Validation commands (run as phase-appropriate):
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1`
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js`
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js`
- `wctl doc-lint --path docs/work-packages/20260423_landuse_first_class_agent_interface_migration --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md`

Package lifecycle updates required:
- Keep ExecPlan living sections current (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`).
- Update `tracker.md` with UTC-stamped progress, decisions, risks, and test evidence.
- Keep security artifact current; close findings as phases land.
- Update `package.md` when scope/contract details solidify.
- Move package state in `PROJECT_TRACKER.md` from Backlog -> In Progress -> Done as work advances.
- On completion, move ExecPlan from `prompts/active/` to `prompts/completed/` with outcome notes.

Finish with a concise closure summary:
- changed files
- route/contract behavior delta by phase
- validation commands + results
- security finding disposition
- residual risks/follow-ups
