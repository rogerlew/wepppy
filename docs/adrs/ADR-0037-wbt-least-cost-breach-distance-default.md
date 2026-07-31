# ADR-0037: Increase WBT Least-Cost Breach Distance Default

Status: Accepted

Date: 2026-07-30

## Context

WEPPpy WBT configurations that define `blc_dist` currently use 1,000 m.
Least-cost breaching is again the selected default for
`disturbed9002_wbt`, and bounded searches that cannot resolve every depression
now fail explicitly instead of silently filling unresolved terrain.

## Decision

Change `blc_dist` from 1,000 m to 3,000 m in every configuration that defines
the attribute. Do not add the attribute to configurations that do not already
define it. Existing projects retain their persisted value.

## Decision Provenance

Decision Venue: Codex API workspace thread, 2026-07-30 23:20 PDT

Participants Present: requesting WEPPcloud operator; Codex

Decision Owner(s): requesting WEPPcloud operator

Implementer(s): Codex

## Change Summary

Old behavior: the 13 defining configurations initialized `blc_dist=1000`.

New behavior: the same 13 configurations initialize `blc_dist=3000`.

No conditioning token, formula, unit conversion, or configuration membership
changes.

## Rationale

A larger bounded search gives least-cost breaching more opportunity to resolve
depressions before the existing fail-on-unresolved guard stops delineation.
Applying the same literal to every defining configuration keeps the default
consistent across WBT workflows.

## Alternatives Considered

1. Retain 1,000 m - rejected because the operator selected a 3,000 m default.
2. Change only `disturbed9002_wbt` - rejected because the operator explicitly
   requested every configuration that defines the attribute.
3. Add the attribute to other configurations - rejected because that broadens
   behavior beyond the requested scope.

## Consequences

New projects may spend longer searching and may produce different least-cost
breach paths than projects initialized with 1,000 m. Existing persisted
projects are unchanged. The fail-on-unresolved contract remains active when a
3,000 m search is still insufficient.

## Evidence

- Direct inventory of `wepppy/nodb/configs/*.cfg`: 13 definitions, all at
  1,000 m before this change.
- `docs/adrs/ADR-0035-wbt-least-cost-unresolved-depression-failure.md`

## Risk and Rollback Notes

Monitor least-cost channel duration, controlled unresolved-depression failures,
and conditioning diagnostics. Rollback restores the same 13 literals to
`blc_dist=1000`; it does not rewrite existing projects.

## Implementation Notes

Validation is limited to direct inventory/readback of the defining config
lines. No dedicated literal assertion or full test suite is warranted.
