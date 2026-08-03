# Superseded REM-06 Draft Checkpoint Operations and Security Review

**Reviewer**: Independent operations/security control agent
**Date**: 2026-08-03 UTC
**Mode**: Read-only
**Verdict**: Blocked; two high, two medium, and two low findings

## High Findings

1. Completion/retry authority conflicts between a non-null `run_watar`
   timestamp and package claims that missing/stale artifacts force retry. Choose
   timestamp-plus-failed-metadata semantics or define exact artifact/version/
   catalog validity and invalidation behavior.
2. AshPost no-data semantics are undefined. `AshPost.run_post()` can
   legitimately return after no watershed daily aggregation, update the
   catalog, and allow the timestamp without producing normal version/docs
   artifacts. Define whether no-data is successful, inapplicable, or failed and
   align acceptance evidence.

## Medium Findings

1. Old serialized directive maps show a missing `run_watar` key as enabled but
   `update_run_directives()` ignores keys absent from `_run_directives`. Require
   normalization/backfill and an old-state disable/save/reload test.
2. Lock parity is underspecified. Standalone WATAR locks climate, watershed, and
   landuse roots together. Specify roots, acquisition order/helper, archive
   preflight, bounded retries, no nested worker, and whether leaf exclusivity is
   sufficient for the ash write root.

## Low Findings

1. Limit timestamp ownership wording to Batch Runner because standalone
   `run_ash_rq` also timestamps after its own post-step.
2. Add a direct finalizer assertion for a WATAR leaf failure represented by the
   leaf worker's existing `(False, elapsed)` result and verify no new auth/route
   surface.
