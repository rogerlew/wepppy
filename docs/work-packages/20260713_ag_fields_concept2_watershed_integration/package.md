# AgFields Concept 2 Watershed Integration

**Status**: Engineering complete; scientific evaluation pending (2026-07-14)
**Timezone**: UTC

## Overview

This package implements the selected AgFields Concept 2 watershed integration.
Each independent sub-field WEPP result remains the canonical field-scale source;
an area-weighted combiner merges those sources with the uncovered parent response,
writes one parent PASS per hillslope, and reruns watershed WEPP under an isolated
AgFields output tree.

Engineering delivery proves area, water, and sediment accounting plus executable
integration. Mariana Dobre owns the subsequent scientific evaluation. Concept 1
and its field-aware OFE implementation are deferred and are not prerequisites for
this package.

## Objectives

- Add a weighted, conservation-diagnosed PASS combiner to the owned `wepppyo3`
  interchange kernel without changing the Roads combiner contract.
- Add an AgFields watershed-integration collaborator that derives source areas from
  aligned rasters, materializes current parent PASS files in an isolated workspace,
  combines affected parents, stages untouched parents, and runs watershed WEPP.
- Persist additive source, event, and full-run accounting artifacts so every
  weighted contribution remains auditable after source identity is collapsed.
- Expose the operation as a separate, authenticated RQ/API/UI stage with explicit
  readiness, staleness, failure, clear, and result state.
- Produce generated-output evidence and a scientific-evaluation bundle from
  `/wc1/runs/sa/sacral-self-discipline` while leaving its existing artifacts
  unchanged.

## Scope

### Included

- A field-by-field PASS semantic table and finalized ADR-0018 scaling/closure
  contract.
- Additive Rust/PyO3 weighted PASS API, parser/writer round-trip validation,
  diagnostics, release-tree refresh, and `wepppyo3` documentation/provenance.
- Additive AgFields NoDb facade state and a dedicated watershed-integration
  collaborator rather than expanding the existing controller with one monolith.
- Isolated `wepp/ag_fields/watershed/{runs,output,manifest}` artifacts.
- Explicit parent PASS materialization from current prepared parent WEPP inputs, so
  projects remain runnable when baseline PASS files were deleted after interchange.
- Versioned Parquet/JSON manifests for source areas/scales, event closure, run
  closure, execution summary, staleness provenance, and evaluation guidance.
- Separate RQ job, rq-engine routes, state hydration, runs-page stage, browse link,
  regression coverage, queue graph/catalog updates, and security review.
- Synthetic unit/integration fixtures and real generated-output acceptance on the
  designated dev project.

### Explicitly Out of Scope

- Concept 1 OFE planning, MOFE slope/soil/management synthesis, Concept 1 fixtures,
  or using Concept 1 as a validation oracle.
- A delivery-ratio, buffer-trapping, runon, or other empirical correction.
- Mariana's scientific conclusions; this package produces and hands off the
  evaluation evidence but does not substitute engineering judgment for her review.
- Rewriting, moving, or deleting baseline `wepp/{runs,output}` or independent
  `wepp/ag_fields/{runs,output}` artifacts.
- Reclassifying standard report output scope before report consumers have an
  approved `ag_fields` scope contract.
- Weighted HBP output in v1. The isolated materialization and combined watershed
  path use legacy ASCII PASS files, matching current AgFields sub-field outputs.

## Stakeholders

- **Primary**: WEPPpy and `wepppyo3` maintainers responsible for AgFields and WEPP
  interchange.
- **Decision owner**: Roger Lew, WEPPpy maintainer.
- **Scientific evaluator**: Mariana Dobre.
- **Reviewers**: AgFields/NoDb maintainer, WEPP interchange reviewer, RQ/API/UI
  reviewer, and QA reviewer.
- **Security Reviewer**: Required before closure because the package adds queue,
  subprocess, authenticated route, and run-tree write surfaces.
- **Informed**: AgFields users and operators through updated UI and durable docs.

## Success Criteria

- [x] ADR-0018 is Accepted with every PASS field classified by units,
  extensive/intensive semantics, transformation, zero-volume behavior, and a
  serialization-derived closure tolerance.
- [x] The weighted native API leaves the existing Roads API unchanged and passes
  exact synthetic area/water/sediment identities plus parser round-trip tests.
- [x] Historical AgFields NoDb state loads without migration; new state and artifact
  schemas are additive and documented.
- [x] One integration run stages exactly one legacy PASS for every parent hillslope,
  preserves source/event/run closure within the approved tolerance, completes
  watershed WEPP, and generates required interchange resources.
- [x] Missing/deleted baseline PASS files are materialized from current prepared
  parent inputs inside the isolated tree; no baseline setting or file is rewritten.
- [x] RQ, route, state, clear, staleness, status-stream, UI, and browse behavior are
  covered and the RQ dependency graph is current.
- [x] `/wc1/runs/sa/sacral-self-discipline` produces an evaluation bundle covering
  6,626 sub-fields and 1,869 affected parents, with immutable preexisting artifacts
  and recorded generated-output evidence.
- [x] The bundle is published in the now-public run for Mariana with explicit
  outlet-injection limitations; scientific qualification remains recorded as
  pending until her disposition.
- [x] Security review has no unresolved medium/high findings and all applicable
  focused, broad, docs, and release-import gates pass.

## Parameterization ADR Gate

- **Parameterization change present**: `yes`
- **ADR required**: `yes`
- **ADR link(s)**: `docs/adrs/ADR-0018-agfields-weighted-pass-accounting.md`
- **Decision provenance captured**: `yes`

ADR-0018 is Accepted and records the final field semantics and tolerances.

## Dependencies

### Prerequisites

- Completed AgFields backend and runs-page packages from 2026-07-09.
- Current independent AgFields sub-field outputs and prepared parent WEPP inputs.
- Owned `wepppyo3.wepp_interchange` PASS parser/writer and Roads combiner precedent.
- Parent watershed structure and a WEPP executable that supports legacy ASCII PASS.

### Blocks

- Mariana's scientific evaluation of integrated AgFields watershed results.
- Any later decision to promote the result beyond explicit experimental/internal
  outlet-injection labeling.

## Related Packages

- **Depends on**: [AgFields Backend Readiness](../20260709_ag_fields_backend_readiness/package.md)
- **Depends on**: [AgFields Runs-Page UI](../20260709_ag_fields_runs_page_ui/package.md)
- **Related**: [Roads NoDb Inslope E2E](../20260323_roads_nodb_inslope_e2e/package.md)
- **Deferred**: Concept 1 requires a new package and decision if reopened.

## Timeline Estimate

- **Expected duration**: 2-4 focused weeks, including cross-repository kernel and
  generated-output validation.
- **Complexity**: High
- **Risk level**: High because PASS semantics and full-watershed execution are
  contract-sensitive, even though the selected architecture is feasible.

## Security Impact and Review Gate

- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: Adds authenticated mutation routes, RQ queue wiring, worker
  subprocess execution, and writes/serves files within a run tree.
- **Security review artifact**:
  `artifacts/2026-07-13_security_review.md`

## References

- `wepppy/weppcloud/routes/usersum/weppcloud/ag_field-mod.md` - authoritative
  selected-concept contract and delivery sequence.
- `docs/adrs/ADR-0018-agfields-weighted-pass-accounting.md` - formula and scaling
  decision.
- `wepppy/nodb/mods/ag_fields/ag_fields.py` - existing AgFields facade and sub-field
  execution.
- `/home/workdir/wepppyo3/wepp_interchange/src/hill_pass_combine.rs` - existing
  unweighted Roads combiner.
- `wepppy/nodb/mods/roads/roads.py` - isolated workspace and watershed-rerun
  precedent.
- `artifacts/2026-07-13_run_artifact_compatibility_plan.md` - required compatibility
  and downstream regression plan.

## Deliverables

- Accepted PASS semantics and ADR-0018 plus the additive weighted native API and
  refreshed py312 release.
- `AgFieldsWatershedIntegrator`, additive NoDb facade/state/stub, fixed isolated
  artifact schemas, parent materialization, watershed/interchange execution, and
  evaluation README generation.
- `agfields_run_watershed`, authenticated run/clear routes, single-flight state
  hydration, fifth runs-page stage, regenerated controller asset, and queue graph.
- Focused NoDb/RQ/route/template/Jest coverage and a passing dedicated security
  review, broad validation, and full generated-output evidence.

## Engineering Acceptance Evidence

- Final authenticated RQ job `2fc269a6-12f8-4d74-a876-0619b2ea3cf7` ran from
  2026-07-13 23:15:08 UTC to 2026-07-14 00:14:33 UTC (59 minutes 25 seconds).
  The canonical job endpoint reports `finished`; the Stage 5 state endpoint reports
  `completed`, `stale=false`, and source signature
  `8885d05b786ed85f06def046a581a8260c6e99a6a601495639c1a7383adc29cc`.
- The isolated tree contains 3,543 parent PASS files, 10,169 source rows, 11,606,490
  event-closure rows, 1,869 run-closure rows, and every required interchange
  resource. No event or run exceeds its serialization-derived budget; the maximum
  event budget ratio is `0.9999999999305551`.
- Peak observed unique allocation during the run was 6,884,441,600 bytes. The
  public evaluation bundle is under
  `wepp/ag_fields/watershed/manifest/`, including its limitation README and
  `evaluation_evidence/authoritative_{pre,post}.parquet`.
- The [public acceptance run](https://wc.bearhive.duckdns.org/weppcloud/runs/sacral-self-discipline/disturbed9002_wbt/)
  returns HTTP 200 with the expected CAPTCHA gate. The dev compose contract now
  passes the same CAP base/asset/site-key settings as production, with a compose
  regression covering the configuration.
- The pre/post inventories of baseline and independent AgFields trees are identical:
  97,734 files, 18,498,460,698 bytes, no missing/added/changed paths, and SHA-256
  `198212dd58c9301b9d0b6bcd70c980e45b1c09b64374cc7db22dac8d28477426`.
- Repository validation passed with 4,833 tests, 60 skipped; frontend validation
  passed 85 suites/621 tests; the final native kernel passed 41 Rust tests and two
  release-tree Python tests. The dedicated security review remains `pass` with no
  unresolved findings.

## Follow-up Work

- Mariana's scientific disposition and any approved use constraints.
- A separate Concept 1 work package only if explicitly reopened after evaluation.
