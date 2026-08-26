# Batch OMNI Multi-OFE Treatment Propagation

**Status**: Closed (2026-08-06)
**Timezone**: UTC

## Overview

Batch Runner projects using multi-OFE landuse currently select OMNI thinning and
prescribed-fire treatments at the hillslope level but leave the per-OFE landuse
mapping and synthesized WEPP management files unchanged. This package makes the
treatment mutation propagate through the multi-OFE representation so scenario
WEPP inputs and outputs reflect the selected canopy and ground cover.

## Objectives

- Apply an OMNI treatment independently to every eligible OFE within each
  selected hillslope while preserving ineligible OFEs.
- Rebuild multi-OFE management and soil artifacts after treatment mutation.
- Prove propagation reaches generated `wepp/runs/*.man` inputs.
- Preserve existing single-OFE treatment behavior.

## Scope

### Included

- `Treatments.build_treatments()` multi-OFE thinning, prescribed-fire, and mulch
  landuse mutation.
- Multi-OFE management and soil artifact regeneration required by OMNI runs.
- Batch Runner OMNI regression tests and durable operator/developer docs.

### Explicitly Out of Scope

- Changing treatment canopy-cover or ground-cover parameter values.
- Reprocessing or mutating existing production runs.
- Changing RQ dependency wiring, public routes, or analytics calculations.
- Deploying the completed change to production.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful extraction
- **Authoritative source paths**: `wepppy/nodb/mods/treatments/treatments.py`,
  `wepppy/nodb/core/landuse.py`, and `wepppy/nodb/core/wepp.py`
- **Cutover proof required**: selected multi-OFE forest segments use treatment
  management keys and generated `wepp/runs/*.man` differs from undisturbed input
- **Acceptance evidence type**: both

## Stakeholders

- **Primary**: Batch Runner operators and OMNI scenario consumers
- **Reviewers**: WEPPpy NoDb and WEPP model maintainers
- **Security Reviewer**: not required
- **Informed**: Utility Watershed Analytics maintainers

## Success Criteria

- [x] Multi-OFE treatments update eligible `domlc_mofe_d` entries and preserve
  ineligible entries.
- [x] `landuse/hill_<topaz_id>.mofe.man` is rebuilt from treated OFE mappings.
- [x] Generated `wepp/runs/p<wepp_id>.man` contains treated canopy and ground
  cover rather than the undisturbed values.
- [x] Targeted and full regression gates pass.
- [x] Batch Runner documentation states the multi-OFE propagation contract.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: yes; operator requested this remediation in
  the 2026-08-06 Codex session after production evidence identified the defect

## Dependencies

### Prerequisites

- Existing OMNI scenario cloning and Treatments mappings.
- Existing Landuse multi-OFE synthesis implementation.

### Blocks

- Trustworthy thinning and prescribed-fire comparisons for affected Batch
  Runner projects using `disturbed_wbt` multi-OFE configuration.

## Related Packages

- **Depends on**: none
- **Related**: none identified
- **Follow-up**: production rebuild/reprocessing is an operator action outside
  this package

## Timeline Estimate

- **Expected duration**: one focused session
- **Complexity**: Medium
- **Risk level**: Medium

## Security Impact and Review Gate

- **Security impact triage**: none
- **Dedicated security review required**: no
- **Triage rationale**: internal model-input propagation only; no route, auth,
  queue, path-acceptance, secret, or external-egress behavior changes
- **Security review artifact**: N/A

## Hardening and Callus Softening

- **Failure signature(s)**: treatment logs report changed `domlc_d`, while
  `domlc_mofe_d`, `landuse/hill_*.mofe.man`, generated `wepp/runs/*.man`, and
  scenario summary Parquet files remain identical to undisturbed
- **Related prior hardening efforts**: none identified
- **Health signals**: treated OFE keys and generated management-file cover
  values differ from undisturbed
- **Danger signals**: non-forest OFEs are overwritten or single-OFE behavior
  changes
- **Observation window**: targeted generated-output tests plus the next Batch
  Runner OMNI validation run
- **Temporary calluses introduced**: none
- **Callus softening hypothesis**: N/A

## References

- `wepppy/nodb/README.batch-runner.md` - Batch Runner behavior
- `wepppy/nodb/mods/treatments/treatments.py` - treatment mutation
- `wepppy/nodb/core/landuse.py` - multi-OFE synthesis
- `wepppy/nodb/core/wepp.py` - generated WEPP input preparation

## Deliverables

- Segment-aware treatment propagation for thinning, prescribed fire, and mulch.
- Explicit regeneration of multi-OFE management and disturbed-soil artifacts.
- Mixed-OFE preservation and generated `wepp/runs/*.man` regression coverage.
- Updated Batch Runner multi-OFE validation guidance.

## Follow-up Work

- Deploy through the normal release process, then rebuild the affected
  `nasa-roses-202606-psbs/OR-18` OMNI scenarios and compare outputs. Deployment
  and production mutation were not authorized by this package.

## Closure Notes

**Closed**: 2026-08-06

**Summary**: Multi-OFE OMNI treatments now mutate eligible OFE assignments,
preserve unrelated segments, rebuild synthesized management and soil inputs,
and propagate the result into WEPP run files. The final full repository gate
passed with 5,895 tests, 61 skips, and 12 passing subtests.

**Lessons Learned**: A changed scalar `domlc_d` is insufficient evidence for a
multi-OFE run. Generated `hill_*.mofe.*` and `wepp/runs/*` artifacts must be part
of treatment-path regression evidence.

**Archive Status**: The completed ExecPlan is retained under
`prompts/completed/`.
