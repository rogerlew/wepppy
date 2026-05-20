# Technical and Operational Plan — I-CREWS WEPPcloud Deployment

**Date:** May 2026
**Project:** I-CREWS / St. Joe River Basin Watershed Modeling
**Companion to:** [budget-justification.md](budget-justification.md)
**Supporting detail:** [procurement-request.md](procurement-request.md), [weppcloud-architecture-overview.md](weppcloud-architecture-overview.md), [lemhi-rq-workers.md](lemhi-rq-workers.md)

---

## Why a Dedicated Deployment Is Needed

The existing WEPPcloud production servers are a shared resource. It carries:

- **BAER post-fire assessments** — time-sensitive runs for federal and state Burned Area Emergency Response teams during fire season.
- **Public WEPPcloud users** — agencies (USFS, BLM, NRCS), researchers, educators, and international users running watershed and erosion analyses through wepp.cloud.
- **Internal research workloads** — model development, ablation studies, and ongoing platform work.

WEPPcloud production servers cannot provide the compute for basin-scale calibration of the St. Joe Basin without displacing this existing workload. Only a small fraction of current capacity can be reserved for sustained I-CREWS use without disrupting unrelated operations. Background and platform topology are documented in [weppcloud-architecture-overview.md](weppcloud-architecture-overview.md); shared-service contention is summarized in [procurement-request.md § Shared Infrastructure Cannot Supply Enough Project-Usable Compute](procurement-request.md#shared-infrastructure-cannot-supply-enough-project-usable-compute).

## Why Lemhi Is Not a Fit

Lemhi was evaluated as a possible host for I-CREWS WEPPcloud workers and found to be non-viable. The summary reasons:

- WEPPcloud workers are always-on service containers attached to a Redis job queue, not scheduled Slurm jobs.
- WEPP simulations generate millions of small files per basin run; Lustre is explicitly documented as unsuitable for that I/O pattern, so a Lemhi adaptation would still require dedicated non-Lustre storage.
- Compute nodes do not provide unrestricted internet access, which breaks worker tasks that pull data from external APIs (climate, soils, terrain).
- Adapting the WEPPcloud microservices topology to HPC scheduling, container, network, and storage semantics is a substantial software project, not a deployment task.

Full feasibility analysis: [lemhi-rq-workers.md](lemhi-rq-workers.md). Summary justification: [procurement-request.md § Lemhi (C3+3) Feasibility Assessment](procurement-request.md#lemhi-c33-feasibility-assessment).

## Deployment Plan

The I-CREWS deployment uses the same operating pattern as the existing WEPPcloud production stack: Docker Compose, Caddy reverse proxy, Redis-backed RQ job queues, stateless workers reading and writing local storage. No new application architecture is required.

### Two-server topology

| Role | Host | Containers |
|------|------|------------|
| Frontend + worker pool | Server A | weppcloud (Flask), rq-engine (FastAPI), query-engine (Starlette), browse (Starlette), status2 (Go), preflight2 (Go), Redis, Caddy reverse proxy, **rq-worker**, **rq-worker-batch** |
| Worker pool only | Server B | **rq-worker**, **rq-worker-batch** |

Server B's workers connect to Server A's Redis and join the same job queues. Adding a node to the pool is a configuration change, not an application change — this is the same horizontal-scaling pattern used by production.

Run data lives on local RAID-protected storage on each server. Run outputs are replicated between hosts (ZFS send/receive) so either server holds a recoverable copy. Backup workflow is documented in [procurement-request.md § Backup and Restore Plan](procurement-request.md#backup-and-restore-plan).

## Why Two Servers

- **Frontend overhead.** The frontend stack (Flask, FastAPI, Starlette, Redis, Go WebSocket fan-out, Caddy, supporting services) consumes roughly half a node's capacity to remain interactively responsive under real user and agent traffic. A single-node deployment would either starve the frontend or starve the worker pool. Splitting roles across two hosts provides 3x the compute of a single server.
- **Storage redundancy.** Each server provides local RAID 6 SAS storage. Cross-host ZFS replication gives the deployment NAS-style redundancy without depending on the production NAS — and avoids the small-file NFS performance penalty (up to ~8x on small-file writes) that constrains the current production stack. NFS bottleneck evidence: [procurement-request.md § NFS Storage Is a Proven Bottleneck](procurement-request.md#nfs-storage-is-a-proven-bottleneck).
- **Service continuity.** Either server can independently run the full WEPPcloud stack. Planned maintenance, OS upgrades, or hardware faults on one host do not stop the deployment — the surviving host continues serving users and draining queued work.
- **Operational flexibility.** During calibration campaigns the pool can be split (Server A serves interactive users and AI-agent sessions; Server B runs long batch sweeps) or unified for maximum throughput.

## Lifecycle After I-CREWS

The servers are standard rackmount hardware running a containerized stack. Once the I-CREWS scope of work is complete, the equipment has two natural redeployment paths, subject to award terms, sponsor or pass-through instructions, and institutional property controls:

- **WEPPcloud production refresh.** The current production hosts (wepp1, wepp2) are aging Xeon 5120-class hardware. The I-CREWS servers are a direct upgrade path and can be moved into the production fleet to extend operational life of the broader public WEPPcloud service.
- **General-purpose research computing.** If production capacity is met through other means, the servers can be redeployed within RCDS as general-purpose research computing nodes. No specialized components; standard Linux server hardware.

Because WEPPcloud is fully containerized, the technical effort to redeploy between these roles is modest. The award-side approval and property-management process is governed separately by 2 CFR § 200.313 and the applicable award terms.
