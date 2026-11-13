# Declarative DEM v1 contract

Status: implemented; bounded cluster conformance validated 2026-11-11 UTC.
See [receiving evidence](../work-packages/20261110_declarative_dem_vertical_slice/artifacts/receiving_acceptance.md).
This bounded contract specializes [declarative model builds](declarative-model-build-spec.md).

## Scope and authority

The operator requested execution of the DEM vertical slice and a deployment-ready
handoff before deployment. Use existing science, normal projects and deployment
credentials. The initial checkpoint did not authorize deployment; Roger subsequently
authorized the recorded receiving deployment and migrations. Future deployments
still require explicit operator authorization and receiving verification. The initial
source and project are public; private projects and sources are rejected by this
protocol. Existing ordinary project visibility and authorization remain unchanged.
This restriction avoids claiming private access enforcement in the existing
unauthenticated elevation-query service. Adding private declarative builds requires
a separately reviewed access contract.

## Definition and approval

Model schema `dem-v1`, engine protocol `dem-engine-v1`. JSON objects reject unknown
keys, duplicate keys, nonfinite numbers and incorrect types. Required definition:
`schema`, `image`, `submission_id`, `extent`, `source`, `product`, `visibility`.
`submission_id` is a canonical UUID; `image` is a full approved
`ghcr.io/rogerlew/wepppy@sha256:<64 lowercase hex>` platform-manifest reference.
`source` is exactly `ned1/2024`; `product` is `dem`; `visibility` is `public`.
`extent` is four finite WGS84 longitude/latitude numbers, ordered west/south/east/north,
within CONUS (-125..-66 longitude, 24..50 latitude), with each span at most 0.02
degrees. The fixed existing configuration is `disturbed9002`, 30 m cells; these
are admission bounds for this experiment, not changed scientific defaults.
No arbitrary paths, URLs, Python names, environment variables or secret references.

Deployment-owned approval JSON maps exact image references to `schema`, `protocol`,
`platform` (`linux/amd64`) and `operation` (`fetch_dem_rq`). Exactly matching entries
are required for new admission. Revocation does not block status/cancel for an
existing build. The worker template and approval file are reviewed deployment inputs,
not model fields. An image may implement only one schema. No candidate digest is
approved until publication and operator review; an empty approval file denies all.
Invalid input or unavailable/mismatched runtime evidence causes no project or job
creation. Owner identity is an explicit existing user ID supplied by the private
operator invocation, outside the model. No new public submission route.

## Engine and image adapter

The independent stdlib operator engine lives in `tools/declarative_dem.py`; it
invokes the image-local `wepppy.declarative.adapter` through Kubernetes exec using
the operator's current kubeconfig. Commands are validate, submit, status, cancel.
The engine does not import scientific/NoDb application modules. The adapter owns
project creation and RQ dispatch. Worker provisioning is deployment-owned and
operator-invoked from a reviewed, rendered template; neither engine nor task
receives authority to modify arbitrary cluster resources.

Use one dedicated Pod/queue for one submission, with one RQ slot, no automatic
scientific retries, and no executable/code mounts. `fetch_dem_rq` does not enqueue
or wait for children. Engine observation runs outside the worker. Queue name is
`declarative-dem-<UUID hex>`; worker name equals the Pod UID. Job/attempt IDs are
persisted before enqueue. Repeated submit with identical identity/definition/owner
returns the existing project. A conflicting definition or owner is rejected.
A process crash after admission or ambiguous enqueue never permits automatic
re-enqueue; status reports incomplete/interrupted and retains the project.

Project allocation reuses canonical run-root, creation lifecycle, Ron component
initialization, TTL and owner registration. A deterministic ordinary run ID
`declarative-<UUID hex>` provides durable submission lookup without another database.
An exclusive directory reservation precedes initialization; an existing directory
without valid admission state is an incomplete reservation, never permission to
initialize over existing files. No custom storage root is accepted by production CLI.

## Runtime identity verifier

Before dispatch and again before verified completion, the operator engine reads
the exact dedicated Pod and its Node through Kubernetes. Retain namespace, Pod
name/UID, node name, container name, declared image, runtime imageID/containerID, restart count,
node architecture/OS, observation time and worker name. Require the approved
single-platform image digest, linux/amd64, Running/ready container and zero restarts.
Reject index/config digest ambiguity; only a runtime identity whose documented
manifest digest equals the selected digest can verify this slice. Actual cluster
format is a deployment acceptance gate, not presumed equivalent.

Compare initial/final Pod UID, containerID, imageID and restart count. The task
records downward-API Pod UID/name/namespace, container name, RQ worker/job/attempt
and queue. All must match engine observation. A replacement or missing evidence
blocks completion. Engine-supplied evidence is trusted only on the private operator
path and still cross-checked against actual task observations; job fields or queue
names alone cannot prove runtime identity. No worker Kubernetes API credential.
Reject template changes introducing image overlays, init/sidecar code injection,
command overrides, PYTHONPATH or unreviewed environment/mount changes.
Compare reviewed resource limits/requests and node placement too; the actual Node
must satisfy the reviewed selector. This prevents accepting an oversize or
misplaced worker under the same image identity.

## Visible records and publication

Use `provenance/` in the normal project browser/archive. `declarative.json` is the
immutable admission marker: version, build/submission ID, run ID, owner ID, exact
definition, queue and attempt/job IDs. `build.json` stores processing and protection
outcomes separately, selected attempts, verified runtime evidence and checkpoint
IDs. Create its path with an incomplete outcome before finalization so manifest
browsing includes it. `attempts/<UUID>.json` records each actual task boundary;
`claims/<UUID>.json` is the durable exclusive execution claim, retained on failure.
`provenance/.git/` is a local audit repository, never Bootstrap or a remote transport.
Serialize atomic same-directory JSON replacement and Git publication using a
project-local file lock inside the existing stable `catalog_lifecycle_guard`.
Admission, claims, observation publication and finalization all take that lifecycle
guard first and revalidate the admission identity/incarnation before publication.
Archive/restore reject active or uncertain execution; no old lock descriptor may
confer publication authority after replacement. Reject symlinked record
directories/files and path escapes.

Git stages only explicit definition/attempt record paths, never `git add .`, rasters,
logs, arbitrary NoDb configuration, credentials or runtime environment dumps.
Attempt records contain schema, operation, run/build/node/job/attempt IDs, execution
or observation disposition, UTC times, effective source/map/cell size at the actual
acquisition boundary, runtime observation, output SHA-256 and semantic raster
readback. Include CRS, transform/bounds, shape, nodata, valid-cell count and finite
sample/min/max values; missing/invalid output prevents declarative success.
Source content is an acquisition observation, not reproducibility certification.
Do not serialize raw exceptions, signed URLs, secrets or hashes of secrets.

A record cannot include its own enclosing commit hash. Associate commits via exact
attempt identity in the commit message and build record; discover an already
published commit after interruption, but never fabricate a missing historic commit
from later files. Preserve failed/partial records and output bytes. Missing required
checkpoint prevents completion without rerunning science. Measure publication,
hashing time and Git bytes separately from baseline acquisition.

Ordinary `fetch_dem_rq` keeps signature, defaults, science and failure semantics.
Shared observation publication failures log a diagnostic and do not fail otherwise
successful ordinary science; mandatory batch/handoff contracts remain unchanged.
The shared helper cannot depend on engine/Kubernetes availability. Unavailable
ordinary image identity is explicitly unknown; do not infer a registry digest.

## Protection and lifecycle

The admission marker establishes engine ownership from creation onward. Absent
marker, empty provenance directory and legacy projects retain ordinary behavior.
Empty/malformed/symlinked admission marker is exceptional and fails closed for
mutations; it is never interpreted as an ordinary project. Valid populated markers
permit only their bound adapter attempt while building. Exclusive persistent
attempt claims prevent duplicate delivery; a claimed but unfinished attempt remains
uncertain and is never automatically replayed.

Ordinary project-changing HTTP requests and queued tasks reject declarative projects
at admission and execution, including jobs queued before finalization. Only the
bound adapter task can acquire build mutation authority; flags supplied by public
requests cannot confer it. Queue rejection must use normal RQ failure bookkeeping.
NoDb read-only clearing is prohibited, including direct calls. Bootstrap enable,
push authorization, checkout, no-prep and initialization reject before any Git or
model writes. The frontend shows declarative origin/outcome and disables editing,
unlocking and Bootstrap; backend guards remain authoritative.

Allowed post-build operations are normal read-only browsing/downloads, map elevation
query, and existing archive/restore under their authorization and lifecycle fences.
Archive/restore must preserve the marker, records, protected bytes and READONLY;
restoring a mutable archive over a declarative project is rejected. Before any
deletion, validate incoming admission/build/run/submission/owner identity, exact
retained provenance records and protected payload hashes against the current
build's `provenance/protected.json` manifest (root NoDb configuration and DEM files).
Preserve the authoritative `provenance/` tree and `READONLY` during both destructive
cleanup and extraction; never unlink, overwrite or truncate that fence. Interrupted
restore therefore remains declarative/protected even when science files are missing.
Incoming malformed/mutable/different-build archives fail before deletion. Restore
to a different project is outside v1. Archive/restore acquire the same stable
catalog lifecycle fence, and wait for no writers; uncertain execution is rejected. Archive writing
and execution logs are operational writes, not scientific mutation authority.
No generic report/catalog write exemption is introduced. All other scientific RQ
tasks remain prohibited for this first slice, including direct task invocation.

Processing outcomes: admitted, running, succeeded, failed, canceled, interrupted.
Protection outcomes: pending, readonly, failed. Public build success additionally
requires required attempt/checkpoint evidence, verified runtime identity and
successful shared read-only finalization. The engine publishes verified completion
last. It waits until the bound science writer has stopped, uses existing catalog
flush/manifest finalization, then updates the already-visible build record. A failed
or canceled project is protected after writers stop without relabeling its outcome.
If finalization fails, keep admission protection and truthful failed protection state.
Cancellation never means rollback; record request, stop only the bound owned job,
and do not claim stopped/protected until confirmed. Worker loss stays interrupted.
Explicit recovery uses a new submission/project after old writers are proven stopped.

## Finalization authority and command results

`validate` is side-effect free. `submit` admits/dispatches once, observes the bound
science attempt, then enqueues exactly one separate image-local finalization job
with a persisted distinct attempt ID on the same dedicated queue. Repeated submit
may observe existing science and advance this bounded finalization flow; it never
requeues claimed/uncertain science. `status` only reads. `cancel` records intent,
cancels/stops only owned job IDs, and observes settlement before finalization.

The fixed adapter finalizer is an explicitly allowed operational task, not general
science authority. It checks science is terminal and has no live RQ executions;
stopped/killed work additionally requires surviving-supervisor child-cleanup proof.
Missing writer-settlement proof leaves protection pending/interrupted. It invokes
shared `set_run_readonly_rq` within its real RQ job, under the lifecycle guard,
retains the original processing outcome, and records finalization/checkpoint result.
The engine verifies the actual finalizer binding and before/after container evidence
before a private adapter completion call publishes verified success. Completion
revalidates admission/attempt IDs, required checkpoints, protected hashes, READONLY
and finalizer result under the lifecycle fence. Duplicate completion is observational.
A missing checkpoint or uncertain finalizer never causes automatic reconstruction
or science replay. Failure protection may complete without verified build success.

Command results are JSON objects with `protocol`, `command`, `submission_id`,
`runid` (null before admission), `processing`, `protection`, `verified` (boolean),
`job_ids` and `error` (null or object with fixed `code` and sanitized `message`).
`validate` returns `valid` and no project side effects. Invalid definition, image
or evidence exits nonzero; incomplete/interrupted state is explicit, never a zero-
evidence verified result. No raw exception text or credentials enter result records.

## Selected consumer and fixture

Baseline/acceptance extent: `[-116.10,46.70,-116.09,46.71]`, public `ned1/2024`,
`disturbed9002`, 30 m, ordinary `dem/dem.tif`. Verify NoDb reloaded map and source,
and the actual raster semantics. The existing map hover consumer is
`wepppy.microservices.elevationquery:elevationquery_endpoint` -> `_sample_dem`,
POST `/runs/<runid>/<config>/elevationquery/` at the extent center. Its fresh JSON
response (elevation, units, longitude, latitude) is the derived viewing result.
This is a real HTTP viewing task, not an RQ job or a persisted report. It has zero
project writes and no catalog refresh, so no read-only catalog exception is needed.
Retain its response and matching DEM hash in acceptance evidence outside protected
build records. Fingerprint protected files before/after; failure belongs to the
later request and never changes historical build outcome.

## Validation and deployment limits

Exercise real filesystem/Git/raster boundaries, malformed metadata, duplicate
submission/delivery, missing/mismatched image observations, checkpoint loss,
cancellation, worker interruption, finalization failures, Bootstrap and queued
mutation rejection, ordinary parity, normal browse/download and byte-preserving
canonical archive/restore. Local mocks do not establish Kubernetes conformance.
Before rollout, render the scoped worker configuration and review image, identity,
mounts, umask, existing queue capacity, target context and rollback. Do not displace
an existing worker. Deployment readiness is separate from live acceptance and package
closure; the package remains open until the cluster workflow is evidenced.
