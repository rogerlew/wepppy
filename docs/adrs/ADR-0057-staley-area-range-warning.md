# ADR-0057: Warn outside the Staley study area range

Status: Accepted

Date: 2026-09-09

## Context

The supplied Staley accepted manuscript, printed page 12, reports study
catchments of 0.2–8 km². The earlier WEPPpy 0.02 km² lower bound lacked source
support. The owner selected the manuscript as authoritative, then requested
warnings rather than hard failures outside its reported range.

## Decision

For both M1 and M3, warn below 0.2 km² or above 8 km². Both endpoints are
inside the range. Compare full delineated watershed area in unrounded m²
against 200,000 and 8,000,000; display conversion/rounding does not control
the decision. Present the warning with results and reports, while allowing
assessment and preserving numerical outputs. Area alone must not cause a
readiness failure, execution rejection or unavailable result.

The [specification](../../wepppy/nodb/mods/postfire_debris_flow/specification.md#published-coefficients)
defines the canonical policy and warning wording. Integration belongs to
future project results/UI work; the scalar engine has no area parameter.

## Decision Provenance

Decision Venue: repository conversation, 2026-09-09 UTC
(2026-09-08 America/Los_Angeles).

Participants Present: repository owner and Codex.

Decision Owner: repository owner, explicitly selecting manuscript authority
and a warning without hard failure outside its range.

Implementer: Codex (current contracts); runtime integration pending.

## Change Summary

Replace an unsupported 0.02 km² source transcription with 0.2 km² and resolve
the previously open area policy to a nonblocking warning outside 0.2–8 km².
No equation, probability, inverse calculation, or runtime code changes here.

## Rationale and Alternatives Considered

Study coverage is evidence context, not a demonstrated physical validity
boundary. A warning communicates extrapolation while preserving the user's
ability to assess a basin. Hard rejection was explicitly rejected; silence
would hide the study-domain limitation. Do not infer a warning threshold from
pfdf tutorial delineation filters.

## Evidence

- Supplied manuscript: `wepppy/nodb/mods/postfire_debris_flow/docs/pdfs/staley_2017.pdf`,
  printed page 12; source SHA-256 and reading evidence in the
  [publication audit](../work-packages/20260908_staley_watershed_engine/artifacts/coefficient_check.md).
- Explicit owner directions in the repository conversation.

## Consequences and Risk / Rollback Notes

Out-of-range predictions remain extrapolations, not newly validated results.
Future integration must test below, at and above both endpoints, unchanged
numerical outputs, and consistent warning presentation across display units.
Revise this ADR if the owner changes the accepted source or warning policy;
there is no persisted-state migration or runtime rollback in this docs change.
