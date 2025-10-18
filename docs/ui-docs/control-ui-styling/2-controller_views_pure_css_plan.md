docs/dev-notes/controller_views_pure_css_plan.md
New
+79
-0

# Controller View Modernization and Pure CSS Strategy

## 1. Current Run Page Composition
- The run dashboard (`run_0/templates/0.htm`) pulls in Bootstrap, DataTables, and other vendor CSS/JS assets before composing the page with the header, command bar, and the `controls/` partials inside a flex-based `project-layout` wrapper.【F:wepppy/weppcloud/routes/run_0/templates/0.htm†L1-L195】
- Every control section is injected via `{% include 'controls/<name>.htm' %}`. Most panels extend `controls/_base.htm`, which defines the shared `form` skeleton plus the required `#rq_job`, `#status`, `#info`, and `#stacktrace` containers consumed by the JavaScript controllers.【F:wepppy/weppcloud/routes/run_0/templates/0.htm†L124-L179】【F:wepppy/weppcloud/templates/controls/_base.htm†L1-L20】
- A smaller group of read-only/informational panels extend `controls/_content_base.htm`, which swaps the `<form>` wrapper for a content-only container while preserving the `.controller-section` styling hook.【F:wepppy/weppcloud/templates/controls/_content_base.htm†L1-L5】

## 2. Control Infrastructure in JavaScript
- `control_base.js` is the mixin that all controllers consume. It standardizes job-state polling, button disabling, stacktrace rendering, and WebSocket orchestration by assuming the template IDs defined in `_base.htm`. The helper also renders RQ job metadata, requeues polling while work is in-flight, and exposes `triggerEvent` for cross-controller signaling.【F:wepppy/weppcloud/controllers_js/control_base.js†L5-L344】
- `ws_client.js` connects each control to the Redis-backed status stream. It pushes spinner frames into `#braille`, appends exception text to `#stacktrace`, and forwards `TRIGGER` payloads back into the parent control’s `triggerEvent` handler.【F:wepppy/weppcloud/controllers_js/ws_client.js†L6-L161】
- The controllers bundle is documented in `controllers_js/README.md`, which clarifies the singleton pattern (`Controller.getInstance()`), the bundling pipeline, and the DOM contract between templates and JavaScript. This doc is the authoritative reference for keeping new controls aligned with the infrastructure.【F:wepppy/weppcloud/controllers_js/README.md†L7-L46】

## 3. Categories of Existing Controls
- **Simple asynchronous forms**: Many controllers (e.g., soils, landuse, wepp) are single-submit panels that rely on `_base.htm` for status areas and use `controlBase` only for button state and job polling.
- **Mode-gated forms**: Climate exposes dozens of radio groups and conditional containers that are toggled by mode. The template checks locale flags directly (`ron.locales`) and shows/hides sections with controller logic, highlighting the need for structured data-driven layouts.【F:wepppy/weppcloud/templates/controls/climate.htm†L1-L160】
- **File upload flows**: Climate uploads `.cli` payloads through `<input type="file">` fields and `FormData` AJAX posts before queueing RQ work.【F:wepppy/weppcloud/templates/controls/climate.htm†L25-L55】【F:wepppy/weppcloud/controllers_js/climate.js†L67-L107】
- **Dynamic builders**: Omni renders scenario cards in JavaScript, serializes mixed input/file data, and resubmits via JSON-formatted `FormData`. It uses custom DOM builders outside the static template to manage arbitrary scenario counts.【F:wepppy/weppcloud/controllers_js/omni.js†L20-L150】
- **Standalone pages**: The Batch Runner dashboard uses `_base.htm` but behaves like a multi-section page with cards, tables, and embedded navigation, exposing the limits of the existing `.controller-section` styling and Bootstrap dependency.【F:wepppy/weppcloud/routes/batch_runner/templates/batch_runner.htm†L1-L162】

## 4. Data Flow from Runs to Controllers
- `run_0_bp.runs0` loads the working directory context, instantiates all relevant `NoDbBase` singletons, harvests cached RQ job IDs from `RedisPrep`, and passes everything into the `0.htm` template so the front end can restore state and resume polling.【F:wepppy/weppcloud/routes/run_0/run_0_bp.py†L115-L219】
- `run_page_bootstrap.js.j2` seeds globals (`runid`, `config`, `readonly`), then asks every singleton controller to bind to the DOM, restore their state, and set RQ job IDs. The script also wires cross-control dependencies (map clicks feed outlet selection, subcatchment coloring toggles rangeland panels, etc.).【F:wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2†L5-L200】
- Once a controller submits work it typically hits a `tasks/<name>/` or `rq/api/<job>` endpoint, queues an RQ job, and relies on the Redis pub/sub → Go status relay → `WSClient` path described in the repository’s architecture notes.【F:wepppy/weppcloud/controllers_js/control_base.js†L178-L277】【F:wepppy/weppcloud/controllers_js/ws_client.js†L35-L108】

## 5. Unit Awareness Today
- `initUnitConverters` scans the DOM for `[data-convert-*]` attributes and keeps paired metric/imperial inputs synchronized, but the integration is ad-hoc: individual templates need to set the attributes manually and must call `initUnitConverters` after injecting new markup.【F:wepppy/weppcloud/static/js/input-unit-converters.js†L1-L95】【F:wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2†L51-L57】
- The Unitizer control exposes preference radio groups but those selections are not consistently reflected back into other controls; a pure CSS restyle should treat these as first-class design tokens that templates and controllers can consume.

## 6. Pain Points to Address
- Styling mixes Bootstrap utility classes, bespoke inline styles, and older Pure.css idioms within the same panel, making consistent theming difficult.【F:wepppy/weppcloud/routes/run_0/templates/0.htm†L38-L118】【F:wepppy/weppcloud/routes/batch_runner/templates/batch_runner.htm†L5-L155】
- Templates embed presentation logic (e.g., climate locale checks) rather than consuming structured configuration from the backend, leading to brittle cascades whenever new locales or modes appear.【F:wepppy/weppcloud/templates/controls/climate.htm†L63-L157】
- Route proliferation: controllers call purpose-built endpoints such as `tasks/set_climatestation_mode` or `view/closest_stations`, each defined separately in the Flask blueprint. Refactoring toward reflective dispatch would reduce duplication and make htmx adoption easier.【F:wepppy/weppcloud/controllers_js/climate.js†L120-L196】

## 7. Design Goals for the Pure CSS Refresh
1. **Codify the panel contract**
   - Publish a Jinja macro (e.g., `{% controller_panel id="climate" title="Climate" %}`) that renders the `form`, status region, and structural hooks so controls stop copy/pasting `_base.htm`. This macro can accept slots for primary inputs, advanced sections, file upload dropzones, and summary blocks.
   - Provide companion macros for secondary content (`controller_content_panel`) and shared UI fragments like button rows, labeled fields, or accordion toggles.

2. **Adopt a token-based stylesheet**
   - Replace inline styles with a `controllers.css` file that defines spacing, typography, and state colors using CSS custom properties derived from the unit/system preferences.
   - Define semantic utility classes (e.g., `.controller-grid`, `.controller-actions`, `.controller-status`) to replace ad-hoc Bootstrap classes and make the templates framework-agnostic.

3. **Composable advanced options**
   - Introduce partial templates for common patterns (collapsible “Advanced” sections, file-upload cards, summary tables) so controllers toggle them via data attributes rather than reimplementing markup. htmx fragments can progressively enhance the content by swapping sections without reloading the entire page.

4. **Async UX normalization**
   - Establish a shared status header that always shows job state, last message, elapsed time, and links to the RQ dashboard using `controlBase.render_job_status`. Buttons should live in a `.controller-actions` slot so `controlBase` can toggle `disabled` without jQuery data lookups.
   - Augment `controlBase` with opt-in htmx helpers: controls can attach `hx-post` attributes to buttons and let a single `/controls/<name>/<action>` endpoint route requests to the relevant `NoDb` method by reflection, returning partial HTML for the status/summary panels.

5. **Unit-aware inputs as first-class components**
   - Wrap unit-paired inputs in a reusable macro that emits both text boxes, the required `data-convert-*` attributes, and contextual unit labels. Controllers then initialize them via `initUnitConverters` automatically when the macro runs.
   - Reflect unit metadata from `Unitizer` in the Flask context so templates can show preferred units without hardcoding locale-specific strings.【F:wepppy/weppcloud/routes/run_0/run_0_bp.py†L156-L213】

6. **Locale inheritance strategy**
   - Model locales as Python classes that inherit from base definitions (e.g., `class USLocale(BaseLocale)` → `class IdahoLocale(USLocale)`), supplying static descriptors for climate modes, landuse presets, and label text.
   - Surface the active locale hierarchy (`ron.locales`) to templates as structured JSON rather than scattered string flags. Controllers can request locale-aware config through a single endpoint (`/api/control/<name>/schema`) that merges parent/child definitions, letting the front end render choices dynamically.

7. **Runs0 page choreography**
   - Break the current monolithic `0.htm` into a layout template and a registry of controller panels. Each panel registers metadata (title, anchor ID, required roles), enabling the Table of Contents, command bar, and `run_page_bootstrap.js` to iterate over the registry instead of hard-coded includes.
   - Move inline `<style>` blocks into the new stylesheet and let the layout expose CSS variables (`--controller-spacing`, `--controller-max-width`) that locale or unit selections can override.

## 8. Backend Coordination Principles
- `NoDbBase` singletons remain the source of truth for validation and security. New reflective routes should delegate immediately to the appropriate `NoDb` method and return structured errors that `controlBase.pushResponseStacktrace` can display.【F:wepppy/weppcloud/controllers_js/control_base.js†L71-L98】
- Reduce the surface area of Flask endpoints by introducing controller registries: each control describes its tasks (`build`, `refresh`, `upload`) and the blueprint exposes a generic dispatcher (`/controls/<name>/<action>`). Reflection keeps task definitions close to their `NoDb` counterparts while avoiding dozens of bespoke routes.
- RQ job submissions should return a unified payload (`{Success, job_id, message}`) so controls can call `set_rq_job_id` and rely on shared status rendering without bespoke success handlers.【F:wepppy/weppcloud/controllers_js/control_base.js†L141-L218】

## 9. HTMX Integration Opportunities
- htmx can progressively load advanced sections (`hx-get` on expand) or submit lightweight configuration changes (`hx-post` for unit toggles) without wiring custom jQuery for each interaction.
- Combine htmx with the proposed dispatcher so `/controls/<name>/view/<partial>` returns HTML fragments that drop into the `.controller-summary` slot. This preserves full-page functionality for non-JS clients while offering richer interactivity.

## 10. Next Steps Checklist
1. Inventory every control to catalog required subcomponents (selectors, maps, tables, uploads) and identify candidates for reusable macros.
2. Draft the shared CSS tokens and macro API, then spike a pilot conversion (e.g., Unitizer + Climate) to validate the structure.
3. Add backend registries for locales and controller actions, exposing schema metadata to templates and controllers.
4. Refactor `run_page_bootstrap.js` to iterate over a declarative controller manifest so new panels participate automatically in initialization and polling.
5. Evaluate htmx adoption by prototyping a reflective POST endpoint and htmx-driven summary refresh for one control.
6. Document the locale inheritance model and unit-aware component usage so future controls ship with the standardized UX by default.

This plan captures the current implementation details and outlines a path toward composable, pure-CSS controller views that align front-end ergonomics with the NoDb-first backend philosophy.