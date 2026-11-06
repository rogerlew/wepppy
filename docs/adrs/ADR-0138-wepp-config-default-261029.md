# ADR-0138: Migrate remaining WEPP 261010 config defaults to 261029

Status: Accepted  
Date: 2026-11-05

## Context

Five repository configs still select `wepp_261010` in `[wepp] bin`.
The operator explicitly requested migration of all such config values to
`wepp_261029`.

## Decision

Change only those `[wepp] bin` literals. This decision authorizes repository
config defaults, not migration of saved project selections or deployment.
The independent `[ag_fields] bin` value remains unchanged.

## Decision Provenance

Decision Venue: Codex task conversation, 2026-11-05, America/Los_Angeles;
time not recorded.  
Participants Present: requesting operator and Codex.  
Decision Owner(s): requesting operator.  
Implementer(s): Codex.

## Change Summary

In `wepppy/nodb/configs/`, change `[wepp] bin` from `wepp_261010` to
`wepp_261029` in:

- `disturbed-mofe.cfg`
- `disturbed9002-10-mofe.cfg`
- `disturbed9002-10m-wbt.cfg`
- `disturbed9002-wbt-mofe.cfg`
- `disturbed9002_wbt.cfg`

## Rationale

Apply the operator's chosen release consistently to every remaining matching
WEPP config default.

## Alternatives Considered

- Retain 261010 defaults: conflicts with the explicit migration request.
- Replace all 261010 references: would change independent AgFields settings,
  historical evidence and explicit version selections outside the request.

## Consequences

New projects consuming these defaults select 261029 and may produce different
model results. Existing persisted executable selections are not rewritten.

## Evidence

- [ADR-0136: release interpretation and retained evidence](ADR-0136-wepp-261029-modeling-release.md).
- Section-aware config readback verifies all five replacement values and no
  remaining `[wepp] bin` selections of 261010 in repository configs.

## Risk and Rollback Notes

Release corrections can materially change predictions; the evidence limitations
in ADR-0136 still apply. If this default migration must be reversed, restore the
five config literals. That does not revert saved projects or regenerate results.

## Implementation Notes

Literal-only edit: validate by config readback and diff inspection; no test
changes or model runs are required for this migration.
