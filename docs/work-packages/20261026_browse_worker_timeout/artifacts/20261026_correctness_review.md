# Correctness and user-experience review

Date: 2026-10-26 UTC. Contract ancestor: 8b56c3d94. See independent
[implementation reviews](20261026_implementation_reviews.md).
Canonical authority: docs/schemas/browse-filesystem-contract.md and ADR-0108.

## User outcome and valid states

Generic file inspection exposes actual files regardless of Roads result state.
New filesystem regressions exercise legacy/unreceipted data, malformed receipts,
active writer locks, permitted aliases and raw retired archive bytes. Existing
route tests cover absent files, empty directories, public/private callers,
traversal, sensitive/root-only paths and escaping symlinks. Model production,
reports and query eligibility remain unchanged. Ordinary file-type/not-found
checks remain; formatting can still fail on unreadable or malformed content.
D-Tale eager views are snapshots; lazy reads retain byte-consistency errors.

## Evidence and boundaries

333 targeted tests passed, with unmocked local filesystem/lock/readback boundaries.
The actual 155,573-file production project was enumerated by the revised collector
in an isolated process in 2.192 seconds. No service code was replaced or restarted.
The wepp1 timeout command parses as 120 with eight workers and graceful_timeout 30.
No model inputs/outputs were regenerated; this is delivery semantics, not model
result certification. Runtime command remains at 30 until separate deployment.

## Findings disposition and remaining limits

Independent medium findings (ordinary directory-download 404 and old archive
error expectations) are resolved. Only security/PII may gate existing generic
files under the new canonical rule. Persistent logging remains a separate
follow-up. Friday's two-second 500 was not reproduced; Monday's no-response
manifest timeouts and new per-file cost are distinct evidence. Broad validation
and deployment boundaries are recorded in execution_evidence.md and tracker.md.
