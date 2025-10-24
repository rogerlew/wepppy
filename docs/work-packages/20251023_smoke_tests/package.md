# Smoke Tests & Profile Harness

**Status**: Open (2025-02-24)

## Overview
Establish a reusable Playwright-based smoke harness driven by YAML profiles (quick, rattlesnake, blackwood, earth). The work covers the `wctl run-smoke` command, profile loader, extended Playwright helpers, and supporting documentation so teams can get a fast health snapshot or exercise larger scenarios on demand.

## Objectives
- Parse smoke profile files (`tests/smoke/profiles/*.yml`) and expose a friendly CLI (`wctl run-smoke --profile <name>`).
- Expand the Playwright smoke suite to honor profile steps (map extent, landuse toggles, treatments, future flows).
- Support optional run root overrides (`SMOKE_RUN_ROOT`) to compare NFS vs `/tmp` vs `/dev/shm` performance.
- Grow coverage beyond the quick profile (Rattlesnake SBS, Blackwood larger watershed, Earth international datasets).
- Capture results (HTML report, traces) and document runbook for CI/staging.

## Scope
- CLI: Profile loading, env merge, flag overrides (run root, keep-run, base URL, etc.).
- Playwright: Action dispatcher functions and tagging to map profile steps to helpers.
- Profiles: Author quick baseline; scaffold future rattlesnake/blackwood/earth profiles.
- Docs: Update smoke README, AGENTS guidance, and tests README; reference new CLI usage.

## Out of Scope
- Full regression suite (beyond smoke) — left to future packages.
- Deep backend/test-support enhancements outside what profiles need (keep the blueprint minimal for now).

## Stakeholders
- Frontend team (maintains controllers & smoke flows)
- QA/ops (consumes smoke results in pipelines)
- Tooling maintainers (wctl integration)

## Success Criteria
- `wctl run-smoke --profile quick` provisions a run, executes the steps, and reports pass/fail within ~2 minutes.
- Additional profiles can be added by dropping YAML files without touching Playwright helpers.
- Documentation outlines how to create/modify profiles and interpret results.
- Smoke artifacts (HTML report, trace) saved under a predictable location for CI retrieval.

## Reference
- Profiles live under `tests/smoke/profiles/` (see `quick.yml`).
- Playwright suite: `wepppy/weppcloud/static-src/tests/smoke/run-page-smoke.spec.js`.
- Test support blueprint: `wepppy/weppcloud/routes/test_bp.py` (honors `SMOKE_RUN_ROOT`).
- Docs: `tests/README.smoke_tests.md`, `AGENTS.md` (Smoke Tests section).
