# Implement WMesque priority retrieval and master synchronization


This is a living ExecPlan maintained under `docs/prompt_templates/codex_exec_plans.md`.
Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective
current together with the package tracker. Status: COMPLETE — M1–M8 accepted; daily hpc recurrence enabled on 2026-10-16.

## Purpose / Big Picture


A deployment should explicitly choose local WMesque raster service first and
wepp.cloud second, while deployments with no configuration keep using wepp.cloud.
Non-master deployments should periodically copy master resources through existing
RQ jobs and retain their own additional datasets. When wepp.cloud adopts a local
identifier, the normal next sync updates it from master without a migration job.
Success is demonstrated by real raster retrieval, outage failover, and verified
sync/adoption followed by downstream project input and output readback.

## Progress

- [x] (2026-10-16 UTC) Operator accepts M7 based on operational rollout/recovery, latency, full baseline and matching stubtest. See `artifacts/20261016_m7_closeout.md`. General isolation findings move to `docs/dev-notes/test-isolation-followup.md`; exhaustive CI becomes weekly/manual, automatic CI retains one baseline.

- [x] (2026-10-16 UTC) Hosted `38825109720` baseline passes 10,671 tests/329 skips; all five unchanged-order repeats pass.
- [x] (2026-10-16 UTC) Repair lazy snapshot imports, framework/native initialization findings, persistent report/Daymet/soil stubs, and strict BLC helper forwarding. Matching runner passes 15 focused per-file checks including real WBT; additional checker regressions pass 27 tests. Final-source collection rechecks pass all 36 flagged files; four additional files pass actual combined/per-file isolation with no findings.
- [x] Hosted `38860272720` baseline passes 10,690 tests/329 skips and stubtest passes; exhaustive isolation reports 18 state findings, transferred to the separate backlog under the revised acceptance scope.

- [x] (2026-10-15 UTC) Local stubtest repaired: two undefined `Optional` annotations now use `float | None`; all eight default modules and test-stub completeness pass.
- [x] (2026-10-15 UTC) Operator approved and Forest completed PostgreSQL migration to `docker_forest-postgres-ssd`; stopped bytes/metadata and database counts match, durability preserved, backups and public health restored. All four latency gates pass: READONLY added p95 5.81 ms, TTL 4.73 ms.
- [x] (2026-10-15 UTC) Runner-02 pinned isolated runtime passes eight stubtest modules, completeness, and 77 database/catalog/NoDb tests with 648 verified LFS assets. Generated workflow preserves the full isolation gate as a separate long job.
- [x] (2026-10-15 UTC) Hosted stubtest job 116520586851 passes on runner-02 at `5325742bf`, including LFS materialization and cleanup. First hosted preflight caught fetched-but-unmaterialized LFS objects; explicit checkout corrected it without bypassing verification.
- [x] (2026-10-15 UTC) Hosted baseline exposed `/wc1` lock permissions and deployment-account dependencies. CI uses the existing writable lock-directory setting; isolated account fixtures preserve real identity resolution. Ten runner transport integration tests pass.
- [x] (2026-10-15 UTC) Second hosted baseline exposed missing development `SITE_PREFIX`; CI now uses `/weppcloud`, matching Forest. All ten runner d-Tale tests pass without assertion changes.
- [x] (2026-10-15 UTC) Full Forest regression passes: 10,872 passed, 126 skipped in 2,836.09 seconds, including all catalog latency checks.
- [x] (2026-10-15 UTC) Final configuration `f8ce2bb92` passes hosted stubtest job `116535294278`, including cleanup.
- [x] (2026-10-15 UTC) Commit `24dcc083e` supplies exact committed management fixtures, resolving the baseline failure after 2,844 passes. Focused tests pass on Forest and a fresh committed-source extraction on runner-02 with ignored matrix data absent.
- [x] (2026-10-15 UTC) Resolved run `38792764959` missing binary inputs in `9ce4195f8`. The binary and two seed-generator test modules use dedicated committed fixtures; 89 tests pass on both Forest and runner-02 with the ignored source absent and all 16 hashes verified.
- [x] Historical failure resolved by subsequent passing baseline: run `38797621501` passed stubtest then failed after 5,843 baseline passes on a unit test using the real cache/run-directory boundary. Affected orchestration tests now explicitly record scoped invalidation; 19 focused browser/schema/CSRF tests and 4,693 remaining-group tests pass on runner-02. See `artifacts/20261015_validation_followup.md` and retained raw samples.
- [x] (2026-10-15 UTC) GitHub restored; source `467901f08` pushed; canonical build `38683704256` started. Exact published candidate fails native startup preflight; no cluster promotion performed.
- [x] (2026-10-15 UTC) Operator selected full current-state openwepp upgrade, including other current behavior changes. Published validated native release `0515272453e36fe071c7812fb9d8ca2cf1642d08`; canonical workflow pin corrected to pair interchange and climate releases.
- [x] (2026-10-15 UTC) Paired image5f46ed68 built from a217f7342/native0515272; native hashes/API, PRISM cache,65 exact-image tests and actual worker WEPP/Parquet readback pass. Full current-runtime rollout restored healthy admission via receiving PR192–194.
- [x] (2026-10-15 UTC) Live restricted hpc sync, complete release hashes/raster read, convergence and unchanged original/local-extension hashes pass; local/master parity,404/outage fallback and wrong-revision rejection pass.
- [x] (2026-10-15 UTC) Deployed local-first/remote-only recovery/local-first acceptance passes; PR199 restored admission at846f0f81. All33 replicas available,18 nodes Ready, public health OK; actual web/batch default routing and existing-project reads pass; no RQ fence remains.
- [x] (2026-10-15 UTC) Resolved original broad-validation failure (READONLY 123.88 ms versus 50 ms) through the approved storage migration, verified in the full Forest suite. Hosted stubtest now has a qualified matching runner; no threshold waiver.

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
- [x] M7: Operational canary, recovery, latency, full Forest/hosted baseline and hosted stubtest accepted. General isolation is a separate backlog, not an M7 gate.
- [x] (2026-10-16 UTC) M8 complete: versioned open-wepp-org script/systemd units deployed on hpc; two actual timer cycles, full release/raster readback, failure/catalog preservation, duplicate rejection and idle timer disable/re-enable pass. Daily recurrence enabled. See artifacts/20261016_m8_closeout.md and receiving PR201.

## Surprises & Discoveries

2026-10-16: the latest hosted job took 4h42m despite all test executions passing.
Its five full repeats used unchanged order; final findings concern environment
and test-module state. This expanded M7 into unrelated repository maintenance.

The per-file checker invoked lazy module attributes while observing singleton
state, crashing after six files had passed pytest. Its pre-startup/post-shutdown
snapshot also counted pytest and native-library initialization as pollution.
Two opt-in real WBT tests exposed missing strict-failure forwarding in the
TerrainProcessor helper; the broad suite had skipped those cases.

A broader clean-runner probe found unit tests using real cache and configuration
lock paths despite mocked controllers. It also found missing Node and generated
controller assets. Use explicit test-boundary fixtures and temporary paths; extend
only the CI image with existing Node 20 and locked Playwright/Chromium dependencies,
invoke the canonical controller builder, and initialize the disposable account
schema from current models plus the canonical preferences migration for named
constraints. Fresh migrations assume an existing account table; the bootstrap
refuses nonempty databases. The common production runtime and isolation controls stay
unchanged.

The next clean baseline exposed another ignored input family: the registered
binary and two seed-generator modules used local `deductive-futurist` data.
Commit their bounded input set together; keep optional full interchange-output
fixtures outside this correction.

The management corpus test read ignored Forest-only disturbed matrix output.
Commit the exact small inputs as dedicated fixtures with provenance; passing
on a persistent development checkout does not establish clean CI portability.

Fresh CI exposed transport authentication tests reading Forest account tables,
plus a default lifecycle lock directory outside the unprivileged container
write area. Use fixture-owned account data and the existing lock-directory
setting; no production mounts, credentials, or privileges are needed.

Follow-up measurements separate SQL execute (about 1.7 ms p95) from durable
commit (30–42 ms p95, up to 80 ms). File-sync p95 is 89.47 ms on the PostgreSQL
RAID6 filesystem versus 0.55 ms on Forest SSD. TTL also fails, so the evidence
does not support a READONLY-specific application fix. Local stubtest uncovered
undefined annotations in addition to the unmatched CI runner selector.

The RQ1.16.2 blocking dequeue loop may not observe a suspension flag until
after dequeue. An owned fence was acquired then safely resumed before any
restart; use the already-tested GitOps admission-stop/drain sequence for routing
promotion/recovery instead. No queue/job data was removed. Local-service traffic
needed a narrowly scoped paired TCP8030 policy between the five web/RQ consumers
and WMesque2; unrelated d-Tale access remains denied. Actual master raster shape
is187 rows/161 columns, correcting the earlier width/height interpretation.

The published Kubernetes candidate contains native artifact `c6b746bb...`, but
its startup preflight requires `103f2096...`; direct execution fails and the
soil anisotropy API is absent. The canonical workflow still pins the older
WEPPpyo3 source. Its deployed-to-candidate delta also changes model defaults and
adds saved-state readers, so the deployed `7288e8fe5` image cannot be treated as
an unconditional rollback target. These findings supersede the authentication
blocker and earlier source-only approvals; see the receiving package's
`artifacts/image-delta-review.md` for the independent image-level gate.

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

- Decision (2026-10-16, operator grant): execute M8 from forest over SSH to hpc; retain deployed operations/wmesque-sync.sh and timer/service configuration in open-wepp-org. Reuse the proven hpc writer instead of changing Kubernetes mounts or enabling unrelated scheduler tasks.

- Decision (2026-10-16, operator approval): accept M7 on rollout/recovery,
  latency, baseline and stubtest evidence. Retain isolation findings separately
  and move exhaustive CI to weekly/manual; keep one automatic baseline. This
  supersedes the earlier full-isolation closeout gate without representing a
  failed state scan as passing. Rationale: the original rollout obligations are
  met, while unchanged-order repetitions delay unrelated fixture debugging.

- Decision (2026-10-16, Codex): retain collection-time leak detection and the
  full gate, fix observer lifecycle and native initialization classification,
  and make incomplete execution fail explicitly. Correct the BLC helper under
  ADR-0095 without relaxing diagnostics or adding configuration flags.

- Decision: Make clean CI prerequisites explicit: committed inputs, opt-in unit
  boundary fixtures, generated controllers, existing locked browser dependencies,
  and a disposable schema from current models plus the canonical preferences
  migration for named constraints. Rationale: broad runner probes
  demonstrate dependence on Forest-local state; preserve actual integration
  behavior, assertions, privileges, and thresholds instead of skipping tests.
  Date/Author: 2026-10-15, Codex.

- Decision: Commit the two management corpus fixtures and reference their
  dedicated directory. Rationale: the operator explicitly requires committed
  fixtures, and ignored generated outputs made the test depend on local state.
  Preserve source bytes and assertions. Date/Author: 2026-10-15, Roger/Codex.

- Decision: Preserve synchronous database durability and the existing latency
  threshold; prepare a reversible Forest storage move for operator approval.
  Verify general runner capabilities before changing CI routing; keep the
  dedicated image builder excluded. Rationale: measurements point to storage
  commit cost, and label matching alone does not establish a working runner.
  Date/Author: 2026-10-15, Codex; subsequent operator approval received and migration completed.

- Decision: Recover M7 by reverting only routing while retaining the paired
  current-reader runtime and verified data. Stop admission during the exercise.
  Rationale: Old readers cannot safely consume newly persisted PRISM/EDDE state;
  native pairing and actual model output passed. RQ suspension alone does not
  close dequeue races. Full-runtime regressions need compatible forward repair.
  Date/Author: 2026-10-15, Codex, independently reviewed.

- Decision: Execute the full current-state openwepp upgrade, not a scoped backport.
  Rationale: Roger explicitly accepted the other deploying changes and requested
  matching current state. Correct native packaging and PRISM configuration while
  preserving existing runtime identities and M8 exclusion. The prior scope hold
  is resolved; exact-image/recovery gates are not waived.
  Date/Author: 2026-10-15, Roger/Codex.

- Decision: Hold common-runtime promotion pending operator choice of scoped
  backport or broader runtime upgrade. Remove the unapplied candidate transform.
  Rationale: M7 authority does not authorize unrelated model-default changes;
  the exact-image startup check also fails. Do not weaken that check.
  Date/Author: 2026-10-15, Codex.

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

2026-10-16 final closure: M1–M8 complete. Daily hpc receiver enabled; the unchanged
script and installed units are retained in open-wepp-org PR201 with complete live
receipts and final independent security PASS. No Kubernetes or master changes.
Timer execution, artifact readback and bounded recovery establish acceptance;
general test-isolation maintenance remains a separate backlog. Archive this plan.

Earlier checkpoints below are retained history, superseded by this closeout.

2026-10-16 closeout: M7 accepted; M8 remains pending and disabled. Latest hosted
baseline passes 10,690 tests/329 skips and matching stubtest passes. The 18 general
isolation findings remain open outside this milestone. Future isolation repairs
start with affected-file execution, then periodic exhaustive qualification.
See `artifacts/20261016_m7_closeout.md`; earlier observations below are historical.

2026-10-16: hosted baseline and all five unchanged-order repeats pass. The
remaining per-file gate exposed checker observation/lifecycle defects and a
strict BLC helper mismatch. Focused corrections retain collection leak detection
and diagnostic validation; see `artifacts/20261016_isolation_followup.md` and
the separate 20261016 correctness/security reviews. Full isolation remains open.

Clean-runner follow-up: explicit unit boundaries and CI prerequisites resolve
the discovered failures. The final remaining-group check passes 4,693 tests
(83 skips, 12 subtests); 19 focused database/browser/CSRF tests also pass.
The disposable-schema refusal preserves the logical schema/data hash.
These bounded results do not replace full hosted baseline/isolation acceptance.

Validation follow-up: Forest PostgreSQL now uses the approved SSD-backed named
volume, with matching stopped data/metadata and table counts, unchanged durable
commit settings, restored health, and RAID6 backups. All four unchanged latency
gates pass; READONLY added p95 is 5.81 ms and TTL 4.73 ms. Stubtest passes all
eight modules locally and on hosted runner-02 after the annotation correction.
The isolated CI runtime preserves the dedicated builder boundary and test
thresholds. Fresh-run prerequisites exposed by CI are corrected through explicit
LFS materialization, the existing writable lock-directory setting, and test-owned
account fixtures. Ten transport tests pass on runner-02; all twelve focused
transport/generator tests pass on Forest. Full Forest regression passes 10,872 tests with 126 skips; final hosted
baseline/isolation still needs results. Earlier interrupted isolation runs
are not passes, and no randomized coverage is claimed without the plugin.

Final runtime checkpoint: receiving PR199 at846f0f81 restores healthy admission
after actual local-first/master-only/local-first recovery acceptance. Live sync,
hash/full-raster readback, parity/fallback/revision checks, existing-project reads
with unchanged NoDb hashes, and fresh WEPP/native-Parquet artifacts pass. All33
replicas and18 nodes healthy; RQ15 idle, no fence/suspension, deferred/failure
registries preserved; scheduler dry-run and syncfalse retained. M7 operational
acceptance passes, but full closeout remains open: the unchanged forest baseline
suite failed after10664 passes/126 skips on the READONLY marker-notification
latency test; isolated rerun reproduces123.88ms p95 overhead versus50ms limit.
No unrelated fix or threshold relaxation was attempted; cause remains undiagnosed.
This supersedes in-progress checkpoints below without erasing their history.

Latest checkpoint supersedes the historical holds below: full runtime deployed,
public health restored, live receiver sync and service parity/fallback accepted.
Receiving source PR653 merged; immutable runtime digest is
`sha256:5f46ed689b3d6e604c732ed68ddacde264abc804b852c68a65bb26c519ece9bc`.
The remaining M7 routing recovery exercise is underway with admission drained;
M8 stays disabled. Durable detailed receipts live in open-wepp-org
`docs/work-packages/20261014-wmesque-receiver-canary/artifacts/current-runtime-rollout.md`.
Exact-image65-test suite passes without application/native overlays. The broad
baseline suite is still running on unchanged forest31c6d5d; stubtest CI is queued
because no runner has its requested homelab label, not represented as passed.

M7 remains incomplete after GitHub access restoration. Source publication is
underway, but no live receiving image/routing/geodata promotion occurred.
The image-level review caught a stale native dependency pin before deployment;
focused WMesque tests alone did not establish common-runtime compatibility.

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
