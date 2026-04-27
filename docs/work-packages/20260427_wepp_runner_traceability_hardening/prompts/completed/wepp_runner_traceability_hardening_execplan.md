# WEPP Runner Traceability Hardening (Hillslope + Watershed, Single Rollout)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, operators can inspect a single run stderr log and quickly answer three questions that currently take too long during incidents: which exact binary executed, which exact command/context launched it, and whether the process entered prolonged D-state before failure. The work also makes watershed close-path infrastructure faults explicit, reducing false attribution to WEPP model behavior.

The user requested one integrated rollout, so startup trace parity, binary identity fields, and watchdog telemetry ship together under one validation gate.

## Progress

- [x] (2026-04-27 19:15 UTC) Package scaffolded with `package.md` and `tracker.md`.
- [x] (2026-04-27 19:15 UTC) Scope constraints recorded: exclude flowpath and single-storm paths.
- [x] (2026-04-27 19:26 UTC) Implemented shared cached binary identity helper in `wepp_runner/wepp_runner.py`.
- [x] (2026-04-27 19:26 UTC) Added startup trace parity and close-path diagnostics in `run_watershed`.
- [x] (2026-04-27 19:26 UTC) Added D-state watchdog helper and integrated it with `run_hillslope` + `run_watershed`.
- [x] (2026-04-27 19:26 UTC) Added targeted `tests/wepp_runner/test_traceability_hardening.py` coverage.
- [x] (2026-04-27 19:27 UTC) Updated runner docs and package lifecycle fields.
- [x] (2026-04-27 20:07 UTC) Completed operator-requested post-closure release addendum (`wepp_260427` build + vendoring + dirty include guidance docs).
- [x] (2026-04-27 20:12 UTC) Dispatched `reviewer` + `qa_reviewer` and dispositioned addendum findings (dirty-tree provenance fixed; concurrent RQ findings deferred to owning scope).

## Surprises & Discoveries

- Observation: `run_hillslope` already emits startup context including `cmd`, but `run_watershed` does not emit equivalent startup metadata.
  Evidence: `wepp_runner/wepp_runner.py` current implementations at `run_hillslope` and `run_watershed`.
- Observation: watershed close-path uses an unguarded `_log.close()` path that can raise infrastructure-level I/O errors.
  Evidence: production incident signature (`OSError: [Errno 116] Stale file handle`) and current close logic in `run_watershed`.
- Observation: targeted tests can exercise all new traceability contracts without invoking real WEPP binaries by stubbing `subprocess.Popen`.
  Evidence: `wctl run-pytest tests/wepp_runner --maxfail=1` passed with `17 passed`, including startup parity, binary identity, watchdog, and close-path cases.
- Observation: release workflow remained deterministic with `/usr/bin/gfortran` and retained `-g/-fbacktrace` defaults while still passing watchlist and full pytest gates.
  Evidence: `/workdir/wepp-forest` build + `pytest` (`53 passed`) + watchlist (`12/12`) + reconciled-condenser replay success marker.

## Decision Log

- Decision: Ship both enhancement lanes (traceability + watchdog) in one rollout.
  Rationale: user request; reduces churn and avoids two production deployments.
  Date/Author: 2026-04-27 / Codex

- Decision: Keep `run_flowpath` and all single-storm runners out of scope.
  Rationale: user request and incident-focused scope minimization.
  Date/Author: 2026-04-27 / Codex

- Decision: Cache binary identity by resolved executable path for the process lifetime.
  Rationale: every run log needs deterministic binary identity, but repeated SHA256 hashing should not add avoidable overhead on worker processes.
  Date/Author: 2026-04-27 / Codex

- Decision: Implement the D-state watchdog as logging-only Linux `/proc` telemetry with env controls.
  Rationale: the package needs stall evidence without changing subprocess control, timeout, or kill behavior.
  Date/Author: 2026-04-27 / Codex

- Decision: Watershed close-path diagnostics classify and re-raise close failures instead of converting them to success.
  Rationale: preserving existing failure contracts avoids hiding infrastructure I/O errors while making stale-handle attribution explicit.
  Date/Author: 2026-04-27 / Codex

- Decision: Record and execute the binary release/vendoring request as a post-closure addendum under this same package.
  Rationale: operator explicitly requested inclusion in this package and the work directly extends traceability operations (debug-symbol permanence, binary provenance, dirty-include guidance).
  Date/Author: 2026-04-27 / Codex

## Outcomes & Retrospective

Closed 2026-04-27 19:27 UTC. Operators can now identify the run directory, run file, error file, command, binary path, binary SHA256, and prolonged D-state signals from in-scope runner stderr logs. Watershed close-path failures now emit explicit `close_path_failure` diagnostics with `classification=stale_file_handle` for the observed `errno=116` production signature while preserving the raised `OSError`.

The final implementation stayed within the requested scope: continuous `run_hillslope` and `run_watershed` only. `run_flowpath`, single-storm methods, and WEPP binary build/release work were not changed.

Targeted validation passed:

    wctl run-pytest tests/wepp_runner --maxfail=1
    # 17 passed, 2 warnings

    wctl run-pytest tests/wepp/test_wepp_runner_outputs.py tests/wepp_runner --maxfail=1
    # 18 passed, 2 warnings

Post-closure review/disposition pass (2026-04-27 19:41 UTC):

    reviewer + qa_reviewer findings: 2 Medium, 0 High
    - binary identity cache staleness after in-place binary replacement
    - watershed cleanup potentially masking a primary exception

Both Medium findings were fixed and revalidated with added regression tests:

    wctl run-pytest tests/wepp_runner --maxfail=1
    # 20 passed, 2 warnings

    wctl run-pytest tests/wepp/test_wepp_runner_outputs.py tests/wepp_runner --maxfail=1
    # 21 passed, 2 warnings

Post-closure release addendum (2026-04-27 20:07 UTC) executed in `/workdir/wepp-forest` and `wepppy`:

    TARGET_TAG=260427 COMPILER=/usr/bin/gfortran /workdir/wepp-forest/tools/build_wepp_dated_release.sh
    # produced release/wepp_260427 (sha256 5ba0b48f...) and release/wepp_260427_hill (sha256 bf9e5468...)

    /workdir/wepp-forest/tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/release/wepp_260427
    /workdir/wepp-forest/tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/release/wepp_260427_hill
    python /workdir/wepp-forest/tools/run_hillslope_watchlist.py --binary /workdir/wepp-forest/release/wepp_260427_hill
    pytest
    # watchlist 12/12 passed; pytest 53 passed

    /workdir/wepp-forest/release/wepp_260427 < pw0.run > /tmp/wepp_pw0_reconciled_260427_stdout.txt 2> /tmp/wepp_pw0_reconciled_260427_stderr.txt
    # success marker present; no parse/runtime error signatures

    tools/check_wepp_binary_provenance.sh wepp_runner/bin/wepp_260427 wepp_runner/bin/wepp_260427_hill
    tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_260427
    tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_260427_hill
    # all passed

Code/QA review disposition addendum (2026-04-27 20:12 UTC):
- `reviewer` + `qa_reviewer` findings were reviewed.
- Release-provenance ambiguity was resolved by marking `wepp_260427` changelog provenance as `6bb872ca (dirty tree)` in source and vendored changelogs.
- Concurrent RQ-route/schema findings in the dirty workspace were classified as out-of-scope for this release addendum and deferred to their owning package.

## Context and Orientation

`wepp_runner/wepp_runner.py` contains runner entrypoints for hillslope, watershed, flowpath, and single-storm variants. `run_hillslope` currently has richer startup trace logging and timeout instrumentation than `run_watershed`. `run_watershed` currently streams stdout to `pw0.err` but does not write a startup context header and does not protect close-path diagnostics when filesystem I/O fails.

`tests/wepp_runner/test_run_hillslope_retries.py` already validates parts of hillslope traceability. This package should add or extend tests under `tests/wepp_runner/` for watershed startup trace parity, binary identity logging, and watchdog behavior.

No queue wiring, public route handlers, or binary release vendoring are in scope.

## Plan of Work

Add two small helper layers in `wepp_runner/wepp_runner.py` and then apply them to in-scope runners.

First, add binary identity/provenance helper(s). The helper should resolve executable path deterministically and compute an operator-useful identity payload (at minimum resolved path + SHA256 digest), with bounded overhead and clear fallback behavior when metadata cannot be read.

Second, add a watchdog helper for prolonged Linux D-state. The helper should be best-effort and bounded: poll interval, consecutive-threshold tracking, and concise log emission. It must never interrupt the child process and should degrade to no-op on unsupported environments.

Then wire helpers into `run_hillslope` and `run_watershed`, preserving current success/error contracts. For watershed, add startup context parity logging and explicit close-path diagnostics around `_log.close()` and any final stream cleanup.

Finally, add/adjust tests and update docs that describe run-log semantics.

## Concrete Steps

Run from `/workdir/wepppy`.

1. Edit runner helpers and in-scope methods:

    rg -n "def run_hillslope|def run_watershed" wepp_runner/wepp_runner.py
    $EDITOR wepp_runner/wepp_runner.py

2. Add/adjust tests:

    rg -n "run_hillslope|run_watershed" tests/wepp_runner
    $EDITOR tests/wepp_runner/<target_test_files>.py

3. Run targeted validation:

    wctl run-pytest tests/wepp_runner --maxfail=1

4. Run broader guard for touched surfaces:

    wctl run-pytest tests/wepp/test_wepp_runner_outputs.py tests/wepp_runner --maxfail=1

5. Lint docs and check patch hygiene:

    wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260427_wepp_runner_traceability_hardening
    git diff --check

## Validation and Acceptance

Acceptance requires all of the following observable outcomes:

- A watershed run log begins with a startup trace line that includes run directory, run file, err file, and command text.
- In-scope runner logs include binary identity fields (including SHA256 hash) that can be matched across incidents.
- When D-state conditions are simulated in tests, watchdog entries appear only after configured threshold conditions and remain bounded.
- Watershed close-path failure handling logs explicit infrastructure-context messages without obscuring final run status.
- Targeted `wepp_runner` tests pass.

## Idempotence and Recovery

The package is code-and-doc additive and safe to iterate. Re-running tests is idempotent. If watchdog defaults produce noisy output during validation, adjust thresholds in-code and repeat targeted tests before merge.

If implementation proves too noisy or risky, keep helper functions isolated and disable watchdog emission by default while preserving startup/provenance logging.

## Artifacts and Notes

Capture in tracker notes:

- Commands run and pass/fail outcomes.
- Representative log snippets showing startup context, hash/provenance fields, and watchdog output.
- Any discovered overhead measurements for hashing or watchdog polling.

## Interfaces and Dependencies

In `wepp_runner/wepp_runner.py`, keep existing public function signatures stable for:

- `run_hillslope(...)`
- `run_watershed(...)`

Add internal helpers only, with clear names and limited scope (for example binary identity collection and watchdog lifecycle). Any new environment variables must be documented in `wepp_runner/AGENTS.md` and reflected in this package tracker.

Do not modify:

- `run_flowpath(...)`
- `run_ss_batch_hillslope(...)`
- `run_ss_batch_watershed(...)`

## Revision Notes

- 2026-04-27: Initial active ExecPlan created from incident follow-up request; scoped to single rollout and constrained to hillslope + continuous watershed paths.
- 2026-04-27: Updated at closure with implemented helper decisions, validation results, outcomes, and package lifecycle notes before archiving to `prompts/completed/`.
- 2026-04-27: Post-closure code/QA review findings were dispositioned and revalidated; outcomes and validation transcripts updated.
