# Manuscript Planning — Applied Computing and Geosciences 2026

> Update/successor to Lew et al. (2022), *J. Hydrology* 608:127603 (WEPPcloud Part I).
> Venue decided 2026-06-12: **Applied Computing & Geosciences** (see
> journal-fit-rubric.md for the C&G comparison and rationale).
> Status: planning; scope revised 2026-09-21. See [current scope decision](01_devops_and_provenance.md).

## Working thesis
The evolving production service and the replayable scientific experiment have
different lifecycles. This paper explains the operational lessons behind
WEPPcloud's interactive on-demand architecture, the move toward declarative
infrastructure, and the proposed separation of interactive projects from
strictly specified scientific executions.

**Scope decision (Roger, 2026-09-21):**
[Operations, provenance, and two execution modes](01_devops_and_provenance.md)
is the current editorial authority, including rationale, evidence status, and
claim limits. WEPPcloud keeps its interactive workflow. A secondary backend is
proposed to run declarative experiments as image-digest-pinned Kubernetes Jobs
with cryptographic dependency tracking. The Talos deployment at `openwepp.org`
is documented experience; RKE2/GitOps for production `wepp.cloud` is a future
direction. For interactive jobs, the goal is to identify the executing container
and use its whole-stack version metadata to retrieve and review corresponding
source, using [the stack map](../../docs/weppcloud-stack.md) as the inventory.
The declarative mode additionally aims to pin the runtime and enforce pipeline
dependencies for stronger replicability.

Retain the June emphasis on operational lessons: each architecture section
opens with an observed pressure, explains the decision, and reports evidence.
File-backed state, queue isolation, columnar interchange, native kernels, and
bounded analytics remain supporting mechanisms. Avoid a tool-adoption chronology.

OMNI scenarios/contrasts, detailed visualization features, and their scientific
case study belong to the [companion paper](../2026-weppcloud-scenarios-and-contrasts/00_planning.md).
Scenario fan-out can remain a workload example here. Interactivity makes
provenance and reproducibility substantially more challenging: selective reruns,
mutable parameters, and retained artifacts complicate dependency tracking.
Notebooks and model containers do not by themselves remove that tension.

## Article type — DECIDED 2026-06-12: Application article

**Application article** (5,000 w): "real-world case study." Adoption, a
representative execution case study, and operational measurements carry the evidence load;
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

1. **Introduction** (~550 w): production watershed modeling; an evolving service
   versus a frozen experiment; contributions limited to demonstrated behavior.
2. **Operational pressures and design principles** (~500 w): burst demand,
   interactive latency, long simulations, portable state, projects spanning
   deployments. Ground each pressure in retained evidence.
3. **Interactive execution architecture** (~800 w): service boundaries, RQ,
   NoDb, locking, data interchange, analytics, and native kernels; explain why
   these mechanisms were needed rather than inventorying services.
4. **Operating and evolving the deployment** (~800 w): Compose experience,
   bare-metal Talos/Flux evidence, storage and worker constraints, image promotion
   and recovery. Identify RKE2 migration as intended until it is demonstrated.
5. **Execution identity and provenance** (~650 w): deployment versus experiment
   versus execution records; mixed-version project histories; actual consumed
   inputs and artifact validation; current capabilities and gaps.
6. **Operational evaluation** (~950 w): representative watershed workflow,
   responsiveness/resource measurements, retained migration experiments and
   recovery evidence. Add declarative replay results only when available.
7. **Discussion: complementary execution modes** (~550 w): proposed declarative
   Kubernetes Jobs, cryptographic dependency tracking, replay criteria, costs,
   and limitations. Move evaluated backend methods into the main architecture
   only after implementation and evidence justify it.
8. **Conclusions** (~200 w).

The outline totals 5,000 words. Feature methods and their evaluation are reserved
for the companion paper. Application article remains the working choice; revisit
it if an implemented provenance/replay method becomes the principal contribution.
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
  artifacts, execution provenance boundaries and measured workload
  behavior under burst demand. Detailed scenario methods move to the companion paper.
- Differentiate concretely vs. HydroShare (publication/collaboration, not
  execution) and SWATShare (SWAT-focused sharing/execution).
- GEE/Pangeo are conceptual comparators for cloud data/analytics patterns, not
  competitors; do not invite scale comparison.
- Genre lesson: ACG papers ground themselves in a specific workflow, platform,
  or benchmark with measured behavior or a concrete use case — the operational evaluation must provide concrete evidence.

## Evidence inventory (gates drafting)

- [ ] Inventory real operational pressures and incidents since the 2022 paper;
      distinguish retained measurements from retrospective observations.
- [ ] Select a representative watershed execution as the running example.
- [ ] Audit demand, queue, latency, and utilization records; collect a defined
      window where historical telemetry is unavailable.
- [ ] Pin the Talos source/evidence revisions; extract deployment, recovery,
      storage, and worker findings from `open-wepp-org` with exact test scope.
- [ ] Inspect a project continued across software revisions; establish which
      dependencies can be recovered for each result and identify gaps.
- [ ] Collect bounded component measurements only where they explain an
      architectural choice; avoid an unrelated benchmark catalog.
- [ ] If implemented, run the declarative replay and dependency-change evaluation
      specified in [the scope decision](01_devops_and_provenance.md#evaluation-and-claim-limits).
- [ ] Deposit citable code, images/data where permitted, and a representative
      execution package; draft the data availability statement.

The previous OMNI efficiency study and feature-driven post-fire case study are
retained in the companion paper's evidence inventory. RKE2 migration and strict
replay are not prerequisites for submitting an evidence-grounded operations
paper, but cannot be claimed as achieved without their own validation.
## Figures plan (revised 2026-09-21)

1. Interactive runtime topology: service boundaries, state, and execution flow.
2. Deployment record versus scientific execution record: what each identifies
   and where inputs prepared under earlier revisions enter the result lineage.
3. Operational evidence: selected demand, resource, storage, or recovery results
   with their environment and workload scope stated.
4. Complementary execution modes: existing interactive service and proposed
   declarative Jobs, visually distinguishing implemented and proposed elements.

OMNI workflow and dashboard/event-analysis screenshots move to the companion
paper. Use a separate replay-results panel only if the backend is evaluated.
## Submission mechanics

- Submit at https://submit.elsevier.com/ACAGS.
- Template: `els-cas-templates/cas-sc.cls`; numbered sections; numeric references.
- Separate files: highlights, graphical abstract (optional), declaration of
  interests (.docx via declarations.elsevier.com), CRediT statement, data
  availability statement, **generative AI declaration**.
- Title brainstorm (avoid AI/MCP/agentic in title — secondary surfaces):
  - "Operating an evolving watershed-modeling service: architecture and provenance
    lessons from WEPPcloud"
  - If replay is implemented and evaluated: "From interactive watershed modeling
    to reproducible execution: operational lessons from WEPPcloud"

## Next steps

0. ~~Deep Research bibliography~~ done 2026-06-12; key entries verified (see
   Related work). Claude review additions and Oldemeyer & Russell DOI check
   addressed 2026-06-12.
1. ~~Article type~~ Application article. ~~Author list~~ set; Lew corresponding;
   Robichaud affiliation USDA FS RMRS (all confirmed 2026-06-12). Remaining:
   verify APC amount + University of Idaho Elsevier agreement coverage for ACG.
2. Revised abstract, highlights, and outline drafted 2026-09-21. Resolve evidence
   placeholders and revisit claims once the operational evaluation is assembled.
3. Audit available production telemetry (top of evidence inventory); decide
   whether a collection window is needed before drafting the operational evaluation.
4. Scaffold `manuscript/` from cas-sc template; draft sections in markdown until
   structure stabilizes.
