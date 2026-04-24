# Landuse First-Class Agent Interface Migration (Phased)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, agent clients can retrieve and mutate run-scoped landuse state through first-class rq-engine APIs with canonical auth and response contracts. WEPPcloud retains ownership of HTML/template-render routes, while legacy Flask state/task routes are migrated in phases behind explicit compatibility and security gates.

The migration is intentionally phased because a direct full move currently risks regressions in run-root scope handling, browser transport assumptions, and map/catalog hardening parity.

## Progress

- [x] (2026-04-24 04:01 UTC) Created work-package scaffold, tracker, security artifact, and initial ExecPlan.
- [x] (2026-04-24 04:26 UTC) Gate 0 decisions finalized and recorded in this ExecPlan, tracker, and security artifact.
- [x] (2026-04-24 04:31 UTC) Phase 1 low-risk mutators migrated and validated.
- [x] (2026-04-24 04:31 UTC) Phase 2 read/discovery parity delivered and validated.
- [x] (2026-04-24 04:31 UTC) Phase 3 gate honored as no-go for this package scope; map/catalog/file surfaces remain in WEPPcloud until a follow-up package enters and passes Gate 3.
- [x] (2026-04-24 04:36 UTC) Legacy compatibility/deprecation policy finalized with explicit sunset criteria.
- [x] (2026-04-24 05:02 UTC) Deprecation policy revised to no-delay posture (calendar hold removed; readiness criteria retained).

## Surprises & Discoveries

- Discovery confirmed an existing route discoverability gap: `modify-landuse-mapping` existed in rq-engine routing but was absent from run endpoint-doc builder output in `schema_defaults_routes.py`.
- `wctl run-pytest` for the required microservice/route suites consistently exited `137` in this environment. Equivalent suites passed under `.venv/bin/pytest`, and results are recorded in tracker/security evidence.
- Phase 1 route cutover plus Phase 2 discovery additions increased frozen rq-engine inventory contract expectations from 83 to 85 routes and required OpenAPI size-budget updates.
- Existing map/catalog/file surfaces already implement hardening-sensitive behavior under WEPPcloud and were intentionally not moved in this package to avoid bypassing Gate 3.

## Decision Log

- Decision: Keep render routes in WEPPcloud (`/report/landuse`, `/landuse-user-defined`, `/landuse-map`) and migrate machine/state APIs to rq-engine.
  Rationale: Render ownership is a UI concern; state API ownership should be standardized in rq-engine for agent clients.
  Date/Author: 2026-04-24 / Codex.

- Decision: Gate 0 PUP/active-root strategy for migrated routes is explicit `?pup=` resolution under run `_pups/` with containment checks; composite runids (`;;`) ignore `pup` and use encoded run context.
  Rationale: Preserves WEPPcloud active-root intent for scenario runs while preventing path traversal and ambiguous run-root selection.
  Date/Author: 2026-04-24 / Codex.

- Decision: Gate 0 token-class/scope policy for landuse mutators requires `rq:enqueue` plus run-access checks and allows token classes `user`, `session`, `service`, `mcp` only.
  Rationale: Matches existing rq-engine mutation model while preventing accidental broadening to unknown token classes.
  Date/Author: 2026-04-24 / Codex.

- Decision: Gate 0 browser transport policy for migrated browser callers is `requestWithSessionToken` to `/rq-engine/api/...`; no cookie-mutation fallback is introduced on rq-engine mutator routes.
  Rationale: Preserves non-browser bearer semantics and avoids CSRF-coupled mutation fallback behavior.
  Date/Author: 2026-04-24 / Codex.

- Decision: Phase 3 map/catalog/file movement remains out of this package execution scope unless Gate 3 opens; no high-risk surface was moved.
  Rationale: Security artifact retained hardening-gate controls and this package closed only Gate 0-2 deliverables.
  Date/Author: 2026-04-24 / Codex.

- Decision: Remove fixed-date deprecation delay for legacy Flask landuse mutator routes; allow removal package as soon as readiness/security criteria are met.
  Rationale: Reduces dual-route operational burden for agent-driven workflows while preserving explicit safety gates.
  Date/Author: 2026-04-24 / Codex.

## Outcomes & Retrospective

Delivered outcomes:
- Phase 1: Added rq-engine replacements for `set-landuse-mode`, `set-landuse-db`, and `modify-landuse-coverage` with explicit token-class enforcement and run authorization.
- Phase 1: Updated WEPPcloud landuse browser caller (`controllers_js/landuse.js`) to use `requestWithSessionToken` for migrated mutators.
- Phase 2: Added `GET /api/runs/{runid}/{config}/controllers/landuse/state` with `rq:read`/`rq:status` read policy and run-access enforcement.
- Phase 2: Closed endpoint-catalog parity gap by adding operation descriptors/schema/defaults for migrated landuse routes and existing `modify-landuse-mapping`.
- Contracts/docs: Updated rq-engine agent API contract, rq response contract, CSRF contract, package docs, tracker, security artifact, and project tracker lifecycle state.

Not moved in this package:
- Phase 3 map/catalog/file surfaces remained in WEPPcloud by explicit no-go gate policy.

Retrospective:
- The phased gate framework prevented premature movement of high-risk path/archive/concurrency surfaces.
- The largest operational friction was `wctl run-pytest` instability (`137` exits); direct `.venv` pytest remained reliable for verification.
- Scope discipline held: no render-route movement and no cookie fallback added.

## Scope and Route Boundary

### Routes that stay in WEPPcloud
- `/runs/{runid}/{config}/report/landuse`
- `/runs/{runid}/{config}/landuse-user-defined`
- `/runs/{runid}/{config}/landuse-map`

### Migrated to rq-engine in this package
- `POST /api/runs/{runid}/{config}/set-landuse-mode`
- `POST /api/runs/{runid}/{config}/set-landuse-db`
- `POST /api/runs/{runid}/{config}/modify-landuse-coverage`
- `GET /api/runs/{runid}/{config}/controllers/landuse/state`

### Deferred for follow-up package (Gate 3 entry required)
- `api/landuse/user_defined/catalog`
- `api/landuse/map_snapshot`
- `tasks/landuse/user_defined/upload|delete|update-description`
- `tasks/landuse/map/save|clear-override`
- `tasks/modify_landuse/` (subject to UX need)

## Gate Framework

### Gate 0: Preconditions
Status: **PASS** (2026-04-24)
1. PUP/active-root strategy finalized.
2. Browser transport strategy finalized (`requestWithSessionToken`).
3. Token-class policy finalized (`user/session/service/mcp` for mutators).
4. Endpoint discovery parity plan finalized.

### Gate 1: Phase 1 exit criteria (low-risk mutators)
Status: **PASS** (2026-04-24)
1. rq-engine replacements for `set_landuse_mode`, `set_landuse_db`, and `modify_landuse_coverage` implemented.
2. WEPPcloud callers switched for migrated routes in `landuse.js`.
3. Auth-negative/auth-positive tests passed (missing scope, token-class rejection, run-access policy coverage).
4. Canonical response/error contract verified by route and contract tests.

### Gate 2: Phase 2 exit criteria (read + discovery)
Status: **PASS** (2026-04-24)
1. Landuse controller-state read endpoint implemented.
2. Endpoint catalog/discovery includes migrated landuse operations and existing mapping mutator.
3. `rq:read`/`rq:status` read matrix validated.
4. Contract docs updated in same package closeout.

### Gate 3: Phase 3 exit criteria (map/catalog/file surfaces)
Status: **NOT ENTERED (NO-GO BY SCOPE)** (2026-04-24)
1. Hardening parity validation remains mandatory for any future movement.
2. Browser transport migration remains mandatory for any moved route.
3. Security artifact medium/high closure remains mandatory for moved surfaces.
4. No Phase 3 surface moved in this package.

### Gate 4: Closure and deprecation
Status: **PASS** (2026-04-24)
1. Legacy compatibility behavior and sunset criteria documented in package docs.
2. Tracker/security artifact updated with closeout evidence.
3. Project tracker lifecycle state updated.

## Validation and Acceptance

Validation evidence captured:
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` -> exit `137`; fallback `.venv/bin/pytest ...` passed (`28 passed`).
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> exit `137`; fallback `.venv/bin/pytest ...` passed (`10 passed`).
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` -> exit `137`; fallback `.venv/bin/pytest ...` passed (`54 passed`).
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1` -> exit `137`; fallback `.venv/bin/pytest ...` passed (`19 passed`).
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` -> passed (`20 passed`).
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js` -> passed (`3 passed`).
- `wctl doc-lint --path docs/work-packages/20260423_landuse_first_class_agent_interface_migration --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md` -> pass evidence recorded in tracker closeout.

## Idempotence and Rollback

- Gate 0-2 changes are independently deployable and reversible.
- Legacy Flask routes remain as compatibility surfaces pending sunset criteria.
- No calendar hold is required before legacy-route removal once readiness criteria are met.
- Phase 3 remains blocked until a dedicated follow-up package passes hardening + security gates.

## Revision Notes

- 2026-04-24 / Codex: Initial ExecPlan authored for phased migration with explicit gate framework.
- 2026-04-24 / Codex: Updated with Gate 0 decisions, Gate 1/2 implementation evidence, Phase 3 no-go disposition, and closure evidence.
