# Batch Climate and RAP finalization

Observed GridMET (single and PRISM-revised multiple climates) and RAP time-series
builders collect outside the NoDb lock. They stage files within the run, then
lock, hydrate the controller from disk, compare relevant inputs, publish the
files, apply explicit derived fields, and dump once. The governing specification
is [Writer Ownership and Mutation Topology](../schemas/nodb-persistence-concurrency-contract.md#writer-ownership-and-mutation-topology).

## User and operator behavior

Unrelated controller edits survive a build. A changed climate year, station,
spatial input, RAP source raster, or other captured input rejects the collected
result with an explicit superseded error. Fix or finish the input edit and retry
through the existing workflow. No automatic stale-object dump retry is used.

Failed collection preserves existing controller state and published files.
Successful GridMET replacement removes obsolete climate sidecars so old calendar
parquet or NOAA location data cannot survive as authoritative output. PRISM
revision keeps its existing channel climate and publishes hillslope outputs.
Configuration supplied through Climate `attrs` remains a separate input update.

RAP retains six cover bands, percent units, year/TOPAZ/OFE columns, legacy
embedded-data reads, and downstream `.cov` files. Empty summaries produce an
empty typed parquet instead of retaining a previous summary. Remote retrieval
and per-year/band analysis retain contextual progress and failure messages.

The completion timestamp follows successful finalization and catalog update.
Batch domain failures still return `(False, elapsed)` to RQ, publish
`EXCEPTION_JSON`, remain retry eligible, and retain the existing completion
trigger. RQ's successful execution of that wrapper is not watershed success;
inspect `run_metadata.json`, batch classification, and the final failure summary.

## Publication and recovery

Artifact replacement preserves existing file modes. Publication and rollback
check lock ownership; rollback also checks that the artifact still belongs to
the failed publication. Unmanaged Climate directory symlinks retain the router's
unlink behavior; direct builders reject them. Managed `.nodir` Climate
projections remain supported. RAP output and source paths stay within the run.

Pre-commit failures restore previous artifacts. A `dump()` error after its own
NoDb replacement keeps the matching new artifacts and reports failure without a
completion timestamp. If commit readback is unavailable or rollback loses
ownership, `.derived-backup-*` directories retain recovery copies and the log
identifies the interrupted operation. Preserve those copies and failed-job
evidence; inspect the durable controller and artifacts before recovery. Never
copy an old backup over a newer writer's output or clear live locks as a retry
shortcut.

The artifact set and NoDb are not one crash-atomic transaction. Process death
during publication remains an interrupted, retryable operation. Cooperative
locks do not protect against out-of-band writers. A deployment-specific replay
is necessary to measure recurrence, but no live replay or deployment was part
of the September 2026 correction at the operator's direction.

## Implementation and regression evidence

- `wepppy/nodb/core/climate_observed_build.py` captures observed settings and
  centroid; PRISM also captures map extent/cell size, hillslope coordinates,
  raster-service settings, and the source CLI signature.
- `wepppy/nodb/mods/rap/rap_ts_build.py` captures years/map identity; analysis
  also captures the six bands, multi-OFE setting, manager configuration, and
  watershed/source raster signatures. Workers return results to the collector.
- `wepppy/nodb/_derived_build.py` owns fresh hydration and reversible file
  publication. Exact final-payload comparison distinguishes an own NoDb commit
  from a competing rewrite; it is never used to retry persistence.
- `tests/nodb/test_batch_climate_rap_contention.py` exercises real locks, NoDb
  signatures, dumps, artifact replacements, conflicts, partial failures,
  containment, and real raster-to-parquet-to-WEPP-cover propagation.

Health signals are successful artifacts/timestamps and zero target stale-write
exceptions. Danger signals are superseded results marked complete, lost unrelated
fields, retained stale sidecars, loss of recovery copies, or an old publisher
overwriting newer files. Recurrence requires a new incident record and attribution
from the affected deployment; local injected writers do not identify that writer.
