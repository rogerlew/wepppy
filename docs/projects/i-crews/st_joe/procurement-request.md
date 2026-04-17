# Server Procurement Request: WEPPcloud Compute Infrastructure for the St. Joe Basin Project

**Date:** March 2026

**Project:** I-CREWS / St. Joe River Basin Watershed Modeling

**Requested by:** WEPPcloud Development Team

**Funding Source:** I-CREWS Grant

**Total Cost:** $42,783.00 (two servers at $21,391.50 each)

---

## Executive Summary

We request the procurement of two Supermicro SuperServer 621P-TR rack servers to serve as dedicated compute infrastructure for the I-CREWS St. Joe River Basin modeling initiative. During the scope of the I-CREWS project, these servers will be dedicated to I-CREWS sites and primarily the St. Joe basin calibration, scenario analysis, and WEPP simulation workloads. They will provide approximately 4x the compute capacity of the current infrastructure, include dedicated local storage to eliminate the NFS bottlenecks that currently constrain modeling throughput, and establish redundancy for a service that supports time-critical Burned Area Emergency Response (BAER) operations during fire season.

Upon completion of the I-CREWS project, these servers will transition into the university's broader research computing infrastructure — either as permanent WEPPcloud production nodes (replacing or augmenting the aging current hardware) or as general-purpose compute within RCDS (Research Computing and Data Services), as institutional need dictates. The containerized, portable architecture of WEPPcloud makes this transition seamless.

The WEPPcloud software platform is ready for production use. The entire St. Joe basin has already been delineated into 56 tributary watersheds comprising 134,033 hillslopes and 151,121 channel segments. Modeling is waiting on compute capacity.

---

## WEPPcloud and Its Mission-Critical Role

### What WEPPcloud Does

WEPPcloud ([wepp.cloud](https://wepp.cloud)) is a web-based watershed modeling platform built on the USDA Water Erosion Prediction Project (WEPP) model. It enables users to delineate watersheds, assign soils and land cover, configure climate scenarios, and run physically-based erosion and hydrology simulations — all through a browser interface. The platform processes digital elevation models, constructs hillslope profiles, runs FORTRAN-based WEPP simulations for each hillslope and channel segment, and aggregates results at the watershed scale.

WEPPcloud is fully containerized using Docker and Docker Compose, making it portable and configurable for multiple deployment environments — development, staging, and production — with environment-specific configuration managed through composable overlay files. The platform's simulation workload is distributed through a Redis-backed RQ (Redis Queue) worker pool. Workers are stateless processes that pull jobs from the queue and execute WEPP simulations independently, allowing the worker pool to scale horizontally across multiple nodes. Adding a second server doubles the available worker capacity with no changes to application code — new workers simply join the existing queue.

WEPPcloud also supports batch processing of watersheds through its API and task pipeline, enabling automated runs across collections of watersheds with different parameter sets, climate scenarios, or management treatments. This capability is essential for the St. Joe project, where calibration and scenario analysis require systematic runs across all 56 tributary watersheds.

### Supporting BAER Teams During Fire Season

Each wildfire season, Burned Area Emergency Response (BAER) teams are deployed to assess post-fire erosion risk and recommend emergency stabilization treatments. These teams operate under extreme time pressure — assessments must be completed within days of fire containment to inform decisions about road closures, culvert upgrades, seeding, and erosion barriers before the first significant rainfall.

WEPPcloud is a primary tool used by BAER teams to model post-fire erosion scenarios. The platform's "disturbed" configuration mode allows teams to apply fire-severity burn maps to watersheds and simulate how different soil burn severities affect runoff and sediment delivery. During peak fire season (June through November), multiple BAER teams may be running concurrent simulations across different fire perimeters, each requiring thousands of individual hillslope WEPP runs.

Service reliability during fire season is not optional. When a BAER team is in the field with a 7-day assessment window, server downtime or slow processing directly impacts their ability to deliver actionable recommendations. A second deployment provides the redundancy necessary to maintain service availability during this critical period.

### Public Use for Land Management and Research

Beyond BAER response, WEPPcloud serves a broad user base:

- **Federal land managers** (USFS, BLM, NRCS) use the platform for watershed assessment, forest management planning, and environmental impact analysis
- **State agencies** model erosion risk for road construction, timber harvest, and post-fire rehabilitation projects
- **Academic researchers** use WEPPcloud for hydrological studies, climate change impact analysis, and graduate research
- **Educators** use WEPPcloud for classroom exercises in hydrology and erosion science, as well as practitioner training for land management professionals
- **International users** apply the platform to watersheds worldwide for erosion prediction and land management planning

The platform currently serves users across multiple time zones and use cases simultaneously. As the user base grows and project scope expands (particularly with the St. Joe basin initiative), the current infrastructure cannot sustain acceptable response times for all users.

---

## The St. Joe Basin: Scale and Compute Demand

### Delineation Status — Ready for Modeling

The entire St. Joe River Basin has been delineated and is ready for WEPP simulation. This work, completed in March 2026, decomposed the basin into 56 tributary watersheds at 30-meter resolution using WhiteboxTools terrain processing. The delineation statistics demonstrate the scale of the compute challenge:

| Metric | Value |
|--------|-------|
| Tributary watersheds | 56 |
| Total channels | 151,121 |
| Total hillslopes / subcatchments | 134,033 |
| Total flowpaths | 4,562,720 |
| Total watershed area | ~4,112 km² (~411,200 ha) |

Each of these 134,033 hillslopes requires an individual WEPP simulation. A single WEPP hillslope run executes a FORTRAN binary that reads soil, climate, and management input files, performs daily water balance and erosion calculations over the simulation period, and writes output files. At the watershed scale, an additional WEPP run routes water and sediment through the 151,121 channel segments. The 120 TB of storage is anticipated to provide a roughly 20x capacity factor for calibration runs.

### Why Basin-Level Calibration Requires Full-Basin Runs

Calibrating the St. Joe basin model is not a matter of tuning individual tributaries in isolation. Upstream flow volume and sediment load directly affect downstream delivery timing and magnitude. A change in hillslope erodibility in an upper tributary alters the sediment supply to every downstream channel segment and ultimately the basin outlet. This means that each calibration iteration requires running the entire basin — all 134,033 hillslopes and 151,121 channels — to evaluate the effect of parameter adjustments on watershed-scale outputs. On current hardware, a single full-basin run is prohibitively slow due to running in a deprioritized batch queue. With the proposed servers, iterative calibration becomes feasible.

### Compute Estimate

On current hardware, a single WEPP hillslope run takes on the order of seconds, but 134,033 hillslopes running through multi-year climate sequences accumulate to hours or days of wall time depending on parallelism. The proposed servers would reduce this by roughly 4x in aggregate throughput and 20% per individual simulation (single-thread improvement), making iterative calibration and scenario analysis practical within research timelines.

The RQ worker pool architecture is well-suited to this workload. Hillslope simulations are embarrassingly parallel — each is independent and can be dispatched to any available worker. With 256 cores across two servers (versus 88 today), the worker pool can sustain far higher job concurrency. Combined with WEPPcloud's batch processing capability, which automates the submission and tracking of multi-watershed runs, the proposed infrastructure enables systematic parameter sweeps and scenario comparisons across the full St. Joe basin without manual intervention.

### Alternative Futures Scenario Modeling

Beyond calibration, a central objective of the I-CREWS project is to evaluate alternative management futures for the St. Joe basin — comparing how different land management strategies affect erosion, sediment delivery, and watershed health under varying climate conditions. This scenario modeling multiplies the compute demand far beyond a single baseline run.

WEPPcloud includes OMNI, a scenario modeling framework that supports a range of land management treatments and disturbance types:

- **Wildfire** — post-fire erosion modeling with spatially distributed burn severity maps
- **Prescribed fire** — planned burn scenarios with controlled severity and extent
- **Forest thinning** — selective harvest treatments that alter canopy cover and ground disturbance
- **Mulching** — post-disturbance surface cover treatments that reduce erosion
- **Other landuse changes** — grazing, road construction, vegetation recovery, and restoration treatments

Each of these management scenarios can be evaluated under multiple climate regimes:

- **Observed climate** — historical weather records for hindcast validation
- **Stochastic climate** — statistically generated weather sequences (via CLIGEN) that capture natural variability and enable probabilistic risk assessment
- **Future climate** — downscaled climate projections (e.g., CMIP scenarios) to evaluate management strategies under changing precipitation and temperature regimes

The combinatorial nature of this analysis — multiple management treatments crossed with multiple climate regimes across 56 tributary watersheds — produces dozens to hundreds of full-basin runs. Each full-basin run requires simulating all 134,033 hillslopes and routing through 151,121 channels. This is the fundamental driver of the compute requirement: not a single model run, but a matrix of alternative futures that must be evaluated systematically to inform land management decisions for the St. Joe basin.

---

## Why Dedicated Servers Are Necessary

### Platform Topology and AI-Driven Workflow

WEPPcloud is a persistent containerized service platform, not a single executable that can be submitted to a scheduler and forgotten. The production topology includes the `weppcloud` web application, `rq-engine` for operational job control, `query-engine` and `browse` for analytics and file access, Redis-backed job queues, and stateless RQ worker pools operating against shared run state and local model outputs. Human users and AI agents both authenticate into this stack and drive the same APIs. For the full topology diagram and service description, see [weppcloud-architecture-overview.md](weppcloud-architecture-overview.md).

That service topology exists to support an AI-driven calibration workflow rather than one-shot batch execution. The St. Joe loop is: inspect basin outputs, form a calibration hypothesis, adjust parameters, submit another full-basin run, query the resulting diagnostics, and repeat. That requires always-on services, immediate queue dispatch, persistent run state, and low-latency access to very large numbers of small WEPP files over hours-long working sessions. Dedicated servers match that operating model. Shared infrastructure and HPC-style scheduling are optimized for queued batch jobs; the St. Joe effort requires an interactive modeling platform that can remain online while continuously feeding new work to the worker pool.

### Why Two Servers Are Needed

- RAID 6 arrays on each server provide resilient local storage for active run data before calibration outputs are archived to DataHub.
- Two hosts provide enough compute for an independent WEPPcloud deployment dedicated to I-CREWS workloads; because that workload is bounded, frontend worker counts and RQ parallelism can be tuned aggressively for throughput without risking public quality-of-service regressions.
- Dedicated I-CREWS capacity isolates large St. Joe calibration/scenario runs from BAER and public WEPPcloud traffic, preventing cross-project resource contention and user-facing slowdowns.
- The two-node layout supports split-mode operations: one server can prioritize interactive/operational traffic while the other executes long-running calibration and scenario batches, then both can be pooled when maximum throughput is required.
- Planned maintenance and unplanned faults become survivable events: one server can be patched, rebooted, or repaired while the other continues serving the stack and draining queued work.
- In the post-I-CREWS transition path, these same servers can be reassigned as additional production `rq-worker` nodes, extending WEPPcloud compute throughput without redesigning the application architecture.

### Stack Compute Optimizations Already in Place

This procurement request is not an attempt to compensate for inefficient software. WEPPcloud is an approximately eight-year-old production stack that has already been repeatedly optimized to fit within a modest on-prem server footprint. The current bottleneck is basin scale, not a lack of engineering effort.

Over that time, the team has moved multiple hot paths out of Python and into owned Rust components designed specifically for WEPPcloud workloads. The current stack includes `wepppyo3` for climate and raster acceleration, `peridot` for watershed abstraction, and the custom `weppcloud-wbt` fork for terrain and TOPAZ processing. Documented examples already in use include:

- A production microservices topology split across Starlette services (`query-engine`, `browse`), FastAPI services (`rq-engine`), and Go services (`status2`, `preflight2`), with tunable Gunicorn/Uvicorn process counts and RQ worker-pool sizing to absorb interactive and batch load spikes

- Rust `make_rhem_storm_file` in `wepppyo3`, which delivered a documented **400x speedup** for RHEM storm-file generation
- `peridot` watershed abstraction, documented in the codebase as **3x to 10x faster than Python**, with representative-flowpath mode reducing hillslope abstraction time by **10x to 100x** for large batch workflows
- `weppcloud-wbt` VRT/windowed GeoTIFF support, which avoids full in-memory raster loads for cropped DEM inputs and reduces memory pressure during terrain preprocessing
- WEPP interchange plus the DuckDB-backed query stack, which converts large raw WEPP text outputs into compressed Parquet tables, supports cleanup of selected raw text artifacts after successful conversion to reduce disk footprint and inode pressure, and enables interactive real-time querying of multi-GB Parquet datasets

Memory footprint has also been explicitly optimized in the core WEPP executable path. Since October 2025, the build system has produced both the full watershed `wepp` binary and a hillslope-optimized `wepp_hill` variant. The hillslope build compiles against reduced-dimension include files specifically for hillslope work, shrinking key static limits from `mxhill 45000 -> 45`, `mxplan 15000 -> 15`, `mxelem 60000 -> 85`, and `ntype 15000 -> 15`. In the currently vendored binaries (`wepp_260414` versus `wepp_260414_hill`), that cuts the compiled `.bss` static array footprint from approximately **14.0 GB** to **2.0 MB** — about a **7000x reduction** in reserved global-array space for hillslope runs.

These optimizations are the reason WEPPcloud remains usable on constrained hardware today. They also strengthen the procurement case: even after aggressive software and memory optimization, the St. Joe basin still requires dedicated compute and local storage because the workload itself is inherently large.

### NFS Storage Is a Proven Bottleneck

The current production server (wepp1) stores all modeling data on a network-attached storage (NAS) device accessed via NFS. Benchmarking (compared to development ZFS NFS share) has quantified the performance penalty this imposes on WEPPcloud's metadata-heavy workload:

| Operation | NFS (Production) | Local Filesystem | Penalty |
|-----------|-------------------|------------------|---------|
| Small-file write | 135.7 files/s | 1,101.4 files/s | **8.1x slower** |
| File read | 1.37 MiB/s | 8.91 MiB/s | **6.5x slower** |
| File delete | 861 files/s | 2,030 files/s | **2.4x slower** |
| Metadata stat | 12,900 stats/s | 17,700 stats/s | **1.4x slower** |

WEPPcloud's workload is dominated by small-file I/O: each hillslope generates multiple input files (soil, slope, management, climate) and multiple output files (water balance, sediment, runoff summaries). A 20,000-hillslope watershed creates over 100,000 small files during a single model run. At the St. Joe basin scale (134,033 hillslopes), the NFS penalty on file creation alone adds hours of overhead per run.

The proposed servers include 176 TB of local SAS storage per server (8 x 22 TB drives with hardware RAID 6), eliminating the NFS bottleneck entirely. Run data stays local to the compute node, and completed results can be archived to network storage asynchronously.

Additionally, the production NAS is approaching inode capacity (60% consumed at 149 million of 250 million inodes), further motivating the transition to local storage for active modeling workloads.

### Shared Infrastructure Degrades User Experience

The current production server is a shared resource. When a large modeling job (such as a BAER team's fire assessment or a research user's climate scenario batch) consumes available CPU cores, all other users experience degraded response times — slower map rendering, delayed watershed delineation, and queued simulation jobs. The St. Joe basin project, with its 134,033 hillslopes, would monopolize the current server during calibration runs, effectively locking out other users.

During the I-CREWS project, dedicating these servers to St. Joe basin work allows calibration and scenario runs to proceed at full throughput without impacting the public-facing WEPPcloud service on the existing infrastructure. During fire season, the containerized architecture allows compute to be temporarily reallocated to prioritize BAER team requests, then returned to I-CREWS workloads once the immediate response period ends.

### Redundancy for Service Continuity

WEPPcloud currently runs on a single production server (wepp1) with a partial VM on a second machine (wepp2) providing limited overflow capacity. There is no failover capability — if wepp1 goes down during fire season, BAER teams lose access to the platform entirely.

The second proposed server establishes true redundancy. Because WEPPcloud is containerized, the full application stack — web frontend, API, task queue, and worker pool — can be deployed identically on either server. Either server can independently run the complete WEPPcloud service, so hardware failure, maintenance windows, or OS upgrades do not result in service outages. In normal operation, both servers contribute RQ workers to a shared job queue, effectively doubling simulation throughput. If one server goes offline, the remaining server continues processing without manual intervention — jobs simply take longer as the worker pool is reduced.

For the St. Joe project, this two-node architecture enables parallel modeling: one server can run calibration batch jobs while the other serves interactive users, or both can be pooled together for maximum throughput during intensive calibration cycles.

---

## Lemhi (C3+3) Feasibility Assessment

For the full first-class `rq-worker` integration thought experiment (requirements, blockers, timelines, and costs), see [lemhi-rq-workers.md](lemhi-rq-workers.md).

### Summary Conclusion

Using Lemhi as a direct replacement for WEPPcloud production worker hosts is **not currently viable**. Lemhi is a shared high-performance computing (HPC) system for scheduled research jobs, but WEPPcloud's production worker architecture is designed around always-on service containers, continuously connected queue workers, and run-directory mounts that behave like dedicated infrastructure.

**Simple batching of jobs is also problematic.** Many WEPPcloud RQ tasks are hierarchical: a parent job dynamically enqueues child jobs, records the child ids in job metadata, and uses Redis-backed `depends_on` edges to build multi-stage execution trees for prep, hillslopes, watershed routing, post-processing, interchange, export, and finalization. Running an RQ task function as a standalone Slurm job is therefore not equivalent to running the workflow. The parent task still needs live RQ/Redis access in order to enqueue its descendants, publish status, support cancellation, and advance the job tree.

### Plain-Language Architecture Comparison

| WEPPcloud production worker model | Lemhi (C3+3) operating model |
|---|---|
| Long-running `rq-worker` containers continuously pull jobs from a Redis Queue (RQ). | Compute is allocated through scheduled Slurm jobs (`srun`/`sbatch`) with partition/runtime policies and fair-share scheduling. |
| Worker hosts mount shared run/geodata paths (`/wc1`, `/geodata`) with stable write permissions and path contracts. | Users run in shared Lustre-backed storage with quota and contention controls; path and permission model is not a drop-in match for WEPPcloud host mounts. |
| Worker jobs may call external APIs (for example topography and climate providers) during execution. | Cluster guidance indicates compute nodes do not generally have internet access; dependency/data staging is expected before job execution. |
| Worker stack includes container assumptions such as local Docker socket and optional local `weppcloudr` service for some job paths. | HPC centers typically optimize for scheduler-managed jobs, not persistent rootful Docker daemon workflows across shared compute nodes. |

### Primary Architectural Barriers

1. **RQ service model mismatch**
WEPPcloud workers are designed as persistent services that stay online and attached to the queue. Lemhi is designed for scheduled jobs with time limits and queue fairness, not for always-on daemon pools as primary infrastructure.

Even if a communication workaround were created, the child jobs themselves are enqueued with explicit RQ timeout assumptions for the always-on WEPPcloud queues (typically 12-hour timeouts on the default and batch queues). Those timeouts assume immediate pickup by persistent workers, not scheduler latency, queue wait time, or nested allocation delays inside Slurm.

2. **Required WEPPcloud mount contracts (`/wc1`, `/geodata`)**
The WEPPcloud worker deployment contract requires shared mounts at canonical paths with stable permissions and ownership semantics. This is a hard requirement for run-directory discovery, NoDb state, and output write paths. Recreating that contract on a shared HPC filesystem would require non-trivial storage and permission exceptions.

3. **Small-file I/O behavior conflicts with Lustre guidance**
WEPP workloads generate very large numbers of small files and metadata operations. C3+3 Lustre guidance explicitly warns that small-file-heavy patterns and high metadata pressure create contention and degrade shared filesystem performance. This is the opposite of the local high-IOPS worker storage model described in this request.

4. **Networking and secure queue connectivity**
WEPPcloud remote workers require secure connectivity to the RQ Redis server on wepp.cloud and shared secrets alignment. On Lemhi, compute-node network constraints and security boundaries make persistent external queue attachment operationally difficult.

5. **Internet-restricted compute nodes block some worker tasks**
Some WEPPcloud worker paths call public APIs to acquire source data. If compute nodes cannot reach the internet, those tasks fail unless data is pre-staged or architecture is redesigned.

6. **Policy and intended-use mismatch**
C3+3 documentation explicitly warns users not to run heavy compute on shared login/OnDemand nodes; heavy work is expected through scheduled compute jobs. WEPPcloud production workers, however, are designed as continuously running service components rather than ad hoc scheduled research jobs.

7. **Container runtime expectations differ (Docker daemon vs HPC runtimes)**
Lemhi documentation does not explicitly advertise Docker daemon support for user workloads. In HPC practice, this usually means running containers through Apptainer/Singularity under Slurm. Apptainer is designed for HPC and supports Docker/OCI images, so containerized execution is still possible, but only with adaptation of runtime, scheduling, and service-lifecycle assumptions compared with WEPPcloud's Docker Compose worker-host model.

### Practical Implication for This Procurement

Lemhi may still be useful for specific, tightly scoped research workflows that are explicitly rewritten for Slurm-native batch execution. However, it is not a drop-in host for the WEPPcloud production worker stack needed for reliable St. Joe calibration/scenario throughput and BAER-adjacent service continuity. The dedicated server procurement remains the correct architecture-aligned path.

### External References

- C3+3 Getting Started: <https://docs.c3plus3.org/docs/help/Getting_Started/>
- C3+3 Partitions/Slurm usage: <https://docs.c3plus3.org/docs/help/Tutorials/Partitions.html>
- C3+3 Linux workshop (shared node guidance): <https://docs.c3plus3.org/docs/workshops/Linux/>
- C3+3 R tutorial (compute node internet note): <https://docs.c3plus3.org/docs/help/Tutorials/R.html>
- C3+3 Lustre guidance (small-file contention): <https://docs.c3plus3.org/docs/help/Tutorials/Lustre.html>

---

## Hardware Specifications and Justification

### Proposed Configuration (per server)

| Component | Specification |
|-----------|---------------|
| Chassis | Supermicro SuperServer 621P-TR, 2U rackmount |
| Processors | 2x Intel Xeon Gold 6530 (32-core, 2.1 GHz, 160 MB cache) |
| Memory | 256 GB DDR5-5600 ECC RDIMM (8x 32 GB) |
| Boot drive | 480 GB Micron 7450 PRO M.2 NVMe |
| Data storage | 8x 22 TB SAS 12 Gb/s (176 TB raw) with Broadcom MegaRAID 9560-8i + CacheVault |
| Network | Dual 1 GbE onboard |
| Power | 1200 W 1+1 redundant PSU |
| Management | Supermicro Update Manager (SUM) OOB management |

### Compute Improvement

| Metric | Current (wepp1 + wepp2) | Proposed (2x 621P-TR) | Improvement |
|--------|-------------------------|------------------------|-------------|
| Total cores | 56 + 32 = 88 | 128 + 128 = 256 | 2.9x |
| Passmark (aggregate) | ~46,910 | ~183,956 | **3.9x** |
| Single-thread Passmark | 1,756 | 2,116 | **1.2x (20%)** |
| RAM | — | 512 GB total | — |
| Local storage | NFS only | 352 TB raw SAS + RAID | Eliminates NFS bottleneck |

The 3.9x aggregate compute improvement, combined with the elimination of NFS I/O penalties (up to 8x on small-file writes), translates to an effective throughput improvement well in excess of 4x for WEPPcloud's modeling workload.

---

## Cloud Compute Equivalency and Break-Even (AWS Snapshot)

### Pricing Snapshot Date

April 16, 2026

### Equivalency Assumptions

- **Purchase baseline:** two servers for **$42,783.00** total.
- **Project accounting boundary:** ongoing operational and maintenance costs are assumed to be covered by RCDS (not charged to I-CREWS), so break-even is calculated against project-visible spend.
- **Compute parity target:** two AWS `c6i.32xlarge` Linux instances in US West (Oregon), yielding **256 vCPU** and **512 GiB RAM** (matching the proposed two-server aggregate).
- **Storage parity targets:**
  - **Full local parity:** 264 TB usable RAID6 equivalent (`2 x (8 - 2) x 22 TB`).
  - **Planned active working set parity:** 120 TB.
- **Container footprint reserve:** 1 TB additional gp3 block storage to account for OS + Docker images + writable layers + deployment rollback headroom. Local images are already multi-GB (for example `wepppy:latest` ~6.8 GB, `wepppy-dev:latest` ~4.5 GB, `docker-fcgiwrap:latest` ~4.4 GB, `weppcloudr-dev:latest` ~3.0 GB).
- **Cloud rates used (US West/Oregon):**
  - `c6i.32xlarge` Linux On-Demand: **$5.44/hour**.
  - EBS gp3 storage: **$0.08/GB-month**.
  - Sensitivity case for discounted compute: 3-year Reserved Instance effective rate for `c6i.32xlarge` (standard, all upfront): **$2.0846/hour**.

### Break-Even Method

`break_even_months = server_purchase_cost / equivalent_cloud_monthly_cost`

### Results

| Scenario | Equivalent Cloud Monthly Cost | Break-Even vs $42,783 Purchase |
|---|---:|---:|
| Compute only (2x `c6i.32xlarge`, no storage parity) | $7,942.40 | 5.39 months |
| Compute + 120 TB gp3 + 1 TB container reserve | $17,854.72 | 2.40 months |
| Compute + 264 TB gp3 + 1 TB container reserve | $29,651.20 | 1.44 months |
| 3-year RI compute + 120 TB gp3 + 1 TB reserve | $12,955.76 | 3.30 months |
| 3-year RI compute + 264 TB gp3 + 1 TB reserve | $24,752.24 | 1.73 months |

### Interpretation

With compute-and-storage equivalency, the hardware purchase breaks even quickly (roughly **1.4 to 3.3 months** in the scenarios above). Storage parity dominates total cloud cost for this workload profile; container footprint reserve changes the result only marginally but is included for realism.

These estimates are conservative for cloud spend because they do **not** include additional cloud-side costs such as data egress, request charges, snapshots/backups, extra gp3 IOPS/throughput provisioning, or managed service overheads.

### AWS Price Sources

- AWS EC2 price index (US West/Oregon): <https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/us-west-2/index.json>
- AWS S3 price index (US West/Oregon): <https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/us-west-2/index.json>

---

## Asset Lifecycle: I-CREWS and Beyond

During the I-CREWS project period, both servers will be dedicated to St. Joe basin modeling — calibration runs, scenario analysis, and batch simulation workloads that require sustained, high-throughput compute with local storage.

Upon completion of the I-CREWS project, the servers retain full value to the university through two natural transition paths:

- **WEPPcloud production infrastructure.** The current production servers (wepp1, wepp2) are aging Xeon 5120-class hardware. The new servers are a direct upgrade path, capable of replacing the existing production fleet and serving the growing WEPPcloud user base — BAER teams, federal agencies, researchers, and students — with significantly improved capacity and redundancy.
- **RCDS general-purpose compute.** If WEPPcloud's production needs are met through other means, the servers are standard 2U rackmount hardware with no specialized components. They can be redeployed as general-purpose research computing nodes within the university's Research Computing and Data Services infrastructure.

Because WEPPcloud is fully containerized and environment-agnostic, transitioning the servers between these roles requires only configuration changes — no hardware modifications or software rewrites. The same Docker Compose stack that runs St. Joe calibration today can serve public WEPPcloud traffic tomorrow.

---

## Backup and Restore Plan

### Design Goals

- Keep active WEPP run execution on local storage with no NFS dependency in the hot path.
- Maintain a nearline on-prem backup copy on the second server for rapid recovery.
- Promote only high-value finalized outputs to DataHub for long-term retention.
- Keep calibration and parameterization definitions versioned in Git repositories with GitHub remotes.

### Storage Topology

- **Server A (primary run host):** primary WEPPcloud run execution storage on local RAID6 ZFS.
- **Server B (backup host):** backup target storage on local RAID6 ZFS.
- **Cross-mounting:** each server mounts the peer ZFS dataset read/write for replication operations and read-only for recovery validation where appropriate.
- **Role model:** one server is active for run generation; the other is backup-first. Roles can be swapped during maintenance or failover.

### Data Classes and Protection Strategy

| Data Class | Typical Size | System of Record | Protection Method |
|---|---|---|---|
| Run inputs (watershed extent, outlet, ~100 parameters, configs) | Small | Git repositories + run metadata | Git commits + GitHub remote replication; included in run manifests |
| Active run working data/results | Very large | Primary ZFS on active host | Frequent ZFS snapshots + cross-host ZFS replication |
| Milestone/final run outputs worth preserving | Large | DataHub archive | Curated export from run storage to DataHub with manifest/checksum |
| Calibration/parameterization code and scripts | Small to moderate | Git repositories | Branch/tag/release discipline with GitHub remote backup |

### Backup Workflow

1. **Local snapshot cadence**
   - Create frequent immutable ZFS snapshots on the active run dataset during calibration windows.
   - Keep shorter retention for high-frequency snapshots and longer retention for daily/weekly checkpoints.
2. **Cross-host replication**
   - Replicate snapshots from Server A to Server B using incremental ZFS send/receive.
   - Run replication continuously or on a short schedule so backup lag remains low.
3. **Archive promotion**
   - After calibration milestones or accepted scenario sets, export selected results to DataHub.
   - Record archive manifests with run identifiers, parameter hashes, and checksums.
4. **Git-backed reproducibility**
   - Commit calibration/parameterization changes with run-linked commit references.
   - Push all authoritative repositories to GitHub remote as off-site backup.

### Restore Procedures

1. **Single-run or partial restore**
   - Locate snapshot by run ID and timestamp.
   - Restore only the required run subtree from Server B to Server A.
   - Re-run verification queries against restored outputs.
2. **Primary host storage failure**
   - Promote Server B dataset as the active run store.
   - Repoint WEPPcloud worker and service mounts to Server B paths.
   - Resume queue processing; rebuild Server A and re-establish reverse replication.
3. **Corruption discovered after milestone**
   - Recover from DataHub archived package for finalized results.
   - Reconstruct working state from Git-tracked inputs and parameterization commits when necessary.

### Recovery Objectives

- **RPO (run storage):** bounded by snapshot/replication interval (target: low-hour or better).
- **RTO (host failure):** bounded by service remount and worker restart time on the backup host.
- **Reproducibility objective:** any archived milestone run can be regenerated from Git-tracked inputs/parameters plus recorded run manifests.

### Operational Notes

- The run-generation footprint is input-light but output-heavy; backup policy prioritizes fast protection of large run outputs and durable versioning of small control inputs.
- This plan assumes ongoing infrastructure operations are covered by RCDS and can be integrated with existing RCDS monitoring, backup scheduling, and incident response practices.

---

## Institutional Support and Partnership Context

WEPPcloud's compute operations are not a one-off arrangement. Over the entire life of `wepp.cloud` (8+ years), the platform has benefited from RCDS operations, maintenance, and hosting support. This procurement extends an established operating model rather than creating a new institutional dependency.

At the university level, this support path is aligned with the Office of Research and Economic Development (ORED) through the Institute for Interdisciplinary Data Sciences (IIDS), which houses RCDS and positions research computing as core university research infrastructure. RCDS's statewide HPC collaboration (including jointly operated supercomputing resources) and on-campus computing/data-center operations provide the institutional foundation for long-lived, compute-intensive research platforms like WEPPcloud.

### University of Idaho Context References

- IIDS (within ORED; includes RCDS): <https://iids.uidaho.edu/>
- ORED and IIDS context in U of I catalog: <https://catalog.uidaho.edu/university/research/>
- U of I Newsroom (Lemhi statewide HPC collaboration): <https://www.uidaho.edu/newsroom/lemhi-supercomputer>
- RCDS facilities/resources snapshot (statewide and on-prem HPC): <https://www.iids.uidaho.edu/docs/RCDS-Facilities-Resources-2025.pdf>

---

## Cost Summary

| Item | Unit Cost | Qty | Total |
|------|-----------|-----|-------|
| SuperServer 621P-TR (fully configured) | $21,391.50 | 2 | **$42,783.00** |

---

## Summary

- **The software is ready.** WEPPcloud is a mature, containerized, production platform actively used by BAER teams, federal agencies, researchers, and the public. Its worker-pool architecture scales horizontally — adding servers increases simulation throughput with no code changes.
- **The data is ready.** The entire St. Joe River Basin has been delineated: 56 watersheds, 134,033 hillslopes, 151,121 channels, covering over 411,000 hectares. Modeling is blocked solely on compute capacity.
- **Current infrastructure is insufficient.** The existing servers provide ~47,000 Passmark of compute behind an NFS bottleneck that adds up to 8x overhead on the small-file I/O that dominates WEPP modeling workloads.
- **Dedicated local storage is essential.** Benchmarked NFS penalties make basin-scale calibration (which requires full-basin runs for every parameter iteration) impractical on current infrastructure.
- **Redundancy protects mission-critical operations.** BAER teams depend on WEPPcloud during fire season. A single point of failure is unacceptable for a service supporting emergency response.
- **The investment extends beyond I-CREWS.** For $42,783, the project gains approximately 4x the compute throughput, eliminates the storage bottleneck, and establishes redundancy — enabling the St. Joe basin calibration now, with a clear transition path to WEPPcloud production or RCDS general-purpose compute after the project concludes. The hardware serves I-CREWS today and the university's broader research mission long-term.
