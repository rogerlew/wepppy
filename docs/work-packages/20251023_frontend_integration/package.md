# Frontend Integration & Smoke Automation

**Status**: Open (2025-02-24)

## Overview
The controller modernization and StatusStream cleanup landed, but the last stretch of the UI upgrade requires coordinated work: finish the remaining Pure-template migrations, rewrite the run-page bootstrap script, and ship a repeatable smoke validation flow. This work package tracks that integration push.

## Objectives
- Deliver a Pure-first runs0 page with modernized controllers (map/delineation + treatments conversions outstanding).
- Replace legacy `run_page_bootstrap.js.j2` wiring with helper-driven initialization that works for both legacy and Pure shells.
- Stand up a smoke testing workflow (manual script + plan for Playwright/Cypress) to validate controller functionality end-to-end.

## Scope
- Update remaining templates/controllers (map, delineation, treatments) to Pure + StatusStream patterns.
- Refactor bootstrap initialization to use controller emitters/helpers instead of direct DOM manipulation.
- Document and implement smoke commands covering key user flows (map, landuse build, climate upload, WEPP run, StatusStream verification).
- Align docs (`control-ui-styling`, `AGENTS.md`) with the new bootstrap and testing pipeline.

## Out of Scope
- Deep UX redesign of map/delineation controls beyond necessary modernization.
- Non-controller front-end improvements (e.g., command bar redesign, htmx adoption).
- Full end-to-end Playwright suite (planning only unless time permits).

## Stakeholders
- Frontend controllers team (implementation)
- QA/ops (smoke testing tooling)
- Docs maintainers

## Success Criteria
- Map/delineation and treatments controls run on Pure templates with consistent StatusStream telemetry.
- `run_page_bootstrap.js.j2` supports modern controllers without legacy shim calls.
- Smoke testing command/script documented and usable by other agents.
- Documentation refreshed to match the new entry points and validation steps.

## Remaining 2 % Checklist
- [x] **Map / delineation bundle** – Finish Pure template migration for map, channel delineation, and subcatchment controls; ensure they emit StatusStream events and use helper APIs end-to-end.
- [ ] **Treatments control** – Convert template + controller to the Pure/StatusStream pattern and remove legacy fallback logic.
- [ ] **Bootstrap overhaul** – Refactor `run_page_bootstrap.js.j2` to rely on controller bootstrap hooks, handle Pure vs legacy shells, and drop manual DOM pokes.
- [ ] **Smoke validation flow** – Ship a repeatable smoke script/command covering map viewing, landuse build, climate upload stub, WEPP run, and StatusStream verification; document how to run it.
- [ ] **Docs & guidance** – Update `control-ui-styling` and `AGENTS.md` with the new bootstrap workflow, smoke routine, and map/treatments status.
