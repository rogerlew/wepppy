# SHR-07 Security Review

**Date**: 2026-07-29
**Disposition**: Pass; no unresolved high or medium findings.

## Scope

Reviewed privileged panel rendering, clear-lock recovery, recorder promotion,
run-token mint/copy, optional web-push initialization, CSRF handling, run
authorization, and the Command Bar consumer of the clear-lock route.

## Findings and Resolution

1. **High - ordinary viewers received privileged panel markup and clients.**
   Resolved by independently gating the launcher and panel to PowerUser, Admin,
   or Root. Actual Jinja renders prove ordinary-user exclusion.
2. **High - clear-lock was a destructive authenticated GET without a privileged
   role boundary.** Resolved by requiring POST plus accepted
   PowerUser/Admin/Root roles and
   retaining canonical run authorization. Project and Command Bar consumers now
   use same-origin CSRF-protected POST.
3. **Medium - absent notification UI still requested permission and initialized
   service-worker/subscription state.** Resolved by returning before
   initialization when the toggle pair is absent. Direct jsdom execution proves
   zero permission, registration, or network calls.
4. **Medium - repeated token script execution could bind duplicate action
   owners.** Resolved with a root-scoped initialization marker. Direct execution
   proves one POST with repeated script evaluation.
5. **Medium - recorder promotion rendering required Admin while the backend
   requires PowerUser.** Resolved by matching the rendered control to the
   established backend PowerUser role without broadening route authority.

## Retained Controls

- Server-owned run/config URLs and canonical authorization remain in place.
- Token mint remains Admin/Root-only, same-origin, CSRF-protected, 24-hour
  service-token behavior; no client persistence was added.
- External links retain `rel="noopener"`.
- Existing clear-lock implementation and recorder payload semantics are
  unchanged.

## Evidence

- `tests/weppcloud/routes/test_pure_controls_render.py`
- `tests/weppcloud/routes/test_project_bp.py`
- `wepppy/weppcloud/controllers_js/__tests__/project.test.js`
- `wepppy/weppcloud/controllers_js/__tests__/poweruser_panel_inline.test.js`
- Full frontend lint/test, focused backend tests, full Python suite, RQ graph,
  docs lint, and diff hygiene recorded in the tracker and ExecPlan.
