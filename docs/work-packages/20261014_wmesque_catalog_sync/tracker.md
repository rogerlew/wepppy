# Tracker — WMesque Catalog Synchronization

## Quick Status

**Started**: 2026-10-14 20:16 UTC
**Updated**: 2026-10-15 04:04 UTC
**Phase**: M1–M6 complete; receiving rollout pending
**Next milestone**: M7 receiving-deployment access and canary
**Security**: High; independent implementation review approved, findings closed
**Plan**: [Active ExecPlan](prompts/active/wmesque_catalog_sync_execplan.md)

## Task Board

- [x] Capture governance and static analysis; scaffold package and reviews.
- [x] M1: Resolve manifest, transfer/publication layout, endpoint/error contract, and writer placement.
- [x] M2: Implement compatible server metadata and publication fixtures on forest.
- [x] M3: Implement client priority/failover and provenance on forest.
- [x] M4: Implement manual sync/RQ wrapper with scheduling disabled.
- [x] M5: Validate forest scheduled integration, downstream artifacts, and Compose parity.
- [x] M6: Reviews approved; all three production hosts deployed; master publication and private export validated.
- [ ] M7: Canary receiving deployment sync and local-first routing when authorized.
- [ ] M8: Enable recurrence, validate recovery, and close with evidence.

## Decisions

- **2026-10-14 20:24 UTC** — Operator specified a shared tailnet for all deployments for now. Governance “Scheduled Synchronization” and M1 now use private sync connectivity; rsync over SSH is the preferred proposal. Actual task connectivity and permissions remain unverified. Public bulk-transfer and cross-tailnet support are excluded to keep implementation simple.
- **2026-10-14 20:16 UTC** — Operator selected wepp.cloud as master, extension-only receiving catalogs, and seamless adoption through ordinary sync. Authority: governance, “Catalog Authority and Extensions.” Avoid runtime conflict machinery.
- **2026-10-14 20:16 UTC** — Operator requires unconfigured deployments to use wepp.cloud. Authority: governance, “Deployment Endpoint Defaults.” Local service installation alone must not change routing.
- **2026-10-14 20:16 UTC** — Scaffold only this session. Interface details in the assessment remain proposals until M1 resolves them; no invented production access or writer permissions.

## Risks and Open Decisions

| Issue | Impact | Next action |
| --- | --- | --- |
| Master export validated under operator SSH access; receiver credentials pending | Receiving task cannot yet pull | Validate actual task identity/trust/writer access in M7; broader resources, including NED materialization, need bounded publication |
| Kubernetes geodata is read-only for compute workers | Sync cannot run on ordinary workers as configured | Select smallest authorized writer path before rollout |
| Kubernetes scheduler dry-run and three-task assertion | Naive activation enables unrelated jobs or fails readiness | Define sync-only activation in deployment repo |
| Replica lag and unpinned requests | Different runs may use different revisions | Document behavior and provenance; do not claim name-based reproducibility |
| New dataset source families | Unhandled driver sidecars could invalidate a published copy | Validate representative dependency closure before publication; GeoTIFF/VRT fixture gate passed |

## Verification Checklist

- [x] Focused tests and broad `wctl run-pytest tests --maxfail=1` gate.
- [x] Stub checks if interfaces change; changed-code exception checks.
- [x] RQ dependency catalog, graph check, and actual job tree.
- [x] Real raster/source checks, downstream prepared inputs, and fresh representative output.
- [x] Default, override, outage, interrupted sync, overlap, extension, and adoption tests.
- [x] Operator documentation and fallback/timeout ADR.
- [x] [Correctness review](artifacts/20261014_correctness_review.md) complete.
- [x] [Security review](artifacts/20261014_security_review.md) complete.
- [x] M6 authorized master rollout and rollback-layout evidence; no open medium/high findings.
- [ ] M7/M8 receiving rollout, recurrence, and recovery evidence.

## Progress Notes

### 2026-10-14 20:24 UTC — Shared tailnet assumption

Updated governance, assessment, package scope, and active plan. Runtime behavior,
client defaults, and deployment permissions are unchanged. Implementation remains
unstarted.

### 2026-10-14 20:16 UTC — Scaffold

Created brief, active plan, tracker, and pending review artifacts from the static
assessment. No tests of runtime behavior or live deployment actions were performed.
Next executor starts M1 and maintains both this tracker and the plan. Documentation
lint passed for all five package files, the root project tracker, and AGENTS.md.
The root onboarding size gate passed at 160 lines; whitespace checks passed.
Spelling preview suggested only “afterward” to “afterwards”; retained the existing
valid American spelling.

### 2026-10-14 UTC — Execution

Operator authorized M1–M5 and forest restarts. Contract checkpoint `193df8b8c`
passed two independent reviews. First focused runs: 16 passed/1 legacy opt-in
skip and 41 passed. Broad suite and implementation reviews running. M5 uses
isolated fixture data/services with real forest batch workers; no production
activation. Scheduler snapshots source/destination arguments to avoid worker
environment drift. NED remote VRT dependencies require operator materialization
before managed publication; legacy retrieval is preserved.

### 2026-10-14 UTC — Forest artifact acceptance

Real scheduled batch jobs verified adoption, failed-copy recovery, and concurrent
reads across publication. Actual SIGKILL during a 268 MB copy preserved the old
catalog and retry succeeded. An isolated canonical project fork rebuilt DEM,
landuse, soils, and spatial PRISM climate, prepared model files, and executed a
100-year hillslope. Native report readers verified five loss rows and 36,525
daily-water rows. Focused service/scheduler tests: 72 passed, one legacy opt-in
skip; EDDE/helpers: 59 passed. API stubs, stub completeness, RQ graph/job inspection,
and changed exception gates pass. Both independent reviews approved fixes.
See [acceptance evidence](artifacts/20261014_forest_acceptance.md). Broad suite and
image validation remain in progress. Read-only forest1 checks found matching
identity/mount ownership and the same missing SSH client; Dockerfiles now add it
without changing identity, credentials, or mounts.

### 2026-10-14 21:24 UTC — M1–M5 complete

Implementation committed as `c138a8bab`, following contract checkpoint `193df8b8c`.
Broad gate finished successfully: **10,846 passed, 126 skipped** in 48m55s.
Final focused service/scheduler suite: **72 passed, 1 legacy opt-in skip**;
EDDE/helpers: **59 passed**; fresh-image suite: **67 passed**, no skips. A real
EDDE normals acquisition also verified written source/revision maps. Rebuilt-image
WEPP execution and native report readback passed. The canonical job-tree helper
confirmed the expected successful/failed/recovered fixture jobs with no children.

Only the forest batch worker was recreated and WMesque v2 restarted; post-restart
local raster readback passed. Defaults remain wepp.cloud-only and sync disabled.
Forest1 was inspected read-only; wepp.cloud and Kubernetes were not deployed.
The developer task UID lacks an SSH passwd entry, so export/credentials/identity
and large-resource validation remain explicit rollout gates, without a workaround.
Docs/Compose/graph/stub/exception checks passed; no open medium/high review finding.
The package stays open for M6–M8 and its active plan is retained.

### 2026-10-15 03:12 UTC — M6 authorized

Operator authorized production deployment on wepp1, wepp2, and wepp3. Host identities and clean checkouts verified at `84337c967`. Queue and deployment-delta checks precede activation. Installed RQ rejects the runbook’s `rq-info --detailed` flag; direct read-only started-registry inspection supplies the required gate evidence.

### 2026-10-15 03:31 UTC — Master publication validated

wepp1 canonical deployment completed and released the global queue fence. Tenerife publication and repeat publication passed; pinned pixels/geospatial metadata match the baseline, original hashes are unchanged, and old-image retrieval remains compatible. Actual tailnet rsync verified the full release in 3.5 seconds. wepp2 is building; wepp3 awaits its ordered deployment. See [M6 evidence](artifacts/20261015_master_rollout.md).

### 2026-10-15 03:42 UTC — wepp2 complete, wepp3 building

wepp2 deployed successfully and its actual batch runtime passed managed/legacy raster and revision checks. Old idle pools needed a second SIGTERM after unregistering; zero started jobs and the owned queue fence were verified before that bounded recovery. The canonical script then completed and resumed dequeueing. wepp3 preflight passed and its fork/archive-only build is underway.

### 2026-10-15 04:04 UTC — M6 complete

All three hosts deployed `052019426` through their canonical presets and scripts, in order. All actual runtimes passed managed/legacy raster and revision checks. The initial Tenerife release and private source transfer are verified; old-image retrieval remains compatible. Global queue suspension/fence is cleared. wepp3 unrelated containers were unchanged. See [rollout evidence](artifacts/20261015_master_rollout.md), including shutdown recovery and the separate documentation-indexing failure. M7/M8 remain pending; defaults stay remote-only and sync disabled.

### M7 administration handoff preparation

Read-only forest inspection found no kubectl, Flux CLI, Talos CLI, configured
KUBECONFIG, or default kubeconfig. The open-wepp-org deployment architecture
identifies the iMac as management root of trust and dev-01 as its Linux build
node. Recommended execution location: administrative iMac. Prepared the
[M7 agent handoff](prompts/m7_imac_handoff.md); this is preparation, not M7
execution or a new live-change grant. No cluster configuration was changed.
