# Specification – Smoke Harness MVP

## Objective
Define the minimal viable smoke test harness that:
1. Allows developers to run `wctl run-smoke --profile <name>` for consistent, automated UI smoke checks.
2. Supports profile-based configuration (run config, overrides, provisioning flags, run root, etc.).
3. Captures a basic run-through (map/StatusStream, landuse mode toggles, treatments presence) and lays the foundation for more extensive flows (Rattlesnake, Blackwood, Earth).

## Components

### 1. Profile Files (YAML)
Location: `tests/smoke/profiles/<profile>.yml`

Minimum fields:
```yaml
name: quick
description: "Small US watershed for fast health checks"
env:
  SMOKE_CREATE_RUN: "true"
  SMOKE_RUN_CONFIG: dev_unit_1
  SMOKE_RUN_OVERRIDES:
    general:dem_db: "ned1/2016"
  SMOKE_RUN_ROOT: "/tmp/weppcloud_smoke"
  SMOKE_KEEP_RUN: "false"
  SMOKE_BASE_URL: "http://localhost:8080"
steps:
  - description: load runs0 page and ensure controllers render
    spec: run-page-smoke.spec.js
    tags: [core]
  - description: map StatusStream sanity checks
    spec: run-page-smoke.spec.js
    focus: map
    tags: [map]
  - description: toggle landuse mode and verify UI
    spec: run-page-smoke.spec.js
    focus: landuse
    tags: [landuse]
  - description: treatments panel (if present)
    spec: run-page-smoke.spec.js
    focus: treatments
    tags: [treatments]
timeout: 120000
```

- `env` holds all `SMOKE_*` overrides, including optional `SMOKE_RUN_ROOT` for /tmp or /dev/shm.
- `steps` enumerates the actions the profile expects (optional `focus/tags` for spec filtering).
- `timeout` optional per-profile override (ms).

### 2. `wctl run-smoke` Command
- New command that accepts `--profile <name>` and optional overrides (`--run-root`, `--no-create`, `--keep-run`, `--base-url`, etc.).
- Workflow:
  1. Locate `tests/smoke/profiles/<profile>.yml`.
  2. Load env variables, merge CLI overrides.
  3. Ensure the backend has `TEST_SUPPORT_ENABLED=true` (either instruct the user or start the stack accordingly).
  4. Execute `npm run smoke` (or directly `npx playwright test`) with the resolved env.
  5. Collect exit code, standard output, and store Playwright artifacts (list reporter, HTML report, traces).

### 3. Playwright Spec Enhancements
- Existing `run-page-smoke.spec.js` already provisions runs (optional), checks map tabs, landuse toggles, and treatments.
- For MVP: ensure there are tags or focus hooks that align with profile steps (e.g., `test.describe` blocks with annotations or `test` names matching the steps).
- Support run root via `SMOKE_RUN_ROOT` (set before `POST /tests/api/create-run`). The blueprint should honor `os.environ.get("SMOKE_RUN_ROOT")` when deciding where to create directories.

### 4. Documentation
- `tests/README.smoke_tests.md` extended with profile instructions (done).
- Work package tracker references the spec and quick profile target.
- `AGENTS.md` references profile support and `SMOKE_RUN_ROOT`.

### 5. MVP Scope
- Provide one sample profile (`quick`) covering the existing Playwright spec (map, landuse, treatments).
- `wctl run-smoke --profile quick` loads the YAML and runs the suite.
- Manual override flags available for experimentation:
  - `--run-root PATH` – sets `SMOKE_RUN_ROOT` override.
  - `--keep-run` – sets `SMOKE_KEEP_RUN=true`.
  - `--no-create` – forces `SMOKE_CREATE_RUN=false`.
  - `--base-url URL` – overrides `SMOKE_BASE_URL`.

### 6. Future Profiles (post-MVP)
- `rattlesnake`: includes SBS workflows, disturbed/treatments-specific assertions.
- `blackwood`: larger run to observe performance and status streaming under heavier loads.
- `earth`: non-US datasets (Earth DB) for international use cases.
- Additional steps (climate upload stub, landuse build submission, WEPP run completion) can be added to the spec and referenced by tags.

## Open Questions
- Should `wctl run-smoke` automatically start the dev stack with `TEST_SUPPORT_ENABLED=true` if it’s not already running? (MVP may just warn.)
- How should we structure the Playwright spec(s) to support tag-based filtering (e.g., `@map`, `@landuse`)? Option: convert tests to use `test.describe` with `.tag()` or adopt Playwright test annotations.
- Where to store Playwright artifacts (HTML report, traces) for CI integration.
- For non-quick profiles, what cleanup strategy is required (longer runs may produce more output; we may want to keep artifacts for analysis).

---

Focus next: implement `quick` profile end-to-end (YAML, `wctl` command, Playwright harness updates) and iterate on longer flows afterwards.
