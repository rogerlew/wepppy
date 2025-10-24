# Prompt – Bootstrap Refactor & Smoke Testing

## Goal
Implement the new controller bootstrap flow and author smoke validation scripts for the Pure runs0 experience.

## Steps
1. **Bootstrap API design** ✅
   - `Controller.bootstrap(context)` contract implemented; run context documented via `WCControllerBootstrap`.
2. **run_page_bootstrap.js.j2 refactor** ✅
   - Pure-only path established; controller bootstrap hooks wired in.
3. **Controller updates** ✅
   - Controllers handle their own job IDs + StatusStream connections.
4. **Smoke script** *(handed off)*
   - Playwright suite now provisions runs (optional) and validates map tabs, StatusStream wiring, landuse mode toggles, and treatments status panels.
   - Further automation (job submission, profile loader, CI integration) tracked under the `20251023_smoke_tests` work package.
   - Document prerequisites: backend running, `SMOKE_RUN_PATH` or profile-driven provisioning, optional `SMOKE_BASE_URL` and `SMOKE_HEADLESS` overrides.
5. **Documentation updates** ✅ (bootstrap) / 🔄 (smoke)
   - Bootstrap workflow captured in `AGENTS.md` and work package notes.
   - Smoke instructions partially documented (`tests/README.smoke_tests.md`), including profile concept and `SMOKE_RUN_ROOT`; flesh out once suite expands/CI hooked.

## Completion Criteria
- Bootstrap script merged using controller-provided APIs.
- Smoke script committed (or instructions captured) and runnable by other agents.
- Docs refreshed accordingly.
