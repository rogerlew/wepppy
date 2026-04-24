# Execute: Landuse Phase 3 Hardening Parity Tests and Migration Gate

Execute the active work package end-to-end:

- Package: `/home/workdir/wepppy/docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/`
- Active ExecPlan: `/home/workdir/wepppy/docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/prompts/completed/landuse_phase3_hardening_parity_execplan.md`
- Security artifact: `/home/workdir/wepppy/docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/artifacts/2026-04-24_security_review.md`
- Hardening matrix: `/home/workdir/wepppy/docs/work-packages/20260424_landuse_phase3_hardening_parity_tests/artifacts/2026-04-24_hardening_parity_test_matrix.md`

Required outcomes:
1. Gate 3.0 baseline hardening behaviors are frozen in tests for all required matrix rows.
2. Gate 3.1 rq-engine replacements for deferred Phase 3 landuse surfaces achieve parity on path/archive/concurrency/atomicity behavior.
3. Gate 3.2 transport/auth/discovery parity is complete for moved surfaces.
4. Gate 3.3 security gate closes with no unresolved medium/high findings for moved surfaces.
5. WEPPcloud render routes remain in WEPPcloud:
   - `/report/landuse`
   - `/landuse-user-defined`
   - `/landuse-map`

Non-negotiable constraints:
- Do not move render routes from WEPPcloud.
- Do not bypass Gate 3 hardening/security checks.
- Do not introduce cookie-mutation fallback on rq-engine mutators.
- Preserve explicit error contracts; no silent fallbacks.

Validation commands:
- `wctl run-pytest tests/weppcloud/routes/test_landuse_bp.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js`
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse_modify_gl.test.js`
- `wctl doc-lint --path docs/work-packages/20260424_landuse_phase3_hardening_parity_tests --path docs/schemas/rq-engine-agent-api-contract.md --path docs/schemas/rq-response-contract.md --path docs/schemas/weppcloud-csrf-contract.md --path PROJECT_TRACKER.md`

Package lifecycle updates required:
- Keep ExecPlan living sections current (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`).
- Update `tracker.md` with UTC-stamped progress, decisions, risks, and test evidence.
- Keep security artifact current and close findings as evidence lands.
- Update `package.md` and schema contracts as behavior/contracts solidify.
- Update `PROJECT_TRACKER.md` as package lifecycle advances.
- On completion, move active prompts to `prompts/completed/` with outcome notes.

## Outcome Note (2026-04-24 06:04 UTC)

Execution completed with Gate 3 pass verdict:
- Gate 3.0 baseline hardening behaviors frozen for all required matrix rows.
- Gate 3.1 rq-engine replacements achieved parity for deferred Phase 3 landuse surfaces.
- Gate 3.2 transport/auth/discovery parity completed (including token-bridge browser transport for moved surfaces).
- Gate 3.3 security review closed with no unresolved medium/high findings.
- WEPPcloud render routes remained in WEPPcloud (`/report/landuse`, `/landuse-user-defined`, `/landuse-map`).
