# Prompt – Bootstrap Refactor & Smoke Testing

## Goal
Implement the new controller bootstrap flow and author smoke validation scripts for the Pure runs0 experience.

## Steps
1. **Bootstrap API design**
   - Draft a `Controller.bootstrap(context)` convention (or similar) for each controller needing run-scoped initialization.
   - Document expected context keys (job IDs, feature flags, initial states).
2. **run_page_bootstrap.js.j2 refactor**
   - Detect Pure vs legacy templates.
   - Invoke controller bootstrap methods instead of manually calling `set_rq_job_id`, `triggerEvent`, etc.
   - Replace direct DOM selectors with controller emitters/helpers.
3. **Controller updates**
   - Implement `bootstrap` (or equivalent) on map, delineation, treatments, landuse, etc.
   - Ensure each controller handles its own initial job IDs and StatusStream connections.
4. **Smoke script**
   - Write a repeatable script/command (shell or npm) that:
     - Loads the Pure page (headless or manual instructions).
     - Triggers core workflows (map view, landuse build, climate upload stub, WEPP run).
     - Verifies StatusStream output (via console/log or DOM inspection).
   - Document prerequisite data (sample config/run) for the smoke run.
5. **Documentation updates**
   - Update `control-ui-styling/AGENTS.md` with bootstrap & smoke instructions.
   - Note the workflow in `package.md` and `tracker.md`.

## Completion Criteria
- Bootstrap script merged using controller-provided APIs.
- Smoke script committed (or instructions captured) and runnable by other agents.
- Docs refreshed accordingly.
