# Tracker - AgFields Runs-Page UI

> Living document tracking progress, decisions, risks, validation, and handoffs for the AgFields pure-CSS runs-page control implementation.

## Quick Status

**Timezone**: UTC
**Started**: Not started (scaffolded 2026-07-09 23:21 UTC)
**Current phase**: Backlog
**Last updated**: 2026-07-09 23:21 UTC
**Next milestone**: Milestone 1 — control template with stage panels and DOM hooks
**Security impact**: `low` — no new backend surface; browser client reuses existing rq-engine session bearer tokens
**Dedicated security review**: `no`
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Milestone 1: `ag_fields_pure.htm` — control shell, four stage panels, collapsibles, chips, DOM hooks per spec §6; rotation mapping modal per spec §5.
- [ ] Milestone 2: `ag_fields.js` — singleton bootstrap, state-snapshot hydration, job keys, status streams with poll fallback, delegated events, crop-year pattern suggestion, 409 handling.
- [ ] Milestone 3: Runs-page wiring — `show_ag_fields` flag, nav item, section include, modal include, feature-id/maturity label (registry bump to `experimental`).
- [ ] Milestone 4: Map overlay — `addGeoJsonOverlay` registration against the overlay resource endpoint with rebuild refresh.
- [ ] Milestone 5: Jest suites per spec §12.1; `wctl run-npm lint` / `wctl run-npm test` green.
- [ ] Milestone 6 (acceptance): manual four-stage walkthrough on a fresh small-watershed `ag-fields` project (created by Roger); closes this package's acceptance and the backend package's real-binary E2E limitation; Playwright walkthrough (spec §12.2) recorded here if automated at this time.

### In Progress
- [ ] None.

### Blocked
- [ ] None. (Milestone 6 waits on a fresh AgFields project; Milestones 1-5 have no external dependencies.)

### Done
- [x] Package scaffold created with package brief, tracker, active ExecPlan, and root tracker registration (2026-07-09 23:21 UTC).

## Timeline

- **2026-07-09 23:21 UTC** - Package scaffolded as the successor to `20260709_ag_fields_backend_readiness` (closed same day). Sequencing decision: UI ships first, then a fresh project (copacetic-note no longer exists) provides the acceptance walkthrough that also closes the backend package's real-binary E2E gap.

## Decisions Log

### 2026-07-09: UI before fresh-project creation
**Context**: No seeded AgFields project exists; both the UI and the backend's real-binary E2E need one. The project could be created first (validating the backend by scripting JWT routes) or after the UI ships.

**Decision**: Implement the UI first. A single manual walkthrough on the new project then validates UI, backend routes, Peridot on a fresh watershed, and the real WEPP binary in one pass — no throwaway API scripting. UI development itself needs no seeded data (Jest + fixture-driven hydration). Risk accepted: latent backend defects reachable only in real runs surface late, but they sit behind a tested HTTP contract, so fixes are internal and will not churn the UI.

### 2026-07-09: Backend defects found during UI work are findings, not scope
**Context**: The backend package is closed; UI integration is the first real consumer of its surface.

**Decision**: Defects surfaced by UI work are recorded here as findings and fixed in scoped follow-up commits referencing this package. This package's own scope stays template/controller/wiring.

## Validation

Planned gates (record command outputs as work proceeds):

- `wctl run-npm lint` and `wctl run-npm test` (Jest suites per spec §12.1)
- Targeted pytest for any `run_0_bp.py` template-context changes
- Acceptance walkthrough evidence (Milestone 6): stage-by-stage notes plus output listing under `wepp/ag_fields/output/`

## Handoffs

- Fresh AgFields project creation (Roger): small agricultural watershed; `ag-fields` config; observed climate years must match the boundary GeoJSON's crop-year columns; boundary file needs a literal `field_id` column; plant zip from the USDA rotation builder or weppcloud management ids for the mapping.
- On acceptance completion, update `20260709_ag_fields_backend_readiness` closure notes to record that the real-binary E2E limitation is closed.
