# SURF-05 Security Review

**Date**: 2026-07-29 UTC
**Security impact**: `high`
**Disposition**: Pass; no unresolved high or medium findings

## Boundary Reviewed

The review covered Admin rendering and API authorization, rq-engine token
claims, private source-run token handling, exact remote/source and local-target
identity, duplicate submission, status/provenance output, dependent migration
enqueue, filesystem confinement, download verification, error/stacktrace
presentation, and terminal navigation.

## Evidence

- The WEPPcloud route requires login and Admin role. Its direct token test proves
  subject, Admin role, user token class, rq-engine audience, enqueue scope,
  email, and unique token ID.
- The rq-engine submit and status APIs independently require Admin; submission
  additionally requires enqueue scope.
- Actual rendering escapes hostile target-root and bearer-token values and
  retains the exact server-owned API URLs, channels, fields, and defaults.
- Job and migration metadata use text nodes. Hostile job IDs, run IDs, local
  paths, and status data cannot create browser elements.
- The private source-run token is sent only in the authorized submission,
  stripped, stored under a short-lived opaque Redis key, and consumed once by
  the worker. It is absent from job arguments, status serialization, browser
  storage, and provenance.
- The repaired browser latch prevents accidental duplicate remote downloads and
  migration chains during the request and active-job window. Backend Admin,
  validation, and queue boundaries remain authoritative.
- Run/config path components reject traversal. The resolved run directory must
  remain beneath the Admin-selected target root. Downloads are integrity
  checked before provenance registration.
- Migration enqueue remains dependent on successful sync. The RQ dependency
  graph is current.
- Terminal navigation encodes run/config components. Completion/failure is
  idempotent, preserves visible evidence, and refreshes authoritative status.
- No authorization rule, token class, token TTL, target-root policy, download
  rule, migration behavior, queue edge, external dependency, secret, parameter,
  or default changed.

## Findings and Disposition

One medium-impact client finding was reproduced: repeated submission could
enqueue duplicate remote downloads and dependent migration work before the
operator received terminal feedback. The minimal dashboard-local latch resolves
that finding and is covered by direct pending-request, completion, failure, and
repeat-initialization tests.

No unresolved high or medium finding remains.
