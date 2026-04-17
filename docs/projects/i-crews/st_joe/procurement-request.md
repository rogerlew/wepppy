# Server Procurement Request: WEPPcloud Compute Infrastructure for the St. Joe Basin Project

**Date:** March 2026

**Project:** I-CREWS / St. Joe River Basin Watershed Modeling

**Requested by:** WEPPcloud Development Team

**Funding Source:** I-CREWS Grant

**Total Cost:** $42,783.00 (two servers at $21,391.50 each)

## Approval Snapshot

- **Request:** Approve procurement of two dedicated compute servers for St. Joe basin calibration and scenario modeling.
- **Amount:** **$42,783.00** total.
- **Why now:** The St. Joe basin is already delineated and ready to model; the project is blocked on compute capacity, not software readiness.
- **Why not Lemhi/HPC:** The Lemhi alternative is not a practical project path. The companion analysis estimates approximately **30-42 weeks with 3-4 FTE** and **10x** in engineering labor to make that path production-safe, which is not a reasonable use of I-CREWS time or staffing.
- **Federal cost basis:** This request is framed as a direct I-CREWS cost under [`2 CFR § 200.403`](https://www.ecfr.gov/current/title-2/section-200.403) and [`2 CFR § 200.405`](https://www.ecfr.gov/current/title-2/section-200.405), with equipment treatment and any required approval/documentation to be handled consistent with [`2 CFR § 200.407`](https://www.ecfr.gov/current/title-2/section-200.407) and [`2 CFR § 200.439`](https://www.ecfr.gov/current/title-2/section-200.439).
- **Operational model:** RCDS already supports this class of WEPPcloud infrastructure. Any long-term hosting, operations, or post-award reassignment would remain subject to institutional approval and applicable award/property requirements.
- **If approved:** I-CREWS gains a dedicated local-storage-backed WEPPcloud deployment for St. Joe calibration, scenario analysis, and access by other I-CREWS sites, participants, and partners.
- **Long-term value:** If the equipment is no longer needed for the original I-CREWS purpose, it could later support WEPPcloud production or broader RCDS research infrastructure, subject to award terms, sponsor/pass-through instructions, and [`2 CFR § 200.313`](https://www.ecfr.gov/current/title-2/section-200.313).

---

## Executive Summary

We request the procurement of two Supermicro SuperServer 621P-TR rack servers to serve as compute infrastructure for an independent I-CREWS deployment of WEPPcloud. During the scope of the I-CREWS project, these servers are intended primarily for use by I-CREWS sites, participants, and partners, especially for St. Joe basin calibration, scenario analysis, alternative-futures modeling, and WEPP simulation workloads. They will provide approximately 4x the raw compute capacity of the current infrastructure, include dedicated local storage to eliminate the NFS bottlenecks that currently constrain modeling throughput, and, because the new deployment would be provisioned primarily for I-CREWS rather than shared with unrelated workloads, provide an operational provisioning estimate of roughly 40x more compute capacity available to this award than the status quo.

If and when the equipment is no longer needed for the original I-CREWS purpose, the servers could be transitioned into the university's broader research computing infrastructure — either as permanent WEPPcloud production nodes (replacing or augmenting the aging current hardware) or as general-purpose compute within RCDS (Research Computing and Data Services), as institutional need dictates. Any such transition would remain subject to award terms, sponsor/pass-through instructions, institutional property controls, and [`2 CFR § 200.313`](https://www.ecfr.gov/current/title-2/section-200.313). Because WEPPcloud is containerized and portable, the technical side of redeployment is straightforward even though the approval and property-management path is governed separately.

The WEPPcloud software platform is Technical Readiness Level 9 (TRL). The entire St. Joe basin has already been delineated into 56 tributary watersheds comprising 134,033 hillslopes and 151,121 channel segments. Modeling is waiting on compute capacity. Running all 56 tributaries is a planning target within roughly 1 month of server availability.

---

## Federal Award Allowability and Allocability Basis

This request is written to align with the Uniform Guidance cost principles as reflected in the current eCFR. Under [`2 CFR § 200.403(a)`](https://www.ecfr.gov/current/title-2/section-200.403), allowable costs must be necessary and reasonable for the performance of the Federal award; [`§ 200.403(b)`](https://www.ecfr.gov/current/title-2/section-200.403) requires conformity with the Federal award; and [`§ 200.403(g)`](https://www.ecfr.gov/current/title-2/section-200.403) requires adequate documentation. The remaining [`§ 200.403(c)-(f)`](https://www.ecfr.gov/current/title-2/section-200.403) factors also apply and should be satisfied through institutional accounting controls, consistent direct-cost treatment, GAAP-conformant cost determination where applicable, and avoidance of any double-charging or duplicate cost-sharing treatment.

Under [`2 CFR § 200.405(a)(1)`](https://www.ecfr.gov/current/title-2/section-200.405), a cost is allocable when it is incurred specifically for the Federal award. Accordingly, the requested servers are justified here as project-specific I-CREWS infrastructure for St. Joe calibration, alternative-futures modeling, and access by I-CREWS sites, participants, and partners, not as relief for unrelated WEPPcloud operating demand.

That distinction matters because [`2 CFR § 200.405(c)`](https://www.ecfr.gov/current/title-2/section-200.405) generally prohibits charging a cost allocable to one Federal award to another Federal award. The same subsection also clarifies that this does not preclude shifting costs that are allowable under two or more Federal awards in accordance with governing statutes, regulations, or award terms. If mixed benefit must later be recognized because of the interrelationship of the work, [`2 CFR § 200.405(d)`](https://www.ecfr.gov/current/title-2/section-200.405) requires proportional allocation when those proportions can be determined and otherwise allows allocation on a reasonable documented basis. In practice, that means any later capacity-building benefit that becomes material during the award period should be documented prospectively and allocated using a reasonable method tied to actual benefit received, such as reserved capacity, node-hours consumed, run counts, or storage usage. Later secondary benefit is not a retroactive basis for charging the full purchase to I-CREWS if actual use during the period of performance becomes materially shared. That subsection also states that where equipment is specifically authorized under a Federal award, the costs remain assignable to that award even when the equipment is no longer needed for the original purpose.

Because this procurement is server equipment, approval and documentation should be handled consistent with [`2 CFR § 200.407`](https://www.ecfr.gov/current/title-2/section-200.407) and [`2 CFR § 200.439`](https://www.ecfr.gov/current/title-2/section-200.439), recognizing that prior approval affects allowability only where specifically required and that treatment depends on whether the asset is `general purpose equipment` or `special purpose equipment` as defined in [`2 CFR § 200.1`](https://www.ecfr.gov/current/title-2/section-200.1). Any later use, inventory management, retention, or disposition of the servers would also remain subject to [`2 CFR § 200.313`](https://www.ecfr.gov/current/title-2/section-200.313) and the applicable award terms.

Capacity building is relevant here, but as a supporting program-fit argument rather than the primary cost basis. NSF's EPSCoR RII Track-1 program describes awards as supporting research-driven improvements to physical and cyber infrastructure and human capital development, and states that requested infrastructure investments should complement the proposed research activities and clearly benefit jurisdictional R&D capacity. This request fits that framing because the servers create durable I-CREWS modeling capacity shared across sites and partners while directly enabling the St. Joe research scope. See the official NSF [RII Track-1 program page](https://www.nsf.gov/funding/opportunities/rii-track-1-epscor-research-infrastructure-improvement-program-track-1) and current Track-1 [solicitation](https://www.nsf.gov/funding/opportunities/rii-track-1-epscor-research-infrastructure-improvement-program-track-1/503429/nsf23-582/solicitation).

---

## Asset Classification and Approval Path

For award-planning purposes, the working classification for the proposed servers should be `general purpose equipment` under [`2 CFR § 200.1`](https://www.ecfr.gov/current/title-2/section-200.1), unless the pass-through entity or institutional grants office directs otherwise. The most defensible reading is `general purpose` because the assets are standard rackmount servers and `information technology equipment and systems` are expressly listed in the definition of general purpose equipment. The current draft also contemplates later transition to `RCDS general-purpose compute`, which cuts against representing these servers as assets used only for research or other similar technical activities. This remains a working determination pending sponsor/pass-through/institutional confirmation, and prior-approval requirements remain controlling either way at this unit cost.

Primary intended use during the award period supports allocability under [`2 CFR § 200.405(a)(1)`](https://www.ecfr.gov/current/title-2/section-200.405), but intended dedication does not by itself convert standard IT servers into `special purpose equipment`. During the period of performance, the equipment must also be made available for other federally supported projects when such use would not interfere with the original purpose, consistent with [`2 CFR § 200.313(c)(2)`](https://www.ecfr.gov/current/title-2/section-200.313). Under [`2 CFR § 200.439(b)(1)`](https://www.ecfr.gov/current/title-2/section-200.439), capital expenditures for general purpose equipment are allowable as direct costs only with prior written approval of the Federal agency or pass-through entity. As a practical matter, each server's unit cost (`$21,391.50`) is high enough that prior written approval should be documented explicitly in the award file regardless of any alternative classification argument.

The approval package and retained award file should explicitly document the following:

| Documentation item | What the file should say |
|---|---|
| Necessity and reasonableness | State that the St. Joe basin is already delineated and ready to model; that full-basin calibration and alternative-futures analysis are blocked by compute/storage rather than software readiness; that the full-basin scope was added later at the request of the Coeur d'Alene Tribe, an I-CREWS partner; and that the dedicated deployment is necessary to execute the approved project scope. Cite this request, the technical scale of the basin, the Lemhi infeasibility analysis, and the NFS bottleneck evidence as supporting attachments. |
| Direct charge to I-CREWS | State that the servers will host an independent WEPPcloud deployment for primary use during the award period on St. Joe calibration, scenario analysis, alternative-futures modeling, and access by I-CREWS sites, participants, and partners. Make clear that the charge is not justified as relief for unrelated WEPPcloud demand and that any incidental non-I-CREWS benefit is secondary rather than the charging basis. |
| Material later capacity-building benefit | If broader capacity-building benefit becomes material during the award period rather than remaining incidental, retain a short allocation memo describing when that shift occurred, which activities benefitted, and what allocation method will be used going forward. The memo should tie the chosen method to [`2 CFR § 200.405(a)(2)`](https://www.ecfr.gov/current/title-2/section-200.405) and [`§ 200.405(d)`](https://www.ecfr.gov/current/title-2/section-200.405), using a reasonable documented basis such as reserved capacity, node-hours, run counts, or storage consumption. Make clear that later shared benefit does not retroactively convert the original I-CREWS-specific justification into a general institutional charge. |
| Prior written approval | Retain the written approval from the authorized Federal agency or pass-through official identifying the servers as direct-charged equipment, including quantity (`2`), unit cost (`$21,391.50`), total cost (`$42,783.00`), working classification (`general purpose equipment` unless otherwise directed), and approved project use. If NSF prior approval is required under the award terms, retain the approved budget, award amendment, Research.gov Notification and Request Module record, or other award-specified approval vehicle in the grant file. |
| During-award primary use | Retain deployment records showing that the servers are assigned primarily to the I-CREWS deployment during the award period. Appropriate evidence can include host/deployment names, queue configuration, access policy, project operations notes, and run-accounting or administrative records demonstrating that the servers are being used for the approved I-CREWS modeling scope while still allowing other federally supported use that does not interfere with the original purpose. |
| Post-award reassignment after original purpose is complete | If the servers are later moved to WEPPcloud production or RCDS general-purpose compute, retain a short transition memo stating that the equipment is no longer needed for the purpose for which it was originally required, the date of transition, the new role of the hardware, and the sponsor/pass-through/institutional approvals or disposition instructions relied on. That record should tie the reassignment not only to [`2 CFR § 200.405(d)`](https://www.ecfr.gov/current/title-2/section-200.405) but also to the equipment use, records, inventory, and disposition requirements in [`2 CFR § 200.313`](https://www.ecfr.gov/current/title-2/section-200.313). |

Any later reassignment or disposition is therefore not automatic. It remains subject to award terms, sponsor/pass-through instructions, institutional property controls, and any continuing Federal interest in the equipment under [`2 CFR § 200.313`](https://www.ecfr.gov/current/title-2/section-200.313).

This section is intended to make the approval path concrete. It does not replace sponsor-specific terms and conditions; if the pass-through entity or NSF award terms impose additional approval or property-management requirements, those should control.

---

## WEPPcloud Platform Context

### What WEPPcloud Does

WEPPcloud ([wepp.cloud](https://wepp.cloud)) is a web-based watershed modeling platform built on the USDA Water Erosion Prediction Project (WEPP) model. It enables users to delineate watersheds, assign soils and land cover, configure climate scenarios, and run physically-based erosion and hydrology simulations — all through a browser interface. The platform processes digital elevation models, constructs hillslope profiles, runs FORTRAN-based WEPP simulations for each hillslope and channel segment, and aggregates results at the watershed scale.

WEPPcloud is fully containerized using Docker and Docker Compose, making it portable and configurable for multiple deployment environments — development, staging, and production — with environment-specific configuration managed through composable overlay files. The platform's simulation workload is distributed through a Redis-backed RQ (Redis Queue) worker pool. Workers are stateless processes that pull jobs from the queue and execute WEPP simulations independently, allowing the worker pool to scale horizontally across multiple nodes. Adding a second server doubles the available worker capacity with no changes to application code — new workers simply join the existing queue.

WEPPcloud also supports batch processing of watersheds through its API and task pipeline, enabling automated runs across collections of watersheds with different parameter sets, climate scenarios, or management treatments. This capability is essential for the St. Joe project, where calibration and scenario analysis require systematic runs across all 56 tributary watersheds.

### Existing Operating Context

Outside I-CREWS, WEPPcloud already serves a broad operational and research user base:

- **Federal land managers** (USFS, BLM, NRCS) use the platform for watershed assessment, forest management planning, and environmental impact analysis
- **State agencies** model erosion risk for road construction, timber harvest, and post-fire rehabilitation projects
- **Academic researchers** use WEPPcloud for hydrological studies, climate change impact analysis, and graduate research
- **Educators** use WEPPcloud for classroom exercises in hydrology and erosion science, as well as practitioner training for land management professionals
- **International users** apply the platform to watersheds worldwide for erosion prediction and land management planning

This operating context matters because it explains why St. Joe cannot be run opportunistically on the shared service. During wildfire season, the shared public deployment may prioritize BAER teams for time-sensitive post-fire assessments. At other times, the same infrastructure supports agencies, researchers, and training users. That makes WEPPcloud mature and operationally proven, but it also means only a limited fraction of the existing footprint can be devoted to sustained I-CREWS basin calibration without displacing unrelated work. That shared-service pressure is background context rather than the charging basis for this request.

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

### Why This Request Emerged After Proposal Submission

When the original I-CREWS proposal was written, and even a year ago, WEPPcloud did not yet have an owned basin-scale delineation workflow capable of preparing the full St. Joe basin for WEPP. Since then, the team has implemented ground-up hydrological delineation routines in Rust on top of WhiteboxTools (https://github.com/rogerlew/weppcloud-wbt), turning full-basin preparation into an operational workflow.

Full-basin St. Joe execution was also not part of the initial project scope. That basin-scale modeling requirement was added later at the request of the Coeur d'Alene Tribe, an I-CREWS partner. This is therefore a material change in both technical readiness and project scope, not simply a request for faster hardware. For context, the Miles project (2013-2018) modeled Fernan Watershed at roughly 3,800 hectares. The St. Joe effort now in scope is more than 100x larger in area (411,200 ha) and far larger in hillslope and channel count. The procurement is emerging now because the software stack can finally prepare the basin, and compute plus storage have become the limiting resource.

### Why Basin-Level Calibration Requires Full-Basin Runs

Calibrating the St. Joe basin model is not a matter of tuning individual tributaries in isolation. Upstream flow volume and sediment load directly affect downstream delivery timing and magnitude. A change in hillslope erodibility in an upper tributary alters the sediment supply to every downstream channel segment and ultimately the basin outlet. This means that each calibration iteration requires running the entire basin — all 134,033 hillslopes and 151,121 channels — to evaluate the effect of parameter adjustments on watershed-scale outputs. On current hardware, a single full-basin run is prohibitively slow due to running in a deprioritized batch queue. With the proposed servers, iterative calibration becomes feasible.

### Compute Estimate

On current hardware, a single WEPP hillslope run takes on the order of seconds, but 134,033 hillslopes running through multi-year climate sequences accumulate to hours or days of wall time depending on parallelism. The proposed servers would reduce this by roughly 4x in aggregate throughput and 20% per individual simulation (single-thread improvement), making iterative calibration and scenario analysis practical within research timelines.

In raw hardware terms, the proposed servers are about a 4x increase over current WEPPcloud compute. In project-usable terms, the gain is much larger because resource provisioning is centrally controlled. On the shared production service, only about 10% of current capacity can be reserved for sustained I-CREWS use without commandeering unrelated operations. The proposed two-server deployment would instead be provisioned primarily for I-CREWS during the award period. On that administrative allocation basis, the project would gain on the order of 40x more compute capacity available to this award than it has under the current shared-service arrangement. This is a provisioning and queue-allocation estimate, not a benchmarked end-to-end throughput study.

The RQ worker pool architecture is well-suited to this workload. Hillslope simulations are embarrassingly parallel — each is independent and can be dispatched to any available worker. With 256 cores across two servers (versus 88 today), the worker pool can sustain far higher job concurrency. Combined with WEPPcloud's batch processing capability, which automates the submission and tracking of multi-watershed runs, the proposed infrastructure enables hypothesis-driven small-set systematic parameter sweeps and scenario comparisons across the full St. Joe basin without manual intervention.

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

During the award period, the intended use is an independent WEPPcloud deployment dedicated to St. Joe calibration, alternative-futures analysis, and access for I-CREWS sites, participants, and partners. That service topology exists to support an AI-driven calibration workflow rather than one-shot batch execution. The St. Joe loop is: inspect basin outputs, form a calibration hypothesis, adjust parameters, submit another full-basin run, query the resulting diagnostics, and repeat. That requires always-on services, immediate queue dispatch, persistent run state, and low-latency access to very large numbers of small WEPP files over hours-long working sessions. Dedicated servers match that operating model. Shared infrastructure and HPC-style scheduling are optimized for queued batch jobs; the St. Joe effort requires an interactive modeling platform that can remain online while continuously feeding new work to the worker pool.

### Why Two Servers Are Needed

- RAID 6 arrays on each server provide resilient local storage for active run data before calibration outputs are archived to DataHub.
- Two hosts provide enough compute for an independent WEPPcloud deployment sized primarily for I-CREWS workloads; because that workload is bounded to the award, frontend worker counts and RQ parallelism can be tuned aggressively for project throughput and partner access.
- Dedicated I-CREWS capacity keeps the project on a clean accounting boundary that is separable from unrelated WEPPcloud operations, consistent with the allocability constraints in [`2 CFR § 200.405(c)`](https://www.ecfr.gov/current/title-2/section-200.405).
- The two-node layout supports split-mode operations: one server can prioritize interactive/operational traffic while the other executes long-running calibration and scenario batches, then both can be pooled when maximum throughput is required.
- Planned maintenance and unplanned faults become survivable events: one server can be patched, rebooted, or repaired while the other continues serving the stack and draining queued work.
- If the equipment is later cleared for post-I-CREWS reassignment, these same servers could serve as additional production `rq-worker` nodes, extending WEPPcloud compute throughput without redesigning the application architecture.

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

### Shared Infrastructure Cannot Supply Enough Project-Usable Compute

The current production deployment is a shared resource. From an I-CREWS accounting perspective, that means only a small fraction of existing compute can be practically and responsibly devoted to St. Joe work. Because resource allocation on the shared service is centrally administered, only about 10% of current capacity can be reserved for sustained I-CREWS use without commandeering unrelated operations.

That is why the raw hardware comparison understates the project benefit. The proposed servers are roughly 4x the current WEPPcloud compute footprint in absolute terms, but because the new deployment would be provisioned primarily for I-CREWS they represent an operational provisioning estimate of roughly 40x more compute capacity available to this award than the status quo. This is the difference between occasional opportunistic runs and a sustained basin calibration plus scenario-analysis program. Avoiding cross-project contention on the public deployment is a secondary operational benefit, not the charging basis.

### Redundancy for Service Continuity

An independent I-CREWS deployment still needs service continuity. If one server fails in the middle of a calibration campaign, partner workshop, or scenario production run, the project should not stall entirely.

The second proposed server establishes true redundancy. Because WEPPcloud is containerized, the full application stack — web frontend, API, task queue, and worker pool — can be deployed identically on either server. Either server can independently run the complete I-CREWS WEPPcloud service, so hardware failure, maintenance windows, or OS upgrades do not result in project outages. In normal operation, both servers contribute RQ workers to a shared job queue, effectively doubling simulation throughput. If one server goes offline, the remaining server continues processing without manual intervention — jobs simply take longer as the worker pool is reduced.

For the St. Joe project, this two-node architecture enables parallel modeling: one server can run calibration batch jobs while the other serves interactive users, or both can be pooled together for maximum throughput during intensive calibration cycles.

---

## Lemhi (C3+3) Feasibility Assessment

For the full first-class `rq-worker` integration thought experiment (requirements, blockers, timelines, and costs), see [lemhi-rq-workers.md](lemhi-rq-workers.md).

### Summary Conclusion

Using Lemhi as a direct replacement for WEPPcloud production worker hosts is **not a practical path for this project**. Lemhi is a shared high-performance computing (HPC) system for scheduled research jobs, but WEPPcloud's production worker architecture is designed around always-on service containers, continuously connected queue workers, and run-directory mounts that behave like dedicated infrastructure.

**Simple batching of jobs is also problematic.** Many WEPPcloud RQ tasks are hierarchical: a parent job dynamically enqueues child jobs, records the child ids in job metadata, and uses Redis-backed `depends_on` edges to build multi-stage execution trees for prep, hillslopes, watershed routing, post-processing, interchange, export, and finalization. Running an RQ task function as a standalone Slurm job is therefore not equivalent to running the workflow. The parent task still needs live RQ/Redis access in order to enqueue its descendants, publish status, support cancellation, and advance the job tree.

Even if either the `rq-worker` path or a simpler batch-oriented path were forced into Lemhi, the storage problem would remain. The St. Joe Basin scope still generates extreme small-file and inode pressure, and C3+3 Lustre guidance explicitly warns against that access pattern. At basin scale, an HPC adaptation would therefore still likely require dedicated NAS or other non-Lustre storage engineered around WEPPcloud's file-heavy run directories, which undercuts the premise that Lemhi can replace the dedicated-server procurement cleanly.

Even if the cost and timeline estimates in [lemhi-rq-workers.md](lemhi-rq-workers.md) were wrong by a full order of magnitude, the effort would still carry high delivery risk and remain organizationally non-viable. WEPPcloud is a tightly integrated microservices platform that is effectively supported by a single principal engineer. In that setting, a partial failure or prolonged adaptation effort would consume the same scarce engineering capacity needed to execute St. Joe calibration, maintain production WEPPcloud, and deliver partner-facing project outcomes.

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
Lemhi documentation does not explicitly advertise Docker daemon support for user workloads. In HPC practice, this usually means running containers through Apptainer/Singularity under Slurm. Even if containerized execution is technically possible in adapted form, it would still require material changes to runtime, scheduling, and service-lifecycle assumptions compared with WEPPcloud's Docker Compose worker-host model.

8. **Labor opportunity cost is prohibitive**
The blocking issue is not only technical incompatibility. WEPPcloud is a tightly integrated microservices platform with a Docker Compose topology of 20+ containers and a broader `wepppy` codebase that the project documents elsewhere as roughly 1.5 million lines of code. In practice, this remains an effectively single-developer-maintained system. Making Lemhi useful would therefore mean diverting scarce engineering time away from St. Joe calibration, model improvements, and partner-facing delivery into an HPC adaptation project touching queue semantics, storage contracts, container runtime assumptions, network boundaries, and operational recovery paths. Even if that work were technically possible, the opportunity cost is too high for this award.

### Practical Implication for This Procurement

Lemhi is not a useful path for the St. Joe WEPPcloud deployment. The barrier set is too large, and the engineering opportunity cost to make it even partially workable is not justified for this award. This is especially important because the stack is both large and tightly integrated: adapting it to HPC semantics would become its own substantial software project rather than a deployment task. It is not a drop-in host for the WEPPcloud production worker stack needed for reliable St. Joe calibration/scenario throughput and continuity for the independent I-CREWS deployment. The dedicated server procurement remains the correct architecture-aligned path.

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

The 3.9x aggregate compute improvement, combined with the elimination of NFS I/O penalties (up to 8x on small-file writes), translates to an effective throughput improvement well in excess of 4x for WEPPcloud's modeling workload. Separately, because the shared production service can reserve only about 10% of its current capacity for sustained I-CREWS use, the dedicated two-server deployment yields an operational provisioning estimate of roughly 40x more compute capacity available to this award than the status quo.

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

During the I-CREWS project period, both servers are intended for primary use on St. Joe basin modeling — calibration runs, scenario analysis, and batch simulation workloads that require sustained, high-throughput compute with local storage. That direct project use is the primary allocability basis under [`2 CFR § 200.405(a)(1)`](https://www.ecfr.gov/current/title-2/section-200.405). Consistent with [`2 CFR § 200.313(c)(2)`](https://www.ecfr.gov/current/title-2/section-200.313), that primary use does not foreclose other federally supported use when such use would not interfere with the original purpose and is permitted by the award terms.

Upon completion of the I-CREWS project, the servers may retain value to the university through two natural transition paths. That later lifecycle value is secondary to the project-specific justification above and is informed by [`2 CFR § 200.405(d)`](https://www.ecfr.gov/current/title-2/section-200.405), which states that when equipment is specifically authorized under a Federal award, the costs remain assignable to the award even when the equipment is no longer needed for the original purpose. Any actual reassignment would occur only if the equipment is no longer needed for the original project purpose and only in accordance with sponsor/pass-through instructions, institutional property controls, and any continuing Federal interest described in [`2 CFR § 200.313`](https://www.ecfr.gov/current/title-2/section-200.313).

- **WEPPcloud production infrastructure.** The current production servers (wepp1, wepp2) are aging Xeon 5120-class hardware. If post-award reassignment is approved, the new servers are a direct upgrade path capable of replacing or augmenting the existing production fleet.
- **RCDS general-purpose compute.** If WEPPcloud's production needs are met through other means and the equipment is cleared for reassignment, the servers are standard 2U rackmount hardware with no specialized components. They could be redeployed as general-purpose research computing nodes within the university's Research Computing and Data Services infrastructure.

Because WEPPcloud is fully containerized and environment-agnostic, the technical work required to redeploy the servers between these roles is modest. That technical portability does not change the need to satisfy sponsor/pass-through/institutional approval, property-record, inventory, and disposition requirements before reassignment.

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

WEPPcloud's compute operations are not a one-off arrangement. Over the entire life of `wepp.cloud` (8+ years), the platform has benefited from RCDS operations, maintenance, and hosting support. This procurement therefore extends an established operating model rather than creating a new institutional dependency.

At the university level, this support path is aligned with the Office of Research and Economic Development (ORED) through the Institute for Interdisciplinary Data Sciences (IIDS), which houses RCDS and positions research computing as core university research infrastructure. RCDS's statewide HPC collaboration and on-campus computing/data-center operations provide the institutional foundation for long-lived, compute-intensive research platforms like WEPPcloud. That institutional context is operational background showing there is an existing home for rack space, systems administration, and stewardship if the purchase is approved; it is not the primary allocability basis for charging the servers to I-CREWS.

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

## Federal Regulation References

- [`2 CFR § 200.403`](https://www.ecfr.gov/current/title-2/section-200.403) — Factors affecting allowability of costs
- [`2 CFR § 200.405`](https://www.ecfr.gov/current/title-2/section-200.405) — Allocable costs
- [`2 CFR § 200.313`](https://www.ecfr.gov/current/title-2/section-200.313) — Equipment use, management, and disposition
- [`2 CFR § 200.407`](https://www.ecfr.gov/current/title-2/section-200.407) — Prior written approval
- [`2 CFR § 200.439`](https://www.ecfr.gov/current/title-2/section-200.439) — Equipment and other capital expenditures
- [`2 CFR § 200.1`](https://www.ecfr.gov/current/title-2/section-200.1) — Definitions, including general purpose equipment and special purpose equipment

---

## Summary

- **The software is ready.** WEPPcloud is a mature, containerized, production platform with a horizontally scalable worker-pool architecture. Adding servers increases simulation throughput with no code changes.
- **The data is ready.** The entire St. Joe River Basin has been delineated: 56 watersheds, 134,033 hillslopes, 151,121 channels, covering over 411,000 hectares. That basin-scale readiness only became possible after the recent Rust-on-WhiteboxTools delineation work; modeling is now blocked on compute capacity.
- **Current infrastructure is insufficient.** The existing servers provide ~47,000 Passmark of compute behind an NFS bottleneck that adds up to 8x overhead on the small-file I/O that dominates WEPP modeling workloads.
- **The project-specific gain is much larger than the raw hardware delta.** The purchase is about 4x current WEPPcloud compute in absolute terms, but because shared-service resource allocation is centrally controlled and only about 10% of current capacity can be reserved for sustained I-CREWS use, the proposed deployment provides an operational provisioning estimate of roughly 40x more compute capacity available to this award.
- **Dedicated local storage is essential.** Benchmarked NFS penalties make basin-scale calibration (which requires full-basin runs for every parameter iteration) impractical on current infrastructure.
- **The federal cost basis is documented.** The request is framed as a direct, award-specific cost under [`2 CFR § 200.403`](https://www.ecfr.gov/current/title-2/section-200.403) and [`2 CFR § 200.405`](https://www.ecfr.gov/current/title-2/section-200.405), with equipment treatment and any required approval/documentation aligned to [`2 CFR § 200.407`](https://www.ecfr.gov/current/title-2/section-200.407) and [`2 CFR § 200.439`](https://www.ecfr.gov/current/title-2/section-200.439).
- **The investment extends beyond I-CREWS, but that is secondary.** For $42,783, the project gains approximately 4x raw compute throughput, an operational provisioning estimate of roughly 40x more compute capacity available to this award, and elimination of the storage bottleneck for an independent I-CREWS deployment now. Any later transition to WEPPcloud production or RCDS general-purpose compute would follow a separate, documented post-award path under [`2 CFR § 200.313`](https://www.ecfr.gov/current/title-2/section-200.313) and the applicable award terms.
