# AgFields Runs-Page UI

**Status**: Closed (2026-07-10)
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
- Register the real control and maintain its current lifecycle disposition. It
  shipped initially as `experimental`, then returned to an internal beta
  (`maturity: internal`, `internal_reason: beta`, `min_role: dev`) for continued
  operational hardening.
- Jest coverage per spec §12.1; frontend gates (`wctl run-npm lint`, `wctl run-npm test`) pass.

## Scope

### Included

- `wepppy/weppcloud/templates/controls/ag_fields_pure.htm` (control + modal).
- `wepppy/weppcloud/controllers_js/ag_fields.js` and its Jest tests.
- `runs0_pure.htm` wiring and any `run_0_bp.py` template-context additions the include idiom requires.
- Feature registry maturity change and control-shell feature-id resolution.
- Browser client auth: reuse the existing rq-engine session bearer token mechanism (no new auth surface).
- Stage 4 follow-up: persisted AgFields WEPP executable selection, the
  `wepp_dcc52a6` new-project default, and automatic worker sizing in the browser.

### Explicitly Out of Scope

- Unrelated backend changes. Acceptance findings may be fixed as scoped,
  documented follow-ups; the Stage 4 executable persistence and propagation
  change is one such follow-up and is governed by ADR-0017.
- The full Playwright staged walkthrough (spec §12.2) — it needs a seeded AgFields project; it lands in the acceptance phase below.
- Sub-fields-as-OFEs, `first_year_only` exposure, and everything the spec's §13 open decisions defer.

## Acceptance Phase (after implementation)

The fresh acceptance project is `sacral-self-discipline`. Its initial Stage 2
CRS failure was corrected with a project-UTM (`EPSG:32611`) export, and the
walkthrough reached Stage 4. The first WEPP attempt exposed management synthesis
overflow; `20260710_management_rotation_synth_hardening` fixes that path and the
systematic Jim-interface residue-only `hmax=0` placeholder. A wired replay now
advances into simulation and exposes an independent zero-random-roughness
SIGFPE in `frcfac.for:184` under `wepp_260430` and `wepp_260606`. The exact
repaired p3733 replay completes under `wepp_dcc52a6`, now the new-project
AgFields default. The full browser-started project run subsequently completed
on 2026-07-10 and is recorded in `tracker.md`; acceptance is closed.

1. Use the small-watershed `sacral-self-discipline` project with its corrected
   project-UTM boundaries.
2. Drive all four stages through the UI: upload boundaries, confirm schema, build sub-fields, review overlay on the map, upload a plant zip from the USDA rotation builder, complete the mapping modal, run WEPP.
3. This single walkthrough simultaneously closes this package's UI acceptance AND the backend package's recorded limitation (no real-WEPP-binary end-to-end run).

The walkthrough is deliberately the last gate: it validates UI, backend, Peridot-on-fresh-watershed, and the real binary in one pass instead of scripting the JWT route surface separately.

## Stakeholders

- **Primary**: WEPPpy maintainers for weppcloud templates/controllers.
- **Reviewers**: UI review against the spec's Design Mandate and copy rules; accessibility check per spec §11.
- **Security Reviewer**: Not dedicated — no new backend surface; browser client uses existing session tokens. Revisit if scope grows.
- **Informed**: AgFields end users (usersum docs already describe the workflow).

## Success Criteria

- [x] Four-stage control renders per spec §2 wireframe with all §6 DOM hooks; no backend method names appear in labels or instructions.
- [x] Stage gating and staleness render exclusively from the state snapshot; disabled primary buttons always have an adjacent explanatory chip.
- [x] Crop-year pattern auto-detection handles the three spec outcomes (single candidate, multiple, none → collapsible auto-expands with per-year table).
- [x] Rotation modal round-trips mapping read/save, renders per-row server errors without closing, and supports partial saves.
- [x] Job lifecycle: enqueue → stream attach → terminal event → snapshot re-hydration works for all three job families; 409 conflict keeps the existing stream.
- [x] Sub-fields overlay appears via "Show on Map" and refreshes after a rebuild.
- [x] The real registry control is wired; its current lifecycle is internal
  beta and Dev-role only, and the shell renders the Internal label.
- [x] Jest suites per spec §12.1 pass; `wctl run-npm lint` and `wctl run-npm test` pass.
- [x] Boundary rasterization accepts unlabeled coordinates in the exact project UTM grid, retains WGS84/correctly declared reprojection support, and reports the required project CRS/bounds for ambiguous projected input.
- [x] Acceptance walkthrough on a fresh small-watershed project completes all four stages and produces sub-field outputs under `wepp/ag_fields/output/` with a real WEPP binary.

## Closure Summary

Milestones 1-5 were implemented on 2026-07-09: the four-stage template and modal, the `AgFields` singleton controller, dynamic and initial runs-page bootstrap wiring, authenticated rq-engine overlay loading through `MapController.addGeoJsonOverlay`, registry promotion to `experimental`, and Jest/Python regression coverage.

The acceptance walkthrough on `sacral-self-discipline` (2026-07-10) surfaced and drove four real fixes: unlabeled project-UTM boundary handling with actionable CRS errors, rotation-synthesizer scenario canonicalization against WEPP's 20-plant limit (`20260710_management_rotation_synth_hardening`, ADR-0016), the Stage 1 current-file display, and the AgFields-owned WEPP executable defaulting to `wepp_dcc52a6` (ADR-0017). The completed run produced 6,626 sub-field simulations (46,382 output files) under the `wepp_dcc52a6` executable; the maintainer validated the interface. Acceptance evidence and one filed follow-up (persisting `_wepp_bin` on the pre-ADR-0017 acceptance project) are recorded in `tracker.md`. This walkthrough also closes the backend package's real-binary E2E limitation.

A post-close projection UX follow-up makes the upload contract visible at the decision point: Stage 1 names the preferred project EPSG, accepted WGS84 input, and metadata requirement for other projected CRSs. Runs-page and report headers show the assigned project projection as an `EPSG:<srid>` pill and omit it before map assignment.

The canonical UI specification was reconciled after acceptance so it describes the snapshot-driven lifecycle, current DOM/route contracts, management-ingestion hardening, AgFields-owned executable, and recorded validation rather than the package's original prospective design state. On 2026-07-11 the feature was reclassified from user-visible experimental to an internal beta (`min_role: dev`) while operational hardening continues; this changes registry visibility only and does not alter existing project data or the implemented control.

A final Stage 2 simplification removes the redundant "Show on Map" action: current sub-fields load automatically after hydration and successful builds, while the shared map layer control hides and restores the retained overlay registration.

The layer re-show path reconstructs a fresh Deck descriptor from the retained remote GeoJSON data rather than reusing a finalized hidden descriptor, so checking `AgFields Sub-fields` displays it again without another authenticated download.

AgFields is also integrated with preflight through additive `TaskEnum.run_ag_fields` and checklist key `ag_fields`. The 🌽 indicator appears only after a successful current Stage 4 run; AgFields mutations/jobs invalidate it, and upstream freshness is enforced by `preflight2`. The durable contract is documented in `docs/ui-docs/control-ui-styling/preflight_behavior.md`.

## References

- UI spec (authoritative): `wepppy/nodb/mods/ag_fields/ui_control_layout.md`
- Backend package: `docs/work-packages/20260709_ag_fields_backend_readiness/`
- Route contract doc: `docs/schemas/rq-engine-agent-api-contract.md`
- Controller conventions: `wepppy/weppcloud/controllers_js/AGENTS.md`, `README.md`
