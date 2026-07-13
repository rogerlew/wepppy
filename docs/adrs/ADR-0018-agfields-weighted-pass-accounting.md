# ADR-0018: AgFields Weighted PASS Accounting

Status: Accepted
Date: 2026-07-13

## Context

AgFields currently runs each retained field/hillslope intersection as an
independent WEPP hillslope. Those simulations preserve each sub-field's Peridot
representative slope and crop rotation, but their water and sediment do not enter
the parent watershed run. Two integration concepts were assessed in
`wepppy/weppcloud/routes/usersum/weppcloud/ag_field-mod.md`.

Concept 2 combines independent sub-field PASS records with the uncovered fraction
of the parent hillslope PASS and reruns watershed WEPP. Concept 1 would instead
collapse the field mosaic into ordered OFEs on the parent profile. The maintainer
selected Concept 2 for implementation and deferred Concept 1. Mariana Dobre will
perform the scientific evaluation after the implementation produces runnable
results.

## Decision

Implement Concept 2 as explicit area-weighted outlet injection. For parent area
`A_parent`, retained field raster areas `A_i`, and sub-field modeled PASS areas
`A_modeled_i`, use:

```text
A_background = A_parent - sum(A_i)
baseline_scale = A_background / A_parent
subfield_scale_i = A_i / A_modeled_i
```

Scale extensive water-volume, groundwater-volume, sediment-mass, and peak-rate
quantities by the applicable source scale. Reconstruct runoff, subsurface-flow, and
tile-drainage depths from combined volumes and target parent area. Reconstruct each
sediment concentration from combined class mass and runoff volume, and reconstruct
particle fractions with source sediment-mass weights. Superimpose scaled triangular
source hydrographs to obtain combined peak runoff and its peak time. The normative
field-by-field rules are in
`docs/work-packages/20260713_ag_fields_concept2_watershed_integration/artifacts/pass_field_semantics.md`.

Legacy `E11.5` row serialization and `E10.5` header-area serialization retain five
significant decimal digits in the Fortran `0.ddddd` mantissa. Closure therefore
uses the value-specific half-ULP budget
`0.5 * 10^(floor(log10(abs(x))) - 4)`, plus a bounded floating-point term,
rather than a tunable percentage. Derived sediment-mass and depth-volume identities
use the documented product-of-rounded-operands bound. Event budgets sum into the
full-run budget. A parent combine fails before replacement when any reparsed
conserved quantity exceeds its calculated budget.

Do not apply a delivery ratio, buffer correction, or other uncalibrated heuristic.
The combined source is delivered at the parent hillslope outlet, after which normal
watershed and channel routing applies. Preserve source-level accounting in additive
manifests because the combined parent PASS no longer retains source identity.

Materialize parent PASS files under the isolated AgFields watershed tree from the
current prepared parent WEPP inputs when baseline PASS files are unavailable or
were removed after interchange. Never rewrite baseline or independent sub-field
run/output trees. Concept 1 is not an implementation or validation dependency.

`gwbfv` and `gwdsv` are extensive m3 volumes. `clot`, `slot`, `saot`, `laot`, and
`sdot` are unitless particle fractions, not rates or percentages. Header particle
diameters and phosphorus concentrations must match across sources and are copied
from the target parent; v1 does not silently average heterogeneous chemistry.

## Decision Provenance

- Decision Venue: Codex API conversation, 2026-07-13 12:37 PDT
- Participants Present: Roger Lew, Codex
- Decision Owner(s): Roger Lew, WEPPpy maintainer
- Scientific Evaluator: Mariana Dobre
- Implementer(s): Codex

## Change Summary

Old behavior: independent AgFields sub-field PASS outputs are summarized at field
scale but are not routed through the parent watershed.

New behavior: an isolated watershed-integration stage will area-weight the parent
background and every retained sub-field source, verify source/event/run closure,
write one combined PASS per parent hillslope, and rerun watershed WEPP. Concept 1
remains deferred.

## Rationale

Concept 2 retains the independent sub-field simulations and their water and
sediment accounting. It avoids reducing a two-dimensional field mosaic to
quantized one-dimensional OFE bands and has a smaller, testable implementation
kernel. Its known limitation is delivery-path fidelity between a field and the
parent outlet; that limitation is explicit and will be assessed scientifically
after engineering delivery.

## Alternatives Considered

1. Rebuild parent hillslopes as field-aware OFEs - deferred because arbitrary field
   mosaics require lossy band assignment and a substantially larger implementation.
2. Require a Concept 1 prototype as a validation oracle - rejected because Mariana
   will perform the scientific evaluation from Concept 2 outputs and geometry.
3. Apply an empirical buffer or sediment-delivery correction - rejected because no
   calibrated transfer function has been approved.
4. Modify the existing Roads PASS combiner semantics - rejected because Roads owns
   an additive, unweighted contract that must remain stable.

## Consequences

Concept 2 preserves represented source area and weighted water/sediment accounting,
but it does not simulate runon, deposition, or trapping below a field. Background
response is approximated by scaling the full parent hillslope result to uncovered
area. Integrated outputs therefore require explicit outlet-injection labeling and
scientific-use guidance from Mariana's evaluation.

The implementation adds an isolated run-artifact tree, a weighted native kernel,
and additive NoDb/RQ/API/UI state. Legacy projects remain readable because absence
of the new state means "not run."

## Evidence

- `docs/work-packages/20260713_ag_fields_concept2_watershed_integration/`
- `/wc1/runs/sa/sacral-self-discipline`
- The dev project contains 6,626 independent sub-field PASS files spanning 1,869
  affected parent hillslopes. Its retained field raster area is 113,774,400 m2;
  affected parent area is 176,981,400 m2; no parent is overcovered.
- Peridot metadata on that project closes `length * width` to raster area within
  `5.9e-11` m2 per sub-field.
- The accepted semantic table cites the WEPP producer, watershed consumer,
  sediment producer, binary PASS contract, and owned Rust parser for every field.

## Risk and Rollback Notes

Primary risks are incorrect PASS column classification, serialization drift,
stale/mismatched calendars, and scientific over-interpretation of outlet injection.
Mitigate them with the field-semantics table, parser round-trip tests, explicit
source manifests, event/run closure diagnostics, isolated outputs, and user-facing
limitations.

Roll back by disabling/removing the separate watershed-integration stage and its
additive UI/API exposure. Existing baseline and independent AgFields artifacts are
unchanged, and the isolated `wepp/ag_fields/watershed/` tree can be cleared without
data migration.

## Implementation Notes

The active ExecPlan is
`docs/work-packages/20260713_ag_fields_concept2_watershed_integration/prompts/active/ag_fields_concept2_watershed_integration_execplan.md`.
The weighted kernel and its diagnostics must use the accepted semantic-table
version `ag_fields_pass_semantics_v1` and algorithm name `ag_fields_v1`. A change
to any formula, zero-volume rule, or closure budget requires a superseding ADR
revision before implementation changes.
