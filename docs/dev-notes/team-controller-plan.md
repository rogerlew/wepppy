# Team Controller Plan
> Helper-first contract recap for project collaborator management. See also: [docs/dev-notes/controller_foundations.md](controller_foundations.md) for the shared modernization vision.

## Overview
- Coordinates the Team run-control (`wepppy/weppcloud/controllers_js/team.js`), collaborator templates (`wepppy/weppcloud/templates/controls/team*.htm` and `templates/reports/users.htm`), and project blueprint endpoints (`project_bp.task_adduser`, `project_bp.task_removeuser`).
- Replaces jQuery-era wiring with `WCDom`, `WCForms`, `WCHttp`, `WCEvents`, and `controlBase`, keeping StatusStream/WSClient telemetry intact.
- Maintains legacy public methods (`Team.adduser`, `Team.removeuser`, `Team.report`) and DOM events (`TEAM_ADDUSER_TASK_COMPLETED`, `TEAM_REMOVEUSER_TASK_COMPLETED`) while emitting scoped helper events for downstream dashboards.

## DOM Contract
- Form wrapper: `#team_form` retains status (`#status`), stack trace (`#stacktrace`), info (`#info`), and hint (`#hint_run_team`) nodes so `controlBase` and StatusStream work automatically.
- Invite input: `#adduser-email` now carries `data-team-field="email"` with semantic `type="email"`, `autocomplete="email"`, and `disable-readonly` guard.
- Buttons expose delegated hooks via `data-team-action`:
  - `data-team-action="invite"` on `#btn_adduser` to trigger invites.
  - `data-team-action="remove"` with `data-team-user-id="<id>` on each collaborator row (rendered inside `#team-info`).
- Removal controls adopt `disable-readonly` so readonly projects hide destructive affordances without controller logic.

## Event Surface
- The controller registers `team.events = WCEvents.useEventMap([...])`, emitting:
  - Lifecycle: `team:list:loading`, `team:list:loaded`, `team:list:failed`.
  - Invite flow: `team:invite:started`, `team:invite:sent`, `team:invite:failed`.
  - Removal flow: `team:member:remove:started`, `team:member:removed`, `team:member:remove:failed`.
  - Telemetry bridge: `team:status:updated` (mirrors StatusStream/WS updates).
- Legacy DOM events (`TEAM_ADDUSER_TASK_COMPLETED`, `TEAM_REMOVEUSER_TASK_COMPLETED`, plus `job:*`) continue to dispatch through `controlBase.triggerEvent` to keep historical listeners functional.

## Payload Schemas
- **Invite collaborator** (`POST tasks/adduser/`)
  - Request JSON: `{ "email": "user@example.com" }` (legacy `adduser-email` form field still accepted).
  - Response success: `{ Success: true, Content: { user_id: <int>, email: <str> } }`.
  - Duplicate membership surfaces as `{ Success: true, Content: { already_member: true, user_id, email } }`.
  - Failures use `{ Success: false, Error: "…" }` with standardized copy (missing email, unknown account, unexpected errors).
- **Remove collaborator** (`POST tasks/removeuser/`)
  - Request JSON: `{ "user_id": <int> }` (legacy form payload accepted).
  - Response success: `{ Success: true, Content: { user_id: <int> } }`.
  - Already-removed case: `{ Success: true, Content: { already_removed: true, user_id: <int> } }`.
  - Validation errors include `user_id is required.`, `user_id must be an integer.`, `User … not found.`, `User is not a collaborator on this project.`
- Routes normalise inputs via `parse_request_payload`, rely on `user_datastore.find_user`, and keep add/remove operations idempotent.

## Telemetry & Helpers
- `controlBase` integration keeps queue-friendly behaviour (status appenders, stacktrace helpers, `job:*` events).
- Status panels prefer `StatusStream.attach` when available; otherwise the WS fallback reconnects via `WSClient` as before.
- Buttons respect `data-jobDisabled` flags written by `controlBase` so queue polling can continue to disable inputs when necessary.

## Testing & Tooling
- **Jest**: `wepppy/weppcloud/controllers_js/__tests__/team.test.js` covers initial hydration, invite/remove flows, event emission, and error handling. Run via `wctl run-npm test -- team` (full test suite also valid).
- **Pytest**: `tests/weppcloud/routes/test_team_bp.py` exercises the refreshed blueprint contract using stubbed `user_datastore`/query models. Execute with `wctl run-pytest tests/weppcloud/routes/test_team_bp.py`.
- Bundle rebuild: `python wepppy/weppcloud/controllers_js/build_controllers_js.py`.

## Follow-Ups
- Consider surfacing live roster details (owners vs collaborators) through a JSON endpoint to avoid HTML scraping when downstream services need structured data.
- Evaluate consolidating invite success messaging with centralized notification helpers (`controlBase.setStatus`) once other controllers adopt the pattern.
- Audit other routes still calling `user_datastore.create_run` directly to ensure duplicate membership cases remain idempotent.
