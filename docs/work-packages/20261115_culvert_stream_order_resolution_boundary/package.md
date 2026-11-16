# Culvert Stream-Order Resolution Boundary

**Status**: Complete: implementation and forest end-to-end validation (2026-11-16 UTC).

## Overview

Use a coarse channel network when it preserves the supplied culvert connection,
and try finer networks per run when necessary. This keeps large watersheds
manageable while allowing small watersheds to use more detailed channels.

The initial nominal-1m boundary repair selected three passes, but its 3,344
hillslopes and 1,339 channels exceeded twice the retained 726/298 baseline.
The operator then authorized a resolution/outlet study and per-run descending
selection. Four passes produces 783/313 for Point_ID 1040, while seven other
supplied points need finer candidates. Re-extraction and DEM coarsening can move
channels; production selection therefore preserves the supplied DEM and streams.

## Current contract and execution

The authoritative [selection contract](../../schemas/culvert-stream-selection-contract.md)
and ADR-0144 define starting passes 4/3/2/1/1 for nominal 1/2/4/8/10 m,
with effective-resolution boundaries 1.5/3/6 m. Each run descends to the first
candidate with positive stream intersection at the supplied point and positive
watershed stream coverage. Zero means original supplied streams. The existing
threshold-scaling formula and explicit override precedence remain intact.

Execute [the per-run plan](prompts/active/per_run_selection_execplan.md).
The original boundary plan and calibration plan retain the experiments and
rejected alternatives. Reviewed contract ancestor: `61645e8a1`.
Implementation commit: `4266e740a`.

## Scope and compatibility

New admissions receive an internal versioned policy marker. Batch preparation
publishes immutable candidates and a ready/failed manifest; per-run receipts
record considered and selected candidates. Missing/corrupt artifacts fail
explicitly. Existing batches without new-policy evidence retain legacy behavior.
Skeleton ZIPs retain manifests, source dependencies, candidates and receipts.
They are not promised as fully standalone executable projects.

Included changes cover the existing upload boundary, batch preparation, runner
selection, skeleton retention, documentation and regression tests. No new queue,
service, dependency, client parameter, authentication rule, or source DEM
resampling is introduced. Numerical defaults are documented in ADR-0144.

## Authority and operational boundary

The operator authorized implementation, a standalone reviewed contract commit,
and forest-only targeted service restarts for real API/RQ replays. Inventory
active jobs first and retain durable artifacts. Do not disrupt unrelated work.
The superseded own three-pass replay was canceled through the supported endpoint.
Production source batches remain unchanged. Forest1 and production deployment
require separate authorization.

Use the existing registered culvert service identity; no human-linked account is
required. Credentials remain in gitignored secret files. Verify uncached SDA soil
construction under the actual batch-worker identity before and after restart.

## Acceptance and evidence

A fresh two-point forest batch must select four passes for 1040 and a finer
candidate for 2913. Verify hashes, actual VRT source pixels, supplied-point and
resolved-outlet channel intersections, raster/parquet cardinality, both child
results, finalizer completion and retained archive dependencies. Parent success
alone is insufficient. The 1040 cardinality must remain below twice 726/298.

See [validation](artifacts/per-run-validation.md),
[tracker](tracker.md), and the independent implementation/security reviews.
Focused tests cover real WBT candidate parity, fallback, explicit zero, missing
and changed artifacts, retry preservation, archive restore, and hostile reserved
upload artifacts. Complete the broad sanity suite and required stub/docs gates.

## Review gates

Two independent contract reviews approved the checkpoint before source edits.
Independent implementation review has no open high/medium source finding;
end-to-end forest acceptance passed; both runs and the finalizer succeeded.

Security triage: **high by repository default**, because this implementation
changes upload admission and artifact path handling. The prior numeric-only
triage is superseded. The dedicated security artifact is
`artifacts/per-run-security-review.md`, following the repository security review
template; no unresolved medium/high finding is permitted at closure. Existing
authentication and queue wiring are unchanged.

## Complexity and rollback

Reuse WBT, rasterio, filesystem locks, atomic JSON publication, existing RQ jobs
and NoDb integration. The new selection module isolates the candidate policy;
small existing-caller changes wire it into admission and execution. Retaining
candidate rasters adds disk/preparation cost but prevents shared topology from
being overwritten on retries. Roll back new admission policy without rewriting
saved batch artifacts.

## Limits and follow-up

This is a performance-first, Santee-supported heuristic, not multi-site scientific
calibration. Other resolution starts have mapping coverage; only native 1m has
this end-to-end replay. The earlier 4m terrain study retains an explicit TOPAZ
failure. Held-out sites and broader resolution/outlet/cardinality calibration
remain follow-up work. Any production rollout is separate from this package.
