# ADR: Extend rq-engine OpenAPI size budget for builder endpoints

## Status

Accepted, 2026-08-26.

## Decision Provenance

- **Decision venue**: WP06 implementation session, 2026-08-26, UTC.
- **Participants/owner**: repository operator request; implemented by Codex.
- **Change**: raise the canonical OpenAPI test ceiling from 138,000 to 141,000
  bytes solely for three documented WP06 routes.

## Rationale and Evidence

The authenticated description, validation, and creation operations are a
ratified workflow surface and must retain summaries, auth/write semantics,
operation IDs, tags, and canonical response metadata. Hiding them from OpenAPI
or deleting metadata would make the budget pass while degrading the contract.
The pre-adjustment document with the initial route schema was 138,494 bytes;
the final exact size remains enforced below 141,000.

## Alternatives Considered

Hiding routes from schema and abbreviating required metadata were rejected.
Splitting the rq-engine schema is outside WP06.

## Risk and Rollback

This changes no model parameter, only a CI documentation-size guard. Revert
the routes and this ceiling together if WP06 is reverted. Future growth still
requires an explicit reviewed adjustment.
