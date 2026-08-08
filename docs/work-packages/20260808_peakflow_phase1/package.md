# Topanga Peak-Flow Audit Phase 1

**Status**: Complete — Gates 0–2 passed (2026-08-08)
**Timezone**: UTC

## Overview

This package executes Gates 0–2 of the WEPP peak-flow discontinuity audit. It
turns the existing Topanga evidence into versioned protocols, immutable event
packets, process-isolated solver replays, and compact acceptance fixtures before
any watershed-wide mutation census is allowed.

## Objectives

- Publish versioned schemas for builds, runs, mutations, events, forcing,
  routing, site selection, and artifact storage.
- Freeze the Hill 106 1980 Ksat and 1986 canopy/cover fixtures.
- Capture legacy solver inputs without changing canonical WEPP output.
- Replay `APPMTH` and `HDRIVE` outside the observational WEPP process.
- Demonstrate reference/logging parity, selected-method replay parity, domain
  diagnostics, and inactive-parameter negative controls.

## Scope

### Included

- Gates 0–2 in the multi-site audit README.
- Restricted-source internal reproducibility using the pinned WEPP-Forest
  commit and public, machine-readable fixture/protocol artifacts in WEPPpy.
- Generated-output evidence for the compact Topanga fixtures.

### Explicitly Out of Scope

- The full Topanga hillslope mutation census.
- Cross-site prevalence, snow, and OFE experiments.
- Behavioral repair of legacy WEPP.
- Claims that either 1986 peak regime is physically correct.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful extraction of legacy solver inputs and methods.
- **Authoritative source paths**: `irs.for`, `appmth.for`, `hdrive.for`,
  `reid.for`, and their included COMMON state at WEPP-Forest commit
  `f24c957e3633898e0fd4cbbea5ae08c781f29dba`.
- **Cutover proof required**: selected-method offline replay reproduces the
  production-selected peak from an immutable packet; no production cutover is
  performed.
- **Acceptance evidence type**: both fixture and generated output.

## Stakeholders

- **Primary**: WEPP and openWEPP developers and hydrology reviewers.
- **Reviewers**: Phase 1 planning reviewer and WEPP stakeholders.
- **Security Reviewer**: not required.
- **Informed**: Topanga investigation readers.

## Success Criteria

- [x] Gate 0 passes with versioned schemas and requested/realized mutations.
- [x] Gate 1 passes with declared parity files, immutable packets, and
  process-isolated replay.
- [x] Gate 2 passes with one-command 1980 and 1986 fixtures and a negative
  control.
- [x] The full Topanga census remains blocked in documentation.
- [x] Targeted tests and documentation lint pass.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no.
- **ADR links**: N/A.
- **Decision provenance captured**: yes; the investigation review and active
  ExecPlan are authoritative.

## Dependencies

### Prerequisites

- Acceptance WEPP-Forest commit `f24c957e3633898e0fd4cbbea5ae08c781f29dba`,
  recorded by the `wepp_260803` provenance sidecar.
- Topanga run `/wc1/runs/ha/hand-to-mouth-drought`.
- Existing Topanga diagnostic and 1986 frozen inputs.

### Blocks

- Topanga Phase 2 mutation census.
- Cross-site audit and openWEPP fixture import.

## Related Packages

- **Related investigation**: [multi-site audit](../../investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/README.md).
- **Evidence source**: [Topanga investigation](../../investigations/2026-08-07-topanga-2025-fire-peak-flow-analysis/README.md).
- **Follow-up**: Phase 2 Topanga candidate census after an explicit Gate 2 review.

## Timeline Estimate

- **Expected duration**: one focused implementation cycle.
- **Complexity**: High.
- **Risk level**: High scientific-integrity risk; low production risk.

## Security Impact and Review Gate

- **Security impact triage**: none.
- **Dedicated security review required**: no.
- **Triage rationale**: local diagnostic builds and committed fixtures do not
  change authentication, services, queues, deployment, or external access.
- **Security review artifact**: N/A.

## References

- [`tracker.md`](tracker.md) — live status and decisions.
- [`artifacts/README.md`](artifacts/README.md) — artifact map and reproduction
  commands.
- [`prompts/completed/phase1_execplan.md`](prompts/completed/phase1_execplan.md) —
  executable implementation plan.
- [audit protocol](../../investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/README.md).

## Deliverables

- Eleven versioned JSON Schemas under [`artifacts/schemas`](artifacts/schemas/).
- A self-contained [1980 Ksat fixture](../../investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/artifacts/topanga-h106-1980-ksat/).
- A three-lane [1986 anomaly fixture](../../investigations/2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/openwepp-hill106-effective-duration-reproducer/).
- [`observer-parity-report.json`](artifacts/observer-parity-report.json), which
  declares and passes byte parity for all seven canonical output files.
- Full-precision immutable packets under [`artifacts/event-packets`](artifacts/event-packets/)
  and process-isolated results under [`artifacts/replay-reports`](artifacts/replay-reports/).
- A passing [`negative-control-result.json`](artifacts/negative-control-result.json)
  for the inactive version-9002 Ksat-factor token.

## Follow-up Work

The full Topanga census remains a separately authorized successor.
