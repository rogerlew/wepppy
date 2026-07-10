# AgFields Backend Readiness

**Status**: Closed (2026-07-09)
**Timezone**: UTC

## Overview

This package makes the AgFields backend ready for the runs-page UI defined in `wepppy/nodb/mods/ag_fields/ui_control_layout.md`. The AgFields NoDb controller (`wepppy/nodb/mods/ag_fields/ag_fields.py`) is functionally complete as a Python-driven workflow, but it has no HTTP routes, no RQ tasks, and several contract gaps the UI spec depends on — including one outright bug: the module-level `run_wepp_subfield` references `self.wepp_instance.wepp_bin`, a `NameError` that breaks every sub-field WEPP run.

The UI template and controller JS are explicitly not in this package; they follow in a separate implementation package once this backend surface exists. The spec's §9 (route and job contract) and §10 (backend prerequisites) are the authoritative requirements list; this package exists to burn down §10 and stand up §9.

## Objectives

- Fix the `run_wepp_subfield` `wepp_bin` self-reference so sub-field WEPP runs execute, with a regression test that fails against the current code.
- Add the three RQ job families (build-subfields chain, plant-db processing, run-wepp) with status-channel publishing and the contractual job keys `agfields_build_subfields`, `agfields_plantdb`, `agfields_run_wepp`.
- Stand up the run-scoped HTTP surface from spec §9: boundary upload, schema confirm (route-enforced atomicity), plant-db upload, plant-file inventory and delete, rotation-mapping read/save, run-wepp enqueue, clear runs/outputs, sub-fields overlay resource, and the state snapshot.
- Close the controller contract gaps: re-upload staleness signals, structured `validate_rotation_lookup` results, deterministic plant-file replace/delete semantics, persisted invalid-plant-file reasons, case-insensitive `.man` extraction, and the JSON-to-`rotation_lookup.tsv` writer.
- Provide the readiness checks the state snapshot needs: observed-climate readiness, watershed abstraction presence, parent-WEPP artifact presence.

## Scope

### Included

- `wepppy/nodb/mods/ag_fields/ag_fields.py` controller changes enumerated in spec §10.
- New RQ task module for AgFields under `wepppy/rq/`.
- New run-scoped routes following the Treatments (`rq_engine/treatments_routes.py`, multipart upload + enqueue) and Disturbed SBS (`rq_engine/upload_disturbed_routes.py`, sync upload) precedents, with `authorize_run_access` on all rq-engine routes.
- A weppcloud management-options source (id + description for the run's landuse mapping) for the rotation mapping modal, reusing existing management summary machinery where possible.
- Targeted pytest coverage: route contracts, RQ chain ordering, schema-confirm atomicity, mapping save round-trip through `CropRotationManager`, run-wepp failure payload naming the failed sub-field.
- Documentation refresh of `wepppy/nodb/mods/ag_fields/README.md` where behavior changes (plant-file semantics, staleness, new surface).

### Explicitly Out of Scope

- The UI template (`controls/ag_fields_pure.htm`), controller JS (`controllers_js/ag_fields.js`), runs-page wiring, and modal — a follow-on package.
- Feature registry maturity bump (`internal` → `experimental`) — happens when the UI ships.
- The "sub-fields as OFEs" watershed feature (documented future work, 0% complete).
- Exposing `first_year_only` truncation on the 2017.1 downgrade (stays hardcoded off per spec §10).
- Changes to Peridot, the sub-field abstraction algorithm, or WEPP management stack/synthesis logic beyond the `wepp_bin` parameter fix.
- Retrofitting historical run artifacts.

## Stakeholders

- **Primary**: WEPPpy maintainers for AgFields, RQ, and rq-engine route surface.
- **Reviewers**: NoDb/AgFields maintainers; route/auth reviewer for the new rq-engine endpoints.
- **Security Reviewer**: Codex; a dedicated review is required because the package adds uploads and queue wiring.
- **Informed**: UI implementation package (successor), AgFields end users via updated docs.

## Success Criteria

- [x] `run_wepp_subfield` accepts `wepp_bin` as a parameter; regression test proves a sub-field run reaches `run_hillslope` without `NameError`.
- [x] Build-subfields RQ job chains rasterize → abstract → polygonize under one job with status publishing; chain order covered by a test.
- [x] Plant-db RQ job processes an uploaded zip and its terminal event carries the valid/invalid summary, naming any aborting 2017.1 file.
- [x] Run-wepp RQ job wraps `run_wepp_ag_fields`; failure payload names `sub_field_id` and parent `field_id`.
- [x] All §9 routes exist, are run-scoped, and rq-engine routes call `authorize_run_access`; route contract tests pass.
- [x] Schema confirm is atomic at the route level: an invalid rotation accessor leaves `field_id_key` unchanged (tested).
- [x] Re-uploading a boundary GeoJSON produces staleness flags in the state snapshot per spec §4 (tested).
- [x] `validate_rotation_lookup` returns structured per-crop results and no longer prints.
- [x] Plant-file upload deterministically replaces same-named files; delete method exists; invalid files persist with reasons; `.man` matching is case-insensitive (all tested).
- [x] Rotation-mapping save writes `rotation_lookup.tsv` from a JSON payload and round-trips through `CropRotationManager` validation (tested).
- [x] State snapshot exposes everything spec §4 hydrates from, including the three readiness checks.
- [x] `tools/check_broad_exceptions.py --enforce-changed` passes; no unallowlisted broad handlers in new routes.
- [x] Module README updated; package closed with disposition of all review findings.

## Closure Summary

Completed the controller, RQ, authenticated HTTP, state/readiness, upload safety,
and documentation work required by the authoritative UI contract. The dedicated
security review passed with all findings resolved. The successor runs-page UI
package is unblocked; feature maturity remains `internal` until that control
ships.

The final focused set passed 52 tests, and the broader NoDb and OpenAPI suites
passed. The repository-wide suite stopped at an unrelated, independently
reproducible batch-runner baseline failure after 2,070 passing tests. No seeded
AgFields run was available for a real WEPP binary end-to-end execution at
closure; that limitation was closed on 2026-07-10 by the `sacral-self-discipline`
acceptance walkthrough (6,626 sub-field simulations under `wepp_dcc52a6` — see
`20260709_ag_fields_runs_page_ui/tracker.md`).

## References

- UI spec (authoritative requirements): `wepppy/nodb/mods/ag_fields/ui_control_layout.md` (§9, §10)
- Spec verification findings: `artifacts/2026-07-09_spec_verification_disposition.md`
- Module docs: `wepppy/nodb/mods/ag_fields/README.md`, `wepppy/weppcloud/routes/usersum/weppcloud/ag_field-mod.md`
