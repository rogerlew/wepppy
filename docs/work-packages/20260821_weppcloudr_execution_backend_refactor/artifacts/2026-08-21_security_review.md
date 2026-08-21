# Security Review — WEPPcloudR Execution Backend Refactor

**Review state**: Pending implementation
**Gate**: FAIL (open review; package must not close)
**Reviewer**: Unassigned independent security reviewer
**Date opened**: 2026-08-21

## Scope

Review backend selection, subprocess/Job authority, request and path validation,
run-scoped file access, logging, receipt integrity, reconciliation,
cancellation, timeout, locking/fencing, and the authorized forest operation.
Kubernetes build/deployment configuration is explicitly outside this review and
must receive its own review before deployment.

## Required Threat Checks

- [ ] Unknown or unavailable backends fail closed without cross-backend fallback.
- [ ] User-controlled values cannot become shell fragments, Docker targets,
  Kubernetes names/labels, or arbitrary paths.
- [ ] `run_root` and `active_root` remain run-scoped while expected PUP links to
  the parent continue to work.
- [ ] Durable receipts cannot be forged or reused across users/runs/renders.
- [ ] Retries, cancellation, timeout, and reconciliation cannot let stale work
  publish over a newer render.
- [ ] Job/RQ logs are bounded, access-controlled, and free of secrets/tokens.
- [ ] Kubernetes client authority is least-privilege by interface; deployment
  RBAC remains blocked on the separate package.
- [ ] Compose retains its existing Docker-socket and mount exposure without
  broadening it.
- [ ] Forest execution remains inside the explicit host/run authorization.

## Open Findings

| ID | Severity | Finding / evidence required | Disposition |
|---|---|---|---|
| SEC-01 | High | Backend and command construction require implementation review and adversarial tests. | Open |
| SEC-02 | High | Run-WD/PUP symlink validation requires traversal and cross-run tests. | Open |
| SEC-03 | High | Receipt ownership, fencing, retry, and cancellation require state-transition review. | Open |
| SEC-04 | Medium | Log bounding/redaction and error translation require implementation evidence. | Open |
| SEC-05 | Medium | Forest preflight and scope adherence require captured operational evidence. | Open |

## Gate Decision

FAIL until an independent reviewer examines the implementation and test evidence,
all findings are dispositioned, and no unresolved medium/high issue remains.
