# Design Review Disposition

**Date**: 2026-08-23
**Gate**: Bearhive rehearsal implementation authorized; production blocked

Independent correctness, security, operations, and UX/governance reviewers
agree that namespacing plus SID-preserving migration is the right direction.
They also identified three high-severity contract gaps that must be resolved in
the checkpoint before implementation.

## Blocking Findings

| Finding | Risk | Proposed disposition | Status |
| --- | --- | --- | --- |
| Multiple live signed legacy SIDs | Wire order could silently choose the wrong account | Inspect bounded live candidates only for conflict detection; authorize only the first signed candidate when every live candidate has the same principal/state class; fail closed on authenticated-principal or authenticated/anonymous conflict | Contract ratified; implementation evidence pending |
| Logout/reset resurrection | Removing the primary cookie can expose another live legacy session | On explicit logout/reset, boundedly validate and revoke every presented WEPPcloud-signed SID server-side without deleting generic browser cookies; fence late responses; test primary and legacy SIDs that differ | Contract ratified; implementation evidence pending |
| Mixed workers and rollback | Legacy-only `wepp.cloud` workers cannot read newly issued sessions | Phase 1 deploy migration readers to every `wepp.cloud` web and rq-engine instance while still writing `session`; phase 2 flip all production writers with no legacy-only overlap; recover only from a pinned migration-aware Git revision through `scripts/deploy-production.sh` | Contract ratified; canonical deploy-script rehearsal pending |

## Medium Findings

- Define identical raw-header semantics for duplicate primary cookies, multiple
  Cookie fields, malformed payloads, Redis errors, and signed missing SIDs.
- A signed SID with no Redis record must never be reused; recovery creates a
  fresh unpredictable SID.
- Ratify aggregate-header, candidate-count, value-length, and Redis-lookup
  limits. Reject rather than truncate.
- Define explicit secure-host, local-HTTP, and test profiles for the `__Host-`
  invariant and inventory same-origin cookie writers.
- Remove raw SID logging from rq-engine migration-adjacent error paths.
- Add a shadow/read-only measurement phase and value-free abort thresholds
  before activating the new writer.
- Replace logout/sign-in repair guidance with an accessible, state-preserving
  exceptional path. Never silently retry a mutation.
- Cover Edge as well as Safari, Firefox, and Chromium, including concurrent
  tabs, OAuth callback, CAP, anonymous sessions, and old-page first POST.
- Start compatibility-retirement timing after the last legacy writer is gone;
  removal is a separate reviewed release after at least one 12-hour inactivity
  window plus deployment and observation margin.

Fleet scope is intentionally narrow: only `wepp.cloud` is production.
Bearhive deployments are dev/test validation targets and do not participate in
production cookie or session migration.

## No-User-Action Assessment

The intended contract preserves the complete Redis payload and SID for every
recoverable legacy session, including users without remember tokens and
anonymous CAP/CSRF state. No normal migration step asks a user to log out, sign
in, clear cookies, or clear site data. This is not yet a deployment guarantee:
the blockers above, recovery UX, fleet inventory, shadow telemetry, and browser
evidence must close first.

Unrecoverable state means the server-side Redis session is already absent or
corrupt. It cannot be reconstructed from a cookie. A valid remember token may
restore identity into a fresh SID, but must not be presented as preservation of
CSRF, OAuth, CAP, or unsaved form state.
