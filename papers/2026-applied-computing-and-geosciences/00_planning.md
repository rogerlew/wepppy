# Manuscript Planning — Applied Computing and Geosciences 2026

> Update/successor to Lew et al. (2022), *J. Hydrology* 608:127603 (WEPPcloud Part I).
> Venue decided 2026-06-12: **Applied Computing & Geosciences** (see
> journal-fit-rubric.md for the C&G comparison and rationale).
> Status: planning. Last updated 2026-06-12.

## Working thesis

A **bespoke, tightly-integrated, on-demand microservices architecture for serving
interactive, physics-based watershed modeling at production scale**. Hook:
prototypes are easy (especially with AI assistance); production is hard —
servicing surge demand, balancing heterogeneous workloads, keeping long-running
legacy model binaries and sub-second interactive requests on shared
infrastructure.

ACG's scope (Distributed Systems, Software Engineering, E-Geoscience, Data Models,
Computer Visualization, Geoinformatics, WWW) admits this thesis told straight —
no vocabulary contortions needed. Still lead with architecture decisions and
measured behavior rather than tooling narrative; "we adopted Docker/CI" is
weaker than "these production requirements forced these designs, here is how
they behave under load."

**Center of gravity (Roger, 2026-06-12): operational lessons learned.** The
paper's distinctive value is *why* the architecture is the way it is — lessons
paid for in operation, not retrofitted rationale. Two flavors: original
decisions validated and hardened (file-backed run state → distributed locking,
Redis caching) vs. decisions operation forced (queue isolation, columnar
interchange, native kernels, pub/sub status streaming). Drafting convention:
each architecture section opens with the operational pressure/incident, then
the design, then observed behavior. Characterize the 2022-era implementation
as "naive" (it had Flask + webservices + NoDb already — not monolithic), i.e.
it worked but had not yet met production. Needed input: Roger's inventory of
actual incidents/pressures 2022–2026 (see TODO in paper.md §2).

Design pillars (each with rationale + observed behavior):

1. File-backed run state with distributed locking (NoDb + Redis) instead of an
   RDBMS — portable, fork-able, archivable runs as a first-class contract.
2. Queue isolation of long-running legacy FORTRAN (multi-hour jobs) from
   interactive request paths; RQ/Redis orchestration.
3. Columnar self-describing interchange (Parquet + Arrow metadata) as the
   contract between model binaries and analytics services; NoDb Parquet sidecars.
4. Purpose-built minimal services where general frameworks underperform:
   Go telemetry fan-out (status2/preflight2), Rust geoprocessing kernels
   (weppcloud-wbt, peridot, wepppyo3, oxidized-rasterstats), sandboxed per-user
   d-tale instances.
5. Declarative, safety-bounded analytics API (query-engine: JSON → planned SQL,
   read-only, timeouts/payload limits) including MCP routes for agentic access.

Omni scenarios/contrasts are the flagship demand-amplification case: one user
action fans out to N cloned model runs; selective rebuild/rerun and shared base
inputs are the resource-balancing answer.

Candidate abstract spine (adapted from external review, 2026-06-12): *the
architecture and production behavior of WEPPcloud as an on-demand geoscience
modeling platform that isolates long-running legacy physics-model workloads from
interactive analysis, preserves portable run state as a first-class research
artifact, and exposes model outputs through columnar interchange and declarative
analytics services.*

Hook placement: the "AI makes prototypes cheap; production is hard" line is
motivation, not contribution — use it in the introduction's framing paragraph
and/or discussion, keep it out of the title and abstract. The durable claim is
the production architecture. Similarly, MCP/agentic access is an operational
capability worth one subsection (it works today), but it is a secondary surface —
not the hook, not in the title.

## Article type — DECIDED 2026-06-12: Application article

**Application article** (5,000 w): "real-world case study." Adoption, the
post-fire workflow case study, and surge demand carry the evidence load;
design principles and measured behavior are presented as the application's
architecture rather than as generalizable research findings. This lowers the
experimental-design bar reviewers can demand while keeping the same word limit.

## Working author list (2026-06-12)

| Author | Affiliation | Notes |
| --- | --- | --- |
| Roger Lew | University of Idaho | **Corresponding author** (confirmed 2026-06-12); UI affiliation determines Elsevier publishing-agreement/APC eligibility |
| Mariana Dobre | University of Idaho | |
| Anurag Srivastava | University of Idaho | |
| Erin Brooks | University of Idaho | |
| Peter R. Robichaud | USDA Forest Service, Rocky Mountain Research Station | Confirmed 2026-06-12; retired May/June 2026, but RMRS is where the work was carried out (matches ACG affiliation rule and 2022 paper: RMRS, Moscow, ID) |

CRediT roles to drift in as drafting assigns work (Conceptualization, Software,
Writing — original draft, etc.). ACG: authorship changes after submission are
heavily restricted and not allowed after acceptance — finalize order before
submitting.

## Venue constraints (from applied-computing-and-geosciences.md)

| Constraint | Value |
| --- | --- |
| Word limit | **5,000** (research paper and application article); count exclusions unstated — verify |
| Abstract | ≤ 250 words |
| Keywords | 1–7, avoid multi-word |
| Highlights | Encouraged; 3–5 bullets, ≤85 chars each, separate file |
| Graphical abstract | Encouraged; 531×1328 px, separate file |
| Sections | Numbered (1, 1.1, 1.1.1); cross-reference by number |
| References | Numeric [n] in order of appearance; LTWA journal abbreviations |
| Units | SI required |
| Data | Option C: deposit in repository + cite/link, or explain why not |
| AI declaration | **Required**: statement of generative AI use in manuscript prep, in a section before references (relevant to our Claude/Codex workflow — draft this early, it will appear in the published article) |
| Open access | Fully OA, mandatory APC — **verify amount + UI/USDA agreement/waiver before committing coauthors** |
| Review | Single anonymized, ≥2 reviewers |
| Template | els-cas (cas-sc.cls fine; double-column permitted for LaTeX but unnecessary) |
| Preprint | Free SSRN posting offered at submission, optional |

## Candidate outline (~5,000 words)

1. **Introduction** (~600 w)
   - Prototype-to-production gap in geoscience web modeling; AI makes prototypes
     cheap, production scarcity unchanged. Demand growth since 2022 (adoption,
     post-fire surge response, larger watersheds, agentic access).
   - Numbered contributions list.
2. **Production requirements and design principles** (~500 w)
   - Requirements that forced the architecture: hybrid workloads (multi-hour
     FORTRAN + sub-second interactive), bursty deadline-driven demand (BAER),
     stateful fork-able runs, legacy binary integration, agent access.
   - Principles up front; sections 3–6 are their realizations.
3. **On-demand microservices architecture** (~800 w)
   - Topology: Caddy → Flask UI, rq-engine (FastAPI), query-engine (Starlette),
     browse, Go status2/preflight2, sandboxed d-tale; RQ worker pools; Redis roles.
   - Why bespoke + tightly-integrated vs. general workflow platforms / PaaS;
     why Go for telemetry fan-out; container strategy in brief.
   - Figure 1: runtime topology (successor to 2022 Fig. 1).
4. **State model and job orchestration** (~550 w)
   - NoDb file-backed singletons + Redis caching/locking; no RDBMS for run state —
     rationale, locking discipline, failure modes.
   - RQ job flow, dependency trees, status pub/sub → WebSocket telemetry.
5. **Data interchange and declarative analytics** (~650 w)
   - WEPP interchange: canonical IDs, calendar bundle, Arrow units/description
     metadata, bounded-memory streaming writers, auto-generated schema READMEs;
     NoDb Parquet sidecars (soils, landuse, hillslopes/channels).
   - Query-engine: per-run catalogs, JSON payload → planned SQL, safety model,
     spatial formats, MCP/agent routes.
6. **Performance substrate** (~400 w)
   - Rust kernels: weppcloud-wbt (delineation), peridot (watershed abstraction →
     parquet manifest), wepppyo3 (PyO3), oxidized-rasterstats.
   - Benchmarks vs. prior TOPAZ/Python paths; raster_tools crosswalk precedent
     (docs/work-packages/20260303_raster_tools_crosswalk_benchmarks).
7. **On-demand scenario computation and analytics surfaces** (~650 w)
   - Omni scenarios/contrasts: clone under `_pups/omni/`, selective rebuild/rerun,
     contrast targeting; storage + compute efficiency vs. forked projects;
     demand-amplification framing.
   - GL-Dashboard: deck.gl/WebGL required at production data volumes (beyond
     Leaflet); scenario comparison, differential colormaps.
   - Storm Event Analyzer: query-engine-driven event-population workflow replacing
     single-storm analysis; CLIGEN vs. NOAA Atlas 14.
8. **Production evidence** (~550 w)
   - Demand: run counts by year, users/institutions, surge case study (fire season).
   - Resources: queue wait times, worker utilization, concurrent-run scaling,
     representative large-watershed wall times.
   - Operability framed as reproducible research infrastructure — one paragraph.
9. **Discussion: transferable lessons, limitations, future work** (~300 w)

Budget totals 5,000; expect to rebalance once exclusions are verified. The
application-article register allows the case-study material (section 8) to grow
at the expense of section 2 if needed.

## Related work

Annotated bibliography: `research/annotated-bibliography.md` (Deep Research,
2026-06-12; 53 annotated entries across the nine themes, ranked top-15,
synthesis with gaps and positioning risks, plus 5 unverified leads). PDFs for
17 entries in `research/pdfs/`.

Verification status (Claude Code, 2026-06-12):
- **Title-page verified from PDFs**: Wilcox et al. 2026 A-KBS (ACG 29:100322),
  Radosevic et al. 2026 Hydro KNIME (ACG 30:100348), Perret et al. 2024
  GEOL-QMAPS (ACG 24:100197).
- **Web-verified**: PixelSWAT (Bole et al. 2024, ACG 100175), Alyaev et al. 2021
  geosteering benchmark (ACG 12:100072), Zhang et al. LLM-driven Mindat workflow
  (ACG 100218), Oldemeyer & Russell 2022 (ACG 13:100077), eWaterCycle (Hut et
  al. 2022, GMD 15:5371-5390), CSDMS (Tucker et al. 2022, GMD
  15:1413-1439), BMI 2.0 (Hutton et al. 2020, JOSS 5:2317), and Model My
  Watershed official software/documentation.
- Remaining entries (HydroShare, Tethys, SWATShare, GEE, DuckDB, Spatial
  Parquet, Pegasus, Parsl, ERMiT, ...) are canonical and low-risk; spot-check
  DOIs at citation time. PDFs on hand cover most of the top-15.

Claude review additions addressed:
- [x] **eWaterCycle** (Hut et al. 2022, Geosci. Model Dev.) — added as the
      strongest comparator for FAIR, containerized hydrological model execution.
- [x] **CSDMS / pymt / Basic Model Interface** (Tucker et al. GMD; Hutton et al.
      JOSS) — added as model-interoperability and coupling infrastructure.
- [x] **Model My Watershed / WikiWatershed** — added as verified public-facing
      watershed scenario software; no DOI-bearing systems architecture paper was
      identified in this pass.

Positioning takeaways from the synthesis (adopted):
- Do not claim novelty for microservices/containers/remote execution per se —
  A-KBS (K8s/HPC/JupyterHub/Globus dispatch) owns that genre claim in ACG. Claim
  the application-level orchestration contract: fine-grained environmental-model
  task orchestration, queue-isolated legacy FORTRAN, file-backed run-state
  artifacts, selective rerun, scenario fan-out, measured post-fire workload
  behavior under burst demand.
- Differentiate concretely vs. HydroShare (publication/collaboration, not
  execution) and SWATShare (SWAT-focused sharing/execution).
- GEE/Pangeo are conceptual comparators for cloud data/analytics patterns, not
  competitors; do not invite scale comparison.
- Genre lesson: ACG papers ground themselves in a specific workflow, platform,
  or benchmark with measured behavior or a concrete use case — Section 8 cannot
  be soft.

## Evidence inventory (gates drafting)

Three evidence modes; the strongest paper combines all three lightly:
(a) operational telemetry, (b) component benchmarks, (c) an end-to-end workflow
case study. Mode (c) is the cheapest to produce and doubles as the geoscience
grounding and figure source.

Workflow case study (new — from precedent review):

- [ ] One real post-fire watershed, end to end: base run → Omni scenario clones →
      contrasts → GL-Dashboard comparison → Storm Event Analyzer. Narrated once,
      referenced from sections 3–8 as the running example.

Production/demand telemetry (verify what is actually retained; Redis is
non-persistent and logs are unstructured — may need a deliberate collection
window before drafting section 8):

- [ ] Run counts over time (run metadata / user DB) since 2022; users, institutions.
- [ ] Surge case study: identify a fire-season demand burst with timestamps.
- [ ] RQ queue depth / wait time / worker utilization — check profile_recorder,
      RQ dashboard history; if absent, instrument and collect a window.
- [ ] Concurrent-run scaling behavior; representative large-watershed wall times.

Component benchmarks:

- [ ] Delineation/abstraction: weppcloud-wbt + peridot vs. TOPAZ-era path
      (wall time, peak memory, representative watersheds).
- [ ] raster_tools crosswalk artifacts (17–323×) — methodology + owned-stack baseline.
- [ ] Interchange: parse-time and size, `wepp/output` text vs. `wepp/interchange`
      parquet, small/medium/large runs.
- [ ] Omni: storage + wall time, N-scenario Omni project vs. N forked projects.
- [ ] Query-engine: example payloads + latency on representative runs.
- [ ] Flask route latency distribution (validate the <300 ms design rule;
      identify the seconds-range outliers and name them honestly).
- [ ] rq-engine jobstatus latency under realistic load (claimed sub-40 ms —
      needs benchmark before the number appears in the paper).
- [ ] GL-Dashboard: dataset sizes that broke Leaflet; interaction latency on deck.gl.

Data/repo (ACG Option C):

- [ ] Deposit citable artifacts (Zenodo DOIs?) for wepppy and companion repos
      (wepppyo3, peridot, weppcloud-wbt); reproducible example run.
- [ ] Draft data availability statement.

## Figures plan (draft)

1. Runtime topology (services, Redis roles, job flow) — successor to 2022 Fig. 1.
   Base on the ASCII topology in
   `docs/projects/i-crews/st_joe/weppcloud-architecture-overview.md` (Roger,
   2026-06-12); ASCII now embedded in paper.md §3. Redraw as vector for
   submission; open decisions noted in paper.md (Caddy edge, batch worker pool,
   service-container collapse).
2. Job orchestration / state model: run dir + NoDb sidecars + locks + RQ flow +
   telemetry fan-out.
3. Data-contract diagram: model binaries → interchange parquet → query-engine
   catalog → consumers (reports, GL-Dashboard, SEA, MCP agents).
4. Production evidence: demand growth + surge case study + queue/utilization panels.
5. Omni scenario/contrast workflow + efficiency comparison.
6. GL-Dashboard or Storm Event Analyzer screenshot (scenario comparison).
7. (Optional) Graphical abstract — condensed version of figure 3.

## Submission mechanics

- Submit at https://submit.elsevier.com/ACAGS.
- Template: `els-cas-templates/cas-sc.cls`; numbered sections; numeric references.
- Separate files: highlights, graphical abstract (optional), declaration of
  interests (.docx via declarations.elsevier.com), CRediT statement, data
  availability statement, **generative AI declaration**.
- Title brainstorm (avoid AI/MCP/agentic in title — secondary surfaces):
  - "WEPPcloud: an on-demand microservices architecture for production-scale
    interactive watershed modeling"
  - "Production-scale interactive watershed modeling with WEPPcloud: an on-demand
    microservices architecture for legacy physics models"

## Next steps

0. ~~Deep Research bibliography~~ done 2026-06-12; key entries verified (see
   Related work). Claude review additions and Oldemeyer & Russell DOI check
   addressed 2026-06-12.
1. ~~Article type~~ Application article. ~~Author list~~ set; Lew corresponding;
   Robichaud affiliation USDA FS RMRS (all confirmed 2026-06-12). Remaining:
   verify APC amount + University of Idaho Elsevier agreement coverage for ACG.
2. Write highlights (3–5) and 250-word abstract first — framing forcing function.
3. Audit available production telemetry (top of evidence inventory); decide
   whether a collection window is needed before drafting section 8.
4. Scaffold `manuscript/` from cas-sc template; draft sections in markdown until
   structure stabilizes.
