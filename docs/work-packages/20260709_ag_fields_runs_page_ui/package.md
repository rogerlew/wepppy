# AgFields Runs-Page UI

**Status**: Backlog (scoped 2026-07-09)
**Timezone**: UTC

## Overview

This package implements the AgFields pure-CSS runs-page control specified in `wepppy/nodb/mods/ag_fields/ui_control_layout.md`. The backend surface it consumes shipped in `20260709_ag_fields_backend_readiness` (closed 2026-07-09): thirteen authenticated rq-engine routes, three RQ job families, and a state snapshot that carries all stage gating, staleness, and readiness signals. The spec is the authoritative design document — its §§1-8 define the four-stage layout, modal, DOM contract, and controller lifecycle; §9 documents the as-built route contract this UI binds to.

The spec's Design Mandate governs review: the UI presents four user decisions, not eight backend methods. Any layout that surfaces a backend method name as a button label fails review.

## Objectives

- Implement `templates/controls/ag_fields_pure.htm`: four numbered stage panels (Field Boundaries, Sub-field Delineation, Crop Managements, Run WEPP on Sub-fields) inside one `control_shell`, with the DOM hooks, collapsibles, chips, and copy rules from spec §§3, 6, 8.
- Implement the rotation mapping modal per spec §5 (self-gating top-level `wc-modal`, dependent selects, per-row validation rendering, unused-mappings group).
- Implement `controllers_js/ag_fields.js`: singleton bootstrap, hydration from `GET .../agfields/state`, the three contractual job keys, status-stream attach with poll fallback, delegated events, client-side crop-year pattern suggestion, and 409 `agfields_job_active` handling that keeps the current stream attached.
- Wire the runs page: `show_ag_fields` flag, `data-mod-nav` item, `data-mod-section` include near roads/geneva, modal include, feature-id resolution for the maturity label.
- Map overlay: register the sub-fields overlay through `addGeoJsonOverlay` against the overlay resource endpoint, refreshing after rebuilds.
- Bump the feature registry maturity from `internal` to `experimental` when the control ships.
- Jest coverage per spec §12.1; frontend gates (`wctl run-npm lint`, `wctl run-npm test`) pass.

## Scope

### Included

- `wepppy/weppcloud/templates/controls/ag_fields_pure.htm` (control + modal).
- `wepppy/weppcloud/controllers_js/ag_fields.js` and its Jest tests.
- `runs0_pure.htm` wiring and any `run_0_bp.py` template-context additions the include idiom requires.
- Feature registry maturity change and control-shell feature-id resolution.
- Browser client auth: reuse the existing rq-engine session bearer token mechanism (no new auth surface).

### Explicitly Out of Scope

- Backend changes. The backend package is closed; if UI work surfaces a backend defect, file it as a finding against this package and fix it in a scoped follow-up commit, not by silently expanding this package.
- The full Playwright staged walkthrough (spec §12.2) — it needs a seeded AgFields project; it lands in the acceptance phase below.
- Sub-fields-as-OFEs, `first_year_only` exposure, and everything the spec's §13 open decisions defer.

## Acceptance Phase (after implementation)

No seeded AgFields project exists (`copacetic-note` is gone), so final acceptance is a manual walkthrough on a freshly created project:

1. Create a small-watershed project from the `ag-fields` config (observed climate years must match the boundary file's crop columns).
2. Drive all four stages through the UI: upload boundaries, confirm schema, build sub-fields, review overlay on the map, upload a plant zip from the USDA rotation builder, complete the mapping modal, run WEPP.
3. This single walkthrough simultaneously closes this package's UI acceptance AND the backend package's recorded limitation (no real-WEPP-binary end-to-end run).

The walkthrough is deliberately the last gate: it validates UI, backend, Peridot-on-fresh-watershed, and the real binary in one pass instead of scripting the JWT route surface separately.

## Stakeholders

- **Primary**: WEPPpy maintainers for weppcloud templates/controllers.
- **Reviewers**: UI review against the spec's Design Mandate and copy rules; accessibility check per spec §11.
- **Security Reviewer**: Not dedicated — no new backend surface; browser client uses existing session tokens. Revisit if scope grows.
- **Informed**: AgFields end users (usersum docs already describe the workflow).

## Success Criteria

- [ ] Four-stage control renders per spec §2 wireframe with all §6 DOM hooks; no backend method names appear in labels or instructions.
- [ ] Stage gating and staleness render exclusively from the state snapshot; disabled primary buttons always have an adjacent explanatory chip.
- [ ] Crop-year pattern auto-detection handles the three spec outcomes (single candidate, multiple, none → collapsible auto-expands with per-year table).
- [ ] Rotation modal round-trips mapping read/save, renders per-row server errors without closing, and supports partial saves.
- [ ] Job lifecycle: enqueue → stream attach → terminal event → snapshot re-hydration works for all three job families; 409 conflict keeps the existing stream.
- [ ] Sub-fields overlay appears via "Show on Map" and refreshes after a rebuild.
- [ ] Registry maturity is `experimental`; the shell renders the label.
- [ ] Jest suites per spec §12.1 pass; `wctl run-npm lint` and `wctl run-npm test` pass.
- [ ] Acceptance walkthrough on a fresh small-watershed project completes all four stages and produces sub-field outputs under `wepp/ag_fields/output/` with a real WEPP binary.

## References

- UI spec (authoritative): `wepppy/nodb/mods/ag_fields/ui_control_layout.md`
- Backend package: `docs/work-packages/20260709_ag_fields_backend_readiness/`
- Route contract doc: `docs/schemas/rq-engine-agent-api-contract.md`
- Controller conventions: `wepppy/weppcloud/controllers_js/AGENTS.md`, `README.md`
