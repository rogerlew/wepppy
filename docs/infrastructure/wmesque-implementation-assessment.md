# WMesque Implementation and Rollout Assessment

> Static analysis, 2026-10-14. Proposed sequencing, not an active execution plan.

This is the pre-implementation snapshot. Implemented interfaces are authoritative
in the [catalog contract](../schemas/wmesque-catalog-contract.md); current execution
and acceptance are in the [package tracker](../work-packages/20261014_wmesque_catalog_sync/tracker.md).

## Scope and Conclusion

Implement and validate in the forest WEPPpy checkout first, publish compatible
server support on wepp.cloud, then opt receiving deployments into synchronization
and local-first retrieval. Preserve wepp.cloud as the default for deployments
without explicit configuration. Follow [catalog governance](wmesque-catalog-governance.md).

This assessment inspected repository source and the manifests in
`/workdir/open-wepp-org/`; it did not inspect live catalogs, permissions, queues,
network reachability, or raster contents. No runtime changes or deployments were
performed. All rollout gates below are future validation, not completed evidence.

## Confirmed Implementation Gaps

| Area | Current evidence | Needed change |
| --- | --- | --- |
| Client selection | `wepppy/all_your_base/geo/webclients/wmesque.py` accepts one v2 endpoint; otherwise uses wepp.cloud. | Central ordered endpoint resolution and bounded failover. |
| Client publication | Client streams directly to the destination, then writes `.meta`; timeout is 300 seconds per request. | Stage each attempt, validate the raster, publish only a successful result with matching provenance; budget total failover time. |
| NoDb integration | `wepppy/nodb/base.py` reads one `wmesque.endpoint`; DEM, landuse, soils, climate, mods, and culvert callers use the common client. Some omit the override. | Resolve deployment defaults in the common client, preserve explicit overrides, audit callsites rather than adding lists to every controller. |
| Legacy protocol | V1 is deprecated but callable; NoDb's missing-version fallback remains 1. | Scope new functionality to v2; preserve v1 behavior and track retirement separately. |
| Catalog | `wepppy/webservices/wmesque2.py` returns path strings loaded from a text file; filtering is by path prefix. | Add portable logical identifiers and revision manifests without breaking existing `/catalog` consumers. Existing catalog entries are not proof of usable rasters. |
| Retrieval identity | Server opens `/geodata/<dataset>/.vrt`; adjacent `metadata.json` is optional. | Publish and return a verified dataset revision; optionally require an expected revision and reject mismatches before generating output. |
| Readiness | `/health` returns static OK. | Retain liveness behavior; use real catalog and raster retrievals for rollout acceptance. |
| Recurring tasks | `wepppy/tools/scheduler.py` already enqueues RQ tasks from YAML with intervals, enable flags, delay, and jitter. | Add an opt-in sync task using this machinery. Literal cron expressions are unnecessary for the requested recurring work. |
| Sync transport | Both Dockerfiles already install rsync; no WMesque source-transfer contract was found. | Establish a bounded source export and receiver destination; evaluate reuse of rsync before adding an HTTP bulk-data protocol. |
| Tests | `tests/services/test_wmesque_retrieve.py` has basic CRS tests and an opt-in network smoke test that skips on retrieval errors. | Add deterministic failover/sync tests and a separate strict acceptance test that fails when expected retrieval fails. |

Related callsites include `nodb/core/{ron,landuse,soils,climate_build_helpers}.py`,
`nodb/mods/{treecanopy,shrubland}`, and `rq/culvert_rq.py`. Climate EDDE provenance
also reads the configured endpoint; actual serving endpoint/revision must come
from retrieval metadata when failover occurs.

## Proposed Small Implementation Boundary

### Endpoint configuration

Use one deployment variable, provisionally `WMESQUE_ENDPOINTS`, containing an
ordered JSON array of v2 base URLs. Proposed precedence:

1. Existing explicit `wmesque_endpoint` argument: one authoritative endpoint.
2. Nonblank deployment list: exactly that ordered list.
3. Unset or blank deployment setting: only
   `https://wepp.cloud/webservices/wmesque2/`.

Reject malformed or explicitly empty lists instead of quietly changing routing.
Do not append hidden endpoints to an explicit list. Forest can opt into
`http://wmesque2:8030` followed by wepp.cloud; Kubernetes can use
`http://weppcloud-wmesque2:8030` followed by wepp.cloud. These service names exist
in manifests; reachability must still be demonstrated from actual consumers.
Pass configuration to web, RQ workers, and other retrieval processes consistently.

Try the next endpoint on connection/timeout failures, dataset absence, transient
server errors, or an unavailable expected revision. Invalid requests and access
errors must surface directly. Define handling for rate limits and damaged/truncated
responses explicitly. Local filesystem errors must not trigger network failover.
Do not add persistent health registries, automatic discovery, or circuit breakers
without evidence they are needed. Log attempts and preserve the final cause.

### Revision metadata and publication

Use a small versioned manifest per published dataset with a content digest and
relative source inventory. Include referenced raster bytes, meaningful metadata,
and VRT composition, not merely the `.vrt` hash or mtimes. Validate absolute and
external VRT references before deciding transfer boundaries; dataset directories
are not proven self-contained by the current sync inventory.

Generate manifests at publication time, not during every raster request. Preserve
the existing `/catalog` response and add a manifest endpoint or explicitly
versioned representation. Add revision identity to existing response provenance.
Do not make old unversioned clients fail when upgraded servers are deployed.

Capture a stable source revision before copying. Stage and verify it, then publish
through one consistent pointer/layout so requests cannot observe a mixed VRT and
source revision. Resolve the pointer once per request; retain old source files
until in-flight reads finish. Test this on actual mounted storage. A directory
rename over an existing populated directory is not a sufficient publication design.

Keep revision enforcement small: a caller-supplied expected revision must be
honored. Automatic project-wide pinning, historical-version APIs, and retention
automation are separate design work, not prerequisites for endpoint configuration.
For unpinned requests, explicitly document that a verified replica may lag master;
record the revision used and do not claim reproducible rebuilds from names alone.

### Synchronization

The operator has specified a shared tailnet for all deployments in the initial
scope. Prefer existing rsync over SSH to a master tailnet address, subject to
verification of available SSH access and the task's network path. This is a
transport proposal, not evidence of configured access. Do not add public bulk-data
endpoints or cross-tailnet support. Keep normal wepp.cloud retrieval defaults.

Add a thin RQ entry point backed by a separately testable sync function and a
disabled-by-default entry in `docker/scheduled-tasks.yml`. Reuse the existing
scheduler and existing queues where their worker permissions permit execution.
Do not add a general scheduling framework.

One job fetches the master inventory, copies changed selected resources, verifies
them, and publishes them. Catalog membership determines master ownership; a local
extension adopted under the same identifier automatically follows this same path.
Preserve resources absent from master. Do not interpret disappearance from master
as permission to delete local data. No separate conflict database or adoption job.

Provide dry-run/manual execution before scheduling. Use a destination-scoped
overlap guard with crash/timeout recovery; a fixed RQ job ID alone is not a proven
locking mechanism. Record last success, resource revisions, failures, and a concise
transfer summary. Prevent duplicate queued work from growing while a sync is slow.
Reuse existing RQ inspection and logs rather than introducing a monitoring service.

## Deployment Constraints

- Forest uses `docker/docker-compose.dev.yml`, with UID/GID configuration and a
  `${GEODATA_DIR}:/geodata` mount. Prove write/read permissions with actual worker
  and WMesque identities; do initial sync tests in an isolated geodata fixture.
- wepp.cloud uses installed `wctl` presets and `scripts/deploy-production.sh`.
  Preserve its build, topology, RQ fencing, Redis, static-asset, and health contracts.
  Ordinary application health checks do not replace WMesque artifact acceptance.
  Production workers must receive the same client configuration as the web process.
- open-wepp-org uses Kubernetes and its own image/GitOps rollout. Relevant files
  are `clusters/openwepp/apps/weppcloud/{request-plane,rq-worker,scheduler,storage,web}.yaml`
  and `docs/operations/weppcloud-rq-execution-plane.md` in that repository.
- Kubernetes RQ manifests mount geodata read-only, using UID 1000/GID 993. Ordinary
  compute workers cannot perform this sync as configured. A narrowly authorized
  writer location is a concrete prerequisite; do not silently grant every worker
  write access or add a new worker topology before resolving the smallest option.
- Kubernetes scheduler manifests set `SCHEDULE_DRY_RUN=true`; readiness asserts
  that value and exactly three tasks. Adding/enabling sync requires updating this
  contract deliberately. Do not globally enable existing GC/database jobs as a
  side effect. A sync-only schedule using the existing scheduler implementation is
  an option if those jobs must remain disabled; deployment shape remains to decide.
- Transfer credentials, source export permissions, network access, storage capacity,
  VRT dependency closure, and real catalog contents remain unverified. These block
  live sync activation, not client/server development on fixtures.

## Implementation and Rollout Sequence

| Stage | Work | Exit evidence |
| --- | --- | --- |
| 1. Contracts on forest | Create an implementation work package and active ExecPlan; settle config precedence, manifest schema, error classes, unpinned behavior, source export, and publication layout. Update normative contracts before code. | Reviewable interfaces and fixture acceptance cases; no speculative new services. |
| 2. Server metadata on forest | Implement publication manifest tooling and backward-compatible v2 catalog/retrieval identity. | Old client still retrieves; manifest matches source files; expected-revision mismatch rejected; raster semantics validated. |
| 3. Client on forest | Implement endpoint resolution, bounded attempts, staged downloads, and actual-serving provenance. Update `.pyi` if API changes. | Deterministic tests cover defaults, overrides, ordered failover, output preservation, and revision handling. Default remains remote-only. |
| 4. Manual sync on forest | Implement sync function/RQ wrapper with scheduling disabled; test two small dataset trees and a local extension. | Interrupted sync preserves service; repeat is harmless; adoption cutover succeeds; concurrent reads see complete revisions. |
| 5. Forest integration | Exercise local WMesque, RQ worker, scheduler, and representative project preparation under deployed identities/mounts. Enable the fixture task explicitly. | Actual job IDs, successful recurring execution/recovery, parsed rasters and downstream prepared WEPP inputs; strict tests cannot skip failures. |
| 6. Publish on wepp.cloud | Deploy compatible server/client code through canonical production workflow; publish verified master inventory and authorized source export. Keep remote-only client default and sync disabled on master. | Existing retrieval consumers pass real raster checks; published manifests correspond to source bytes. |
| 7. Receiving deployment canary | Roll out open-wepp-org code/config through its own procedures; establish approved writer access; manually sync selected datasets before enabling local-first retrieval. | Real Kubernetes writer/server identity and NFS checks, source equality, local extension retrieval, and forced local outage fallback pass. |
| 8. Enable recurrence and local-first | Enable only the intended sync schedule; configure ordered endpoints after the canary passes. Expand synced resources after one successful update/recovery cycle. | Last-success/revision visibility, repeat/adoption tests, and representative end-to-end run pass. Other deployments retain wepp.cloud defaults. |

Stages 2-4 can be separate changes with features disabled. Do not activate a local
server merely because the client can reach its health endpoint. No production
deployment or permission change is authorized by this assessment alone.

## Test Matrix and Gates

| Boundary | Required cases |
| --- | --- |
| Configuration | Unset/blank defaults to wepp.cloud; valid ordering; malformed/empty list fails; explicit override wins; v1 unchanged. |
| Failover | Local hit; missing dataset; connection failure; timeout; transient server error; all endpoints fail; invalid request/auth failure; revision mismatch; truncated transfer. Verify attempts and total budget. |
| Raster publication | Previous file survives failed attempts; metadata identifies actual source; raster opens with expected CRS, bounds, resolution, dtype, nodata, and values. Check supported output formats. |
| Catalog/source | Missing VRT/source, path escape, external references, corrupt metadata, differing bytes under the same name, source mutation during copy. |
| Sync | Initial copy, no-op repeat, update, interruption, disk/permission failure, overlap and worker death, extension preservation, automatic adoption including differing previous local bytes. |
| Serving during sync | Retrieval during publication observes one complete revision; old in-flight reads remain valid; expected revision is never substituted. |
| Downstream | DEM, landuse, soils, and climate acquisitions; projected culvert extent; representative mod retrieval; metadata propagation into prepared inputs and report provenance where applicable. |
| Scheduling | Disabled by default; manual/dry run; enabled interval; duplicate prevention; failure recovery; no unrelated Kubernetes tasks enabled. |

Run focused tests through `wctl run-pytest`, then the required substantive-change
gate `wctl run-pytest tests --maxfail=1`. Run stub checks if API surfaces change.
Update `wepppy/rq/job-dependencies-catalog.md`, run `wctl check-rq-graph`, and retain
a live job tree for new wiring. Run docs lint and changed-code exception checks.
The implementation work package must include review of the cross-deployment
transfer/write boundary. No frontend gates are needed unless UI code changes.

Before project metadata/schema edits, record a compatibility/regression plan;
keep provenance additive and validate generated run artifacts. Document timeout
and fallback policy choices under the parameterization ADR standard when implemented.

## Rollback and Remaining Decisions

Disable the receiving sync task first and account for any active job; disabling a
schedule does not stop an already running transfer. Set the deployment list back
to wepp.cloud-only to bypass local replicas for master datasets. Local-only
extensions will then be unavailable unless an explicit local endpoint is retained.
Keep verified data and manifests; do not run deletion or reverse synchronization.
Use each deployment's canonical code/config rollback procedures. Test that older
server code can still read the chosen publication layout before adopting it.

Resolve during stage 1: actual transfer access; minimal Kubernetes writer placement;
resource selection and disk budget; revision representation/publication layout;
timeout budget; recurrence interval. Start with supported tooling and fixture
evidence. Avoid adding multi-master reconciliation, persistent endpoint health
state, automatic project migration, or a new scheduler to answer these questions.
