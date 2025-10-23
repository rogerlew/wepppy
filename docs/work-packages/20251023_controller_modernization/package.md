# Controller Modernization Documentation Backlog
> Created 2025-02-14 to consolidate retroactive documentation clean-up after the controller modernization (WSClient removal, helper-first controllers).
> **Status:** Closed 2025-02-14

## Context
- All controllers now rely on `controlBase.attach_status_stream` + `StatusStream`; `ws_client.js` has been removed.
- Controller modernization documentation has been consolidated: active guidance now lives in `docs/dev-notes/controller_foundations.md` and `docs/dev-notes/controllers_js_jquery_retro.md`.
- Historical controller plans reside under `docs/work-packages/20251023_controller_modernization/notes/archived-plans/` for reference.

## Completed Work
- Updated `controllers_js_jquery_retro.md` to serve as the modernization retrospective instead of an in-flight roadmap.
- Refreshed `controller_foundations.md`, `controllers_js/README.md`, and `controllers_js/AGENTS.md` to declare StatusStream as the sole telemetry surface and remove WSClient guidance.
- Archived every controller migration/plan document into `notes/archived-plans/` and removed the `docs/dev-notes/*controller-plan.md` stubs.
- Updated prompts/workflows (`god-tier-prompting-strategy.md`, module refactor workflow, helper prompts) to point at the retrospective and archived plan locations.

## Deliverables
- Authoritative helper-first documentation in `controller_foundations.md` and `controllers_js_jquery_retro.md`.
- Archived per-controller plans grouped within this work package.
- Up-to-date controller playbooks (`controllers_js/README.md`, `controllers_js/AGENTS.md`) that reference the new docs.

## Acceptance Criteria
All criteria are satisfied: controllers rely on StatusStream-only telemetry, helper docs are authoritative, and legacy plans are archived.

## Follow-ups
- None. Treat archived plans as historical references; create a new work package if the architecture evolves again.
