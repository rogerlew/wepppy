# WP-11 Plan: Geneva UI Parameterization, RQ-Engine State, and WEPPcloud Integration
Status: not_started  
Last Updated: 2026-04-16  
Work-Package: `WP-11`  
Owner: `codex`

References:
- Plan: `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md`
- Spec: `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`
- Prior closeout: `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-10_qa_security_closeout_and_release_readiness.md`
- Current Geneva control template: `/workdir/wepppy/wepppy/weppcloud/templates/controls/geneva_pure.htm`
- Current Geneva WEPPcloud routes: `/workdir/wepppy/wepppy/weppcloud/routes/nodb_api/geneva_bp.py`
- Current run bootstrap template: `/workdir/wepppy/wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2`
- Current rq-engine defaults/state baseline: `/workdir/wepppy/wepppy/microservices/rq_engine/schema_defaults_routes.py`

## 1. Confirmed Current-State Gaps (2026-04-16)
1. Geneva run-page control is not parameterized for operational workflow; it only exposes CN-table editing launch.
2. `Edit Geneva CN Table` uses `button_row(full_width=True)` and does not follow existing control-button sizing conventions.
3. No dedicated Geneva controller exists under `wepppy/weppcloud/controllers_js`.
4. No Geneva routes exist under `wepppy/microservices/rq_engine` (`rg -n "geneva" wepppy/microservices/rq_engine` returns no matches).
5. Geneva control state is not wired through an rq-engine Geneva state interface.

## 2. Scope
In scope:
- Add parameterized Geneva UI controls for `prepare_hrus`, `build_frequency_panel`, and `run_batch`.
- Make CN-table launch button convention-aligned (non-full-width row behavior).
- Add rq-engine Geneva enqueue and state interface endpoints with canonical auth and error contracts.
- Integrate Geneva control lifecycle with rq-engine state reads (controller initialization, status reconciliation, active job tracking).
- Keep legacy WEPPcloud Geneva endpoints compatible during migration or provide an explicit compatibility shim.
- Add/extend tests and evidence to close WP-11.

Out of scope:
- New Geneva scientific/kernel algorithms.
- Post-release feature expansion beyond UI/rq-engine state linkage.
- Changes outside Geneva and directly related run-control surfaces.

## 3. Software Backlog, Cost, and Ownership
| Backlog ID | Deliverable | Repo(s) | Owner | Estimate (eng-days) | Notes |
| --- | --- | --- | --- | --- | --- |
| `WP11-B01` | Finalize Geneva rq-engine endpoint contracts (enqueue + state) and payload schema | `wepppy` | WEPPpy NoDb hydrology stack | 0.5 | Includes operation IDs, route paths, error contract alignment |
| `WP11-B02` | Implement rq-engine Geneva router and register it in app bootstrap/OpenAPI | `wepppy` | WEPPpy NoDb hydrology stack | 1.5 | Add auth (`require_jwt`, `authorize_run_access`) and queue submission wiring |
| `WP11-B03` | Implement Geneva state payload builder and revision semantics for controller hydration | `wepppy` | WEPPpy NoDb hydrology stack | 1.0 | Reuse run-state concepts where possible; avoid duplicate state truth sources |
| `WP11-B04` | Build Geneva JS controller for parameterized prepare/panel/run lifecycle | `wepppy` | WEPPpy NoDb hydrology stack | 2.0 | Includes status polling/reconciliation, button disable/enable states, form payload normalization |
| `WP11-B05` | Update Geneva control template to add parameter inputs + fix CN-table button width convention | `wepppy` | WEPPpy NoDb hydrology stack | 0.5 | Remove `button_row(full_width=True)` usage for CN-table control |
| `WP11-B06` | Integrate run-page bootstrap/controller registration so Geneva uses rq-engine state, not `.j2` job-hint dependence | `wepppy` | WEPPpy NoDb hydrology stack | 1.0 | Add Geneva controller entry and state bootstrap hooks |
| `WP11-B07` | Test expansion and regression coverage (routes, controller, template, integration) | `wepppy` | WEPPpy NoDb hydrology stack | 1.5 | Pytest + Jest + render tests |
| `WP11-B08` | Final QA/security/manual smoke evidence and closeout updates | `wepppy` | WEPPpy NoDb hydrology stack | 0.5 | Includes go/no-go and residual-risk inventory |

Estimated direct effort: **8.5 eng-days**  
Recommended risk buffer: **+2.0 eng-days** (auth/contract integration + async state race fixes)  
Total planned budget: **10.5 eng-days**

## 4. Timeline (Accounted)
- 2026-04-17 to 2026-04-18: `WP11-B01` to `WP11-B03`
- 2026-04-21 to 2026-04-23: `WP11-B04` to `WP11-B06`
- 2026-04-24 to 2026-04-25: `WP11-B07`
- 2026-04-27: `WP11-B08` closeout + recommendation
- Contingency window: 2026-04-28 to 2026-04-29

Planned recommendation date: **2026-04-27** (or **2026-04-29** if contingency is consumed)

## 5. Implementation Breakdown
### 5.1 rq-engine
- Add new Geneva router module (expected new file): `wepppy/microservices/rq_engine/geneva_routes.py`.
- Register router in `wepppy/microservices/rq_engine/__init__.py`.
- Define Geneva enqueue endpoints for:
  - prepare HRUs
  - build frequency panel
  - run batch
- Define Geneva state endpoint returning run-scoped Geneva state needed by the UI controller:
  - enabled/config snapshot
  - active/last job IDs
  - last status message/progress
  - state revision token for reconciliation
- Enforce canonical auth and run access checks.

### 5.2 WEPPcloud server routes
- Update/bridge `wepppy/weppcloud/routes/nodb_api/geneva_bp.py` to either:
  - proxy to rq-engine Geneva endpoints, or
  - preserve route contracts while switching submission/state reads to rq-engine-backed interfaces.
- Preserve existing API error contract shape for current clients unless an explicit migration note is recorded.

### 5.3 Geneva control UI + controller
- Update template `wepppy/weppcloud/templates/controls/geneva_pure.htm`:
  - add parameter fields for prepare/panel/run requests,
  - add convention-aligned action button rows,
  - remove full-width CN-table button row.
- Add Geneva controller (expected new file): `wepppy/weppcloud/controllers_js/geneva.js`.
- Register controller in run bootstrap/init path so Geneva control initializes when mod is active.
- Controller state flow must read rq-engine Geneva state endpoint and reconcile action/status panels from that state.

### 5.4 Bootstrap migration constraint
- Geneva controller must not depend on `.j2` `jobIds` hints as its primary state source.
- `.j2` bootstrap may still carry generic context, but Geneva runtime state authority must be rq-engine state payload.

## 6. Required Validation Gates
Core (`/workdir/wepppy`):
- `wctl run-pytest tests/weppcloud/routes/test_geneva_bp.py tests/weppcloud/routes/test_geneva_wp08_routes.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_geneva_routes.py --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- `wctl run-pytest tests --maxfail=1`
- `wctl run-npm lint`
- `wctl run-npm test`
- `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py`
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- `wctl check-rq-graph` (required only if queue dependency edges change)

Docs:
- `wctl doc-lint --path wepppy/nodb/mods/geneva`

## 7. Mandatory Review Workflow
- Code review: correctness, contract compatibility, controller lifecycle integrity.
- QA review: parameter flow, control behavior, state hydration/reload determinism, run-page behavior.
- Security review: auth/authorization boundaries, payload validation, error sanitization, queue misuse prevention.
- All fix-now findings must be resolved before marking WP-11 `done`.

## 8. Manual Integration Evidence Required
- Run-page Geneva control flow:
  - configure parameters,
  - queue prepare,
  - queue panel build,
  - queue run batch,
  - validate final status/results/query/report consistency.
- Confirm Geneva controller status/job display matches rq-engine state endpoint transitions.
- Confirm `Edit Geneva CN Table` renders non-full-width and consistent with existing control conventions.
- Record residual limitations and explicit mitigation ownership.

## 9. Risks and Mitigations
| Risk ID | Description | Severity | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| `WP11-R1` | Contract drift between legacy Geneva routes and new rq-engine endpoints | medium | Keep compatibility shim + route tests until full cutover complete | WEPPpy NoDb hydrology stack |
| `WP11-R2` | UI state races between enqueue response and state polling | medium | Single source of truth from rq-engine state + deterministic polling/backoff tests | WEPPpy NoDb hydrology stack |
| `WP11-R3` | Bootstrap migration regression for non-Geneva mods | low | Limit bootstrap edits to Geneva registration path and run full test gate | WEPPpy NoDb hydrology stack |

No pre-authorized waivers for fix-now findings.

## 10. Exit Criteria Checklist
- [ ] Geneva run-page UI supports parameterized prepare/panel/run actions.
- [ ] CN-table launch button follows existing sizing convention (not full-width control row).
- [ ] Geneva rq-engine enqueue + state interface exists and is used by Geneva controller runtime state.
- [ ] `.j2` bootstrap is no longer the Geneva runtime-state authority.
- [ ] Required gates pass with exact outcomes captured.
- [ ] Code + QA + security reviews are complete and fix-now findings resolved.
- [ ] Recommendation and residual-risk ownership are documented.
