# Extract the read-only worker's catalog and manifest operations

## Purpose / Big Picture

Make freeze ordering visible in the worker. A parent run must drain pending
catalog requests, set its read-only marker and publish a verified manifest.
Children skip manifest creation. Thaw must remove the marker before the manifest.

## Progress

- [x] 2026-11-23 UTC. Inspect the worker, its tests and the previous package.
- [ ] Extract private operations and add worker-level failure and thaw coverage.
- [ ] Run focused tests, repository checks and record outcomes.

## Surprises & Discoveries

The previous project RQ refactor already moved subcatchment state inspection
into a separate module. This follow-up addresses a different worker.

## Decision Log

2026-11-23 UTC. Keep the transition inside the existing lifecycle guard.
Keeping marker assignment in the worker makes the rollback scope visible.

## Validation and integration

Exercise the public job with real temporary files. Read back catalog data and
manifest presence on success, and check the restored state after manifest
failure. Run the full pytest gate and document any environmental limitations.
Commit on the task branch and merge into local master.

## Outcomes & Retrospective

Pending validation.
