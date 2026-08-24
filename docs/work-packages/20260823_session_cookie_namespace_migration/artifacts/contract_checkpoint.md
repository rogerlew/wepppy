# Proposed Session Cookie Migration Contract Checkpoint

**Status**: Proposed; operator acceptance and independent review pending
**Date**: 2026-08-23
**Security impact**: High

## Authority Matrix

| Authority | Proposed delta | Unchanged behavior |
| --- | --- | --- |
| WEPPcloud session contract | New default name, dual-read migration, no-user-action UX, compatibility retirement gate | Redis DB/key prefix, TTL, signing, remember policy, logout semantics |
| WEPPcloud CSRF contract | Session migration must preserve CSRF binding; ambiguous candidates cannot bypass validation | Route classifications, token sources, same-origin rules |
| Auth-token specification | rq-engine bridge prefers new cookie and safely accepts legacy during rollout | JWT claims, scopes, audience, TTL |
| Session lifecycle specification | Mixed-version migration and rollback sequence | Browser heartbeat and token-refresh lifecycle |
| ADR-0044 | Durable name/default and migration decision | Other authentication defaults |

## Normative Delta

WEPPcloud uses `__Host-weppcloud_session` as its production-owned cookie. During the
approved compatibility window, Flask and rq-engine accept a validated legacy
`session` cookie only when the new cookie is absent. Invalid signatures may be
skipped, but the first correctly signed legacy SID is authoritative and later
candidates cannot revive an absent Redis session. Adoption preserves the SID and Redis payload and
causes the normal Flask response to issue the new cookie. Ordinary migration
does not delete the legacy cookie and requires no user logout, login, or site
data clearing.

Any occurrence of the new name is authoritative and cannot downgrade to legacy.
Migration occurs before authentication and CSRF hooks, so a first POST works.
Candidate parsing is bounded and duplicate-aware. Production enforces Secure,
Path `/`, and no Domain. Credential and identity values are never logged.

## Compatibility and Data Impact

No project data or schema changes. Redis session payloads and keys remain in
place; migration changes only the browser cookie name used to reference the
same SID. Users without remember tokens retain valid sessions when exactly one
safe legacy session is recoverable. Generic legacy cookies remain untouched.

## Explicit Exclusions

No secret rotation, TTL change, remember-policy change, CSRF exemption,
authorization widening, parent-domain cookie deletion, JavaScript cookie
inspection, or silent cross-account selection.

## Required Evidence Before Implementation

- Operator acceptance of this exact matrix and ADR-0044.
- Independent correctness, security, operations, and UX/governance reviews.
- Disposition of every medium/high finding.
- Standalone committed checkpoint ancestor before production code edits.
