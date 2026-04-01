# Disturbed Lookup Live E2E Work Package

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This work package delivers a deterministic, repeatable live E2E harness that proves both base and extended disturbed lookup table edits propagate into real `wepp/runs` artifacts on forked runs, without mutating the source run. After this change, one command will fork a fresh child run, patch lookup variants through the public API contract, run the required build/run tasks, and emit machine-readable evidence that includes endpoint calls, row diffs, property/resource scope checks, artifact hashes, and explicit pass/fail assertions.

## Progress

- [x] (2026-03-31 04:38Z) Read required instruction sources: repo root `AGENTS.md`, `wepppy/nodb/AGENTS.md`, `tests/AGENTS.md`, and `docs/prompt_templates/codex_exec_plans.md`.
- [x] (2026-03-31 04:38Z) Baseline repository state and confirmed unrelated dirty files to avoid touching.
- [x] (2026-03-31 04:38Z) Mapped disturbed lookup route contracts (`lookup_meta`, `lookup_snapshot`, `tasks/modify_disturbed`, extended lookup tasks) and RQ trigger routes for fork/build/run/poll.
- [x] (2026-03-31 04:38Z) Created this ExecPlan and recorded initial constraints/discoveries.
- [x] (2026-04-01 04:06Z) Completed live harness/auth implementation in `tests/nodb/mods/disturbed/live_e2e/` with runtime `dev-agent` login + profile token mint flow, no dependency on `/home/roger/weppcloud-dev-token.txt`.
- [x] (2026-04-01 04:06Z) Finalized manifest/test wiring and negative contract checks for stale hash, partial rows, and missing columns.
- [x] (2026-04-01 04:06Z) Added one-command runbook documentation at `tests/nodb/mods/disturbed/live_e2e/README.md`.
- [x] (2026-04-01 04:34Z) Executed required non-live validations: disturbed module suite, treatments build, disturbed management overrides, and plan doc lint.
- [ ] (2026-04-01 04:34Z) Live deterministic E2E remains blocked by external fork-copy runtime on source run `assisted-weakness`; harness exits with explicit timeout evidence (`LiveApiError` in `waiting_for_fork`) after bounded wait.
- [x] (2026-04-01 04:34Z) Updated this plan with implementation outcomes, blocker evidence, and follow-up actions.

## Surprises & Discoveries

- Observation: Disturbed lookup write contracts enforce optimistic concurrency (`if_match_sha256`) and reject stale or malformed payloads with explicit error codes.
  Evidence: Route logic in `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py` and existing tests in `tests/weppcloud/routes/test_disturbed_bp.py`.

- Observation: Running CAP endpoint discovery on an authenticated browser session can return the non-CAP run page and miss `apiEndpoint` extraction.
  Evidence: Live run initially failed with `Could not discover CAP endpoint from /weppcloud/runs/assisted-weakness/disturbed9002_wbt/`; resolved by solving CAP with an anonymous client session and using minted bearer only for rq-engine/session-token calls.

- Observation: Source-run fork jobs for `assisted-weakness/disturbed9002_wbt` remain in `started` for multiple minutes and do not complete in practical CI/operator windows.
  Evidence: Live runs timed out waiting on fork job IDs such as `368808e6-1ce1-4ab1-a9e9-cd36f73e2088`; `rq-worker` process inspection showed long-running `rsync -av --progress` under `fork_rq`.

- Observation: Fresh runs created via `/weppcloud/tests/api/create-run` are not immediately suitable as source runs for this harness.
  Evidence: `build-soils` and `run-wepp-watershed` failed on new disturbed runs with missing prerequisite state (`WatershedNotAbstractedError`, missing outlet/baseflow prerequisites).

## Decision Log

- Decision: Implement the runbook as a pytest-driven live harness under `tests/nodb/mods/disturbed/live_e2e/`, with optional thin CLI wrapper only if needed for ergonomics.
  Rationale: User requested CLI or test harness; pytest integrates with marker gating, CI conventions, and deterministic assertions while still supporting one-command execution.
  Date/Author: 2026-03-31 / Codex

- Decision: Use runtime-issued session tokens via `/rq-engine/api/runs/{runid}/{config}/session-token` and not rely on static token files.
  Rationale: Required by prompt, and the provided static token currently fails signature validation.
  Date/Author: 2026-03-31 / Codex

- Decision: Keep source run immutable by enforcing fork-only execution and by adding explicit immutability checks in evidence.
  Rationale: Core acceptance criterion and safest way to guarantee no source mutations.
  Date/Author: 2026-03-31 / Codex

- Decision: Replace static token fallback with mandatory `dev-agent` runtime auth (`GET /login` -> `POST /login` -> `GET /profile` -> `POST /profile/mint-token`) and use minted bearer for session-token issuance.
  Rationale: Required by task constraints, keeps secrets out of source control, and aligns with current rq-engine auth contracts.
  Date/Author: 2026-04-01 / Codex

- Decision: Redact token-bearing response bodies (`/profile/mint-token`, `/session-token`) in endpoint transcripts.
  Rationale: Prevent evidence artifacts from storing bearer/session token values while preserving contract traceability.
  Date/Author: 2026-04-01 / Codex

- Decision: Add a hard fork wait cap (`180s`) even when manifest timeout is larger.
  Rationale: Prevent indefinite/very long live waits under heavy `fork_rq` copy behavior and force explicit, machine-readable blocker evidence.
  Date/Author: 2026-04-01 / Codex

## Outcomes & Retrospective

Implementation outcomes:

- Live harness/auth flow now uses the required `dev-agent` runtime login + mint path and no longer depends on host token files.
- Evidence schema includes endpoint transcript, lookup row/hash scaffolding, lifecycle assertions, determinism payload/signature logic, and artifact-hash fields for successful runs.
- Runbook documentation and marker-gated execution path are in place.

Validation outcomes:

- `DISTURBED_LOOKUP_LIVE_E2E=1 ... --live-disturbed-lookup-e2e ...` fails with explicit blocker evidence at fork wait (`LiveApiError: Timed out waiting for job ... last_status='started'`).
- Required non-live validations passed:
  - `tests/nodb/mods/disturbed` (71 passed, 1 skipped)
  - `tests/nodb/mods/test_treatments_build.py` (3 passed)
  - `tests/nodb/test_disturbed_management_overrides.py` (2 passed)
  - `wctl doc-lint --path docs/mini-work-packages/20260330_disturbed_lookup_live_e2e_execplan.md` (clean)

Remaining gap to full acceptance:

- End-to-end live propagation assertions (base/extended row mutations through WEPP outputs) are currently blocked by slow/non-terminating fork lifecycle on the configured source run.
- Smallest follow-up: provide or select a pre-prepared, fork-fast disturbed source run for `manifest.source_run` (or fix/replace slow fork copy path for this source run in environment operations).

## Context and Orientation

The disturbed lookup edit surface is in `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`. It exposes:

- `GET /runs/{runid}/{config}/api/disturbed/lookup_meta?lookup=base|extended`
- `GET /runs/{runid}/{config}/api/disturbed/lookup_snapshot?lookup=base|extended`
- `POST /runs/{runid}/{config}/tasks/modify_disturbed?lookup=base|extended` with `if_match_sha256`
- `POST /runs/{runid}/{config}/tasks/load_extended_land_soil_lookup`
- `POST /runs/{runid}/{config}/tasks/sync_base_to_extended_land_soil_lookup`

RQ engine orchestration lives in `wepppy/microservices/rq_engine/*`:

- fork: `POST /rq-engine/api/runs/{runid}/{config}/fork`
- token: `POST /rq-engine/api/runs/{runid}/{config}/session-token`
- build: `POST /rq-engine/api/runs/{runid}/{config}/build-landuse`, `build-soils`
- run/prep: `POST /rq-engine/api/runs/{runid}/{config}/prep-wepp-watershed` and/or `run-wepp-watershed`
- polling: `GET /rq-engine/api/jobstatus/{job_id}`

Disturbed propagation targets are generated by `wepppy/nodb/mods/disturbed/disturbed.py`, notably `pmetpara_prep()` and soil/management replacement workflows that emit `wepp/runs/pmetpara.txt` and `.sol` files.

## Plan of Work

The first implementation milestone adds a reusable live client and runbook executor module that performs authenticated API calls, fork management, polling, and artifact evidence capture with strict timeout/error contracts. The module will own request/response transcripts (sanitized), hash calculation, and before/after snapshot persistence.

The second milestone adds fixtures and manifest-driven vectors so base and extended lookup edits are data-driven. This includes explicit targeted lookup row keys, patch values, expected propagation points in `pmetpara.txt` and soil/management artifacts, and negative payloads for stale hash and invalid schema checks.

The third milestone adds marker-gated live tests that call the executor twice (fresh forks) to prove determinism and include property/resource scope checks by comparing targeted vs non-target properties. Tests will verify lookup variant precedence behavior (`lookup=base` vs `lookup=extended`) using both API metadata and output artifact evidence.

The fourth milestone documents one-command execution, required environment variables, retain-on-failure behavior, and cleanup expectations, then runs required validations and records outcomes.

## Concrete Steps

From `/workdir/wepppy`:

1. Add harness modules and fixture manifests under `tests/nodb/mods/disturbed/live_e2e/`.
2. Add marker-gated pytest suite under `tests/nodb/mods/disturbed/`.
3. Add runbook documentation under `docs/` and wire command examples.
4. Execute focused and required validation commands.
5. Update this plan with evidence summary and reviewer disposition.

Expected focused command shape:

    DISTURBED_LOOKUP_LIVE_E2E=1 wctl run-pytest tests/nodb/mods/disturbed/test_disturbed_lookup_live_e2e.py -m "requires_network and integration" --live-disturbed-lookup-e2e --maxfail=1 -s

## Validation and Acceptance

Acceptance is met when:

- A single command runs the live harness and succeeds end-to-end on a fresh fork.
- Evidence artifact includes endpoint transcript, lookup diffs, selected property/resource, job completion, artifact hashes, and assertions.
- Base and extended edits both propagate to downstream `wepp/runs` artifacts.
- Source run fingerprint/snapshots are unchanged after the test.
- Determinism check passes across two independent forks with equal asserted hashes.
- Negative contract checks return expected error shape/status.

Required validation commands:

    DISTURBED_LOOKUP_LIVE_E2E=1 wctl run-pytest tests/nodb/mods/disturbed/test_disturbed_lookup_live_e2e.py -m "requires_network and integration" --live-disturbed-lookup-e2e --maxfail=1 -s
    wctl run-pytest tests/nodb/mods/disturbed/test_disturbed_lookup_live_e2e.py -m "requires_network and integration" --maxfail=1
    wctl run-pytest tests/nodb/mods/disturbed --maxfail=1
    wctl run-pytest tests/nodb/mods/test_treatments_build.py --maxfail=1
    wctl run-pytest tests/nodb/test_disturbed_management_overrides.py --maxfail=1
    wctl doc-lint --path docs/mini-work-packages/20260330_disturbed_lookup_live_e2e_execplan.md

## Idempotence and Recovery

Each test execution creates a new fork run and never writes to the source run. The harness will support cleanup of fork runs on success and retain-on-failure for debugging. Polling uses bounded timeouts with explicit failure reasons so retries can rerun from a fresh fork without ambiguous partial state.

## Artifacts and Notes

Planned evidence outputs (machine-readable JSON plus Markdown summary) will include:

- run identifiers (`source_runid`, `fork_runid`, config)
- endpoint call log with method, URL path, status, and key payload fragments
- base and extended lookup row before/after snapshots and hashes
- selected artifact hashes (for example `wepp/runs/pmetpara.txt`, selected `.sol`)
- property/resource scope assertions and non-target control checks
- deterministic rerun comparison hashes
- cleanup actions and retained-run reason when applicable

Latest blocker evidence artifact:

- `/tmp/wepppy-disturbed-lookup-live-e2e/determinism_a_20260401042723/evidence.json`
- `/tmp/wepppy-disturbed-lookup-live-e2e/determinism_a_20260401042723/evidence.md`

## Interfaces and Dependencies

No new external dependencies are planned. Implementation will use existing repo/runtime libraries (`requests`, `hashlib`, `json`, pytest) and existing WEPPcloud/RQ-engine API contracts. Failures will be explicit; no silent fallback wrappers will be added.

---

Revision note (2026-03-31 / Codex): Initial plan authored from discovered route/test contracts and current environment constraints before implementation edits.
Revision note (2026-04-01 / Codex): Completed harness/auth/runbook implementation updates, executed required validations, and recorded the live fork-timeout blocker with concrete evidence and bounded failure behavior.
