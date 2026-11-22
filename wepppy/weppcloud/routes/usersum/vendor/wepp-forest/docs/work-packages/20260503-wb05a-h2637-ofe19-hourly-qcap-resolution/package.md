# WB-05A Work Package: H2637 OFE19 Hourly Q-Cap Closure Resolution

**Status**: Completed
**Timezone**: UTC

## Overview

WB-05A is a blocker package created after WB-05 closeout because targeted
H2637 evidence showed that OFE19 still exposes bad hourly-path/q-cap behavior
when `wepp_ui.txt` is present.

This package is intentionally not a legacy-parity exercise. Closure is
water-balance. The goal is to find and repair the non-conservation mechanism on
the hourly path, then prove the repaired behavior with targeted OFE closure,
whole-hillslope replay evidence, and regression tests.

## Objective

Resolve the H2637 OFE19 hourly-path q-cap defect:

- reproduce H2637 with and without `wepp_ui.txt`,
- isolate the process term or scheduler interaction that creates OFE19
  non-conservation,
- implement the smallest defensible mass-conservation repair,
- add regression coverage for the targeted case and relevant kernel/adapter
  contract,
- update divergence records so downstream packages do not treat the defect as
  acceptable legacy behavior.

## Scope

### Included

- Targeted H2637 OFE19 reproduction using current `src/wepp_hill`.
- OFE-level closure calculations for OFE19, including day 44 and top residual
  days.
- Investigation of hourly q-cap, `Q`/`QOFE`, upstream transfer, storage delta,
  lateral flow, and output-mapping terms needed to conserve mass.
- Edits to shared process kernels, hourly adapter, or legacy integration glue
  if evidence shows the defect sits at those boundaries.
- Unit tests and replay acceptance tests proving the fix.
- Updated WB-00 board/dependency state to block WB-06/WB-07 until this package
  closes.

### Explicitly Out of Scope

- Preserving H2637 hourly q-cap output parity when parity conflicts with
  closure.
- Broad scientific retuning beyond the terms required to conserve water.
- WEPPpy downstream parser/report integration; that remains WB-06 after this
  blocker closes.
- Performance and observability rollout; that remains WB-07 after this blocker
  closes.

## Success Criteria

- [ ] H2637 reproduction artifacts are published under this package, not only
  temporary paths.
- [ ] With `wepp_ui.txt`, H2637 OFE19 no longer has positive q-cap violations
  or unexplained large OFE closure residuals.
- [ ] Without `wepp_ui.txt`, H2637 remains effectively closed on the daily path.
- [ ] The H2637 day-44 OFE19 closure evidence is explicitly reported.
- [ ] New unit/regression tests fail before the repair and pass after it.
- [ ] `fpm test`, Fortitude on touched `.f90` files, `make wepp`, `make
  wepp_hill`, targeted H2637 replay, hillslope watchlist, and targeted pytest
  all pass.
- [ ] Divergence ledger has zero `UNRESOLVED` entries.
- [ ] WB-06/WB-07 unblock checklist is accepted.

## Deliverables

- `artifacts/h2637_ofe19_initial_evidence.md`
- `artifacts/reproduction_plan.md`
- `artifacts/source_target_manifest.md`
- `artifacts/closure_authority.md`
- `artifacts/divergence_ledger.md`
- `artifacts/wb06_wb07_unblock_checklist.md`
- `tracker.md`
- `prompts/active/wb05a_h2637_ofe19_hourly_qcap_resolution_execplan.md`
- `prompts/active/wb05a_h2637_ofe19_hourly_qcap_resolution_agent_prompt.md`
- `notes/2026-05-03_wb05a_disposition.md`

## Dependencies

- Completed WB-04 daily shared-core package.
- Completed WB-05 hourly adapter package.
- WB-00 correctness authority update stating that closure, not legacy parity,
  governs promotion.

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Rationale**: numerical model accounting and tests only; no auth, session,
  secret, or network surface is intentionally changed.

## References

- `docs/waterbalance-rewrite-strategy.md`
- `docs/work-packages/20260503-wb00-waterbalance-program-bootstrap/artifacts/program_governance.md`
- `docs/work-packages/20260503-wb05-waterbalance-hourly-adapter/notes/2026-05-03_wb05_disposition.md`
- `docs/ablation/20260430_uncapped-spectacular_h2637_hillslope_closure-spike/`
