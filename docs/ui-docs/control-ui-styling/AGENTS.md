# Control UI Styling – Agent Guide

## Authorship
**This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**

_Last updated: 2025-10-18_

## Current Status
- **Inventory complete.** `control-inventory.md` now catalogs every runs0 control, including inputs, backend bindings, and conditional behavior.
- **Macro surface ready.** `_pure_macros.html` covers the common control patterns (header, text, numeric, radio, select, checkbox, textarea, upload, display, table, dynamic slot, collapsible card) with accessible help + error wiring documented in `control_components.md`.
- **Prototype live.** `/ui/components/` renders the Pure-aware control shell (see `ui_showcase/component_gallery.htm`) powered by `_pure_base.htm`, `_pure_macros.html`, and updated tokens in `static/css/ui-foundation.css`.
- **Legacy `_base.htm` untouched (yet).** Existing controls still rely on Bootstrap-era templates; migration will start after the component API stabilizes.

## Key Files
| Area | Path | Notes |
| --- | --- | --- |
| Inventory | `docs/ui-docs/control-ui-styling/control-inventory.md` | Source of truth for control inputs, routes, and JS wiring. Update in sync with code changes. |
| Component spec | `docs/ui-docs/control-ui-styling/control_components.md` | Macro contracts, layout hierarchy, run-header guidance. |
| Blueprint | `wepppy/weppcloud/routes/ui_showcase/` | Flask blueprint for `/ui/components/` showcase. |
| Prototype template | `wepppy/weppcloud/templates/ui_showcase/component_gallery.htm` | Demonstrates shell + example fields. Expand with every new macro. |
| Pure shell | `wepppy/weppcloud/templates/controls/_pure_base.htm` | Block-based control structure (header, body grid, sidebar). |
| Macros | `wepppy/weppcloud/templates/controls/_pure_macros.html` | Early helper macros (`control_shell`, `text_field`, etc.). |
| CSS | `wepppy/weppcloud/static/css/ui-foundation.css` | Holds design tokens and new `.wc-control` styles. Extend here, not inline. |

## Active Workstream
1. **Pilot migration**  
   - Migrate a low-risk production control (e.g., `channel_delineation`) onto the Pure macros to validate metadata contracts and error handling.  
   - Capture lessons learned in `control-inventory.md` and update this AGENT guide.
2. **Define metadata contract**  
   - Decide which attributes controllers must expose (labels, unit hints, validation rules).  
   - Document the contract in `control_components.md` and retrofit NoDb controllers once agreed.
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
- Keep legacy `_base.htm` untouched until a new macro pattern is proven in the showcase and documented.
- When a control is migrated, update both `control-inventory.md` and this AGENTS file with progress/notes.
- Pure shell styling lives in `ui-foundation.css`; no inline styles in templates.
- Dark mode is explicitly out-of-scope for this iteration; stay focused on polishing the light theme tokens and contrast ratios.

## Open Questions
- Final macro signatures for table-oriented panels (landuse/soils summaries) and how to wrap dynamic controller-managed sections; defer decision until we port the first legacy control.
- Whether to expose additional global CSS variables for spacing/width adjustments beyond the current token set.

## Contact / Escalation
- Architectural questions: reference the Pure UI spec (`control_components.md`) first; if unclear, tag UI maintainers in GitHub issues.
- Showcase bugs or missing macros: open a ticket in the UI Components board and assign to the styling working group.

Stay within this doc for the latest guidance; update it whenever workflows or priorities shift.
