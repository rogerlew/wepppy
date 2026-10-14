# Implement WMesque priority retrieval and master synchronization


This is a living ExecPlan maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective
current together with the package tracker. Status: executing M1–M5; forest restarts authorized. M6–M8 remain pending.

## Purpose / Big Picture


A deployment should explicitly choose local WMesque raster service first and
wepp.cloud second, while deployments with no configuration keep using wepp.cloud.
Non-master deployments should periodically copy master resources through existing
RQ jobs and retain their own additional datasets. When wepp.cloud adopts a local
identifier, the normal next sync updates it from master without a migration job.
Success is demonstrated by real raster retrieval, outage failover, and verified
sync/adoption followed by downstream project input and output readback.

## Progress


- [x] (2026-10-14 20:16 UTC) Governance, static assessment, and work-package scaffold prepared.
- [ ] M1: Finalize concrete interfaces and bounded fixture/publication design.
- [ ] M2: Add backward-compatible server manifest and revision support.
- [ ] M3: Add client configuration, bounded failover, and staged publication.
- [ ] M4: Add manual synchronization and disabled scheduled RQ integration.
- [ ] M5: Validate forest integration and production-equivalent Compose behavior.
- [ ] M6: Complete reviews and authorized wepp.cloud publication.
- [ ] M7: Complete authorized receiving-deployment canary.
- [ ] M8: Enable recurrence/local-first routing and retain recovery evidence.

## Surprises & Discoveries


The existing `wepppy/tools/scheduler.py` already supports interval-based RQ
enqueueing; a new scheduler is unnecessary. Kubernetes manifests in
`/workdir/open-wepp-org/clusters/openwepp/apps/weppcloud/` mount geodata read-only
on compute workers. Their scheduler is dry-run-only and its readiness check
asserts exactly three tasks. These are static observations, not live verification.
The existing WMesque network test skips retrieval exceptions, so it cannot be
the strict rollout acceptance test.

## Decision Log


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

## Outcomes & Retrospective


Only the static assessment and planning scaffold exist. No runtime implementation,
artifact validation, review approval, or deployment is claimed. M2 through M8
deliver and validate the working feature; scaffolding cannot close this package.

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
