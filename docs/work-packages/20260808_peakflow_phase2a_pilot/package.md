# Topanga Peak-Flow Phase 2A Pilot

**Status**: Complete — local census released by design amendment (2026-08-09)
**Timezone**: UTC

## Overview

This package exercises the accepted peak-flow observer and replay protocol on
a small, stratified set of Topanga hillslopes before the full mutation census.
It validates local event pairing and candidate adjudication while measuring
the cost and limitations of watershed routing. The routing pilot failed three
original criteria; the subsequent design amendment culls routing from the
local census critical path.

## Objectives

- Freeze a preregistered pilot set containing Hill 106 and enough additional
  hillslopes to cover both solver methods, surface-return regimes, routing-path
  lengths, soils, cover, Ksat, and topographic positions.
- Run burned and undisturbed strata with `±1%` first-horizon Ksat and `±0.01`
  paired-ground-cover probes, mutating one hillslope per run.
- Demonstrate correct outer event joins, routing closure, hydrograph volume
  accounting, observer-generated no-surplus packets, and stop dispositions.
- Adaptively bracket and replay at least one known-positive candidate.
- Measure storage and runtime well enough to project the full Topanga census.

## Scope

### Included

- Topanga burned-base and undisturbed-Omni strata.
- Eight preregistered pilot hillslopes, including Hill 106.
- First-horizon Ksat and paired `inrcov`/`rilcov` probes only.
- Local hillslope, downstream-channel, and outlet observations.
- Full-history mutations plus frozen-event replay for adjudicated candidates.
- The ten automatic exit criteria in the accepted Gate 2.1 disposition.

### Explicitly Out of Scope

- The full Topanga mutation census, which is a follow-on execution rather than
  part of this completed pilot package.
- Canopy and LAI probes until the initial Ksat and ground-cover mechanics pass.
- Cross-site prevalence estimates, snow sites, and single-/multiple-OFE work.
- Changes to WEPP peak-flow equations or calibration of model parameters.
- Claims that a candidate anomaly is a defect before adaptive bracketing and
  frozen-event replay establish its mechanism.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful observation and replay of legacy execution.
- **Authoritative source paths**: WEPP-Forest `src/irs.for`, `src/appmth.for`,
  and `src/hdrive.for` at `ea25ad79`; WEPPpy Phase 1 packet/replay tools.
- **Cutover proof required**: generated pilot outputs must validate mutation,
  event, forcing, routing, and storage contracts end to end.
- **Acceptance evidence type**: both generated output and frozen fixtures.

## Stakeholders

- **Primary**: WEPP and openWEPP developers and hydrology reviewers.
- **Reviewers**: WEPP stakeholders responsible for the accepted audit design.
- **Security Reviewer**: not required.
- **Informed**: Topanga investigation readers.

## Success Criteria

- [x] The pilot selection is frozen before mutation results are inspected.
- [x] Every requested mutation has a valid manifest, realized value, terminal
  status, and exact input diff.
- [x] Baseline and mutant events are outer-joined; absence is never encoded as
  numerical zero.
- [x] A real observer-generated no-surplus packet validates.
- [ ] Unmutated hillslopes and off-path channels remain unchanged.
- [ ] Every changed channel record lies on the declared downstream path.
- [ ] Local, downstream, and outlet hydrographs pass timestamp and volume
  consistency checks.
- [x] At least one known-positive candidate is adaptively bracketed and replayed
  with frozen antecedent state.
- [x] Storage and runtime projections are acceptable for the full census.
- [x] Every incomplete HDRIVE replay is stopped and explicitly dispositioned.
- [x] A machine-readable exit report records pass/fail evidence for all ten
  criteria and separately recommends or withholds full-census execution.

## Post-Pilot Design Amendment

The [local-census amendment](artifacts/study-design-amendment-local-census.md)
supersedes the original requirement that routing criteria 5–7 pass before the
local census begins. Those criteria remain failed historical evidence. The
amended census runs hillslopes only and cannot support downstream-channel or
watershed-outlet claims.

## Parameterization ADR Gate

- **Parameterization change present**: yes; diagnostic screening and routing
  comparison thresholds were introduced, while mutations remain probes rather
  than model defaults.
- **ADR required**: yes.
- **ADR links**:
  [ADR-0042](../../adrs/ADR-0042-peakflow-phase2a-screening-and-volume-floors.md).
- **Decision provenance captured**: yes; the Gate 2.1 disposition authorizes
  the probe magnitudes and staged execution.

## Dependencies

### Prerequisites

- [Gate 2.1 accepted package](../20260808_peakflow_gate21/package.md).
- Pushed WEPP-Forest observer commit `ea25ad79`.
- Frozen Topanga burned and undisturbed scenario inputs.

### Blocks

- Later canopy and LAI pilot probes.

## Related Packages

- **Depends on**: [Phase 1 assurance](../20260808_peakflow_phase1/package.md)
  and [Gate 2.1 remediation](../20260808_peakflow_gate21/package.md).
- **Related**: [multi-site audit protocol](../../investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/README.md).
- **Follow-up**:
  [durable Topanga census preparation](../20260808_peakflow_topanga_census_prep/package.md),
  followed by the active
  [Topanga census execution package](../20260809_peakflow_topanga_census_execution/package.md).

## Timeline Estimate

- **Expected duration**: one to two focused weeks.
- **Complexity**: High.
- **Risk level**: High scientific-integrity and computational-cost risk.

## Security Impact and Review Gate

- **Security impact triage**: none.
- **Dedicated security review required**: no.
- **Triage rationale**: local model execution and analysis do not change auth,
  network, queue, secret, or deployed application surfaces.
- **Security review artifact**: N/A.

## References

- [Accepted Gate 2.1 disposition](../20260808_peakflow_gate21/artifacts/gate21-review-disposition.md).
- [Phase 1 artifact contracts](../20260808_peakflow_phase1/artifacts/README.md).
- [Topanga investigation](../../investigations/2026-08-07-topanga-2025-fire-peak-flow-analysis/README.md).

## Deliverables

- Frozen pilot-selection and scenario manifests.
- Partitioned event, forcing, routing-response, and hydrograph artifacts.
- Candidate-screen and adjudication reports.
- Storage/runtime projection for the complete census.
- Machine-readable and stakeholder-readable Phase 2A exit reports.

## Follow-up Work

Execute the frozen matrix through the
[Topanga census execution package](../20260809_peakflow_topanga_census_execution/package.md)
without per-mutation watershed routing. Preserve routing failures for a sampled
follow-up after off-path isolation and channel-volume authority are repaired.
Cross-site, snow-site, and OFE work remain governed by Gates 4 and 5.

## Final Disposition

Selection `3b5778d7c9171311` completed all 64 mutation and watershed-routing
trials. The known-positive Hill 106 response was bracketed and mechanism
traced, real no-surplus and incomplete-HDRIVE paths validated, and projected
cost was acceptable. The [exit report](artifacts/phase2a-exit-report.md)
withholds the census because 34,899 off-path channel records changed and all
20 known-positive interval/daily volume comparisons exceeded tolerance. The
later [design amendment](artifacts/study-design-amendment-local-census.md)
releases a hillslope-only census while retaining that historical disposition.
