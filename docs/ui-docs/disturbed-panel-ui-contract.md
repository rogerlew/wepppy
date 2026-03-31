# Disturbed Panel UI Contract

## Purpose
Define the canonical UI and route contract for the Disturbed modal that manages landsoil lookup tables for the Disturbed mod.

## Entry Point
- Run header `More` menu exposes `Disturbed` when `disturbed` mod is enabled.
- Modal id: `disturbedModal`.
- Modal sizing matches the PowerUser modal footprint (`90vw x 90vh` max envelope).

## Layout Contract

### 1. Landsoil Lookup Parameter Table
- `Reset Base Landsoil Lookup Table` button  
  `data-disturbed-action="reset-lookup"`
- `Load Extended Landsoil Lookup Table` button  
  `data-disturbed-action="load-extended-lookup"`
- `Delete Extended Landsoil Lookup Table` button  
  `data-disturbed-action="delete-extended-lookup"`
- Shared feedback node:
  - `.pu-action-feedback[data-disturbed-lookup-status]`
  - `role="status" aria-live="polite" aria-atomic="true"`

### 2. Select Landsoil Lookup Table Resource
- Radio controls:
  - Base: `value="base"`
  - Extended: `value="extended"`
- Selector hook: `data-disturbed-lookup-variant`.
- Controller refresh source of truth: `GET api/disturbed/lookup_meta`.
- Selection persistence:
  - Active lookup selection is persisted in Disturbed NoDb (`disturbed.nodb`) as run-scoped state.
  - Radio change contract: `POST /runs/<runid>/<config>/tasks/set_lookup_variant` with `{"lookup_variant":"base|extended"}`.
  - On refresh, server response remains authoritative (`lookup_variant` falls back to `base` if extended is unavailable).
- Extended-availability gating:
  - UI reads `has_extended_lookup` from `GET /runs/<runid>/<config>/api/disturbed/lookup_meta`.
  - When `has_extended_lookup=false`, disable:
    - Extended radio selector
    - `Modify Extended Table`
    - `Delete Extended Landsoil Lookup Table`
    - `Sync Base to Extended`

### 3. Modify Landsoil Lookup Tables
- `Modify Base Table` link: `modify_disturbed?lookup=base`
- `Modify Extended Table` link: `modify_disturbed?lookup=extended`
- `Sync Base to Extended` button  
  `data-disturbed-action="sync-base-to-extended-lookup"`

### 4. Help
- Help links should use the Jinja helper:
  - `usersum_doc_link(category, filename, label)`
- Helper renders a prefixed docs affordance in link text:
  - `📄 <label>`
- Disturbed panel doc target:
  - `usersum.view_markdown(category='weppcloud', filename='disturbed-land-soil-lookup.md')`

## Backend Route Contract
- Mutating (POST-only):
  - `POST /runs/<runid>/<config>/tasks/reset_disturbed`
  - `POST /runs/<runid>/<config>/tasks/load_extended_land_soil_lookup`
  - `POST /runs/<runid>/<config>/tasks/set_lookup_variant`
    - Persists the active lookup selector (`base|extended`) in Disturbed NoDb for run-scoped disk persistence.
  - `POST /runs/<runid>/<config>/tasks/delete_extended_land_soil_lookup`
    - Idempotent: returns success even if extended file is already absent.
  - `POST /runs/<runid>/<config>/tasks/sync_base_to_extended_land_soil_lookup`
    - Rebuilds extended lookup from current base lookup.
- Read-only:
  - `GET /runs/<runid>/<config>/modify_disturbed?lookup=base|extended`
  - `GET /runs/<runid>/<config>/api/disturbed/lookup_meta`

## Default Lookup Preference
- Resolver behavior:
  - If `lookup=base` is provided, honor base selection.
  - If `lookup=extended` is provided, require extended lookup to exist (otherwise return `LOOKUP_VARIANT_UNAVAILABLE`).
  - If no explicit lookup is provided, resolve from Disturbed NoDb `active_lookup_variant`.
  - Backward compatibility: if no persisted value exists, legacy default still applies (prefer extended when extended CSV exists; otherwise base).
- Deleting the extended table forces active selection to base.

## PowerUser Separation Contract
- Disturbed lookup controls are no longer rendered in `poweruser_panel.htm`.
- Disturbed-specific lookup lifecycle and docs link actions live only in the Disturbed modal.

## References
- Template: `wepppy/weppcloud/templates/controls/disturbed_modal.htm`
- Header menu: `wepppy/weppcloud/templates/header/_run_header_fixed.htm`
- Routes: `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`
- Controller: `wepppy/weppcloud/controllers_js/disturbed.js`
- Usersum helper: `wepppy/weppcloud/_jinja_filters.py`
