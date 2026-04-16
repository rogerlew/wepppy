# WEPPcloud Architecture Overview — St. Joe Basin

**Date:** April 2026
**Project:** I-CREWS / St. Joe River Basin Watershed Modeling
**Context:** Compute infrastructure planning for AI-driven basin calibration

---


## Why HPC and WEPPcloud are a Poor Match

To understand the friction, we have to look at the difference between how HPC clusters are designed versus how modern web platforms operate.

**Batch Queuing vs. Real-Time Needs**: HPC clusters rely on job schedulers (like Slurm or PBS). A user submits a job, it sits in a queue, and it runs when resources free up. WEPPcloud, conversely, is an on-demand web service utilized by stakeholders—including fire response teams (BAER) and land managers—who require immediate, interactive modeling for time-sensitive environmental conditions. Waiting in a cluster queue during an active wildfire response is a non-starter.

**The "Always-On" Architecture**: WEPPcloud's codebase relies heavily on persistent, "always-on" web technologies: Redis pub/sub networks, Go-based WebSockets, and sub-second latency browser dashboards. HPC compute nodes are strictly locked down; you generally cannot open web ports, expose continuous HTTP traffic to the public, or run persistent daemon services on them.

**Storage I/O Bottlenecks**: The wepppy repository uses a "NoDb" architecture, utilizing file-backed singleton controllers that serialize thousands of small JSON files and cache them in Redis. HPC clusters typically use parallel file systems (like Lustre) designed for massive, sequential data reads/writes. They often perform terribly with the rapid, random I/O required by web applications, which run much better on local NVMe SSDs found in dedicated workstations.

**Dependency Management**: The WEPP system is a complex glue of legacy FORTRAN 77 executables, modern Python web services, and Rust-accelerated tooling. Deploying and maintaining this specific web stack via standard Docker containers on a dedicated Linux box is straightforward. Attempting to shoehorn it into an HPC's strict module system and restrictive container environment (e.g., Apptainer/Singularity) is notoriously difficult and time-consuming.


## WEPPcloud Platform Topology

WEPPcloud is a containerized web-application and modeling platform. This figure illustrates the system's microservices architecture, highlighting how requests from both human users and AI agents are authenticated and routed through the core web stack. It demonstrates the structural separation between the lightweight user-facing web services, the asynchronous worker pool handling the intensive WEPP simulations, and the centralized storage systems (Postgres, Redis, and Local Storage) that maintain run data.

```
 DATA BUS LEGEND
 ---------------
 ···  Postgres
 ooo  Redis
 ───  Local Storage


    OPERATORS                  WEPPCLOUD CORE STACK                            STORAGE
 ───────────────            ─────────────────────────                    ─────────────────────
                                                          DATA BUSES
 ┌─────────────┐            ┌───────────────────────┐                    ┌───────────────────┐
 │    Human    │            │   weppcloud (Flask)   ├───▶ | o▶ o    ·····│     Postgres      │
 │ Web Browser │──http────▶ │   UI · Auth · NoDb    │···· | ·· o ·▶ :    │   users · runs    │
 └─────────────┘  /jwt      └───────────┬───────────┘     |    o    :    └───────────────────┘
                    │                   │                 |    o    :
                    │       ┌───────────┴───────────┐     |    o    :    ┌───────────────────┐
                    ├─────▶ │  rq-engine (FastAPI)  ├───▶ | o▶ oooo : ooo│       Redis       |
                    │       │  tasks · state · jobs │···· | ·· o ·▶ :    │  rq · job status  |
                    │       └───────────┬───────────┘     |    o    :    │ nodb locks/cache  |
                    │                   │                 |    o    :    └───────────────────┘
                    │       ┌───────────┴───────────┐     |    o    :           
                    │       |    rq-worker pool     ├───▶ |    o    :
                    │       |  data acquisition /   │oooo | o▶ o    :
                    │       |  processing (Rust)    │···· | ·· o ·▶ :
                    |       |  subprocess (WEPP)    |     |    o    :
                    |       └──┬────┬───────────────┘     |    o    :
                    │          |   http                   |    o    :
                    |      docker   |                     |    o    :
                    |        exec   └-▶ EXTERNAL APIS     |    o    :
                    |          |                          |    o    :
                    |          └-▶ SERVICE CONTAINERS     |    o    :    ┌───────────────────┐
                    │                                     ├──────────────│  Local Storage    │
                    │       ┌───────────────────────┐     |    o    :    │  Run Data         │
                    ├─────▶ │  query-engine         ├───▶ |    o    :    │  ├ *.nodb         │
                    │       │  Analytics · MCP API  │oooo | o▶ o    :    │  ├ **.parquet     │
                    │       └───────────────────────┘     |    o    :    │  ├ wepp           │
                    │                                     |    o    :    │  ├ ...            │
                    │       ┌───────────────────────┐     |    o    :    └───────────────────┘
 ┌─────────────┐    ├─────▶ │  browse (Starlette)   ├───▶ |    o    : 
 │  AI Agent   │    │       │  UI · files API       │oooo | o▶ o    :
 │  OpenClaw   │──http      └───────────────────────┘     |    o    : 
 |    (WIP)    |  /jwt                                    |    o    : 
 └─────────────┘    │                                     |    o    :
                    │              WEBSERVICES            |    o    :
                    │       ─────────────────────────     |    o    :
                    │       ┌───────────────────────┐     |    o    :
                    ├─────▶ │         dtale         ├───▶ | o▶ o    :
                    |       |      (sandboxed)      │···· | ·· o ·▶ :
                    │       └───────────────────────┘     |    o
                    │       ┌───────────────────────┐     |    o
                    ├─wss─▶ │       status (Go)     ├───▶ | o▶ o
                    │       └───────────────────────┘     |    o
                    │       ┌───────────────────────┐     |    o
                    ├─wss─▶ │     preflight  (Go)   ├───▶ | o▶ o
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

---

## AI-Driven Calibration Workflow

Calibrating the St. Joe basin (134,033 hillslopes, 56 watersheds) requires iterative full-basin simulation runs. Each parameter adjustment must propagate through the entire channel network to evaluate watershed-scale effects. This is not feasible manually at this scale.

### Why brute-force parameter sweeps are not feasible

The naive approach to calibration is batch parameter sweeps: generate a grid of parameter combinations, submit them all as independent jobs, and pick the best result. This is the kind of workload that fits naturally on an HPC batch scheduler. It does not work here for two reasons:

**Combinatorial explosion.** WEPP calibration involves soil erodibility, hydraulic conductivity, effective saturated conductivity, rill spacing, critical shear, and management parameters — per soil type, per land use class, across 56 watersheds with heterogeneous geology. Even a coarse 5-value sweep across 8 parameters produces 390,625 combinations. Each combination requires a full-basin run of 134,033 hillslopes. The compute cost of exhaustive search is intractable at basin scale.

**Equifinality.** In watershed hydrology, many different parameter sets produce statistically indistinguishable fits to observed data (Beven, 2006). A brute-force sweep that minimizes an objective function (NSE, PBIAS) will return dozens or hundreds of "equally good" parameter sets with no basis for choosing among them. The resulting model is not calibrated — it is curve-fit without physical constraint.

Resolving equifinality requires an agent that can reason about intermediate outputs: Does the seasonal pattern of baseflow match? Are sediment peaks arriving at the right time relative to storm events? Is the snow accumulation/melt timing physically plausible for these elevations? These are diagnostic judgments that inform the next parameter adjustment. They cannot be encoded as a scalar objective function and batch-submitted.

This is why the calibration workflow is iterative hyothesis driven and orchestrated by AI agents rather than batch-submitted.

---

## AI Agent Integration

WEPPcloud is designed to be operated by both human users and autonomous AI agents. AI agents are first-class operators — they authenticate with scoped JWT tokens and interact with the same service APIs that human users do.

The planned agent operator is OpenClaw/Hermes pen-source autonomous AI assistant. Agent runs external to weppcloud on their own development box with sandboxed tool execution (bash, file I/O, HTTP), a skills system for domain-specific workflows, and multi-agent session routing. It connects to external services via HTTP and drives autonomous workflows without human intervention.

### How an OpenClaw agent operates WEPPcloud

An OpenClaw agent authenticates to the WEPPcloud stack via JWT and interacts with two service APIs:

**rq-engine (FastAPI)** — the operational interface:
- Create runs
- Query run state/parameters
- Submit tasks (e.g. run WEPP)
- Poll job status and completion
- Cancel and re-submit runs with modified parameters

**query-engine (Starlette)** — the analytical interface:
- Query the dataset catalog for a run (hillslope outputs, channel outputs, climate summaries)
- Execute DuckDB SQL against Parquet-formatted run results
- Validate queries before execution
- Retrieve prompt templates with embedded schema context

**browse - files (Starlette)** — file access:
- Designed as a first class OpenAPI interface for agents
- provide file access

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
