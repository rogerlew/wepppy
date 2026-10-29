# ADR-0088: Optional depth-specific soil anisotropy

Status: accepted and implemented on forest; production rollout pending.

Amendment DM-01, accepted 2026-10-29 UTC; implementation pending: [project developer mode](../schemas/project-developer-mode-contract.md) removes override maxima only for projects with developer mode enabled. The original implementation evidence below does not cover this amendment.

## DM-01 development exception

Decision venue: user/Codex workspace conversation, 2026-10-28 America/Los_Angeles (recorded 2026-10-29 UTC). Participants present: requesting operator and Codex. Decision owner: requesting operator. Implementer: not yet assigned; Codex authored the contract and scaffold. Anurag is the intended experimenter, not an inferred approver.

Normal projects retain upper [1,100] and lower [1,10]. Ron-owned developer mode permits finite overrides >=1 without either maximum. Only the exact Dev role plus ordinary project mutation authority can activate mode in the PowerUser panel. Thereafter project mode, not the submitter's role, dictates limits. Clones inherit mode and settings. Defaults, source ratios, MOFE/hourly eligibility and horizon classification remain unchanged.

Rationale: bounded project experiments should survive cloning and background execution without user-role-dependent validation. Instance-wide changes affect unrelated projects; reversible mode needs destructive clamping or invalid-saved-state policy; a user-only bypass cannot consistently govern queued preparation. All were rejected in favor of enable-only project state with the lifecycle exceptions below. This is not permission to bypass other feature entitlements.

Evidence: [implementation package](../work-packages/20261028_project_developer_mode/package.md) records source inspection and review, not experimental stability. Extreme finite values may destabilize simulations; retain warnings and failures without clamping. Paired Python/native rollback may reject experimental inputs, so preserve activated state and document that limitation rather than resetting projects. No deployment or bulk data mutation is part of the documentation task.

Lifecycle clarification, same operator/Codex conversation, 2026-10-29 UTC: “permanent” means no dedicated off toggle, not a sticky flag across project replacement. Archive restore uses archived Ron state; existing failed-fork recovery uses copied source state. Both may return an activated project to normal mode, without a new Dev check or downgrade rejection. The operator chose existing recovery flexibility and simpler implementation over destination-state preservation or blocking restore/fork functionality, which could prevent project recovery. Normal limits apply after replacement to normal mode; reactivation still requires Dev. Runtime conformance remains pending.

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
