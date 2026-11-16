# ADR: Per-run culvert pruning with finer candidate fallback

Status: Accepted direction; implementation pending checkpoint  
Date: 2026-11-16

## Decision

Use the [stream selection contract](../schemas/culvert-stream-selection-contract.md).
Prefer coarse connected networks, stepping from the initial pass count to zero
per run. Map nominal 1/2/4/8/10 m to starts 4/3/2/1/1, with effective-size upper
bounds 1.5/3/6 m. Keep the threshold-scaling formula. Payload/fixed overrides set
the starting maximum. Pass zero uses supplied unpruned streams.

## Provenance

Venue: operator/Codex conversation, 2026-11-16 UTC (exact message time unrecorded).
Participants and decision owner: operator; implementer: Codex.
Operator explicitly requested per-run descending fallbacks and a performance-first
bias; bin midpoints and manifest compatibility are implementation decisions.

## Context and evidence

[Study findings](../work-packages/20261115_culvert_stream_order_resolution_boundary/artifacts/outlet-fidelity-findings.md)
show that four passes fits1040's scale but loses seven smaller culvert outlets.
Three passes retains all39. The proposed ADR-0143 three-pass boundary alone did
not meet the count target; this decision replaces that candidate direction.

## Alternatives and consequences

Universal four passes loses outlets; immediate unpruned fallback needlessly
restores maximum density. Re-extraction/coarsening can move channels. Descending
selection preserves supplied channel locations and spends finer delineation work
only where connections require it. Batch candidate rasters add disk/preparation
cost; no new service or dependency is introduced.

## Risk and rollback

This is Santee-supported heuristic policy, not general scientific calibration.
Four-metre terrain diagnostics contain an unresolved TOPAZ failure. Exact point
intersection can reject legacy input inconsistencies; preserve old batches and
fail new invalid inputs explicitly. Do not promote before real forest artifact
validation. Rollback applies to new admission policy; retain evidence and avoid
rewriting existing run artifacts.
