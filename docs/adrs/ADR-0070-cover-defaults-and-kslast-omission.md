# ADR-0070: Propagate cover defaults and preserve omitted kslast

Status: accepted intent; implementation conformance pending.

## Context and decision

Configured cover defaults currently update summaries after MOFE generation.
Regenerate once when defaults apply, using saved segment assignments, even on
retry with unchanged saved values. Preserve existing default precedence and RAP
canopy semantics. Omitted kslast currently clears the saved conductivity override;
preserve it instead. Explicit clearing/set semantics stay unchanged.
No numerical defaults, formulas, units or compiler policies change.

## Provenance and rationale

Venue: user/Codex workspace conversation, 2026-09-19 America/Los_Angeles;
exact message time unavailable. Participants and decision owners: requesting
user and Codex (implementer). Operator authorized this package and explicitly
deferred WEPP executable work. Honor stored intent at the executable boundary;
do not treat an omitted field as a request to alter a scientific parameter.

Alternatives rejected: moving default application before management summaries
exist; rebuilding per field/class; skipping unchanged values after failure;
changing default precedence; requiring every API client to resubmit kslast.

## Evidence, risk and rollback

[Work package](../work-packages/20260919_cover_defaults_api_omission/package.md).
Canonical rules: [MOFE artifacts](../schemas/mofe-management-artifact-contract.md)
and [WEPP run inputs](../schemas/wepp-run-input-contract.md).
Existing outputs do not change on deployment; rebuild/rerun is required.
New runs can differ where previously stale covers or unintended kslast clearing
affected inputs. Validate real inputs before numerical attribution. Revert the
bounded source change on regression; retain failed artifacts and diagnostics.
