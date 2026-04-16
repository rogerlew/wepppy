# Lemhi Integration Plan: First-Class Persistent RQ Workers for WEPPcloud

**Status:** Draft planning document  
**Date:** 2026-04-15  
**Audience:** WEPPcloud engineering, I-CREWS leadership, RCDS/Lemhi operations, security/network administrators  
**Purpose:** Define what is required to make Lemhi support first-class persistent WEPPcloud `rq-worker` capacity.

## 1. Problem Statement

This document answers one question:

`What would it take to run WEPPcloud rq-workers on Lemhi as first-class persistent infrastructure, not ad hoc HPC batch jobs?`

The answer is a multi-domain program touching software architecture, DevOps, cluster operations, security, networking, data management, and support ownership.

Decision headline: estimated engineering cost is approximately 9-18x the ~$42k hardware procurement, plus about 7-10 months of delivery delay before production hardening.

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
| P2 | Approved outbound connectivity path from Lemhi worker jobs to WEPPcloud queue endpoint | Lemhi network + UI security | Workers must maintain durable queue connectivity |
| P3 | Approved secure tunnel pattern (mTLS or equivalent) for Redis traffic | Security + network | Direct Redis exposure is not acceptable |
| P4 | Storage class approved for WEPP small-file metadata-heavy I/O | Lemhi storage admins | Lustre defaults can be poor fit for this workload |
| P5 | Decision on internet-restricted compute model for external APIs | I-CREWS + RCDS + security | Some task types fail without controlled egress |
| P6 | Named operations owner for 24x7 worker incidents | RCDS + WEPPcloud | No owner means no production service |
| P7 | Written Slurm/cgroup + Linux limits contract for worker jobs (`cpus-per-task`, cgroup enforcement, `ulimit` profile) | Lemhi ops + security | Nested worker fanout cannot be sized or stabilized safely without explicit limits |

## 5. Target Reference Architecture

### 5.1 Control Plane (WEPPcloud side)

1. Keep authoritative Redis and rq-engine control plane in WEPPcloud environment.
2. Add `rq-link-gateway` service in a controlled network segment.
3. Enforce mTLS + ACL-limited Redis credentials + source allowlists.
4. Export queue health metrics and tunnel session metrics.

### 5.2 Worker Plane (Lemhi side)

1. Add `rq-slurm-supervisor` (service process) that continuously maintains target worker count by submitting/renewing Slurm jobs.
2. Each Slurm job launches:
   - `rq-worker` process in approved runtime (Apptainer/OCI-compatible path).
   - `rq-link-agent` user-space tunnel client to the WEPPcloud `rq-link-gateway`.
3. Worker process points to local tunnel endpoint (localhost) instead of direct external Redis endpoint.
4. Worker process writes run data to approved mounted path that preserves WEPP path contract.

### 5.3 Storage Plane

1. Provide path-compatible mount strategy for `/wc1` and `/geodata` equivalents.
2. Add node-local scratch staging for hot intermediate files.
3. Implement async flush/promote policy for scratch -> persistent storage.
4. Define inode, quota, cleanup, retention, and backup policy for run artifacts.

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

### 6.2 Blocker B: Secure tunneling to Redis server

Required actions:

1. Build `rq-link-gateway` with mTLS termination and strict upstream mapping to Redis.
2. Issue short-lived client certs/tokens for Lemhi jobs (no long-lived static secrets in job scripts).
3. Deploy `rq-link-agent` sidecar in each worker job:
   - outbound-only connection to gateway (for firewall friendliness)
   - local bind endpoint for worker (`localhost:<port>`)
4. Implement automatic tunnel health checks and reconnect logic.
5. Add security controls:
   - cert rotation
   - revocation
   - source IP allowlist
   - per-client ACL and rate limits
6. Map and validate all required Redis database contracts through the tunnel:
   - DB 0 (locks/metadata)
   - DB 2 (status pub/sub)
   - DB 9 (RQ queues/jobs)
   - DB 11 (sessions/markers)
   - DB 13 (NoDb cache)
   - DB 15 (log-level controls)
7. Measure and enforce latency budgets for high-frequency lock/state operations. `NoDb locked()/dump_and_unlock()` patterns crossing a Lemhi->Moscow boundary introduce additional RTT and can degrade throughput if not explicitly budgeted.

Exit criteria:

1. Redis is never directly exposed to Lemhi nodes.
2. Tunnel compromise blast radius is limited by ACL scope and credential TTL.
3. Tunnel outage surfaces as alerts within SLA window.

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
   - new worker must pass tunnel, Redis auth, storage mount, and queue-heartbeat checks before accepting jobs
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
4. Enforce startup guardrails:
   - worker startup fails fast if observed limits are below required profile
   - submission templates require explicit `--cpus-per-task` and memory requests

Exit criteria:

1. Signed CPU/limits contract exists for all partitions/QOS used by Lemhi workers.
2. Soak tests show no FD exhaustion, PID exhaustion, or cgroup throttle/kill events under representative load.
3. Worker throughput and failure rate are stable across repeated runs.

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
5. Explicitly validate read/write latency impacts from Redis RTT and filesystem metadata latency together; both affect end-to-end worker throughput.

Exit criteria:

1. Throughput is within acceptable envelope against WEPPcloud baseline.
2. No data integrity regressions under concurrent worker pressure.

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
5. CI smoke tests for worker bootstrap and queue handshake.

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
3. Firewall and ACL rules for tunnel egress.
4. PKI/certificate lifecycle for mTLS.
5. Incident runbooks and escalation matrix.

### 7.4 Security Workstream

Deliverables:

1. Threat model and control mapping for tunnel and secret distribution.
2. Credential rotation and revocation procedures.
3. Audit logging requirements and retention policy.
4. Penetration test or focused red-team review of queue tunnel boundary.

### 7.5 Operations/SRE Workstream

Deliverables:

1. SLOs/SLIs for worker availability, queue lag, and job completion latency.
2. Alerting, dashboards, and paging thresholds.
3. Failure drills: tunnel loss, Redis failover, storage outage, preemption storm.
4. On-call ownership and handoff documentation.

## 8. Required Software Backlog (Concrete)

| Area | Required change | Reason |
|---|---|---|
| Queue routing | Add queue execution profiles and task capability routing | Prevent internet-required tasks from failing on offline workers |
| Worker bootstrap | Add Lemhi bootstrap mode with tunnel sidecar launch checks | Ensure deterministic secure startup |
| Task contracts | Add explicit errors for disallowed task contexts | Avoid hidden partial failures |
| Path resolution | Parameterize or map run roots while preserving `/wc1` contracts | Maintain compatibility with `get_wd` assumptions |
| Docker-coupled tasks | Replace or route around Docker CLI dependencies in HPC jobs | Docker daemon assumptions do not hold on shared HPC compute nodes |
| Runtime limit guards | Add startup checks for CPU/cgroup/`ulimit` contract compliance | Prevent unstable fanout due to unknown scheduler/runtime limits |
| Observability | Add worker/tunnel health metrics and structured events | Operability and incident response |

## 9. Program Phases, Timeline, and Gate Reviews

Estimated duration assumes prerequisites are approved quickly.

| Phase | Duration | Primary owners | Exit gate |
|---|---|---|---|
| Phase 0: Preconditions | 4-6 weeks | Governance + security + network + Lemhi ops | P1-P7 signed off |
| Phase 1: Platform plumbing | 6-8 weeks | DevOps + sysadmin | Tunnel, runtime, and supervisor MVP works in non-prod |
| Phase 2: Software adaptation | 10-14 weeks | SWE + DevOps | Queue routing and blocker guardrails merged and tested |
| Phase 3: Pilot operations | 6-8 weeks | SRE + SWE + Lemhi ops | Sustained pilot with defined SLO pass |
| Phase 4: Production hardening | 4-6 weeks | SRE + security + platform | Runbooks, alerts, drills, and rollback plan approved |

Total: approximately 7-10 months under active cross-team staffing.

Detailed execution specs with explicit decisions, weekly milestones, gate criteria, and complexity scoring are provided in Section 16.

## 10. Staffing Model (Minimum Practical Team)

| Role | FTE | Notes |
|---|---|---|
| Senior SWE / architecture lead | 0.8-1.0 | Queue/task contract refactor and integration decisions |
| DevOps/platform engineer | 1.0 | Runtime packaging, CI/CD, supervisor, deployment |
| Lemhi systems engineer | 0.5 | Scheduler/storage/network integration |
| Security/network engineer | 0.3-0.5 | Tunnel controls, PKI, firewall, audit |
| SRE/operations engineer | 0.5 | SLOs, dashboards, alerts, runbooks, drills |
| QA/integration engineer | 0.3-0.5 | End-to-end validation and regression coverage |

Estimated effort: roughly 25-35 person-months.

## 11. Cost Envelope (Order-of-Magnitude)

Using typical fully-loaded engineering rates, 25-35 person-months yields an approximate labor envelope of:

- Low range: 25 x $15,000 = $375,000
- Mid range: 30 x $18,000 = $540,000
- High range: 35 x $22,000 = $770,000

This excludes opportunity cost from diverted WEPPcloud roadmap and support work.

## 12. Validation and Acceptance Criteria

A Lemhi worker deployment should not be considered first-class until all criteria pass:

1. 30-day pilot with automated worker self-healing and no manual daily intervention.
2. Queue connectivity survives tunnel rotation, node churn, and scheduler preemption.
3. End-to-end run workflows pass with deterministic behavior and contract-compliant errors.
4. Storage integrity checks pass under concurrent high-volume run load.
5. Security review signs off on tunnel, secret handling, and audit trails.
6. On-call team accepts ownership with documented runbooks and escalation paths.

## 13. Risks and Stop Conditions

High risks:

1. Policy denial of persistent-like scheduler usage model.
2. Inability to approve secure egress/tunnel pattern.
3. Small-file metadata performance on shared storage remains unacceptable.
4. Understaffed cross-team ownership leads to unstable operations.

Stop conditions:

1. If P1-P7 are not approved by end of Phase 0, stop project.
2. If pilot cannot achieve minimum availability/latency envelope, stop productionization.
3. If security controls cannot meet institutional requirements, stop deployment.

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

The tunneling architecture described in Section 6.2 creates exactly the kind of persistent outbound connection from compute nodes that has been exploited at scale.

1. **2020 European HPC compromise** — 11+ European supercomputers compromised via stolen SSH credentials. Attackers used SSH tunneling to create proxy chains between HPC centers. 12+ German HPC centers went offline for weeks. Researchers had reused SSH keys across institutions without passphrase protection; attackers then used compute nodes as Tor and tunneling hosts.
   - References:
     - <https://www.welivesecurity.com/2020/05/18/european-supercomputers-hacked-mine-cryptocurrency/>
     - <https://www.educv.de/blog/post-2021-02-17-analyzing-a-compromised-hpc-cluster/>
     - <https://www.theregister.com/2020/05/19/supercomputers_mining_bitcoin/>

2. **NIST SP 800-223 (HPC Security Architecture)** — the federal HPC security standard defines a four-zone architecture in which *"compute nodes are not routable from outside the HPC cluster making compute nodes only available from within the cluster itself."* Establishing persistent outbound tunnels from compute nodes to external Redis violates this architecture.
   - Reference: <https://csrc.nist.gov/pubs/sp/800/223/final>
   - Reference: <https://aws.amazon.com/blogs/hpc/building-a-secure-and-compliant-hpc-environment-on-aws-following-nist-sp-800-223/>

3. **WEPPcloud Redis posture** — a single shared password across all services, no per-service Redis ACLs (as documented in `CLAUDE.md`). A compromised Lemhi worker with an active tunnel would have full read/write access to all Redis databases including session data (DB 11), locks (DB 0), and job queues (DB 9).

This is not a hypothetical risk. It is the specific attack class that took down more than a dozen European HPC centers in 2020.

### 15.6 Industry Has Moved Toward Ephemeral Workers, Not Persistent Ones

Even on cloud infrastructure (where persistent workers are architecturally supported), industry guidance has moved away from the persistent-worker model. AWS's recommended pattern for Celery on batch compute is *ephemeral* workers that scale to zero when the queue is empty — not persistent long-lived daemons.

- Reference: <https://aws.amazon.com/blogs/hpc/run-celery-workers-for-compute-intensive-tasks-with-aws-batch/>
- Reference: <https://github.com/aws-samples/aws-batch-celery-worker-example>

The Lemhi proposal moves in the opposite direction: it tries to force persistent workers onto infrastructure that is *even less* suited to them than cloud batch services, while the cloud community has already abandoned the persistent pattern where it *is* supported.

### 15.7 The Architectures That Do Work on HPC

For completeness: there are patterns that *do* work for dispatching compute to HPC from web applications. None of them preserve WEPPcloud's current architecture.

1. **Globus Compute (formerly funcX)** — function-as-a-service model where a cloud-hosted broker dispatches tasks to HPC endpoints that dynamically provision Slurm jobs. Web app → cloud broker → HPC batch jobs. Adopting this would require rewriting WEPPcloud's task dispatch layer.
   - Reference: <https://funcx.org/globus-compute.html>
   - Reference: <https://access-ci.atlassian.net/wiki/spaces/ACCESSdocumentation/pages/552828929/Globus+Compute+on+ACCESS>

2. **Slurm REST API (slurmrestd)** — a web application can submit batch jobs to Slurm via REST without running persistent workers on HPC. Again, requires re-architecting from RQ workers to Slurm batch jobs.
   - Reference: <https://aws.amazon.com/blogs/hpc/using-the-slurm-rest-api-to-integrate-with-distributed-architectures-on-aws/>

3. **Dask-jobqueue** — HPC-native pattern where a Dask scheduler dynamically submits and manages Slurm jobs. Designed for batch analytics, not for a web application task queue serving interactive users. The Dask-jobqueue documentation itself notes: *"Running Celery on HPC environment is usually very tricky whereas spawning a Dask Cluster is a lot easier."*
   - Reference: <https://jobqueue.dask.org/>

All three patterns require re-architecting WEPPcloud to submit batch jobs rather than feed persistent workers. None of them is a drop-in reuse of existing code. Each is its own multi-month engineering program, equivalent in cost to the Lemhi RQ-worker effort this plan describes — and still does not solve the shared-filesystem or internet-access problems.

### 15.8 Synthesis: What the Evidence Demands

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
3. Aligns to the Section 9 7-10 month envelope (40-42 weeks with contingency).

### 16.1 Phase 0: Preconditions (6 Weeks, Apr 20-May 29, 2026)

#### Objective

Convert `P1-P7` into signed operating contracts so engineering starts only after governance/security/network/storage/operations decisions are explicit.

#### Scope boundaries

In scope:

1. Governance, security, network, scheduler, storage, and operations decisions required for `P1-P7`.
2. Written contracts for Slurm/cgroup/`ulimit`, secure tunnel pattern, and run-path/storage model.
3. Phase 1 readiness packet with approved non-production deployment constraints.

Out of scope:

1. Building `rq-link-gateway` or `rq-slurm-supervisor`.
2. Queue-routing code changes and task rewrites (Phase 2+).
3. Production cutover or pilot operations.

#### Explicit decisions and deadlines

| Decision ID | Decision | Owner (accountable) | Deadline |
|---|---|---|---|
| D0-1 / P1 | Approve service-like persistent Slurm job pattern (or deny) | Lemhi governance lead | End of Week 2 (May 1, 2026) |
| D0-2 / P7 | Approve written Slurm/cgroup/`ulimit` runtime limits contract | Lemhi ops lead | End of Week 2 (May 1, 2026) |
| D0-3 / P2 | Approve outbound connectivity path from Lemhi workers to WEPPcloud queue boundary | Lemhi network lead | End of Week 3 (May 8, 2026) |
| D0-4 / P3 | Approve secure tunnel pattern (`rq-link-agent` -> `rq-link-gateway`) with mTLS and ACL model | Security architect | End of Week 3 (May 8, 2026) |
| D0-5 / P4 | Approve storage class and path compatibility approach for `/wc1` and `/geodata` contract | Storage admin lead | End of Week 4 (May 15, 2026) |
| D0-6 / P5 | Select internet-restricted operating policy (default target: `hybrid`) | I-CREWS sponsor + RCDS ops + security | End of Week 4 (May 15, 2026) |
| D0-7 / P6 | Assign 24x7 incident ownership and escalation chain | RCDS operations manager | End of Week 5 (May 22, 2026) |
| D0-8 | Approve Phase 1 non-production guardrails and go/no-go | Joint gate board | End of Week 6 (May 29, 2026) |

#### Weekly plan

| Week | Dates | Tasks | Deliverables |
|---|---|---|---|
| W1 | Apr 20-24 | Kickoff, owner assignment, `P1-P7` evidence template, decision calendar | Decision register template, RACI, meeting cadence |
| W2 | Apr 27-May 1 | Resolve `P1` + `P7` policy and limits discovery plan | Signed/denied `P1`, draft `P7` limits contract |
| W3 | May 4-8 | Resolve `P2` + `P3` network/tunnel security boundary | Network and security decision records |
| W4 | May 11-15 | Resolve `P4` + `P5` storage contract and hybrid policy | Storage contract memo, hybrid policy memo |
| W5 | May 18-22 | Resolve `P6` operations ownership and escalation | Ops ownership charter, escalation matrix |
| W6 | May 25-29 | Gate review and publish signed precondition packet | Phase 0 gate packet, Phase 1 go/no-go record |

#### Acceptance criteria

1. All `P1-P7` are signed with explicit constraints and owners.
2. `hybrid` policy defines task boundaries (`lemhi-safe` vs rerouted).
3. Non-production security/network/storage controls are approved for Phase 1 start.

#### Complexity (1-5)

| Major task | Score | Rationale |
|---|---|---|
| `P1` persistent Slurm policy decision | 4 | Cross-organization governance with operational risk |
| `P7` scheduler/cgroup/`ulimit` contract | 4 | Requires policy plus empirical runtime verification |
| `P2` + `P3` secure connectivity decisions | 5 | Security-critical multi-team network boundary |
| `P4` storage/path contract | 4 | High correctness and performance impact |
| `P5` hybrid policy boundary | 3 | Policy-heavy but implementation deferred |
| `P6` operations ownership model | 3 | Organizational alignment and escalation design |

### 16.2 Phase 1: Platform Plumbing (8 Weeks, Jun 1-Jul 24, 2026)

#### Objective

Deliver non-production platform plumbing (`rq-link-gateway`, `rq-link-agent`, `rq-slurm-supervisor`, startup guardrails) that is contract-aligned and operationally testable.

#### Scope boundaries

In scope:

1. `rq-link-gateway` MVP with mTLS, ACL boundary, and metrics.
2. `rq-link-agent` MVP with local bind endpoint and reconnect behavior.
3. `rq-slurm-supervisor` MVP with desired worker cardinality, heartbeat, and restart controls.
4. Worker startup guardrails (limits, mounts, tunnel readiness).
5. Non-production failure drills for tunnel loss, cert rotation, and scheduler churn.

Out of scope:

1. Full enqueue-surface routing refactor (Phase 2).
2. Docker-coupled task rewrites (Phase 2+).
3. Production pilot/hardening activities (Phases 3-4).

#### Explicit decisions and deadlines

| Decision ID | Decision | Owner | Deadline |
|---|---|---|---|
| D1-1 | Final `rq-link-gateway` placement/failover topology | DevOps lead + network lead | End of Week 1 (Jun 5, 2026) |
| D1-2 | Cert issuance and rotation workflow for `rq-link-agent` | Security lead | End of Week 2 (Jun 12, 2026) |
| D1-3 | Worker runtime packaging standard (OCI -> Apptainer profile) | DevOps lead + Lemhi ops lead | End of Week 3 (Jun 19, 2026) |
| D1-4 | Supervisor lease/heartbeat/drain thresholds | SWE lead + SRE lead | End of Week 4 (Jun 26, 2026) |
| D1-5 | MVP queue profile boundary for hybrid non-production tests | SWE lead + product owner | End of Week 5 (Jul 3, 2026) |
| D1-6 | Phase 1 exit-gate evidence checklist | Joint gate board | End of Week 6 (Jul 10, 2026) |

#### Weekly plan

| Week | Dates | Tasks | Deliverables |
|---|---|---|---|
| W1 | Jun 1-5 | Finalize topology and metrics/event schema | Topology diagram, deployment skeleton |
| W2 | Jun 8-12 | Implement `rq-link-gateway` MVP and ACL policy | Gateway config, health endpoints |
| W3 | Jun 15-19 | Implement `rq-link-agent` MVP and reconnect logic | Agent profile, reconnect test evidence |
| W4 | Jun 22-26 | Add worker guardrails for limits/mount/tunnel | Startup checks, Slurm templates |
| W5 | Jun 29-Jul 3 | Implement `rq-slurm-supervisor` MVP | Supervisor service and lease model |
| W6 | Jul 6-10 | End-to-end non-production integration under hybrid model | Integration report and handshake evidence |
| W7 | Jul 13-17 | Failure drills (tunnel/cert/preemption/restart storm) | Drill reports and control updates |
| W8 | Jul 20-24 | Gate review and Phase 2 handoff | Phase 1 gate packet and risk register |

#### Acceptance criteria

1. Gateway enforces authenticated mTLS clients with ACL-limited Redis access.
2. Supervisor restores target worker count after cancellation/preemption in non-production.
3. Worker startup fails fast when limits/mount/tunnel contracts are violated.
4. Failure drills demonstrate deterministic recovery with observable metrics.

#### Complexity (1-5)

| Major task | Score | Rationale |
|---|---|---|
| `rq-link-gateway` MVP | 5 | Security boundary + observability + correctness |
| `rq-link-agent` reconnect behavior | 4 | Stateful networking under scheduler churn |
| Worker startup guardrails | 4 | Cross-layer contract checks |
| `rq-slurm-supervisor` control loop | 5 | Desired-state reliability under churn |
| End-to-end integration and drills | 4 | Multi-component coupling |

### 16.3 Phase 2: Software Adaptation (Baseline 12 Weeks, Jul 27-Oct 16, 2026)

#### Objective

Implement contract-safe hybrid execution so Lemhi workers run only HPC-compatible tasks while WEPPcloud-hosted workers keep internet-dependent and Docker-coupled workloads.

#### Entry criteria

1. Phase 1 tunnel/runtime/supervisor plumbing is operational in non-production.
2. `P1-P7` remain approved and unchanged.
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
| E2-4 | Redis/tunnel contract hardening | DevOps + SWE + security | 4 | Multi-DB latency and resilience |
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
| S2-13 | Redis DB preflight (`0/2/9/11/13/15`) | DB health/reachability checks | None | 3 |
| S2-14 | Retry/timeout budgets for tunnel Redis clients | Bounded failure behavior | S2-13 | 4 |
| S2-15 | Lock/pubsub/queue RTT observability | Metrics and alert thresholds | S2-14 | 3 |
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
| 7 | Redis DB preflight + retry budgets | `0/2/9/11/13/15` checks passing |
| 8 | Routing/tunnel/lock RTT observability | Dashboards + alert thresholds |
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
2. Tunnel-related failure rates above agreed baseline.
3. Lock/pubsub latency causing repeatable failures or starvation.
4. Filesystem freshness/consistency violations in browse/export/readiness.
5. Security control regression in tunnel/auth path.

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
| Tunnel flap drill | 4 | Auto-reconnect and bounded retry | Worker crash loop > 10 min |
| Redis transient outage drill | 4 | Graceful retry/recovery without lock corruption | Lock-timeout error rate > 1% |
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
| Technical uncertainty | 4 | Scheduler, tunnel, storage behavior still partly unknown |
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

### 17.2 Blocker B: Secure tunneling to Redis

| Option | Timeline (weeks) | PM | Cost | Complexity | Software | DevOps | Sysadmin | Viability |
|---|---:|---:|---:|---:|---|---|---|---|
| B1 `rq-link-agent` + `rq-link-gateway` (mTLS) | 8-12 | 6-9 | $90k-$198k | 4 | H | H | M | High |
| B2 Envoy sidecar + egress gateway | 12-18 | 9-13 | $135k-$286k | 5 | M | H | H | Medium near-term / High long-term |
| B3 WireGuard overlay + direct Redis | 6-10 | 4-7 | $60k-$154k | 4 | L-M | M | H | Medium-Low |
| B4 Bastion SSH/stunnel bridge (interim) | 2-5 | 2-4 | $30k-$88k | 2 | M | L-M | M | Low (stopgap only) |

Required contract coverage for all viable options: Redis DB `0/2/9/11/13/15` with explicit ACL and observability.

NoDb lock/unlock latency implication:

1. `locked() ... dump_and_unlock()` patterns perform about 7 Redis round trips in the happy path.
2. Added cross-site RTT cost is approximately `7 * RTT` per lock cycle (before retries/contention).
3. At 12 ms RTT this is about 84 ms additional lock-cycle latency; at 25 ms RTT this is about 175 ms.

Recommended near-term option: `B1`.  
Recommended long-term option: `B2`.

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

1. `A3 + B1 + C4 + D1/D2 + E2 + F1`
2. Critical path duration: approximately 16-24 weeks when sequenced with dependencies from Section 16.
3. Raw blocker-sum effort: approximately 32-49 PM.
4. Integrated program effort after overlap: approximately 25-35 PM (aligns to Sections 10 and 11).
5. Integrated labor cost: approximately $375k-$770k.

Path B: Long-term durable Lemhi-first path (post-St. Joe horizon)

1. `A4 + B2 + C1 + D3 + E3 + F3`
2. Additional modernization duration: approximately 9-15 months beyond Path A stabilization.
3. Raw blocker-sum effort: approximately 53-78 PM.
4. Indicative labor cost: approximately $795k-$1.716M.

### 17.8 Options not viable for near-term St. Joe delivery

1. `A2` data-prestage as primary model (high operational burden, long lead time).
2. `C3` preemptible persistent workers with checkpoint-recovery as primary model (does not satisfy non-interruption requirement).
3. `D4` and `E3` as immediate baseline (high-refactor migration risk).
4. `F2` as immediate baseline (runtime parity and validation burden too high for near-term schedule).

## 18. End Note: Long-Term Lemhi-First Modernization Path

The long-term Lemhi-first modernization path remains:

1. `A4 + B2 + C1 + D3 + E3 + F3`
2. Additional modernization duration: approximately 9-15 months beyond Path A stabilization.
3. Raw blocker-sum effort: approximately 53-78 PM.
4. Indicative labor cost: approximately $795k-$1.716M.

Estimate caveat:

1. AI-generated implementation estimates are generally conservative for execution work.
2. This program is high complexity and cross-domain (software, DevOps, systems, security, operations), and it will require substantial human oversight, governance decisions, and coordination across teams.
3. Actual delivery effort and elapsed time can increase materially if policy approvals, ownership assignment, or cross-team dependency resolution are delayed.
