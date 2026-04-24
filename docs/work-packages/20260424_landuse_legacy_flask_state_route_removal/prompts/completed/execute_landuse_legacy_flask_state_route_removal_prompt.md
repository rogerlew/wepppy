# Execute: Landuse Legacy Flask State Route Removal (Post Gate 3)

Execute the active work package end-to-end:

- Package: `/home/workdir/wepppy/docs/work-packages/20260424_landuse_legacy_flask_state_route_removal/`
- Active ExecPlan: `/home/workdir/wepppy/docs/work-packages/20260424_landuse_legacy_flask_state_route_removal/prompts/completed/landuse_legacy_flask_state_route_removal_execplan.md`
- Security artifact: `/home/workdir/wepppy/docs/work-packages/20260424_landuse_legacy_flask_state_route_removal/artifacts/2026-04-24_security_review.md`

Required outcomes:
1. Deprecated Flask landuse state/mutator compatibility routes are removed from `landuse_bp.py`.
2. WEPPcloud render routes remain in WEPPcloud and continue to pass render-route tests:
   - `/report/landuse`
   - `/landuse-user-defined`
   - `/landuse-map`
3. No in-repo callers still target removed Flask compatibility endpoints.
4. rq-engine remains the only machine/state API surface for removed operations.
5. Security artifact closes with no unresolved medium/high findings.

Non-negotiable constraints:
- Do not move render routes from WEPPcloud.
- Do not introduce cookie-mutation fallback for rq-engine mutators.
- Preserve explicit error contracts; no silent fallbacks.
- Keep route docs and schema contracts in sync with removals.

Validation commands:
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js`
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js`
- `wctl doc-lint --path docs/work-packages/20260424_landuse_legacy_flask_state_route_removal --path wepppy/weppcloud/routes/nodb_api/README.md --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md`

Package lifecycle updates required:
- Keep ExecPlan living sections current (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`).
- Update `tracker.md` with UTC-stamped progress, decisions, risks, and test evidence.
- Keep security artifact current and close findings as evidence lands.
- Update route/schema contract docs and `PROJECT_TRACKER.md` as package lifecycle advances.
- On completion, move active prompts to `prompts/completed/` with outcome notes.

## Outcome Note (2026-04-24 06:33 UTC)

Execution completed with package outcomes met:
- Deprecated Flask landuse state/mutator compatibility routes were removed from `landuse_bp.py`.
- WEPPcloud render routes remained in WEPPcloud (`/report/landuse`, `/landuse-user-defined`, `/landuse-map`) and render-route suites passed.
- Caller audit found no production in-repo callers for removed endpoints; regression tests now assert removed Flask paths return `404`.
- rq-engine remains the sole machine/state API surface for removed operations.
- Security artifact closed with no unresolved medium/high findings.
