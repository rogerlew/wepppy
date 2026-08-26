# Deferred Job Retry Recovery

**Status**: Contract checkpoint review
**Stable ID**: SURF-20A / GOV-00A-M1J
**Started**: 2026-08-21 UTC
**Security impact**: High; authenticated submissions mutate RQ registries and enqueue replacement work

## Purpose

Users must be able to retry any controller action when its last recorded RQ job
is deferred. A retry must require no cancellation knowledge or extra UI step.
The submission path cancels and detaches the superseded deferred job before it
records the replacement job, preventing both permanent submission locks and a
later release of obsolete work.

## Scope

Included are the shared `controlBase` command-button rule and the exhaustive
backend/frontend inventory in `artifacts/deferred_retry_surface_matrix.md`,
covering every persisted user-facing controller hint writer, dependent
controller workflow, registry admission guard, and specialized poller/latch.
The package adds one shared conditional RQ cancellation
helper, verified controller/workflow association, graph-wide deferred cleanup,
exact job-id hint replacement, focused tests, generated controller assets, RQ
catalog validation, and user/developer documentation.

The 2026-08-23 correction additionally includes the finite dependency and
aggregate-status boundary in `artifacts/dependency_edge_matrix.md`: dependency
construction in WEPP, Culvert, Geneva, run-sync/migrations, WBT watershed,
DEM/channel build, SWAT, Omni, AgFields, and Batch; registered-tree status
aggregation in `wepppy/rq/job_info.py`; Fork rerun finalization; mixed-version
rollout; and their direct
RQ, route/admission, and controller regression evidence. It borrows only the
named dependency edges and polling rule from those workflow owners.

Excluded are authorization, CSRF, queue selection, worker algorithms,
queued/started/scheduled single-flight behavior, explicit
user cancellation endpoints, job-dashboard fields other than registered-tree
status precedence, and production job mutation during development.

## Success Criteria

- Every shared controller command becomes available when polling reports
  `deferred`.
- Every submission guard permits retry over a recorded deferred job.
- Every safely associated deferred node in the superseded workflow is removed
  from its deferred registry, detached from dependency/dependent sets, and
  canceled before the replacement ID is saved.
- Queued, started, and scheduled work retains existing duplicate protection.
- Missing, terminal, malformed, and legacy job hints remain retryable without a
  new user interaction.
- A concurrent deferred-to-queued/started transition is never canceled and
  resolves through the existing active-job conflict.
- Focused frontend/backend tests, generated-bundle checks, RQ graph validation,
  documentation lint, and broad pre-handoff gates pass.

## Related Work

This supersedes the deferred-admission portion of
`docs/work-packages/20260802_wepp_singleflight_tracking/` while retaining that
package's descendant tracking for queued, started, and scheduled jobs. It does
not weaken its protection against concurrently executing WEPP work.

## Parameterization and Data Compatibility

No model parameter, formula, threshold, unit, fallback heuristic, persisted
schema, response key, or column changes. No ADR or data compatibility plan is
required.

## Review Gates

The contract checkpoint requires two independent read-only reviews and a
standalone ancestor commit. Because this changes authenticated queue admission
and RQ registry state, final implementation requires dedicated correctness and
security review artifacts with no unresolved high or medium findings.
