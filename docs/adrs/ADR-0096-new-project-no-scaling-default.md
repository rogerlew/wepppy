# ADR-0096: Explicit NoScaling default for new projects

## Status

Accepted by the operator; implemented and locally validated after checkpoint
`88c8c9fdc`. Production deployment remains separate.

## Decision and provenance

Decision venue: Codex conversation, 2026-10-16, recorded 17:57 UTC.
Participants: requesting operator and Codex. Decision owner: requesting
operator. Implementer: Codex.

The operator requested: "let's fix the blank radio selection for new projects.
the default should be NoScaling".

After all existing configuration precedence resolves, initialize an otherwise
unset precipitation scaling mode to `ClimatePrecipScalingMode.NoScaling` (0).
Previously the stored value remained `None`, leaving every scaling radio blank.
Both states execute without precipitation scaling; numerical behavior is
unchanged. Configured scaling modes/factors retain their precedence.

## Rationale and alternatives

An explicit persisted default makes the existing radio control represent the
new project's effective behavior. A template-only fallback would leave stored
state inconsistent with the selection. Changing the getter would also affect
existing projects, outside this request's new-project scope. Neither is needed.

## Compatibility, evidence and rollback

No new keys, schema version, formulas or scaling factors. Existing projects are
not migrated. Constructor tests must cover unset and configured modes through
persistence/reload, and template rendering must assert exactly the default
radio is checked. Verify generated climate behavior remains unscaled through
the existing EDDE regression. Roll back the constructor assignment if configured
precedence changes; retain saved enum values, which existing readers support.

Evidence: [incident diagnosis](../dev-notes/edde-none-scaling-incident.md) and
[current contract](../schemas/climate-precipitation-scaling-contract.md).
