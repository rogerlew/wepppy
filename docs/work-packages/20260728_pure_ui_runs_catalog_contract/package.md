# SURF-06 Pure UI Runs Catalog Contract

**Status**: Verified
**Package ID**: SURF-06
**Security impact**: `high`
**Dedicated security review**: required

## Purpose

Verify the authenticated Runs dashboard from the owned-run query through
catalog/table/map rendering, Admin/Root user scoping, deletion enqueue and job
polling, and terminal reload. Users can inspect and delete only authorized
projects, while privileged viewers can explicitly scope the same catalog to
another account.

## Concise Intent Contract

The Runs page, catalog, and map endpoints require authentication. Ordinary
users always receive only their owned runs and cannot widen scope with an
`alias` query. Admin and Root users may search the protected user directory and
scope catalog/map results to an exact user ID or case-insensitive email.

Catalog rows preserve the stored run ID and configuration, safely render
escaped metadata, open the exact run URL, show rolling TTL deletion or
last-modified state, and disable deletion for readonly runs. Search, sorting,
pagination, empty/error states, table/map tabs, and scoped URL state remain
consistent.

Deletion requires explicit confirmation and posts with CSRF to the exact
encoded run/config route. The route reauthorizes the run, rejects readonly
projects, records queued deletion state, and enqueues the existing RQ worker.
The client polls the returned owned job until a recognized terminal state,
removes a row only after `finished`, bounds retries, and presents failures
without treating them as success.

## Scope

- `wepppy/weppcloud/templates/user/runs2.html`;
- `wepppy/weppcloud/routes/user.py::{runs,runs_users,runs_catalog,runs_map_data}`;
- `wepppy/weppcloud/routes/nodb_api/project_bp.py::delete_run`;
- `wepppy/rq/project_rq.py::delete_run_rq` and its helper seam;
- run ownership, readonly, TTL/delete-state, map metadata, and reload evidence;
  and
- actual render, actual-inline-client, route, persistence/RQ, and security
  evidence.

## Exclusions

SURF-06 adds no new run field, ownership rule, Admin role, retention policy,
delete semantics, queue, map provider, bulk server endpoint, restore behavior,
or account lifecycle operation. Run creation, archive, fork, and sync remain
separate packages.

## Acceptance

Actual rendering proves field/action/endpoint identity and ordinary versus
privileged controls. The real inline client proves catalog/search/pagination/
map/scoping/deletion/poll states and exact encoded run/config requests. Existing
route and worker tests are retained only after inspection and execution.
Confirmed mismatches receive failing regressions before the smallest compatible
repair. Focused and broad validation, security review, documentation lint, a
separate commit, and a clean worktree are required.

## Outcome

SURF-06 verified the actual page, inline client, ownership and privileged
scoping routes, exact deletion enqueue, readonly handling, worker, and terminal
reload behavior. Repairs encode run/config path segments, preserve the stored
configuration during deletion, send same-origin credentials explicitly,
return HTTP 400 for readonly deletion, and keep failures visible without
logging run identifiers. The dedicated security review found no unresolved
high- or medium-severity issue.
