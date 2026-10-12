# ADR-0086: Configuration WEPP 261010 Default

Status: Accepted

Date: 2026-10-11

## Context and Decision

The operator requested that every configuration defaulting to `wepp_260803`
instead default to `wepp_261010`. Change only `[wepp] bin` in these files under
`wepppy/nodb/configs/`:

- `disturbed-mofe.cfg`
- `disturbed9002-10-mofe.cfg`
- `disturbed9002-10m-wbt.cfg`
- `disturbed9002-wbt-mofe.cfg`
- `disturbed9002_wbt.cfg`

## Decision Provenance

- Decision Venue: Codex workspace conversation, 2026-10-11 22:45 PDT.
- Participants Present: requesting WEPPcloud operator; Codex.
- Decision Owner: requesting WEPPcloud operator.
- Implementer: Codex.

## Change Summary and Rationale

New projects initialized from these configurations select `wepp_261010` instead
of `wepp_260803`, as explicitly requested. The selected watershed and hillslope
executables are already vendored. Existing persisted project selections are not
migrated. Config Builder code defaults and compatibility constraints are a
separate mechanism and are not changed by this literal configuration edit.

## Alternatives Considered

- Retain `wepp_260803`: rejected by the operator's requested default change.
- Replace all historical references or migrate existing projects: outside the
  requested configuration scope and would alter retained provenance.

## Consequences and Rollback

New runs may produce different scientific results with the selected executable.
No numerical equivalence is claimed. Restore the five default values to
`wepp_260803` to roll back; retain existing runs' saved executable selections.

## Evidence and Validation

- Vendored metadata: [watershed](../../wepp_runner/bin/wepp_261010.json) and
  [hillslope](../../wepp_runner/bin/wepp_261010_hill.json).
- Parse all five configuration files and read back `[wepp] bin`.
- Confirm no `wepp_260803` references remain under `wepppy/nodb/configs/`.
- Literal-only edit: no executable logic or tests changed; no simulation or
  broad test suite is required for this value replacement.
