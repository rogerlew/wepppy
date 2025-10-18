# Control View Standardization & Run0 Restyling Blueprint

## 1. Current state inventory

### 1.1 Control templates
- All controller views extend `templates/controls/_base.htm`, which still ships Bootstrap era layout (`col-md-*`, `.form-group`) and inline spacing for titles, status, and summary panes.【F:wepppy/weppcloud/templates/controls/_base.htm†L1-L18】
- Individual controls (e.g., `landuse.htm`) embed large conditional blocks that pivot on locale flags and module toggles (such as `ron.locales` or `ron.mods`), leading to deeply nested `<option>` lists and duplicated markup for display modes and advanced inputs.【F:wepppy/weppcloud/templates/controls/landuse.htm†L1-L117】
- Specialized panes like Omni and BatchRunner pull in extra partials under `controls/omni/` or separate blueprints, but they still rely on the `_base.htm` DOM contract for status, stacktrace, and summary rendering.

### 1.2 Run 0 page shell
- `routes/run_0/templates/0.htm` is a self-contained HTML document that bootstraps Bootstrap, jQuery, Leaflet, glify, and the legacy CSS bundle, then inlines a large `<style>` block to arrange the sidebar and content areas.【F:wepppy/weppcloud/routes/run_0/templates/0.htm†L1-L133】
- The page includes nearly every control template in sequence, producing a long single-column layout with repeated `controller-section` wrappers and bespoke spacing overrides.【F:wepppy/weppcloud/routes/run_0/templates/0.htm†L69-L140】
- Command routing is orchestrated via the `controllers.js` bundle and `preflight.js`, both included globally on the run page regardless of which controls are active.【F:wepppy/weppcloud/routes/run_0/templates/0.htm†L22-L64】

### 1.3 JavaScript orchestration
- `control_base.js` defines the shared contract for ControlBase subclasses: run/job state management, stacktrace rendering, RQ job polling, and WebSocket integration with `WSClient`. Controls configure IDs and callbacks so the infrastructure can disable buttons, fetch `/rq/api/jobstatus/`, and stream status updates to the standard DOM nodes.【F:wepppy/weppcloud/controllers_js/control_base.js†L1-L138】【F:wepppy/weppcloud/controllers_js/control_base.js†L139-L220】
- Controller modules are singletons assembled into `static/js/controllers.js` through a Jinja template, guaranteeing each panel hooks into the shared form markup once per page.【F:wepppy/weppcloud/controllers_js/README.md†L5-L62】

### 1.4 Backend singletons & locales
- NoDb controllers inherit locale context either from the run configuration (`config_get_list('general', 'locales')`) or `NoDbBase.locales`, which hard-codes fallbacks for common configs (US, EU, AU, regional overlays).【F:wepppy/nodb/core/climate.py†L786-L812】【F:wepppy/nodb/base.py†L1147-L1173】
- Controls frequently branch on `ron.locales` to load locale-specific options (e.g., CORINE vs. NLCD layers), but the inheritance story is implicit—there is no composable locale object graph yet.【F:wepppy/weppcloud/templates/controls/landuse.htm†L23-L117】
- Unit conversions live in `nodb/unitizer.py`, a large registry of converter lambdas and precision tables, currently surfaced via modal dialogs on the run page.【F:wepppy/nodb/unitizer.py†L1-L120】

## 2. Pain points to address
1. **Inconsistent markup & styling.** Bootstrap-era classes mixed with inline styles prevent the Pure.css foundation from taking over and force each control to solve layout spacing independently.
2. **Duplicated locale logic.** Template branches manually enumerate locale-specific options; backend logic already knows the locale list but lacks a standardized way to expose structured metadata.
3. **Fragmented validation.** Some inputs post onchange to dedicated routes while others submit the full form. Front-end validation is minimal and drifts from backend enforcement in NoDb controllers.
4. **File upload divergence.** Upload-based controls (BAER, road, Omni scenario imports) bend the shared `_base` contract to accommodate file inputs and progress states without reusable patterns.
5. **Dynamic builders.** Omni’s JS builder and BatchRunner’s page-scale interface diverge from static form assumptions, complicating the push toward reusable CSS and htmx-style partial updates.
6. **Locale expansion.** Non-US locales bolt on datasets and configuration toggles without hierarchical inheritance, making it hard to reason about available options or unit expectations per run.

## 3. Design objectives for the restyle
- **Adopt Pure.css grid + foundation tokens.** Replace Bootstrap columns and inline padding with `.pure-g`, `.pure-u-*`, and `wc-*` utilities so controls inherit consistent spacing and typography (as defined in `ui-foundation.css`).
- **Formalize the control DOM contract.** Document a minimal required structure (status banner, summary region, stacktrace, controls toolbar) so ControlBase JS continues to function while allowing custom sections for advanced options or uploads.
- **Standardize command workflows.** Encourage a single request surface per control (preferably POST endpoints keyed by control slug) that trigger NoDb mutations and enqueue RQ jobs when needed. Use JSON responses with uniform schema (`status`, `info`, `stacktrace`) so `controlBase` can render them without custom handlers.
- **Introduce declarative metadata.** Push locale- and unit-specific details from NoDb singletons to the front-end as structured JSON (e.g., `Landuse.available_datasets`), reducing template conditionals and enabling shared option components.
- **Enable progressive enhancement.** Rely on semantic HTML and data attributes so htmx (or Alpine) can progressively enhance advanced sections without requiring React-class complexity.
- **Align validation layers.** Allow lightweight client hints (masking, units display) while delegating authoritative parsing and validation to NoDb methods executed immediately when the POST lands.

## 4. Target architecture

### 4.1 Control template refactor stack
1. **New Pure base partial.** Create `controls/_pure_base.htm` that wraps the shared form content with `.pure-form` markup, `wc-panel` shells, and named slots for toolbars, status, summary, stacktrace, and advanced sections.
2. **Macro-driven inputs.** Introduce Jinja macros for common input types (text, select, radio clusters, file uploads) that apply consistent classes, label placement, helper text, and optional unit adornments.
3. **Mode-aware sections.** Use `<section data-control-mode="...">` wrappers toggled by CSS classes to show/hide content based on the active mode. Controllers can flip `data-state` attributes instead of injecting inline styles.
4. **Status & summary fragments.** Move the markup for status banners and RQ job details into reusable include files (`controls/fragments/status.htm`, `controls/fragments/summary.htm`) so updates to the DOM contract propagate automatically.
5. **Upload pattern.** Define a canonical upload block that pairs `<input type="file">`, progress text, and a retry button with the same Pure classes, ensuring BAER, road, and Omni uploads feel consistent.

### 4.2 Controller JavaScript alignment
- **Centralize endpoint mapping.** Extend `control_base.js` (or companion helper) to generate URLs based on control name + action (`/weppcloud/controls/<slug>/<action>`), enabling reflection-friendly backend routing.
- **Event normalization.** Encourage controllers to emit structured events (`control:submitted`, `control:mode-changed`) on the form element; htmx can then listen and fetch partial updates for advanced options or summary panels.
- **Unit sync helpers.** Surface a small adapter over `Unitizer` so controls can display both system and metric units and keep them synchronized. For onchange sync, throttle AJAX requests and coalesce updates server-side.
- **WebSocket standardization.** Document channel naming conventions and message payloads so new controls know which topics to subscribe to when streaming job status through Redis + `WSClient`.

### 4.3 Backend routing & NoDb expectations
- **Consolidated blueprint.** Introduce a `/controls` blueprint (or extend `run_0` blueprint) with predictable POST routes: `/<control_slug>/submit`, `/<control_slug>/preview`, `/<control_slug>/upload`. Each route delegates to a method on the corresponding NoDb singleton, keeping validation centralized.
- **Reflection-based dispatch.** Implement a registry mapping control slugs to NoDb handlers so the blueprint can resolve `Landuse` vs. `Climate` without duplicating route functions. This aligns with the goal of reducing bespoke routes.
- **Immediate validation.** File uploads should stream to temporary storage, then immediately pass through NoDb validators or worker queue tasks that sanitize and confirm payloads before writing to run directories.
- **Metadata endpoints.** Expose `/controls/<slug>/meta` returning JSON describing available modes, fields, defaults, unit info, and locale-specific overrides so front-end templates can generate dropdowns without manual branching.

## 5. Locale strategy proposal
1. **Locale class hierarchy.** Define locale descriptors under `wepppy/locales/` as composable dataclasses with `parent_ids` and `overrides` dictionaries. Allow multiple inheritance by merging parent option sets before applying child overrides.
2. **Run-level locale selection.** Each run persists a locale identifier; `NoDbBase.locales` resolves it to a merged descriptor and exposes helpers like `get_dataset_options("landuse")` and `default_units("precipitation")` for controls to consume.
3. **Frontend consumption.** Pass the merged locale JSON to templates so macros can iterate datasets, units, and climate modes without hard-coded conditionals. Example: `locale.landuse.datasets` returns label/value pairs for the dropdown.
4. **Locale-aware workers.** RQ jobs receive the locale descriptor alongside run paths, allowing workers to pick the correct dataset paths or climate adjustments without re-parsing config files.
5. **Configuration updates.** Update `.cfg`/`.toml` run configs to specify locales by identifier; the backend merges definitions to calculate dataset availability and unit expectations. Provide migration guidance for existing configs.

## 6. htmx-driven interaction model
- **Partial swaps.** Use `hx-get`/`hx-post` on sections that need dynamic content (advanced options, summary panels). Server responses return HTML fragments rendered with the same macros so styling stays consistent.
- **Progressive fallback.** Ensure each action still works via full form submission if JavaScript is disabled; htmx merely enhances with partial refreshes and loading indicators.
- **Reduced custom JS.** Let htmx handle content updates while ControlBase continues to manage job lifecycle. Omni’s builder can progressively migrate pieces (e.g., scenario row add/remove) to declarative htmx snippets while retaining bespoke logic where necessary.

## 7. Implementation phases
1. **Documentation & audit (this document).** Finalize DOM contract, metadata expectations, and locale hierarchy plan.
2. **Prototype shared components.** Build `_pure_base.htm`, macros, and fragments; migrate one simple control (e.g., `channel_delineation`) to validate the approach.
3. **Routing refactor.** Introduce the consolidated controls blueprint and metadata endpoints; adjust existing controllers to use standardized responses.
4. **Locale descriptor rollout.** Implement the hierarchical locale module, update NoDb to consume it, and refactor templates to read from the descriptor instead of branching on `ron.locales`.
5. **Run0 shell restyle.** Rebuild the run page on top of the Pure base layout (`base_pure.htm`), replacing inline CSS with `wc-` utilities and moving the TOC into a reusable component.
6. **Complex control migration.** Tackle Omni, BatchRunner, and upload-heavy panels using the new patterns; integrate htmx where it provides clear wins (dynamic builder sections, summary refresh).
7. **Unit sync enhancements.** Wire up unit metadata and synchronous conversions, offering paired inputs or inline unit toggles where appropriate.
8. **Regression pass.** Verify RQ workflows, websocket streams, and locale-specific datasets across representative runs before cutting over.

## 8. Next steps
- Circulate this blueprint with the core team for feedback on routing, locale inheritance, and the extent of htmx adoption.
- Draft the `_pure_base` template and macros in a spike branch to validate feasibility without disrupting current production templates.
- Inventory all controls that require file uploads or dynamic builders to ensure the shared patterns cover each scenario.
- Plan migrations for locale configs, including default inheritance (e.g., `idaho -> us`) and documentation updates for partners.