# ADR-0027: Click-Only Cap.js Challenge Parameterization

Status: Accepted

Date: 2026-07-27

Review Date: 2026-08-10

## Context

Users reported that the proof-of-work CAPTCHA on local password login took too
long. The Cap.js server was called without challenge options and therefore used
the library defaults: 50 challenges, 32 bytes per challenge, and difficulty 4.
The authentication incident on the same date made this usability cost more
visible, although CAPTCHA computation did not cause the route-prefix or CSRF
failure.

The Cap service is shared by login, registration, anonymous create/fork
actions, and invisible CAPTCHA gates. It cannot change login difficulty alone
without adding a second site key or a scope-specific challenge protocol.

## Decision

Use one challenge at difficulty 1 for all WEPPcloud Cap.js challenges. Keep the
32-byte challenge size, token redemption, server-side token validation, secret
handling, expiry, and fail-closed behavior unchanged.

Expose the two values as `CAP_CHALLENGE_COUNT` and
`CAP_CHALLENGE_DIFFICULTY`. Both default to `1` and accept only positive
integers.

## Decision Provenance

Decision Venue: Codex operator conversation, 2026-07-27 11:16 PDT

Participants Present: WEPPcloud operator, Codex

Decision Owner(s): WEPPcloud operator

Implementer(s): Codex

## Change Summary

| Parameter | Previous | Accepted |
| --- | ---: | ---: |
| Challenge count | 50, Cap.js library default | 1 |
| Challenge difficulty | 4, Cap.js library default | 1 |
| Challenge size | 32 bytes | 32 bytes, unchanged |

The expected user experience changes from a noticeable proof-of-work wait to
an effectively click-only interaction.

## Rationale

The operator prioritized login usability after user complaints. A single
difficulty-one challenge preserves the CAPTCHA token protocol and basic
interaction gate without imposing noticeable computation on legitimate users.
Explicit environment values also make future changes observable and
reviewable.

## Alternatives Considered

1. Keep 50 challenges at difficulty 4 - rejected because it preserves the
   reported login delay.
2. Reduce only challenge count or only difficulty - rejected because the
   operator requested an effectively click-only interaction.
3. Apply the reduction only to login - rejected for this change because the
   shared Cap endpoint has no trustworthy workflow scope; doing so would
   require separate service credentials or a signed scope contract.
4. Remove CAPTCHA validation - rejected because it would eliminate the token
   gate rather than reduce its proof-of-work penalty.

## Consequences

Legitimate users should see substantially faster login and registration
interactions. Automated clients also incur substantially less computational
cost. Cap token issuance, redemption, expiry, and server-side validation still
apply, but proof of work is no longer a meaningful substitute for explicit
rate limiting or abuse detection.

Because the service is shared, the lower penalty also applies to anonymous
create/fork actions and invisible gates.

## Evidence

- User complaints reported during the 2026-07-27 authentication incident.
- `docs/infrastructure/incident-2026-07-27-flask-security-double-prefix-csrf.md`
- `@cap.js/server` 4.0.5 defaults in its `createChallenge()` implementation.
- Compose and service configuration validation in the implementation commit.

## Risk and Rollback Notes

Monitor authentication failures, account-creation volume, anonymous project
creation, and Cap challenge/redeem traffic through 2026-08-10. Unexpected
automated abuse is the rollback trigger.

Rollback by setting `CAP_CHALLENGE_COUNT=50` and
`CAP_CHALLENGE_DIFFICULTY=4`, then recreating the Cap container. Prefer adding
explicit endpoint rate limits if abuse occurs; raising client computation again
should require evidence and an ADR update.

## Implementation Notes

The Cap service validates both environment settings as positive integers and
fails startup on invalid configuration. Deployments must rebuild the Cap image
and recreate the Cap container for the new server behavior to take effect.
