# ADR-0066: Staley scalar estimates on valid support

## Status and provenance

Accepted direction, 2026-09-11; numerical implementation pending.
Venue: repository owner/Codex conversation, America/Los_Angeles; exact clock
time not recorded. Participants: repository owner and Codex. Decision owner:
repository owner. Implementer: Codex (documentation and subsequent authorized work).

## Decision

Compute scalar catchment estimates over non-masked usable data and communicate
valid coverage. Publish the exact valid-support GeoTIFF through normal project
files and a download link. Defer mapped reports and the GL dashboard. Missing
observations are excluded, never assigned zero. Zero usable support remains
unavailable. Explicit numerical aggregation/schema details are ratified before
scientific implementation; the current increment wires UI and model RQ tasks.

Initial M3 source eligibility is effective `[general] cellsize = 10` and
`dem_db = "ned13/2022"`; full integration checks actual raster alignment too.
M1 gains no 10 m restriction. Keep POLARIS/RUSLE automatic enablement for both
models; only M1 requires the user to prepare K through RUSLE.

## Change and rationale

Previously unknown M1 slope/SBS intersections produced bounds and no point T,
and incomplete K also suppressed point estimates. A large real basin had only
114 unknown intersections among 4,311,420 cells yet no probabilities. The owner
prefers useful scalar estimates with explicit spatial support. This supersedes
the production point-availability direction in ADR-0058/0059, without altering
Horn, the 23-degree threshold, the raw three-state tool outputs or coefficients.
Existing outputs retain their original semantics; do not silently reinterpret them.

## Alternatives

Probability bounds were proposed and rejected in favor of scalar valid-support
estimates. Imputation, silent renormalization without coverage, zero-filling and
mandatory map dashboards are not the selected workflow.

## Evidence, risk and rollback

See [selection contract](../../wepppy/nodb/mods/postfire_debris_flow/docs/model_selection.md),
[SSURGO assessment](../../wepppy/nodb/mods/postfire_debris_flow/docs/ssurgo_validity_assessment.md)
and the addicted-reservist published predictor diagnostics. Masking changes
representativeness; valid coverage must accompany results. No arbitrary minimum
coverage cutoff is introduced by this decision. Keep accepted versions and
attempts observable; rollback changes future execution policy, never deletes or
rewrites prior scientific results. Exact M3 support/geometry treatment remains
part of the scientific integration checkpoint.
