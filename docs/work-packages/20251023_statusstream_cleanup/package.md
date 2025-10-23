# StatusStream Telemetry Cleanup

**Status**: Closed 2025-10-23

## Overview
- Replace the legacy `WSClient` shim with the unified `controlBase.attach_status_stream` helper.
- Ensure every controller relies on StatusStream for telemetry (spinner, stacktrace, trigger events).
- Update documentation and architectural notes to describe the new flow.

## Scope
- Delete `wepppy/weppcloud/controllers_js/ws_client.js` and any infrastructure references.
- Refresh controller tests and stubs to drop `manage_ws_client` expectations.
- Migrate docs/prompts into the work-package structure for future reference.

## Out of scope
- Further refactoring of individual controllers beyond telemetry wiring.
- Additional UI modernization unrelated to StatusStream.

## Stakeholders
- Front-end controllers team (primary)
- Docs maintainers (for AGENTS / architecture updates)

## Deliverables
- Unified telemetry pipeline with no `WSClient` references in code or docs.
- Archived prompts and notes captured under this package.
- Documentation pointing to the work-package model for future efforts.

## References
- `wepppy/weppcloud/controllers_js/control_base.js`
- `wepppy/weppcloud/controllers_js/status_stream.js`
- Root doc updates (`readme.md`, `ARCHITECTURE.md`, `AGENTS.md`)

## Follow-ups
- Monitor new packages to ensure they adopt the work-package structure.
- Consider migrating other long-running efforts (e.g., NoDb docs refresh) into work packages.
