# Lemhi Integration Plan: First-Class Persistent RQ Workers for WEPPcloud

**Status:** Draft planning document  
**Date:** 2026-04-16  
**Audience:** WEPPcloud engineering, I-CREWS leadership, RCDS/Lemhi operations, security/network administrators  
**Purpose:** Define what is required to make Lemhi support first-class persistent WEPPcloud `rq-worker` capacity.

## 1. Problem Statement

This document answers one question:

`What would it take to run WEPPcloud rq-workers on Lemhi as first-class persistent infrastructure, not ad hoc HPC batch jobs?`

The answer is a multi-domain program touching software architecture, DevOps, cluster operations, security, networking, data management, and support ownership.

Decision headline: estimated engineering cost is approximately 9-18x the ~$42k hardware procurement. Baseline schedule is approximately 30-42 weeks (about 7-10 months) through production hardening.

## 2. Baseline Assumptions from Current WEPPcloud Architecture

The current runtime contract is service-oriented:

- Browser -> Caddy -> Flask/rq-engine/query-engine -> Redis -> `rq-worker` pool.
- Worker jobs are long-lived queue consumers, not one-shot compute jobs.
- Worker jobs resolve run data under `/wc1/runs` (with legacy fallback under `/geodata/weppcloud_runs`).
- Worker jobs rely on Redis DBs for queueing, locks, state cache, and status pub/sub.
- Worker paths include external-data acquisition (OpenTopography/WMEsque and climate-related services), not just offline local CPU work.
- Browse and orchestration APIs expose run state and files as first-class service surfaces.

Relevant references:

- [ARCHITECTURE.md](../../../../ARCHITECTURE.md)
- [wepppy/weppcloud/utils/helpers.py](../../../../wepppy/weppcloud/utils/helpers.py)
- [docker/docker-compose.dev.yml](../../../../docker/docker-compose.dev.yml)
- [wepppy/nodb/core/ron.py](../../../../wepppy/nodb/core/ron.py)
- [wepppy/microservices/rq_engine/orchestration_read_routes.py](../../../../wepppy/microservices/rq_engine/orchestration_read_routes.py)
- [wepppy/microservices/browse/browse.py](../../../../wepppy/microservices/browse/browse.py)

## 3. Definition of "First-Class Persistent RQ Workers"

For this effort, "first-class persistent" means all of the following:

1. Worker availability is continuous and scheduler-resilient (automated restart/renewal under Slurm limits).
2. `rq-worker` behavior is contract-compatible with current WEPPcloud queues, locks, and status semantics.
3. Run filesystem contracts are preserved (`/wc1`, `/geodata` compatibility or a transparent equivalent).
4. Security posture is production-grade (no plaintext Redis exposure, managed secrets, auditable access).
5. Network-dependent tasks are either supported safely or explicitly routed elsewhere.
6. Observability and on-call operations are complete (alerts, logs, runbooks, ownership).

## 4. Hard Prerequisites (External Dependencies)

No engineering should start until these are approved in writing.

| ID | Prerequisite | Owner | Why it is hard-gate |
|---|---|---|---|
| P1 | Policy exception or approved pattern for continuously renewed service-like Slurm jobs | Lemhi governance | Persistent workers cannot exist if long-running job renewal is prohibited |
| P2 | Approved non-tunneled private routed connectivity path from Lemhi worker jobs to WEPPcloud Redis endpoint | Lemhi network + UI security | First-class workers must maintain durable direct queue + status/preflight signaling connectivity |
| P3 | Approved secure Redis transport/auth pattern (TLS + ACL + rotation + audit) | Security + network | Uncontrolled cross-boundary Redis connectivity is not acceptable |
| P4 | Storage class approved for WEPP small-file metadata-heavy I/O | Lemhi storage admins | Lustre defaults can be poor fit for this workload |
| P5 | Decision on internet-restricted compute model for external APIs | I-CREWS + RCDS + security | Some task types fail without controlled egress |
| P6 | Named operations owner for 24x7 worker incidents | RCDS + WEPPcloud | No owner means no production service |
| P7 | Written Slurm/cgroup + Linux limits contract for worker jobs (`cpus-per-task`, explicit memory floor by workload profile, cgroup enforcement, `ulimit` profile) | Lemhi ops + security | Slurm default memory and nested worker fanout cannot be sized or stabilized safely without explicit limits |
| P8 | Funded procurement and logistics plan for high-performance 3-2-1 storage (hot run tier + replica + offsite immutable copy) | I-CREWS leadership + RCDS operations | Lustre is non-viable for this workload; no funded 3-2-1 storage means no production-safe Lemhi path |

`P2 + P3` hard requirement clarification:

1. Lemhi must provide a non-tunneled routed path from Slurm compute jobs to the WEPPcloud Redis endpoint that supports mTLS session establishment and long-lived worker/pubsub connections.
2. If that routed mTLS path is not approved and operational, Lemhi cannot be treated as first-class persistent RQ worker infrastructure.
3. In that case, first-class scope stops and only non-first-class fallback models (`B1`) remain in scope.

## 5. Target Reference Architecture

### 5.1 Control Plane (WEPPcloud side)

1. Keep authoritative WEPPcloud orchestration and Redis-backed control plane in WEPPcloud environment.
2. Expose Redis through an approved private routed boundary (no tunnel pattern) with strict source allowlists.
3. Enforce TLS, ACL-scoped principals, credential/certificate rotation, and audit logging for cross-boundary Redis access.
4. Export Redis connectivity health, queue health, and status/preflight stream-health metrics.

### 5.2 Worker Plane (Lemhi side)

1. Add `rq-slurm-supervisor` (service process) that continuously maintains target worker count by submitting/renewing Slurm jobs.
2. Preferred first-class execution path: Lemhi workers connect directly to WEPPcloud Redis over approved private routed TLS connectivity (no SSH/stunnel).
3. If direct secure Redis connectivity cannot be approved, downgrade to a non-first-class brokered dispatch model instead of presenting Lemhi workers as first-class RQ workers.
4. Worker process writes run data to approved mounted path that preserves WEPP path contract.

### 5.3 Storage Plane

1. Provide path-compatible mount strategy for `/wc1` and `/geodata` equivalents.
2. Add node-local scratch staging for hot intermediate files.
3. Implement async flush/promote policy for scratch -> persistent storage.
4. Define inode, quota, cleanup, retention, and backup policy for run artifacts.
5. Implement explicit 3-2-1 data durability:
   - Copy 1: high-performance primary run tier for active workload
   - Copy 2: replicated secondary copy on separate storage node/media class
   - Copy 3: offsite immutable backup copy with defined retention and restore tests

### 5.4 Connectivity for External Data Calls

Choose one model and document as policy:

1. Allowlisted egress proxy for required endpoints only.
2. Pre-staged data model with no runtime internet calls from worker jobs.
3. Hybrid queue model where internet-dependent tasks run on non-Lemhi workers and pure compute tasks run on Lemhi.

Recommended default for any near-term attempt: option 3 (hybrid routing). It is the only model that can plausibly deliver value without first completing a full network and storage redesign.

## 6. Blocker Resolution Plan

### 6.1 Blocker A: No internet access on compute nodes

Required actions:

1. Inventory all network-dependent worker paths and classify them as `required`, `optional`, or `reroutable`.
2. Decide policy path:
   - `A1`: controlled egress
   - `A2`: data pre-stage
   - `A3`: hybrid task routing
3. Implement queue-level routing so tasks that require network do not fail silently on Lemhi workers.
4. Add hard-fail guardrails and explicit error payloads when blocked tasks are invoked on the wrong queue profile.

Exit criteria:

1. Zero unknown outbound calls from Lemhi worker jobs.
2. All blocked call sites produce deterministic errors with remediation hints.
3. Required workflows still complete end-to-end under selected model.

### 6.2 Blocker B: SSH tunnel is non-viable; first-class workers require secure direct Redis connectivity

Required actions:

0. Treat `P2/P3` as hard gates, not soft risks:
   - no routed mTLS path from Lemhi Slurm jobs to WEPPcloud Redis means no first-class Lemhi worker program.
1. Adopt non-tunneled private routed Redis connectivity as the primary first-class pattern:
   - Lemhi compute nodes establish direct TLS Redis sessions to WEPPcloud Redis endpoint.
   - No SSH/stunnel bridge layer is permitted.
2. Implement secure Redis communication controls:
   - TLS required for all cross-boundary Redis traffic
   - ACL-scoped principals by service role (`rq-worker`, `rq-engine`, telemetry services)
   - short-lived credentials/certs with defined rotation and revocation workflows
   - audited auth failures and access attempts
3. Validate first-class Redis contract coverage required by WEPPcloud:
   - distributed lock + run metadata semantics
   - status/log pub/sub semantics for live telemetry
   - RQ queue/job semantics for worker execution
   - cache/session/log-level control paths required by existing contracts
4. Enforce status/preflight viability controls:
   - Lemhi-originated worker messages must flow to status streaming channels with no translation layer
   - preflight checklist/lock visibility must remain real-time under load
   - connection keepalive/idle timeout/NAT settings must support long-lived pub/sub + queue worker sessions
5. Explicitly consider and reject SSH tunnel/stunnel patterns for production Redis connectivity:
   - no `ssh -L/-R/-D`, `autossh`, or `stunnel` persistent control-plane channels
   - no bastion-mediated Redis exposure as production architecture
6. If direct secure Redis connectivity cannot be approved, either:
   - downgrade to non-first-class brokered dispatch, or
   - stop the first-class Lemhi worker effort.

Exit criteria:

1. Lemhi workers successfully consume/publish over direct TLS Redis connectivity with ACL enforcement and audit coverage.
2. Status streaming and preflight checklist behavior remain contract-correct for Lemhi-originated activity under pilot load.
3. SSH/stunnel tunnel options are explicitly documented as considered and rejected for production.
4. Redis-route outage, credential-rotation, and recovery drills surface alerts within SLA windows.

#### 6.2.1 Downstream implications for status2/preflight2 viability (no SSH tunnel)

No SSH tunnel means there is no ad hoc transport fallback for telemetry paths; viability is binary on approved direct secure Redis communication.

1. `status2` viability implication:
   - `status2` streams Redis pub/sub run channels.
   - If Lemhi workers cannot publish to Redis status channels over the approved direct path, WebSocket sessions stay connected but receive stale/no updates.
2. `preflight2` viability implication:
   - `preflight2` depends on Redis-backed checklist/lock state changes and notifications.
   - If direct Redis writes/notifications from Lemhi-side activity do not propagate, checklist state drifts stale and readiness UX becomes unreliable.
3. Operational implication:
   - Without direct secure Redis path, Lemhi cannot be considered first-class for RQ workers, status streaming, or preflight streaming.
4. Required monitoring:
   - Alert on channel silence, notification lag, reconnect storms, and auth/ACL denies on the Lemhi Redis route.

### 6.3 Blocker C: Slurm scheduler model versus persistent workers

Required actions:

1. Build `rq-slurm-supervisor` with desired worker cardinality by queue (`default`, `batch`, etc.).
2. Add lease/heartbeat model so supervisor can distinguish stalled versus healthy jobs.
3. Handle preemption/time-limit events with graceful drain and requeue behavior.
4. Add surge controls to avoid queue storms during mass restart.

Exit criteria:

1. Worker pool self-heals after cancellations, preemption, or node loss.
2. No manual babysitting required for normal scheduler churn.

#### 6.3.1 Assurance requirement: active jobs must not be stopped by scheduler policy

If the requirement is "persistent workers are not stopped while running active jobs," the following controls are mandatory:

1. Written scheduler policy guarantee:
   - dedicated worker partition or dedicated nodes for WEPPcloud
   - no preemption for that partition/QOS
   - no oversubscription/co-tenancy
   - no time-limit expiry during active work (`MaxTime` policy compatible with long-lived workers)
2. Maintenance/operations guarantee:
   - planned maintenance uses drain-first workflow, not immediate cancellation
   - node reboot/patch only after active jobs complete
   - advance notice and change-control window for planned outages
3. Worker lifecycle controls:
   - worker drain mode (stop taking new jobs, finish current job, then exit)
   - supervisor honors drain signals and never hard-kills active jobs during normal operations
4. Explicit limits of assurance:
   - this can prevent scheduler-initiated interruption
   - this cannot prevent unplanned host failure, emergency security shutdown, or power/network events
5. Required resilience despite policy:
   - long-running tasks must support restart/recovery semantics
   - operational runbooks must define post-failure recovery of interrupted jobs

#### 6.3.2 Deployment lifecycle control for graceful worker stop/start

Persistent Lemhi workers require a formal deployment lifecycle controller so software updates do not interrupt active jobs.

Required controls:

1. Pre-deploy admission control:
   - place target workers into `drain` mode before deployment
   - block new job pickup on draining workers
2. Graceful stop sequence:
   - wait for current active job to finish or hit an explicit max-drain timeout
   - if timeout is exceeded, mark the job for controlled recovery path (never silent kill)
3. Rolling deployment orchestration:
   - update workers in bounded batches (for example canary then rolling wave)
   - enforce minimum healthy capacity per queue during rollout
4. Start and readiness gating:
   - new worker must pass Redis/auth contract checks, storage mount checks, and queue-heartbeat checks before accepting jobs
   - failed readiness must auto-remove worker from service
5. Rollback controls:
   - one-command rollback to previous worker image/runtime profile
   - rollback honors same graceful drain semantics
6. Auditability:
   - every lifecycle action (drain/start/stop/promote/rollback) logged with operator identity and timestamp
   - deployment events correlated to queue lag and job failure metrics

Exit criteria:

1. Repeated upgrade tests complete with zero active-job interruption from deployment actions.
2. Rollback tested and successful under load.
3. No manual SSH intervention required for normal rollouts.

#### 6.3.3 CPU allocation and `ulimit` contract (currently not documented in this repo)

Current known facts from public C3+3 docs:

1. Standard Lemhi nodes are documented as 40 cores and 192 GB RAM.
2. Slurm default memory allocation is documented as 3 GB per job unless explicitly requested otherwise.
3. WEPP watershed executable footprint is approximately 12 GB memory for a single watershed process before adding Python worker overhead, process/thread fanout overhead, and OS headroom.

Known unknowns for WEPPcloud persistent-worker viability:

1. Partition/QOS-specific CPU policy for service-like jobs (effective `--cpus-per-task`, oversubscription, and preemption interactions).
2. Slurm cgroup enforcement details for CPU, memory, and process limits.
3. Runtime Linux `ulimit` profile on compute jobs (`nofile`, `nproc`, `stack`, `memlock`, `core`).

Required actions:

1. Obtain written scheduler/runtime contract from Lemhi ops for target partition(s).
2. Capture live job limits from compute nodes during pilot jobs:
   - `ulimit -a`
   - `cat /proc/self/limits`
   - `nproc`
   - cgroup CPU/memory quotas for the running job
3. Define WEPP concurrency budget aligned to those limits:
   - map `rq worker-pool -n`
   - map nested `ThreadPoolExecutor`/`ProcessPoolExecutor` fanout
   - map `WEPPPY_NCPU` and `PERIDOT_CPU`
   - define per-job memory minimums that account for the ~12 GB watershed executable footprint plus orchestration/runtime headroom
4. Enforce startup guardrails:
   - worker startup fails fast if observed limits are below required profile
   - submission templates require explicit `--cpus-per-task` and memory requests (`--mem` or `--mem-per-cpu`), never Slurm defaults

Exit criteria:

1. Signed CPU/limits contract exists for all partitions/QOS used by Lemhi workers.
2. Soak tests show no FD exhaustion, PID exhaustion, or cgroup throttle/kill events under representative load.
3. Worker throughput and failure rate are stable across repeated runs.
4. No cgroup OOM kills occur for representative watershed workloads under approved queue profiles.

### 6.4 Blocker D: Filesystem and small-file I/O mismatch

#### 6.4.1 WEPP FORTRAN workload: concrete file I/O profile

WEPPcloud does not run a single binary that reads one input and writes one output. It orchestrates the USDA WEPP FORTRAN executable — a legacy scientific model that operates on per-hillslope and per-channel input/output file sets. Understanding the file I/O profile is essential to evaluating Lustre fitness.

**Per hillslope (parallelized across all hillslopes in a watershed):**

| Direction | Files | Patterns |
|-----------|-------|----------|
| Input | 4 | `pN.slp` (slope profile), `pN.sol` (soil), `pN.man` (management/landuse), `pN.cli` (climate symlink) |
| Output | 6 | `HN.pass.dat`, `HN.wat.dat`, `HN.ebe.dat`, `HN.element.dat`, `HN.loss.dat`, `HN.soil.dat` |

That is **10 files per hillslope**, every one a small text file (kilobytes to low megabytes). The FORTRAN binary reads input files, performs daily water-balance and erosion calculations, and writes fixed-width text output — six separate report files per hillslope, not one consolidated output.

**Per watershed (sequential, after all hillslopes complete):**

| Direction | Files | Patterns |
|-----------|-------|----------|
| Input | 4-5 | `pw0.slp`, `pw0.sol`, `pw0.man`, `pw0.cli`, optional `network.txt` |
| Output | 7 | `chan.out`, `chanwb.out`, `chnwb.txt`, `pass_pw0.txt`, `ebe_pw0.txt`, `soil_pw0.txt`, `loss_pw0.txt` |

**Post-processing (interchange):** After WEPP execution, all hillslope and watershed text outputs are parsed and converted to ~21 consolidated Parquet files with metadata manifests.

**Additionally:** Conditional feature files (`frost.txt`, `phosphorus.txt`, `gwcoeff.txt`, `snow.txt`, `firedate.txt`, `pmetpara.txt`) are written per-run depending on active feature flags.

#### 6.4.2 St. Joe basin: file count at scale

The St. Joe basin contains **134,033 hillslopes** across 56 tributary watersheds. A single full-basin WEPP run produces:

| Component | Calculation | Files |
|-----------|-------------|-------|
| Hillslope input | 134,033 x 4 | 536,132 |
| Hillslope output | 134,033 x 6 | 804,198 |
| Watershed I/O | 56 x ~12 | ~672 |
| Interchange/metadata | 56 x ~21 | ~1,176 |
| **Total per single run** | | **~1,342,178** |

**One full-basin run creates approximately 1.34 million small files.**

Calibration requires iterative full-basin runs — each parameter adjustment requires re-running all 134,033 hillslopes to evaluate watershed-scale effects. A modest calibration campaign of 50 iterations produces ~67 million files. Alternative-futures scenario modeling (multiple management treatments x multiple climate regimes x 56 tributary watersheds) produces hundreds of runs and hundreds of millions of files.

Every one of these files is a small text file. The largest (multi-year daily output) may reach single-digit megabytes. Most are kilobytes. This is the pathological workload that every Lustre deployment guide warns against.

#### 6.4.3 Why this workload destroys Lustre performance

Lustre is a parallel filesystem optimized for large sequential I/O — reading and writing multi-gigabyte files across striped object storage targets. Its metadata server (MDS) is a single point of serialization for file creation, `stat`, `open`, `close`, and `unlink` operations.

WEPPcloud's WEPP workload is the inverse: millions of small-file creates, reads, and writes, each requiring a metadata server round-trip. Concurrent hillslope workers issuing parallel file creates hammer the MDS. The procurement request already benchmarked this pattern against NFS: small-file writes on production NFS were 8.1x slower than local filesystem. Lustre metadata performance under contention is typically worse than NFS for this access pattern, because the MDS must also coordinate with Object Storage Servers for each new file.

Published Lustre best practices from multiple HPC centers confirm this:

1. INCD: accessing small files on Lustre is "very inefficient"; recommended minimum file size is 1 GB. WEPPcloud files are 3-6 orders of magnitude smaller than the recommended minimum.
2. UMBC: scripts that continuously check for file presence can generate 5,000+ stat requests per second, creating persistent MDS pressure. NoDb lock-check-mutate-dump cycles produce exactly this pattern.
3. UMBC: writing thousands of files to a single directory can overload Lustre metadata servers and take filesystems offline. A single watershed run writes thousands of files to `wepp/output/`.

Lemhi's 1.3 PB Lustre filesystem is shared across all cluster users. Sustained small-file pressure from WEPPcloud workers would degrade metadata performance for every other Lemhi user — an unacceptable externality on shared infrastructure.

Required actions:

1. Benchmark representative WEPP run patterns on candidate storage tiers.
2. Add local scratch for high-churn small files and configurable promote policy.
3. Validate lock semantics and path safety under shared filesystem behavior.
4. Establish cleanup and archival processes to avoid inode exhaustion.
5. Explicitly validate read/write latency impacts from direct Redis RTT (or broker/API RTT only if `B1` fallback is selected) and filesystem metadata latency together; both affect end-to-end worker throughput.

Exit criteria:

1. Throughput is within acceptable envelope against WEPPcloud baseline.
2. No data integrity regressions under concurrent worker pressure.

#### 6.4.4 Mandatory high-performance 3-2-1 storage procurement and integration

Lustre non-viability means a separate high-performance 3-2-1 storage program is mandatory for any production-safe Lemhi path.

Procurement cost anchors from `docs/projects/i-crews/st_joe/procurement-request.md`:

1. SuperServer 621P-TR (fully configured): `$21,391.50` per server.
2. Two-server total: `$42,783.00`.

Required 3-2-1 architecture (minimum practical baseline):

1. Copy 1 (primary): high-performance run tier for active WEPP small-file I/O.
2. Copy 2 (secondary): replicated copy on separate node/media class with snapshot/promotion controls.
3. Copy 3 (backup): offsite immutable backup copy with tested restore path.

Costed implementation scenarios:

| Scenario | Storage design | Procurement CAPEX | Integration labor | Logistics/non-labor | Delivery delta |
|---|---|---:|---:|---:|---|
| S-321A (recommended baseline) | Two high-performance storage servers (`$21,391.50 x 2`) + institutional offsite immutable backup service | $42,783.00 | 3-6 PM ($45k-$132k) | $8k-$18k | +6 to +12 weeks |
| S-321B (fully self-hosted copy-3) | S-321A plus one additional server for dedicated backup tier (`$21,391.50 x 3`) | $64,174.50 | 4-8 PM ($60k-$176k) | $12k-$24k | +8 to +16 weeks |

Logistics scope includes shipping/receiving, rack/power/network turn-up, rails/cabling/transceivers, datacenter installation windows, and acceptance burn-in.

Critical-path dependency note:

1. If storage procurement decision, purchase order issuance, and installation window are not locked by end of Phase 0 Week 5, the baseline schedule assumes Phase 2 filesystem adaptation and Phase 3 pilot will slip.
2. In that state, near-term Path A must either absorb schedule delay or reduce scope until storage readiness is available.

Exit criteria:

1. 3 copies are verified for each run artifact class with documented retention policy.
2. Copy 3 is immutable/offsite and restore drills pass within agreed RTO/RPO.
3. Storage throughput and metadata performance meet WEPP baseline acceptance thresholds under representative load.
4. Procurement, logistics, and ownership runbooks are signed by operations owners before pilot expansion.

### 6.5 Blocker E: Shared filesystem contract between Lemhi workers and WEPPcloud services

Problem statement:

Workers write run artifacts under `/wc1/runs`, and WEPPcloud services (Flask, rq-engine, browse) read the same run trees. A mere "path-compatible mount" on Lemhi is insufficient unless both sides see coherent, timely, two-way state.

Required actions:

1. Select and approve one cross-environment data architecture:
   - shared two-way mounted filesystem with coherent metadata semantics
   - staged replication pipeline (for example rsync/promote model)
   - object-store-backed refactor of run artifact access
2. Define consistency model and freshness SLOs for run artifacts.
3. Validate browse/rq-engine reads against actively mutating Lemhi-produced runs.
4. Validate failure behavior for partial sync, delayed sync, and stale reads.

Exit criteria:

1. WEPPcloud service tier sees Lemhi-produced run state within agreed freshness SLO.
2. Browse, export, and pipeline/readiness routes remain contract-correct for Lemhi-backed runs.
3. No silent divergence between worker-visible and service-visible run trees.

### 6.6 Blocker F: Docker-coupled worker tasks (for example `weppcloudr`)

Problem statement:

Some worker paths shell into Docker-managed sidecars (for example report rendering). Shared HPC compute nodes usually do not provide user Docker daemon access.

Required actions:

1. Inventory Docker-coupled tasks and classify as `rewrite`, `reroute`, or `disable_on_lemhi`.
2. For each `rewrite` task, implement an HPC-compatible runtime path (Apptainer-native execution or service-side offload).
3. For each `reroute` task, enforce queue routing so those jobs stay on WEPPcloud-hosted workers.
4. Add explicit error contracts when a Docker-coupled task is submitted to Lemhi-capable queues without compatibility support.

Exit criteria:

1. No Lemhi worker path assumes a local Docker daemon.
2. Report/export contracts remain functional via rewrite or reroute path.
3. Task routing prevents accidental execution in unsupported runtime contexts.

## 7. Workstreams and Deliverables

### 7.1 DevOps Workstream

Deliverables:

1. Reproducible worker runtime build pipeline (OCI + Apptainer-compatible).
2. Signed artifact publication and rollbackable release channels.
3. Slurm job templates and `rq-slurm-supervisor` deployment automation.
4. Environment profile management for Lemhi queues.
5. CI smoke tests for worker bootstrap and direct secure Redis handshake.

### 7.2 Software Engineering Workstream

Deliverables:

1. Queue profile support (`local`, `lemhi`, `hybrid`) across enqueue paths.
2. Task classification and routing for network-dependent operations.
3. Worker startup health probes and capability flags (internet-enabled vs offline).
4. Refactor or gate container-coupled paths (for example Docker-dependent report tasks).
5. Enhanced failure contracts for blocked/misrouted tasks.

Likely touch points:

- `wepppy/microservices/rq_engine/*`
- `wepppy/rq/*`
- `wepppy/nodb/core/ron.py`
- `wepppy/weppcloud/utils/helpers.py`

### 7.3 System Administration Workstream

Deliverables:

1. Service accounts, group permissions, and least-privilege model.
2. Storage provisioning, quota policy, and mount contracts.
3. Firewall/routing/ACL rules for direct Redis connectivity from Lemhi worker nodes and telemetry surfaces.
4. PKI/certificate lifecycle for mTLS.
5. Incident runbooks and escalation matrix.

### 7.4 Security Workstream

Deliverables:

1. Threat model and control mapping for direct Redis boundary, secrets, and identity controls.
2. Credential rotation and revocation procedures.
3. Audit logging requirements and retention policy.
4. Penetration test or focused red-team review of the Redis boundary and telemetry signaling paths.

### 7.5 Operations/SRE Workstream

Deliverables:

1. SLOs/SLIs for worker availability, queue lag, and job completion latency.
2. Alerting, dashboards, and paging thresholds.
3. Failure drills: Redis route outage, auth/ACL rotation fault, status/preflight signaling lag, storage outage, preemption storm.
4. On-call ownership and handoff documentation.

## 8. Required Software Backlog (Concrete)

| Area | Required change | Reason |
|---|---|---|
| Queue routing | Add queue execution profiles and task capability routing | Prevent internet-required tasks from failing on offline workers |
| Worker bootstrap | Add Lemhi bootstrap mode with direct Redis TLS/ACL contract checks | Ensure deterministic secure startup |
| Redis connectivity integration | Add non-tunneled private-route Redis profile, ACL principals, and connection policy checks | Enable first-class workers without SSH tunnel patterns |
| Task contracts | Add explicit errors for disallowed task contexts | Avoid hidden partial failures |
| Path resolution | Parameterize or map run roots while preserving `/wc1` contracts | Maintain compatibility with `get_wd` assumptions |
| Docker-coupled tasks | Replace or route around Docker CLI dependencies in HPC jobs | Docker daemon assumptions do not hold on shared HPC compute nodes |
| Runtime limit guards | Add startup checks for CPU/cgroup/`ulimit` contract compliance | Prevent unstable fanout due to unknown scheduler/runtime limits |
| Observability | Add worker/Redis/status/preflight stream health metrics and structured events | Operability and incident response |

### 8.1 Software Backlog Accounting (Included in Baseline)

Accounting assumptions:

1. Baseline program envelope from Sections 10-11 is `25-35 PM`.
2. Phase-duration allocation for software-heavy phases:
   - Phase 1 (8 weeks): `5.0-7.0 PM`
   - Phase 2 (12 weeks): `7.5-10.5 PM`
3. Section 8 rows map to Section 16.2/16.3 execution units; mapped PM rows overlap and are not additive.

| Backlog item | Mapped execution units | Included in baseline | PM range | Timeline window |
|---|---|---|---:|---|
| Queue routing | E2-1 + S2-01..S2-05 | Yes | 2.3-3.2 | Jul 27-Sep 25, 2026 |
| Worker bootstrap | Phase 1 guardrails + S2-09 + S2-13 | Yes | 1.8-2.5 | Jun 22-Sep 11, 2026 |
| Redis connectivity integration | Phase 1 Redis boundary hardening + E2-4 | Yes | 3.3-4.6 | Jun 8-Sep 18, 2026 |
| Task contracts | S2-08 + S2-12 | Yes | 0.7-1.0 | Aug 24-Sep 18, 2026 |
| Path resolution | E2-3 (S2-09..S2-12) | Yes | 1.8-2.5 | Aug 31-Sep 18, 2026 |
| Docker-coupled tasks | E2-2 (S2-06..S2-08) | Yes | 1.0-1.4 | Jul 27-Sep 4, 2026 |
| Runtime limit guards | Phase 1 guardrails | Yes | 0.9-1.3 | Jun 22-Jul 3, 2026 |
| Observability | Phase 1 integration/drills + S2-05 + S2-15 | Yes | 1.6-2.3 | Jul 6-Sep 25, 2026 |

Software-core subtotal (phase allocation basis, not row-sum): `12.5-17.5 PM` in baseline scope.

### 8.2 Software Backlog Addendum (Currently Under-Accounted)

The following software work is required for reliable delivery but is not explicitly PM-accounted in the current baseline narrative:

| Addendum software item | Why needed | Additional PM | Suggested window |
|---|---|---:|---|
| Deployment lifecycle controller implementation (`drain/start/rollback`) | Required by Section 6.3.2 controls | 1.2-1.8 | Phase 1 W5-W8 + Phase 3 prep |
| CI/CD and supply-chain controls for Redis boundary/supervisor artifacts (signing/SBOM/vuln gates) | New boundary services need release hardening | 0.8-1.2 | Phase 1 W2-W8 |
| Enqueue-site classification backfill ledger + owner sign-off | Prevents long-tail unclassified routing drift | 0.6-0.9 | Phase 2 W1-W6 |
| Canonical hard-error contract conformance test pack | Needed for unsupported profile/filesystem contract paths | 0.7-1.0 | Phase 2 W6-W10 |
| Capacity/performance harness (routing/reconciliation/churn) | Repeated evidence needed for gate decisions | 0.8-1.1 | Phase 2 W8-W11 |
| Dashboards and runbooks as code for new metrics/events | Operational readiness for new control plane | 0.7-1.0 | Phase 2 W8-W12 |

Addendum software delta if fully scoped separately: `+4.8-7.0 PM` and approximately `+6-12 weeks` elapsed (with partial parallelization).

## 9. Program Phases, Timeline, and Gate Reviews

Estimated duration assumes prerequisites are approved quickly.

| Phase | Duration | Primary owners | Exit gate |
|---|---|---|---|
| Phase 0: Preconditions | 4-6 weeks | Governance + security + network + Lemhi ops | P1-P8 signed off |
| Phase 1: Platform plumbing | 6-8 weeks | DevOps + sysadmin | Direct secure Redis path, runtime, and supervisor MVP works in non-prod |
| Phase 2: Software adaptation | 10-14 weeks | SWE + DevOps | Queue routing and blocker guardrails merged and tested |
| Phase 3: Pilot operations | 6-8 weeks | SRE + SWE + Lemhi ops | Sustained pilot with defined SLO pass |
| Phase 4: Production hardening | 4-6 weeks | SRE + security + platform | Runbooks, alerts, drills, and rollback plan approved |

Total: approximately 7-10 months under active cross-team staffing.

Detailed execution specs with explicit decisions, weekly milestones, gate criteria, and complexity scoring are provided in Section 16.

Accounting note: this baseline timeline is the same baseline scope used for the `25-35 PM` labor envelope and includes the Section 8 software backlog plus Section 16 phase execution work.
Staffing assumption note: the `30-42 week` baseline and `26-36 week` pilot-ready path assume approximately `3.4-4.0` concurrent FTE from the role mix in Section 10.

## 10. Staffing Model (Minimum Practical Team)

| Role | FTE | Notes |
|---|---|---|
| Senior SWE / architecture lead | 0.8-1.0 | Queue/task contract refactor and integration decisions |
| DevOps/platform engineer | 1.0 | Runtime packaging, CI/CD, supervisor, deployment |
| Lemhi systems engineer | 0.5 | Scheduler/storage/network integration |
| Security/network engineer | 0.3-0.5 | Redis-boundary controls, PKI, firewall, audit |
| SRE/operations engineer | 0.5 | SLOs, dashboards, alerts, runbooks, drills |
| QA/integration engineer | 0.3-0.5 | End-to-end validation and regression coverage |

Estimated effort: roughly 25-35 person-months.

## 11. Cost Envelope (Order-of-Magnitude)

Using typical fully-loaded engineering rates, 25-35 person-months yields an approximate labor envelope of:

- Low range: 25 x $15,000 = $375,000
- Mid range: 30 x $18,000 = $540,000
- High range: 35 x $22,000 = $770,000

This excludes opportunity cost from diverted WEPPcloud roadmap and support work.

### 11.1 Cost/Timeline Accounting Coverage (Included vs Additional)

| Bucket | Scope | Timeline | PM | Labor cost | Primary dependency gates | Included in baseline `25-35 PM`? |
|---|---|---|---:|---:|---|---|
| Baseline program | Path A Phases 0-4, including Section 8 software backlog and Section 16 phase execution | 30-42 weeks | 25-35 | $375k-$770k | `P1-P8` signed; `P2/P3` routed mTLS path approved/operational by Phase 1 gate | Yes |
| Routed mTLS connectivity package | Section 11.4 `P2/P3` network/security/PKI work package | 4-7 weeks (partially parallel) | 2.6-4.4 | $39k-$96.8k | Lemhi network/security approval, routed path provisioning, PKI availability | Yes (within baseline/`B4`) |
| Conditional adders | Section 17.10 triggered scope (`P1` denial path, direct-Redis denial fallback, `D3/E3` acceleration, PII controls, `F3` acceleration) | Trigger-dependent | +3 to +18 each trigger | +$45k-$396k each trigger | Specific trigger condition realized in execution | No |
| Long-term modernization | Section 18 post-Path-A program (`A4 + B4 + C1 + D3 + E3 + F3`) | +9-15 months | +20-30 delta from Path A stabilization | +$300k-$660k delta | Path A stabilized; sustained `P2/P3`; long-term `C1/D3/E3/F3` approvals/funding | No |
| Software addendum under-accounted work | Section 8.2 items | +6-12 weeks (partially parallel) | +4.8-7.0 | +$72k-$154k | Phase 1-2 staffing availability and CI/CD ownership in place | No (currently implicit/partial) |
| Mandatory 3-2-1 storage program | Section 6.4.4 S-321A/S-321B storage procurement and integration path | +6 to +16 weeks | +3 to +8 (partially overlapping with D/E) | +$45k-$176k labor | `P8` funding + procurement/logistics windows + operations ownership | No (CAPEX/logistics are additional cash spend) |

### 11.2 Under-Accounted Non-Software Items

These items are partially represented in workstream text but not explicitly line-itemed in baseline PM/time math.

| Non-software item | Additional timeline | Additional PM | Additional labor cost | Notes |
|---|---:|---:|---:|---|
| Program management + cross-org governance cadence | +2 to +6 weeks | +4 to +8 | +$60k-$176k | No explicit PM role in staffing table |
| CAB/change-management/release coordination overhead | +2 to +6 weeks | +1 to +3 | +$15k-$66k | Required by lifecycle controls but not line-itemed |
| External security assessment + remediation buffer | +4 to +10 weeks | +2 to +5 | +$30k-$110k | Vendor scheduling/remediation often dominate |
| Compliance evidence package (non-PII baseline) | +4 to +12 weeks | +2 to +6 | +$30k-$132k | PII trigger exists; baseline compliance packaging still under-scoped |
| 24x7 ops readiness ramp (training/shadow/backfill) | +4 to +8 weeks | +3 to +7 | +$45k-$154k | Ownership is required, ramp is not explicitly costed |
| Post-cutover hypercare stabilization | +4 to +8 weeks | +2 to +4 | +$30k-$88k | No dedicated hypercare phase currently |
| Observability/SIEM retention run-rate implementation overhead | +2 to +6 weeks | +1 to +3 | +$15k-$66k | Labor only; tool OPEX excluded from labor totals |
| PKI/secrets lifecycle operations overhead | +2 to +8 weeks | +1 to +2.5 | +$15k-$55k | Tooling/service costs are separate OPEX |
| Procurement/vendor lead-time management overhead | +6 to +20 weeks | +0.5 to +2 | +$7.5k-$44k | Lead time can affect critical path even when labor is low |
| Hybrid cloud run-rate planning and capacity management | +1 to +3 weeks | +0.5 to +2 | +$7.5k-$44k | Recurring cloud OPEX excluded from labor totals |

Important: Section 11.2 rows are risk adders and not fully additive with each other.

### 11.3 Mandatory 3-2-1 Storage CAPEX and Logistics (Lustre replacement path)

This section captures required non-labor storage cash exposure using the procurement-request hardware estimate (`$21,391.50` per server).

| Scenario | Server basis | Hardware CAPEX | Logistics/non-labor | Total non-labor spend | Notes |
|---|---|---:|---:|---:|---|
| S-321A (recommended baseline) | 2 servers (`$21,391.50 x 2`) | $42,783.00 | $8k-$18k | $50,783-$60,783 | Copy 3 provided by institutional offsite immutable backup service |
| S-321B (self-hosted copy-3) | 3 servers (`$21,391.50 x 3`) | $64,174.50 | $12k-$24k | $76,174.50-$88,174.50 | Dedicated third server for backup tier |

Combined first-year cash exposure for Path A (labor + storage non-labor):

1. Path A labor: `$375k-$770k`.
2. Path A + S-321A storage non-labor: `$425,783-$830,783` (plus offsite backup service OPEX).
3. Path A + S-321B storage non-labor: `$451,174.50-$858,174.50`.

### 11.4 Routed mTLS Connectivity Work Package (`P2/P3`) Budget and Timeline

This is the explicit estimate for Lemhi-provided routed mTLS connectivity from Slurm compute jobs to WEPPcloud Redis.

| Work item | Timeline (weeks) | PM | Labor cost | Notes |
|---|---:|---:|---:|---|
| Network/routing/security design + approvals | 1-2 | 0.6-1.0 | $9k-$22k | ACL boundaries, route domains, failure domains |
| Firewall/allowlist and routed-path implementation | 1-2 | 0.5-0.9 | $7.5k-$19.8k | Non-tunneled path from Lemhi compute to Redis TLS endpoint |
| PKI and mTLS credential lifecycle implementation | 1-2 | 0.8-1.3 | $12k-$28.6k | Issuance, rotation, revocation, service principal mapping |
| Validation and failure drills | 1-2 | 0.7-1.2 | $10.5k-$26.4k | Auth-rotation, route outage, reconnect behavior, telemetry viability |
| **Total (`P2/P3`)** | **4-7 elapsed (partially parallel)** | **2.6-4.4** | **$39k-$96.8k** | Hard requirement for first-class designation |

Planning note:

1. This `P2/P3` work package is included in baseline program estimates and within `B4` scope; it is not additive unless schedule slips force sequential execution.
2. If `P2/P3` is delayed or denied, first-class Lemhi scope cannot proceed.

### 11.5 Budget Dependency Matrix and Re-Baseline Rules

| Dependency state | Budget implication | Timeline implication | Program action |
|---|---|---|---|
| `P1-P8` signed and `P2/P3` operational by Phase 1 gate | Keep Path A baseline (`$375k-$770k` labor) plus selected storage non-labor scenario | Keep baseline `30-42 weeks` | Proceed as first-class path (`A3 + B4 + C4 + D1/D2 + E2 + F1`) |
| `P2/P3` delayed or denied | First-class budget model is invalid; apply Section 17.10 direct-Redis denial fallback delta (`+3-6 PM`, `+$45k-$132k`) and re-scope | Add `+4-8 weeks` and re-sequence dependent Phase 1/2 work | Drop first-class designation; re-baseline to fallback-only (`B1`) or stop |
| `P7` limits contract unresolved (memory/CPU defaults retained) | Capacity assumptions in baseline are invalid; add guardrail and profile work before scale-up | Add `+2-6 weeks` to complete limits contract and load validation | Hold scale-out until explicit `--mem/--cpus-per-task` profile is approved; no reliance on Slurm default 3 GB/job |
| `P8` not funded/approved, or PO/ETA/install window not locked by Phase 0 Week 5 | Storage-backed production budget is invalid until resolved | Add procurement/logistics delay (`+6-20 weeks` typical lead-time range in Section 11.2) and re-sequence Phase 2/3 storage-dependent work | Stop production path or approve alternate funded copy-3 path (`S-321B`) |
| `P1` denied (no persistent-like Slurm policy) | Add Section 17.10 `P1` denial delta (`+6-10 PM`, `+$90k-$220k`) for recovery-SLA architecture shift | Add `+8-16 weeks` | Re-baseline from non-interruption model to recovery model (`C2/C3`) |
| Multiple dependency failures occur together | Additive estimate is unreliable; row-level sums will understate integration overhead | Schedule compression assumptions become invalid | Run full re-estimation and publish a new baseline envelope before continuing |

## 12. Validation and Acceptance Criteria

A Lemhi worker deployment should not be considered first-class until all criteria pass:

1. 30-day pilot with automated worker self-healing and no manual daily intervention.
2. Direct secure Redis connectivity survives auth rotation, node churn, and scheduler preemption.
3. Status and preflight streaming surfaces remain viable for Lemhi-originated work (no silent telemetry gaps).
4. End-to-end run workflows pass with deterministic behavior and contract-compliant errors.
5. Storage integrity checks pass under concurrent high-volume run load.
6. Security review signs off on direct Redis boundary, secret handling, and audit trails.
7. On-call team accepts ownership with documented runbooks and escalation paths.

## 13. Risks and Stop Conditions

High risks:

1. Policy denial of persistent-like scheduler usage model.
2. Inability to approve secure non-tunneled direct Redis connectivity pattern.
3. Small-file metadata performance on shared storage remains unacceptable.
4. Understaffed cross-team ownership leads to unstable operations.

Stop conditions:

1. If P1-P8 are not approved by end of Phase 0, stop project.
2. If pilot cannot achieve minimum availability/latency envelope, stop productionization.
3. If security controls cannot meet institutional requirements, stop deployment.
4. If routed mTLS connectivity (`P2/P3`) is not approved and operational by the Phase 1 integration gate, stop first-class scope and explicitly re-baseline as fallback-only.

## 14. Practical Decision Framing

This plan describes what is required to make Lemhi support first-class persistent WEPPcloud workers. It is not a zero-cost reuse path.

The effort is a separate infrastructure program with explicit staffing, policy exceptions, and substantial lead time. If those conditions are not funded and owned, Lemhi should not be treated as a substitute for dedicated WEPPcloud-aligned servers for near-term St. Joe delivery.

## 15. Prior Art and Industry Evidence

This section addresses a question the planning process should not have to re-litigate: *has anyone succeeded at running persistent, externally-connected task-queue workers on a shared HPC cluster?*

The answer from the research record is unambiguous: **no**. No HPC center publishes guidance recommending it. Every HPC center that has encountered the need for persistent services has built separate infrastructure. Every attempted production pattern of this kind is documented as broken, abandoned, or replaced by an alternative architecture. The plan above is therefore not cautious — it is aligned with the consensus of the HPC operations community.

Readers should weigh this evidence before entering Phase 0.

### 15.1 HPC Centers Explicitly Recommend Against This Pattern

1. **Sulis HPC (UK national Tier 2)** — published Celery-on-Slurm guidance explicitly states: *"Celery is based on network technologies that are common in the web server space, not the HPC space so it is not recommended for use on Sulis."* Sulis recommends GNU Parallel or Dask as HPC-native alternatives.
   - Reference: <https://sulis-hpc.github.io/advanced/ensemble/celery.html>

2. **NCAR Derecho (NSF)** — use policies terminate resource-intensive processes on login nodes and restrict compute nodes to batch/interactive jobs. Persistent service daemons would violate use policies.
   - Reference: <https://ncar-hpc-docs.readthedocs.io/en/latest/compute-systems/derecho/derecho-use-policies/>

3. **Multiple university HPC acceptable use policies** (Case Western, Alabama, Hofstra, NC State, Utah CHPC) prohibit non-batch workloads on login nodes, restrict compute nodes to time-limited jobs, and explicitly scope HPC to research workloads — not production web-service backends.
   - References:
     - <https://case.edu/utech/departments/research-computing-and-infrastructure-services/resources/acceptable-use-policy-high-performance-computing-hpc-cluster>
     - <https://hpc.ua.edu/current-services/acceptable-use-policy/>
     - <https://www.chpc.utah.edu/documentation/policies/2.1GeneralHPCClusterPolicies.php>

### 15.2 Major HPC Centers Built Separate Infrastructure Instead

Every major US research-computing center that encountered the persistent-service problem solved it by standing up dedicated infrastructure — not by bending their HPC to accommodate service workloads.

1. **NERSC (DOE)** built **Spin**, a separate Kubernetes-based platform for science gateways, databases, API endpoints, and workflow managers. NERSC explicitly states it is "not a web hosting service" and provides only 8x5 support for Spin services. Persistent WEPPcloud-like workloads run on Spin, not on Perlmutter compute nodes.
   - Reference: <https://docs.nersc.gov/services/spin/>
   - Reference: <https://docs.nersc.gov/services/science-gateways/>

2. **University of Virginia Research Computing** maintains a separate clustered Kubernetes environment with 1,000+ cores and ~1 TB RAM specifically for persistent containerized services (web servers, Shiny apps, APIs, databases). Architecturally distinct from their HPC batch cluster.
   - Reference: <https://www.rc.virginia.edu/userinfo/microservices/>

3. **NSF Jetstream2** (via ACCESS) was created specifically because traditional HPC cannot run persistent services. Its documentation states: *"Jetstream2 is not a traditional High Performance Computing (HPC) or High Throughput Computing (HTC) environment."* It exists as a user-friendly cloud environment "designed to allow 'always on' research infrastructure." Many science gateways already run there.
   - Reference: <https://docs.jetstream-cloud.org/overview/overview-doc/>

The implication is direct: the national-scale research-computing community has already made the capital and engineering investment to build Kubernetes-based platforms for persistent services, because HPC clusters cannot host them reliably. Lemhi is an HPC cluster. It does not have an equivalent persistent-service overlay, and building one is exactly the separate infrastructure program this plan describes.

### 15.3 Attempts to Run Task Queues on HPC Are Documented as Broken

1. **Charliecloud (LANL) Issue #230** — extensive community thread on running non-MPI worker daemons on Slurm concludes that Slurm fundamentally kills background daemons by design: *"it kills the worker as soon as it goes into the background"* and *"clears up any processes from that job left around once that job exits."* Documented workarounds (pdsh, GNU Parallel, backgrounded mpirun) are all described as inadequate. The repository was archived in 2025 with the issue unresolved.
   - Reference: <https://github.com/hpc/charliecloud/issues/230>

2. **Apache Airflow on HPC** — multiple attempts documented with the same failure modes: compute nodes cannot run persistent webserver or broker; autoscaling fails under HPC MFA requirements; Airflow has no built-in mechanism to scale workers up/down on HPC; when Airflow fails, Slurm jobs keep running but Airflow loses tracking and marks them failed. All known working deployments use a hybrid pattern with centralized services running *external* to the HPC cluster.
   - Reference: <https://avik-datta-15.medium.com/how-to-setup-apache-airflow-on-hpc-cluster-ea2575764b43>
   - Reference: <https://github.com/apache/airflow/discussions/24076>

3. **Singularity + Celery + RabbitMQ (Lawrence Berkeley Lab, 2017)** — public mailing-list discussion of running Celery workers in Singularity on HPC. Participants documented networking limitations of container runtimes, inability to maintain persistent TCP connections to external queues, and lack of container orchestration. The discussion ended without a working solution.
   - Reference: <https://groups.google.com/a/lbl.gov/g/singularity/c/OWyJSyWjm-I>

The pattern is consistent: attempted; documented; abandoned; replaced with either a hybrid architecture or a dedicated platform.

### 15.4 Lustre Small-File Performance Is Well-Documented

The WEPP FORTRAN I/O profile in Section 6.4 is the worst possible workload for Lustre. Published best-practices from independent HPC centers converge on the same guidance:

1. **INCD Lustre Best Practices**: *"Accessing small files on the Lustre filesystem is very inefficient."* Recommended minimum file size: 1 GB. *"Writing thousands of files to a single directory produces massive load on Lustre metadata servers, often resulting in taking filesystems offline."*
   - Reference: <https://wiki.incd.pt/books/filesystem-user-guide/page/lustre-best-practices>

2. **UMBC HPCF Lustre Best Practices**: *"Accessing small files on the Lustre filesystem is not efficient. Scripts that continuously check for file presence can generate 5,000+ stat requests per second."* NoDb's lock-check-mutate-dump cycle produces this load.
   - Reference: <https://hpcf.umbc.edu/general-productivity/lustre-best-practices/>

3. **University of Bonn HPC Wiki** and **NCAR GLADE Lustre documentation** — same guidance: avoid small files; avoid metadata-heavy operations; Lustre is tuned for large sequential I/O.
   - References:
     - <https://wiki.hpc.uni-bonn.de/marvin/lustre-best-practices>
     - <https://ncar-hpc-docs.readthedocs.io/en/latest/storage-systems/glade/lustre/>

4. **Academic literature**: published performance analysis confirms Lustre's metadata bottleneck under small-block-size access.
   - Reference: <https://www.researchgate.net/publication/323607172_Performance_Of_Small_Block_Size_Accesses_In_Lustre_File_System>

The St. Joe basin workload (~1.34 million small files per full-basin run, tens of millions per calibration campaign, hundreds of millions for scenario analysis) is categorically the wrong workload for Lemhi's 1.3 PB Lustre filesystem.

### 15.5 Security Precedent: HPC SSH Tunnels Have Been Weaponized

Security posture conclusion for this plan:

1. Persistent SSH/stunnel cross-boundary control-plane channels are a **NO-GO** for production.
2. Viable first-class path is non-tunneled direct secure Redis connectivity (TLS/ACL/rotation/audit); brokered API dispatch is fallback only when first-class designation is dropped.

Evidence and rationale:

1. **Protocol tunneling is a recognized adversary technique** (ATT&CK T1572, command-and-control tactic), including SSH-based tunnels and proxy chaining.
   - Reference: <https://attack.mitre.org/techniques/T1572/>

2. **Recent CISA/FBI/CNMF incident guidance** documents threat actors using encrypted SSH tunnels for command-and-control and data movement.
   - Reference: <https://www.cisa.gov/sites/default/files/2023-09/aa23-250a.pdf>

3. **NIST firewall guidance** warns that tunneled/encrypted traffic can bypass boundary inspection/policy if not terminated and governed correctly.
   - Reference: <https://doi.org/10.6028/NIST.SP.800-41r1>

4. **NIST SSH key-management guidance** highlights unmanaged SSH trust relationships as a pivot and persistence risk when lifecycle governance is weak.
   - Reference: <https://doi.org/10.6028/NIST.IR.7966>

5. **OpenSSH server documentation** explicitly notes forwarding controls are not a complete security boundary if shell access exists.
   - Reference: <https://man.openbsd.org/sshd_config>

6. **Zero Trust guidance** requires per-session/per-request identity and authorization controls rather than implicit trust by network location or static tunnel adjacency.
   - Reference: <https://doi.org/10.6028/NIST.SP.800-207>

7. **Real vulnerability pressure on SSH endpoints** (for example CVE-2024-6387) reinforces that long-lived exposed tunnel endpoints are high-value targets.
   - Reference: <https://nvd.nist.gov/vuln/detail/CVE-2024-6387>

Explicit architectural decision:

1. `ssh -L/-R/-D`, `autossh`, and `stunnel` were considered for Section 6.2 and rejected for production.
2. Section 6.2 therefore requires a non-tunneled direct secure Redis model for first-class workers; brokered dispatch remains a non-first-class fallback.

### 15.6 Direct Database Connections Across HPC Perimeters Are Generally Prohibited

While direct secure Redis (Option B4) is the only acceptable first-class architectural pattern once SSH tunneling is rejected, obtaining firewall exceptions for direct database access (e.g., TCP 6379) across HPC perimeter boundaries is historically very contentious. Institutional security and network administrators frequently deny these requests by policy.

1. **Default-Deny HPC Perimeters**: Most research and university HPC clusters place compute nodes on strictly private, unroutable subnets with default-deny egress policies. While API polling (HTTPS 443) via a NAT gateway might be permitted, arbitrary stateful TCP protocols are intentionally blocked. The industry standard **ESnet Science DMZ** architecture explicitly separates external data-facing nodes from general-purpose compute to aggressively control perimeter risk.
   - Reference: <https://fasterdata.es.net/science-dmz/>

2. **Databases Are Targeted Assets**: Redis, even when wrapped in mTLS and ACLs, is a raw database protocol. Security teams are deeply reluctant to open firewall holes for distributed databases crossing institutional boundaries due to the history of database-targeting ransomware and data exfiltration.
   - Reference: CISA alerts regularly highlight threat actors targeting exposed databases and message brokers: <https://www.cisa.gov/news-events/cybersecurity-advisories/aa22-011a>

3. **L7 Inspection Limitations**: In zero-trust networks, establishing a direct, non-HTTP stateful persistent connection between an external WEPPcloud environment and an internal Lemhi compute node violates least-privilege network segmentation. Brokered HTTPS API dispatch (Option B1) is the standard way to cross these security domains precisely because web application firewalls (WAFs) and Layer-7 gateways can inspect and terminate HTTPS API requests, whereas raw Redis TCP streams cannot be transparently inspected.

This friction reinforces why Option B4 is classified as a high-risk institutional dependency in Phase 0. If institutional security denies the direct Redis route, the project is forced back to Option B1 (brokered dispatch), which permanently drops the "first-class worker" designation and requires rewriting the task-dispatch architecture.

### 15.7 Industry Has Moved Toward Ephemeral Workers, Not Persistent Ones

Even on cloud infrastructure (where persistent workers are architecturally supported), industry guidance has moved away from the persistent-worker model. AWS's recommended pattern for Celery on batch compute is *ephemeral* workers that scale to zero when the queue is empty — not persistent long-lived daemons.

- Reference: <https://aws.amazon.com/blogs/hpc/run-celery-workers-for-compute-intensive-tasks-with-aws-batch/>
- Reference: <https://github.com/aws-samples/aws-batch-celery-worker-example>

The Lemhi proposal moves in the opposite direction: it tries to force persistent workers onto infrastructure that is *even less* suited to them than cloud batch services, while the cloud community has already abandoned the persistent pattern where it *is* supported.

### 15.8 The Architectures That Do Work on HPC

For completeness: there are patterns that *do* work for dispatching compute to HPC from web applications. None of them preserve WEPPcloud's current architecture.

1. **Globus Compute (formerly funcX)** — function-as-a-service model where a cloud-hosted broker dispatches tasks to HPC endpoints that dynamically provision Slurm jobs. Web app → cloud broker → HPC batch jobs. Adopting this would require rewriting WEPPcloud's task dispatch layer.
   - Reference: <https://funcx.org/globus-compute.html>
   - Reference: <https://access-ci.atlassian.net/wiki/spaces/ACCESSdocumentation/pages/552828929/Globus+Compute+on+ACCESS>

2. **Slurm REST API (slurmrestd)** — a web application can submit batch jobs to Slurm via REST without running persistent workers on HPC. Again, requires re-architecting from RQ workers to Slurm batch jobs.
   - Reference: <https://aws.amazon.com/blogs/hpc/using-the-slurm-rest-api-to-integrate-with-distributed-architectures-on-aws/>

3. **Dask-jobqueue** — HPC-native pattern where a Dask scheduler dynamically submits and manages Slurm jobs. Designed for batch analytics, not for a web application task queue serving interactive users. The Dask-jobqueue documentation itself notes: *"Running Celery on HPC environment is usually very tricky whereas spawning a Dask Cluster is a lot easier."*
   - Reference: <https://jobqueue.dask.org/>

All three patterns require re-architecting WEPPcloud to submit batch jobs rather than feed persistent workers. None of them is a drop-in reuse of existing code. Each is its own multi-month engineering program, equivalent in cost to the Lemhi RQ-worker effort this plan describes — and still does not solve the shared-filesystem or internet-access problems.

### 15.9 Synthesis: What the Evidence Demands

The consensus is unanimous across three independent axes:

1. HPC operations community: this is not what HPC is for. Sulis, NERSC, NCAR, UVA, Jetstream2, and ACCESS have collectively put millions of dollars and years of engineering into building separate platforms precisely because HPC cannot host persistent services.
2. Published engineering record: documented attempts (Charliecloud, Airflow, Singularity+Celery+RabbitMQ) all failed or were replaced with hybrid architectures.
3. Lustre and security best practices: the specific workload (small files, persistent outbound tunnels, always-on daemons) is the pathological case that published guidance, federal standards, and real-world incidents explicitly warn against.

If the I-CREWS governance review chooses to proceed with the Lemhi path despite this evidence, the plan above is the minimum-viable engineering program. If the review chooses not to re-derive what the HPC community has already established, procurement of dedicated WEPPcloud-aligned servers is the correct path.

There is no documented third option that is fast, cheap, and safe.

## 16. Detailed Phase Execution Specs

Planning baseline in this section:

1. Assumes kickoff on Monday, April 20, 2026.
2. Uses a baseline 40-week program:
   - Phase 0: 6 weeks
   - Phase 1: 8 weeks
   - Phase 2: 12 weeks (with 2-week contingency to reach 14)
   - Phase 3: 8 weeks
   - Phase 4: 6 weeks
3. This section is the conservative reference schedule (40-42 weeks with contingency), which sits in the upper half of the Section 9 `30-42 week` baseline envelope.

### 16.1 Phase 0: Preconditions (6 Weeks, Apr 20-May 29, 2026)

#### Objective

Convert `P1-P8` into signed operating contracts so engineering starts only after governance/security/network/storage/operations decisions are explicit.

#### Scope boundaries

In scope:

1. Governance, security, network, scheduler, storage, and operations decisions required for `P1-P8`.
2. Written contracts for Slurm/cgroup/`ulimit`, secure direct Redis boundary pattern, and run-path/storage model.
3. Phase 1 readiness packet with approved non-production deployment constraints.

Out of scope:

1. Building fallback broker dispatch stack or `rq-slurm-supervisor`.
2. Queue-routing code changes and task rewrites (Phase 2+).
3. Production cutover or pilot operations.

#### Explicit decisions and deadlines

| Decision ID | Decision | Owner (accountable) | Deadline |
|---|---|---|---|
| D0-1 / P1 | Approve service-like persistent Slurm job pattern (or deny) | Lemhi governance lead | End of Week 2 (May 1, 2026) |
| D0-2 / P7 | Approve written Slurm/cgroup/`ulimit` runtime limits contract | Lemhi ops lead | End of Week 2 (May 1, 2026) |
| D0-3 / P2 | Approve non-tunneled private routed path from Lemhi workers to WEPPcloud Redis | Lemhi network lead | End of Week 3 (May 8, 2026) |
| D0-4 / P3 | Approve secure Redis boundary pattern (TLS + ACL + rotation + audit) | Security architect | End of Week 3 (May 8, 2026) |
| D0-5 / P4 | Approve storage class and path compatibility approach for `/wc1` and `/geodata` contract | Storage admin lead | End of Week 4 (May 15, 2026) |
| D0-6 / P5 | Select internet-restricted operating policy (default target: `hybrid`) | I-CREWS sponsor + RCDS ops + security | End of Week 4 (May 15, 2026) |
| D0-7 / P6 | Assign 24x7 incident ownership and escalation chain | RCDS operations manager | End of Week 5 (May 22, 2026) |
| D0-8 / P8 | Approve funded 3-2-1 storage procurement/integration path (`S-321A` or `S-321B`) and lock PO/ETA/install window | I-CREWS sponsor + RCDS operations manager | End of Week 5 (May 22, 2026) |
| D0-9 | Approve Phase 1 non-production guardrails and go/no-go | Joint gate board | End of Week 6 (May 29, 2026) |

#### Weekly plan

| Week | Dates | Tasks | Deliverables |
|---|---|---|---|
| W1 | Apr 20-24 | Kickoff, owner assignment, `P1-P8` evidence template, decision calendar | Decision register template, RACI, meeting cadence |
| W2 | Apr 27-May 1 | Resolve `P1` + `P7` policy and limits discovery plan | Signed/denied `P1`, draft `P7` limits contract |
| W3 | May 4-8 | Resolve `P2` + `P3` network/Redis security boundary | Network and security decision records |
| W4 | May 11-15 | Resolve `P4` + `P5` storage contract and hybrid policy | Storage contract memo, hybrid policy memo |
| W5 | May 18-22 | Resolve `P6` operations ownership and `P8` storage funding/procurement decision | Ops ownership charter, escalation matrix, funded storage decision record, PO/ETA/install window record |
| W6 | May 25-29 | Gate review and publish signed precondition packet | Phase 0 gate packet, Phase 1 go/no-go record |

#### Acceptance criteria

1. All `P1-P8` are signed with explicit constraints and owners.
2. `hybrid` policy defines task boundaries (`lemhi-safe` vs rerouted).
3. Non-production security/network/storage controls are approved for Phase 1 start.
4. `P8` includes explicit PO issuance status, vendor ETA, and installation/acceptance windows.

#### Complexity (1-5)

| Major task | Score | Rationale |
|---|---|---|
| `P1` persistent Slurm policy decision | 4 | Cross-organization governance with operational risk |
| `P7` scheduler/cgroup/`ulimit` contract | 4 | Requires policy plus empirical runtime verification |
| `P8` funded 3-2-1 storage plan | 5 | Hard funding/logistics dependency for non-Lustre path |
| `P2` + `P3` secure connectivity decisions | 5 | Security-critical multi-team network boundary |
| `P4` storage/path contract | 4 | High correctness and performance impact |
| `P5` hybrid policy boundary | 3 | Policy-heavy but implementation deferred |
| `P6` operations ownership model | 3 | Organizational alignment and escalation design |

### 16.2 Phase 1: Platform Plumbing (8 Weeks, Jun 1-Jul 24, 2026)

#### Objective

Deliver non-production platform plumbing (secure direct Redis boundary profile, `rq-slurm-supervisor`, startup guardrails, telemetry viability checks) that is contract-aligned and operationally testable.

#### Scope boundaries

In scope:

1. Direct Redis boundary MVP with TLS/ACL auth policy, route controls, and metrics.
2. `rq-slurm-supervisor` MVP with desired worker cardinality, heartbeat, and restart controls.
3. Worker startup guardrails (limits, mounts, Redis/auth readiness).
4. Status2/preflight2 signaling viability tests under Lemhi-originated activity.
5. Non-production failure drills for Redis-route outage, auth rotation, and scheduler churn.

Out of scope:

1. Full enqueue-surface routing refactor (Phase 2).
2. Docker-coupled task rewrites (Phase 2+).
3. Production pilot/hardening activities (Phases 3-4).

#### Explicit decisions and deadlines

| Decision ID | Decision | Owner | Deadline |
|---|---|---|---|
| D1-1 | Final direct-Redis network placement/failover topology | DevOps lead + network lead | End of Week 1 (Jun 5, 2026) |
| D1-2 | Cert/credential issuance and rotation workflow for Redis clients | Security lead | End of Week 2 (Jun 12, 2026) |
| D1-3 | Worker runtime packaging standard (OCI -> Apptainer profile) | DevOps lead + Lemhi ops lead | End of Week 3 (Jun 19, 2026) |
| D1-4 | Supervisor lease/heartbeat/drain thresholds | SWE lead + SRE lead | End of Week 4 (Jun 26, 2026) |
| D1-5 | MVP queue profile boundary for hybrid non-production tests | SWE lead + product owner | End of Week 5 (Jul 3, 2026) |
| D1-6 | Phase 1 exit-gate evidence checklist | Joint gate board | End of Week 6 (Jul 10, 2026) |

#### Weekly plan

| Week | Dates | Tasks | Deliverables |
|---|---|---|---|
| W1 | Jun 1-5 | Finalize topology and metrics/event schema | Topology diagram, deployment skeleton |
| W2 | Jun 8-12 | Implement direct Redis TLS/ACL boundary profile and policy | Redis boundary config, health endpoints |
| W3 | Jun 15-19 | Validate queue/lock/status/preflight contract coverage over direct Redis route | Contract coverage test evidence |
| W4 | Jun 22-26 | Add worker guardrails for limits/mount/Redis-auth | Startup checks, Slurm templates |
| W5 | Jun 29-Jul 3 | Implement `rq-slurm-supervisor` MVP | Supervisor service and lease model |
| W6 | Jul 6-10 | End-to-end non-production integration under hybrid model | Integration report and handshake evidence |
| W7 | Jul 13-17 | Failure drills (Redis-route outage/auth rotation/preemption/restart storm) | Drill reports and control updates |
| W8 | Jul 20-24 | Gate review and Phase 2 handoff | Phase 1 gate packet and risk register |

#### Acceptance criteria

1. Direct Redis boundary enforces TLS, authenticated clients, and ACL-limited access.
2. Supervisor restores target worker count after cancellation/preemption in non-production.
3. Worker startup fails fast when limits/mount/Redis-auth contracts are violated.
4. Phase 1 worker profiles use explicit Slurm memory requests that account for the ~12 GB watershed executable footprint plus runtime headroom (no 3 GB default reliance).
5. Status2/preflight2 show Lemhi-originated updates with no contract regressions.
6. Failure drills demonstrate deterministic recovery with observable metrics.

#### Complexity (1-5)

| Major task | Score | Rationale |
|---|---|---|
| Direct Redis boundary hardening | 5 | Security boundary + observability + correctness |
| Redis contract-coverage validation | 4 | Cross-service correctness under scheduler churn |
| Worker startup guardrails | 4 | Cross-layer contract checks |
| `rq-slurm-supervisor` control loop | 5 | Desired-state reliability under churn |
| End-to-end integration and drills | 4 | Multi-component coupling |

### 16.3 Phase 2: Software Adaptation (Baseline 12 Weeks, Jul 27-Oct 16, 2026)

#### Objective

Implement contract-safe hybrid execution so Lemhi workers run only HPC-compatible tasks while WEPPcloud-hosted workers keep internet-dependent and Docker-coupled workloads.

#### Entry criteria

1. Phase 1 direct-Redis/runtime/supervisor plumbing is operational in non-production.
2. `P1-P8` remain approved and unchanged.
3. Filesystem architecture is selected and documented.

#### Queue-routing design decisions

| ID | Decision | Rationale | Consequence |
|---|---|---|---|
| QD-1 | Use logical execution profiles (`cloud_service`, `lemhi_compute`) | Avoid hardcoded queue names in handlers | Central routing policy becomes required |
| QD-2 | Preserve `default`/`batch`, add profile-resolved targets (`lemhi_default`, `lemhi_batch`) | Backward compatibility | Worker fleets must advertise supported queues |
| QD-3 | Capability tags (`needs_network`, `needs_docker`, `cpu_only`, `shared_fs_strict`) | Prevent incompatible routing | Every enqueue site needs explicit classification |
| QD-4 | Unclassified tasks route to `cloud_service` initially; CI blocks new unclassified after Week 6 | Safe migration without silent failures | Temporary cloud skew accepted |
| QD-5 | Unsupported profile/runtime returns canonical hard error payload | Contract clarity | Replaces hangs/ambiguous failures |

#### Epic-level backlog and complexity

| Epic | Description | Owners | Complexity | Notes |
|---|---|---|---|---|
| E2-1 | Profile-based routing substrate | SWE lead + SWE | 5 | Cross-cutting enqueue refactor |
| E2-2 | Docker-coupled task strategy | SWE + DevOps | 3 | Reroute-first policy |
| E2-3 | Filesystem contract adaptation | SWE + Lemhi sysadmin | 4 | Preserve `/wc1` compatibility |
| E2-4 | Redis boundary and telemetry contract hardening | DevOps + SWE + security | 4 | ACL/TLS, pub/sub, and checklist signaling resilience |
| E2-5 | Validation/rollout/gates | QA + SRE + SWE | 3 | Broad test and readiness burden |

#### Story backlog (execution units)

| Story ID | Story | Deliverable | Dependencies | Complexity |
|---|---|---|---|---|
| S2-01 | Define capability taxonomy/profile schema | Typed config and taxonomy doc | None | 2 |
| S2-02 | Implement central routing resolver | `resolve_queue(profile, capability, task)` | S2-01 | 4 |
| S2-03 | Integrate resolver into rq-engine enqueue sites | Route handlers call resolver | S2-02 | 5 |
| S2-04 | Integrate resolver into pipeline enqueue sites | Pipeline jobs classified/routed | S2-02 | 5 |
| S2-05 | Add routing telemetry + CI guard | Metric + gate for unclassified tasks | S2-03, S2-04 | 3 |
| S2-06 | Inventory Docker-coupled tasks | Tagged `needs_docker` list | S2-01 | 2 |
| S2-07 | Reroute `weppcloudr` tasks to cloud profile | No Lemhi routing for Docker tasks | S2-06 | 3 |
| S2-08 | Add explicit unsupported-runtime errors | Canonical contract errors | S2-07 | 3 |
| S2-09 | Worker filesystem preflight | `/wc1/runs` mount + write checks | None | 4 |
| S2-10 | Run-root adapter preserving `get_wd` contract | Explicit mapping logic | S2-09 | 4 |
| S2-11 | Freshness guard for Lemhi-produced artifacts | Prevent stale browse/export reads | S2-10 | 4 |
| S2-12 | Filesystem violation hard errors | `filesystem_contract_violation` path | S2-11 | 3 |
| S2-13 | Redis route preflight and auth validation | TLS/auth/ACL reachability checks | None | 3 |
| S2-14 | Retry/timeout/keepalive budgets for Redis flows | Bounded failure behavior for queue + pub/sub | S2-13 | 4 |
| S2-15 | Redis/status/preflight observability hardening | Metrics and alert thresholds | S2-14 | 3 |
| S2-16 | Routing/contract regression suite | Targeted tests | S2-03..S2-15 | 3 |
| S2-17 | Canary rollout with mixed worker pools | Controlled rollout evidence | S2-16 | 3 |
| S2-18 | Failure drills + rollback rehearsal | Verified rollback under load | S2-17 | 4 |

#### Weekly milestones (baseline 12 weeks)

| Week | Milestone | Exit evidence |
|---|---|---|
| 1 | Finalize capability taxonomy + routing ADRs | Approved `QD-1..QD-5` |
| 2 | Resolver skeleton behind feature flag | Resolver tests passing |
| 3 | rq-engine enqueue migration | Core routes use resolver |
| 4 | Pipeline enqueue migration | Batch/pipeline paths classified |
| 5 | Docker reroute complete | Docker tasks forced to cloud profile |
| 6 | Filesystem preflight + contract errors merged | Lemhi startup fail-fast active |
| 7 | Redis preflight + retry budgets | Queue/pubsub checks passing |
| 8 | Routing/Redis/status/preflight observability | Dashboards + alert thresholds |
| 9 | Full targeted regressions stable | Required validation commands pass |
| 10 | Canary rollout with small Lemhi slice | No critical regressions under load |
| 11 | Soak + chaos drills + rollback rehearsal | Drill reports closed |
| 12 | Final acceptance review | Gates G1-G4 pass |

Contingency:

1. Weeks 13-14 reserved only for residual defects/hardening.

#### Acceptance gates

| Gate | When | Required conditions |
|---|---|---|
| G1 Design freeze | End Week 2 | ADRs approved; no routing contract ambiguity |
| G2 Functional completeness | End Week 6 | Routing + Docker strategy + filesystem preflight complete |
| G3 Contract/integration | End Week 9 | Test suite + queue graph + stub checks pass |
| G4 Operational readiness | End Week 12 | Canary/soak/drills pass; rollback rehearsal successful |

#### Rollback criteria and actions

Rollback triggers:

1. Persistent misrouting above threshold for two consecutive business days.
2. Redis-route/telemetry failure rates above agreed baseline.
3. Lock/pubsub latency causing repeatable failures or starvation.
4. Filesystem freshness/consistency violations in browse/export/readiness.
5. Security control regression in Redis/auth path.

Rollback actions:

1. Set default execution profile to `cloud_service` and disable Lemhi routing feature flag.
2. Drain `lemhi_*` queues and stop Lemhi worker intake.
3. Keep in-flight cloud jobs running unless safety requires interruption.
4. Revalidate baseline with targeted tests and `wctl check-rq-graph`.
5. Open incident record with root cause, blast radius, and re-entry checklist.

### 16.4 Phase 3: Pilot Operations (8 Weeks, Oct 19-Dec 11, 2026)

#### Objective

Prove Lemhi persistent workers can run bounded production-adjacent workloads with stable SLOs, deterministic failure behavior, and accepted operations ownership.

#### Pilot design

| Pilot element | Execution detail | Required gate |
|---|---|---|
| Scope | Only `lemhi-eligible` jobs (no runtime internet, no Docker-coupled paths, storage contract validated) | Task classification sign-off by SWE + SRE leads |
| Control group | Run matched workload on current WEPPcloud workers | Baseline metrics frozen at pilot start |
| Traffic policy | Ramp eligible-job share 0% -> 5% -> 10% -> 15% -> 20% | Pause/reduce ramp on SLO misses |
| Worker capacity | Start with 2 canaries, then +2/week to max 8 if healthy | Weekly go/no-go review |
| Routing contract | Tag `execution_profile=lemhi-pilot`; ineligible tasks hard-routed away | Zero silent fallback |
| Data integrity | Validate `/wc1/runs` visibility/freshness from browse/rq-engine daily | No silent divergence |

#### Soak and chaos scenarios

| Scenario | Week | Pass criteria | Abort threshold |
|---|---|---|---|
| 72-hour steady soak | 3 | Stable queue and success ratio | Queue lag > 15 min for 30 min |
| 7-day mixed soak | 5 | Stable throughput without babysitting | More than 2 Sev2 incidents/week |
| Redis route outage drill | 4 | Fail-closed routing + bounded retry/recovery behavior | Unbounded queue growth > 30 min |
| Status/preflight event lag drill | 4 | Deterministic eventual state reconciliation after delayed events | Reconciliation lag > 15 min or terminal-state mismatch > 0.5% |
| Slurm preemption storm | 6 | Supervisor replaces workers and drains safely | Recovery > 20 min or job loss |
| Storage latency spike | 6 | Alerts fire and no corrupt outputs | Any output integrity failure |
| Cert rotation drill | 7 | Successful reconnect without manual SSH | Unplanned downtime > 10 min |
| Misroute guardrail test | 8 | Deterministic contract error | Silent run or partial output |

#### SLO targets and abort thresholds

| SLI | Target | Abort threshold |
|---|---|---|
| Worker availability | `>= 99.0%` weekly | `< 97.5%` weekly |
| Queue pickup latency | `p95 <= 90s`, `p99 <= 180s` | `p95 > 180s` for 2 hours |
| Job success ratio (`lemhi-eligible`) | `>= 97.0%` weekly | `< 95.0%` weekly |
| Recovery after worker loss | `<= 10 min` | `> 20 min` |
| Artifact freshness | `p95 <= 5 min` | `p95 > 15 min` |
| Lock/state error rate | `< 0.5%` | `>= 1.0%` for 30 min |

#### Phase 3 complexity (1-5)

| Dimension | Score | Rationale |
|---|---|---|
| Cross-team coordination | 5 | Weekly synchronous decisions across SWE/SRE/ops/security |
| Technical uncertainty | 4 | Scheduler, Redis boundary, and storage behavior still partly unknown |
| Operational blast radius | 4 | Pilot impacts production-adjacent queues |
| Verification burden | 5 | Continuous SLO monitoring and repeated chaos drills |
| Compliance/security dependency | 4 | mTLS/ACL/audit evidence required before expansion |

### 16.5 Phase 4: Production Hardening (6 Weeks, Dec 14, 2026-Jan 22, 2027)

#### Objective

Convert pilot capability into production-ready service with durable ownership, strict change controls, and full compliance evidence.

#### Hardening design

| Hardening element | Execution detail | Required gate |
|---|---|---|
| Traffic expansion | Increase eligible routing cap 25% -> 40% -> 60% -> 75% -> 80% max | Weekly CAB-style review with SRE + security |
| Availability architecture | Maintain minimum healthy worker floor; no rollout wave removes >25% capacity | Capacity policy documented and alert-backed |
| Deployment lifecycle | Mandatory drain/start/readiness/rollback for worker updates | Two successful rolling updates under load |
| Incident discipline | Full incident command with postmortem action tracking | All Sev2+ incidents reviewed |
| Ownership transfer | Runbook acceptance and on-call transition | Ops manager sign-off |

#### Hardening drills

| Scenario | Week | Pass criteria | Stop condition |
|---|---|---|---|
| 14-day production soak | 2-4 | SLOs hold without chronic manual intervention | More than 3 Sev2 in 7 days |
| Rolling update under load | 3 | Zero active-job interruption | Any uncontrolled active-job termination |
| Full rollback drill | 4 | Restore service within rollback SLO | Rollback > 20 min |
| Node-loss fault injection | 5 | Recover capacity floor within 15 min | Recovery > 30 min |
| Security response drill | 5 | Cert revocation/rotation works live | Unauthorized session remains active |
| Audit traceability drill | 6 | Complete actor/timestamp/event chain | Missing critical audit links |

#### Production SLO thresholds

| SLI | Target | Reject threshold |
|---|---|---|
| Worker availability | `>= 99.5%` monthly | `< 99.0%` |
| Queue pickup latency | `p95 <= 60s`, `p99 <= 120s` | `p95 > 120s` for 2 hours |
| Job success ratio (`lemhi-eligible`) | `>= 98.5%` monthly | `< 97.0%` |
| Recovery after worker/node loss | `<= 15 min` | `> 30 min` |
| Artifact freshness | `p95 <= 3 min` | `p95 > 10 min` |
| MTTR (Sev2+) | `<= 30 min` median | `> 60 min` median |

#### Phase 4 complexity (1-5)

| Dimension | Score | Rationale |
|---|---|---|
| Cross-team coordination | 4 | Approval-heavy but fewer unknowns than pilot |
| Technical uncertainty | 3 | Core architecture proven; resilience tuning remains |
| Operational blast radius | 5 | Now directly production-impacting |
| Verification burden | 4 | Long soak + deployment/rollback drills + audit checks |
| Compliance/security dependency | 5 | Production declaration depends on complete evidence |

### 16.6 Cross-Phase Complexity and Governance Summary

#### Phase complexity totals

| Phase | Complexity summary | Interpretation |
|---|---|---|
| Phase 0 | High governance complexity (policy + ownership) | Organizationally hard; low code churn |
| Phase 1 | High platform complexity | Security/control-plane heavy implementation |
| Phase 2 | High software adaptation complexity | Broad enqueue/task contract refactor |
| Phase 3 | 22/25 | High-risk pilot validation period |
| Phase 4 | 21/25 | High-risk production hardening and acceptance |

#### Governance guardrails for entire program

1. No phase starts without prior phase gate sign-off.
2. No implicit fallback for unsupported runtime paths; fail explicitly with contract errors.
3. No production declaration without on-call ownership acceptance and security evidence.
4. If stop conditions trigger, revert to WEPPcloud-hosted workers and treat Lemhi work as paused until corrective gates pass.

## 17. Blocker Option Evaluation and Viable Paths

Estimation notes for this section:

1. Cost ranges use `$15k-$22k` per person-month (PM), consistent with Section 11.
2. Blocker estimates are incremental and partially overlapping; summing rows directly overstates integrated program effort.
3. Effort levels use `L/M/H` for software, DevOps, and system administration work.

### 17.1 Blocker A: No internet access on compute nodes

| Option | Timeline (weeks) | PM | Cost | Complexity | Software | DevOps | Sysadmin | Viability |
|---|---:|---:|---:|---:|---|---|---|---|
| A3 Hybrid routing (network tasks stay cloud-side) | 8-12 | 5-8 | $75k-$176k | 3 | M | M | L | High |
| A1 Controlled egress proxy allowlist | 12-16 | 8-11 | $120k-$242k | 4 | M | H | H | Medium |
| A2 Data pre-stage model | 14-20 | 10-14 | $150k-$308k | 5 | H | H | M | Low-Medium |
| A4 Phased hybrid -> selective egress | 16-24 | 12-16 | $180k-$352k | 4 | H | H | H | Medium-High |

Recommended near-term option: `A3`.  
Recommended long-term option: `A4`.

### 17.2 Blocker B: First-class Redis connectivity alternatives (SSH/stunnel explicitly rejected)

| Option | Timeline (weeks) | PM | Cost | Complexity | Software | DevOps | Sysadmin | Viability |
|---|---:|---:|---:|---:|---|---|---|---|
| B4 Non-tunneled private routed direct Redis (TLS/ACL, first-class workers) | 10-16 | 7-11 | $105k-$242k | 4 | M-H | H | H | High (if policy approved) |
| B1 Slurm-native brokered dispatch (non-first-class fallback) | 12-18 | 9-13 | $135k-$286k | 4 | H | H | M-H | Medium (not first-class) |
| B2 Federated RQ island (local Lemhi Redis + API/event bridge) | 14-22 | 11-16 | $165k-$352k | 4 | H | H | H | Medium-High |
| B3 SSH/autossh/stunnel persistent tunnel pattern | 2-5 | 2-4 | $30k-$88k | 2 | M | L-M | M | No-Go (rejected) |

Explicit consideration and rejection of SSH tunnel/stunnel:

1. `ssh -L/-R/-D`, `autossh`, and `stunnel` were considered for persistent control-plane connectivity and rejected for production.
2. Rejection rationale:
   - opaque tunnel channels weaken boundary inspection and policy enforcement
   - weak per-request identity/authorization and audit granularity relative to API boundary controls
   - operational fragility under Slurm churn and higher single-point-of-failure risk
   - inconsistent with zero-trust and least-privilege boundary posture for shared HPC environments

Security and best-practice references used for this decision:

1. NIST SP 800-207 (Zero Trust): <https://doi.org/10.6028/NIST.SP.800-207>
2. NIST SP 800-41r1 (firewall/tunnel boundary concerns): <https://doi.org/10.6028/NIST.SP.800-41r1>
3. NIST IR 7966 (SSH key-management and trust-sprawl risk): <https://doi.org/10.6028/NIST.IR.7966>
4. ATT&CK T1572 (protocol tunneling as C2 technique): <https://attack.mitre.org/techniques/T1572/>
5. CISA/FBI/CNMF AA23-250A (encrypted SSH tunnel abuse): <https://www.cisa.gov/sites/default/files/2023-09/aa23-250a.pdf>
6. OpenSSH `sshd_config` forwarding limitations: <https://man.openbsd.org/sshd_config>

Recommended near-term first-class option: `B4`.  
Recommended non-first-class fallback: `B1` (only when first-class designation is dropped).

### 17.3 Blocker C: Slurm scheduler model versus persistent workers

| Option | Timeline (weeks) | PM | Cost | Complexity | Software | DevOps | Sysadmin | Viability |
|---|---:|---:|---:|---:|---|---|---|---|
| C4 Hybrid persistent model (bounded compute queues on Lemhi) | 10-16 | 6-9 | $90k-$198k | 3 | H | M-H | M | High near-term |
| C1 Dedicated non-preempt service partition (gold model) | 14-20 | 8-12 | $120k-$264k | 4 | H | H | H | High long-term |
| C2 Renewable finite-lease in shared partition | 12-18 | 7-10 | $105k-$220k | 4 | H | H | H | Medium |
| C3 Preemptible persistent pool + checkpoint/recovery | 20-30 | 12-18 | $180k-$396k | 5 | H | H | H | Low |

Assurance for active-job non-interruption:

1. Highest under `C1` with no-preempt/no-oversubscribe/drain-first maintenance policy.
2. Medium-high under `C2` and `C4` with lease overlap + drain controls.
3. Not satisfiable under `C3` without changing requirement from non-interruption to recovery-based SLA.

Recommended near-term option: `C4` (fallback `C2` if needed).  
Recommended long-term option: `C1`.

### 17.4 Blocker D: Filesystem and small-file I/O mismatch

| Option | Timeline (weeks) | PM | Cost | Complexity | Software | DevOps | Sysadmin | Viability |
|---|---:|---:|---:|---:|---|---|---|---|
| D1 Shared filesystem tuning only | 3-5 | 1.5-2.5 | $22.5k-$55k | 2 | L | L | M | Medium (stabilization only) |
| D2 Node-local scratch + async promote | 6-9 | 4-6 | $60k-$132k | 4 | H | M | M | High near-term |
| D3 Dedicated high-IOPS POSIX run tier | 8-12 | 5-8 | $75k-$176k | 4 | M | M-H | H | High long-term |
| D4 Object-store-backed artifact refactor | 16-28 | 10-16 | $150k-$352k | 5 | H | H | M | Low near-term |

Recommended near-term option: `D2` with `D1` as immediate prerequisite.  
Recommended long-term option: `D3`.

Cost note: Section 17.4 and 17.5 cost rows are labor estimates; mandatory storage CAPEX/logistics for the 3-2-1 path are accounted separately in Section 11.3.

### 17.5 Blocker E: Shared filesystem contract across Lemhi and WEPPcloud services

| Option | Timeline (weeks) | PM | Cost | Complexity | Software | DevOps | Sysadmin | Viability |
|---|---:|---:|---:|---:|---|---|---|---|
| E1 Shared two-way mount with coherent metadata semantics | 6-9 | 6-9 | $90k-$198k | 4 | M | M-H | H | Medium |
| E2 Staged replication with snapshot/promotion protocol | 8-12 | 8-12 | $120k-$264k | 4 | H | M | M | High near-term |
| E3 Object-store refactor with manifest semantics | 16-28 | 16-24 | $240k-$528k | 5 | H | H | M-H | Medium now / High long-term |

Hardest failure mode:

1. `E1`: cross-site metadata incoherency causes stale or partial reads.
2. `E2`: promotion marker races ahead of full sync, exposing incomplete run trees.
3. `E3`: hidden POSIX assumptions break browse/export contracts during migration.

Recommended near-term option: `E2`.  
Recommended long-term option: `E3`.

### 17.6 Blocker F: Docker-coupled worker tasks

| Option | Timeline (weeks) | PM | Cost | Complexity | Software | DevOps | Sysadmin | Viability |
|---|---:|---:|---:|---:|---|---|---|---|
| F1 Reroute Docker-coupled tasks to cloud workers | 3-5 | 1.5-2.5 | $22.5k-$55k | 2 | M | M | L | High near-term |
| F3 Service-offload pattern (`weppcloudR` service call) | 6-10 | 3-5 | $45k-$110k | 4 | H | H | M | Medium-High long-term |
| F2 Rewrite to Apptainer/native HPC runtime | 8-14 | 4-7 | $60k-$154k | 5 | H | H | H | Medium long-term only |

Recommended near-term option: `F1`.  
Recommended long-term option: `F3`.

### 17.7 Viable integrated paths

Path A: Near-term St. Joe viable path (recommended)

1. `A3 + B4 + C4 + D1/D2 + E2 + F1`
2. Time to pilot-ready bounded St. Joe execution (through Phase 3): approximately 26-36 weeks.
3. Time to first-class hardened service (through Phase 4): approximately 30-42 weeks.
4. Raw blocker-sum effort: approximately 33-51 PM (`D1 + D2` included as the recommended pair).
5. Integrated program effort after overlap: approximately 25-35 PM (aligns to Sections 10 and 11).
6. Integrated labor cost: approximately $375k-$770k.
7. Timeline assumption: durations above assume approximately `3.4-4.0` concurrent FTE staffing.
8. Mandatory 3-2-1 storage non-labor spend (S-321A baseline using procurement-request server estimate): approximately $50,783-$60,783.
9. Combined Path A first-year cash exposure (labor + S-321A non-labor storage): approximately $425,783-$830,783 (plus offsite backup service OPEX).

Path B: Long-term durable Lemhi-first path (post-St. Joe horizon)

1. `A4 + B4 + C1 + D3 + E3 + F3`
2. Additional modernization duration: approximately 9-15 months beyond Path A stabilization.
3. Raw blocker-sum effort: approximately 51-76 PM.
4. Indicative labor cost: approximately $765k-$1.672M.
5. Planning delta from stabilized Path A to Path B: approximately +18-27 PM and +$270k-$594k (migration and revalidation heavy).
6. Storage note: if moving to self-hosted copy-3 backup tier (`S-321B`), add approximately $76,174.50-$88,174.50 non-labor storage spend.

### 17.8 Options not viable for near-term St. Joe delivery

1. `A2` data-prestage as primary model (high operational burden, long lead time).
2. `C3` preemptible persistent workers with checkpoint-recovery as primary model (does not satisfy non-interruption requirement).
3. `D4` and `E3` as immediate baseline (high-refactor migration risk).
4. `F2` as immediate baseline (runtime parity and validation burden too high for near-term schedule).
5. `B3` SSH/autossh/stunnel persistent control-plane tunnels (explicit security no-go).
6. `B1` brokered dispatch presented as first-class worker equivalent (it is fallback-only and does not preserve first-class Redis-coupled worker semantics).

### 17.9 Security and Best-Practice-Backed Go/No-Go Decisions (Recommended Blockers)

Global hard stops (all rows):

1. `P1-P8` unsigned by end of Phase 0 -> stop.
2. Pilot SLO floor miss -> stop expansion.
3. Institutional security-control failure at boundary controls -> stop.

| Recommended blocker path | Prerequisites | Control requirements | Residual risk | Go/No-Go | Rationale |
|---|---|---|---|---|---|
| `A3` Hybrid routing | `P2/P3/P5` approved; routing boundary in place; full capability inventory | 100% task classification, CI guard for unclassified tasks, deterministic misroute errors | Classification drift and hidden dependencies | GO (conditional) | Best near-term containment of internet-dependent task risk |
| `B4` Direct secure Redis (no tunnel) | `P2/P3` approved; non-tunneled private route active; ACL/TLS identity live | End-to-end DB contract tests, status/preflight viability tests, rotation drills, channel-silence alerting | Policy churn on cross-boundary Redis and long-lived connection instability | GO (conditional) | Only viable first-class Lemhi worker model without SSH tunnel |
| `C4` Hybrid persistent model | `P1/P7` signed; lifecycle thresholds defined; `P6` on-call owner named | Drain-first lifecycle controller, no uncontrolled active-job interruption, rollback drill under load | Shared-HPC policy churn and emergency outage events | Scope-reduce | Pilot-only GO; production no-go until repeated evidence |
| `D2` Node-local scratch + promote (with `D1`) | `D1` benchmark evidence; `P4` and `P8` approved; scratch quota/cleanup policy | Atomic promote + checksums, freshness guard, integrity load tests | Promote backlog and scratch pressure | GO (conditional) | Practical small-file mitigation while preserving rollback path |
| `E2` Staged replication | `D2` data path available; consistency and freshness SLO approved; `P8` funded | Promotion marker only after full sync verification, idempotent retry, audit trail | Replication lag and operator error | GO (conditional) | Better integrity containment than live two-way mount for near-term path |
| `F1` Reroute Docker-coupled tasks | Docker-coupled task inventory complete; cloud worker capacity planned | Hard routing to cloud profile, explicit contract errors on Lemhi, queue latency monitoring | Cloud queue saturation if under-capacity | GO (conditional) | Fastest way to remove unsupported runtime assumptions from Lemhi nodes |

### 17.10 Conditional Scope Adders (Decision-Dependent Work)

These are not in the baseline 25-35 PM estimate. Triggering any row adds scope, time, and cost.

| Conditional trigger | Additional required work | Timeline delta | PM delta | Cost delta | Decision owner(s) |
|---|---|---:|---:|---:|---|
| `P1` denies no-preempt/service-like scheduling guarantees | Shift from non-interruption model to recovery-SLA model (`C2/C3` style), add stronger checkpoint/restart and user-facing SLA contract changes | +8-16 weeks | +6-10 PM | +$90k-$220k | Lemhi governance + I-CREWS sponsor |
| Security/network disallow non-tunneled direct Redis route from Lemhi (`P2/P3` failure) | Drop first-class designation and implement brokered dispatch fallback (`B1`) with reconciliation controls | +4-8 weeks | +3-6 PM | +$45k-$132k | Security + network + platform leads |
| Institutional offsite immutable backup service is unavailable (`P8` gap) | Procure and integrate dedicated copy-3 backup tier (`S-321B`) with immutability controls and restore drills | +4-8 weeks | +1.5-3 PM | +$22.5k-$66k labor + $25,391.50-$33,391.50 capex/logistics | I-CREWS sponsor + RCDS operations |
| `D2/E2` cannot meet artifact freshness/integrity SLOs under load | Accelerate `D3` and/or `E3` migration, including compatibility adapters and dual-run validation | +12-24 weeks | +10-18 PM | +$150k-$396k | Storage admin + SWE lead + SRE lead |
| PII/regulated data is introduced into Lemhi worker flows | Data classification, encryption key lifecycle, tighter access controls, audit expansion, and compliance evidence pack | +6-12 weeks | +4-8 PM | +$60k-$176k | Security/compliance + data owner |
| `F1` reroute causes sustained cloud-queue saturation | Implement `F3` service-offload pattern with capacity controls and retry semantics | +6-10 weeks | +3-5 PM | +$45k-$110k | SWE + DevOps + operations |

## 18. End Note: Long-Term Lemhi-First Modernization Path

The long-term Lemhi-first modernization path remains:

1. `A4 + B4 + C1 + D3 + E3 + F3`
2. Additional modernization duration: approximately 9-15 months beyond Path A stabilization.
3. Raw blocker-sum effort: approximately 51-76 PM.
4. Indicative labor cost: approximately $765k-$1.672M.

### 18.1 Long-Term Work Packages (Post-Path A)

| Work package | Scope | Duration | PM | Cost |
|---|---|---:|---:|---:|
| `LT1` Control-plane hardening | Strengthen Redis boundary identity/policy automation and audit depth; close pilot-era security debt | 8-12 weeks | 4-7 | $60k-$154k |
| `LT2` Storage modernization | Move from staged replication constraints toward durable `D3/E3` architecture with compatibility adapters | 16-28 weeks | 16-24 | $240k-$528k |
| `LT3` Scheduler hardening | Progress from `C4` bounded model toward `C1` dedicated service partition guarantees | 10-16 weeks | 6-9 | $90k-$198k |
| `LT4` Runtime modernization | Convert rerouted Docker-coupled paths (`F1`) to service-offload (`F3`) for reduced cloud dependency | 6-10 weeks | 3-5 | $45k-$110k |

### 18.2 Conditional Governance for Long-Term Work

1. Start `LT2` only after two consecutive quarters of passing artifact freshness and integrity SLOs on current path.
2. Start `LT3` only with a signed Lemhi governance policy guaranteeing non-preempt service partition behavior.
3. Start `LT4` only after cloud-reroute utilization exceeds agreed saturation threshold for two consecutive reporting windows.
4. Keep dual-run rollback capability until each long-term package passes soak, chaos, and rollback drills.

Estimate caveat:

1. AI-generated implementation estimates are generally conservative for execution work.
2. This program is high complexity and cross-domain (software, DevOps, systems, security, operations), and it will require substantial human oversight, governance decisions, and coordination across teams.
3. Actual delivery effort and elapsed time can increase materially if policy approvals, ownership assignment, or cross-team dependency resolution are delayed.
