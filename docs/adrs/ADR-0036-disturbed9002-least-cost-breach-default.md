# ADR-0036: Restore disturbed9002 Least-Cost Breach Default

Status: Accepted

Date: 2026-07-30

## Context

ADR-0032 changed the new-project conditioning default in
`disturbed9002_wbt.cfg` from least-cost breach to TOPAZ conditioning. The
owned WhiteboxTools fill routine and its depression handling have since been
fixed and verified end to end. The operator now wants new projects using this
configuration to return to the prior least-cost breach default while retaining
TOPAZ conditioning as an explicit supported choice.

## Decision

Set `[watershed.wbt] fill_or_breach` in `disturbed9002_wbt.cfg` to
`"breach_least_cost"`. Do not remove or alter the `topaz` token, its native
dispatch, timeout safeguards, or user-visible option. Do not mutate existing
projects or their persisted conditioning selections.

This decision supersedes only the config-default portion of ADR-0032. The
remaining ADR-0032 decisions stay accepted.

## Decision Provenance

Decision Venue: Codex API workspace thread, 2026-07-30 22:52 PDT

Participants Present: requesting WEPPcloud operator; Codex

Decision Owner(s): requesting WEPPcloud operator

Implementer(s): Codex

## Change Summary

Old behavior: new `disturbed9002_wbt` projects initialized
`fill_or_breach = "topaz"`.

New behavior: new `disturbed9002_wbt` projects initialize
`fill_or_breach = "breach_least_cost"`.

Existing projects, persisted selections, other configurations, the four
supported conditioning tokens, conditioning implementations, and downstream
flow/channel algorithms are unchanged.

## Rationale

Least-cost breach is again the preferred default for this configuration after
the owned WhiteboxTools depression-handling fix passed end-to-end operator
verification. Retaining TOPAZ as an explicit option preserves the validated
implementation and backward compatibility without making it the default.

## Alternatives Considered

1. Keep `topaz` as the default - rejected because the operator explicitly
   restored least-cost breach after validating the depression-handling fix.
2. Remove `topaz` entirely - rejected because existing projects may persist
   that token and the implementation remains supported.
3. Change every WBT configuration - rejected because the decision is scoped
   only to `disturbed9002_wbt`.

## Consequences

New `disturbed9002_wbt` projects may produce different conditioned DEMs,
drainage, watersheds, and derived model inputs than projects initialized while
TOPAZ was the default. Existing projects remain reproducible because their
persisted selections are not rewritten.

## Evidence

- Operator end-to-end verification of the WhiteboxTools fill routine in this
  workspace thread.
- `docs/adrs/ADR-0032-topaz-conditioning-disturbed9002-default.md`
- `tests/nodb/test_watershed_topaz_conditioning_contract.py`
- `/workdir/weppcloud-wbt/docs/work-packages/20260730_fill_depressions_edge_outlet/artifacts/validation.md`

## Risk and Rollback Notes

The risk is new-project delineation drift relative to the temporary TOPAZ
default. Compare conditioning diagnostics and delineation outputs if a
regression is reported. Rollback changes only the same config value back to
`"topaz"`; it must not rewrite persisted project state.

## Implementation Notes

Keep regression coverage on the parsed config value and on acceptance of all
canonical tokens. No data migration or fallback wrapper is required.
