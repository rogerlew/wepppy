# SURF-03 Pure UI Archive Console Contract

**Status**: Closed 2026-07-29 UTC
**Package ID**: SURF-03
**Security impact**: `high`

## Purpose

Verify the authenticated archive console from authorized rendering through
list/create/restore/delete actions, active-job exclusion, RQ lifecycle,
filesystem confinement, terminal refresh, and restored-project navigation.

## Concise Intent Contract

Only an authenticated user authorized for the exact run and configuration may
load or mutate its archives. The route renders one server-owned config node
containing confined list, create, restore, delete, and project URLs. The client
lists archive metadata as text, uses server-provided download URLs, and never
constructs a filesystem path from rendered archive data.

Create submits one comment truncated to the existing 40-character limit.
Restore and delete require explicit confirmation and submit the exact listed
archive name with renewable rq-engine session authorization. Archive and
restore share one active-job slot; while either is active, create/restore/delete
actions remain disabled. Delete is synchronous and refreshes the list.

StatusStream and controlBase retain their existing archive-channel lifecycle,
bounded log, stacktrace, and idempotent terminal behavior. Completion or failure
refreshes authoritative list state; restore success exposes the confined
project link. Empty lists, conflicts, transport failures, stale job ids, and
worker failures remain visible and retryable. Archive creation, extraction,
deletion, and download remain confined to the authorized run's `archives`
directory.

## Scope

- `wepppy/weppcloud/routes/archive_dashboard/archive_dashboard.py`;
- `wepppy/weppcloud/routes/archive_dashboard/templates/rq-archive-dashboard.htm`;
- `wepppy/weppcloud/templates/controls/archive_console_control.htm`;
- `wepppy/weppcloud/static-src/js/archive_console.js` and built parity;
- rq-engine archive/restore/delete authorization, parsing, exclusion, and
  enqueue;
- archive/restore RQ workers and path/integrity/cache/lock safeguards;
- actual-render, executable-client, route, API, worker, and security evidence.

## Exclusions

SURF-04 owns forking. SURF-07 owns the general RQ dashboard. The dedicated
download service owns byte/range delivery after WEPPcloud supplies its confined
archive URL. This package does not add an action, field, token class, route,
queue edge, archive format, comment limit, copy/extraction rule, default, or
compatibility alias.

## Acceptance

Actual renders prove exact run/config/list/API/project/script identity and
hostile-value escaping. The real client proves empty/populated lists, safe
hostile metadata, create/comment truncation, refresh, restore, delete,
confirmation cancellation, one active mutation, repeat initialization,
success/failure/stacktrace, and terminal refresh/navigation. Existing route,
API, and worker tests prove authorization, stale/active job handling, enqueue,
path traversal rejection, integrity/disk/lock/cache safeguards, and failure
triggers. A dedicated security review passes with no unresolved high or medium
finding.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Decision provenance captured**: yes; the operator directed SURF-03
  execution and the package preserves existing fields, limit, actions, and
  defaults.

## Related Packages

- **Depends on**: verified SHR-04A/04B and DOM-02; consumer evidence for
  deferred SHR-02/03A.
- **Related**: verified SURF-04 fork console and SURF-07 RQ dashboard.

## Security Review Gate

Archive management crosses run authorization, bearer/session tokens, archive
filenames and download URLs, destructive restore/delete actions, zip
extraction, filesystem replacement, locks/cache, and RQ job state. A dedicated
review is required at `artifacts/2026-07-29_security_review.md`.

## Outcome

Verified and closed. Direct actual-render and real-client evidence found one
request-window race: restore and delete did not disable every sibling mutation
before the server established the shared active job. The source and served
clients now enforce mutual exclusion, and route, API, worker, auth/security,
frontend, repository, graph, and documentation gates pass.

## SURF-03A Fork/Archive Serial Queue Amendment

The operator-approved bounded enhancement at
`../20260803_fork_archive_serial_queue/` routes archive-create and restore,
together with SURF-04 fork, to one `fork-archive` queue. Archive-create retains
its worker-start `.nodb` lock check. Restore adds the same lock-status check
after validation and immediately before destructive removal; an active lock
fails without deleting current files. Static console guidance states that work
may wait, archive creation observes project state when its worker begins, and
the project must not be edited while restore is queued or running.

Delete remains synchronous. Download, archive format, extraction rules,
submission authorization, response shapes, active-job markers, and archive-
console actions remain unchanged. No archive-console cancel button is added.
For `fork-archive` jobs canceled through an existing shared surface, authorized
project users may cancel while queued and started cancellation requires Admin
or Root. SURF-03 stays closed; SURF-03A implementation conformance is pending
its GOV-00A-M1G checkpoint ancestor.
