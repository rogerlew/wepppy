# Features Export UI Subagent Roles

Purpose: define reusable subagent roles for planning and implementing the `features_export` Runs-page control using established WEPPcloud patterns.

## Shared Standards (Required)
- `docs/ui-docs/controller-contract.md`
- `wepppy/weppcloud/controllers_js/AGENTS.md`
- `docs/ui-docs/control-ui-styling/control-components.md`
- `docs/ui-docs/control-ui-styling/control-inventory.md`
- `docs/ui-docs/gl-dashboard.md`
- `wepppy/weppcloud/static/js/gl-dashboard/AGENTS.md`
- `docs/standards/nodb-facade-collaborator-pattern.md`

## Role: `features_export_ui_designer`
Use for:
- control information architecture
- field grouping and progressive disclosure
- discoverability strategy for layers/scopes/temporal selectors
- wireframes (desktop + mobile)

Must deliver:
1. control layout narrative
2. ASCII wireframes with labeled regions
3. control-state matrix (idle/running/success/error/partial)
4. accessibility notes (`aria-live`, keyboard, error focus order)

Design constraints:
- keep parity with existing Runs-page visual language and macro patterns
- avoid novel widget frameworks
- ensure status/stacktrace/job-hint surfaces are explicit

## Role: `features_export_ui_developer`
Use for:
- concrete DOM contract (`data-*` hooks)
- controller lifecycle/event wiring
- payload serialization and validation UX behavior
- integration notes for NoDb async patterns

Must deliver:
1. template structure contract (form + panels + hint areas)
2. `data-*` hook map
3. controller event contract (`job:*` + domain events)
4. endpoint interaction contract and error rendering behavior
5. test checklist (Jest + Playwright smoke + targeted pytest)

Implementation constraints:
- singleton bootstrap pattern, idempotent re-hydration
- `controlBase.attach_status_stream` and `set_rq_job_id` fallback polling
- `WCHttp` + `url_for_run` for run-scoped requests
- no inline handlers, delegate events only

## Spawn Prompt Template
```text
Act as <features_export_ui_designer|features_export_ui_developer>.
Use the required standards listed in:
wepppy/nodb/mods/features_export/SUBAGENT_ROLES.md

Task:
- Produce a detailed UI specification for the Features Export control.
- Include desktop/mobile ASCII wireframes.
- Use existing WEPPcloud Runs-page controller patterns and status-stream conventions.
- Do not implement code; deliver a spec artifact only.
```

