# RQ Job ID Canonicalization and Dashboard Compatibility

**Status**: Closed (2026-08-08)
**Timezone**: UTC

## Overview

Newer atomic orchestration paths preallocated RQ UUIDs with `uuid4().hex`, while
RQ itself and older paths use `str(uuid4())`. A legacy dashboard route then
rewrote every 32-character ID by inserting hyphens, making valid bare-hex jobs
uninspectable. This package restores one canonical generation format without
invalidating existing Redis records.

## Approved Intent and Scope

The operator explicitly directed that newly generated UUID-based RQ job IDs be
normalized to `str(uuid4())` and that durable documentation prevent recurrence.
Included scope is RQ ID generation, exact opaque lookup in the job dashboard,
compatibility tests, and current RQ documentation. Error IDs, JWT identifiers,
lock tokens, filenames, artifact execution IDs, auth, queue topology, and job
dependencies are excluded.

## Success Criteria

- New preallocated UUID RQ IDs use the shared hyphenated generator.
- Existing 32-character bare-hex and 36-character hyphenated IDs pass through
  the dashboard unchanged.
- RQ 1.16.2 dependency and tree semantics remain unchanged.
- Focused tests and RQ graph guard pass.

## Gates

- Parameterization change: `no`; ADR required: `no`.
- Security impact: `low`; no dedicated security review required because UUID
  entropy, auth, access, and disclosure are unchanged.
- Starting revision: `212c8d80b7c46be4119f616c86d426d69778ad35`.

## References

- `docs/schemas/rq-response-contract.md`
- `wepppy/rq/README.md`
- `wepppy/weppcloud/routes/rq/job_dashboard/README.md`
- `docs/standards/contract-first-change-standard.md`

## Closure Notes

**Closed**: 2026-08-08

Canonical generation now uses one `str(uuid4())` helper across serialized
subcatchment, migration, fork/finalizer, and AgFields preallocation. The job
dashboard preserves exact IDs, so existing bare-hex records remain inspectable.
No auth, queue topology, dependency edge, or response shape changed.

Checkpoint: `1778b66d1`; implementation: `41b23983d`.
