# Implement WMesque priority retrieval and master synchronization


This is a living ExecPlan maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective
current together with the package tracker. Status: M1–M6 complete; production deployed on wepp1, wepp2, and wepp3. M7–M8 remain pending.

## Purpose / Big Picture


A deployment should explicitly choose local WMesque raster service first and
wepp.cloud second, while deployments with no configuration keep using wepp.cloud.
Non-master deployments should periodically copy master resources through existing
RQ jobs and retain their own additional datasets. When wepp.cloud adopts a local
identifier, the normal next sync updates it from master without a migration job.
Success is demonstrated by real raster retrieval, outage failover, and verified
sync/adoption followed by downstream project input and output readback.

## Progress

- [x] (2026-10-15 UTC) M7 restricted master key/branches explicitly authorized and installed; source-overlay dry-run/transfer/hash/full-raster/convergence and negative shell/upload checks passed. Independent source/security/QA reviews found no blocking defect. GitHub authentication blocks corrected-image publication; final M7 acceptance remains pending.


- [x] (2026-10-14 20:16 UTC) Governance, static assessment, and work-package scaffold prepared.
- [x] (2026-10-14 UTC) M1: Concrete contract/ADR accepted and independently reviewed; checkpoint `193df8b8c`.
- [x] (2026-10-14 UTC) M2: Compatible server manifest, immutable publication, and revision support; real GDAL fixtures pass.
- [x] (2026-10-14 UTC) M3: Ordered client configuration, deadline transport, validated publication, and additive EDDE provenance; focused regressions pass.
- [x] (2026-10-14 UTC) M4: Manual sync and disabled/coalesced scheduled RQ integration; actual batch jobs validate adoption and failure recovery.
- [x] (2026-10-14 21:24 UTC) M5: Forest scheduled integration, NFS interruption/concurrent reads, rebuilt model inputs/output, and fresh Compose image validated; broad suite 10,846 passed/126 skipped.
- [x] (2026-10-15 03:31 UTC) M6 master: wepp1 deployed; verified Tenerife publication, unchanged pixels/source files, private tailnet transfer, and old-image rollback-layout acceptance passed.
- [x] (2026-10-15 03:41 UTC) M6 wepp2: canonical deployment, worker registration, queue resume, and actual batch-runtime retrieval checks passed.
- [x] (2026-10-15 04:04 UTC) M6 complete: wepp3 deployed and actual runtime checks passed; all three hosts validated, private export proven, rollback-layout evidence retained.
- [ ] M7: Complete authorized receiving-deployment canary (iMac baseline and hpc fixture/write acceptance passed; restricted SSH compatibility correction in progress).
- [ ] M8: Enable recurrence/local-first routing and retain recovery evidence.

## Surprises & Discoveries

M7 iMac inspection confirmed geodata is read-only at Kubernetes and NFS export
layers, and compute cannot connect to master TCP22. Roger selected a bounded
container on existing hpc, preserving all compute mounts. Its exact candidate
image passed local adoption/extension/convergence/corrupt-transfer fixtures and
a real destination write/fsync/read/cleanup probe as UID:GID 1000:993, umask 0022.
Master remains the two-file 37,493,165-byte Tenerife release. The proposed
read-only rrsync credential exposed a real incompatibility: the helper forces
`--protect-args`, while installed rrsync rejects `-s`. The source correction
validates shell-safe relative paths and explicitly disables secluded arguments;
server path inspection, strict trust and read-only restrictions are preserved.
The actual SSH credential and rebuilt-image acceptance remain pending.

Production Git LFS 2.3.4 stalled on a release-notes PDF. Seeding the verified object from forest resolved it without skipping LFS validation. The canonical failed-pull rollback left 410 candidate-created untracked files; each matched its candidate Git blob and was preserved outside the checkout before retry. The operator skill’s `rq-info --detailed` flag is unsupported by installed RQ; direct read-only registry inspection supplied its gate.


The existing `wepppy/tools/scheduler.py` already supports interval-based RQ
enqueueing; a new scheduler is unnecessary. Kubernetes manifests in
`/workdir/open-wepp-org/clusters/openwepp/apps/weppcloud/` mount geodata read-only
on compute workers. Their scheduler is dry-run-only and its readiness check
asserts exactly three tasks. These are static observations, not live verification.
The existing WMesque network test skips retrieval exceptions, so it cannot be
the strict rollout acceptance test.

Forest and forest1 existing worker images contain rsync but not ssh. The smallest
repair adds the standard OS client package to both Dockerfiles, with no new
service or credential mount. Forest1's existing worker identity and umask match
forest (1000:993, 0022); its deployment was inspected read-only. Forest fixtures
exercise existing NFSv4.2 `/wc1` storage. At forest acceptance, actual master export access and Kubernetes write permissions remained rollout checks. M6 now verifies operator export access; receiving task credentials and Kubernetes write permissions remain M7.

Live NED VRTs reference mutable `/vsicurl/` sources. Managed publication correctly
rejects them until materialized; legacy retrieval remains available. The isolated
project referenced a retired model executable, so only that clone selected the
currently installed `wepp_261010`. Native output lacks optional interception
storage; readback checks the required water-balance fields explicitly.

## Decision Log

Latest 2026-10-15 authority update: Roger explicitly approved both the restricted
master public key and M7 branches. Branches `codex/wmesque-m7-rsync` and
`codex/wmesque-m7-receiver` now exist. Dedicated credential is restricted to
hpc 100.104.131.11 and `/usr/bin/rrsync -ro /geodata`; operator private keys were
not copied. Preserve strict trust and read-only compute/NFS export boundaries.

On 2026-10-15 UTC Roger authorized the bounded hpc writer and M7 deployment.
Master credential changes and new PR branch creation remain separately gated.
Use the existing storage host rather than expanding NFS/compute write authority
or Kubernetes tailnet access. Prepare the rrsync compatibility correction in
`/Users/roger/src/wepppy-wmesque-m7` at detached candidate 31c6d5d19; preserve the
unrelated dirty original iMac checkout. No new branch has been created.

On 2026-10-15, M6 initially published the existing Tenerife 25 m DEM because its 37.5 MB local dependency closure is bounded and independently verifiable. Mutable remote NED mosaics remain legacy-readable until materialized. Existing operator SSH access establishes the private source without new accounts or privileges; actual receiver task credentials and writer access stay in M7.

On 2026-10-15, Roger authorized M6 deployment to wepp1, wepp2, and wepp3. Execute the canonical host-local production script in that order, preserving queue gates, runtime identities, remote-only defaults, and disabled master synchronization. Receiving rollout and recurrence remain M7/M8.


On 2026-10-14, Roger selected wepp.cloud master authority, extension-only local
catalogs, and automatic adoption by catalog membership. This avoids competing
ownership records and special collision handling. The same conversation required
wepp.cloud defaults for unconfigured deployments. Durable authority resides in
`docs/infrastructure/wmesque-catalog-governance.md`.

On 2026-10-14 20:16 UTC, the scaffold preserves implementation proposals as M1
design work instead of asserting unverified transfer access or granting runtime
write privileges. The initial turn authorized scaffolding; the subsequent operator instruction authorizes M1–M5 and forest restarts.

On 2026-10-14, Roger specified that all deployments should be assumed to share
one tailnet for now. Use private synchronization connectivity and exclude public
bulk-transfer and cross-tailnet designs. Prefer rsync over existing SSH access;
verify task reachability and permissions instead of assuming membership supplies
them. This narrows transport design without changing client endpoint defaults.

On 2026-10-14, independent reviews required rejecting disguised VRT downloads,
checking VRT content rather than suffixes, rejecting catalog symlinks, and treating
damaged catalog/server processing as retryable 500. Invalid processing options
are checked before source IO and remain nonretryable 400. These close confirmed
failure paths. Read deadlines use standard urllib/socket hooks because a real
trickling-header test showed ordinary idle timeouts can starve fallback. DNS and
connection setup are explicitly outside a universal wall-clock guarantee.

## Outcomes & Retrospective

Latest M7 checkpoint: actual restricted source-overlay transfer and repeat
convergence succeeded into isolated hpc `/home/roger/wmesque-m7-canary`.
Both files/37,493,165 bytes verify; full GDAL array is rows2747 x columns3255,
EPSG:32628. Non-rsync shell and upload requests are rejected. Source correction
passed 33 focused tests and real protocol regression with master rrsync; independent
QA/security reviews approve source/credential design. The iMac GitHub CLI token
is invalid, preventing canonical publication/protected PR. Operator reauthentication
is required; corrected-image, live serving/fallback and rollback are still pending.

M7 is not complete. Existing candidate is downloaded on hpc; isolated raster
fixtures and destination identity/write checks pass. No master credential,
cluster image/routing or recurrence has changed. The receiving execution record
is open-wepp-org `docs/work-packages/20261014-wmesque-receiver-canary/`.
The actual transfer, local-service parity, fallback and rollback remain gates.

M6 master acceptance passed on wepp1 at 2026-10-15 03:31 UTC. The initial managed resource is `tenerife/136_MDT25_TF`; other datasets remain legacy-readable. Existing operator SSH access over the tailnet successfully transferred and verified its 37.5 MB release. Actual receiver task credentials and writer configuration remain M7. wepp2 and wepp3 rollout and actual-runtime acceptance also passed; see `artifacts/20261015_master_rollout.md`.


M1–M4 implementation and independent reviews are complete. Forest real scheduled
jobs, adoption, concurrent retrieval, SIGKILL during copy, and retry all passed.
An isolated project rebuilt DEM/landuse/soils/spatial climate and prepared inputs;
a fresh 100-year WEPP hillslope run yielded five loss rows and 36,525 daily water
rows through production interchange/report readers. The fresh image passed 67
focused checks and a fresh model execution/readback; final service/scheduler tests
passed 72 with one legacy opt-in skip. The broad suite passed 10,846 tests with
126 skips. Implementation commit: `c138a8bab`. See
`artifacts/20261014_forest_acceptance.md` and retained
JSON/CSV evidence. That forest acceptance did not claim production or Kubernetes activation. M6 now supplies production evidence; M7–M8 keep the package open and recurrence remains disabled.

The batch worker was recreated from the canonical forest build, and WMesque v2
was restarted and validated with an actual local NLCD request. Other deployment
services were not restarted. The source project and live geodata catalog were
not changed. Forest1 parity was inspected read-only; no production rollout is
implied by successful local fixture transfer. M6 subsequently verified the master export for its initial bounded release. Receiving task credentials, SSH identity/home, broader-source capacity, and Kubernetes writer access remain explicit M7 activation gates.

## Context and Orientation


Work in `/home/workdir/wepppy` on forest without creating a branch. The common
client `wepppy/all_your_base/geo/webclients/wmesque.py` accepts a single v2 endpoint
and otherwise uses wepp.cloud. It currently streams directly to the final output
and records metadata afterward. `wepppy/nodb/base.py` exposes the endpoint through
configuration; DEM, soils, landuse, climate, mods, and culvert RQ code share the
client. V1 is deprecated but remains callable and is outside the new routing scope.

`wepppy/webservices/wmesque2.py` opens `/geodata/<dataset>/.vrt`. A VRT is a GDAL
file describing how source rasters combine. Its filename does not identify the
underlying bytes. The server catalog is a text-derived path list and `/health`
does not check data. A revision manifest will identify a published resource's
actual inputs so a replica can report what it serves.

`wepppy/tools/scheduler.py` reads `docker/scheduled-tasks.yml` and periodically
enqueues RQ functions. Docker images already contain rsync for copying files.
Forest uses `docker/docker-compose.dev.yml`. wepp.cloud uses installed wctl
presets and `scripts/deploy-production.sh`; Kubernetes deployment belongs to
`/workdir/open-wepp-org/`. Read nearest instructions before editing each subsystem.

## Plan of Work


### M1 — Contract and fixture design


Read the governance, `docs/infrastructure/wmesque-implementation-assessment.md`,
client/server/scheduler source, and deployment instructions. Inventory a small
representative VRT's source dependencies without modifying live data. Define an
additive manifest schema, stable publication layout, and bounded source export.
Assume a shared tailnet and prefer existing rsync over SSH to the master's tailnet
address if authorized access supports it. Verify connectivity from the actual
RQ task, including Kubernetes routing; host membership alone is insufficient.
Do not add public bulk-transfer or cross-tailnet support. Record the chosen
interfaces in canonical documentation and this plan before implementation.
Resolve writer placement separately from ordinary compute permissions.

Adopt proposed `WMESQUE_ENDPOINTS` as an ordered JSON URL list unless concrete
repository constraints justify a documented alternative. Preserve explicit
single-endpoint arguments above deployment configuration; unset/blank setting
means wepp.cloud only. Malformed or explicitly empty lists fail visibly. Do not
append hidden fallback endpoints. Define retryable failure classes, total time
budget, and expected-revision mismatch semantics; add the required policy ADR.
For unpinned retrieval, document verified replica lag and record actual revision.
Do not add automatic project pinning as part of this change.

Build two small dataset fixtures with matching and differing revisions plus one
local extension. Exit M1 with concrete file layouts, source/export access needs,
expected outputs, and fixture tests designed to fail against current behavior.
No new queue, service, dependency, or privilege without evidence that the simpler
approach cannot meet these acceptance cases and a recorded escalation decision.

### M2 — Compatible server identity


Extend `wepppy/webservices/wmesque2.py` and a focused publication helper to expose
logical IDs and revision manifests while preserving `/catalog` for old clients.
Include raster contents, relevant metadata, and VRT composition in publication
identity. Validate dependencies and paths. Generate manifests during publication,
not per tile request. Return actual revision in response metadata and honor an
optional expected revision without silently substituting another.

Use a stable revision directory and publication reference or an equivalently
tested layout. Resolve source identity once per retrieval and preserve in-flight
reads. Prove old-client compatibility and exact source/metadata agreement on
fixtures. Do not assume replacing a populated directory is atomic.

### M3 — Client routing and output publication


Implement ordered selection centrally in the common client so callers omitting
an override also inherit deployment configuration. Preserve v1 behavior and the
existing successful return contract. Retry bounded network/transient/unavailable
resource failures; surface invalid requests, authorization failures, and local
filesystem errors directly. Specify rate-limit and malformed-response behavior.

Write attempts into temporary files, parse supported raster output, and publish
only complete validated output with matching metadata. Preserve prior destination
on failure and record actual endpoint/revision. Audit climate EDDE provenance and
all callers; update `.pyi` declarations if signatures change. Add configuration
and outage tests before enabling any deployment list.

### M4 — Manual sync and disabled scheduling


Create a focused sync helper and `wepppy/rq/wmesque_rq.py` thin entry point, with a
disabled task in `docker/scheduled-tasks.yml`. Finalize function signatures in M1
and update them here before coding. The helper supports a dry run and a single
manual execution using an explicit source and destination; RQ delegates to it.
Fetch a stable master inventory, copy changes into staging, verify, and publish.
Resources absent from master remain untouched. Master membership makes an adopted
local identifier ordinary sync work even when previous local bytes differ.

Guard destination publication against overlapping jobs and recover after worker
death without permanent lockout. Prevent repeated scheduling from building a
backlog. Record last success, revisions, and failures through existing mechanisms.
Update the RQ dependency catalog and graph. Prove repeat, interrupted copy,
extension preservation, adoption, and concurrent serving before enabling schedules.

### M5 — Forest and Compose acceptance


Run strict integration under actual worker/server identities, groups, mounts,
umask, and configuration. Start with isolated geodata fixtures; then validate a
representative project through DEM, soils, landuse, climate, and prepared WEPP
inputs. Read real rasters and fresh output/report evidence. Cover a projected
culvert request and applicable mod callsites. Retain actual job IDs and source
revisions. Exercise one scheduled update and one interrupted/retried update.
Validate forest1 Compose parity where its deployment differs; document any
non-applicability rather than claiming environment validation from unit tests.

### M6 — Reviews and master deployment


Complete independent correctness and dedicated security artifacts; resolve all
medium/high findings. Run required regression gates. Obtain applicable deployment
authorization, then use the installed wctl preset and canonical production script,
preserving existing deployment contracts. Publish verified master manifests and
the authorized source export. Keep master sync disabled and unconfigured clients
remote-only. Prove existing callers still retrieve valid rasters.

### M7 — Receiving deployment canary


Follow the open-wepp-org repository's own instructions and GitOps deployment
procedure. Establish the authorized geodata writer path and verify its NFS access.
Do not change all compute-worker mounts to writable. Manually sync selected
resources and validate source identity plus local extension behavior. Configure
local-first only after successful retrieval and simulated local failure show
correct fallback. No registry workflow is introduced on wepp.cloud.

### M8 — Recurrence and closure


Enable only the intended receiving sync task; update scheduler readiness without
activating unrelated GC/database tasks. Observe a complete recurring update and
failure recovery with real artifacts. Record deployment revisions and rollback
results. Update package, tracker, governance/runbooks, and root board; archive
this plan only when all required claims have supporting evidence.

## Concrete Steps


From `/home/workdir/wepppy`, inspect `git status --short` and preserve unrelated
changes, especially generated `docs_index.json`. Start M1 with source reads and
fixture design. During implementation use these existing entry points:

    wctl run-pytest tests/services/test_wmesque_retrieve.py
    wctl run-pytest tests/tools/test_scheduler_runtime.py tests/tools/test_scheduler_env_ints.py
    wctl check-rq-graph
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

Add exact new fixture and strict integration commands here as M1 defines them.
Successful checks must report passing tests and no unexpected skips; no pass count
is predicted. If interface declarations change, run the relevant stubtest and
`wctl check-test-stubs`. Lint all changed documentation with `wctl doc-lint --path`.
Do not run deployment commands until the environment prerequisites and authority
are established. Record exact canonical commands used in milestone evidence.

## Validation and Acceptance


With configuration absent, retrieval contacts only wepp.cloud. With local and
master configured, a local dataset succeeds locally; a local outage reaches
master within the defined budget. Explicit overrides win. All failed attempts
leave the prior raster usable. Expected revisions never silently change.

A manual sync copies a complete resource; running it again leaves the same
revision. An interrupted transfer leaves the previous revision usable. A local
extension survives until master adopts its identifier, after which the next
normal sync makes it master-managed without renaming. Concurrent readers see one
complete revision. Raster checks include CRS, resolution, bounds, dtype, nodata,
and values, followed by checks at actual downstream prepared-input paths.

Strict rollout tests must fail on unavailable expected services rather than skip.
Review absent, empty, populated, legacy, malformed, and hostile resource states
separately from endpoint configuration combinations. Record live permissions and
NFS behavior before claiming environment validation. Unit tests and job success
alone do not satisfy artifact acceptance.

## Idempotence and Recovery


Repeated sync compares verified revisions and must not damage local extensions.
Disable the sync schedule first for rollback, then account for active jobs; a
disabled schedule does not cancel work already running. Restore remote-only
client configuration for master resources, retaining explicit local access if
local-only extensions are needed. Keep verified source data and manifests and
use each deployment's canonical code/config rollback. Test compatibility of old
server code with the publication layout before activating it. Never delete local
data merely because a resource disappears from the master catalog.

## Artifacts and Notes


Store concise test output, fixture manifests, raster readbacks, job IDs, candidate
revisions, environment identity, and rollout/recovery results in package artifacts.
Never store credentials. Pending review scaffolds are not approvals. The static
assessment is evidence of code structure only, not functional deployment evidence.

## Interfaces and Dependencies


Keep the existing `wmesque_retrieve` API backward compatible, including integer
success return and explicit endpoint behavior. New expected-revision input and
metadata fields must be additive. Use the existing FastAPI server, urllib client,
GDAL raster tooling, RQ scheduler, and installed transfer tooling. Manifest schema,
sync function signature, and publication layout are explicit M1 deliverables;
implementation must wait for these concrete contracts, not invent independent
interpretations in server and worker code.

Revision note: 2026-10-14 20:16 UTC — initial scaffold from the operator-approved
governance and static assessment; implementation and rollout remain pending.

Revision note: 2026-10-14 UTC — added the operator's shared-tailnet assumption
to narrow M1 transport design; runtime access remains to be validated.

Execution update: 2026-10-14 UTC — operator authorized M1–M5 and forest stack restarts. Concrete interfaces and policy now live in `docs/schemas/wmesque-catalog-contract.md` and ADR-0094. M5 failure injection uses isolated services/data; M6 production actions remain excluded.

Execution update: M2–M4 code and focused tests exist; M5 real-worker integration underway. Interfaces are implemented in `wepppy/webservices/wmesque_catalog.py` and `wepppy/rq/wmesque_rq.py`; scheduler snapshots administrative source/destination into jobs. Initial focused checks passed (16 + 41); one pre-existing opt-in remote smoke skipped.

Execution update: 2026-10-15 03:12 UTC — M6 authorized. All three production checkouts are clean at `84337c967`; forest candidate is `052019426`. Production preflight is checking the intervening deployment delta, queue state, and actual geodata mounts.

Execution update: 2026-10-15 04:04 UTC — M6 completed on all three authorized hosts. Canonical deployments and actual-runtime retrieval passed; master publication and private tailnet transfer verified. Old idle RQ pools on wepp2/wepp3 required a second SIGTERM after confirming no target jobs. No fence remains. A separate docs-indexing failure is recorded in the rollout evidence. M7/M8 remain pending.

Handoff preparation: read-only forest inspection found no local Kubernetes
administration tools or kubeconfig. The receiving repository documents the iMac
as management root of trust and dev-01 for Linux builds. The recommended M7
execution handoff is `../m7_imac_handoff.md`; it preserves receiving-repository
controls and does not assert new deployment authorization. M7 remains pending.
