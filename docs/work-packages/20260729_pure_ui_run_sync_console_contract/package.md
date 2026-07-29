# SURF-05 Pure UI Run Sync Console Contract

**Status**: Closed 2026-07-29 UTC
**Package ID**: SURF-05
**Security impact**: `high`

## Purpose

Verify the Admin-only Run Sync dashboard from exact rendering through sync
submission, optional migration chaining, source-token handoff, status and
provenance presentation, RQ lifecycle, filesystem confinement, and terminal
navigation.

## Concise Intent Contract

Only an authenticated Admin may render or call Run Sync. The dashboard renders
server-owned submit/status URLs, target-root and channel defaults, and an
rq-engine user token scoped for enqueue. The client submits the exact source
host, run ID, optional config, target root, owner email, optional source-run
token, migration boolean, and archive-before boolean. Source-run tokens are
never rendered into status tables or retained in browser storage.

Run ID is required. One initialized dashboard owns one submit handler and one
status-refresh timer. During submission and active polling, another submission
must not be accepted. Errors remain visible and retryable. Job and migration
metadata render as text. Successful completion is idempotent, refreshes
authoritative status, and exposes a safely encoded local-run link; failure
retains status and stacktrace evidence.

The API enforces Admin and enqueue scope, parses native booleans, stores an
optional source token under a short-lived opaque Redis key, and passes only that
key to the worker. Migration work depends on successful sync. The worker
consumes the token once, confines output beneath the selected target root,
verifies downloaded content, records provenance without secrets, and publishes
terminal status.

## Scope

- Run Sync dashboard route, template, config, and token issuance;
- `controllers_js/run_sync_dashboard.js` and generated bundle parity;
- rq-engine Run Sync authorization, parsing, token handoff, enqueue, and status;
- Run Sync worker download, confinement, verification, provenance, and events;
- actual-render, direct-client, route, API, worker, and security evidence.

## Exclusions

SURF-08 owns migration-status UI. SURF-07 owns the general RQ dashboard.
Deployment, cross-host networking, migration implementation details, target-root
policy changes, new token classes, new fields, and new queue edges are excluded.

## Acceptance

Actual rendering proves exact Admin-only config, field/default, token, and
script identity with hostile values escaped. The real controller proves exact
payloads, boolean/default behavior, safe rows, validation, duplicate
initialization, submission exclusion, status refresh, terminal success/failure,
stacktraces, and safely encoded navigation. Existing route, API, and worker
tests retain authorization, token secrecy/consumption, dependency ordering,
download verification, provenance, confinement, and terminal evidence. A
dedicated security review passes with no unresolved high or medium finding.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Decision provenance captured**: yes; the operator directed SURF-05
  execution and this contract preserves existing fields, defaults, worker
  behavior, and queue topology.

## Related Packages

- **Depends on**: verified SHR-04A/04B; consumer evidence for deferred
  SHR-02/03A/03B.
- **Related**: verified SURF-07 RQ dashboard and SURF-08 migration status.

## Security Review Gate

Run Sync crosses Admin authorization, rq-engine bearer tokens, a private source
run token, remote download input, filesystem destination paths, dependent RQ
work, provenance records, logs, and terminal navigation. A dedicated review is
required at `artifacts/2026-07-29_security_review.md`.

## Outcome

Verified and closed. Direct real-controller evidence found and repaired one
duplicate-submission window. The dashboard now admits one request/job at a time
and restores submission on terminal state or visible request failure. Exact
render, client, route, API, worker, security, frontend, graph, repository, and
documentation gates pass.
