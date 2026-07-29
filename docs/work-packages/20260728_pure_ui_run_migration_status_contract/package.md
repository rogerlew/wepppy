# SURF-08 Pure UI Run Migration Status Contract

**Status**: Verified
**Package ID**: SURF-08
**Security impact**: `high`
**Dedicated security review**: PASS; no unresolved high or medium findings

## Purpose

Verify the migration gate from its authorized Flask host through rendered
migration choices, session-token enqueue, duplicate-job protection, bounded
status polling, terminal result/error handling, migration execution, optional
archive creation, readonly restoration, and project reload.

## Concise Intent Contract

An authorized run viewer sees the exact migration inventory and permission
state. Only an owner or administrator can enqueue migration, with an explicit
native `create_archive` boolean and one disabled action while submission is
pending. The client uses the run-scoped session-token transport, safely renders
job and server metadata, polls the returned canonical status URL compatibly
with configured poll authentication, backs off boundedly on rate limiting,
stops for every terminal/not-found state, and exposes retry or project
continuation as appropriate.

The server retains `rq:enqueue`, session-marker/run-ownership, lock, active-job,
readonly restoration, archive confinement, canonical response/error, persisted
job-id, worker status, and version-update behavior.

## Scope

- `run_0_bp.py` run gate and migration host;
- `run_0/rq-migration-status.htm` rendered and inline behavior;
- rq-engine `migrate-run`, `jobstatus`, and `jobinfo`;
- `migrations_rq` worker result, archive, readonly, and status behavior; and
- direct render, real inline Jest, Flask, rq-engine, and worker tests.

## Exclusions

No migration inventory, schema/version policy, archive format, authorization
policy, queue topology, timeout, or run-sync behavior changes are authorized.
Shared transport and status producers remain exercised consumers, not advanced
owner packages.

## Acceptance

Actual rendering proves inventory, permission, option, actions, safe bootstrap,
and lifecycle targets. Real inline execution proves enqueue, duplicate
submission prevention, polling/backoff, terminal/error rendering, retry, and
reload. Existing server/worker evidence is retained only after inspection and
execution. Confirmed mismatches receive the smallest compatible repair and
proportional independent review.

## Outcome

Direct rendering and real inline execution now cover permission-dependent
actions, archive selection, session-token enqueue and polling, bounded
rate-limit recovery, terminal success/failure, escaped metadata, retry, and
continuation. The audit repaired two confirmed template mismatches: run/config
bootstrap values now use JSON-safe Jinja serialization, and jobstatus/jobinfo
polls now use the same run-scoped session-token transport as enqueue. Server
conformance repairs also enforce owner/admin mutation authority, restrict human
owner matching to user/session tokens, fail closed on owner lookup, serialize
concurrent submissions, persist job identity before queue publication, pin
bearer polling to canonical local job URLs, preserve readonly until worker
execution, and fail requested archive/restoration errors explicitly. Migration
inventory, payload, version, and job dependency behavior are unchanged.
