# Prepare the Durable Topanga Peak-Flow Census

**Status**: Closed - GO (2026-08-09)
**Timezone**: UTC

## Overview

This package prepares, but does not execute, the full Topanga hillslope
mutation census. It converts the successful Phase 2A pilot mechanics into a
site-independent, manifest-driven engine, proves that the new engine preserves
pilot results, and freezes the exact Topanga trial matrix for a separate
execution package.

## Objectives

- Replace Topanga- and pilot-specific orchestration with reusable mutation,
  execution, event-pairing, and screening interfaces.
- Define versioned study, trial-plan, terminal, and event-pair contracts that
  another site can use without changing Python source.
- Freeze every eligible Topanga Ksat and paired-cover mutation before full
  matrix outcomes exist.
- Demonstrate pilot parity and safe resume behavior with generated evidence.
- Publish a GO/NO-GO handoff that is sufficient to scaffold and execute the
  separate full-census package.

## Scope

### Included

- A reusable Python package under `wepppy/wepp/peakflow_census/` and a thin CLI
  under `tools/`.
- Site/scenario manifests, mutation planning, boundary eligibility, immutable
  identifiers, input isolation, local hillslope execution, observer parsing,
  outer event joins, screening, and artifact validation.
- A frozen Topanga local-census manifest and content-addressed trial plan.
- Tests proving the reusable engine reproduces the 64 Phase 2A pilot trials
  and metrics from immutable evidence.
- Security review of path, filesystem, and subprocess boundaries.

### Explicitly Out of Scope

- Executing the full Topanga mutation matrix.
- Per-mutation watershed routing or all-channel output retention.
- Changing screening floors, mutation magnitudes, WEPP equations, or model
  parameter defaults.
- Canopy, LAI, cross-site, snow-site, and OFE experiments.
- Confirming every screened candidate; adjudication execution belongs to the
  later census package.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful extraction.
- **Authoritative source paths**: `tools/peakflow_phase2a_pilot.py`, Phase 2A
  external evidence rooted at
  `/home/workdir/peakflow-phase2a-evidence/8162d509d69cb4da`, and the accepted
  observer/replay contracts from Phase 1.
- **Cutover proof required**: the new engine must plan the same 64 pilot trials
  and reproduce the committed pilot terminal counts, outer-join counts,
  candidate flags, and selected metric values before the Topanga plan freezes.
- **Acceptance evidence type**: both generated output and frozen fixtures.

## Stakeholders

- **Primary**: WEPP and openWEPP developers conducting the peak-flow audit.
- **Reviewers**: hydrology reviewers and WEPPpy maintainers.
- **Security Reviewer**: required for local path and subprocess boundaries.
- **Informed**: future site-audit operators.

## Success Criteria

- [x] No site name, run root, hillslope range, pilot size, or artifact package
  path is hard-coded in the reusable engine.
- [x] A versioned manifest can plan Topanga and a synthetic second site without
  Python edits.
- [x] The planner records requested, eligible, and excluded trials with an
  explicit reason and never clips mutations.
- [x] Every planned trial has a content-derived ID, exact source hashes,
  requested and expected realized values, and an output locator.
- [x] Pilot parity passes for all 64 trials and the 14,157 outer-joined event
  rows, including 30 baseline-only, 25 mutant-only, and 697 candidate rows.
- [x] Repeated planning is byte-identical and repeated execution safely reuses
  only hash-matching terminal artifacts.
- [x] No watershed binary or routing output appears in the full-census plan.
- [x] Targeted tests, schema checks, documentation lint, and the dedicated
  security review pass with no unresolved medium/high findings.
- [x] A preparation disposition explicitly authorizes or blocks creation of
  the separate full-census execution package.

## Parameterization ADR Gate

- **Parameterization change present**: no. This package reuses the mutation
  magnitudes and screening floors accepted in ADR-0042.
- **ADR required**: no new ADR.
- **ADR links**:
  [ADR-0042](../../adrs/ADR-0042-peakflow-phase2a-screening-and-volume-floors.md).
- **Decision provenance captured**: yes; the two-package sequence was directed
  by the requesting operator on 2026-08-09 and implemented by Codex.

## Dependencies

### Prerequisites

- [Completed Phase 2A pilot](../20260808_peakflow_phase2a_pilot/package.md).
- [Local-census design amendment](../20260808_peakflow_phase2a_pilot/artifacts/study-design-amendment-local-census.md).
- Accepted Phase 1 observer and replay evidence.
- Read-only burned and undisturbed Topanga scenario authorities.

### Blocks

- The separately dated `YYYYMMDD_peakflow_topanga_census_execution` package.
- Full Topanga local-mutation execution and Gate 3 prevalence reporting.

## Related Packages

- **Depends on**: [Phase 2A pilot](../20260808_peakflow_phase2a_pilot/package.md).
- **Related**: [Phase 1 assurance](../20260808_peakflow_phase1/package.md) and
  [Gate 2.1](../20260808_peakflow_gate21/package.md).
- **Follow-up**: a separately scaffolded Topanga census execution package only
  after this package publishes a GO disposition.

## Timeline Estimate

- **Expected duration**: one to three focused days.
- **Complexity**: High.
- **Risk level**: High data-integrity risk; low scientific-compute cost because
  the full matrix is prohibited here.

## Security Impact and Review Gate

- **Security impact triage**: high.
- **Dedicated security review required**: yes.
- **Triage rationale**: the reusable local CLI accepts filesystem authorities,
  creates content-addressed run trees, and launches an explicitly selected WEPP
  subprocess. These are path, file-integrity, and subprocess surfaces even
  though no public route, queue, network, auth, or secret behavior changes.
- **Security review artifact**:
  `docs/work-packages/20260808_peakflow_topanga_census_prep/artifacts/20260809_security_review.md`.

## References

- [Completed preparation ExecPlan](prompts/completed/topanga_census_prep_execplan.md).
- [Authoritative study design](../../investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/README.md).
- [Phase 2A completed ExecPlan](../20260808_peakflow_phase2a_pilot/prompts/completed/phase2a_pilot_execplan.md).
- `tools/peakflow_phase2a_pilot.py` - proven but Topanga-specific implementation.
- `tests/investigations/test_peakflow_phase2a_pilot.py` - current focused tests.

## Deliverables

- Reusable census engine and thin CLI.
- Versioned schemas and compatibility/regression plan.
- Frozen Topanga study manifest and complete trial plan.
- Pilot-parity, idempotence, failure-recovery, and security evidence.
- Preparation GO/NO-GO disposition and execution-package handoff.

## Follow-up Work

After a GO disposition, create the separately dated Topanga census execution
package. That package will consume the frozen plan without changing trial
eligibility, mutation semantics, screening floors, or output contracts.
