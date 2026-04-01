# Disturbed Lookup Live E2E Work Package

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This work package delivers a deterministic, repeatable live E2E harness that proves both base and extended disturbed lookup table edits propagate into real `wepp/runs` artifacts on forked runs, without mutating the source run. After this change, one command will fork a fresh child run, patch lookup variants through the public API contract, run the required build and prep tasks, and emit machine-readable evidence that includes endpoint calls, row diffs, property and resource scope checks, artifact hashes, and explicit pass or fail assertions.

## Progress

- [x] (2026-03-31 04:38Z) Read required instruction sources: repo root `AGENTS.md`, `wepppy/nodb/AGENTS.md`, `tests/AGENTS.md`, and `docs/prompt_templates/codex_exec_plans.md`.
- [x] (2026-03-31 04:38Z) Baseline repository state and confirmed unrelated dirty files to avoid touching.
- [x] (2026-03-31 04:38Z) Mapped disturbed lookup route contracts (`lookup_meta`, `lookup_snapshot`, `tasks/modify_disturbed`, extended lookup tasks) and RQ trigger routes for fork, build, prep, and job polling.
- [x] (2026-03-31 04:38Z) Authored the initial live E2E ExecPlan draft and identified the existing in-progress harness files in `tests/nodb/mods/disturbed/live_e2e/`.
- [x] (2026-03-31 15:02Z) Fixed live test gating so the suite can be launched through the repo-standard `wctl run-pytest` wrapper with `--live-disturbed-lookup-e2e` instead of depending on a host env var that does not enter the container.
- [x] (2026-03-31 15:13Z) Hardened `tests/nodb/mods/disturbed/live_e2e/runbook.py` so it writes evidence artifacts incrementally and on failure, and so it can consume a dev token from `DISTURBED_LOOKUP_LIVE_E2E_DEV_TOKEN` when the host token file is not mounted inside the container.
- [ ] Validate the current harness against the live public run and fix any remaining contract or propagation gaps that appear under real execution.
- [ ] Finalize reusable live E2E client and executor modules for auth, fork lifecycle, lookup patching, task triggers, polling, artifact capture, and evidence serialization.
- [ ] Finalize manifest-driven vectors for base and extended patches, target property selection, and negative contract cases.
- [ ] Finalize the marker-gated live E2E suite so one command proves lifecycle, propagation, scoping, variant precedence, determinism, and negative contracts.
- [ ] Run the required validation commands and capture outcomes.
- [ ] Update this plan with evidence summary, reviewer or QA disposition, and final retrospective.

## Surprises & Discoveries

- Observation: The workspace already contains an untracked first-pass live E2E package and a prior `20260330` ExecPlan draft for the same feature area.
  Evidence: `git status --short` shows untracked `tests/nodb/mods/disturbed/live_e2e/`, `tests/nodb/mods/disturbed/test_disturbed_lookup_live_e2e.py`, and `docs/mini-work-packages/20260330_disturbed_lookup_live_e2e_execplan.md`.

- Observation: The existing first pass already uses the public session-token flow and the public fork CAPTCHA flow instead of hardcoded secrets.
  Evidence: `tests/nodb/mods/disturbed/live_e2e/runbook.py` mints `POST /rq-engine/api/runs/{runid}/{config}/session-token` tokens and redeems the fork CAPTCHA challenge before calling `POST /rq-engine/api/runs/{runid}/{config}/fork`.

- Observation: Disturbed lookup write contracts enforce optimistic concurrency with `if_match_sha256` and explicit error codes for stale writes.
  Evidence: `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py` returns `409` with code `STALE_LOOKUP` when the supplied hash does not match the current lookup snapshot.

- Observation: `wctl run-pytest` does not forward ad hoc host env vars into the `weppcloud` container, so env-only test gates skip unless the suite also exposes an explicit pytest option.
  Evidence: `DISTURBED_LOOKUP_LIVE_E2E=1 wctl run-pytest ...` still skipped the live suite until `--live-disturbed-lookup-e2e` was added.

- Observation: The default dev-token file path in `manifest.json` exists on the host but not inside the `weppcloud` container, so containerized runs silently fall back to anonymous session-token issuance unless a mounted file path or env token is supplied.
  Evidence: `/home/roger/weppcloud-dev-token.txt` exists on the host, but `docker compose ... exec weppcloud test -f /home/roger/weppcloud-dev-token.txt` returned `missing`.

- Observation: Before the latest patch, the runbook wrote `evidence.json` only after full success, which meant mid-run failures or long waits left no machine-readable breadcrumbs.
  Evidence: During a live run, `/tmp/wepppy-disturbed-lookup-live-e2e/` existed inside the container but contained no evidence files until the run completed.

## Decision Log

- Decision: Keep the live work package under pytest in `tests/nodb/mods/disturbed/live_e2e/` and use the test itself as the single-command runbook entrypoint.
  Rationale: The user asked for a CLI or test harness. Pytest already matches the repo’s marker-gated workflow and gives deterministic assertions and evidence paths without adding a second orchestration surface.
  Date/Author: 2026-03-31 / Codex

- Decision: Create a new dated ExecPlan at `docs/mini-work-packages/20260331_disturbed_lookup_live_e2e_execplan.md` instead of reusing the older `20260330` draft path.
  Rationale: The task explicitly requires the `YYYYMMDD` plan path and today’s date is 2026-03-31.
  Date/Author: 2026-03-31 / Codex

- Decision: Treat the existing dirty harness files as in-scope substrate, but avoid unrelated dirty files such as `code-quality-report.json` and `code-quality-summary.md`.
  Rationale: The harness and lookup files are directly relevant to the task; the code-quality files are not.
  Date/Author: 2026-03-31 / Codex

- Decision: Add a pytest option gate for the live suite and keep the env-var gate as a fallback.
  Rationale: The canonical `wctl run-pytest` wrapper does not pass arbitrary host env vars into the container, but it can pass pytest CLI arguments directly.
  Date/Author: 2026-03-31 / Codex

- Decision: Flush evidence artifacts incrementally and on exceptions instead of only after full success.
  Rationale: The deliverable requires machine-readable evidence even when the live run fails or must be retained for debugging.
  Date/Author: 2026-03-31 / Codex

## Outcomes & Retrospective

No milestone outcomes yet. This section will be updated after implementation and validation runs with delivered behavior, remaining gaps, and follow-up actions.

## Context and Orientation

The disturbed lookup edit surface lives in `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`. It exposes run-scoped snapshot and metadata reads plus lookup mutation routes:

- `GET /weppcloud/runs/{runid}/{config}/api/disturbed/lookup_meta?lookup=base|extended`
- `GET /weppcloud/runs/{runid}/{config}/api/disturbed/lookup_snapshot?lookup=base|extended`
- `POST /weppcloud/runs/{runid}/{config}/tasks/modify_disturbed?lookup=base|extended`
- `POST /weppcloud/runs/{runid}/{config}/tasks/load_extended_land_soil_lookup`
- `POST /weppcloud/runs/{runid}/{config}/tasks/sync_base_to_extended_land_soil_lookup`

The live orchestration surface lives in `wepppy/microservices/rq_engine/`. The current harness depends on:

- `POST /rq-engine/api/runs/{runid}/{config}/session-token`
- `POST /rq-engine/api/runs/{runid}/{config}/fork`
- `POST /rq-engine/api/runs/{runid}/{config}/build-soils`
- `POST /rq-engine/api/runs/{runid}/{config}/prep-wepp-watershed`
- `GET /rq-engine/api/jobstatus/{job_id}`

The downstream propagation logic lives in `wepppy/nodb/mods/disturbed/disturbed.py`, especially the soil replacement and management generation paths that feed `wepp/runs/pmetpara.txt`, `.sol`, and `.man` artifacts. The active first-pass harness lives in `tests/nodb/mods/disturbed/live_e2e/` and the live pytest entrypoint lives in `tests/nodb/mods/disturbed/test_disturbed_lookup_live_e2e.py`.

## Plan of Work

First, validate the existing harness against the live public run and identify exact failures instead of refactoring speculatively. Fixes should be limited to confirmed contract mismatches, missing propagation steps, incomplete evidence capture, or determinism issues.

Second, finalize the reusable client and manifest layer so the live runbook is entirely data-driven. The manifest will remain the single source of truth for the public source run, base and extended patch vectors, target lookup key, negative cases, and artifact selectors. The client will remain a small explicit wrapper over the discovered WEPPcloud and rq-engine APIs and will not add hidden fallback behavior.

Third, finalize the executor so it captures before and after lookup snapshots, selected property artifacts, endpoint traces, job completion status, deterministic signatures, and cleanup disposition. The executor must prove that the source run was not mutated and that non-target property output remains unchanged unless the observed design proves otherwise.

Fourth, run the required live suite and disturbed regression suites, then update this plan with concrete outcomes, evidence locations, and any unresolved risks.

## Concrete Steps

From `/workdir/wepppy`:

1. Run the focused lookup contract tests to make sure the local substrate still passes after any production lookup selection changes.
2. Run the live disturbed lookup pytest target with the required environment flag and inspect the first real failure against the public source run.
3. Patch only the failing harness or propagation code paths.
4. Re-run the focused live target until it passes twice on fresh forks with matching deterministic signatures.
5. Run the required disturbed safety-net suites and doc lint for this plan.

Expected focused live command shape:

    DISTURBED_LOOKUP_LIVE_E2E=1 wctl run-pytest tests/nodb/mods/disturbed/test_disturbed_lookup_live_e2e.py -m "requires_network and integration" --maxfail=1

## Validation and Acceptance

Acceptance is met when:

- One command runs the live harness end to end on a fresh fork.
- Evidence artifacts show endpoints called, lookup row diffs, selected property and resource, job completion, artifact hashes, and assertion results.
- Base lookup edits are proven in downstream `pmetpara.txt` and targeted `.sol` outputs.
- Extended lookup edits are proven in downstream management or soil-effective outputs used by WEPP prep.
- The source run fingerprints remain unchanged after the harness finishes.
- Two fresh-fork executions produce the same deterministic signature for the asserted artifacts.
- Negative contract checks return the expected error payloads.

Required validation commands:

    DISTURBED_LOOKUP_LIVE_E2E=1 wctl run-pytest tests/nodb/mods/disturbed/test_disturbed_lookup_live_e2e.py -m "requires_network and integration" --maxfail=1
    wctl run-pytest tests/nodb/mods/disturbed --maxfail=1
    wctl run-pytest tests/nodb/mods/test_treatments_build.py --maxfail=1
    wctl run-pytest tests/nodb/test_disturbed_management_overrides.py --maxfail=1
    wctl doc-lint --path docs/mini-work-packages/20260331_disturbed_lookup_live_e2e_execplan.md

## Idempotence and Recovery

Each live execution must create a new fork run and must not mutate the source run. The harness should be safe to re-run because it operates only on fresh fork run identifiers. When a live attempt fails, it should preserve evidence and, if cleanup cannot be performed safely, record exactly why the fork was retained. Polling must use bounded timeouts and explicit failure messages so retries start from a clean fork instead of guessing at partial state.

## Artifacts and Notes

Planned machine-readable evidence should include:

- the source and fork run identifiers plus config
- the endpoint call transcript with request and response summaries
- base and extended lookup target-row before and after snapshots plus lookup hashes
- targeted and control property artifact paths and hashes
- job identifiers and terminal status payloads
- deterministic signature payload and hash
- cleanup disposition and retained-run reason, if any

This plan currently records no reviewer or QA findings because no review pass has been performed yet. If no subagent or separate reviewer is used during this task, the final update will say so explicitly rather than implying a missing review.

## Interfaces and Dependencies

No new external dependencies are planned. The live harness should continue using the repository-standard stack: pytest, `requests`, the existing session-token route, the existing fork CAPTCHA contract, and the public disturbed and rq-engine APIs. Failures must remain explicit and must not silently downgrade to local file mutation or unauthenticated shortcuts.

---

Revision note (2026-03-31 / Codex): Created the required 20260331 ExecPlan path, carried forward the known contract context, and reset the living document to track the current validation-and-finish phase.
