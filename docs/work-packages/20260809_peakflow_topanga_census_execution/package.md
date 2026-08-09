# Execute the Frozen Topanga Peak-Flow Census

**Status**: Completed (2026-08-09)
**Timezone**: UTC

## Overview

This package executes the 1,088 eligible local hillslope mutations frozen by
the completed Topanga census preparation package. It preserves the approved
plan unchanged, runs only an explicit complete selection with the pinned WEPP
observer, aggregates terminal and outer-joined event evidence, and publishes
eligible mutation-trial and paired-event-row screening prevalence without
watershed-routing claims.

## Objectives

- Verify the frozen plan, input authorities, observer executable, evidence
  root, and exact 1,088-trial eligible selection before model execution.
- Execute every eligible trial with bounded concurrency and hash-bound,
  resumable terminal records.
- Produce validated terminal, event-pair, candidate, and prevalence ledgers
  without changing the preregistered mutation or screening contracts.
- Complete scientific, code, QA, and security reviews before publishing the
  execution disposition.

## Scope

### Included

- Execution of the frozen Topanga Ksat and paired-cover hillslope trials.
- Minimal engine and CLI wiring needed for an explicit selection file, bounded
  workers, progress reporting, resume, aggregation, and artifact validation.
- Immutable external evidence below the frozen plan's declared evidence root.
- Outer event pairing, candidate screening, denominator accounting, compact
  committed summaries, and mutation-trial/event-row screening prevalence reporting.
- Failure recovery and reconciliation for complete, failed, stopped, or
  missing terminal records.

### Explicitly Out of Scope

- Replanning, recalculating eligibility, changing the 1,088-trial selection,
  or executing any of the 32 excluded cover trials.
- Changing mutation factors, cover deltas, screening floors, formulas, units,
  source authorities, executable identity, or serialized contracts.
- Watershed execution, routing closure, channel hydrographs, downstream-impact
  claims, canopy, LAI, snow-site, cross-site, or OFE experiments.
- Candidate mechanism adjudication beyond producing the frozen screening
  ledger; any expensive follow-up requires a separate package.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful wired execution of the prepared engine.
- **Authoritative source paths**:
  `wepppy/wepp/peakflow_census/`, `tools/peakflow_census.py`, and
  `../20260808_peakflow_topanga_census_prep/artifacts/topanga-trial-plan.json`.
- **Cutover proof required**: all 1,088 eligible frozen trial IDs reach an
  explicit terminal state under matching plan, input, executable, and schema
  hashes; all generated rows reconcile to those terminals.
- **Acceptance evidence type**: generated output plus immutable preparation and
  Phase 2A compatibility fixtures.

## Stakeholders

- **Primary**: WEPP and openWEPP developers conducting the peak-flow audit.
- **Reviewers**: hydrology reviewers and WEPPpy maintainers.
- **Security Reviewer**: required for filesystem, subprocess, concurrency, and
  recovery boundaries.
- **Informed**: future multi-site audit operators.

## Success Criteria

- [x] The canonical plan file SHA-256 is
  `32e6f5e99a77747fcdd93388302f2a5ffb496a87b764ac4505e09691955db756`
  and its plan ID is
  `b575fde4a28cf85f1d28e0dfff305472b5419fd9b3639d39dc437600617080de`.
- [x] A frozen selection enumerates exactly the 1,088 eligible trial IDs and no
  excluded or unknown ID, with byte-identical regeneration proof.
- [x] All 1,088 trials have matching complete terminals, exactly one declared
  changed input, and validated trace and hillslope-pass artifacts.
- [x] Event pairs retain outer-join semantics and reconcile to every complete
  terminal without converting missing events to zero.
- [x] Candidate and prevalence summaries recompute from immutable ledgers with
  exact scenario, family, direction, and exclusion denominators.
- [x] No watershed, route, channel, canopy, or LAI command or artifact enters
  the plan, execution tree, or conclusions.
- [x] Resume and retry preserve prior attempts and reject every hash-binding or
  evidence-root mismatch.
- [x] Focused validation, scientific, code, QA, and dedicated security reviews
  close with no unresolved medium or high finding; the attempted canonical
  broad suite remains explicitly limited by container `/tmp` ENOSPC.
- [x] The final disposition states only eligible mutation-trial and paired-event-row
  screening prevalence and clearly
  separates screened candidates from adjudicated mechanisms.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no new ADR; execution must preserve
  [ADR-0042](../../adrs/ADR-0042-peakflow-phase2a-screening-and-volume-floors.md).
- **Decision provenance captured**: yes; the frozen preparation GO disposition
  is the execution authority and the requesting operator initiated this
  separately dated package.

## Dependencies

### Prerequisites

- [Completed preparation package](../20260808_peakflow_topanga_census_prep/package.md).
- [Preparation GO disposition](../20260808_peakflow_topanga_census_prep/artifacts/preparation-disposition.md).
- Frozen plan and manifest, accepted observer executable, read-only Topanga
  authorities, and sufficient external evidence storage.

### Blocks

- Gate 3 eligible mutation-trial and paired-event-row screening prevalence and
  candidate reporting for the multi-site audit.
- Any separately authorized candidate-adjudication or sampled routing study.

## Related Packages

- **Depends on**:
  [Topanga census preparation](../20260808_peakflow_topanga_census_prep/package.md)
  and [Phase 2A pilot](../20260808_peakflow_phase2a_pilot/package.md).
- **Related**: [Phase 1 assurance](../20260808_peakflow_phase1/package.md) and
  [Gate 2.1](../20260808_peakflow_gate21/package.md).

## Timeline Estimate

- **Expected duration**: one to three focused days, including execution and
  evidence review.
- **Complexity**: High.
- **Risk level**: High data-integrity and local subprocess risk.

## Security Impact and Review Gate

- **Security impact triage**: high.
- **Dedicated security review required**: yes.
- **Triage rationale**: the package accepts an explicit selection, launches a
  pinned executable concurrently, creates and resumes a large filesystem tree,
  and aggregates untrusted partial artifacts.
- **Security review artifact**:
  `artifacts/20260809_security_review.md`.

## References

- [Completed execution ExecPlan](prompts/completed/topanga_census_execution_execplan.md).
- [Frozen Topanga plan](../20260808_peakflow_topanga_census_prep/artifacts/topanga-trial-plan.json).
- [Execution data-contract compatibility plan](artifacts/data-contract-compatibility-plan.md).
- [Preparation QA review](../20260808_peakflow_topanga_census_prep/artifacts/20260809_qa_review.md).

## Deliverables

- Preflight and immutable explicit-selection artifacts.
- External terminal, trace, hillslope-pass, and event-pair evidence.
- Compact terminal, candidate, denominator, storage, and prevalence summaries.
- Scientific, code, QA, and security review artifacts.
- Final local-census disposition and follow-up handoff.

## Follow-up Work

Candidate mechanism adjudication, cross-site replication, and any sampled
watershed-routing study require separate authorization after this package
publishes its terminal and prevalence disposition.
