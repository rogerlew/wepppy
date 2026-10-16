# ADR-0097: MACA projection selection and CCSM4 member

## Status

Accepted intent; implementation pending the reviewed checkpoint.

## Decision and provenance

Venue: Codex operator conversation, 2026-10-16 UTC. Participants: requesting
operator and Codex. Decision owner: requesting operator. Implementer: Codex.
The operator requested a model/scenario select like EDDE, approved the MACA
attribution, and then directed: "okay. let's implement the selection anf patch
the client". Earlier checkpoint commit authorization remains in effect for
local reviewed documentation checkpoints; no deployment is requested.

Expose the 20 MACA models crossed with RCP4.5/RCP8.5, preserving the actual
GFDL-ESM2G/RCP8.5 default for new/legacy projects and direct helper callers.
Select CCSM4 member r6i1p1; other supported models use r1i1p1. Previously the
client incorrectly constructed every model's path with r1i1p1, causing CCSM4
HTTP 500 errors. No formulas, unit conversions, scaling or CLIGEN defaults change.

## Rationale and alternatives

Combined selection matches the EDDE interaction and prevents unsupported model/
scenario pair strings. Explicit source membership matches provider identities;
retrying alternate members would conceal a scientific input change. Removing
CCSM4 was rejected because correcting only its member succeeded for all seven
variables under both scenarios. A different default would change existing runs.

## Compatibility, evidence and rollback

Persist one additive optional field, validate before enqueue, and retain existing
catalog IDs and mode numbers. Old payloads omit the field and retain the saved
choice; legacy objects without it use the old implicit default. Reject explicit
invalid selections rather than interpreting them as omission.

Evidence: [source-member diagnosis](../dev-notes/maca-ccsm4-source-member-diagnosis.md)
and [canonical selection contract](../schemas/maca-cmip5-selection-contract.md).
Regression covers request-to-disk-to-retrieval propagation and actual generated
CLI data. Rollback to a reader that ignores the new field would silently rebuild
nondefault projects with the old default: retain selection-aware readers/builders
or explicitly return affected projects to the default before such a rollback.
