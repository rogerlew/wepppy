# Companion paper: interactive watershed scenarios and contrasts

> Scope established by Roger Lew, 2026-09-21. Working outline; title, venue,
> authorship, and submission schedule remain undecided.
> Split from the [ACG architecture draft](../2026-applied-computing-and-geosciences/01_devops_and_provenance.md).

## Working thesis

Explain how WEPPcloud's scenario and contrast workflows help users formulate,
execute, and interpret watershed-management comparisons. Organize the paper
around a scientific decision and the semantics of its comparisons, supported
by a real case study. A catalog of interface features is insufficient.

## Material transferred from the architecture paper

- OMNI scenarios and contrasts: shared base inputs, scenario clones, selective
  rebuild/rerun, contrast targeting, and comparison semantics.
- GL-Dashboard: multi-scenario visualization and differential maps; explain
  reference selection, units, and interpretation.
- Storm Event Analyzer: event-population analysis where it supports the same
  scientific case; defer a separate feature tour if it fragments the argument.
- Scenario workflow figure, comparison screenshots, and storage/wall-time
  evaluation against separately forked projects.

## Candidate outline

1. Decision problem and limitations of manually constructed comparisons.
2. Scenario and contrast definitions: shared assumptions, changed parameters,
   spatial targeting, reference cases, and comparability constraints.
3. Workflow: baseline construction, scenario execution, selective rebuilding,
   contrasts, and interactive interpretation.
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
