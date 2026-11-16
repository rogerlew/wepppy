# User-file staging lifecycle

Status: UFS-01 accepted intent (2026-11-16); candidate implemented and scoped validation passed; no production rollout.

## Scope and adoption

This contract governs project-owned staging of user-provided files for consumers
that explicitly adopt it. `_limbo` is a staging location, not a file identity or
a new storage service. The first consumer is the
[Omni SBS control](../ui-docs/contracts/omni-sbs-control-contract.md).
Other upload workflows retain their existing contracts until explicitly enrolled.
[Upload admission](upload-endpoint-contract.md) governs format/size validation;
[NoDb persistence](nodb-persistence-concurrency-contract.md) governs state commits.

## Ownership and acceptance

Every accepted input has a server-owned project and consumer association. Request
row position and basename alone MUST NOT establish that association. A submitted
reference selects an existing association; it does not authorize filesystem access.
Consumers specify their staging layout and permitted resolution locations, validate
containment, and preserve existing access controls and file validation.

Validate a candidate before accepting it. A failed replacement MUST preserve the
previous accepted association and its usable file. Stage replacements separately
until their association is accepted; do not overwrite another accepted input just
because a row moved. Multi-input requests validate all inputs before publishing
accepted state. A failed request may leave unreferenced staging files, but these
MUST NOT become selectable merely by directory enumeration.

## Consumption and resolution

Consumers document how accepted inputs move or copy into their working projects.
After verified copy a consumer MAY consume the staging source if its documented
resolution rule still supports the required subsequent use. Loss of a temporary
file alone is not loss of input when its associated consumer copy remains usable.

Resolve only the associated file in the consumer's documented locations. A
present but invalid or unreadable preferred source is an explicit failure, not
permission to substitute an older copy. If the preferred source is absent, the
consumer MAY resolve its documented secondary location and validate it normally.
Preserve needed input outside a consumer project before destructive reset.
Input availability does not establish that previous execution outputs are fresh.

## Replacement, failure, and cleanup

Only accepted replacement changes the current association. Failed validation or
state persistence leaves the previous association usable. Consumers recheck
validated bytes and the saved association at the persistence boundary under
existing concurrency rules. Do not claim isolation from arbitrary filesystem
writers beyond those rules.

The owning consumer controls cleanup. It may delete its staging source after
verified consumption or remove unreferenced files when no accepted or in-progress
operation needs them. Project deletion may remove project-owned files. This
contract introduces no age-based cleanup, daemon, retention timer, or cross-project
sweep. A filename or old modification time alone never proves cleanup eligibility.

## Rationale

User uploads can outlive their temporary staging location. A shared lifecycle
keeps validation, replacement, consumption, and recovery consistent while leaving
concrete paths and execution semantics with each consumer. It requires no generic
storage framework, identifier migration, or historical receipt scheme.
