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
script, installed `wctl` identity, deploy mode/options, secret-safe canonical
rendered Compose projection, and every service-to-image ID still match. Bind the
host with `/etc/machine-id`, hostname, and Docker Engine ID; all three must match
on resume.

Store candidate directories beneath
`/workdir/weppcloud-deployments/.local/dependency-security/candidates/` and
operator approvals beneath the sibling `approvals/` authority. Directories are
0700 and files 0600, owned by the invoking operator, non-symlinked, atomically
published and fsynced. The receipt schema includes its version, creation time,
host/daemon identities, source/build identities, effective configuration hash,
selected services, immutable image map and retained activation-file hashes. The
approval path is derived only from the protected authority root plus the
candidate-receipt hash; it is never accepted from the candidate receipt, CLI or
environment. That separate record binds the candidate hash to evidence manifest,
policy and disposition hashes.

Activation must consume the frozen IDs, not mutable tags. Retain the rendered
Compose configuration and an override mapping every selected locally built
service to its `sha256:` image ID. After validating the current projection,
activate through the canonical deploy script using only those private retained
files with build and pull disabled. Revalidate the receipt and independent
evidence policy before the first service change and again after any warm wait,
immediately before each activation attempt. Verify running container IDs after
activation as defense in depth, not as the primary substitution control. Generic
`--skip-build` remains invalid; a retained receipt is not transferable between
hosts or Docker daemons.

Drain default/batch work while the current containers remain running: acquire
the owned RQ dequeue fence, wait for started registries to reach zero, and rerun
the complete receipt/evidence gate before stopping any service. A gate failure
releases only the deployment-owned fence and leaves the prior workload running.
Immediately before cutover, also retain the current rendered configuration and
running service-to-image ID map. Once any service stop begins, every error path
must restore that unchanged known-good map with build/pull disabled, verify the
restored container IDs, and only then release the RQ fence. Failed restoration
keeps the bounded fence and returns an explicit recovery signal; it never starts
an unapproved candidate or resumes dequeue into a partial stack.

## Decision Provenance

Decision Venue: Codex execution session, 2026-11-11 UTC; approval recorded at
05:41:25 UTC (2026-11-10 in America/Los_Angeles). The exact message timestamp was
not separately retained.  
Participants Present: Roger Lew; Codex.  
Decision Owner: Roger Lew.  
Implementer: Codex; implementation pending the required baseline.  
Review: independent correctness, security, and wepp1 operations agents.

Amendment Venue: Codex execution session, 2026-11-13 UTC. Roger answered
“yes” to the explicit question authorizing retained-candidate resume: build once,
pin activation to immutable image IDs, independently review evidence, and resume
the same host-local Compose candidate without rebuilding. This authorizes the
workflow implementation and validation; it does not authorize M5 production
service interruption or activation.

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
