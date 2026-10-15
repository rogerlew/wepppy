# Tracker — WMesque Catalog Synchronization

## Quick Status

Final checkpoint (2026-10-15 UTC): operational rollout and recovery accepted;
full validation closeout blocked. Receiving PR199 at846f0f81 restores healthy
local-first admission,33/33 replicas and18/18 nodes. Live sync/full artifact
checks, actual local/master/local routing, existing-project reads and model
outputs pass; RQ resumed, recurrence disabled. Baseline full suite10664 passed,
126 skipped,1 failed at98%; isolated READONLY notification-latency test reproduces
123.88ms p95 overhead versus50ms limit. Cause undiagnosed; no threshold waiver.
Exact-image65 tests pass separately. Stubtest lacks its homelab runner. Historical
checkpoints below are retained, not current blockers except these validation items.

Latest checkpoint supersedes historical holds below: source PR653 merged,
paired current runtime5f46ed68 deployed through receiving PR192–194; actual
native/model/Parquet and65 focused tests pass. Restricted live sync and repeat,
complete hash/raster verification, unchanged originals/extensions, local/master
parity and404/outage/revision checks pass. Local-first default receipt passes;
remote-only recovery is underway with admission drained via PR195–197.
M8 remains disabled; full forest baseline suite still running.

Current M7 checkpoint (2026-10-15 UTC): bounded hpc writer, restricted master key
and branches explicitly approved. Actual isolated receiver transfer/readback and
convergence pass; source correction passes 33 focused tests and independent
QA/security reviews. GitHub access is restored; source `467901f08` pushed and
build `38683704256` started. Promotion is held: the canonical native dependency
pin fails the candidate's startup hash/API checks, and the common-image delta
contains unrelated model-default changes and new saved-state reader floors.
Operator subsequently selected the full current-state upgrade. Validated native
release `0515272453e36fe071c7812fb9d8ca2cf1642d08` is now published and the
canonical image workflow pin updated; rebuilt-image/recovery gates remain.
Live service/routing/rollback remain pending; M8 disabled. Receiving evidence:
`docs/work-packages/20261014-wmesque-receiver-canary/artifacts/image-delta-review.md`
in the open-wepp-org repository.

**Started**: 2026-10-14 20:16 UTC
**Updated**: 2026-10-15 UTC
**Phase**: M1–M6 complete; M7 operational acceptance passed, validation closeout blocked
**Next milestone**: M7 baseline latency-test disposition; M8 remains excluded
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
- [ ] M7: Operational sync/local-first/recovery accepted; full validation closeout blocked by reproducible baseline latency test.
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

### Latest M7 execution — restricted-key acceptance complete, publication held

Roger approved the restricted master public-key entry and M7 branches. Both
completed. Real receiver source-overlay transfer passed dry-run, copy, complete
hash verification, full GDAL readback and repeat convergence. Shell execution
and rsync upload dry-run failed at rrsync as required. Retained evidence lives in
the receiving package `artifacts/20261015_transfer_evidence.md`; source QA is
`artifacts/20261015_m7_qa_review.md`, and independent security review is in the
receiving package. The iMac's `gh auth status` reports an invalid credential;
operator reauthentication is the external publication blocker. No corrected
immutable image, live geodata publication, cluster promotion or local-first
routing has occurred. No master service restart or policy broadening occurred.

### 2026-10-15 UTC — Authorized iMac/hpc M7 execution

Roger selected and authorized the bounded hpc container and M7 deployment;
master credential and PR branch permissions remain separately pending.
Cluster/Flux healthy; all 15 workers idle, zero started/scheduled jobs, retained
deferred counts default=11 and batch=3. Candidate 31c6d5d19/digest 97b1abe5...
downloaded on hpc. Actual UID:GID 1000:993/home /home/roger/umask 0022 passed
destination write/fsync/read/cleanup and isolated full-raster adoption, extension,
convergence and corrupt-transfer recovery checks. Original datasets unchanged.

Confirmed failure: installed master rrsync rejects `--protect-args` (`-s`).
Prepared a minimal client correction with safe remote-path validation and explicit
`--no-protect-args`; preserve strict SSH trust and server-side read-only/path
enforcement. Source/tests/docs live in detached `/Users/roger/src/wepppy-wmesque-m7`;
the original dirty checkout is preserved. Actual restricted SSH transfer and
rebuilt-image deployment are still unverified. Receiving records:
open-wepp-org `docs/work-packages/20261014-wmesque-receiver-canary/`.

Focused source-overlay acceptance passed 33 catalog tests in the published
candidate image on hpc; the real rsync protocol regression also passed against
the exact master rrsync script. Canonical wctl/full-suite execution is blocked
on the iMac (no wctl); this was explicitly an isolated image test, not that gate.
No rebuilt image, master credential installation, GitOps promotion or live
receiving transfer is claimed. Do not promote the old candidate digest before
publishing the corrected source. Original checkout remains untouched; detached
checkout also shows an unrelated TIFFW artifact change from checkout/filtering,
which is excluded from this work.

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
