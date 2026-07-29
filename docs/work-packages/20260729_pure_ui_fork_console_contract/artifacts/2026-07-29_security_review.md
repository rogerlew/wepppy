# SURF-04 Security Review

**Date**: 2026-07-29 UTC
**Security impact**: `high`
**Disposition**: Pass; no unresolved high or medium findings

## Boundary Reviewed

The review covered run authorization, anonymous public/CAP access,
authenticated bearer/session renewal, exact fork options, destination
allocation and ownership, scoped browser recovery, cancellation, status/job
metadata, filesystem copy and symlink defenses, persisted identity
normalization, hostile values, errors, and terminal state.

## Evidence

- The WEPPcloud route authorizes the source run before rendering and mints an
  rq-engine token only for authenticated users.
- Actual renders escape hostile run/config/site/token values and preserve exact
  server-owned option defaults.
- Anonymous submission remains disabled until the `fork` CAP section supplies
  a nonempty token; the token is sent only in the direct fork POST.
- Authenticated submission uses the rendered bearer token with renewable
  session-token fallback. Existing API tests retain token-class, run-access,
  public-run, CAP, and target-run validation.
- Browser storage is keyed by encoded source/config and contains only
  source/config/job/destination identifiers. Invalid and cross-scope records
  are removed; no CAP, bearer, or session token is stored.
- Hostile restored destination identifiers render as text and use an encoded
  link with `noopener`.
- Cancellation targets only the accepted job id and retains rq-engine
  authorization/ownership checks.
- Stream triggers cannot manufacture terminal state; authoritative polling
  confirms completion/failure and terminal handlers are idempotent.
- Worker evidence retains source/destination confinement, symlink rejection,
  preflight-before-write behavior, atomic rollback, copied identity cleanup,
  marker/cache handling, copy exclusions, and failure triggers.
- No authorization rule, token class, storage field, route, queue edge, copy
  rule, secret, external dependency, parameter default, or production code
  changed.

## Findings and Disposition

No security finding was identified. The administrative predecessor close and
new regression tests introduce no runtime attack surface.

The RQ dependency checker reports preexisting static artifact drift. Because
SURF-04 changes no queue wiring, regenerating those artifacts would broaden the
package and is not a security remediation.
