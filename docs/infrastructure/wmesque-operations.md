# WMesque Priority Retrieval and Synchronization Operations

Implementation contract: [catalog/retrieval](../schemas/wmesque-catalog-contract.md).
Ownership: [catalog governance](wmesque-catalog-governance.md).

## Retrieval Configuration

Without configuration, v2 uses `https://wepp.cloud/webservices/wmesque2/`.
An explicit run/client endpoint overrides the deployment list. Set an ordered
JSON array in the deployment environment to opt into local-first retrieval:

```text
WMESQUE_ENDPOINTS=["http://wmesque2:8030","https://wepp.cloud/webservices/wmesque2"]
```

Use the appropriate internal service name on Kubernetes. A blank value preserves
the default; an empty array or malformed URL is an error. Do not put credentials
in URLs. V1 remains deprecated and retains its old behavior.

Availability errors move to the next configured endpoint; invalid requests,
authorization failures, and local filesystem failures surface immediately. The
300-second network budget is divided over remaining candidates. Read deadlines
cover headers and body; OS name resolution and connection/TLS establishment are
not a universal wall-clock guarantee. No repeated attempts or background health
registry are maintained.

Successful raster `.meta` files record the actual serving endpoint, attempt
history, and managed revision when available. Legacy servers may omit revision;
unpinned callers can use them. Requests with `expected_revision` cannot substitute
an unidentified or different revision. EDDE normal provenance additionally records
per-variable `serving_endpoints` and `dataset_revisions`, preserving the existing
configured `endpoint` field. An unpinned replica may lag; a dataset name alone
cannot establish reproducible rebuilds.

## Publish a Managed Dataset

Run the publication CLI in the existing WEPPpy runtime with access to the geodata
root. For example, on forest after preparing an isolated dataset:

```sh
wctl exec -T weppcloud python -m wepppy.webservices.wmesque_catalog publish /geodata example/dataset
```

Publication copies the local VRT dependency closure into an immutable release,
verifies it, and updates `.wmesque/catalog.json`. Original dataset directories
remain intact. Local sources must be contained under the configured root.
Virtual/network sources, including current NED `/vsicurl/` mosaics, must first be
materialized into a stable local snapshot; publication refuses to assign a data
revision to mutable remote URLs. Validate all required source formats/sidecars
on a representative resource before publishing a new dataset family.

`/catalog` retains logical path entries. `/catalog/manifest` exposes the managed
logical ID/revision mapping. `/health` only proves application responsiveness;
read and parse a representative raster before calling a release usable.

## Manual and Scheduled Pulls

All initial deployments are assumed to share one tailnet. Provision read access
to the master's export, SSH credentials and known-host trust, and destination
write access for the actual task identity. SSH is noninteractive and requires
host verification. Never bypass host checks to make a sync succeed.
Restricted `rrsync -ro /geodata` credentials require ordinary inspectable rsync
arguments. The helper validates shell-safe paths and explicitly disables secluded
arguments, which rrsync rejects. For a restricted export rooted at `/geodata`,
use source `sync@tailnet-host:/.`; its paths are relative to that export root.
Retain the read-only forced command and source-host restriction on the credential.
Both runtime Dockerfiles install `openssh-client` alongside the existing rsync
transport. Older images may lack it: check `command -v ssh` in the actual task
container and rebuild through the normal deployment workflow before activation.
This adds no SSH server or credential mount.
The task UID must also resolve to a normal passwd entry/home for SSH. Current
forest development containers use numeric UID 1000 without that entry; their
local fixture sync is validated, but SSH activation needs an explicitly configured
task identity/home. Production Dockerfiles already create their application user.
Do not add a runtime identity workaround or weaken trust checks to bypass this gate.

```sh
wctl exec -T weppcloud python -m wepppy.webservices.wmesque_catalog sync sync@wepp1:/geodata /geodata --dry-run
wctl exec -T weppcloud python -m wepppy.webservices.wmesque_catalog sync sync@wepp1:/geodata /geodata
```

These are example source identifiers, not provisioned accounts. An absolute local
source root is supported for fixture acceptance. Dry run reports revision changes
without publishing; it does not prove that all source files are transferable.

After manual validation, configure the existing receiving scheduler:

```text
WMESQUE_SYNC_ENABLED=true
WMESQUE_SYNC_SOURCE=sync@wepp1:/geodata
WMESQUE_SYNC_DESTINATION=/geodata
WMESQUE_SYNC_INTERVAL_SECONDS=86400
```

Default is disabled. The task uses `batch` with a one-hour job timeout; individual
SSH/rsync transfers have bounded timeouts. Measure large resource copy times before
activation. Scheduler admission snapshots source/destination into job arguments,
coalesces queued/running jobs, and the sync helper also holds a destination lock.
Existing periodic tasks are unaffected by leaving this task disabled.

The sync copies managed master releases, verifies them, and only then publishes
catalog updates. Local-only resources survive. When master adopts a local ID,
normal sync takes ownership without renaming or manual conflict resolution.
Resources missing from a later master catalog are not deleted automatically.

## Inspect and Recover

Inspect `.wmesque/sync-status.json`, RQ job state, and worker logs together.
The status file includes the last successful sync and current attempt outcome.
An abruptly killed process may leave `running` status and staged files; RQ state
and the next attempt distinguish interruption from completion. OS locks release
on process death, and retry does not advance the catalog until verification passes.
Failed staging directories may be retained as evidence; no automatic release
retention or garbage-collection policy is implemented.

Disable scheduling before rollback and account for active work. Restore
wepp.cloud-only routing to bypass replicas; local-only extensions then need an
explicit local endpoint to remain available. Keep verified releases and legacy
paths. No automatic reverse sync or deletion is part of recovery.

## Deployment Gates

Forest uses its existing Compose runtime. Restart affected services for code changes and recreate them through the normal
deployment workflow to apply environment changes; isolate failure injection from shared services. Master
production changes use the canonical deployment script and installed wctl preset.
Kubernetes changes use open-wepp-org's procedures. Its current compute workers
mount geodata read-only and its scheduler is dry-run-only with a fixed-task
readiness assertion: establish the authorized writer and sync-only activation
before rollout. Do not enable unrelated GC/database jobs as a side effect.

## Master Publication Rollout (2026-10-15)

The first managed master resource is `tenerife/136_MDT25_TF`, revision
`aa96d31fe8aff11778b84be268798c04295e0d3de758649ec6e666d854fee295`.
Other datasets retain legacy retrieval until separately published. Do not infer
that the complete geodata inventory is managed from this initial publication.

The verified private source is `roger@wepp1:/geodata`, reached over the shared
tailnet using existing operator SSH access with strict host-key checking.
This is a verified operator transfer path, not a provisioned receiver service
credential. Configure and validate the actual receiving task's credentials,
normal passwd/home, known-host trust, and destination write access during its
canary. Do not copy operator credentials into containers or enable master pulls.

Original source directories remain unchanged. The previous production image
successfully retrieved the published resource through its original path with
read-only geodata access, validating layout compatibility for code rollback.
Use the canonical deployment recovery procedure and retained image references;
keep release directories and source data intact. See the
[master rollout evidence](../work-packages/20261014_wmesque_catalog_sync/artifacts/20261015_master_rollout.md)
for commands, revision, actual transfer and raster readback, and deployment status.
