# Control UI Final Implementation Blueprint

## Purpose
This blueprint fuses the prior controller UI strategy drafts into a single implementation guide. It captures the current state of controller views and the `runs0` experience, documents the key constraints (ControlBase contracts, NoDb patterns, special-case controllers), and outlines a plan to standardize styling with a Pure CSS friendly design system. It also lays out the complementary backend expectations (NoDb singletons, RQ workers, locale inheritance) that the front-end must partner with.

## Existing Architecture Snapshot

### Controller Rendering Pipeline
- Controller-specific HTML lives in `wepppy/weppcloud/templates/controls/`, all extending `_base.htm` which defines the canonical status/summary/stacktrace blocks expected by the JS layer.【F:wepppy/weppcloud/templates/controls/_base.htm†L1-L19】
- The `runs0` layout (`routes/run_0/templates/0.htm`) stitches the controller partials together, injects `controllers.js`, and hosts large inline CSS blocks for layout and color tweaks.【F:wepppy/weppcloud/routes/run_0/templates/0.htm†L1-L194】
- JavaScript controllers are singletons bundled into `controllers.js`. `control_base.js` provides orchestration helpers (job polling, summary/status writers, stacktrace rendering) that every controller mixes in.【F:wepppy/weppcloud/controllers_js/control_base.js†L5-L199】

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
1. **Pure base wrapper**
   - Replace `_base.htm` and `.controller-section` with a new `_pure_base.htm` built on `.pure-form`, `.pure-g`, and `.pure-u-*` grid utilities. The wrapper manages spacing, border, and background consistently across controls, enforcing the Pure.css foundation.
   - Keep the semantic structure: heading, inputs, job status, summary, stacktrace. Expose optional slots via `{% block summary %}` or `{% block footer %}` overrides so downstream templates can extend the base without forking markup.
2. **Macro-driven components**
   - Mandate Jinja macros for inputs, status banners, summaries, and advanced sections (e.g., `controls/macros/forms.html`). Each control imports the macro set and renders fields by calling macros instead of hand-written markup, eliminating copy/paste drift.
   - Macros accept locale- and mode-aware metadata (labels, help text, unit adornments) supplied by NoDb so the same template primitives can render every control consistently.
3. **Typography and spacing**
   - Centralize spacing tokens (`--space-sm`, `--space-md`) and apply them through utility classes. Avoid inline `style` attributes.
   - Use `<fieldset>` and `<legend>` for grouped inputs so screen readers and keyboard users benefit from the structure.
4. **Status + summary module**
   - Implement reusable fragments (e.g., `_control_status.htm`, `_control_summary.htm`) that are invoked from macros and `_pure_base.htm`. Controllers that do not need summaries can opt out by passing a flag.
   - Style the summary block with Pure CSS cards, leaving `#info` available for ControlBase to inject markup while keeping macro-generated HTML minimal.
5. **Advanced options**
   - Use `<details>` / `<summary>` or a Pure CSS accordion module. Provide JS hooks to auto-open on validation errors or server-provided context.
6. **File uploads**
   - Introduce a `control-file-input` component that pairs file inputs with asynchronous progress bars. Hook into ControlBase to disable submit buttons until uploads finish.
7. **Unit-aware inputs**
   - Standardize on a `data-unit-key` attribute. A shared `UnitSynchronizer` module can watch `unitizer_modal` events and format values accordingly.
8. **Mode switches**
   - Prefer CSS class toggles driven by data attributes (`data-mode="basic"`) with htmx snippets for server-rendered fragments when options differ dramatically.

## Interaction and Routing Strategy
- **Event contract**
  - Controllers emit `change` events to keep UI state synchronized, but actual persistence happens on explicit actions (`Run`, `Save`, `Preview`). This avoids a proliferation of micro-routes while keeping the UI responsive.
  - Adopt htmx `hx-post`/`hx-swap` for targeted updates (e.g., recalculating summary blocks) without requiring bespoke fetch logic in every controller.
- **Route consolidation**
  - Stand up a `/controls` blueprint with predictable routes such as `/<control_slug>/submit`, `/<control_slug>/upload`, and `/<control_slug>/meta`. Reflection maps each slug to its NoDb handler so controllers configure only their slug and allowed actions.
  - Every async action returns the uniform JSON schema (`status`, `info`, `summary_html`, `stacktrace`, optional `htmx`) so `control_base.js` can update the DOM without controller-specific logic.
  - Maintain a single validation surface: the NoDb method performs schema enforcement (potentially via dataclasses) and returns serialized errors for the UI. Metadata routes reuse the same descriptors that power macros to keep template data consistent.
- **WebSocket alignment**
  - Standardize on `controlBase.attach_status_stream` with `data-ws-channel` (or explicit options) so controllers opt in without manual wiring. The helper fabricates hidden status/stacktrace panels when Pure markup is absent; the legacy `ws_client.js` bridge has been removed.

## Target Architecture
- **Templating + metadata contract**
  - `_pure_base.htm` and the macro library act as the only public entry points for control markup. NoDb exposes metadata (field definitions, help text, unit hints) that macros consume, ensuring the HTML fragments the macros emit always match backend expectations.
  - Reusable fragments (`_control_status.htm`, `_control_summary.htm`, upload macros) live beside `_pure_base.htm` so updates automatically propagate to every control without template rewrites.
- **NoDb orchestration**
  - Guarantee every control action maps to a method on the run-scoped singleton via a declarative registry. Decorators capture command metadata (idempotent, requires lock, spawns RQ job) so logging and locking stay consistent.
  - Responses follow the uniform JSON schema (`status`, `info`, `summary_html`, `stacktrace`, optional `htmx`) and can optionally bundle macro-ready data blobs so templates render new fragments without ad-hoc serialization logic.
- **Asynchronous work + telemetry**
  - RQ workers standardize payload schemas and emit structured status messages (`summary`, `progress`, `warnings`). ControlBase consumes these messages uniformly, updating the macro-generated summary/status panes without controller-specific JS.
  - File uploads stream to temporary storage, trigger immediate validation, and publish start/finish events so the shared progress UI flips states predictably.
- **Unit and locale services**
  - Centralize unit conversion helpers in NoDb; controls pass `unit_key` and values and receive canonical units plus display formatting hints to hand to macros.
  - Locale descriptors (see below) expose datasets, labels, and units through the same metadata surface so macros and htmx payloads stay locale-aware.

## Locale Strategy
- **Run-scoped locale selection**
  - Persist a `locale_code` on each run; controllers read it from the run manifest and pass it with every request.
- **Inheritance hierarchy**
  - Model locales as composable Python dataclasses (e.g., `BaseLocale`, `USLocale(BaseLocale)`, `IdahoLocale(USLocale)`) where subclasses override metadata such as climate options, landuse codes, and default units.
  - Serialize locale descriptors (`display_name`, `climate_modes`, `landuse_catalog`, `unit_overrides`) for client use. Provide a `resolve_locale(locale_code)` helper in NoDb to merge parent dataclasses before applying overrides, guaranteeing predictable inheritance.
- **Content hooks**
  - Register a Jinja context processor that injects locale-aware strings and metadata (`locale`, `unit_labels`) into every controller template, giving macros direct access without extra plumbing.
  - JS controllers receive locale data via `data-locale` attributes to drive drop-downs and validations without hardcoding US defaults.

## htmx Adoption Opportunities
- Replace bespoke AJAX calls with `hx-post` for simple form submissions, letting the server return partial HTML fragments (`hx-target="#info"`) alongside JSON payloads for ControlBase.
- Use `hx-trigger="change delay:500ms"` on numeric inputs that need debounced recomputation (e.g., dynamic summaries) without manual timers.
- Implement cascading selects (e.g., locale -> climate mode) via `hx-get` requests that fetch localized option lists.

## Implementation Roadmap
1. **Inventory + Audit**
   - Catalogue each controller template, noting input types, file uploads, dynamic behaviors, and backend routes. Capture this in a shared spreadsheet to prioritize work.
2. **Design system scaffolding**
   - Create `static/css/controls.css` with Pure CSS modules (`control-card`, layout tokens). Build `_pure_base.htm`, macro libraries, and shared fragments so every control can migrate without duplicating markup.
3. **Runs0 shell refactor**
   - Move inline CSS from `0.htm` into `controls.css`; rework layout using Pure CSS grid classes. Ensure the TOC and content area remain accessible on mobile.
4. **Controller migration**
   - Tackle controllers in batches: start with simple static forms, then advanced-option panels, then file upload flows. Each migration swaps `_base.htm` for `_pure_base.htm`, replaces Bootstrap classes with Pure utilities, and adopts the macro set.
5. **Interaction cleanup**
   - Stand up the `/controls` blueprint, reflection registry, and uniform JSON responses; update ControlBase helpers and macros to consume the shared schema. Introduce a shared `control-actions.js` (or htmx attributes) that handles change vs submit semantics, retiring redundant routes as the dispatcher comes online.
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
