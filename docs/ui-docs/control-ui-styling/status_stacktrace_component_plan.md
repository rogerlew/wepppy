# Status & Stacktrace Component Plan

## Objectives
- Establish reusable status and stacktrace components that align with the Pure-based control system while supporting console-style pages (rq-fork-console, rq-archive-dashboard) that demand taller, streaming views.
- Replace duplicated JavaScript (custom WebSocket clients, log appenders, stacktrace fetchers) with a shared module usable by both run controls and console dashboards.
- Define interface contracts so templates, macros, and controllers share a predictable API (HTML structure, CSS classes, data attributes, JS hooks).

## Current State Findings
- **Templates**: `rq-fork-console.htm` and `rq-archive-dashboard.htm` hand-roll status `<div>`s and stacktrace `<details>` with slightly different DOM ids and ad-hoc spacing classes.
- **CSS**: `ui-foundation.css` includes `.wc-status`, `.wc-log`, and `.wc-panel` styles but no variant for tall, fixed-height streaming panes.
- **JavaScript**: Legacy pages once defined their own `WSClient` clones, `appendStatus` queues, and stacktrace logic (including polling `/rq/api/jobinfo/<id>`). The migration standardizes this on `StatusStream.attach` via `controlBase.attach_status_stream`, and the old wrapper has been removed.
- **Accessibility**: Live regions vary (`aria-live="polite"` vs none) and stacktrace toggles rely on manually toggled `hidden`.

## Component Strategy
### Status Panel
- **Macro**: Introduce `status_panel` in `_pure_macros.html` that renders:
  - Wrapper `<section class="wc-status-panel">` with optional heading slot.
  - Inner log area `<div class="wc-status-log">` with `role="log"` and `aria-live="polite"`.
  - Optional footer slot for actions (download log, copy).
- **Variants**: Accept `variant="compact|console"` to control height. Use CSS custom properties (`--wc-status-height`) so console pages request taller fixed panes (e.g., 16rem vs 8rem).
- **Data Hooks**: Macro emits `data-status-panel` + `data-status-target="<id>"` for JS registration.

### Stacktrace Panel
- **Macro**: `stacktrace_panel` renders an accessible disclosure:
  - `<details class="wc-stacktrace" data-stacktrace-panel>` with summary text configurable via args.
  - `<pre class="wc-stacktrace__body" data-stacktrace-body>` that JS fills.
  - Optional “Open in new tab” action slot.
- **Behavior**: Hidden by default; JS toggles `open` and populates text when payload arrives.

### Shared JavaScript Module
- **File**: `controllers_js/status_stream.js`.
- **Exports**:
  - `StatusStream.attach({ root, channel, runId, variant, stacktraceFetcher })`.
  - Internally handles WebSocket lifecycle, ping/pong, reconnection backoff, message queue with trim limit, auto-scroll, and optional stacktrace fetching.
  - Emits custom events (`status:append`, `status:error`, `status:trigger`) to allow page-specific hooks (e.g., fork completion).
  - Accepts `formatter` callback so existing ControlBase log formatting can plug in without branching.
- **Stacktrace Fetcher**: Default implementation mirrors fork console behavior (strip job id, request `/rq/api/jobinfo/<id>`).

### CSS Adjustments
- Add `.wc-status-panel` and `.wc-stacktrace` blocks to `ui-foundation.css` with Pure tokens:
  - `display: flex` column layout, header/footer spacing.
  - `--wc-status-height` variable (default 10rem). Console variant sets `--wc-status-height: 20rem;`.
  - `.wc-status-log` uses `overflow-y: auto`, preserves monospace log text, and maintains padding.
  - `.wc-stacktrace__body` inherits monospace font, uses `overflow-x: auto`.

## Implementation Plan
1. **Author Macros & Tokens**
   - Add `status_panel` and `stacktrace_panel` to `_pure_macros.html`.
   - Update `ui-foundation.css` with new classes and height tokens.
   - Extend `/ui/components/` gallery to demonstrate both variants (compact vs console) and stacktrace usage without duplicating JS (use shared module once implemented).
2. **Create JS Module**
   - Build `status_stream.js` with WebSocket handling, message queue, and stacktrace support.
   - Refactor `Project`/ControlBase to optionally delegate to the module (while keeping existing behavior until migration completes).
3. **Migrate Console Pages**
   - Replace manual markup in `rq-fork-console` and `rq-archive-dashboard` with new macros.
   - Swap inline legacy WSClient/appendStatus code for the shared `StatusStream` module (via `controlBase.attach_status_stream` in run controls or direct `StatusStream.attach` elsewhere).
   - Use module callbacks to trigger page-specific actions (fork completion, archive refresh) while letting the helper drop in hidden placeholders when the legacy markup lacks panels.
4. **Integrate with ControlBase**
   - Update control macros to optionally render the new status/stacktrace components in `_pure_base.htm`.
   - Refactor ControlBase JS to register status panels using the shared module, ensuring existing run0 controls benefit from consistent behavior.
5. **Testing & Accessibility**
   - Verify live region announcements, keyboard access (focus trapping not required), and scroll behavior across browsers.
   - Add unit coverage for `status_stream.js` (simulate message bursts, reconnection).
6. **Documentation**
   - Update `control-components.md` with the new macros.
   - Record JS usage patterns in `controllers_js/README.md`.
   - Capture migration notes in `control-inventory.md` for the console panels.

## Component Interface Contracts
### Status Panel Contract
- **Template API**:
  - `{{ ui.status_panel(id="fork_status", title="Console", variant="console") }}`
  - Optional blocks: `actions`, `footer`.
  - Macro outputs `data-status-panel` and `data-status-log`.
- **JS API** (`status_stream.js`):
  - `StatusStream.attach({ element, channel, runId, logLimit, onTrigger, stacktrace })`.
  - Emits `CustomEvent("status:trigger", { detail })` for TRIGGER lines.
  - Provides `StatusStream.append(id, message)` for manual pushes (e.g., immediate POST feedback before WS connects).
- **CSS API**:
  - `.wc-status-panel[data-variant="console"]` sets `--wc-status-height` override.
  - `.wc-status-log` expects `white-space: pre-wrap` and autop scroll.

### Stacktrace Panel Contract
- **Template API**:
  - `{{ ui.stacktrace_panel(id="fork_stacktrace", summary="Stack trace", collapsed=True) }}`
  - Macro exposes `data-stacktrace-panel` and `data-stacktrace-body`.
- **JS API**:
  - `StatusStream.attach` receives `stacktrace: { element, fetchJobInfo }`.
  - When status line includes `EXCEPTION`, module expands details and injects text (optionally enriched by `fetchJobInfo`).

## Next Steps
1. Align with stakeholders on the proposed macro signatures and JS module shape.
2. Spike `status_stream.js` in isolation with unit tests (write to `tests/weppcloud/controllers_js/`).
3. Implement Phase 1–3, keeping legacy markup available behind feature flags until console pages validate the new flow.
4. Roll the change into `_pure_base.htm` once console adoption stabilizes, ensuring run controls share the same components.

## Implementation Status
- **Phase 1–3 complete:** `status_panel`/`stacktrace_panel` macros ship with showcase examples, `status_stream.js` handles shared WebSocket plumbing, and both fork/archive consoles now consume the new components.
- **Testing added:** Node-based regression test (`status_stream_test.js`) exercises buffering, trigger dispatch, stacktrace enrichment, and reconnection behaviour.
- **Documentation synced:** `control-components.md`, `controllers_js/README.md`, and the styling AGENT guide reference the new macros and streaming module.
- **Outstanding migration:** `_pure_base.htm` and ControlBase still depend on legacy IDs; schedule a separate pass to align run controls once telemetry shakes out on the console pages.
