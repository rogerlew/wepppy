# Tracker - AgFields Backend Readiness

> Living document tracking progress, decisions, risks, validation, and handoffs for AgFields backend readiness (routes, RQ tasks, controller contract gaps, `wepp_bin` bug fix).

## Quick Status

**Timezone**: UTC
**Started**: Not started (scaffolded 2026-07-09 21:47 UTC)
**Current phase**: Backlog
**Last updated**: 2026-07-09 21:47 UTC
**Next milestone**: Milestone 1 — `run_wepp_subfield` `wepp_bin` fix with regression test
**Security impact**: `low` — new run-scoped upload/enqueue routes; `authorize_run_access` required on rq-engine surface; zip extraction path-safety guards must be preserved
**Dedicated security review**: `no` (CLAUDE.md security checklist applies to new routes at review)
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Milestone 1: Fix `run_wepp_subfield` `self.wepp_instance.wepp_bin` `NameError` (`ag_fields.py:1046`) — pass `wepp_bin` as a parameter from `run_wepp_ag_fields`; regression test that fails pre-fix.
- [ ] Milestone 2: Controller contract gaps (spec §10): re-upload staleness signals; structured `validate_rotation_lookup`; plant-file replace/delete + persisted invalid reasons + case-insensitive `.man`; JSON→`rotation_lookup.tsv` writer; readiness helpers (observed climate, `dem/wbt/flovec.tif`, parent-WEPP `p*.sol`/`.cli`); `logger.warn` → `logger.warning`.
- [ ] Milestone 3: RQ tasks with job keys `agfields_build_subfields`, `agfields_plantdb`, `agfields_run_wepp`; status-channel publishing; build chain ordering rasterize → abstract → polygonize.
- [ ] Milestone 4: HTTP routes per spec §9 (Treatments/Disturbed-SBS precedents; `authorize_run_access`): boundary upload, atomic schema confirm, plant-db upload, inventory/delete, rotation-mapping read/save, run-wepp, clear, overlay resource, state snapshot, management options.
- [ ] Milestone 5: Targeted pytest coverage per package success criteria; `check_broad_exceptions --enforce-changed` clean.
- [ ] Milestone 6: Update module README; closure notes; root tracker lifecycle update.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Package scaffold created with package brief, tracker, active ExecPlan, spec-verification artifact, and root tracker registration (2026-07-09 21:47 UTC).

## Timeline

- **2026-07-09 21:47 UTC** - Package scaffolded from the UI spec's backend prerequisites (`ui_control_layout.md` §10) after Codex spec-verification review; findings dispositioned into the spec and captured as an artifact.

## Decisions Log

### 2026-07-09: Split backend readiness from UI implementation
**Context**: The UI spec depends on backend surface that does not exist (routes, RQ tasks) and on contract fixes (staleness, plant-file semantics, `wepp_bin` bug). Bundling backend and UI in one package would couple a large template/controller effort to backend churn.

**Decision**: This package delivers only spec §9/§10 backend work; the UI template/controller ships in a successor package against a stable surface.

### 2026-07-09: Treat the UI spec as the requirements document
**Context**: Requirements could be duplicated into this package and drift.

**Decision**: `wepppy/nodb/mods/ag_fields/ui_control_layout.md` §9 and §10 are authoritative; this package's docs reference rather than restate them. Spec changes during implementation must be made in the spec file first.

## Validation

Planned gates (record command outputs here as work proceeds):

- `wctl run-pytest tests/nodb/mods/` (AgFields controller tests, including new regression coverage)
- Targeted route/RQ tests added under `tests/`
- `python tools/check_broad_exceptions.py --enforce-changed`

## Handoffs

- Successor package: AgFields runs-page UI implementation (template, controller JS, runs-page wiring, modal) — blocked on this package.
- Feature registry maturity bump happens in the successor package when the control ships.
