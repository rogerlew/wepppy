# WP-11 Execution Prompt: Geneva UI + RQ-Engine State Integration

Use this prompt verbatim in a new Codex/Copilot session to execute WP-11.

---

Execute WP-11 end-to-end for Geneva UI parameterization, rq-engine state integration, and package closeout.

Authoritative docs:
- `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-10_qa_security_closeout_and_release_readiness.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-11_geneva_ui_rq_engine_state_integration.md`
- `/workdir/wepppy/docs/schemas/rq-response-contract.md`
- `/workdir/wepppy/docs/schemas/weppcloud-csrf-contract.md`

Read local instructions before editing any touched area:
- `/workdir/wepppy/wepppy/nodb/AGENTS.md`
- `/workdir/wepppy/wepppy/weppcloud/AGENTS.md`
- `/workdir/wepppy/wepppy/weppcloud/controllers_js/AGENTS.md` (if JS/controller files are touched)
- `/workdir/wepppy/tests/AGENTS.md` (if tests are touched)

Scope (must complete):
1. Finalize Geneva rq-engine contracts for:
   - `prepare_hrus`
   - `build_frequency_panel`
   - `run_batch`
   - Geneva state payloads and revision semantics used by the UI controller
2. Implement and register Geneva rq-engine routes with canonical auth, run-access checks, submission envelopes, and error contracts.
3. Update/bridge WEPPcloud Geneva routes so run-page actions use rq-engine-backed enqueue/state flows while preserving current client-facing contracts unless an explicit migration note is recorded.
4. Implement parameterized Geneva run-page controls for prepare/panel/run actions.
5. Make `Edit Geneva CN Table` convention-aligned instead of a full-width control row.
6. Add Geneva controller wiring and switch Geneva runtime-state authority from `.j2` bootstrap hints to rq-engine state.
7. Add or extend route, controller, and template/render coverage for the exact WP-11 behavior.
8. Complete code review, QA review, and security review; resolve fix-now findings before closeout.
9. Capture manual smoke evidence through Geneva status/results/query/report flow.
10. Update WP-11 evidence and the implementation-plan row only after required gates and reviews pass.

Implementation targets (expected touched files):
- `wepppy/microservices/rq_engine/geneva_routes.py` (new router expected)
- `wepppy/microservices/rq_engine/__init__.py`
- `wepppy/weppcloud/routes/nodb_api/geneva_bp.py`
- `wepppy/weppcloud/templates/controls/geneva_pure.htm`
- `wepppy/weppcloud/controllers_js/geneva.js` (new controller expected)
- `wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2`
- `tests/microservices/test_rq_engine_geneva_routes.py`
- `tests/weppcloud/routes/test_geneva_bp.py`
- `tests/weppcloud/routes/test_geneva_wp08_routes.py`
- `tests/weppcloud/routes/test_pure_controls_render.py`
- `wepppy/weppcloud/controllers_js/__tests__/geneva.test.js`

Contract and migration requirements:
- rq-engine Geneva routes must enforce `require_jwt` and `authorize_run_access`.
- Request payloads must use canonical normalization and typed validation.
- Error payloads must conform to the canonical RQ response/error contract and must not leak internal traces.
- Geneva state payload must provide the run-scoped state needed by the controller, including enabled/config snapshot, active/last job IDs, status/progress, and a revision token for reconciliation.
- Geneva runtime-state authority must be the rq-engine state interface, not `.j2` `jobIds` bootstrap hints.
- `.j2` bootstrap may continue to provide generic page context, but the Geneva controller must not depend on bootstrap job hints as its primary truth source.
- Preserve compatibility for existing Geneva client flows during migration unless a bounded contract change is explicitly documented.

Required gates (`/workdir/wepppy`):
- `cd /workdir/wepppy && wctl run-pytest tests/weppcloud/routes/test_geneva_bp.py tests/weppcloud/routes/test_geneva_wp08_routes.py --maxfail=1`
- `cd /workdir/wepppy && wctl run-pytest tests/microservices/test_rq_engine_geneva_routes.py --maxfail=1`
- `cd /workdir/wepppy && wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- `cd /workdir/wepppy && wctl run-pytest tests --maxfail=1`
- `cd /workdir/wepppy && wctl run-npm lint`
- `cd /workdir/wepppy && wctl run-npm test`
- `cd /workdir/wepppy && python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`
- `cd /workdir/wepppy && python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- `cd /workdir/wepppy && wctl check-rq-graph` (required only if queue dependency edges change)
- `cd /workdir/wepppy && wctl doc-lint --path wepppy/nodb/mods/geneva`

Mandatory review workflow:
- Code review
- QA review
- Security review
- Resolve fix-now findings before closeout

Evidence updates required:
- `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-11_geneva_ui_rq_engine_state_integration.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md` (WP-11 row state/gates/evidence link)

Manual integration evidence required:
- In the Geneva run page:
  - configure parameters,
  - queue prepare,
  - queue panel build,
  - queue run batch
- Validate Geneva status/job transitions against rq-engine Geneva state endpoints and any active status-stream UI.
- Confirm query/report payload consistency after run completion.
- Confirm CN-table launch button width/layout conformance.
- Record any residual limitations and explicit mitigation ownership.

Out of scope:
- New Geneva scientific or kernel algorithm work.
- Broader non-Geneva run-page/controller modernization.
- Post-WP-11 feature expansion beyond UI/state integration and closeout.

Constraints:
- Do not modify `wepppy/weppcloud/routes/usersum/generated/docs_index.json`.
- Ignore unrelated dirty files outside Geneva/WP-11 scope.
- Keep scope bounded to WP-11 integration and closeout.

---
