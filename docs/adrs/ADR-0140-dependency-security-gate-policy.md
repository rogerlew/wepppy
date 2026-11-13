# ADR-0140: Bind dependency-security decisions to the candidate image

Status: Accepted; implementation and deployment validation pending  
Date: 2026-11-11

## Context

The dependency audit retained an advisory count without an exact image,
database identity, or raw report. Requirements alone do not describe installed
Debian/Python packages, vendored code, downloaded binaries, or emitted browser
assets. A release decision needs reproducible evidence for the image that will
actually run, with explicit treatment of scanner omissions and exceptions.

## Decision

Gate the selected common WEPPcloud image and primary frontend lock before
activation, using one repository-owned policy interface for CI and deployment.
Bind native SBOM, scan, direct inventory, and npm evidence to immutable image
and lock identities and retained report hashes. Distinct unrelated images are
not covered by this gate.

Reports and advisory database build timestamps must be at most 24 hours old;
future timestamps beyond five minutes of clock skew fail. Require successful
database refresh before a new scan. An applicable unresolved Critical/High
finding blocks activation; applicable Medium findings require a fix or an
approved exception. Unknown severity needs explicit review. Low findings remain
tracked. A blocked-follow-up label does not authorize activation.

Accepted-risk records require advisory/package/ecosystem/version/path identity,
image or lock scope, owner and approver, rationale, evidence, compensating
control, creation/expiry timestamps, and review trigger. They expire within
30 days; renewal requires fresh review. Approval hashes come from trusted
operator records outside candidate-controlled inputs. PR authors cannot approve
their own policy or exception changes.

Retain ordinary CI evidence for at least 90 days and activated-image evidence
for at least 365 days and throughout rollback eligibility, whichever is longer.
Use the owner-selected `/workdir/weppcloud-deployments/` private store, with
ignored `.local/dependency-security/` evidence/approval areas, 0700 directories
and 0600 records. Retain database bytes or a retrievable immutable database
artifact reference. Public source contains sanitized summaries and hashes.
Roger selected manual evidence transfer: required raw reports must be imported
into this store and checked against their image/lock identities and hashes
before acceptance. CI success alone is not proof of retention. Production stays
on Docker Compose through installed `wctl` and `scripts/deploy-production.sh`;
manual transfer adds no registry or alternate deployment path.

PR execution must be isolated from production mounts, credentials, registry
write authority, and the production Docker socket. Scanner execution uses
explicit image archives/SBOMs in an unprivileged confined process. Missing or
malformed evidence, partial parser/analysis results, identity mismatch, stale
evidence, and blocking findings fail before any service stop/recreate operation.
Scanner-ignored and matcher-suppressed findings still require disposition.

The gate covers selected common images in full, web, worker, fork/archive,
batch-derived, and retained rollback paths. Targeted CAP alone is excluded.
Recheck selected image IDs immediately before activation; a rollback flag grants
no policy bypass. This decision does not authorize production rollout or any
specific advisory-risk exception.

For host-local Compose deployment, build and record the candidate before any
service stop, then exit for independent evidence collection and review. A later
resume must bind to a host-specific private receipt and reject before service
changes unless the source revision and cleanliness, dependency lock, deploy
script, effective Compose service/image selection, and every immutable local
image ID still match. Immediately before activation, rerun the independent
evidence policy and freshness checks against those exact IDs and approved
disposition hashes. Generic `--skip-build` remains invalid for locally built
services; a retained receipt is not transferable between hosts.

## Decision Provenance

Decision Venue: Codex execution session, 2026-11-11 UTC; approval recorded at
05:41:25 UTC (2026-11-10 in America/Los_Angeles). The exact message timestamp was
not separately retained.  
Participants Present: Roger Lew; Codex.  
Decision Owner: Roger Lew.  
Implementer: Codex; implementation pending the required baseline.  
Review: independent correctness, security, and wepp1 operations agents.

## Change Summary

Previously there was no artifact-bound common-image dependency activation gate
or enforceable freshness/exception/retention policy. The approved limits are
24-hour evidence/database freshness, five-minute future-clock tolerance,
30-day maximum exceptions, and minimum 90-day/365-day evidence retention.
Scientific parameterization, application permissions, runtime identities, and
existing deployment topology do not change under this decision.

## Rationale

Daily freshness bounds advisory staleness. Short, owned exceptions prevent
permanent suppression. Exact artifact readback avoids testing one dependency
image while activating another. Pre-activation failure preserves availability
of the running stack. Retained evidence supports review and rollback decisions.

## Alternatives Considered

1. Manifest-only counts: rejected because installed and unmanaged components
   differ from manifests and build-time resolution can drift.
2. Scanner exit status alone: rejected by qualification trials that produced
   exit zero despite a missed GDAL advisory or recovered parser panic.
3. Permanent exceptions or stale-evidence fallback: rejected because they hide
   unresolved exposure and invalidate the release evidence boundary.
4. A new hosted vulnerability service: unnecessary; reuse the private store,
   existing build/test tooling, and a bounded command-line gate.
5. Waiting for manual review within one deployment invocation: rejected because
   it leaves a long-running privileged process open across an unbounded human
   review interval and complicates interruption and recovery semantics.

## Consequences

Scanner/database outages or newly blocking findings can delay deployment.
Coverage reconciliation includes unmanaged executables and native parser
diagnostics, not only package counts. Private storage and CI ingestion need
operational validation. Full pytest, npm lint, and full npm tests must pass on
the exact final candidate; scanner qualification does not substitute for them.

## Evidence

- [Active implementation plan](../work-packages/20261110_wepp1_dependency_security_gate/prompts/active/implementation_execplan.md)
- [Ratified scope and policy](../work-packages/20261110_wepp1_dependency_security_gate/artifacts/20261110_scope_and_policy_decision.md)
- [M0 receipt](../work-packages/20261110_wepp1_dependency_security_gate/artifacts/20261110_m0_validation.md)
- [Scanner evaluation](../work-packages/20261110_wepp1_dependency_security_gate/artifacts/20261110_scanner_evaluation.md)

## Risk and Rollback Notes

Preserve the known-good image and running services on gate failure. A retained
rollback image must satisfy current policy or have explicit temporary risk
acceptance. No emergency override is created here. Changes to these limits or
authority require a recorded owner decision and an ADR amendment.

## Implementation Notes

The reviewed tool choice is scoped Syft 1.57.1 image-archive inventory followed
by Grype 0.121.3 native-SBOM matching. Tool pins and capabilities require explicit
review when updated. Enforce cataloger/input restrictions, inspect native
analysis uncertainty, include suppressed findings, and preserve explicit
failure status. M3/M4 must prove the wired gate, CI storage path, production-
equivalent identities, and activation ordering before rollout readiness.
