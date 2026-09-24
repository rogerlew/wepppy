# Companion paper: interactive watershed scenarios and contrasts

> Scope established by Roger Lew, 2026-09-21; expanded the same day to include
> GL-Dashboard and query-engine analysis. Working Pubroot case-study scaffold;
> authorship, final venue approval, and submission schedule remain open.
> Split from the [ACG architecture draft](../2026-applied-computing-and-geosciences/01_devops_and_provenance.md).

## Working files and editorial decision

### Accepted narrative and audience (Roger, 2026-09-23)

Write for land managers, hydrologists, soil scientists, and watershed specialists.
The main case is the Tenderfoot-area `animal-misgiving` run: two thinning
prescriptions and 36 contrasts across 18 spatial groups. Organize the manuscript
around prescription effects, treatment location, and whether isolated effects
can represent combined treatment. The strongest measured model result is
nonadditive outlet sediment response despite nearly additive water-volume
response; use this to explain the value of process-based watershed routing.
Report small absolute hillslope losses alongside relative increases and include
the mean group-contrast effects. Explain quantities and management implications
before implementation details.

The modeled basin is larger than the experimental forest and uses synthetic
weather. Present a demonstration, not a reconstruction of actual thinning,
field validation, an optimization, or evidence of avoided wildfire impacts.
Keep Lookout as a complementary appendix, preserving its scenario results and
BAER context. Retain reproducible scripts and artifact limitations in the
[Tenderfoot analysis](data/tenderfoot/analysis.md). This direction replaces the
earlier Lookout-centered evaluation plan below without discarding its evidence.

### Working resources

- [paper.md](paper.md): manuscript draft with results, figures, and explicit evidence gaps.
- [evidence.md](evidence.md): source map, proposed evaluation, and figure plan.
- [pubroot.md](pubroot.md): installed CLI version, submission-format caveat,
  working category, and publication preparation.
- [Literature review](references/literature-review.md): introduction sources,
  locally retained PDFs, and [full-text acquisition status](references/access-needed.md).

Roger requested a connected treatment of OMNI, GL-Dashboard scenario support,
and potentially query-engine analysis/aggregation across scenarios. The working
narrative is **construct alternatives -> inspect spatial effects -> quantify
and compare outcomes**. GL-Dashboard is part of the scientific workflow, not
just a screenshot. Include query-engine methods where they explain how plotted
and aggregated results are obtained and checked. Keep deployment architecture
and stronger future provenance guarantees in the operations paper.

Working venue: Pubroot, `earth/sustainability`, Case Study. Target approximately
3,000–4,000 words as an editorial budget, not a verified venue requirement.
Alternative category if the emphasis shifts strongly toward visual analytics:
`data/visualization`; domain decision support remains the present organizing idea.

## Working thesis

Explain how OMNI scenario construction and spatial contrasts, GL-Dashboard
comparison, and scenario-aware queries form an interactive watershed treatment
assessment workflow. Organize the paper around a scientific decision and the
semantics of its comparisons, supported by a real case study. A catalog of
interface features is insufficient.

## Introduction direction (Roger, 2026-09-21)

Introduce WEPP and WEPPcloud through forest/native-vegetation land management
and pre/post-fire assessment. Explain the `(Un)Disturbed` soil/management
parameterization harness before OMNI. The prior workflow required careful
forking and manual synchronization of shared parameters, including WEPP Advanced
Options; this is operator-reported motivation, not measured user-error evidence.
OMNI Scenarios propagates parent delineation and parameterization during child
construction, then applies the intended alternative. Do not imply that completed
children automatically inherit every subsequent edit without regeneration.

Explain the hillslope-first execution and serialized pass-file boundary before
introducing contrasts. Replacing one selected hillslope's control pass file with
its treatment equivalent and rerunning the watershed assesses outlet response
while retaining WEPP's process-based channel water/sediment routing. Use
post-fire mitigation and downstream water-supply/resource protection as practical
motivations. Individual effects are conditional model comparisons, not additive
portfolio benefits or measured causal effects. Acknowledge Pi-VAT when introducing
GL-Dashboard and scenario analytics. This establishes workflow evolution rather
than claiming that OMNI invented scenario comparison or spatial targeting.

## Material transferred from the architecture paper

- OMNI scenarios and contrasts: shared base inputs, scenario clones, selective
  rebuild/rerun, contrast targeting, and comparison semantics.
- GL-Dashboard: multi-scenario visualization and differential maps; explain
  reference selection, units, distributions, and interpretation. Verify map and
  graph scenario selection separately; they have different controls.
- Query engine: scenario-scoped queries, joins and aggregations, and comparisons
  using combined OMNI summary tables or matched queries across scenario catalogs.
  Do not imply arbitrary cross-catalog federation in one request.
- Storm Event Analyzer: event-population analysis where it supports the same
  scientific case; defer a separate feature tour if it fragments the argument.
- Scenario workflow figure, comparison screenshots, and storage/wall-time
  evaluation against separately forked projects.

## Candidate outline

1. Decision problem and limitations of manually constructed comparisons.
2. Scenario and contrast definitions: shared assumptions, changed parameters,
   spatial targeting, reference cases, and comparability constraints.
3. Workflow: baseline construction, scenario execution, contrast assembly and
   watershed rerouting, GL-Dashboard inspection, and quantitative query analysis.
4. Real watershed case study: management question, input provenance, justified
   treatments, modeled outcomes, and interpretation limits.
5. Evaluation: agreement with independently prepared reference runs, execution
   and storage costs, and what users can infer from displayed differences.
6. Discussion: scientific usefulness, model uncertainty, reproducibility limits,
   and applicability beyond the demonstrated case.

## Evidence to collect

- [ ] Select one real post-fire watershed and management question.
- [ ] Record scenario definitions and why the comparisons are scientifically valid.
- [ ] Validate generated inputs against intended changes and unchanged assumptions.
- [ ] Compare OMNI outputs with equivalent independently prepared model runs.
- [ ] Measure N-scenario storage and wall time against N forked projects.
- [ ] Validate selected dashboard values and difference signs against exact
      query responses and underlying Parquet artifacts.
- [ ] Retain cross-scenario query payloads, results, aggregation rules, units,
      missing-data handling, and entity/time alignment.
- [ ] Retain the displayed quantities, units, reference cases, and source outputs
      behind every comparison figure.
- [ ] Establish the role of event analysis in the case before including it.
- [ ] Retain a citable run/data package and identify any data redistribution limits.

## Boundary with the operations paper

Introduce enough architecture to make the workflow understandable and refer to
the operations paper for service isolation, deployment, and execution-provenance
design. This paper owns detailed OMNI methods and scientific comparison results.
The operations paper may describe scenario fan-out as demand, but does not reuse
this paper's feature evaluation as its principal contribution.

## Interpretation boundaries

The cumulative-contribution selector chooses candidates, then builds individual
hillslope contrasts; it does not automatically execute growing treatment
portfolios. Grouped selections can evaluate combined treatment areas explicitly.
Polygon selection uses whole-hillslope inclusion, not exact polygon clipping.
Treatments are modeled interventions, and contrasts are model comparisons rather
than statistical contrasts or causal estimates from field experiments. Software
reuse correctness, model validity, and user effectiveness require distinct evidence.

## Candidate refinement: Skin Gulch (September 22, 2026)

Roger's intended design separates historical grounding from treatment exploration:
use a documented severe post-fire case to assess whether WEPPcloud reproduces
the order of magnitude of observed responses, then demonstrate hypothetical
prefire thinning scenarios and contrasts on an undisturbed baseline. Agreement
with observed magnitudes is an evaluation target, not an established result.
The thinning comparison is not a reconstruction of how treatment would have
changed the historical fire, and does not attribute losses to past management.
This separation keeps the contribution focused on scenario analysis without
requiring a treatment-to-fire-severity model.

Skin Gulch is a candidate, not yet a replacement for the retained Lookout case.
A targeted public-source search found collaborative restoration accounts and
no specific Skin Gulch management dispute, objection, or lawsuit in the reviewed
results. This is not evidence that all stakeholders agree. The wider High Park
Fire did generate debate about suppression policy and home-protection measures.

- [CPRW Skin Gulch project](https://www.poudrewatershed.org/skin-gulch): restoration
  with the USFS Canyon Lakes Ranger District, Wildlands Restoration Volunteers,
  and AloTerra; sediment reduction, floodplain function, and biodiversity goals;
  completion reported in spring 2016.
- [Larimer County hazard mitigation plan](https://www.larimer.gov/sites/default/files/2021-hazard-mitigation-planlarimer-county-112022.pdf):
  reports Skin Gulch among projects selected with stakeholder input and funding.
- [Collaborative watershed-management case study](https://online.ucpress.edu/cse/article/3/1/1/108968/Improving-the-Resilience-of-Water-Resources-after):
  documents consensus building, private-land access, and initial resistance to
  prescribed burning at the broader Poudre watershed scale.
- [High Country News, August 8, 2012](https://www.hcn.org/issues/44-13/what-the-high-park-wildfire-can-teach-us-about-protecting-homes/):
  reports homeowner and expert debate over defensible space after High Park;
  not a Skin Gulch restoration dispute.

Screening judgment: Skin Gulch is suitable to advance under the separated
historical-grounding and undisturbed-treatment framing. Do not describe it as
contention-free or imply stakeholder endorsement. Select observation periods
with explicit accounting for the September 2013 flood and subsequent restoration.
