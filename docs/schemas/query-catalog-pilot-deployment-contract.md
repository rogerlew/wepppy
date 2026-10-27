# Query-catalog pilot: scoped batch deployment

Status: operator-authorized pilot intent, implementation/acceptance pending
(2026-10-27 UTC). Applies with the bounded-pilot section of
[query catalog refresh](query-engine-catalog-refresh-contract.md) and the existing
canonical `scripts/deploy-production.sh` entry point. No general enablement or
unrelated source deployment is authorized.

## Opt-in targeted batch mode

Add `--targeted-batch`, mutually exclusive with existing targeted modes. Existing
full/web/CAP behavior and defaults remain unchanged. Accept only existing full
or worker-pool presets with active `rq-worker-batch`; unsupported presets or
missing services fail before mutation. Render the actual installed Compose
configuration and derive the batch service's build/runtime acceptance set from
it. Recreate and accept only `rq-worker-batch`, preserving existing replicas,
identity, groups, mounts, environment and command.

Use existing owned RQ admission fencing and default/batch drain checks. Never
flush RQ data or reuse/remove a foreign fence. Warm-stop only batch workers,
then use the canonical service-scoped no-dependencies recreate path; never
`compose down`. Release only the owned fence with the existing failure semantics.
Do not restart Redis, default workers, web/query services, CAP, scheduler or other
services. Skip unrelated static/theme/CAP work, whole-stack health checks and
pruning. New mode rejects incompatible destructive flags.

For this pilot, existing containers do not mount the repository source. Build
the candidate batch image through the canonical targeted mode from the retained
production baseline plus only the reviewed task patch; `--skip-build` cannot
activate new source. Use `--skip-themes --skip-pull --no-flush-rq-db`. Pin and
verify existing native/scientific and dependency inputs; do not import unrelated
local repository, sibling-library, Dockerfile, requirements or Compose changes.
No secret, permission, mount, identity, dependency-policy or service change is
required. Record the built image ID and source/native/dependency fingerprints,
and reject unexplained drift before worker cutover. Source installation is a reviewed candidate-only
patch against each host's retained production baseline, with exact source
hashes, prior-content/absence backups and a bounded rollback manifest. Never
pull the local development HEAD containing unrelated Roads/secret changes.
Use the canonical entry point for lifecycle operations, not an alternate
copy/restart deployment script or an execution bootstrap in RQ jobs.

## Preflight and acceptance

Before source mutation, verify host identity, clean applicable source baseline,
existing service/image identities, candidate patch applicability, manifest
completeness and effective Compose plan. Follow the existing operator rule for
active default/batch jobs; do not force-stop scientific work. Validate candidate
source and native/runtime imports inside the exact built image under equivalent
identity/mount/configuration before replacing worker participants. Preserve the
old image ID with an owned local rollback reference before changing its tag;
existing unrelated containers must retain their original running image IDs.
Deploy wepp1 first, then repeat preflight and deploy wepp2.

Read back genuine new batch registrations, current process birth/heartbeat,
source/capability/configuration and all existing eight compatible consumers
before pilot admission. Lost/mixed workers block admission; registration fields
cannot be fabricated. Verify untouched services/image IDs, unchanged general
async-disabled mode, actual owned-scope execution and sanitized job trees.
Service/process health alone is not pilot acceptance.

On failure, pause only pilot/catalog admission, preserve job/receipt evidence,
drain admitted work, restore only manifest-listed source files/absences and the retained original
image reference, then use the same targeted canonical worker cutover. Verify
original source/native/image readback after rollback. Never delete coordination inodes,
reset consumed pilot budgets, expand rollout scope or restart unrelated services
to make acceptance pass. General enablement remains disabled throughout.

## Rationale

Existing full mode would recreate 24 services on wepp1; targeted-web explicitly
excludes workers and no batch-only mode exists. The opt-in target is the smallest
canonical mechanism for authentic worker capability without full-stack disruption,
a new queue/pool, registration spoofing or arbitrary job-time code loading.

## Source-only image derivation

Baseline Dockerfiles use mutable vendor branches/base tags and uncached installs;
unchanged Dockerfile text cannot prove native/dependency parity. For this pilot,
the canonical targeted mode therefore supports a manifest-bound source-only
image derivation from each host's exact retained running batch image. The base
must already exist locally and its immutable ID must match the inspected
container; no registry publication/pull, package installer, vendor checkout or
native rebuild is involved. This is an opt-in path within the canonical entry
point, not a second deployment workflow.

Stage only the checkpoint-listed Python source files, with strict relative
repository destinations, no symlinks/traversal and verified content hashes.
Reject unexpected files, a changed base image or a mismatched manifest before
build/cutover. Generate the build recipe from trusted tooling, never accept an
operator-supplied arbitrary Dockerfile/command. Preserve the base image's runtime
configuration and dependencies. Remove only stale bytecode for replaced source
modules; retain the immutable overlay manifest in the image. Use no-network
build steps and keep exact base/candidate IDs and fingerprints in evidence.
The pilot image's native modules, Python distributions, runtime identity and
entrypoint/command contracts must match its base. Only the approved source and
its derived bytecode/provenance may differ. Unrelated running image IDs remain
unchanged, and rollback restores each host's exact retained original image.
