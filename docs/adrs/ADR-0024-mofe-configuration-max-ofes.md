# ADR: MOFE Configuration Cap of Five OFEs

Status: Accepted
Date: 2026-07-21

## Context

Multiple-OFE (MOFE) watershed segmentation accepts `watershed.mofe_max_ofes`.
The controller's absent-option fallback and its upper safety bound are both 19,
so MOFE configuration files that omit the option can create up to 19 OFEs per
hillslope. The project needs a lower, explicit configuration-level cap and a
Canada WBT MOFE configuration.

## Decision

Set `watershed.mofe_max_ofes = 5` in every active MOFE `.cfg` file. Add
`canada-wbt-mofe.cfg` as the Canada variant of the existing earth/C3S WBT
configuration, with `wepp.multi_ofe = true`, WBT delineation, and the same
five-OFE cap. Register it as a preview WBT configuration available to users.

The implementation-level fallback and hard safety ceiling remain 19 for
non-MOFE and legacy configurations that do not declare this parameter.

## Decision Provenance (Required for Parameterization Changes)

Decision Venue: Codex user session, 2026-07-21 America/Los_Angeles
Participants Present: repository user; Codex
Decision Owner(s): repository user
Implementer(s): Codex

## Change Summary

| Parameter | Previous MOFE configuration behavior | New behavior |
| --- | --- | --- |
| `watershed.mofe_max_ofes` | Not declared; controller fallback allowed 19 | Explicitly `5` in each MOFE configuration |
| Canada WBT MOFE | No selectable MOFE configuration | `canada-wbt-mofe` preview WBT configuration with cap `5` |

## Rationale

An explicit per-configuration value prevents the 19-OFE fallback from silently
governing new MOFE runs and keeps segmentation complexity bounded consistently
across existing and Canada WBT MOFE setups.

## Alternatives Considered

1. Change the global fallback from 19 to 5 — rejected because that would alter
   legacy and non-MOFE configurations that do not opt into this parameter.
2. Change only the CONUS WBT MOFE configuration — rejected because all MOFE
   configurations need the same explicit limit.
3. Retain the 19-OFE cap — rejected by the decision owner due to unnecessary
   segmentation complexity.

## Consequences

New runs created with an MOFE configuration will contain no more than five OFE
segments per hillslope, subject to the existing lower bound and available-cell
limit. Existing persisted runs retain their current saved watershed settings.

## Evidence

- `wepppy/nodb/core/watershed.py`: absent-option fallback is 19.
- `wepppy/nodb/core/watershed_mixins.py`: segmentation applies the configured
  cap after existing cell-count and safety-bound checks.
- `tests/weppcloud/routes/test_feature_registry_runtime.py`: validates every
  registry-exposed MOFE configuration declares the cap as 5.

## Risk and Rollback Notes

The lower cap can reduce spatial segmentation detail for newly created runs.
Rollback is to restore the prior configuration value or omission; no migration
or generated-run artifact rewrite is required.

## Implementation Notes

The runtime safety ceiling remains 19. This ADR changes configuration defaults,
not the controller's accepted input range or segmentation algorithm.
