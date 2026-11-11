# Correctness review - Status and preflight WebSocket run authorization

**Status**: Pending implementation and independent review  
**Date opened**: 2026-11-11 UTC  
**Reviewer**: Unassigned

## Review Scope

Review the final diff and evidence for token issuance, browser transport and
refresh, both Go validators, Redis/session ordering, Origin configuration,
message redaction, generated-controller parity and forest acceptance. This
artifact is a gate scaffold, not a review verdict.

## Required Correctness Checks

- [ ] The implementation matches the ratified valid-state matrix for private,
      collaborator/admin and public cases.
- [ ] Run/config normalization is identical at mint, browser URL and both
      validators; no alternate spelling or encoded path bypasses equality.
- [ ] Validation occurs before WebSocket acceptance and before any run-specific
      Redis operation in both services.
- [ ] Claim time/skew, audience, scope, class and session-state behavior matches
      the contract and fails closed on parse/config errors.
- [ ] Browser refresh/reconnect is bounded, does not downgrade to anonymous and
      does not create duplicate sockets/listeners.
- [ ] Generated status JS corresponds to source and preflight behavior remains
      compatible with current pages.
- [ ] Message redaction preserves intended status/preflight fields and does not
      hide actionable safe state.
- [ ] Rendered forest and production configuration contains required secret
      mounts, Redis DB and exact Origins without raw secret values.
- [ ] Focused and full validation receipts correspond to the reviewed revision.
- [ ] Actual forest E2E corresponds to the redeployed container identities and
      proves both positive and negative cases.

## Findings

Populate with severity, exact location, evidence, required correction and final
disposition. Do not mark this review passed while any correctness finding or
required evidence remains open.

## Gate Verdict

**PENDING** - no implementation or validation has been reviewed.
