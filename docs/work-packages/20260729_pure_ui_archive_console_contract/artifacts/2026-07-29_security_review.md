# SURF-03 Security Review

**Date**: 2026-07-29 UTC
**Security impact**: `high`
**Disposition**: Pass; no unresolved high or medium findings

## Boundary Reviewed

The review covered run authorization, renewable rq-engine session
authorization, server-owned URLs, hostile archive metadata, destructive
restore/delete confirmation, mutation exclusion, active-job state, archive
filename validation, download and extraction confinement, integrity/disk/lock/
cache safeguards, errors, and terminal refresh/navigation.

## Evidence

- The dashboard authorizes the exact run/config before rendering its
  server-owned list, mutation, project, script, and stylesheet URLs.
- Actual rendering escapes hostile identity values. The client inserts archive
  metadata with text nodes and consumes only server-returned download URLs.
- Create, restore, and delete use renewable session authorization. Existing API
  tests retain authenticated run-access, stale-job, active-job, input, and
  enqueue checks.
- Restore and delete require confirmation and submit the exact selected
  `archive_name`; cancellation performs no request.
- The repaired client disables every mutation control from restore/delete
  submission through response reconciliation, preventing conflicting
  destructive operations before the shared active-job slot is established.
- Stream signals do not manufacture terminal state; polling reconciles
  authoritative state before list refresh and restored-project navigation.
- Worker evidence retains confined archive paths, traversal rejection, zip
  integrity checks, disk headroom, NoDb locks/cache, and failure triggers.
- The repair changes no authorization rule, token class, path rule, archive
  format, route, queue edge, worker signature, external dependency, secret,
  parameter, or default.
- Auth/security-focused tests pass 17 cases; archive API/worker tests pass 32;
  route/render tests pass 166; all 23 direct console tests pass.

## Findings and Disposition

The one confirmed finding was a request-window race between sibling archive
mutations. It is resolved by the minimal client-side mutual-exclusion repair
and direct regression coverage. Backend authorization, active-job exclusion,
filename validation, and filesystem safeguards remain the enforcement
boundaries.

No unresolved high or medium finding remains. `wctl check-rq-graph` passes; its
two pending metadata updates are separate work that predates SURF-03.
