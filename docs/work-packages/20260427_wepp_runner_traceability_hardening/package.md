# WEPP Runner Traceability Hardening (Hillslope + Watershed)

**Status**: Done (2026-04-27, post-closure addendum updated 20:07 UTC)
**Timezone**: UTC

## Overview

This package hardens WEPP run traceability so operators can distinguish model faults from infrastructure faults quickly and with high confidence. It targets production pain observed on 2026-04-27, including watershed stderr close failures (`OSError: [Errno 116] Stale file handle`) and missing run-context provenance in non-hillslope execution logs.

The work is intentionally a single rollout: startup-context parity, binary identity logging, and prolonged D-state watchdog logging land together with one validation gate.

## Objectives

- Add startup traceability parity for `run_watershed` to match the practical context currently emitted by `run_hillslope` (`cmd`, run/error files, run directory, attempt context).
- Add binary identity logging (resolved executable path + stable hash/provenance fields) so every run log can be tied to an exact binary artifact.
- Add bounded D-state watchdog logging for long-running/stuck Linux process states in `run_hillslope` and `run_watershed`.
- Harden close-path logging in watershed runs so log-close infrastructure errors are explicit and classified.
- Add targeted regression tests for traceability output and watchdog behavior.
- Update operator-facing docs for new log fields and expected interpretation.

## Scope

### Included

- `wepp_runner/wepp_runner.py` instrumentation for:
  - `run_hillslope` (binary identity + D-state watchdog integration)
  - `run_watershed` (startup trace parity + binary identity + D-state watchdog + close-path diagnostics)
- Shared helper(s) in `wepp_runner/wepp_runner.py` for binary identity and watchdog telemetry.
- Targeted tests under `tests/wepp_runner/` for:
  - startup context logging
  - binary hash/provenance logging
  - watchdog emission behavior and no-op behavior when disabled/inapplicable
- Documentation updates for traceability operations and troubleshooting.
- Post-closure operator-directed release addendum:
  - build `wepp_260427` + `wepp_260427_hill` from `/workdir/wepp-forest`
  - keep `src/makefile` `-g/-fbacktrace` gfortran flags as permanent traceability enhancement
  - vendor release binaries + updated `wepp-forest` changelog into `wepppy`
  - document dirty-cycle guidance for capacity include files:
    - `src/pmxelm.inc`
    - `src/pmxhil.inc`
    - `src/pmxpln.inc`
    - `src/pntype.inc`

### Explicitly Out of Scope

- `run_flowpath`.
- Single-storm paths (`run_ss_batch_hillslope`, `run_ss_batch_watershed`, and related single-storm templates/runners).
- WEPP model/science behavior changes.
- Additional WEPP binary/science changes beyond the operator-requested `wepp_260427` release addendum above.
- RQ route/schema contract changes outside existing runner exception propagation behavior.

## Stakeholders

- **Primary**: WEPPcloud operators and maintainers triaging production run failures.
- **Reviewers**: `wepp_runner` maintainers and RQ/operations maintainers.
- **Security Reviewer**: Optional (not required by default triage; invoke if implementation expands attack surface).
- **Informed**: Incident responders, release managers, and ablation-campaign maintainers.

## Success Criteria

- [x] `run_watershed` emits a startup trace line with command and run-path context comparable to `run_hillslope`.
- [x] `run_hillslope` and `run_watershed` logs include binary identity fields sufficient to tie execution to an exact artifact.
- [x] Prolonged D-state watchdog logging is available, bounded, and does not break normal runs.
- [x] Watershed close-path failures are logged with explicit infrastructure context (instead of opaque generic failure signatures).
- [x] Targeted regression tests cover the new traceability behavior and pass.
- [x] Docs explain new log fields, watchdog toggles, and triage interpretation.

## Dependencies

### Prerequisites

- Current `run_hillslope` trace format in `wepp_runner/wepp_runner.py` as baseline behavior.
- Incident context from 2026-04-27 production failures (NFS stale-handle close-path and long-run diagnostics).

### Blocks

- Faster incident disposition for ambiguous "model vs infrastructure" run failures.
- Reliable binary provenance tracking in production run diagnostics.
- Future automated failure classifiers that depend on canonical run-trace fields.

## Related Packages

- **Related**: [20260424_rq_worker_nodb_cache_hardening](../20260424_rq_worker_nodb_cache_hardening/package.md)
- **Related**: [20260411_rq_operator_experience_hardening](../20260411_rq_operator_experience_hardening/package.md)
- **Related**: [20260422_jagged_hyperpigmentation_hillslope_ablation_queue](../20260422_jagged_hyperpigmentation_hillslope_ablation_queue/package.md)

## Timeline Estimate

- **Expected duration**: 2-4 focused sessions
- **Complexity**: Medium
- **Risk level**: Medium (touches production execution/logging path)

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: Scope is observability and error-traceability in existing runner subprocess flows. No new public routes, auth, secrets handling, upload surfaces, or expanded external egress are introduced.
- **Security review artifact**: `N/A`

## Hardening and Callus Softening (Required for incident/remediation packages)

- **Failure signature(s)**:
  - `OSError: [Errno 116] Stale file handle` surfaced during watershed stderr close (`_log.close()`), causing job failure classification ambiguity.
  - Watershed runs lacked startup trace parity (`cmd` and run-file context), slowing binary/input attribution during incidents.
  - No built-in D-state telemetry for long-running/stuck executions.
- **Related prior hardening efforts**:
  - [20260424_rq_worker_nodb_cache_hardening](../20260424_rq_worker_nodb_cache_hardening/package.md)
  - [20260411_rq_operator_experience_hardening](../20260411_rq_operator_experience_hardening/package.md)
- **Health signals**:
  - Incident triage can identify binary, command, and run-path context from a single `*.err` file.
  - Watershed close-path failures are explicitly classified with infrastructure context.
  - Watchdog log markers appear for prolonged D-state conditions and are absent on healthy runs.
- **Danger signals**:
  - Excessive log noise or heavy per-line hashing overhead.
  - Non-deterministic hash fields that cannot be correlated across runs.
  - Watchdog behavior causing subprocess interference or false positives.
- **Observation window**: 14 days after merge/deploy.
- **Temporary calluses introduced**:
  - Optional watchdog polling via env configuration; keep default conservative and revisit after observation window.
- **Callus softening hypothesis (if applicable)**:
  - If watchdog produces low-value noise with no operational signal during the observation window, reduce default frequency or disable by default while retaining opt-in diagnostics.

## References

- `wepp_runner/wepp_runner.py` - current runner implementations and logging behavior.
- `wepp_runner/AGENTS.md` - binary lifecycle and observability expectations.
- `docs/binary-lifecycle.md` - binary vendoring/provenance context.
- `tests/wepp_runner/test_run_hillslope_retries.py` - existing hillslope traceability test baseline.
- `PROJECT_TRACKER.md` - package lifecycle tracking.

## Deliverables

- Updated runner instrumentation in `wepp_runner/wepp_runner.py`.
- Targeted regression tests in `tests/wepp_runner/`.
- Updated operator/developer docs describing new traceability fields and watchdog behavior.
- Package tracker and ExecPlan artifacts with validation notes.

## Follow-up Work

- Extend traceability parity to currently out-of-scope run methods (`run_flowpath`, single-storm runners) in a separate package, if needed.
- Evaluate whether new fields should be mirrored into structured status-channel metrics.

## Closure Notes

Closed 2026-04-27 19:27 UTC.

Implemented the single-rollout scope in `wepp_runner/wepp_runner.py` for continuous `run_hillslope` and `run_watershed` only. `run_watershed` now logs startup context parity (`runs_dir`, `run_file`, `err_file`, `cmd`, `attempt=1/1`), both in-scope runners log cached binary identity fields, and both use a Linux best-effort D-state watchdog with bounded env-configurable emissions. Watershed cleanup now classifies close-path I/O failures, including `stale_file_handle` for `errno=116`.

Targeted regression coverage landed in `tests/wepp_runner/test_traceability_hardening.py` for watershed startup parity, binary identity fields and fallback behavior, watchdog emit/no-emit behavior, and stale-handle close diagnostics.

Validation recorded at closure:
- `wctl run-pytest tests/wepp_runner --maxfail=1` - `17 passed`, `2 warnings`.
- `wctl run-pytest tests/wepp/test_wepp_runner_outputs.py tests/wepp_runner --maxfail=1` - `18 passed`, `2 warnings`.
- Documentation lint and patch hygiene are recorded in `tracker.md`.

Post-closure addendum (2026-04-27 20:07 UTC):
- Built `/workdir/wepp-forest/release/wepp_260427` and `/workdir/wepp-forest/release/wepp_260427_hill` using `tools/build_wepp_dated_release.sh` with `TARGET_TAG=260427 COMPILER=/usr/bin/gfortran`.
- Preserved `src/makefile` gfortran traceability flags `-g -fbacktrace` (with `-O2` retained) as permanent default-lane behavior.
- Updated `/workdir/wepp-forest/change-log.md` top entry for `wepp_260427` with hashes, validation evidence, dirty include-file guidance, and explicit provenance marker `6bb872ca (dirty tree)`.
- Vendored release artifacts into:
  - `wepp_runner/bin/wepp_260427` (`sha256=5ba0b48fbdaca702e05205daf4b9ab674ba65247949b887c8af74ed4eb8c1b62`)
  - `wepp_runner/bin/wepp_260427_hill` (`sha256=bf9e54686580598090840b6225f58d4f9361f7df20884c7aca440bcb8a954826`)
- Synced vendored changelog copy at `wepppy/weppcloud/routes/usersum/vendor/wepp-forest/change-log.md`.

Review/disposition addendum (2026-04-27 20:12 UTC):
- Dispatched `reviewer` and `qa_reviewer` agents.
- Resolved in-scope release-provenance finding via dirty-tree changelog provenance annotation.
- Concurrent RQ-route/schema findings reported by subagents were classified as outside this package addendum scope and deferred to their owning package stream.

Post-closure review/disposition update (2026-04-27 19:41 UTC):
- `reviewer` and `qa_reviewer` reported medium risks for binary identity cache staleness and watershed close-path exception precedence.
- Both findings were dispositioned in code with added regression coverage in `tests/wepp_runner/test_traceability_hardening.py`.
- Revalidation after dispositions:
  - `wctl run-pytest tests/wepp_runner --maxfail=1` - `20 passed`, `2 warnings`.
  - `wctl run-pytest tests/wepp/test_wepp_runner_outputs.py tests/wepp_runner --maxfail=1` - `21 passed`, `2 warnings`.
