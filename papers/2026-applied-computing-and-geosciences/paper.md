# Operating an evolving watershed-modeling service: architecture and provenance lessons from WEPPcloud

> Working draft for Applied Computing & Geosciences — Application article.
> Scope revised 2026-09-21: [operations and provenance](01_devops_and_provenance.md).
> Feature methods move to the [companion paper](../2026-weppcloud-scenarios-and-contrasts/00_planning.md).
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
WEPPcloud supports interactive watershed modeling through automated acquisition
of environmental data, execution of legacy physics models, and analysis of
hydrology and erosion outputs. Operating this service creates two related
challenges: maintaining responsive workflows as demand and software evolve, and
establishing which software, parameters, and data produced a scientific result.
Interactive changes and selective reruns make provenance and reproducibility
substantially more challenging.
A project may span multiple deployments and retain inputs prepared under earlier
revisions. This paper examines operational lessons since the platform's 2022
description, focusing on asynchronous execution, portable file-backed state,
columnar data interchange, and deployment management. Bare-metal Kubernetes and
GitOps experience provides a setting for examining runtime boundaries, storage
constraints, and controlled software promotion. We distinguish deployment history
from execution provenance and examine what is required to identify the actual
dependencies of retained results. For interactive jobs, the provenance goal is
to identify the executing container and retrieve corresponding source through
whole-stack version metadata. The evaluation will combine a representative
watershed workflow with retained operational measurements [evidence pending].
We then describe a proposed complementary backend for declarative experiments,
executed as image-digest-pinned Kubernetes Jobs with enforced pipeline dependencies
and cryptographic tracking. This backend would preserve WEPPcloud's on-demand user experience while
providing a separate path for stricter replay guarantees. Its implementation and
replay evaluation remain future work. The central lesson is that reproducible
infrastructure and reproducible scientific executions require related but
distinct records and validation.

<!-- Working abstract, not submission-ready: resolve the evidence placeholder
and tense after evaluation. Do not present proposed replay as demonstrated. -->

## Keywords (1–7)

watershed modeling; microservices; decision support; soil erosion; WEPP;
cyberinfrastructure; provenance

<!-- draft — prune/reorder; ACG says avoid multi-word keywords where possible -->

## Highlights (3–5 bullets, ≤85 chars each)

- Operational lessons shape an evolving interactive watershed-modeling service
- Asynchronous execution separates long simulations from interactive requests
- Deployment history and scientific execution provenance need distinct records
- Mixed-version projects motivate tracking the inputs each execution consumes
- A proposed declarative backend complements on-demand modeling

<!-- Reassess highlights after evaluation; submit as a separate file. -->

## 1. Introduction (~550 w)

<!-- Prototype-to-production gap; demand growth since 2022; numbered
contributions list. AI-prototyping hook lives here, not in abstract. -->

## 2. Operational lessons and design principles (~500 w)

<!-- Requirements as discovered in operation, not assumed a priori. Two
flavors: decisions the original design got right and hardened (file-backed
run state) vs. decisions operation forced (queue isolation, columnar
interchange, native kernels). Drafting convention for architecture sections: open each
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

<!-- Reassess the June storage/HPC generalizations above against the retained
Talos/NFS experiments. Report measured workloads and constraints, not categorical
claims that shared storage or HPC cannot support the application. -->

## 3. Interactive execution architecture (~800 w)

<!-- Source material: docs/projects/i-crews/st_joe/weppcloud-architecture-overview.md
"Why HPC and WEPPcloud are a Poor Match" — the why-bespoke argument (batch
queuing vs real-time, always-on services, small-file random I/O vs Lustre,
FORTRAN+Python+Rust dependency glue vs module systems). 20+ container topology,
~1.5M LOC, effectively single-developer-maintained.

UI-responsiveness rationale (Roger 2026-06-12; statically verified against
source/compose — see planning doc):
- Architectural rule: Flask routes stay interactive (<300 ms rule; a few in
  the seconds range); ALL long-running work goes to RQ queues — not just WEPP
  FORTRAN: climate builds, soils, Omni, fork/archive, exports, interchange
  (wepppy/rq/ inventory). Latency provenance: observed browser-session
  timings (devtools), incl. sub-40 ms rq-engine job-status responses.
  Optionally formalize with a measured route-latency distribution in §8.
- Conventional design and its costs: in the manuscript, present generically —
  the Flask-SocketIO + gevent pattern requires single-worker processes,
  sticky-session load balancing to scale horizontally, and risks worker-local
  state divergence; one long request can stall the UI. DO NOT name the Culvert
  web app or cite its audit in the manuscript (Roger 2026-06-12 — no calling
  out a partner app as an anti-pattern; a citation would identify it). The
  audit (docs/culvert-at-risk-integration/audits/, 2026-02-20) remains our
  internal confidence that these constraints are real and domain-relevant —
  it grounds the claim, it does not appear in the paper. Phrase as the
  well-known deployment constraints of the conventional pattern.
- WEPPcloud instead: server push via Redis pub/sub fanned out by Go
  status2/preflight2 WebSocket services; client->server stays plain HTTP
  through Flask and rq-engine (FastAPI, async ASGI). Browse and query-engine
  (both Starlette, ASGI) segregate file-explorer and analytics workloads from
  the UI app. [Keep worker counts out of the paper — extraneous detail;
  demand has not required scaling beyond current provisioning.] -->

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

<!-- Develop state/orchestration, interchange, analytics, and native kernels
within this section. Figure 1 above is retained source material for the Compose
architecture; verify each boundary and date it before submission. -->

## 4. Operating and evolving the deployment (~800 w)

<!-- Compose experience -> documented Talos/Flux deployment and operational
constraints. Production RKE2/GitOps migration is intended, not an achieved result.
Source map and evidence limits: 01_devops_and_provenance.md. -->

## 5. Execution identity and provenance (~650 w)

For the interactive service, the software-provenance goal is to associate every
job with its actual executing container and immutable image identity. Container
metadata should identify versions across the software stack, allowing the
corresponding application, processing, and model source to be retrieved and
reviewed. The [stack inventory](../../docs/weppcloud-stack.md) describes the
component boundaries; a WEPPpy revision alone cannot identify all of them.
Jobs delegated to other containers require those execution identities as well.

This association supports software inspection without imposing a frozen pipeline
on interactive users. It does not, by itself, establish that retained inputs
were produced under consistent dependencies or that a complete project can be
replicated. The proposed declarative backend adds runtime pinning and enforced
pipeline dependencies to address those stronger requirements.

## 6. Operational evaluation (~950 w)

<!-- Representative watershed execution, measured operational pressures,
storage/worker experiments, and deployment/recovery evidence. Audit retained
artifacts and exact revisions before reporting numbers. The prior scenario and
feature case study belongs to the companion paper. -->

<!-- Retained scale lead from the June draft, not yet verified: St. Joe prep —
56 watersheds, 134,033 hillslopes, 151,121 channel segments; >100x the area of
the 2013–2018 Fernan effort (~3,800 ha). Check artifacts and dates before use. -->

## 7. Discussion: complementary execution modes (~550 w)

Interactive projects support exploration: users change parameters, inspect
results, and continue work as the service evolves. A retained result can
therefore depend on inputs prepared under several software revisions. Recording
the project's creation revision or current deployment does not, by itself,
identify that execution's complete dependency history. Interactivity makes
capturing this history and ensuring consistent dependencies substantially harder.

A proposed secondary backend would accept declarative experiments, bind their
resolved inputs to a container image digest, and execute them as Kubernetes
Jobs with enforced pipeline dependencies. Cryptographic tracking would identify the actual consumed
artifacts and their relationships to generated outputs. Retention and semantic
validation would be necessary alongside hashes. This mode would complement the
existing on-demand service; it would not require all users to adopt a batch-only
workflow. Notebook-based interaction retains the same tension unless an
additional mechanism enforces the experiment's runtime and pipeline dependencies.

The backend is a research direction. Claims of replay require measured tests
that distinguish byte identity, numerical agreement, and independent scientific
replication. The [scope decision](01_devops_and_provenance.md) defines the proposed
evaluation and the boundary between demonstrated operations and future work.

## 8. Conclusions (~200 w)

<!-- Limit conclusions to demonstrated operations; proposed replay stays future work. -->

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
