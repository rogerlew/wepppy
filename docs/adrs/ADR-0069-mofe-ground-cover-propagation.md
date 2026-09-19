# ADR-0069: Honor saved MOFE ground-cover selections

Status: Accepted; implementation and Forest conformance validated 2026-09-19.
Production deployment is not included.

## Context and decision

MOFE synthesis ignored saved interrill/rill ground cover while displaying it in
landuse summaries. Apply these independent fractional selections after template
and disturbed replacements; preserve them on summary rebuild and regenerate on
coverage edits. Preserve all defaults, units, formulas and RAP canopy precedence.
The [canonical contract](../schemas/mofe-management-artifact-contract.md) governs
this bounded propagation correction.

## Decision provenance

Venue: user/Codex workspace conversation, 2026-09-18 America/Los_Angeles
(execution continues 2026-09-19 UTC; exact message time unavailable).
Participants: requesting user and Codex. Decision owner: requesting user.
Implementer: Codex. Authorization: scaffold and execute correction with Forest
`equestrian-bonheur` validation. No meeting attendees inferred.

## Rationale and alternatives

Old behavior: saved ground selections ignored by MOFE generation and potentially
cleared on summary rebuild. New behavior: selected values reach generated and
prepared inputs. Rejected retaining inactive metadata or manually patching
managements because neither makes normal workflow selections reliable.

## Evidence, risks and rollback

See the [work package](../work-packages/20260918_mofe_ground_cover_propagation/package.md).
The motivating observation was saved 0.90 ground cover but generated/prepared
0.75 on `hysterical-sourdough`; no production repair is included here.
Old projects can change results when rebuilt because formerly ignored saved
selections now apply. Inspect selections before rebuilding. No claim about the
direction or magnitude of sediment response. Revert code if propagation or
unchanged-workflow acceptance fails; retain validation evidence and do not
silently rewrite existing results.
