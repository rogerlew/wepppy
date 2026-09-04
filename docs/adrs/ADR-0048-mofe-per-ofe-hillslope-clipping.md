# ADR-0048: Apply Hillslope Clip Length Per OFE

## Status

Accepted; implementation pending.

## Context

WEPPcloud already exposes `clip_hillslopes` and `clip_hillslope_length` and
preserves representative area when clipping a single-OFE slope file. The
multiple-OFE preparation path copies its slope files without clipping, even
when the stored option is enabled. This makes the same advanced option mean
different things depending on watershed representation.

## Decision

When clipping is enabled, `clip_hillslope_length` is the maximum length in
meters for each individual OFE. Longer OFEs are capped independently and
shorter OFEs remain unchanged. The one shared slope-file width is scaled by
`original total OFE length / clipped total OFE length`, preserving total
representative hillslope area.

Non-positive and non-finite effective clip lengths fail preparation explicitly
when clipping is enabled. No default value, request key, or persisted field is
changed. Existing request-parser behavior, including the numeric-infinity
`OverflowError`, remains outside this decision.

## Decision Provenance

- **Decision Venue**: Codex workspace conversation, 2026-09-04 04:31 PDT
  (2026-09-04 11:31 UTC), America/Los_Angeles.
- **Participants Present**: repository operator Roger Lew and Codex.
- **Decision Owner**: Roger Lew.
- **Implementer**: Codex.
- **Change Summary**: old behavior clipped only single-OFE hillslopes; new
  behavior applies the configured threshold to every OFE and preserves total
  representative area.

## Rationale

Per-OFE clipping matches the operator's explicit requested meaning and bounds
each modeled transport segment. Scaling the shared width preserves the area
contract already presented by the advanced option.

## Alternatives Considered

Clipping the combined multiple-OFE hillslope to one total-length limit was
rejected because the requested value is explicitly per OFE. Leaving multiple-
OFE inputs unchanged was rejected because it makes an enabled user option
ineffective. Scaling each OFE with a separate width was rejected because the
slope-file format has one shared width.

## Evidence

The initiating run `dainty-signature` using `canada-wbt-mofe.cfg` stored
clipping enabled at 300 m but produced multiple-OFE slope files without applying
the clipping routine. The decision and observed evidence are recorded in
`docs/work-packages/20260904_mofe_hillslope_clipping/artifacts/2026-09-04_contract_decision.md`.
Package acceptance will rerun this project on `forest` through rq-engine with a
60 m per-OFE limit and inspect generated `wepp/runs/p*.slp` files.

## Consequences

Multiple-OFE runs with clipping enabled will generate different model inputs
and may generate different WEPP results. Runs with clipping disabled and valid
single-OFE behavior remain compatible. Invalid negative and non-finite enabled
single-OFE state is newly rejected before generated geometry is published.

## Risk and Rollback Notes

The primary risk is incorrect parsing or width scaling of multiple-OFE slope
files. Unit tests must cover mixed shorter/longer OFEs, no-op geometry, header
preservation, invalid limits, and area preservation. Roll back if any generated
OFE exceeds its enabled finite-positive limit, any source/generated pair changes
OFE count/profile/header fields, area differs beyond the documented tolerance,
or rq-engine fails because of the transform. Rollback reverts the implementation
and recreates the Forest development services at the recorded pre-deploy
revision while retaining reader-compatible persisted settings.
