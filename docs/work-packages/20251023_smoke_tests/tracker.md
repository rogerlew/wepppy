# Tracker – Smoke Tests & Profile Harness

## Timeline
- **2025-02-24** – Work package created; smoke harness scoped; quick profile drafted.

## Task Board
### Ready / Backlog
- [ ] Implement `wctl run-smoke --profile <name>` loader (env merge, overrides).
- [ ] Teach Playwright suite to dispatch actions based on profile steps (`set_map_extent`, `toggle_landuse_mode`, etc.).
- [ ] Capture artifacts (HTML report, trace) and expose location in CLI output.
- [ ] Author additional profiles (`rattlesnake`, `blackwood`, `earth`) with representative steps.
- [ ] Add step scaffolding helper (optional) to ease new profile creation.

### In Progress
- None yet.

### Blocked
- None.

### Done
- [x] Initial quick profile drafted (`tests/smoke/profiles/quick.yml`).
- [x] Smoke harness spec documented (`prompts/active/smoke_harness_spec.md`).
- [x] Test-support blueprint honors `SMOKE_RUN_ROOT` overrides for provisioning.

## Decisions Log
- *2025-02-24* – Profiles will live under `tests/smoke/profiles/` with `env` + `steps`; `wctl run-smoke` will orchestrate Playwright by exporting those settings.

## Risks / Watch List
- Profiles must stay in sync with Playwright helper capabilities; document required actions.
- Provisioned runs may accumulate if `SMOKE_KEEP_RUN=true`; ensure CLI defaults to cleanup.
- CI runtime budget — keep quick profile under ~2 minutes.

## Verification Checklist
- [ ] `wctl run-smoke --profile quick` succeeds locally.
- [ ] Additional profile executes (e.g., rattlesnake).
- [ ] Smoke docs updated with CLI usage & profile authoring guide.
- [ ] CI job consumes the command and archives artifacts.

