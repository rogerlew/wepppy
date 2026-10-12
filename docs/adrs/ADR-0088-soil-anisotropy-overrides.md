# ADR-0088: Optional depth-specific soil anisotropy

Status: accepted and implemented on forest; production rollout pending.

## Context and decision provenance

Decision venue: user/Codex workspace conversation, 2026-10-12, America/Los_Angeles. Participants: requesting operator and Codex. Decision owner: requesting operator; implementer: Codex. No additional meeting participants or scientific validation are inferred.

The operator requested MOFE-only controls for hourly water balance and deep seepage, upper horizons with a 50 cm threshold and ratios 1–100, lower horizons 1–10, a warning above 10, and a Rust implementation with read-once/write-once preparation.

## Decision

SA-01 adds optional upper/lower anisotropy overrides with inclusive finite bounds. Unset values preserve existing source ratios and defaults. Classify by cumulative horizon bottom depth after existing depth adjustments: <=500 mm upper, >500 mm lower, without splitting horizons. This minimal classification is an implementation assumption presented for operator correction. The UI warns that values above 10 can cause numerical instabilities; these accepted input limits do not guarantee stable or physically appropriate simulations.

Only MOFE with hourly water balance/deep seepage (`run_wepp_ui`) can edit/apply overrides. Retain inactive settings without applying them. Preserve native formats; a format lacking per-horizon anisotropy cannot accept an active override.

## Rationale and alternatives

The requested capability supports explicit user parameter experiments without changing existing projects. Blank defaults avoid silently changing the current shallow-layer derivation rules. Splitting horizons would change geometry and require additional format/model-limit decisions; it is not assumed. Rust computes the depth-specific overrides in memory, while the existing parser/writer preserves owned format behavior. A complete Rust parser migration is unnecessary for the confirmed I/O problem: ordinary prep already writes once, and two duplicate-read paths can reuse the same source/object.

## Evidence and consequences

[SA-01](../schemas/soil-anisotropy-contract.md) is normative; [work package](../work-packages/20261012_soil_anisotropy/package.md) retains discovery, reviews and actual generated-output evidence. Existing functions are `prep_soil`, `prep_multi_ofe_hillslope`, and `WeppSoilUtil`. Forest direct and live RQ preparation exercise the rebuilt native module and produce identical soil files with unchanged sources. Browser checks verify eligibility, validation errors and normal output download. These establish software conformance, not hydrologic stability.

Risk: changed horizontal/vertical conductivity ratios can change model results or destabilize integration. Warn without clamping accepted values. Validate all values and format compatibility before writing a prepared soil. Clearing overrides and rebuilding restores original source ratios. Rollback must pair Python and native code; no original soil mutation or production migration is authorized.
