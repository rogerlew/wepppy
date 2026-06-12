# Deep Research Prompt — Literature Review for WEPPcloud ACG 2026 Manuscript

> Paste everything below the line into ChatGPT Deep Research.
> Save the result as `annotated-bibliography.md` in this directory.
> Provenance: prompt authored 2026-06-12 by Claude Code from 00_planning.md.

---

## Role and task

You are conducting a literature review for a manuscript targeting **Applied
Computing & Geosciences** (Elsevier, open access, companion journal to Computers
& Geosciences). Produce an **annotated bibliography** of peer-reviewed papers
relevant to the manuscript described below, followed by a synthesis that
positions the manuscript against the literature.

## The manuscript you are supporting

Working title: "WEPPcloud: an on-demand microservices architecture for
production-scale interactive watershed modeling."

It is the systems/architecture successor to Lew et al. (2022), "WEPPcloud: An
online watershed-scale hydrologic modeling tool. Part I. Model description,"
*Journal of Hydrology* 608:127603, https://doi.org/10.1016/j.jhydrol.2022.127603.

Thesis: the architecture and production behavior of WEPPcloud as an on-demand
geoscience modeling platform that (a) isolates long-running legacy physics-model
workloads (FORTRAN WEPP erosion/hydrology binaries, multi-hour jobs) from
interactive web requests via Redis-backed job queues; (b) preserves portable,
fork-able run state as a first-class research artifact (file-backed JSON state
with distributed locking instead of a relational database); (c) exposes model
outputs through self-describing columnar interchange (Parquet with Arrow
field-level units/description metadata) and a declarative, safety-bounded
analytics service (JSON query payloads planned to SQL over DuckDB, including
MCP routes for LLM-agent access); and (d) serves burst demand from post-wildfire
emergency-response users (USFS BAER teams) through containerized microservices
(Python Flask/FastAPI/Starlette, Go WebSocket telemetry services, Rust
geoprocessing kernels for watershed delineation and abstraction, sandboxed
per-user data-exploration instances) and scenario fan-out (one user action
clones and selectively reruns N treatment scenarios).

Framing: prototypes of geoscience web tools are abundant; platforms that survive
production demand are rare. The contribution is the architecture and its
measured production behavior, plus an end-to-end post-fire workflow case study.

## Research questions

1. What peer-reviewed work exists on **production web-based geoscience modeling
   platforms and science gateways** — their architectures, scaling strategies,
   and operational evidence? How do they evaluate themselves?
2. What has been published on **microservices, containerization, and
   service-oriented architectures in scientific computing and the geosciences**
   specifically (not generic software-engineering venues)?
3. What is the state of literature on **job orchestration / queue-based
   isolation of long-running scientific model executions** behind interactive
   web frontends?
4. What has been published on **cloud-native / columnar geospatial data formats**
   (Parquet, GeoParquet, Arrow, Zarr, COG) as interchange or analytics substrates
   for environmental model output, and on **embedded analytical databases**
   (DuckDB) in scientific data services?
5. What exists on **wrapping or modernizing legacy FORTRAN environmental models**
   (WEPP, SWAT, MODFLOW, VIC, RHESSys, etc.) for web/cloud execution?
6. What exists on **large-scale interactive web geovisualization** of model
   output (WebGL, deck.gl, tile-based rendering) in the geosciences?
7. What exists on **scenario management / ensemble run management systems** for
   environmental models — especially treatment/management scenario comparison
   and efficient storage/compute reuse across scenario variants?
8. What exists on **LLM/agent interfaces to scientific modeling platforms and
   data services** (MCP, natural-language query of model archives)? Treat as a
   secondary theme.
9. What **post-fire erosion/hydrology decision-support tooling** literature
   exists since 2022 (ERMiT, RHEM, Debris-flow tools, BAER workflows) that this
   paper should acknowledge?

## Scope and source constraints

- Prioritize 2019–2026; include older foundational papers only when they are the
  canonical citation for a concept (e.g., science gateways, TOPAZ, WEPP model).
- Prioritize these venues: Applied Computing & Geosciences; Computers &
  Geosciences; Environmental Modelling & Software; Geoscientific Model
  Development; Earth Science Informatics; Journal of Open Source Software;
  Future Generation Computer Systems; Computing in Science & Engineering;
  JAWRA/Hydrology venues for the applied items. Conference series acceptable:
  Gateways/PEARC, AGU/EGU informatics sessions.
- Peer-reviewed strongly preferred. Preprints allowed only if clearly labeled
  as preprints. No blog posts, no vendor marketing, no documentation sites as
  primary entries (they may appear as supplementary links inside annotations).
- **Anti-fabrication requirement (critical):** every entry must include a DOI or
  stable URL that you have verified resolves to the cited work. If you cannot
  verify an item, either omit it or list it in a separate clearly-labeled
  "unverified leads" section at the end. Do not guess author lists or years.

## Specific items to verify or correct

A prior review suggested these as ACG precedents. Confirm each exists as
described, correct the citation details, and annotate; flag any that do not
check out:

1. Wilcox & Pasch, "The arctic knowledge-based system: Science gateway
   integration for petascale arctic data processing and geospatial feature
   prediction," ACG 2026. (Believed verified.)
2. Perret, Jessell & Bétend, "An open-source, QGIS-based solution for digital
   geological mapping: GEOL-QMAPS," ACG 2024, 10.1016/j.acags.2024.100197.
   (Believed verified.)
3. "Hydro KNIME" — hydrology workflow/reproducibility paper, possibly ACG 2026.
4. "PixelSWAT" — SWAT input-preparation tool paper, journal uncertain.
5. Oldemeyer & Russell — interactive web mapping / subsurface cross-sections,
   possibly ACG, Idaho National Laboratory affiliation.
6. Zhang et al. — LLM-driven workflow for Mindat API queries, possibly ACG,
   University of Idaho affiliation.
7. Alyaev et al. — interactive sequential-decision geosteering benchmark,
   possibly ACG (~2021).

Also include and verify the obvious platform comparators if they have citable
papers: HydroShare, Tethys Platform, CSDMS/pymt, Pangeo, Galaxy (genomics, as
cross-domain contrast), CUAHSI HydroDS, SWATShare, HydroFrame, OpenTopography,
Google Earth Engine (architecture paper), WikiWatershed/Model My Watershed.

## Output format

Markdown document with these sections:

1. **Annotated bibliography**, grouped under the nine research-question themes.
   Per entry:
   - Full citation with DOI/URL and venue + year.
   - 2–4 sentence factual summary of what the paper did.
   - 1–3 sentence relevance note: which manuscript section it informs
     (introduction / related work / architecture / data model / visualization /
     scenario management / production evidence / discussion), and whether it
     **supports**, **contrasts with**, or **competes with** our contribution.
   - Evidence type the paper used (benchmarks / case study / adoption metrics /
     none) — we are calibrating reviewer expectations.
2. **Synthesis** (~800 words):
   - The 12–15 most cite-worthy entries as a ranked table with one-line reasons.
   - Gaps: what has *not* been published that our manuscript can claim
     (production telemetry from a long-lived geoscience platform? queue
     isolation of legacy binaries? Arrow-metadata interchange contracts?).
   - Positioning risks: any paper that already makes our claims, and how to
     differentiate.
3. **Unverified leads** (if any) — clearly separated.

Target 35–60 verified entries. Depth of annotation matters more than count.
