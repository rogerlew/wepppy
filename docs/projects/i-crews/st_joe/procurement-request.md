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

## Asset Lifecycle: I-CREWS and Beyond

During the I-CREWS project period, both servers will be dedicated to St. Joe basin modeling — calibration runs, scenario analysis, and batch simulation workloads that require sustained, high-throughput compute with local storage.

Upon completion of the I-CREWS project, the servers retain full value to the university through two natural transition paths:

- **WEPPcloud production infrastructure.** The current production servers (wepp1, wepp2) are aging Xeon 5120-class hardware. The new servers are a direct upgrade path, capable of replacing the existing production fleet and serving the growing WEPPcloud user base — BAER teams, federal agencies, researchers, and students — with significantly improved capacity and redundancy.
- **RCDS general-purpose compute.** If WEPPcloud's production needs are met through other means, the servers are standard 2U rackmount hardware with no specialized components. They can be redeployed as general-purpose research computing nodes within the university's Research Computing and Data Services infrastructure.

Because WEPPcloud is fully containerized and environment-agnostic, transitioning the servers between these roles requires only configuration changes — no hardware modifications or software rewrites. The same Docker Compose stack that runs St. Joe calibration today can serve public WEPPcloud traffic tomorrow.

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
