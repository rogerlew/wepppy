# Controller Modernization Documentation Backlog
> Created 2025-02-14 to consolidate retroactive documentation clean-up after the controller modernization (WSClient removal, helper-first controllers).

## Context
- All controllers now rely on `controlBase.attach_status_stream` + `StatusStream`; `ws_client.js` has been removed.
- The modernization happened incrementally, leaving behind domain-specific plans and progress trackers scattered under `docs/dev-notes/` (for example `*_controller-plan.md`, `controllers_js_jquery_retro.md`).
- Several notes still describe jQuery-era behaviour (historical snapshots now live in `controllers_js_jquery_retro.md`) and should be clearly marked archival so future agents do not follow obsolete guidance.

## Scope
This work package covers documentation that needs to be updated, merged, or retired now that the refactor is complete. Source files primarily live under `docs/dev-notes/` and `docs/prompts/`.

### High-Priority Updates
- `docs/dev-notes/controllers_js_jquery_retro.md`
  - Rewrite the snapshot/footprint sections to reflect completed migration.
  - Convert into a lessons-learned or archive doc, or move historical tables to an appendix.
- `docs/dev-notes/controller_foundations.md`
  - Add explicit note that StatusStream is the sole telemetry surface and that WSClient no longer exists.
  - Link to updated helper docs (dom/forms/http) for current APIs.
- `docs/wepppy/weppcloud/controllers_js/README.md` & `controllers_js/AGENTS.md`
  - Verify telemetry sections mention StatusStream adapter, remove residual references to “legacy jQuery controllers”.

### Per-Controller Plans
For each controller plan archived under `docs/work-packages/20251023_controller_modernization/notes/archived-plans/`:
- Mark migration status (completed date, helper adoption, remaining risks).
- Decide whether to keep the standalone file or collapse details into a single “Controller Modernization Retrospective”.
- Ensure domain-specific payload/event definitions match the final implementation.

### Prompt & Process Docs
- Review prompts under `docs/prompts/` (e.g., `wsclient_statusstream_migration.md`) and align guidance with the final architecture.
- Update `docs/dev-notes/module_refactor_workflow.md` if steps still reference WSClient or jQuery clean-up.

## Deliverables
- Updated/archived markdown files reflecting the finished modernization.
- Optional umbrella retrospective summarizing migration outcomes and linking to consolidated docs.
- Checklist of retired documents (if moved to archive) recorded in repo changelog or release notes.

## Acceptance Criteria
- No documentation instructs agents to use jQuery or WSClient in controllers.
- Helpers (`dom.js`, `forms.js`, `http.js`, `control_base.js`, `status_stream.js`) have authoritative docs referenced from controller playbooks.
- Historical plans are either clearly marked as archived or merged into a single maintained guide.

## Open Questions
- Do we preserve detailed per-controller timelines, or collapse them into a single modernization narrative?
- Should we introduce an automated doc index for `docs/dev-notes/` to highlight active vs. archived guides?

## Suggested Workflow
1. Run `rg 'WSClient' docs` and `rg '\$\(' docs` to locate stale references.
2. Update high-priority docs first, then sweep controller-specific plans.
3. File follow-up prompts for any domain needing fresh guidance (e.g., new telemetry features).

Record progress in this work package file as tasks complete (use checkboxes or dated notes).
