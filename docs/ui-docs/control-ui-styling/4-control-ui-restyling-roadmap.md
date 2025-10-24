# Control UI Restyling Roadmap

## Purpose
This note captures the current state of controller views and the `runs0` experience, documents the key constraints (ControlBase contracts, NoDb patterns, special-case controllers), and outlines a plan to standardize styling with a Pure CSS friendly design system. It also lays out the complementary backend expectations (NoDb singletons, RQ workers, locale inheritance) that the front-end must partner with.

## Existing Architecture Snapshot

### Controller Rendering Pipeline (Current Status)
- Controller-specific HTML now lives in `wepppy/weppcloud/templates/controls/*_pure.htm`, each using the `control_shell` macro to render status/summary/stacktrace slots. `_base.htm` is archived for legacy reference.【F:docs/work-packages/20251023_frontend_integration/notes/final-implementation-blueprint.md】
- The `runs0` layout (`routes/run_0/templates/runs0_pure.htm`) composes the pure control partials, injects `controllers.js`, and delegates layout to `ui-foundation.css` tokens (`wc-page`, `.pure-g`). Legacy `0.htm` remains in the repo but is no longer part of the production flow.【F:wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm†L1-L120】
- JavaScript controllers remain singletons bundled into `controllers.js`. `control_base.js` coordinates job polling, status/summary writers, stacktrace rendering, and StatusStream attachments across controls.【F:wepppy/weppcloud/controllers_js/control_base.js†L5-L199】

### Common Patterns
- Standard controllers render static forms whose layout rarely changes. Some expose hidden sections (advanced toggles, mode-specific content) but still rely on server-rendered markup.
- Several controllers push live summaries back into the shared `<div id="info">` slot, meaning the markup contract in `_base.htm` must remain stable for ControlBase helpers to function.
- Validation philosophy: front-end checks improve UX, but NoDb singletons remain the authority for type/constraint enforcement once payloads reach the server.

### Known Outliers
- **File uploads**: controllers such as BAER and road uploads must maintain `enctype="multipart/form-data"` and guard against malicious payloads early in the request lifecycle.
- **Omni**: mixes static markup with a JavaScript-driven scenario builder. It requires hooks for dynamic row creation and server round-trips to stay in sync.
- **BatchRunner**: resembles a standalone page rather than a small form, so the base template contract needs to support full-width layouts without forcing extraneous chrome.
- **Unit-aware fields**: some controls already integrate `unitizer_modal.htm` and watch for unit conversions triggered elsewhere on the page.【F:wepppy/weppcloud/routes/run_0/templates/0.htm†L184-L193】

## Pain Points to Address
1. **Inline styling and Bootstrap carry-over**: `runs0` injects page-defining CSS directly inside the template, making Pure CSS migration cumbersome and encouraging per-template overrides.【F:wepppy/weppcloud/routes/run_0/templates/0.htm†L38-L118】
2. **Duplicate markup fragments**: the base template mixes structure with styling (e.g., `.col-md-11`, inline margins). Reusing controllers outside the current grid requires manual HTML edits.【F:wepppy/weppcloud/templates/controls/_base.htm†L1-L19】
3. **Event handling inconsistency**: some controllers post on change, others only on submit. Without a shared contract, we accumulate bespoke Flask routes and increase drift between UI state and NoDb state.
4. **Locale assumptions**: configuration options and units are implicitly US-centric; tacked-on overrides lack inheritance and reuse, making new locales error prone.

## Design Goals for the Pure CSS Pass
- **Separation of concerns**: migrate layout primitives (stacking, spacing, typography) into Pure CSS modules (e.g., `.control-card`, `.control-card__header`, `.control-summary`) so controller templates focus on fields.
- **Composable building blocks**: define partials for repeating structures (file upload row, advanced options disclosure, summary list) to avoid copy/paste and keep CSS selectors stable.
- **Progressive enhancement**: ensure base forms remain functional without JavaScript, then layer ControlBase-driven enhancements (job polling, WebSocket streams) via data attributes or unobtrusive bindings.
- **Responsiveness by default**: adopt Pure CSS grids for both the overall runs0 layout and individual forms, eliminating ad-hoc `col-md-*` Bootstrap classes.

## Proposed Controller View Style Guide
1. **Base wrapper**
   - Replace `.controller-section` with `.control-card` defined in a Pure CSS stylesheet. The wrapper manages spacing, border, and background consistently across controls.
   - Keep the semantic structure: heading, inputs, job status, summary, stacktrace. Expose optional slots via `{% block summary %}` or `{% block footer %}` overrides.
2. **Typography and spacing**
   - Centralize spacing tokens (`--space-sm`, `--space-md`) and apply them through utility classes. Avoid inline `style` attributes.
   - Use `<fieldset>` and `<legend>` for grouped inputs so screen readers and keyboard users benefit from the structure.
3. **Status + summary module**
   - Implement a reusable partial (e.g., `_control_status.htm`) that renders the status/pre sections. Controllers that do not need summaries can opt out by passing a flag.
   - Style the summary block with Pure CSS cards, leaving `#info` available for ControlBase to inject markup.
4. **Advanced options**
   - Use `<details>` / `<summary>` or a Pure CSS accordion module. Provide JS hooks to auto-open on validation errors or server-provided context.
5. **File uploads**
   - Introduce a `control-file-input` component that pairs file inputs with asynchronous progress bars. Hook into ControlBase to disable submit buttons until uploads finish.
6. **Unit-aware inputs**
   - Standardize on a `data-unit-key` attribute. A shared `UnitSynchronizer` module can watch `unitizer_modal` events and format values accordingly.
7. **Mode switches**
   - Prefer CSS class toggles driven by data attributes (`data-mode="basic"`) with htmx snippets for server-rendered fragments when options differ dramatically.

## Interaction and Routing Strategy
- **Event contract**
  - Controllers emit `change` events to keep UI state synchronized, but actual persistence happens on explicit actions (`Run`, `Save`, `Preview`). This avoids a proliferation of micro-routes while keeping the UI responsive.
  - Adopt htmx `hx-post`/`hx-swap` for targeted updates (e.g., recalculating summary blocks) without requiring bespoke fetch logic in every controller.
- **Route consolidation**
  - Group controller endpoints by NoDb class (e.g., `/controls/climate/{action}`) and dispatch using reflection. Each controller shares a `control_action(action_name, payload)` on the NoDb singleton that validates inputs and returns structured responses.
  - Maintain a single validation surface: the NoDb method performs schema enforcement (potentially via `pydantic`-style dataclasses) and returns serialized errors for the UI.
- **WebSocket alignment**
  - Standardize on `controlBase.attach_status_stream` with `data-ws-channel` (or explicit args) so controllers opt in without manual wiring. The helper fabricates hidden panels when Pure markup is missing, eliminating the need for the legacy `WSClient` shim.

## Backend Expectations
1. **NoDb singletons**
   - Guarantee every control action maps to a method on the run-scoped singleton. Use decorators to declare command metadata (idempotent, requires lock) for consistent logging.
   - Responses should include `status`, `summary_html`, `stacktrace`, and optional `htmx` fragments so the UI renderer can compose updates without custom JS.
2. **RQ workers**
   - Standardize payload schemas. Workers emit structured status messages (JSON blocks with `summary`/`progress`) so ControlBase can render them without controller-specific parsing.
   - Ensure file operations and long-running tasks publish both start/end events to keep the UI job indicator accurate.
3. **Unit services**
   - Provide a centralized unit conversion service accessible via NoDb. Controls pass `unit_key` and numeric values; backend responds with canonical units and formatting hints.

## Locale Strategy
- **Run-scoped locale selection**
  - Persist a `locale_code` on each run; controllers read it from the run manifest and pass it with every request.
- **Inheritance hierarchy**
  - Model locales as classes (e.g., `USLocale`, `IdahoLocale(USLocale)`) where subclasses override metadata such as climate options, landuse codes, default units.
  - Serialize locale descriptors (`display_name`, `climate_modes`, `landuse_catalog`, `unit_overrides`) for client use. Provide a `resolve_locale(locale_code)` helper in NoDb to surface a merged configuration.
- **Content hooks**
  - Jinja templates pull locale-aware strings through a shared context processor so controllers automatically adopt local terminology (e.g., rainfall vs precipitation).
  - JS controllers receive locale data via `data-locale` attributes to drive drop-downs and validations without hardcoding US defaults.

## htmx Adoption Opportunities
- Replace bespoke AJAX calls with `hx-post` for simple form submissions, letting the server return partial HTML fragments (`hx-target="#info"`) alongside JSON payloads for ControlBase.
- Use `hx-trigger="change delay:500ms"` on numeric inputs that need debounced recomputation (e.g., dynamic summaries) without manual timers.
- Implement cascading selects (e.g., locale -> climate mode) via `hx-get` requests that fetch localized option lists.

## Implementation Roadmap
1. **Inventory + Audit**
   - Catalogue each controller template, noting input types, file uploads, dynamic behaviors, and backend routes. Capture this in a shared spreadsheet to prioritize work.
2. **Design system scaffolding**
   - Create `static/css/controls.css` with Pure CSS modules (`control-card`, layout tokens). Refactor `_base.htm` to import the stylesheet and expose semantic blocks.
3. **Runs0 shell refactor**
   - Move inline CSS from `0.htm` into `controls.css`; rework layout using Pure CSS grid classes. Ensure the TOC and content area remain accessible on mobile.
4. **Controller migration**
   - Tackle controllers in batches: start with simple static forms, then advanced-option panels, then file upload flows. Each migration replaces Bootstrap classes with Pure CSS utilities and adopts the shared partials.
5. **Interaction cleanup**
   - Introduce a shared `control-actions.js` (or htmx attributes) that handles change vs submit semantics. Remove redundant routes as NoDb reflection dispatcher comes online.
6. **Locale framework**
   - Implement locale classes with inheritance, update run creation to accept a locale, and surface locale data to templates/controllers. Migrate existing US-only logic into the US base class.
7. **Documentation + examples**
   - Provide sample controller implementations (static form, file upload, htmx-powered partial) in the docs to guide future development.

## Risks and Mitigations
- **Legacy behavior drift**: Validate each controller after refactor by comparing before/after HTML snapshots and running integration flows in staging.
- **Performance regressions**: Monitor bundle size when adopting htmx. Load it conditionally or from a shared vendor bundle to avoid penalizing non-runs0 pages.
- **Accessibility gaps**: Include keyboard navigation and ARIA reviews in the acceptance criteria for each controller migration.

## Next Steps
- Socialize this roadmap with the core maintainers to confirm priorities.
- Prototype the Pure CSS `control-card` on a low-risk controller (e.g., `export`) to vet spacing and htmx patterns.
- Draft locale class skeletons and run manifest schema updates so backend changes can land in parallel with UI refactors.
