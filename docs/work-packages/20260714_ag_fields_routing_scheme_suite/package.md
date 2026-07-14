# AgFields Routing Scheme Suite

**Status**: In progress - integrated management capacity/corpus milestone (2026-07-14)
**Timezone**: UTC

## Overview

The completed Concept 2 implementation preserves independent sub-field water and
sediment accounting, but the connectivity inventory for
`sacral-self-discipline` found direct channel drainage for only 3,269 of 6,626
retained sub-fields (49.3%). This package reopens Concept 1 and adds a hybrid that
uses direct outlet injection only for channel-connected sub-fields while routing
the remaining sub-fields through field-aware parent OFEs.

The runs-page UI will let a user run one routing scheme or all three. Each scheme
owns an independently repeatable output root under
`wepp/ag_fields/watershed/{concept-1,concept-2,hybrid}/`; there is no `all/`
result directory.

The geometry and mixed-source accounting spike passed. Exact management preflight
then found 141 Concept 1 parents and 59 hybrid residual parents that require more
than the current native maximum of 20 referenced yearly scenarios after structural
deduplication. The package now owns the coordinated forest hillslope-capacity
increase and complete management-corpus validation, including correction of
proven invalid AgFields source values or evidence-driven forest numerical
hardening. UI/API/RQ wiring remains gated; fields, rotations, and failures are not
silently dropped, coerced, or substituted with Concept 2. See the
[Concept 1 feasibility evidence](artifacts/2026-07-14_concept1_feasibility.md) and
[management capacity/corpus plan](artifacts/2026-07-14_management_capacity_and_corpus_validation_plan.md).

## Objectives

- Implement a faithful field-aware OFE routing scheme (Concept 1) that preserves
  the accepted parent plan and routes represented field loads through downstream
  OFEs.
- Implement a connectivity-aware hybrid that uses Concept 2 for a sub-field when
  at least one generated per-cell flowpath enters a channel directly and Concept
  1 otherwise.
- Preserve source area exactly in every parent, including mixed hybrid parents;
  never inject connected sources on top of an unchanged full-area Concept 1
  source.
- Add a description-first UI choice for Concept 1, Concept 2, hybrid, or all, with
  Concept 2 as the backward-compatible default.
- Write scheme-specific state, manifests, watershed outputs, and evaluation
  evidence without changing baseline or independent AgFields artifacts.
- Produce generated-output evidence on
  `/wc1/runs/sa/sacral-self-discipline` for Mariana Dobre's science evaluation.

## Scope

### Included

- Parent-level one-dimensional OFE planning, eligibility diagnostics, explicit
  breakpoint slope segmentation, and multi-OFE soil/management synthesis for
  Concept 1.
- A synchronized `/workdir/wepp-forest_260430_baseline` hillslope management
  capacity increase selected from the complete Concept 1/hybrid corpus, plus
  matching forest release/vendoring and WEPPpy generation limits.
- Complete corpus parsing/execution with stable classification of capacity/parse,
  invalid-input, numerical-model-state, and environment/fixture failures.
- Canonical AgFields management-ingest validation for objectively invalid source
  values and forest ablation hardening for finite-input numerical producer faults,
  with no undocumented science mutation.
- An additive Peridot connectivity-detail output that reuses the existing direct
  channel-drainage classifier and identifies every retained sub-field
  deterministically.
- Hybrid parent composition for pure Concept 1, pure Concept 2, and mixed parents,
  with explicit residual-area accounting and no silent scheme substitution.
- A shared scheme interface over the existing Concept 2 integrator and the new
  Concept 1/hybrid implementations.
- Additive NoDb state, RQ jobs, rq-engine payloads, runs-page controls, result
  links, clear actions, staleness, and failure provenance for each scheme.
- The fixed scheme roots:
  - `wepp/ag_fields/watershed/concept-1/`
  - `wepp/ag_fields/watershed/concept-2/`
  - `wepp/ag_fields/watershed/hybrid/`
- Unit, integration, frontend, queue-contract, security, generated-output, and
  compatibility validation.
- Updates to AgFields design, module, UI, API, output-scope, and operator
  documentation affected by the implementation.

### Explicitly Out of Scope

- Replacing the independent per-sub-field AgFields runs or their canonical
  outputs.
- Treating the direct-channel classifier as a sediment-delivery ratio, buffer
  efficiency model, travel-time estimate, or science acceptance criterion.
- Silently falling back from an ineligible Concept 1 or hybrid parent to another
  routing scheme.
- Automatically moving, rewriting, or deleting the completed legacy Concept 2
  tree at `wepp/ag_fields/watershed/{runs,output,manifest}`.
- Making one scheme the scientific default based on engineering results alone;
  Mariana owns the science disposition.
- Extending the standard reports to AgFields scheme results unless the canonical
  output-scope contract and its route/report tests are updated in the same change.
- General two-dimensional field routing. Concept 1 remains a documented
  one-dimensional abstraction of the parent hillslope.

## Implementation Fidelity and Evidence

- **Fidelity target**: `faithful implementation`. A planner-only or surrogate
  Concept 1 is a non-closable intermediate milestone.
- **Authoritative source paths**:
  `wepppy/weppcloud/routes/usersum/weppcloud/ag_field-mod.md`,
  `wepppy/nodb/mods/ag_fields/watershed_integration.py`,
  `/workdir/peridot/src/subfield_channel_connectivity.rs`, and the current
  WEPPpy/wepppyo3 MOFE synthesis paths named in the active ExecPlan.
- **Cutover proof required**: the authenticated UI/API/RQ path must create current
  results in each selected scheme root, hydrate independent per-scheme state, and
  leave the protected baseline, independent AgFields, and legacy Concept 2 trees
  byte-identical.
- **Acceptance evidence type**: `both`; focused fixtures and generated output from
  the designated dev project are required.
- **Current feasibility disposition**: `implementation expanded`; planning,
  explicit-breakpoint synthesis, and one real mixed-parent native run pass.
  Milestone 2B must increase the supported binary capacity and run every required
  management/input tuple before production routing resumes.

## Routing Scheme Contract

The machine identifiers accepted at the Python/API boundary are `concept_1`,
`concept_2`, and `hybrid`. Their filesystem slugs are `concept-1`, `concept-2`,
and `hybrid`. The UI-only value `all` expands to those three identifiers in that
stable order and never appears in a result path or persisted scheme manifest.

The exact initial visible labels are:

- **Field-aware hillslope routing (routes fields through downstream OFEs)** -
  Concept 1.
- **Direct sub-field outlet injection (preserves independent sub-field results;
  no buffer routing)** - Concept 2.
- **Connectivity-aware mixed routing (injects channel-connected fields; routes
  other fields through OFEs)** - hybrid.
- **Run all routing schemes (writes three separate results for comparison)** -
  sequentially enqueue all three schemes.

Concept 2 is selected when an old client omits the scheme and is the initial UI
default. This preserves the behavior of the completed route while making its
physical limitation explicit in the label.

The hybrid classifier is the existing Peridot definition: a retained sub-field is
channel-connected when at least one of its generated per-cell flowpaths has a
valid D8 successor outside the sub-field and that first outside cell is a channel.
Positive cells in an explicit channel mask take precedence when supplied;
otherwise a SUBWTA identifier ending in `4` identifies a channel. This topology
rule is not a delivery or trapping estimate.

For a mixed parent, connected sub-fields become Concept 2 PASS sources. The
Concept 1 source may represent only the residual parent area after those connected
areas are removed. The weighted merge must close to the parent raster area. A
whole-parent Concept 1 PASS must not be uniformly scaled as a hidden shortcut, and
connected PASS files must not be added to a full-area Concept 1 PASS. If a
defensible residual Concept 1 geometry cannot be generated, the hybrid scheme
fails that parent with explicit manifest provenance.

## Stakeholders

- **Primary / decision owner**: Roger Lew, WEPPpy maintainer.
- **Scientific evaluator**: Mariana Dobre.
- **Implementers**: Codex and WEPPpy/Peridot maintainers.
- **Reviewers**: WEPPpy, Peridot, wepppyo3, frontend, and RQ maintainers.
- **Security Reviewer**: Assigned before route/RQ implementation closes.
- **Informed**: AgFields users and report/output-scope maintainers.

## Success Criteria

- [ ] ADR-0019 is accepted with evidence-backed Concept 1 fit parameters and the
  exact hybrid routing rule before those parameters control the wired UI path.
- [ ] Peridot emits deterministic per-sub-field connectivity details from explicit
  resources while preserving the existing summary CLI contract and test suite.
- [ ] Concept 1 produces parseable, internally consistent slope, soil,
  management, hillslope, PASS, watershed, and interchange artifacts from an
  accepted `ofe_plan.parquet`.
- [ ] ADR-0019 records an evidence-backed synchronized hillslope capacity; the
  forest include family, release binary, and WEPPpy guard agree exactly.
- [ ] Every generated Concept 1 and hybrid management/input tuple parses and runs
  without capacity, invalid-input, floating-point, non-finite, or invalid-producer
  failures; every correction has boundary-appropriate provenance and regression
  evidence.
- [ ] Hybrid parents use the documented pure/mixed composition rules, and every
  parent closes its represented source area to the target raster area without
  overlap or omission.
- [ ] Ineligible Concept 1 or hybrid parents fail explicitly with stable reason
  codes; no implementation path silently substitutes Concept 2 or rescales a
  whole-parent Concept 1 response.
- [ ] The runs page exposes the four exact description-first choices and hydrates
  separate status, staleness, failure, clear, and browse state for every scheme.
- [ ] An omitted API scheme runs Concept 2; `all` expands to three serialized jobs
  and returns an additive scheme-to-job-id mapping while preserving the canonical
  RQ response/error envelope.
- [ ] Each successful scheme writes only under its fixed root, and clearing one
  scheme cannot delete another scheme, the legacy Concept 2 tree, baseline WEPP,
  or independent AgFields data.
- [ ] `sacral-self-discipline` generates all three complete result trees and a
  comparison bundle for Mariana, with protected-tree hashes unchanged.
- [ ] Focused and broad Python, Rust, frontend, stub, RQ graph, documentation, and
  security gates pass with no unresolved medium/high security findings.

## Parameterization ADR Gate

- **Parameterization change present**: `yes`
- **ADR required**: `yes`
- **ADR link**:
  [ADR-0019: AgFields Field-Aware OFE and Connectivity-Aware Hybrid Routing](../../adrs/ADR-0019-agfields-field-aware-ofe-hybrid-routing.md)
- **Decision provenance captured**: `yes` for the scheme/classifier and measured
  engineering rules; production acceptance remains pending a management-limit
  decision and owner acceptance.

The ADR remains Proposed. The spike established a 1-20 OFE engineering limit,
exact source representation/positive overlap/area closure gates, and
length-preserving residual geometry. Fit/error measures remain science diagnostics
for Mariana rather than undocumented rejection thresholds. The complete corpus
inventory must now establish and validate the synchronized forest management
capacity; increasing binary capacity does not increase the 20-OFE planner limit.
The existing user-visible sub-field minimum-area setting remains the retention
threshold; this package must not introduce a second hidden small-field filter.

## Dependencies

### Prerequisites

- [AgFields Concept 2 Watershed Integration](../20260713_ag_fields_concept2_watershed_integration/package.md),
  including ADR-0018 and the weighted PASS combiner.
- [AgFields Flowpath-to-Channel Connectivity Inventory](../20260713_ag_fields_flowpath_channel_connectivity/package.md),
  including Peridot commit `8343b8f` and the 49.3% dev-project result.
- Existing WEPPpy MOFE slope, soil, management, map, and execution code.
- Current parent WEPP inputs and independent AgFields runs for the designated dev
  project.
- `/workdir/wepp-forest_260430_baseline` source/build/release workflow and its
  numerical ablation protocol. Its unrelated detached dirty baseline is preserved
  and explicitly dispositioned before canonical rebuild or staging.

### Blocks

- Side-by-side scientific comparison of the three AgFields watershed-routing
  schemes.
- Any later decision about which scheme or schemes should be promoted beyond
  experimental labeling.

## Related Packages

- **Depends on**: [AgFields Backend Readiness](../20260709_ag_fields_backend_readiness/package.md)
- **Depends on**: [AgFields Runs-Page UI](../20260709_ag_fields_runs_page_ui/package.md)
- **Related**: [Roads NoDb Inslope E2E](../20260323_roads_nodb_inslope_e2e/package.md)
- **Related evidence**: [AgFields Flowpath-to-Channel Connectivity Inventory](../20260713_ag_fields_flowpath_channel_connectivity/package.md)

## Timeline Estimate

- **Expected duration**: 3-6 focused weeks across Peridot, wepppyo3, WEPPpy,
  frontend, and generated-output evaluation.
- **Complexity**: High.
- **Risk level**: High. Concept 1 fit and mixed-parent residual geometry are the
  main feasibility risks; queue/subprocess/path changes are the main operational
  risks.

## Security Impact and Review Gate

- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: The package changes authenticated mutation payloads,
  scheme-selected run-tree writes and deletion, RQ job orchestration, worker
  subprocess execution, NoDb concurrency, and browser-visible artifact links.
- **Security review artifact**:
  [2026-07-14 security review](artifacts/2026-07-14_security_review.md)

## References

- `wepppy/weppcloud/routes/usersum/weppcloud/ag_field-mod.md` - authoritative
  model, UI, and artifact contract.
- `wepppy/nodb/mods/ag_fields/watershed_integration.py` - implemented Concept 2
  parent materialization and watershed rerun.
- `wepppy/nodb/mods/ag_fields/ag_fields.py` - current singular integration facade
  and persisted state to evolve additively.
- `wepppy/microservices/rq_engine/ag_fields_routes.py` and
  `wepppy/rq/ag_fields_rq.py` - authenticated enqueue and worker boundaries.
- `wepppy/nodb/mods/ag_fields/ui_control_layout.md` - runs-page behavioral
  contract.
- `/workdir/peridot/src/subfield_channel_connectivity.rs` - canonical topology
  classifier.
- `/home/workdir/wepppyo3/wepp_interchange/src/mofe.rs` - current slope
  segmentation kernel to extend additively for explicit breakpoints.
- `artifacts/2026-07-14_scheme_artifact_compatibility_plan.md` - required
  compatibility and regression plan.
- `prompts/active/ag_fields_routing_scheme_suite_execplan.md` - active
  implementation plan.

## Deliverables

Completed engineering substrate and evidence:

- deterministic Peridot connectivity detail for all retained sub-fields;
- read-only Concept 1/hybrid planner and full-project census;
- release-tested explicit-breakpoint wepppyo3 segmentation and WEPPpy wrapper;
- Concept 1 input-synthesis and reference-safe management-deduplication spike;
- real mixed-parent native WEPP and ADR-0018 closure proof; and
- [feasibility evidence and stop decision](artifacts/2026-07-14_concept1_feasibility.md).
- [management capacity/corpus compatibility and validation plan](artifacts/2026-07-14_management_capacity_and_corpus_validation_plan.md).

These deliverables are not a user-facing routing implementation. Scheme roots,
state, RQ/API orchestration, UI choices, and generated all-project results remain
unimplemented until the expanded management-capacity/corpus milestone and later
wired acceptance pass.

## Follow-up Work

The binary limit is no longer deferred to a separate package. Milestone 2B of the
active ExecPlan owns inventory, capacity selection, forest changes, data/numerical
failure resolution, release/vendoring, and complete corpus evidence. Mariana's
scientific evaluation may later produce use constraints, scheme-comparison
metrics, or a promotion/deprecation decision after generated engineering results
exist; none are inferred here.
