# Peak-Flow Gate 2.1 Remediation

**Status**: Accepted; Phase 2A authorized (2026-08-08)
**Timezone**: UTC

## Overview

This narrow remediation package corrects the implementation-assurance gaps
found in the Topanga Phase 1 review. It makes observational solver labels,
event packets, domain diagnostics, schemas, parity evidence, and the acceptance
command trustworthy across the event population before any Phase 2 census.

## Objectives

- Record the solver actually called and the post-clamp production peak.
- Emit complete typed packets for surplus and no-surplus events.
- Implement the documented APPMTH `v*`, `t*`, and `q*` domains.
- Prove active-trace byte parity and full one-command acceptance.
- Pin the pushed WEPP-Forest observer commit unambiguously.

## Scope

### Included

- Gate 1 and Gate 2 remediation enumerated in the 2026-08-08 review.
- WEPP-Forest observer changes on `feature/peakflow-phase1-observer`.
- WEPPpy schemas, packetizer, replay, fixtures, tests, and evidence regeneration.

### Explicitly Out of Scope

- The Topanga census or mutation pilot.
- Cross-site, snow, or OFE experiments.
- Behavioral changes to either legacy peak solver.
- A claim that either 1986 peak regime is physically correct.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful observation and replay of legacy execution.
- **Authoritative source paths**: WEPP-Forest `src/irs.for`, `src/appmth.for`,
  and `src/hdrive.for` on the pushed observer branch.
- **Cutover proof required**: active and inactive observer runs retain byte-
  identical canonical outputs; selected-method replay matches the post-clamp
  production peak.
- **Acceptance evidence type**: generated output and frozen fixtures.

## Stakeholders

- **Primary**: WEPP and openWEPP developers and hydrology reviewers.
- **Reviewers**: Gate 2.1 reviewer and WEPP stakeholders.
- **Security Reviewer**: not required.
- **Informed**: Topanga investigation readers.

## Success Criteria

- [x] Actual solver-call logging and post-clamp peak capture pass branch tests.
- [x] Domain limits and `qpstar` pass boundary tests.
- [x] Typed complete packets cover surplus and no-surplus paths.
- [x] Active tracing is byte-identical on both Ksat lanes.
- [x] Build and replay artifacts validate against published schemas.
- [x] One command regenerates and verifies the complete Gate 2 evidence chain.
- [x] Final pushed observer commit is pinned in regenerated evidence.
- [x] Phase 2 remains explicitly blocked pending review.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no.
- **ADR links**: N/A.
- **Decision provenance captured**: yes; the review disposition and this package
  define the assurance contract.

## Dependencies

### Prerequisites

- Completed Phase 1 package `docs/work-packages/20260808_peakflow_phase1/`.
- Pushed WEPP-Forest branch `feature/peakflow-phase1-observer`.

### Blocks

- Any Topanga Phase 2 pilot or census execution.

## Related Packages

- **Depends on**: [Phase 1](../20260808_peakflow_phase1/package.md).
- **Related**: [multi-site audit](../../investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/README.md).
- **Follow-up**: explicit Gate 2.1 review disposition; no additional conceptual
  study-design review is required.

## Timeline Estimate

- **Expected duration**: one focused remediation cycle.
- **Complexity**: High.
- **Risk level**: High scientific-integrity risk; low production risk.

## Security Impact and Review Gate

- **Security impact triage**: none.
- **Dedicated security review required**: no.
- **Triage rationale**: local model diagnostics and fixture tooling do not alter
  authentication, network access, queues, or deployed services.
- **Security review artifact**: N/A.

## Hardening and Callus Softening

- **Failure signatures**: incorrect solver labels, incomplete packets, loose
  domain flags, inactive-only parity, and nonconforming evidence schemas.
- **Related prior hardening efforts**: Phase 1 package linked above.
- **Health signals**: branch-accurate labels, schema-valid artifacts, exact
  replay, and active byte parity.
- **Danger signals**: inline shadow solver calls or modifications to canonical
  WEPP outputs.
- **Observation window**: complete fixture histories during acceptance.
- **Temporary calluses introduced**: none.
- **Callus softening hypothesis**: N/A.

## References

- [`tracker.md`](tracker.md) — live remediation status.
- [`prompts/completed/gate21_execplan.md`](prompts/completed/gate21_execplan.md) —
  executable plan.
- [Phase 1 artifacts](../20260808_peakflow_phase1/artifacts/README.md).

## Deliverables

- Pushed WEPP-Forest observer commit `ea25ad79`.
- Strict event-packet and replay-report schemas.
- Full-precision 1980 expected packet/replay contract.
- Active parity and Gate 2.1 acceptance reports.
- One-command fixture acceptance entry point.
- [Accepted review disposition](artifacts/gate21-review-disposition.md).

## Follow-up Work

Phase 2A is authorized. The full Topanga census follows automatically after
the pilot satisfies the exit criteria in the review disposition. Gates 4 and
5 continue to defer cross-site prevalence, snow-site, and OFE work.
