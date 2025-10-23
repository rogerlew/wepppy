# Controller UI and Runs0 Modernization Roadmap

This note captures the current shape of WEPPcloud controller views, the JavaScript orchestration that powers them, and a forward-looking concept for pure CSS standardization across the runs0 experience. It is written as a baseline for future refactors—especially those that need to rationalize styling, reduce copy/paste layouts, and introduce locale-aware form logic without fragmenting front/back-end responsibilities.

## 1. Current Architecture Inventory

### 1.1 Layout and Templates
- Every controller template extends `_base.htm`, which hard-codes the form scaffold (title row, `<div id="rq_job">`, `<small id="status">`, `<div id="info">`, `<div id="stacktrace">`).【F:wepppy/weppcloud/templates/controls/_base.htm†L1-L19】
- The runs0 page is server-rendered by `0.htm`; it still pulls in Bootstrap, Bootstrap-TOC, DataTables, and inline layout CSS to create the two-column table-of-contents + content layout.【F:wepppy/weppcloud/routes/run_0/templates/0.htm†L1-L194】
- The page assembles controller sections by including dozens of templates in a fixed order, with conditional blocks for optional mods (BAER, Omni, RHEM, etc.).【F:wepppy/weppcloud/routes/run_0/templates/0.htm†L120-L179】

### 1.2 JavaScript Control Infrastructure
- `control_base.js` is the shared mixin that every controller singleton imports. It wires RQ job polling, command button disable/enable logic, stacktrace rendering, and attaches the StatusStream via `controlBase.attach_status_stream` when a job is running.【F:wepppy/weppcloud/controllers_js/control_base.js†L5-L344】
- Controllers register themselves as singletons (for example `Omni.getInstance()`), bind DOM handles, override `triggerEvent` when they need extra bookkeeping, and then rely on `set_rq_job_id` to start/stop polling and WebSocket streaming.【F:wepppy/weppcloud/controllers_js/omni.js†L5-L151】
- Long-lived flows such as BatchRunner build richer state machines on top of `controlBase`, bolting on card-oriented DOM fragments, file uploads, and bespoke polling for child tasks while reusing the base job status and button management functions.【F:wepppy/weppcloud/controllers_js/batch_runner.js†L1-L158】

### 1.3 Backend Contract
- The runs0 blueprint (`run_0_bp.py`) loads all NoDb singletons, collects the `RedisPrep` job IDs, and hydrates the template with every controller dependency in one pass. This is also where run-scoped service worker metadata is attached.【F:wepppy/weppcloud/routes/run_0/run_0_bp.py†L128-L219】
- `Ron` (the run object) captures locales from the config file during initialization, primes the required NoDb controllers, and ensures run metadata lives on disk and in Redis.【F:wepppy/nodb/core/ron.py†L307-L419】
- Individual controllers read locale context through the NoDb facade; `NoDbBase.locales` falls back to a large conditional that hard-codes per-config overrides when `_locales` is absent, which illustrates how ad-hoc the current locale handling is.【F:wepppy/nodb/base.py†L1151-L1173】

### 1.4 View Variants We Must Accommodate
- Many controls are simple form grids, but several embed file uploads (e.g., climate `.cli` upload, BAER shapefiles) and toggle visibility based on run modes. Climate alone branches by locale, data source availability, and upload state within a single template.【F:wepppy/weppcloud/templates/controls/climate.htm†L1-L200】
- Omni is a dynamic, JavaScript-driven scenario builder that serializes multiple FormData payloads, appends uploaded files, and triggers follow-on reporting when RQ broadcasts a completion event.【F:wepppy/weppcloud/controllers_js/omni.js†L32-L150】
- BatchRunner behaves more like an application page: it renders data cards, tracks validation state, and streams progress for numerous subordinate jobs via custom WebSocket channels.【F:wepppy/weppcloud/controllers_js/batch_runner.js†L34-L139】

> **Status (2025-02-24):** Pure templates are now production; the notes below capture historical pain points so new work can avoid falling back to the legacy patterns.

## 2. Pain Points Observed
- (Historical) The `_base.htm` scaffold forced every controller to carry Bootstrap grid classes plus inline spacing overrides, locking us into the legacy markup. Pure templates removed this dependency, but keep an eye out for new includes that accidentally reference `_base`.【F:wepppy/weppcloud/templates/controls/_base.htm†L1-L19】
- (Historical) The legacy runs0 page embedded a large `<style>` block per load. With `runs0_pure.htm` this is gone—future tweaks should extend `ui-foundation.css` instead of inline styles.【F:wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm†L1-L140】
- Locale-specific behaviors are sprinkled throughout templates—frequently via Jinja conditionals—making it difficult to apply consistent unit-aware controls or to layer new locales without copy/paste logic.【F:wepppy/weppcloud/templates/controls/climate.htm†L63-L176】
- File upload handling differs per controller; some rely on `<form enctype="multipart/form-data">` posts, others use AJAX FormData, and error surfaces appear in idiosyncratic ways. Omni, BatchRunner, and Climate all implement their own patterns.【F:wepppy/weppcloud/controllers_js/omni.js†L32-L90】【F:wepppy/weppcloud/controllers_js/batch_runner.js†L83-L138】【F:wepppy/weppcloud/templates/controls/climate.htm†L25-L55】
- Because every controller polls `/rq/api/jobstatus/<id>` independently, we maintain many near-duplicate routes and cannot easily standardize advanced options like auto-refresh of summary panels without more shared plumbing.【F:wepppy/weppcloud/controllers_js/control_base.js†L178-L344】【F:wepppy/weppcloud/routes/run_0/run_0_bp.py†L178-L219】

## 3. Pure CSS Controller Style Guide (Concept)
1. **Canonical Shell** – Replace `_base.htm` with a semantic shell component (e.g., `<section class="wc-control">`) that renders:
   - Header (title + optional status pill)
   - Body slots for form controls, summaries, and stack traces
   - Footer actions (primary button group, help links)
   The shell should be styled via `ui-foundation.css` tokens instead of inline rules.【F:wepppy/weppcloud/templates/controls/_base.htm†L1-L19】【F:wepppy/weppcloud/static/css/ui-foundation.css†L1-L120】
2. **Form Layout Tokens** – Define a CSS utility stack (`.wc-field`, `.wc-field--inline`, `.wc-field__label`, `.wc-field__control`) and migrate controls from Bootstrap grid markup to these utilities to remove `.row`/`.col-*` dependencies.
3. **Status & Summary Blocks** – Standardize success/info/error presentations (job badge, summary card, stacktrace panel) so that `controlBase` can target `.wc-control__status` and `.wc-control__summary` consistently.
4. **Advanced Mode Disclosure** – Provide a `<details>`/`<summary>` or toggle pattern for advanced/optional settings instead of manually hiding DOM fragments. Pair with `htmx` snippets or server-driven partials for complex configuration to avoid large static templates.
5. **Unit-Aware Inputs** – Introduce a `data-unit` attribute standard that the backend can hydrate (e.g., `data-unit="mm"`). A minimal JS helper can render suffix labels or convert values inline, while NoDb remains the canonical validator.
6. **Composable Partials** – Move repeated fragments (file upload row, multi-radio groups, dataset selectors) into include files that accept context dictionaries. This reduces cut-and-paste styling and centralizes locale overrides.

## 4. Asynchronous Workflow Contract
- Consolidate job submission routes behind a reflection-friendly API layer (e.g., `/rq/api/<controller>/<action>`). `controlBase.set_rq_job_id` already normalizes job IDs; we can inject metadata (`data-controller`, `data-action`) to auto-wire event handling without dozens of custom JS methods.【F:wepppy/weppcloud/controllers_js/control_base.js†L141-L208】
- `RedisPrep.get_rq_job_ids()` is the authoritative source of current work; expose it through a unified `/runs/<id>/<cfg>/jobs` endpoint so all controllers can hydrate from a single JSON payload and subscribe to updates via WebSocket topics keyed by controller names.【F:wepppy/weppcloud/routes/run_0/run_0_bp.py†L178-L219】
- Align front-end polling cadence with backend push: the StatusStream (attached through `controlBase.attach_status_stream`) should remain the primary conduit, with polling only as a fallback when a channel is unavailable. That keeps the backend validation surface single-layered—NoDb remains the enforcer and RQ just reports status.【F:wepppy/weppcloud/controllers_js/control_base.js†L203-L344】
- Htmx fits well for partial refreshes (e.g., summary tables, advanced option panels) because it leans on existing Flask routes and avoids bundling overhead. Each controller section can expose an `hx-get` endpoint that re-renders only the summary card after a job completes.

## 5. Runs0 Page Modernization Concept
1. **Shell & Navigation** – Replace the inline styles with a `wc-page` layout defined in `ui-foundation.css`, using CSS Grid/Flexbox to render the table of contents and content areas without custom per-page `<style>` tags.【F:wepppy/weppcloud/routes/run_0/templates/0.htm†L38-L123】【F:wepppy/weppcloud/static/css/ui-foundation.css†L41-L110】
2. **Controller Mount Points** – Wrap each included control in a `<section id="control-<name>" class="wc-control">` container so anchors, htmx swaps, and CSS all share a predictable namespace.【F:wepppy/weppcloud/routes/run_0/templates/0.htm†L120-L179】
3. **Command Bar Integration** – Keep the existing command bar partial but restyle it with the same CSS token set so command buttons, status indicators, and lock icons align visually with controller sections.【F:wepppy/weppcloud/routes/run_0/templates/0.htm†L33-L37】
4. **PowerUser Modal** – Externalize the modal styles into a CSS module and refactor the JS bootstrapping so it can lazy-load via htmx when the user opens the modal. The modal currently contains push-notification setup logic that will not change, but its presentation can inherit the same typography/spacing rules.【F:wepppy/weppcloud/templates/controls/poweruser_panel.htm†L1-L105】

## 6. Locale Strategy Proposal
- Treat locale selection as run metadata (already part of `Ron`) and expose it to the UI as a structured list (primary locale + inheritance chain). Controllers should read a normalized object rather than string tuples, allowing the template to iterate predictable properties.【F:wepppy/weppcloud/routes/run_0/run_0_bp.py†L128-L219】【F:wepppy/nodb/core/ron.py†L343-L419】
- Move the fallback logic out of `NoDbBase.locales` into declarative locale definitions. The current `if/elif` cascade should be replaced by a registry that understands inheritance (e.g., `Idaho -> US -> Earth`), so controllers can derive default datasets or option lists without embedding region-specific conditionals.【F:wepppy/nodb/base.py†L1151-L1173】
- Locale descriptors can carry:
  - Display name, unit system, default climate/landuse/soil datasets
  - Available mode toggles (e.g., which climate methods make sense)
  - Optional htmx endpoints for localized help content
- The backend continues to validate payloads via NoDb singletons; the front-end only uses locale metadata for UI hints and unit rendering, keeping validation centralized.

## 7. Implementation Phases (Recommended)
1. **Document & Audit** – Catalogue each controller’s inputs, AJAX routes, and summary outputs in a shared spreadsheet/doc to confirm edge cases (file uploads, advanced toggles). Use this document as the canonical reference when migrating markup.
2. **Build Pure CSS Shell** – Implement the new control shell components and CSS utilities, wire them into `_content_base.htm` for purely informational panels, and migrate one simple controller (e.g., `export.htm`) as a pilot.【F:wepppy/weppcloud/templates/controls/_content_base.htm†L1-L5】
3. **Standardize Async Pipeline** – Introduce the unified jobs endpoint + metadata-driven polling, update `controlBase` to prefer WebSocket events, and retrofit controllers incrementally.
4. **Refactor Complex Controllers** – Address Omni and BatchRunner once the shell/utilities are battle-tested. Extract shared file upload widgets and adopt htmx for dynamic scenario/validation fragments.
5. **Locale Registry & Unit Helpers** – Implement the locale inheritance registry, surface locale metadata to templates, and retrofit climate/landuse/soil controls to use declarative options. Pair this with unit-aware input helpers so additional controls can opt-in without new routes.
6. **Runs0 Layout Refresh** – After controller sections are styled, replace the inline CSS and legacy Bootstrap grid with the pure CSS layout, ensuring the TOC/command bar remain functional.

Following these steps keeps backend validation single-sourced (NoDb) while letting the front-end become a transparent, declarative layer that is easy to maintain without introducing heavy frameworks such as React. Htmx can provide interactivity where necessary without breaking the unified stack philosophy.
