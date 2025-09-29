# Control Base + WebSocket Client Merge

## Rationale
- **Single source of truth for run-state plumbing**: `control_base.js` and `ws_client.js` both track job IDs, disable buttons, and surface stack traces. Merging them eliminates divergent state machines and reduces the chances of UI regressions when adding new telemetry.
- **Path off jQuery**: A unified module makes it easier to move controllers to vanilla JavaScript. We can expose a small DOM helper layer while keeping the same API surface for existing controllers during the transition.
- **Composable controls**: Controllers should hydrate server-rendered templates (Jinja macros + locale-driven dataclasses) without re-implementing status wiring. A merged base can accept hooks (`onStatus`, `onTrigger`, `onException`) so each controller focuses on its own behaviour.
- **Consistent transport strategy**: RQ polling and WebSocket updates presently compete. Centralising the logic lets us fall back to polling when sockets are unavailable, and push common reconnect/backoff logic into one place.

## Implementation Plan
1. **Author a vanilla `ControlBase` module**
   - Export a class that takes DOM selectors, an optional Redis channel, and an options hash (element IDs, stacktrace panel, command button IDs).
   - Replace jQuery calls with lightweight helpers (`qs`, `qsa`, `on`) so controllers can migrate incrementally.
   - Keep legacy method names (`set_rq_job_id`, `render_job_status`, `manage_ws_client`) but internally call new primitives.

2. **Fold WebSocket handling into the base**
   - Introduce a `StatusStream` helper object inside `ControlBase` that wraps `WebSocket` creation, ping/pong, reconnects, and message parsing.
   - Route incoming messages through hook methods (`handleStatusFrame`, `handleCommandResult`, `handleTrigger`). Default hooks update the status element and spinner; controllers can override as needed.
   - Ensure the helper tears down cleanly on `disconnect()` or when a controller resets its job ID.

3. **Harmonise RQ polling and telemetry**
   - Refactor the existing polling timer (`fetch_job_status`, `stop_job_status_polling`) to live alongside the WebSocket helper. The base decides when to poll (e.g., when no channel is provided or after repeated socket failures).
   - Normalise job status payloads so controllers see a predictable structure, regardless of whether updates originated from the REST endpoint or the WebSocket stream.

4. **Incrementally migrate controllers**
   - Pick one controller (suggested: `Map` or `Landuse`) to adopt the new base. Verify that command button disablement, stack traces, and spinner updates behave identically.
   - Update `run_page_bootstrap.js.j2` to work with the merged base—ideally controllers call a single `initControlBase()` method instead of juggling both files.
   - Once verified, remove the legacy `ws_client.js` file and update the controller bundle build (`build_controllers_js.py`) to exclude it.

5. **Testing & rollout**
   - Manual smoke test: trigger RQ jobs, confirm status streaming, failure handling, and button state resets for converted controllers.
   - Add unit tests (or a lightweight harness) for the new `ControlBase` class that simulate job status updates, WebSocket events, and disconnect/reconnect cycles.
   - Coordinate the rollout with the ongoing UI event binding refactor, ensuring the merged base aligns with the vanilla JS direction described in `ui-event-refactor.md`.

## Follow-up Tasks
- Define locale-aware dataclasses that generate control metadata and feed it into the templates consumed by controllers.
- Document the new controller API contracts so future contributors understand how to plug into the merged base.
- Audit remaining jQuery dependencies and plan removals once the merged module is stable.
