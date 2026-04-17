# WEPPcloud Architecture Overview — St. Joe Basin

**Date:** April 2026
**Project:** I-CREWS / St. Joe River Basin Watershed Modeling
**Context:** Compute infrastructure planning for a dedicated I-CREWS deployment and AI-driven basin calibration

---

## Federal Award Framing for This Topology

This architecture note supports a project-specific infrastructure request, not a request to relieve unrelated WEPPcloud operating demand. During the I-CREWS award period, the intended use is an independent WEPPcloud deployment dedicated to St. Joe calibration, alternative-futures modeling, and access by I-CREWS sites, participants, and partners.

That is the direct-benefit framing required by the Uniform Guidance cost principles as reflected in the current eCFR. [`2 CFR § 200.403(a)`](https://www.ecfr.gov/current/title-2/section-200.403) requires allowable costs to be necessary and reasonable for the performance of the Federal award. [`2 CFR § 200.405(a)(1)`](https://www.ecfr.gov/current/title-2/section-200.405) states that a cost is allocable when it is incurred specifically for the Federal award. Conversely, [`2 CFR § 200.405(c)`](https://www.ecfr.gov/current/title-2/section-200.405) generally prohibits charging costs allocable to one Federal award to another award, while preserving the ability to shift costs that are allowable under two or more awards under governing statutes, regulations, or award terms. That is why this request is not framed as shifting unrelated WEPPcloud operating costs onto I-CREWS. Standard institutional accounting controls would still need to satisfy the consistent-treatment and no-double-charge factors in [`2 CFR § 200.403(c)-(f)`](https://www.ecfr.gov/current/title-2/section-200.403).

If later mixed benefit must be recognized because of the interrelationship of the work, [`2 CFR § 200.405(d)`](https://www.ecfr.gov/current/title-2/section-200.405) allows allocation on a proportional or otherwise reasonable documented basis. Because the requested asset is server equipment, procurement approval and documentation should also be handled consistent with [`2 CFR § 200.407`](https://www.ecfr.gov/current/title-2/section-200.407) and [`2 CFR § 200.439`](https://www.ecfr.gov/current/title-2/section-200.439), with treatment depending on whether the asset is `general purpose equipment` or `special purpose equipment` as defined in [`2 CFR § 200.1`](https://www.ecfr.gov/current/title-2/section-200.1). Any later reuse, retention, or disposition of the servers would also remain subject to [`2 CFR § 200.313`](https://www.ecfr.gov/current/title-2/section-200.313) and the applicable award terms. For this request, the detailed classification and approval path is documented in [procurement-request.md](procurement-request.md).

Capacity building is relevant, but secondary. NSF's EPSCoR RII Track-1 program explicitly ties awards to research-driven improvements in physical and cyber infrastructure and to research/capacity-building activities that increase jurisdictional R&D competitiveness. In this document, that language is used to explain program fit for an I-CREWS-wide modeling asset, not to replace the direct-benefit allocability case above. See the official NSF [RII Track-1 program page](https://www.nsf.gov/funding/opportunities/rii-track-1-epscor-research-infrastructure-improvement-program-track-1) and current Track-1 [solicitation](https://www.nsf.gov/funding/opportunities/rii-track-1-epscor-research-infrastructure-improvement-program-track-1/503429/nsf23-582/solicitation).


## Why HPC and WEPPcloud are a Poor Match

To understand the friction, we have to look at the difference between how HPC clusters are designed versus how modern web platforms operate.

**Batch Queuing vs. Real-Time Needs**: HPC clusters rely on job schedulers (like Slurm or PBS). A user submits a job, it sits in a queue, and it runs when resources free up. WEPPcloud, conversely, is an on-demand web service utilized by stakeholders including I-CREWS participants, partner sites, and land managers. The shared public deployment also serves BAER teams, which illustrates current contention on the existing service but is not the cost basis for this request. Waiting in a cluster queue during an active calibration session or other time-sensitive modeling window is a non-starter.

**The "Always-On" Architecture**: WEPPcloud's codebase relies heavily on persistent, "always-on" web technologies: Redis pub/sub networks, Go-based WebSockets, and sub-second latency browser dashboards. HPC compute nodes are strictly locked down; you generally cannot open web ports, expose continuous HTTP traffic to the public, or run persistent daemon services on them.

**Storage I/O Bottlenecks**: The wepppy repository uses a "NoDb" architecture, utilizing file-backed singleton controllers that serialize thousands of small JSON files and cache them in Redis. HPC clusters typically use parallel file systems (like Lustre) designed for massive, sequential data reads/writes. They often perform terribly with the rapid, random I/O required by web applications, which run much better on local NVMe SSDs found in dedicated workstations.

**Dependency Management**: The WEPP system is a complex glue of legacy FORTRAN 77 executables, modern Python web services, and Rust-accelerated tooling. Deploying and maintaining this specific web stack via standard Docker containers on a dedicated Linux box is straightforward. Attempting to shoehorn it into an HPC's strict module system and restrictive container environment (e.g., Apptainer/Singularity) is notoriously difficult and time-consuming.


## WEPPcloud Platform Topology

WEPPcloud is a containerized web-application and modeling platform. This figure illustrates the system's microservices architecture, highlighting how requests from both human users and AI agents are authenticated and routed through the core web stack. It demonstrates the structural separation between the lightweight user-facing web services, the asynchronous worker pool handling the intensive WEPP simulations, and the centralized storage systems (Postgres, Redis, and Local Storage) that maintain run data.

```
 DATA BUS LEGEND
 ---------------
 ···  Postgres
 ═══  Redis
 ───  Local Storage


    OPERATORS                  WEPPCLOUD CORE STACK                            STORAGE
 ───────────────            ─────────────────────────                    ─────────────────────
                                                          DATA BUSES
 ┌─────────────┐            ┌───────────────────────┐                    ┌───────────────────┐
 │    Human    │            │   weppcloud (Flask)   ├───▶ | ═▶ ‖    ·····│     Postgres      │
 │ Web Browser │──http────▶ │   UI · Auth · NoDb    │···· | ·· ‖ ·▶ :    │   users · runs    │
 └─────────────┘  /jwt      └───────────┬───────────┘     |    ‖    :    └───────────────────┘
                    │                   │                 |    ‖    :
                    │       ┌───────────┴───────────┐     |    ‖    :    ┌───────────────────┐
                    ├─────▶ │  rq-engine (FastAPI)  ├───▶ | ═▶ ‖═══ : ═══│       Redis       |
                    │       │  tasks · state · jobs │···· | ·· ‖ ·▶ :    │  rq · job status  |
                    │       └───────────┬───────────┘     |    ‖    :    │ nodb locks/cache  |
                    │                   │                 |    ‖    :    └───────────────────┘
                    │       ┌───────────┴───────────┐     |    ‖    :           
                    │       |    rq-worker pool     ├───▶ |    ‖    :
                    │       |  data acquisition /   │oooo | ═▶ ‖    :
                    │       |  processing (Rust)    │···· | ·· ‖ ·▶ :
                    |       |  subprocess (WEPP)    |     |    ‖    :
                    |       └──┬────┬───────────────┘     |    ‖    :
                    │          |   http                   |    ‖    :
                    |      docker   |                     |    ‖    :
                    |        exec   └-▶ EXTERNAL APIS     |    ‖    :
                    |          |                          |    ‖    :
                    |          └-▶ SERVICE CONTAINERS     |    ‖    :    ┌───────────────────┐
                    │                                     ├──────────────│  Local Storage    │
                    │       ┌───────────────────────┐     |    ‖    :    │  Run Data         │
                    ├─────▶ │  query-engine         ├───▶ |    ‖    :    │  ├ *.nodb         │
                    │       │  Analytics · MCP API  │oooo | ═▶ ‖    :    │  ├ **.parquet     │
                    │       └───────────────────────┘     |    ‖    :    │  ├ wepp           │
                    │                                     |    ‖    :    │  ├ ...            │
                    │       ┌───────────────────────┐     |    ‖    :    └───────────────────┘
 ┌─────────────┐    ├─────▶ │  browse (Starlette)   ├───▶ |    ‖    : 
 │  AI Agent   │    │       │  UI · files API       │oooo | ═▶ ‖    :
 │  OpenClaw   │──http      └───────────────────────┘     |    ‖    : 
 └─────────────┘  /jwt                                    |    ‖    : 
                    │                                     |    ‖    :
                    │              WEBSERVICES            |    ‖    :
                    │       ─────────────────────────     |    ‖    :
                    │       ┌───────────────────────┐     |    ‖    :
                    ├─────▶ │         dtale         ├───▶ | ═▶ ‖    :
                    |       |      (sandboxed)      │···· | ·· ‖ ·▶ :
                    │       └───────────────────────┘     |    ‖
                    │       ┌───────────────────────┐     |    ‖
                    ├─wss─▶ │       status (Go)     ├───▶ | ═▶ ‖
                    │       └───────────────────────┘     |    ‖
                    │       ┌───────────────────────┐     |    ‖
                    ├─wss─▶ │     preflight  (Go)   ├───▶ | ═▶ ‖
                    │       └───────────────────────┘     |    
                    │       ┌───────────────────────┐     |
                    ├─────▶ │  wmesque2 (FastAPI)   ├───▶ | 
                    │       └───────────────────────┘     |
                    │       ┌───────────────────────┐     |
                    │─────▶ │    metquery (Flask)   ├───▶ |
                    │       └───────────────────────┘     
                    │       ┌───────────────────────┐
                    └─────▶ |    shape-converter    |
                            |   (fully sandboxed)   |
                            └───────────────────────┘    

                                SERVICE CONTAINERS
                            ─────────────────────────
                            ┌───────────────────────┐
                            |     f(ormat)-esri     |
                            └───────────────────────┘      
                            ┌───────────────────────┐
                            |      weppcloudr       |
                            └───────────────────────┘     
                            ┌───────────────────────┐
                            |        cap.js         |
                            └───────────────────────┘     
```

---

## Service Topology

The platform runs as a Docker Compose stack with 20+ containers behind a Caddy reverse proxy. The services relevant to calibration:

| Service | Runtime | Role |
|---------|---------|------|
| **weppcloud** (Flask) | Gunicorn, 4 workers | UI, authentication, NoDb state management, job enqueue |
| **rq-engine** (FastAPI) | Uvicorn | Job submission, polling, cancellation API |
| **query-engine** (Starlette) | Uvicorn | DuckDB analytics over run outputs, MCP API for AI agents |
| **browse** (Starlette) | Gunicorn + Uvicorn | Run output file explorer with diff support |
| **rq-worker** | RQ worker-pool | Executes WEPP simulations, climate processing, soil assignment |
| **rq-worker-batch** | RQ worker-pool | Dedicated queue for batch/calibration workloads |
| **status2** (Go) | Binary | Redis pub/sub → WebSocket fan-out for live job status |
| **redis** | Redis | Job queues (DB 9), NoDb cache (DB 13), distributed locks (DB 0), status channels (DB 2) |

Workers are stateless. They pull jobs from Redis, execute WEPP FORTRAN binaries against run data on local storage, and publish status updates back through Redis. Adding nodes adds workers — no application changes required.

Although the requested hardware is only about 4x current WEPPcloud compute in absolute terms, it is much more significant for I-CREWS specifically. On the shared production service, only about 10% of current compute can be responsibly devoted to St. Joe work without displacing unrelated workloads. On that planning assumption, a dedicated I-CREWS deployment yields roughly 40x more project-usable compute to the award.

---

## Why Basin-Scale Modeling Became Feasible Only Recently

When the original I-CREWS proposal was written, and even a year ago, WEPPcloud did not yet have an owned basin-scale delineation workflow capable of preparing the full St. Joe basin for WEPP. Over the last year, the team implemented ground-up hydrological delineation routines in Rust on top of WhiteboxTools, turning full-basin preparation into an operational workflow.

Full-basin St. Joe execution was also not part of the initial project scope. That basin-scale modeling requirement was added later at the request of the Coeur d'Alene Tribe, an I-CREWS partner. For scale, the 2013-2018 Miles project modeled Fernan Watershed at roughly 3,800 hectares. The St. Joe basin effort now in scope is more than 100x larger in area and requires 56 watersheds, 134,033 hillslopes, and 151,121 channel segments. That is why the infrastructure request is emerging now: the stack can finally prepare the basin, and compute plus storage have become the binding constraints.

---

## AI-Driven Calibration Workflow

Calibrating the St. Joe basin (134,033 hillslopes, 56 watersheds) requires iterative full-basin simulation runs. Each parameter adjustment must propagate through the entire channel network to evaluate watershed-scale effects.

### Why brute-force parameter sweeps are not feasible

The naive approach to calibration is batch parameter sweeps: generate a grid of parameter combinations, submit them all as independent jobs, and pick the best result. This is the kind of workload that fits naturally on an HPC batch scheduler. It does not work here for two reasons:

**Combinatorial explosion.** WEPP calibration involves soil erodibility, hydraulic conductivity, effective saturated conductivity, rill spacing, critical shear, and management parameters — per soil type, per land use class, across 56 watersheds with heterogeneous geology. Even a coarse 5-value sweep across 8 parameters produces 390,625 combinations. Each combination requires a full-basin run of 134,033 hillslopes. The compute cost of exhaustive search is intractable at basin scale.

**Equifinality.** In watershed hydrology, many different parameter sets produce statistically indistinguishable fits to observed data (Beven, 2006). A brute-force sweep that minimizes an objective function (NSE, PBIAS) will return dozens or hundreds of "equally good" parameter sets with no basis for choosing among them. The resulting model is not calibrated — it is curve-fit without physical constraint.

Resolving equifinality requires an agent that can reason about intermediate outputs: Does the seasonal pattern of baseflow match? Are sediment peaks arriving at the right time relative to storm events? Is the snow accumulation/melt timing physically plausible for these elevations? These are diagnostic judgments that inform the next parameter adjustment. They cannot be encoded as a scalar objective function and batch-submitted.

This is why the calibration workflow is iterative hypothesis driven and orchestrated by humans and AI agents rather than batch-submitted. WEPPcloud provides interactive reports and visualizations for humans to understand hydrological processes and APIs for agents to access information.

---

## AI Agent Integration

WEPPcloud already exposes agent-facing operational and analytical interfaces that support human-guided iterative calibration workflows. Agents authenticate with scoped JWT tokens and interact with the same core service surfaces used by human operators.

Current agent-capable behaviors include:
- Replicating runs using the `rq-engine` API
- Troubleshooting and repairing programmatic workflow failures
- Implementing complex hydrological analyses from human expert prompts using agent-facing WEPPcloud APIs
  - [Palisades 2024 Fire - Shrubs Hydrographs](https://github.com/rogerlew/palisades-fire-2024-shrub-hydrographs/blob/main/report_upset_reckoning_hydroshape.pdf)
- Performing hypothesis driven ablation testing to resolve non-parity differences in WEPP-forest outputs across compilation targets
  - Interpreting model code to understand how physical processes are modeled
  - Using subagent workflows to compile and run parity tests on Windows and Linux through SSH
- Following multi-hour procedural workflows with subagents, decision points, and gates
  - weppcloud development extensively uses ExecPlan work-packages that are carried out end-to-end by agents

These capabilities support human-guided calibration today. Fully autonomous basin calibration remains a near-term goal rather than a current production capability.

A near term goal (Summer 2026) is to have autonomous AI agent infrastructure capable of calibrating WEPPcloud watersheds to observed streamflow and sediment delivery. Agents are not expected to be fully autonomous in the 2-month timeframe, but they will have the infrastructure to become more autonomous through close interaction with humans while ablation-testing and calibration protocols are developed. We will start with smaller watersheds that we have previously calibrated before pursuing the larger St. Joe Basin.

Known missing architectural components:
- Knowledge database for agents to form academically sound hypotheses (2 weeks)
- Operational guidance on calibration workflows and gates (2 weeks)
- Multi-agent infra on surplus thin clients (obtained) with communication and orchestration layer (Discord channel shared by Openclaw agents, 2 weeks)

**Important** A planned external agent operator is OpenClaw/Hermes open-source autonomous AI assistant. The agent runs external to weppcloud on its own development box with sandboxed tool execution (bash, file I/O, HTTP), a skills system for domain-specific workflows, and multi-agent session routing. It connects to external services via HTTP and drives autonomous workflows without human intervention.

### How an OpenClaw agent operates WEPPcloud

An OpenClaw agent authenticates to the WEPPcloud stack via JWT and interacts with three service APIs:

**rq-engine (FastAPI)** — the operational interface:
- Create runs
- Query run state/parameters
- Submit tasks (e.g. run WEPP)
- Poll job status and completion
- Cancel and re-submit runs with modified parameters

**query-engine (Starlette)** — the analytical interface:
- Query the dataset catalog for a run (hillslope outputs, channel outputs, climate summaries)
- Execute validated declarative JSON queries against Parquet-formatted run results
- Validate query payloads before execution
- Retrieve prompt templates with embedded schema context

**browse - files (Starlette)** — file access:
- Designed as a first class OpenAPI interface for agents
- Provide file access

The agent uses rq-engine to act and query-engine/browse to observe. The calibration loop is: observe results → formulate hypothesis → modify parameters → submit simulation → observe results → iterate.

---

## Infrastructure Requirements

The calibration workflow imposes specific infrastructure constraints that are inherent to the architecture:

| Requirement | Why |
|-------------|-----|
| **Persistent services** | Flask, rq-engine, query-engine, Redis, and status2 must be running continuously — agents interact with them over hours-long sessions |
| **Low-latency job dispatch** | Workers pull jobs from Redis immediately; no scheduler allocation delay |
| **Local storage** | WEPP I/O is millions of small files per basin run; network filesystems (NFS, Lustre) degrade severely under this pattern |
| **Unrestricted network** | Workers call external data APIs (AWS, SSurgo, Climate Engine, OpenTopography, PRISM) during execution |
| **Horizontal scaling** | More cores = more concurrent hillslope simulations = faster iteration cycles |

These are not preferences — they are consequences of a persistent, interactive modeling platform that serves both human operators and AI agents simultaneously.
