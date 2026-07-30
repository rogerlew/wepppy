# SURF-04 Pure UI Fork Console Contract

**Status**: Closed 2026-07-29 UTC
**Package ID**: SURF-04
**Security impact**: `high`

## Purpose

Verify the fork console from authorized rendering through CAP or authenticated
submission, exact option propagation, RQ tracking and cancellation, worker copy
behavior, terminal presentation, and reload recovery.

## Concise Intent Contract

The console is confined to the authorized source run and configuration.
Anonymous access to an eligible public run requires a successful section-owned
CAP token; authenticated access uses an rq-engine user/session token and never
stores either token. Submission carries the exact `undisturbify` and
`skip_wepp_runs_output` booleans rendered by the route and selected by the user.

One accepted submission yields one destination run and one tracked job.
Session-storage recovery is scoped by encoded source run and configuration and
retains only source/config/job/destination identifiers. Invalid, stale, or
cross-scope records are removed. Stream triggers accelerate reconciliation, but
polled job status remains authoritative for completion and failure. Cancellation
targets only the tracked job and uses the same renewable authorization boundary.

Status rendering retains the accepted bounded heartbeat/log behavior. Success
clears tracking and exposes an encoded destination link; failure and
cancellation remain visible and retryable without reflecting unsafe markup or
token contents. Missing CAP/runtime/transport/status dependencies fail visibly
and do not invent a successful fork.

## Scope

- `wepppy/weppcloud/routes/fork_console/fork_console.py`;
- `wepppy/weppcloud/routes/fork_console/templates/rq-fork-console.htm`;
- `wepppy/weppcloud/templates/controls/fork_console_control.htm`;
- `wepppy/weppcloud/static/js/fork_console.js`;
- rq-engine fork/cancel parsing and authorization;
- fork enqueue, worker copy/identity normalization, terminal triggers, and
  destination state;
- actual-render, executable-client, route, API, worker, recovery, and security
  evidence.

## Exclusions

SURF-03 owns archive/restore. SURF-07 owns the general RQ dashboard. SURF-01
owns public creation CAP behavior. This package does not add a fork option,
authorization rule, token class, storage field, route, queue edge, copy rule,
parameter default, or compatibility alias.

SURF-14A explicitly preserves this copy contract: a fork copies the source
run's Unitizer and WBT boundary-policy state, including the `warn`
compatibility value for legacy source state, and never resolves the destination
owner's account defaults. See `../20260729_user_preferences_wbt_boundary/`.

## Acceptance

Actual route/template renders prove exact run/config/default/token/CAP and asset
identity for authenticated, anonymous, query-selected, and hostile inputs. The
real client proves exact submit payloads, CAP isolation, repeat safety,
token-renewal behavior, scoped restore, cancellation, authoritative terminal
reconciliation, safe links/errors, and visible missing-runtime failures.
Existing API/RQ tests prove authorization, validation, enqueue, copy exclusions,
identity normalization, failure, and terminal behavior. A dedicated security
review passes with no unresolved high or medium finding.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Decision provenance captured**: yes; the operator directed SURF-04
  execution and the package preserves existing options, defaults, and status
  thresholds.

## Related Packages

- **Depends on**: verified SURF-01, SHR-04A/04B, DOM-02/03; consumer evidence
  for deferred SHR-02/03A.
- **Consumes**:
  `docs/work-packages/20260506_fork_skip_wepp_copy/` and
  `docs/adrs/ADR-0021-fork-console-status-backpressure-thresholds.md`.

## Security Review Gate

Forking crosses run authorization, public/CAP access, bearer/session tokens,
new-run ownership, cancellation, filesystem copy, persisted identity, and RQ
job boundaries. A dedicated review is required at
`artifacts/2026-07-29_security_review.md`.

## Outcome

SURF-04 closed with exact authenticated/anonymous/query-selected/hostile
rendering, 15 direct real-client tests, retained authorization/CAP/cancel/API/RQ
worker evidence, and a passing high-impact security review. The fork-copy
predecessor's deferred route-to-client propagation gap is closed. No production
repair, bundle rebuild, queue change, parameter change, or compatibility
behavior was required.
