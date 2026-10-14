# WMesque Priority Retrieval and Master Catalog Synchronization

**Status**: Open — scaffolded; implementation not started
**Started**: 2026-10-14 20:16 UTC
**Owner**: Roger Lew
**Implementation location**: forest WEPPpy checkout

## Overview

Allow deployments to select WMesque servers in priority order while retaining
wepp.cloud as the default. Receiving deployments synchronize master resources
from wepp.cloud and may maintain local extensions. When master adopts an
extension, ordinary synchronization takes ownership under the same identifier.

The current deliverable is planning scaffolding only. This package remains open
until implementation, artifact validation, reviews, and authorized rollout are
recorded separately; creating these documents does not complete the feature.

## Authority and References

- [Catalog governance](../../infrastructure/wmesque-catalog-governance.md) is the durable authority for ownership, adoption, consistency, and deployment defaults.
- [Static assessment](../../infrastructure/wmesque-implementation-assessment.md) records source evidence, proposed interfaces, rollout constraints, and tests.
- [Dataset inventory](../../infrastructure/wmesque-dataset-sync-manifest.md) identifies requested resources, not verified revision identity.
- [Active ExecPlan](prompts/active/wmesque_catalog_sync_execplan.md) governs execution; [tracker](tracker.md) records status.

## Objectives and Scope

Implement v2 endpoint selection in the common client, additive revision metadata
in the server, verified resource publication, and opt-in receiving-side scheduled
RQ synchronization. Validate on forest before production and Kubernetes rollout.
Preserve explicit endpoint overrides, legacy v1 behavior, local extension
identifiers, and default remote-only retrieval. Update operator, developer, and
user-facing provenance documentation with the implementation.

Automatic project-wide pinning, historical-version APIs, retention automation,
v1 removal, multi-master reconciliation, automatic discovery, and a new scheduling
framework are out of scope. New deployment permissions or topology are not
authorized by scaffolding this package.

## Complexity Budget

- Reuse the common retrieval client, WMesque v2 server, existing RQ scheduler,
  existing queues where suitable, rsync already present in images, and normal logs.
- Permit a bounded manifest representation, endpoint resolver, sync function,
  thin RQ entry point, disabled schedule entry, and regression fixtures.
- Test a small two-server fixture and manual sync before live scheduling.
- Require retained acceptance evidence before adding dependencies, services,
  queues, databases, protocols, or runtime privileges. Record the smallest
  escalation and recovery cost before expanding scope.
- No conflict registry, adoption workflow, persistent endpoint health service,
  or automatic upstream publication.

## Generated Artifact Validation Gate

Applicable: this feature retrieves, copies, publishes, and consumes rasters.
Capture endpoint configuration and expected revision, reload published manifests,
verify source checksums, parse the exact raster consumed by NoDb, inspect prepared
WEPP inputs, and retain fresh execution/report evidence for a representative
project. Test copy failure and publication concurrently with real retrievals.
Record job IDs, candidate revision, identities, mounts, raster semantics, and
actual serving endpoint. Health responses, timestamps, and job success alone
cannot establish acceptance. Highest current claim: static assessment only.

## Success Criteria

- [ ] Missing configuration uses wepp.cloud; explicit lists honor priority and overrides.
- [ ] Failed attempts preserve prior output; provenance identifies the actual source and revision.
- [ ] Revision mismatches are explicit; old clients remain compatible with upgraded servers.
- [ ] Sync is repeatable, overlap-safe, observable, and disabled by default.
- [ ] Local extensions survive sync; adopted identifiers transition through ordinary sync.
- [ ] Forest real-worker tests validate complete publication and downstream artifacts.
- [ ] Required regression, correctness, and security gates pass with no open medium/high findings.
- [ ] Authorized rollout and recovery evidence exists for each activated deployment.

## Security Impact and Review Gate

Security impact: **high** because the implementation touches public data serving,
remote transfer/path handling, queue execution, and receiving filesystem writes.
Dedicated [security review](artifacts/20261014_security_review.md) and independent
[correctness review](artifacts/20261014_correctness_review.md) are required before
release. Both are pending; no review verdict is implied by their creation.
Roger is the decision owner; implementation and independent reviewers are assigned
when execution begins.

## Parameterization ADR Gate

Fallback behavior and timeout policy will change: an ADR is required before merge
for those implementation choices. Its identifier is not allocated yet. Preserve
the wepp.cloud default; record operator decisions and implementation rationale.
Before any project metadata/schema mutation, write an additive compatibility and
regression plan and validate downstream artifact propagation.

## Dependencies and Rollout Boundaries

Initial fixture development has no known external blocker. Live synchronization
requires a verified master export, transfer access, storage capacity, and VRT
dependency closure. All deployments are assumed to share one tailnet for this
initial scope; use private sync connectivity and exclude public bulk-transfer or
cross-tailnet support. Prefer existing rsync over SSH, with actual task access
validated before activation. Kubernetes workers currently mount geodata read-only; writer
placement needs a deliberate decision. Its scheduler is dry-run-only with a
three-task readiness assertion; sync activation must not enable unrelated jobs.

Use forest development first, forest1 Compose parity where applicable, then the
canonical wepp.cloud deployment entry point. Open-wepp-org uses its own repository
and Kubernetes/GitOps procedures. Revalidate these static observations before
rollout. Production action requires authorization beyond this scaffold request.

## Deliverables and Closure

Planned deliverables are compatible code, contract documentation, fixtures,
strict acceptance tests, run evidence, review artifacts, rollout instructions,
and rollback evidence. No production code or deployment has been delivered.
At closure, keep durable rules outside this package, archive the active prompt
with outcomes, and update the root project tracker.
