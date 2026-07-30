# SHR-06 Security Review

**Date**: 2026-07-29
**Disposition**: Pass; no unresolved high or medium findings.

## Scope

Reviewed actual Command Bar hosts, keyboard and command ownership, safe and
mutating requests, lock/cache/log-level recovery, Query Engine MCP token
issuance and filesystem instructions, Wojak session lifecycle, StatusStream
teardown, and remote Markdown rendering.

## Findings and Resolution

1. **High - destructive recovery used authorized GET without privileged role.**
   Runtime-directory lock and NoDb-cache clearing are now POST-only,
   PowerUser/Admin/Root operations. Their raw clients attach CSRF and
   same-origin credentials.
2. **High - anonymous public-run viewers could mint an MCP bearer token.**
   Issuance now fails closed unless the exact-run-authorized caller is
   authenticated. Existing run claim, query scopes, audience, MCP token class,
   default TTL, response-only token, and redacted instructions remain intact.
3. **High - agent Markdown retained unsafe URL schemes.** Sanitization now
   permits only HTTP/HTTPS and link-only mailto URLs after URL parsing, while
   continuing to remove active elements and event attributes. Direct hostile
   execution proves `javascript:` and event handlers do not survive.
4. **Medium - raw cookie-authenticated Command Bar mutations omitted CSRF.**
   MCP mint, log-level, migration, Wojak start/send/terminate, and all recovery
   requests now attach the rendered CSRF token and same-origin credentials.
5. **Medium - log-level mutation lacked an explicit operator role boundary.**
   The route now requires an authenticated PowerUser, Admin, or Root after exact
   run authorization.

## Retained Controls

- Safe diagnostic and navigation commands remain available in their existing
  hosts and do not gain mutation authority.
- MCP instructions never persist the bearer token.
- Agent routes retain `login_required` and canonical exact-run authorization.
- Session identifiers are URL-encoded; StatusStream disconnects on termination
  and teardown.
- Repeated initialization reuses the existing Command Bar instance.

## Evidence

- `wepppy/weppcloud/controllers_js/__tests__/command_bar.test.js`
- `tests/weppcloud/routes/test_command_bar_mcp_token.py`
- `tests/weppcloud/routes/test_project_bp.py`
- `tests/weppcloud/routes/test_pure_controls_render.py`
- `tests/weppcloud/controllers_js/test_status_stream_js.py`
- Full frontend lint/test, full Python suite, RQ graph, docs lint, broad
  exception enforcement, and diff hygiene recorded in the tracker and
  ExecPlan.
