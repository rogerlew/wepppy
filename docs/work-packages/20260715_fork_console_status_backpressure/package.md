# Fork Console Status Backpressure and Recovery

**Status**: Complete (2026-07-15)
**Timezone**: UTC

## Overview

Large fork jobs currently publish every `rsync --progress` line to the browser. A production fork completed normally in RQ while its background browser tab continued draining status messages and had not yet rendered the terminal state. This package removes high-volume copy output, preserves redundant completion signals, makes `/jobstatus/<job_id>` authoritative, and hardens the fork console against hidden-tab suspension and log-rendering backpressure.

## Objectives

- Replace per-line rsync telemetry with bounded stage, heartbeat, summary, and failure messages.
- Preserve both WebSocket completion triggers and RQ status polling while requiring terminal `/jobstatus/<job_id>` confirmation before the UI declares completion.
- Batch and bound StatusStream rendering without dropping terminal, error, or stage-transition messages when avoidable.
- Restore fork polling after tab resume or page reload and avoid idle subscriptions to the source-run fork channel.
- Document and test the updated worker and browser contracts.

## Scope

### Included

- Fork rsync command/output behavior in `wepppy/rq/project_rq_fork.py`.
- Shared StatusStream batching and bounded-retention primitives.
- Fork-console heartbeat presentation, visibility/focus recovery, session rehydration, and authoritative completion handling.
- Generated frontend bundles, focused backend/frontend tests, durable UI documentation, ADR, security review, and work-package records.

### Explicitly Out of Scope

- Job-scoped Redis channel names or Redis message persistence/replay.
- Changes to fork authorization, queue selection, dependency wiring, or cancellation contracts.
- A general redesign of all WEPPcloud console layouts.
- Production deployment to wepp1; this package delivers and validates the repository change only.

## Stakeholders

- **Primary**: WEPPcloud operators and users running large project forks.
- **Reviewers**: WEPPpy maintainers.
- **Security Reviewer**: Codex review pass, with maintainer review required before merge.
- **Informed**: RQ and WEPPcloud frontend maintainers.

## Success Criteria

- [x] Successful forks do not publish per-file or per-progress-line rsync output.
- [x] A running copy provides stage and replace-in-place heartbeat feedback.
- [x] Either completion signal causes prompt status confirmation, but only a terminal job-status response completes or fails the UI.
- [x] Status logs render in batches, remain bounded, and preferentially retain important lifecycle/error messages.
- [x] Hidden/resumed and reloaded fork-console tabs immediately reconcile the tracked job with `/jobstatus/<job_id>`.
- [x] The fork channel is disconnected when no job is tracked.
- [x] Focused tests, frontend lint/test, generated asset checks, and documentation lint pass; unrelated shared-worktree blockers for broad pytest and broad-exception enforcement are recorded in the QA review.

## Parameterization ADR Gate

- **Parameterization change present**: yes
- **ADR required**: yes
- **ADR link**: `docs/adrs/ADR-0021-fork-console-status-backpressure-thresholds.md`
- **Decision provenance captured**: yes

## Dependencies

### Prerequisites

- Existing hybrid StatusStream plus `controlBase` polling completion behavior.
- Existing fork worker and rsync helper tests.

### Blocks

- Safe production promotion of the fork-console backpressure fix.

## Related Packages

- **Related**: [`20260506_fork_skip_wepp_copy`](../20260506_fork_skip_wepp_copy/package.md)
- **Related**: [`20251023_statusstream_cleanup`](../20251023_statusstream_cleanup/package.md)

## Timeline Estimate

- **Expected duration**: One focused implementation session plus validation/review.
- **Complexity**: Medium.
- **Risk level**: Medium.

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The package changes an RQ worker subprocess invocation/output boundary. It does not add shell interpolation, routes, privileges, secrets, dependencies, or queue edges.
- **Security review artifact**: `docs/work-packages/20260715_fork_console_status_backpressure/artifacts/20260715_security_review.md`

## Hardening and Callus Softening

- **Failure signature**: RQ job `299b8d3c-bdca-42cd-abe2-506b6b410a8e` finished successfully after 56 minutes 53 seconds, while its hidden fork-console tab continued displaying queued rsync output and delayed terminal-state presentation.
- **Scope boundary**: Fix confirmed fork telemetry backpressure and recovery without changing fork data, authorization, or queue contracts.
- **Related prior hardening efforts**: The StatusStream cleanup package established the shared WebSocket helper; the fork copy package established the current rsync helper and fork UI flow.
- **Hypothesis**: If raw rsync output is replaced with bounded telemetry and browser rendering/reconciliation is hardened, terminal job state will appear promptly after RQ completion even after a tab is hidden.
- **Health signals**: bounded message counts, prompt terminal UI after status reports `finished`, successful reload recovery, and no per-file rsync payloads.
- **Danger signals**: lost completion/error notices, stalled polling after resume, unbounded worker output buffers, or unrelated fork-channel traffic on an idle console.
- **Observation window**: 14 days after production deployment.
- **Temporary calluses introduced**: Session-scoped job restoration and resume reconciliation; review after the observation window and retain only if they continue preventing stale UI.
- **Sunset criteria**: Remove a recovery hook only after tests and production observation show the same reliability without it.

## References

- `wepppy/rq/project_rq_fork.py` - rsync execution and telemetry.
- `wepppy/weppcloud/controllers_js/status_stream.js` - shared browser stream rendering.
- `wepppy/weppcloud/static/js/fork_console.js` - fork submission and lifecycle orchestration.
- `docs/ui-docs/weppcloud-project-forking.md` - authoritative behavior description.
- `docs/standards/hardening-lifecycle-standard.md` - incident-hardening requirements.

## Deliverables

- Implementation and regression tests for backend and frontend changes.
- Rebuilt `controllers-gl.js` and standalone `status_stream.js` assets.
- Updated forking and controller-foundation documentation.
- Completed ADR, security review, code review, QA review, tracker, and ExecPlan outcomes.

## Follow-up Work

- Consider job-scoped fork channels if shared source-run channels continue causing ambiguity after this package.
- Deploy through a separate wepp1 operator action, then review health and danger signals after the 14-day observation window ending 2026-07-29.

## Closure Summary

Completed all requested hardening items. Fork rsync now emits bounded stage, heartbeat, summary, and error telemetry. The browser retains both WebSocket and polling signals while treating `/jobstatus/<job_id>` as authoritative, batches and bounds log rendering, restores same-tab jobs after reload, reconciles on resume, and does not open an idle fork stream. Code, QA, and security review artifacts have no unresolved package findings. The full repository Python and broad-exception gates remain blocked only by unrelated WEPPpyo3 interchange changes already present in the shared worktree.
