# ADR-0082: Historic PRISM forcing and spatial methods

Status: Accepted intended behavior, 2026-10-08; implementation pending.

## Context

The user approved historic PRISM menu/WEPP integration with Multiple (monthly PRISM revision) and MultipleInterpolated (nearest native cell), and forest execution after a walkthrough of wind, solar, dewpoint, seed and persistence choices. Raw extraction/cache already exists (ADR-0081).

## Decision

Follow [the historic PRISM contract](../schemas/prism-historic-climate-contract.md). Add mode16; keep old mode9 Daymet and mode5 stochastic. Use nearest native cells and existing station/seed. Single/Multiple acquire watershed forcing; Multiple applies existing monthly ratios/offsets; mode2 acquires hillslope cells without those adjustments. Reuse watershed GridMET wind by calendar label. Convert PRISM MJ/m2/day to CLI langleys/day with 1e6/41840 (one langley is41840J/m2). Preserve raw values and record derived transformations. Apply established observed Tdew>=Tmin floor, including after monthly temperature revision. Keep full-year menu range1981 through previous year to avoid fabricated unpublished days. Partial-year bulk API is unchanged.

## Rationale and alternatives

Nearest sampling preserves supplied daily spatial storms and cell cache identity; smooth interpolation and double monthly adjustment are rejected for mode2. Shared wind follows existing Daymet precedent without adding spatial wind choices. Selected CLIGEN station supplies unobserved storm structure; generating independent per-hillslope randomness would invent spatial differences. Raw dewpoint is valid source data even below Tmin, but the existing model preprocessing contract remains required. Do not shift daily aggregates to another observation window without subdaily evidence. Changes to stochastic humidity or other climate defaults are outside scope.

## Consequences and validation

Daily PRISM patterns are retained, within-day storms remain modeled, and wind represents watershed conditions. Units/flooring are auditable in derived artifacts; cache is unchanged. Validate numerical CLI readback and both spatial methods through prepared WEPP files and completed runs on forest; source records remain usable without cache after archive/restore. Existing source identifiers and saved projects retain semantics. No new dependency.

## Decision provenance and rollback

Venue: this Codex/user conversation, 2026-10-08 America/Los_Angeles (exact message clock time unavailable). Participants: user and Codex. Decision owner: user approved the integration walkthrough and execution; implementer: Codex. New derived PRISM forcing replaces no existing dataset behavior. The unchanged PRN writer quantizes precipitation to0.254mm and temperature to1F; record trace-rain zeroing and compare generated values against this quantization before CLI rounding. Dewpoint after monthly revision is recomputed from raw source and revised Tmin, avoiding an excessive centroid floor on cooler hillslopes.

Evidence: [bulk validation](../work-packages/20261008_prism_bulk_client/tracker.md), [integration checkpoint](../work-packages/20261008_prism_wepp_integration/artifacts/20261008_contract_decision.md), [WEPP dewpoint audit](../investigations/20261008_prism_800m_bulk/dewpoint-source-audit.md). Live numerical and execution evidence remains pending. Risks: daily-window mismatch with wind, synthetic within-day storm structure, trace-rain rounding, and retained provider revisions. Roll back the additive runtime integration if generated parity or WEPP execution fails; preserve new capability reader support, archived source and pre-test run snapshot. Do not roll back to a reader that cannot reopen newly persisted capability graphs.
