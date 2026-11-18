# ADR-0144: Per-run culvert pruning with finer candidate fallback

Status: Accepted; implemented and validated on the native 1 m forest replay

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
Four-metre terrain diagnostics contain an unresolved TOPAZ failure. The original supplied-point intersection rule rejected valid road-constrained
inputs; the amendment below replaces it for new admissions. Preserve old batches. Do not promote before real forest artifact
validation. Rollback applies to new admission policy; retain evidence and avoid
rewriting existing run artifacts.

## Implementation evidence

Reviewed contract ancestor `61645e8a1`; implementation `4266e740a` and admission
fix `d0732a4d2`. Forest batch `e4eb3edf-0bba-457f-adf0-17eeb61d85b8` selected
four passes for 1040 (783 hillslopes/313 channels) and three for 2913 (3/1). Both
resolved outlets remain on the consumed channels, both runs succeeded, and the
finalizer reports 2 successes, 0 failures, 0 skipped outlets. See the package
`artifacts/per-run-validation.md` for artifact and regression evidence. Other
resolution starts remain provisional; this result does not authorize rollout.

## Amendment: original outlet preservation (2026-11-17)

Operator/Codex conversation, 2026-11-17 UTC (exact message time unrecorded);
operator is decision owner, Codex implements. The operator requested resolving
exact outlets on the CULVERT-supplied stream network before pruning and reconciling
the contracts. Implemented locally; production deployment is pending. See the
[repair validation](../work-packages/20261117_culvert_original_outlets/artifacts/validation.md).

FindOutlet now resolves the modeled outlet on original supplied streams before
any pruning. Selection preserves that resolved cell; downstream delineation uses
the same outlet. The supplied road point remains unchanged and need not be on a
stream cell. No thresholds change. Nearest-stream snapping was rejected because
it can select another drainage and move the road-constrained input.

Incident batch ab283192-441e-41a1-baad-6c2df0c36d31 rejected seven valid road
fallback points adjacent to stream cells. This conflicts with the January guide's
explicit distinction between supplied point and modeled outlet. New admissions
use an explicit selection basis and immutable original outlet records; retained
policies keep their prior semantics. Recovery is a fresh submission, not silently
rewriting old receipts. Validate original and consumed stream membership, crop
translation, archive/resume and failed outlet observability. This repair does
not address the separate SSURGO service failures.
