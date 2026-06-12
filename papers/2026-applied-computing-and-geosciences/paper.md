# WEPPcloud: an on-demand microservices architecture for production-scale interactive watershed modeling

> Working draft for Applied Computing & Geosciences — Application article.
> Drafting in markdown; migrate to els-cas LaTeX (cas-sc.cls) once content is
> nailed down. Constraints: 5,000 words body, 250-word abstract, 1–7 keywords,
> numbered sections, numeric [n] references, SI units.
> `[N]`/`[X]` markers are placeholders awaiting telemetry/benchmark numbers.

**Roger Lew^a,\*, Mariana Dobre^b, Anurag Srivastava^b, Erin S. Brooks^b, Peter R. Robichaud^c**

^a Department of Design and Environments, University of Idaho, Moscow, ID, USA
^b Department of Soil and Water Systems, University of Idaho, Moscow, ID, USA
^c USDA Forest Service, Rocky Mountain Research Station, Moscow, ID, USA

\* Corresponding author: rogerlew@uidaho.edu

## Abstract

WEPPcloud is an online platform that couples watershed-scale erosion and
hydrology models — foremost the Water Erosion Prediction Project (WEPP),
alongside RUSLE, RHEM, WATAR, and debris-flow models —
with automated acquisition of terrain, soil, land cover, and climate data to
support land-management decision making, including post-wildfire emergency
response. The implementation
described in 2022 served early adopters well but was naive about production
demand: larger watersheds, fire-season surges from Burned Area Emergency
Response (BAER) teams, scenario-intensive treatment planning, and programmatic
access. This paper traces the platform's evolution into tightly integrated,
containerized, on-demand microservices, organized around the operational
lessons that shaped each design decision.
(1) Long-running legacy FORTRAN model executions are isolated from interactive
requests through Redis-backed job queues. (2) Portable, file-backed run state —
retained from the original design and hardened with distributed locking — lets
every run be forked, archived, and re-executed. (3) Model outputs are
published as self-describing columnar Parquet tables with embedded units
metadata and queried through a declarative, safety-bounded analytics service
that also serves AI agents. (4) Performance-critical components are
purpose-built: Rust geoprocessing kernels for watershed delineation and
abstraction, Go services for real-time status streaming. These foundations
enable scenario fan-out — one user action clones and selectively reruns
treatment scenarios — and interactive WebGL visualization of multi-scenario
results. We demonstrate a post-fire treatment-planning workflow and report
production evidence: [N] runs across [N] watersheds, fire-season demand
surges, and queue and worker utilization. The lessons offer a
transferable guide for operationalizing legacy environmental models as
responsive, scalable web services.

<!-- ACG limit: 250 words. -->

## Keywords (1–7)

watershed modeling; microservices; decision support; soil erosion; WEPP;
cyberinfrastructure; interactive visualization

<!-- draft — prune/reorder; ACG says avoid multi-word keywords where possible -->

## Highlights (3–5 bullets, ≤85 chars each)

- Operational lessons drove WEPPcloud's evolution to on-demand microservices
- Job queues isolate long-running legacy FORTRAN models from interactive requests
- Portable file-backed run state lets any run be forked, archived, and re-executed
- Self-describing Parquet outputs feed a declarative query API for humans and AI
- One user action clones and selectively reruns post-fire treatment scenarios

<!-- Alternates if any bullet is cut:
- Rust geoprocessing kernels make basin-scale watershed delineation interactive
- Production evidence: [N] runs, fire-season surges, queue/worker utilization
Submit as separate file with "highlights" in the filename. -->

---

## 1. Introduction (~600 w)

<!-- Prototype-to-production gap; demand growth since 2022; numbered
contributions list. AI-prototyping hook lives here, not in abstract. -->

## 2. Operational lessons and design principles (~500 w)

<!-- Requirements as discovered in operation, not assumed a priori. Two
flavors: decisions the original design got right and hardened (file-backed
run state) vs. decisions operation forced (queue isolation, columnar
interchange, native kernels). Drafting convention for sections 3–6: open each
with the operational pressure/incident that motivated the design, then the
design, then observed behavior.
TODO(Roger): inventory of actual operational incidents/pressures 2022–2026 —
what strained or failed (sync requests under load? flat-file parsing cost?
status polling? geoprocessing wall times?). Lessons must be real, not
retrofitted rationale.
Source material: i-crews/st_joe/weppcloud-architecture-overview.md
"Infrastructure Requirements" table — persistent services, low-latency
dispatch, local storage (millions of small files; NFS/Lustre degrade),
unrestricted egress for data APIs, horizontal worker scaling: "not
preferences — consequences of a persistent, interactive modeling platform." -->

## 3. On-demand microservices architecture (~800 w)

<!-- Source material: docs/projects/i-crews/st_joe/weppcloud-architecture-overview.md
"Why HPC and WEPPcloud are a Poor Match" — the why-bespoke argument (batch
queuing vs real-time, always-on services, small-file random I/O vs Lustre,
FORTRAN+Python+Rust dependency glue vs module systems). 20+ container topology,
~1.5M LOC, effectively single-developer-maintained. -->

**Figure 1.** WEPPcloud runtime topology. Requests from human operators and
JWT-authenticated AI agents route through the core web stack; the asynchronous
worker pool executes model simulations; Postgres, Redis, and local storage
maintain run state. (Redraw as vector art for submission; ASCII basis below
from `docs/projects/i-crews/st_joe/weppcloud-architecture-overview.md`.)

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
 │             │──http      └───────────────────────┘     |    ‖    :
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

<!-- Figure adaptations from source: "OpenClaw" genericized to "AI Agent".
Open decisions for the vector redraw: (a) add Caddy reverse-proxy edge in
front of services (present in production, omitted in source diagram);
(b) include rq-worker-batch pool? (c) keep f-esri/weppcloudr/cap.js service
containers or collapse to "sandboxed service containers" for figure economy. -->

## 4. State model and job orchestration (~550 w)

## 5. Data interchange and declarative analytics (~650 w)

## 6. Performance substrate (~400 w)

## 7. On-demand scenario computation and analytics surfaces (~650 w)

## 8. Production evidence (~550 w)

<!-- post-fire workflow case study as running example; telemetry panels.
Scale datapoint (verify current numbers at drafting): St. Joe basin-scale
prep — 56 watersheds, 134,033 hillslopes, 151,121 channel segments; >100x
area of the 2013–2018 Fernan effort (~3,800 ha); enabled by Rust delineation
(weppcloud-wbt) within the last year. Strong "larger watersheds" evidence. -->

## 9. Discussion: transferable lessons, limitations, future work (~300 w)

## Declaration of generative AI use

<!-- Required by ACG; appears in published article before references.
Draft deliberately — covers Claude/Codex manuscript-prep workflow. -->

## CRediT author statement

<!-- TODO -->

## Data availability

<!-- ACG Option C: deposit + cite/link. wepppy + companion repos + Zenodo DOIs
+ reproducible example run. -->

## References

<!-- numeric [n], order of appearance; pull from research/annotated-bibliography.md -->
