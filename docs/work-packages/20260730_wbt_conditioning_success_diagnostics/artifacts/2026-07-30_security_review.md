# Security Review - WBT Conditioning Success Diagnostics

## Metadata

- **Package**: `20260730_wbt_conditioning_success_diagnostics`
- **Reviewer**: independent operations/security control agent
- **Date**: 2026-07-30
- **Context**: documentation checkpoint based on WEPPpy
  `c3deac7fab363bf1babe363019c88e2f8694b8c5` and WBT
  `b4d8774e3375ffd86a487c172f84e0d3f8a6cc50`
- **Scope**: native WBT sidecar, run filesystem, parser, RQ metadata/status,
  controllers, rollout, and rollback

## Triage and Threat Assumptions

- **Impact**: high; dedicated review required.
- The browser cannot choose the sidecar path or operation id.
- A stale, partial, oversized, malformed, symlinked, or cross-job artifact is
  hostile input at the WEPPpy boundary.
- Status streams may reconnect/replay, and polling may complete without the
  live trigger.
- WBT and WEPPpy can briefly differ during fleet rollout or rollback.

## Findings and Disposition

| ID | Severity | Finding | Required action | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | High | Sidecar atomicity, confinement, and freshness were underspecified | Require same-directory temp/fsync/rename, operation identity, symlink-safe run confinement, and race/failure tests | Resolved in schema checkpoint |
| SEC-02 | High | No exact bounded schema | Define exact keys/types/enums/limits/consistency and adversarial parser tests | Resolved in schema checkpoint |
| SEC-03 | High | Status transport/correlation/replay undecided | Define job-meta, aggregate polling, base64url trigger token, size, job binding, and replay behavior | Resolved in schema checkpoint |
| SEC-04 | High | Failure cleanup and two-repository rollback absent | Define controlled error, suppression/cleanup, install order, retained hashes, and rollback order | Resolved in schema checkpoint |
| SEC-05 | Medium | Least-cost fallback conflicted with fail-fast contract | Scope fallback diagnostics to standalone WBT and require no fallback in WEPPcloud success | Resolved in schema checkpoint |

## Required Surface Checks

- Auth, session, CSRF, secrets, routes, queue edges, and egress remain unchanged.
- Fixed paths resolve beneath the run root; symlink targets are rejected.
- WBT invocation remains argv-based without shell interpolation.
- Parser rejects oversized, unknown, duplicate, missing, wrong-type, negative,
  non-finite, inconsistent, control-character, stale, and mismatched data.
- Only allowlisted reduced scalars enter RQ metadata/status.
- Controller verifies job correlation and renders text only.
- Failure occurs under the watershed lock and leaves no completion timestamp or
  downstream success artifacts.
- Rollout installs WBT first; rollback removes WEPPpy dependency first.

## Validation Boundary

Local completion requires exclusive same-directory temp creation, explicit
flush/fsync/rename code inspection, stale-target removal, operation identity,
descriptor-relative no-follow consumption, exact parser rejection, cleanup,
trigger/poll correlation, focused Python/frontend tests, WBT tests and fixture
executions, output checks, docs lint, and final changed-surface review.

OS crash injection, fleet-wide mixed-version execution, retained binaries on
each worker, and deployment rollback drills belong to the separate production
promotion gate. Promotion installs WBT first; rollback removes the WEPPpy
dependency first.

## Verdict

- **Checkpoint gate**: pass; independent operations/security post-fix review
  found no remaining blocking, high, or medium findings.
- **Unresolved high**: 0 in the revised normative design.
- **Unresolved medium**: 0 in the revised normative design.
- **Implementation release recommendation**: hold until tests and final review
  prove conformance.

## Residual Risk and Rollback

No threshold-based interpretation is provided, so users must interpret
magnitudes in project context. This is intentional and owned by the operator.
Retain the prior WBT binary/hash; deploy WBT before WEPPpy and roll back WEPPpy
before WBT.

## Sign-off

- **Checkpoint security reviewer**: operations/security control agent,
  2026-07-30, PASS
- **Final implementation security reviewer**: operations/security control
  agent, 2026-07-30, PASS; no unresolved high or medium findings
- **Final governance reviewer**: governance control agent, 2026-07-30, PASS;
  no unresolved high or medium findings
- **Package owner**: Codex, 2026-07-30
