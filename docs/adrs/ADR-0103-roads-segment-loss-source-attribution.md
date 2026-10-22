# ADR-0103: Attribute Roads segment loss to its native profile

## Status

Proposed checkpoint, 2026-10-22; implementation pending.

## Decision and rationale

Use each completed manifest profile's original PASS exports and modeled WAT area
for mean annual segment loss. Remove target-hillslope join/fallback and fabricated
zero values for missing sources. Preserve columns, explicitly identify profile
scope, and make unavailable prism/buffer aliases NULL. Exact equations, units and
valid states are in [the canonical contract](../schemas/roads-segment-loss-summary-contract.md).

The target-first join repeats receiving-hillslope losses for distinct roads.
Selecting segment rows from watershed loss tables cannot repair this because
those tables contain canonical hillslopes. Parsing human-readable loss summaries
is rejected: their aggregate semantics and rounding differ from source PASS
exports and they do not provide the needed source-qualified daily identity.
Reuse owned native PASS/WAT interchange plus the existing DuckDB reducer.

## Decision provenance

Venue: Roger/Codex task conversation, 2026-10-22 (America/Los_Angeles).
Participants: Roger and Codex. Decision owner: Roger, requesting a work package
and execution to correct `roads_segment_loss_summary.parquet` after the diagnosed
source-attribution defect. Implementer: Codex. Existing session task-scoped commit
authority persists. No model parameter defaults, geometry, runoff physics or
aggregate Roads water accounting changes are authorized by this repair.

## Compatibility, risk and rollback

Existing file/column names and download links stay. Values intentionally change;
nullable aliases and additive provenance distinguish corrected semantics. Historical
artifacts are not relabeled until regenerated. Annual source export is distinct
from routed outlet yield and incremental road impact. Revert code and regenerate
only if rollback is required; retain original artifacts in the isolated validation
copy. No production deployment or original UM1 mutation in this package.

## Evidence

[Work package](../work-packages/20261022_roads_segment_loss_summary/package.md)
retains the source comparison, independent reviews and generated-artifact tests.
