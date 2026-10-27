# RQ 2.12 migration and recovery

The runtime target is exactly `rq==2.12.0`, with required dependency
`croniter==6.0.0`. This is a behavior-preserving migration. Existing queue names,
worker identities, mounts, permissions, API responses, strict prerequisites,
approved terminal observers, retry behavior and generated model outputs remain
the contract. Native RQ webhooks remain disabled and unexposed; do not pass
webhook configuration to enqueue APIs or add delivery infrastructure.

The normative boundary is
[RQ runtime migration](../schemas/rq-response-contract.md#rq-212-runtime-migration-implementation-pending).
The [execution package](../work-packages/20261027_rq_2_12_upgrade/package.md)
retains versioned distribution provenance, compatibility findings, baseline
fixtures and acceptance evidence. The bounded historical replay and isolated
original-state rollback pass; rebuilt-runtime and full lifecycle acceptance
remain pending. This document does not authorize production rollout.

## Developer compatibility rules

Use released 2.12.0 source rather than upstream master when changing overrides.
The existing `handle_job_success` and `handle_job_failure` signatures still match
2.12.0; an additional execution argument from unreleased master is not required.

RQ statuses are string-valued enums. Compare with their values or normalize
`.value`; `str(status)` can produce `JobStatus.STARTED` instead of `started`.
RQ timestamps are timezone-aware. Interpret legacy naive RQ timestamps as UTC
for arithmetic, while retaining existing public timestamp serialization.
`rq.utils.utcnow` is removed; use explicit UTC datetime operations.

Started-registry members can contain `job_id:execution_id`. Use
`StartedJobRegistry.get_job_ids(cleanup=False)` for read-only discovery; do not
treat raw sorted-set members as application IDs. Preserve exact job IDs in
metadata, receipts, lookup URLs and responses. Continue using `new_rq_job_id()`
for preallocated UUIDs and the approved maintenance prefixes.

Actor, correlation and profile metadata must enter the enqueue transaction
before queue publication, so a worker cannot consume a job before its context
is stored. Preserve explicit actor and valid correlation metadata; an active
profile slug overrides a stale supplied profile slug. Caller-supplied pipelines
must not leave a metadata-only job after an aborted WATCH transaction. Test the
pre-publication boundary directly, including enqueue failure and ambiguous
acknowledgment recovery, rather than checking metadata only after enqueue returns.
The [metadata regression evidence](../work-packages/20261027_rq_2_12_upgrade/artifacts/metadata_evidence.md)
retains the original publication-boundary failures and repaired 1.16.2/2.12.0
results; final rebuilt-runtime validation remains separate.

A retry attempt failure must not be mistaken for terminal failure. Process
termination and directory-lock ownership rules still apply independently of RQ
status: never release a lock while its writers may remain alive. A discovered
running-stop/finalizer lifecycle incompatibility is under repair; this guide
does not claim that gate passes. Targeted regression entry points include
`tests/rq/test_rq212_historical.py`, `tests/rq/test_rq212_lifecycle.py` and
`tests/rq/test_rq212_metadata.py`; use their documented disposable Redis
requirements through `wctl`, alongside existing recovery and cancellation tests.

WBT atomic admission primes each job's `redis_server_version` from
`Queue.get_redis_server_version()` before MULTI; the corresponding Job method
was removed. Stopped prerequisites may release only the already-approved
failure-tolerant terminal observers. Strict prerequisites and canceled jobs
must remain blocking; preserving a baseline defect that released strict work
after stop would violate the existing contract.

Pool testing also reproduced an inherited scheduler socket defect under both
1.16.2 and 2.12.0. The bounded repair disconnects only idle Redis-pool connections
before a scheduler fork so it cannot inherit the supervisor's later blocking
dequeue socket. Validation is pending. Queue topology, pool counts, scheduler
policy and production defaults are unchanged.

## Historical jobs and migration gate

The migration must preserve existing Redis state. A successful import or package
install does not establish persisted-job compatibility. The six-state baseline
uses genuine RQ 1.16.2 jobs captured from disposable Redis, including an actual
running workhorse. A second fixture records the original runtime's drained
state, preserving queued and deferred work. The
[historical replay evidence](../work-packages/20261027_rq_2_12_upgrade/artifacts/historical_compatibility.md)
records two passing tests each under original 1.16.2, candidate 2.12.0 and an
original-state restoration under 1.16.2 after candidate execution. Candidate
replay used an isolated import path with actual Redis, scheduler and forked
workers; the final rebuilt forest interpreter replay remains pending.

| State written by 1.16.2 | Required handling | Candidate evidence |
| --- | --- | --- |
| Queued | Preserve exact ID, payload and metadata; execute once with the intended queue | Drained fixture executed once, result 4.0 |
| Deferred | Preserve dependencies; successful prerequisites release strict work, failed ones do not | Strict successor released after success, result 5.0; failure cases require lifecycle coverage |
| Scheduled | Preserve due time and retry state; scheduler releases it once | Stayed scheduled until due score advanced; actual scheduler/worker returned 6.0; retry cases separate |
| Running | Drain on 1.16.2 before cutover; do not transfer a live execution between versions | Original state deserializes for diagnosis; running handover and old-state abandonment recovery not certified |
| Completed | Preserve readable status, timestamps and retained result for existing consumers | Retained result 9.0 remained readable after new execution |
| Failed | Preserve readable failure and diagnostics; exercise supported recovery explicitly | Expected failed status/math-domain traceback retained; no silent retry |

Do not promise arbitrary historical custom IDs, mixed-version worker execution,
or reverse compatibility with 2.x-written state. Inventory invalid or untested
records before cutover and preserve them. Resolve them under the original
runtime or validate a bounded migration using an isolated copy; deleting a job,
dependency or registry entry to make the upgrade pass is not migration.

## Dependency reproducibility

Compare installed candidate distributions with the actual running baseline,
not only freshly resolved old and new requirement inputs. The first canonical
build exposed unrelated allowed-version drift. The authoritative input now
retains these existing forest versions: `fastapi==0.143.1`,
`narwhals==2.27.1`, `pkginfo==1.13` and `python-dateutil==2.9.0.post0`.
These pins prevent unrelated upgrades; only RQ and required croniter should
differ in the main installed-distribution comparison. See
[dependency drift evidence](../work-packages/20261027_rq_2_12_upgrade/artifacts/dependency_runtime_drift.md).
The final rebuilt-image comparison remains a release gate.

The dashboard uses Python 3.12 because RQ 2.12 requires Python 3.10 or later.
Its separate dependency image retains existing Gunicorn 23.0.0, Redis 5.2.0 and
other sibling pins, and pins croniter 6.0.0 with pytz 2022.1. This does not change
the dashboard's runtime identity, mounts or authentication.

## Dashboard source patch

The dashboard source is a sibling checkout bind-mounted at `/rq-dashboard`.
Rebuilding its dependency image does not install source repairs. Before its
2.12 cutover, inspect `/workdir/rq-dashboard` and retain its existing changes.
The reviewed starting revision is
`860ce63b45c4f70db53f21f6fc04a052c6fed90f`; the retained patch fixes dependency-ID
decoding and orphan started-execution cleanup, with two regression tests.

For that inspected baseline, check and apply the owned patch:

```bash
git -C /workdir/rq-dashboard apply --check /workdir/wepppy/docker/patches/rq-dashboard-rq212.patch
git -C /workdir/rq-dashboard apply /workdir/wepppy/docker/patches/rq-dashboard-rq212.patch
```

For an already patched checkout, verify without applying it twice:

```bash
git -C /workdir/rq-dashboard apply --reverse --check /workdir/wepppy/docker/patches/rq-dashboard-rq212.patch
```

A failed check requires inspecting source divergence; do not reset the sibling
or overwrite unrelated edits. Equivalent reviewed changes carried in that
repository may replace patch application. The
[dashboard evidence](../work-packages/20261027_rq_2_12_upgrade/artifacts/dashboard_compatibility.md)
retains exact source/patch hashes and actual HTTP success under candidate 2.12
and an old 2.0 comparison. Final installed-dashboard HTTP readback remains
required; this does not certify every dashboard mutation.

## Local forest cutover

These steps apply only to explicitly authorized local forest development work.
Confirm `hostname` is `forest`, the Docker context endpoint is local, the
installed `wctl` preset selects `docker/docker-compose.dev.yml`, and Compose
labels identify the expected project before operating. Review effective service
configuration without printing environment secrets.

Record the starting source revision, exact image IDs, active jobs, worker
registrations and queue/registry counts. Retain the original images with owned
local rollback tags before overwriting their normal tags. The initial shared
image is retained as `wepppy-rq212-rollback:20261027`; its immutable ID is recorded
in the package's baseline environment evidence. A tag alone is not identity proof.

Build through the installed development preset:

```bash
wctl docker compose build weppcloud
wctl docker compose build rq-dashboard
```

The first build supplies the shared Python image. The dashboard has a separate
image and dependency input; it must be checked independently. Restarting an old
container does not install the new dependency.

Before recreation, identify every relevant producer, worker, scheduler and
observer from the effective Compose configuration. Preserve the current
identity, groups, mounts, umask, queue and worker class. Development source is
bind-mounted: source edits can affect old processes before image cutover, so
stage compatible repairs or stop the affected processes before exposing an
incompatible edit.

Prevent new execution during the transition and inspect active work again.
Use the existing deployment fence's ownership and resume semantics where that
entry point is used; never overwrite another operator's suspension. Warm-drain
all affected worker pools, including fork/archive. Do not force-stop unrelated
jobs. An unrelated long-running job is a blocker to that pool's cutover, not
authority to kill it. Preserve queued, deferred and scheduled jobs.

Recreate only the reviewed affected service list through
`wctl docker compose up -d --no-deps --force-recreate`, after the drain gate.
Record the exact list and commands in acceptance evidence. Do not use
`compose down`, flush Redis, delete volumes, prune retained rollback images or
erase queues. Verify every relevant running container imports RQ 2.12.0 and
runs the intended image; host virtualenv evidence is insufficient.

Require fresh worker registrations with the existing pool counts and queues,
stable container identities/restart counts, successful API/auth submissions,
strict job trees and generated-input/output semantic readback. Retrieve a fresh
user-facing report or output. Repeat cancellation, recovery and resubmission.
Health endpoints and green job statuses alone cannot release the migration.

## Recovery and rollback constraints

Before any 2.x execution, retain the original image, compatible source and a
consistent quiescent-state recovery point. Original-state fixture restoration
and re-execution passed under 1.16.2 after the candidate replay. That bounded
proof covers synthetic records, not live whole-stack rollback or every historical
function/import/ID. Preserve the entire relevant state and inspect resumed
behavior and result retention; project artifacts need an aligned recovery point.

After 2.x writes state, do not attach a 1.x worker to that state merely because
the old image starts. Restore an isolated original snapshot for rollback proof;
never restore it over live Redis, which would discard accepted jobs and newer
results. Stop further package-owned work, retain execution records and artifact
diagnostics, and prefer a bounded forward repair when reverse compatibility is
unproven. A rollback requiring loss of unrelated work is not authorized.

On recovery, restore compatible source as well as image identity, using the
same reviewed service-scoped lifecycle mechanism. Validate version, worker
registration, pending work and actual artifact-producing behavior before
resuming admission. Remove only disposable resources owned by this package;
retained original projects and unrelated jobs remain untouched.

## Production planning

Production was not upgraded by the forest package. A later rollout needs
separate authorization and fleet-wide evidence: web/API producers, scheduler,
default/batch workers and the dedicated fork/archive consumer share RQ state.
A staggered restart that leaves mixed workers is not proven safe. Include the
separate dashboard observer and retained maintenance-job disclosure behavior.

For `wepp.cloud`, inspect the installed preset and canonical
`scripts/deploy-production.sh --print-plan` before proposing a rollout. Use that
entry point's build, owned global fence, drain, exact-image, worker-registration
and health gates; preserve Redis and rollback images. A targeted web-only or
source-only batch update cannot perform this dependency upgrade. Do not reuse
the OpenWEPP Kubernetes/registry workflow for Compose deployments. Forest
acceptance is evidence for planning, not authorization to operate forest1,
wepp1, wepp2, wepp3 or openwepp.org.
