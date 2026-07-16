# AgFields Sub-field WEPP Interchange Integration

**Status**: Complete (2026-07-16)
**Timezone**: UTC

## Overview

The AgFields stage-4 RQ worker currently finishes after running WEPP for each
sub-field. It does not convert the resulting `H*.{pass,ebe,element,loss,soil,wat}.dat`
files into Parquet interchange resources. The native writers also identify every
`H<n>` file only through the existing `wepp_id` column, while an AgFields `H<n>`
uses `n` as the sub-field execution identifier and needs explicit `field_id` and
`sub_field_id` provenance. An individual sub-field is not a TOPAZ hillslope and
must not be assigned its parent hillslope's `topaz_id`.

This package adds dedicated AgFields writer APIs to
`wepppyo3.wepp_interchange`, adds a specialized WEPPpy AgFields interchange
orchestrator, and calls that orchestrator inside `run_ag_fields_wepp_rq` before
the job is stamped complete. The ordinary hillslope interchange path must retain
its current API behavior, schemas, values, and publication locations.

## Objectives

- Generate all six AgFields hillslope Parquet resources after successful
  sub-field WEPP execution.
- Propagate required `field_id` and `sub_field_id` values into every generated
  row without claiming that a sub-field has its own `topaz_id`.
- Preserve the six existing ordinary native writer signatures, schemas, and
  behavior without routing ordinary calls through the new AgFields APIs.
- Fail before publication on missing, duplicate, extra, or inconsistent identity
  mappings, and keep the RQ completion timestamp unset if interchange fails.
- Validate the released native extension and the wired RQ path against the
  `sacral-self-discipline/disturbed9002_wbt` forest project.

## Scope

### Included

- The six native bulk hillslope writers in `/home/workdir/wepppyo3/wepp_interchange`.
- Six additive AgFields-native writer APIs that accept coupled
  `(path, field_id, sub_field_id)` source descriptors and reuse the existing
  parser/scientific logic without changing the ordinary public APIs.
- AgFields schemas with first-class `field_id` and `sub_field_id` columns, no
  fabricated `topaz_id` or parent `wepp_id`, and an explicit dataset-kind/schema
  marker.
- A specialized WEPPpy orchestrator that reads
  `ag_fields/sub_fields/fields.parquet`, validates one-to-one identity coverage,
  writes into a unique staging directory, validates all six datasets, and then
  publishes the completed bundle.
- The call from `wepppy/rq/ag_fields_rq.py::run_ag_fields_wepp_rq`, including
  status/error behavior and additive result provenance.
- Canonical native release refresh, import-origin verification, schema/contract
  tests, generated-output evidence, and related WEPPpy/WEPPpyo3 documentation.
- Independent code-review and QA review artifacts before closeout.

### Explicitly Out of Scope

- Treating a parent TOPAZ hillslope id as the sub-field's own `topaz_id`.
- Changing AgFields delineation, crop schedules, WEPP parameterization, routing
  schemes, or watershed-integration science.
- Changing ordinary `wepp/output/interchange` or roads interchange schemas.
- Adding a new RQ child job, route, UI stage, external dependency, or queue edge.
- Converting `H*.plot.dat`; it is not one of the current six hillslope
  interchange families.
- Deleting raw AgFields reports after conversion. The watershed-routing stages
  still consume raw PASS data.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful wired behavior
- **Authoritative source paths**:
  `wepppy/rq/ag_fields_rq.py`,
  `wepppy/nodb/mods/ag_fields/ag_fields.py`,
  `wepppy/wepp/interchange/`, and
  `/home/workdir/wepppyo3/wepp_interchange/`
- **Cutover proof required**: the actual AgFields stage-4 RQ job must publish a
  terminal success only after all six interchange datasets are present and
  validated in the AgFields output tree.
- **Acceptance evidence type**: both fixture and generated-output

## Stakeholders

- **Primary**: WEPPcloud AgFields and native interchange maintainers
- **Reviewers**: independent WEPPpy/WEPPpyo3 code reviewer and QA reviewer
- **Security Reviewer**: not required by initial low-impact triage; revisit if a
  new route, queue edge, path input, or subprocess behavior is introduced
- **Informed**: forest operators and downstream Parquet consumers

## Success Criteria

- [x] Each of the six existing native bulk writer calls has the same signature,
  schema, metadata, row values, ordering, and output behavior as the pre-change
  release.
- [x] Each dedicated AgFields writer emits exact
  `field_id` and `sub_field_id` values from `fields.parquet`; no parent
  `topaz_id` is emitted as sub-field identity.
- [x] WEPPpy rejects missing/extra descriptor sets; the native AgFields boundary
  rejects duplicate, non-integer, range-invalid, or path-mismatched descriptors
  before a final target is published.
- [x] The WEPPpy orchestrator requires exactly one identity for every input id,
  requires all six raw families to cover the same sub-field set, and publishes
  the six-file bundle failure-atomically.
- [x] `run_ag_fields_wepp_rq` runs interchange after WEPP, stamps
  `TaskEnum.run_ag_fields` only after interchange succeeds, preserves raw
  reports, and preserves the existing explicit RQ error/status contract.
- [x] The ordinary WEPPpy hillslope interchange schema snapshots and targeted
  consumer tests pass without baseline snapshot changes.
- [x] The paired `wepppyo3` release is rebuilt, its provenance is updated, and
  container/runtime import checks prove the intended shared object is loaded.
- [x] Generated acceptance on `sacral-self-discipline` proves six families each
  receive 6,626 coupled descriptors spanning 2,169 fields; every row-bearing
  identity matches the mapping, zero-row sources are explicit without synthetic
  measurements, and baseline/watershed scheme artifacts are unchanged.
- [x] `wctl check-rq-graph` reports no graph drift, confirming that the change
  stays inside the existing stage-4 job.
- [x] Independent review and QA artifacts have no unresolved high or medium
  findings.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: yes, in this package's tracker and ExecPlan

## Dependencies

### Prerequisites

- The completed native-only interchange cutover in
  [`20260715_wepppyo3_only_interchange`](../20260715_wepppyo3_only_interchange/package.md).
- The completed AgFields backend and routing packages, especially
  [`20260715_agfields_watershed_parent_job`](../20260715_agfields_watershed_parent_job/package.md).
- A buildable `/home/workdir/wepppyo3` checkout and the canonical
  `release/linux/py312/wepppyo3` release workflow.
- At least enough free `/wc1` space for one staged AgFields interchange bundle;
  the 2026-07-16 discovery baseline was 1.1 TB free.

### Blocks

- AgFields query/report consumers that need native sub-field-level Parquet data.

## Related Packages

- **Depends on**:
  [`20260715_wepppyo3_only_interchange`](../20260715_wepppyo3_only_interchange/package.md)
- **Related**:
  [`20260713_ag_fields_concept2_watershed_integration`](../20260713_ag_fields_concept2_watershed_integration/package.md)
- **Related**:
  [`20260714_ag_fields_routing_scheme_suite`](../20260714_ag_fields_routing_scheme_suite/package.md)
- **Follow-up**: none planned; downstream reporting remains separate unless
  implementation discovers a concrete consumer requirement.

## Timeline Estimate

- **Expected duration**: 3-5 focused sessions
- **Complexity**: High
- **Risk level**: Medium-High before mitigation; Low-Medium residual after all gates

## Security Impact and Review Gate

- **Security impact triage**: low
- **Dedicated security review required**: no
- **Triage rationale**: the existing authenticated route, RQ job, arguments,
  queue topology, run root, and WEPP subprocess behavior remain unchanged. The
  package adds validated native parsing and run-scoped Parquet writes. Escalate
  to `high` and create the standard security artifact if implementation adds a
  route, queue edge, user-controlled path, new subprocess, or broader file scope.
- **Security review artifact**: N/A under the current scope

## Hardening and Callus Softening

This is a missing integration rather than incident mitigation. No temporary
callus is planned. The failure signature is a successful AgFields stage-4 job
with raw reports under `wepp/ag_fields/output/` but no
`wepp/ag_fields/output/interchange/` bundle.

## References

- `wepppy/rq/ag_fields_rq.py` - stage-4 RQ worker and completion timestamp
- `wepppy/nodb/mods/ag_fields/ag_fields.py` - sub-field source identities and raw
  output paths
- `wepppy/wepp/interchange/hill_interchange.py` - ordinary hillslope aggregate
  behavior that must remain stable
- `wepppy/wepp/interchange/_rust_interchange.py` - required native boundary
- `/home/workdir/wepppyo3/wepp_interchange/src/lib.rs` - PyO3 bulk-writer APIs
- `/home/workdir/wepppyo3/wepp_interchange/src/schema.rs` - canonical native
  hillslope schemas
- `tests/wepp/interchange/fixtures/schema_snapshots/` - ordinary interchange
  schema guard
- `docs/work-packages/20260716_agfields_subfield_interchange/artifacts/2026-07-16_schema_compatibility_plan.md`
  - additive schema and downstream propagation plan
- `/wc1/runs/sa/sacral-self-discipline` - local forest acceptance run
- <https://wc.bearhive.duckdns.org/weppcloud/runs/sacral-self-discipline/disturbed9002_wbt/>
  - browser-facing acceptance project

## Deliverables

- Dedicated native AgFields writer support and canonical release refresh
- WEPPpy AgFields-specific interchange orchestrator and RQ wiring
- Rust, Python binding, WEPPpy facade, RQ, schema, and generated-output tests
- Updated native provenance/module docs and AgFields/interchange contract docs
- Generated acceptance, code-review, and QA artifacts

## Follow-up Work

The generic rq-engine endpoint catalogs omit the existing AgFields route family,
so operator clients cannot discover schema/default/error documents for
`rq_engine_agfields_run_wepp`. Add those established routes to the catalog in a
separate agent-usability change; this package validated the functional route
with an authenticated empty payload and did not broaden queue/API scope during
closeout.
