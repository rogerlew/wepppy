> Outcome (2026-03-29): Completed profile-driven UI contract + profile resolve route + universal zip/provenance packaging, then closed with stabilization fixes for final zip retention and download-link behavior.

# Features Export Profiles + Provenance Zip Packaging (E2E)

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current while work proceeds.

## Purpose / Big Picture

Enable reproducible Features Export requests and reusable artifact metadata by moving from ad hoc defaults to profile-driven controls and by shipping every artifact download as a zip bundle containing both payload outputs and replay/provenance files.

## Progress

- [x] (2026-03-28) Updated specification contract for profile UX and zip/provenance artifact packaging.
- [x] (2026-03-28) Added built-in profiles (`post-wepp.yml`, `prep-details.yml`) and profile helper module.
- [x] (2026-03-28) Updated run-page bootstrap/template/controller to support quick profile loads and profile-text load.
- [x] (2026-03-28) Added rq-engine profile resolve endpoint with canonical validation handling.
- [x] (2026-03-28) Refactored service artifact packaging to produce final zip bundle with payload + manifest/profile/provenance members.
- [x] (2026-03-28) Added manifest profile/provenance relpath fields and bumped cache export version marker.
- [x] (2026-03-28) Updated tests and passed targeted pytest/Jest validation matrix.
- [x] (2026-03-29) Fixed cleanup retention regression that could remove final zip artifacts and patched download-link rendering to avoid `_blank` tab opens.

## Surprises & Discoveries

- Writer implementations already produced deterministic per-layer/container members, which allowed service-level bundling without rewriting format writers.
- GeoPackage cache validation had to account for both file and zip artifact shapes after packaging contract expansion.
- Keeping `features_export:defaults:loaded` for preset profiles avoided downstream event contract churn.
- The new service-level cleanup step can delete the final artifact if the writer artifact path and final bundle path match and the retain set omits the bundle path.

## Decision Log

- Decision: Enforce the final artifact contract in service orchestration, not in each writer.
  Rationale: One packaging boundary avoids repeating profile/provenance logic across all writer classes.
  Date/Author: 2026-03-28 / Codex.

- Decision: Add a dedicated profile resolve endpoint instead of parsing YAML in browser code.
  Rationale: Server-side normalization guarantees planner-valid profile payloads and consistent validation errors.
  Date/Author: 2026-03-28 / Codex.

- Decision: Bump export cache version marker for packaging contract change.
  Rationale: Avoids stale cache reuse across incompatible artifact shapes.
  Date/Author: 2026-03-28 / Codex.

- Decision: Keep cleanup best-effort but explicitly retain final bundle path.
  Rationale: Prevent accidental deletion when writer output equals final bundle target, while preserving intermediate artifact cleanup behavior.
  Date/Author: 2026-03-29 / Codex.

## Outcomes & Retrospective

- Profile UX now supports:
  - quick built-in profile application,
  - pasted profile text loading,
  - clear-selection flow unchanged.
- Artifacts now ship as zip bundles with deterministic replay/provenance members.
- RQ-engine supports profile-text resolution and returns normalized request mappings.
- Targeted backend/frontend suites passed after contract/test updates.
- Download links now render as direct download anchors (no forced new-tab behavior), and zip retention regression coverage protects artifact availability.

## Implementation Plan

1. Update `specification.md` for profile and packaging contracts.
2. Add profile helper module and built-in profile documents.
3. Wire run-page bootstrap/template/controller for profile actions.
4. Add rq-engine profile resolve route.
5. Refactor service packaging + manifest/cache contracts.
6. Update regression tests and run targeted validations.

## Validation Commands

```bash
cd /workdir/wepppy
wctl run-pytest tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_manifest.py tests/microservices/test_rq_engine_features_export_routes.py tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_run_0_openet_admin_gate.py --maxfail=1
wctl run-pytest tests/nodb/mods/test_features_export_exporters.py tests/nodb/mods/test_features_export_manifest.py --maxfail=1
wctl run-npm test -- features_export
```
