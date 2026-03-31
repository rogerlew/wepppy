# Disturbed Panel UI Contract (Draft)

> Canonical successor: `docs/ui-docs/disturbed-panel-ui-contract.md`.

## Purpose
This document captures the implementation contract for the dedicated Disturbed modal requested for run-page controls. It is package-local working guidance for implementation in `docs/work-packages/20260330_disturbed_panel_modal/` and should be promoted to canonical docs after implementation stabilizes.

## Entry Point and Placement Contract
- Run-page More menu adds a `Disturbed` entry alongside `Browse`, `PowerUser`, and `Change Units`.
- Disturbed modal uses the same modal shell dimensions and behavior pattern as Power User modal.
- Disturbed controls are removed from the Power User panel.

## Requested Layout Snapshot (Frozen)
The block below is an explicit capture of the requested layout so implementation does not rely on memory.

    More >
    Browse
    PowerUser
    Disturbed
    Change Units
    ...

    Disturbed Panel

    ## Landsoil Lookup Parameter Table

    [ Reset Base Landsoil Lookup Table ]
    [ Load Extended Landsoil Lookup Table ]
    [ Delete Extended Landsoil Lookup Table ]

    <div class="pu-action-feedback" data-disturbed-lookup-status="" role="status" aria-live="polite" aria-atomic="true"></div>

    ## Select Landsoil Lookup Table Resource

    ( ) Base    ( ) Disturbed

    ## Modify Landsoil Lookup Tables

    [ Modify Base Table ]
    [ Modify Extended Table ]
    [ Sync Base to Extended ]

    ## Help

    📄 WEPPcloud Calibration link text
    -> usersum/weppcloud/disturbed-land-soil-lookup.md

Notes for implementation:
- The snapshot above preserves the requested text literally, including `Disturbed` in the selector row.
- Route wiring still maps table selection to existing lookup variants (`base` and `extended`).

## Disturbed Modal Sections

### 1. Landsoil Lookup Parameter Table
Required action controls:
- `Reset Base Landsoil Lookup Table`
- `Load Extended Landsoil Lookup Table`
- `Delete Extended Landsoil Lookup Table`

Required feedback node:
- `div.pu-action-feedback[data-disturbed-lookup-status][role="status"][aria-live="polite"][aria-atomic="true"]`

### 2. Select Landsoil Lookup Table Resource
Required selector controls:
- Base table selector.
- Extended table selector.

Implementation note:
- Existing backend contract uses `lookup=base|extended`; selector should map directly to that query contract.
- Selector state must be persisted in Disturbed NoDb (`disturbed.nodb`) via a task endpoint, not local browser storage.
- Extended-only controls must be disabled when extended lookup does not exist.

### 3. Modify Landsoil Lookup Tables
Required action controls:
- `Modify Base Table` (opens `modify_disturbed?lookup=base`)
- `Modify Extended Table` (opens `modify_disturbed?lookup=extended`)
- `Sync Base to Extended` (server-side action to regenerate/refresh extended from current base)

### 4. Help
Required documentation link behavior:
- Link text rendered through helper with prefixed glyph: `📄 <label>`.
- Target document for this panel: `usersum/weppcloud/disturbed-land-soil-lookup.md`.
- Link should route through usersum endpoint, not hardcoded external docs host.

## API and Controller Contract

### Existing routes reused
- `POST /runs/<runid>/<config>/tasks/reset_disturbed`
- `POST /runs/<runid>/<config>/tasks/load_extended_land_soil_lookup`
- `GET /runs/<runid>/<config>/modify_disturbed?lookup=base|extended`
  - Explicit `lookup=extended` must hard-fail (`409 LOOKUP_VARIANT_UNAVAILABLE`) when extended lookup is absent.

### New routes required
- `POST /runs/<runid>/<config>/tasks/set_lookup_variant`
  - Payload: `{"lookup_variant":"base|extended"}`
  - Behavior: persist run-scoped active lookup variant in Disturbed NoDb for disk persistence.
- `POST /runs/<runid>/<config>/tasks/delete_extended_land_soil_lookup`
  - Behavior: remove extended CSV if present; return success when already absent (idempotent).
- `POST /runs/<runid>/<config>/tasks/sync_base_to_extended_land_soil_lookup`
  - Behavior: regenerate extended CSV from current base lookup state.

### Status feedback behavior
- All Disturbed modal actions should report status through the shared `data-disturbed-lookup-status` feedback node.
- Failed actions should surface existing error payload message text where available.
- `lookup_meta` should include `has_extended_lookup` so the controller can disable/enable extended-only controls deterministically.

## Jinja Usersum Link Helper Contract
A reusable helper should be introduced for control-page documentation links.

Minimum contract:
- Accept usersum route target (`category`, `filename`) and label text.
- Render final label with prefixed glyph (`📄`).
- Return URL generated via usersum route (`url_for('usersum.view_markdown', ...)`) or equivalent helper output usable in templates.

Rationale:
- Makes in-app docs links consistent and discoverable.
- Avoids scattered hardcoded usersum URLs in templates.

## Removal Contract for Power User Panel
Remove these disturbed-specific controls from Power User template:
- `Modify Disturbed Parameters`
- `Reset Disturbed Parameters`
- `Load Extended Disturbed Parameters`
- `Disturbed Parameters Doc`

All equivalent functionality must exist in Disturbed modal before removal is merged.

## Test Contract
Required validation coverage:
- Disturbed route tests for new delete and sync actions.
- Existing lookup variant tests remain green (`base`/`extended` behavior).
- Template/controller tests verify controls moved from Power User to Disturbed modal.
- Manual smoke check: Disturbed modal actions fire expected requests and update feedback node.

## Discoverability Contract
During package execution:
- This draft remains linked from package `package.md` and `tracker.md`.

At package close:
- Promote to canonical path: `docs/ui-docs/disturbed-panel-ui-contract.md`.
- Add cross-links from:
  - package closure notes,
  - Disturbed controller README section,
  - any relevant UI docs index.
