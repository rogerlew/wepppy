# Control UI Styling – Agent Guide

## Authorship
**This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**

_Last updated: 2025-10-18_

## Current Status
- **Inventory complete.** `control-inventory.md` now catalogs every runs0 control, including inputs, backend bindings, and conditional behavior.
- **Macro surface ready.** `_pure_macros.html` covers the common control patterns (header, text, numeric, radio, select, checkbox, textarea, upload, display, table, dynamic slot, collapsible card) with accessible help + error wiring documented in `control-components.md`.
- **Prototype live.** `/ui/components/` renders the Pure-aware control shell (see `ui_showcase/component_gallery.htm`) powered by `_pure_base.htm`, `_pure_macros.html`, and updated tokens in `static/css/ui-foundation.css`.
- **Status streaming baseline.** `status_panel` / `stacktrace_panel` macros plus `status_stream.js` power the fork console and archive dashboard; ControlBase still points at legacy IDs until run controls migrate.
- **Legacy `_base.htm` untouched (yet).** Existing controls still rely on Bootstrap-era templates; migration will start after the component API stabilizes.

## Key Files
| Area | Path | Notes |
| --- | --- | --- |
| Inventory | `docs/ui-docs/control-ui-styling/control-inventory.md` | Source of truth for control inputs, routes, and JS wiring. Update in sync with code changes. |
| Component spec | `docs/ui-docs/control-ui-styling/control-components.md` | Macro contracts, layout hierarchy, run-header guidance. |
| Blueprint | `wepppy/weppcloud/routes/ui_showcase/` | Flask blueprint for `/ui/components/` showcase. |
| Prototype template | `wepppy/weppcloud/templates/ui_showcase/component_gallery.htm` | Demonstrates shell + example fields. Expand with every new macro. |
| Pure shell | `wepppy/weppcloud/templates/controls/_pure_base.htm` | Collapsible control shell with summary row and stacked status panels. |
| Macros | `wepppy/weppcloud/templates/controls/_pure_macros.html` | Early helper macros (`control_shell`, `text_field`, etc.). |
| CSS | `wepppy/weppcloud/static/css/ui-foundation.css` | Holds design tokens and new `.wc-control` styles. Extend here, not inline. |

## Active Workstream
1. **Pilot migration**  
   - Migrate a low-risk production control (e.g., `channel_delineation`) onto the Pure macros to validate metadata contracts and error handling.  
   - Capture lessons learned in `control-inventory.md` and update this AGENT guide.
2. **Define metadata contract**  
   - Decide which attributes controllers must expose (labels, unit hints, validation rules).  
   - Document the contract in `control-components.md` and retrofit NoDb controllers once agreed.
3. **Validation patterns**  
   - Align staking on error/warning states (copy, iconography, colour usage) and add guidance once consensus lands.  
   - Ensure macros remain lightweight; expand CSS tokens instead of control-specific overrides.
4. **Deprecate legacy assets**  
   - Evaluate road upload panel (currently orphaned) and either remove or rebuild before migration begins.
5. **Unitizer integration**  
   - During the `build_controllers_js.py` step emit a static `unitizer_map.js` derived from the backend tables so browsers can cache conversions.  
   - Macros emit `data-unit-*` attributes; the shared JS helper reads the prebuilt map and syncs fields without custom per-control hooks.
6. **Spec-driven collaboration (exploratory)**  
   - Prototype a lightweight YAML/JSON spec that describes control composition (fields, macros, dynamic sections).  
   - Use it as developer documentation/exemplars, with human interpretation translating specs into `_pure_base` templates. No runtime coupling yet—evaluate after initial migrations.

## Working Agreements
- Showcase (`/ui/components/`) is the canonical example. Update it before touching production controls so reviewers can test new patterns in isolation.
- `_base.htm` is archived; production controls must use the Pure macros. Update the showcase first so reviewers can test changes in isolation.
- When a control is migrated, update both `control-inventory.md` and this AGENTS file with progress/notes.
- Pure shell styling lives in `ui-foundation.css`; no inline styles in templates.
- Checkbox/radio styling: reuse shared classes (`.wc-choice`, `.wc-choice--checkbox`, `.wc-run-header__toggle`) so accent colors and spacing stay consistent; blue system toggles mean the class is missing.
- Dark mode is explicitly out-of-scope for this iteration; stay focused on polishing the light theme tokens and contrast ratios.
- Run pages now bootstrap controllers via `WCControllerBootstrap`. Build a single `runContext` object (run metadata, job ids, `data.*` feature flags) and call `WCControllerBootstrap.bootstrapMany([...], runContext)` instead of poking controller internals. Controllers own their job wiring and report hydration via `instance.bootstrap(context)`.

## Near-Term Focus
- **Unitizer modal polish:** restyle the modal with Pure tokens and align the toggle controls with the shared checkbox/radio pattern.
- **Numeric unit switching:** wire the unitizer controls into `numeric_field` so unit changes propagate across paired inputs.
- **ControlBase integration:** ensure new/updated controls continue to render `status_panel` / `stacktrace_panel` and rely on `controlBase.attach_status_stream` for telemetry.
- **Console follow-through:** monitor fork/archive consoles for regressions (autoscroll, trigger handling, stacktrace enrichment) and fold lessons into the broader migration.
- **Controller metadata contract:** formalize the schema (labels, units, validation states) so macros can rely on consistent inputs.
- **Error/warning messaging:** standardise copy and iconography for validation states before wider macro adoption.


### Coordination Notes
- Keep run-time behaviour intact: preference saves still post through `Project` routes; new JS must merely hydrate from the static map.
- Guard against stale data by hashing the generated map or versioning it alongside the controllers bundle timestamp.
- Avoid introducing a new build dependency if possible—prefer extending the existing `wctl build-static-assets` / controllers build flow.

## Open Questions
- Final macro signatures for table-oriented panels (landuse/soils summaries) and how to wrap dynamic controller-managed sections; document decisions as the integration package progresses.
- Whether to expose additional global CSS variables for spacing/width adjustments beyond the current token set.

## Contact / Escalation
- Architectural questions: reference the Pure UI spec (`control-components.md`) first; if unclear, tag UI maintainers in GitHub issues.
- Showcase bugs or missing macros: open a ticket in the UI Components board and assign to the styling working group.

Stay within this doc for the latest guidance; update it whenever workflows or priorities shift.
