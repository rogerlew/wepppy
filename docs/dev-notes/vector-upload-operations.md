# Vector uploads: use, sharing and recovery

Roads, AgFields, Omni contrasts and Batch Runner accept GeoJSON and, when binary
uploads are enabled, a Shapefile ZIP or a single GeoParquet file. Batch Runner
requires polygons. The converter produces WGS84 GeoJSON; each workflow then
applies its own geometry and attribute requirements. A rejected replacement
preserves the previously accepted input.

Complete originals and failed attempts are retained with SHA-256 receipts for
inspection. Public sharing and team access allow users admitted by the existing
fork workflow to inherit those records, including private archives. The source
owner controls that sharing decision. Direct sensitive downloads retain their
existing authorization checks.

Copies preserve the original upload actor. The additive `retention_actor` records
who incurs the copied storage charge; automated callers without a verified
principal use the existing unattributed bucket. Copies count physical bytes even
when attempt IDs repeat. Replacements need headroom for existing retained bytes
and the incoming copy: deferred stale-workspace cleanup does not free storage.

The ledger covers only `VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT`, identified by
`VECTOR_UPLOAD_RUN_FILESYSTEM_ID`. Existing profile workspaces on other storage
keep their established layout. Both settings must establish that a destination
is outside the ledger; missing settings do not imply external storage. Known
offline profile exports are explicitly designated by their existing callers.

Before deploying the receiver changes or enabling `VECTOR_UPLOAD_BINARY_ENABLED`, run
`tools/check_vector_upload_readiness.py` in the receiver's configured runtime.
It checks filesystem identity, private writes, initialized accounting, pending
repairs and the expected converter binary/lock/source identity. Disabling the
flag rolls binary admission back while preserving GeoJSON support and retained
records. This document does not authorize a deployment.

An interrupted copy, reset, deletion or restore leaves a durable repair marker.
Retry the same recorded operation against the same destination. An incomplete
Batch copy must be removed successfully before recopying; it cannot become a
second retained stale copy. Do not delete markers to bypass failed accounting.
Use `tools/reconcile_vector_upload_retention.py --filesystem-root <root>
--rebuild-ledger` to audit; `--apply` performs the documented repair/rebuild after
reviewing the report. Reconciliation does not replace retrying a pending
filesystem operation. Re-read files, receipts and ledger totals after repair.

The authoritative limits, state machine, authorization and compatibility rules
are in the [normalization contract](../schemas/vector-upload-normalization-contract.md).

A copy refused because source accounting is pending requires source reconciliation
before retry. A terminal receipt alone is insufficient: its accounting status
and any matching Redis reservation must be committed. This refusal occurs before
the destination is changed.
