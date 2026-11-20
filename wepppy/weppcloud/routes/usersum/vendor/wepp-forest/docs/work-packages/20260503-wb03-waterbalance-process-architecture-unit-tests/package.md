# WB-03 Work Package: Water-Balance Process Architecture and Unit Tests

**Status**: Completed (closed 2026-05-03 UTC)
**Timezone**: UTC

## Overview

WB-03 freezes the process-based architecture and unit-test plan for the
water-balance rewrite before production source migration begins. It consumes the
WB-01 investigation and WB-02 freeze decisions and turns them into an explicit
implementation blueprint: process kernels, kernel interfaces, adapter
boundaries, state contracts, and unit-test vectors.

WB-03 exists to prevent a churn-heavy intermediate port. Agents must not first
translate `watbal*` into a shape that later needs to be torn apart. The next
implementation package must start from the intended process architecture.

## Objective

Publish an architecture packet that makes WB-04 directly implementable:

- process decomposition and ownership boundaries,
- process-kernel interface contracts,
- adapter/common-block boundary contract,
- unit-test matrix and vector sourcing policy,
- implementation sequencing and guardrails,
- WB-04 kickoff checklist.

## Scope

### Included

- Define process kernels for storage accounting, percolation/deep seepage,
  lateral subsurface transfer, tile drainage, ET accounting, runoff/output
  mapping, closure diagnostics, and boundary/clamp policy.
- Define explicit input/output structs or argument groups for each kernel:
  units, sign conventions, state mutation rules, finite-value requirements,
  clamp classes, and boundary status values.
- Define the legacy adapter boundary that may read/write common blocks while
  process kernels receive explicit data and return explicit deltas/status.
- Define daily and hourly scheduler responsibilities without duplicating
  process physics.
- Define fpm/unit-test harness expectations, synthetic vector classes, WB-01
  replay-derived vector classes, and invariant tests.
- Define the WB-04 implementation sequence so architecture, tests, and source
  changes land together rather than as an unstructured refactor.

### Explicitly Out of Scope

- Production numerical source migration or rewrite in `src/`; belongs to WB-04
  and WB-05 after WB-03 closes.
- Mechanical `.for` -> `.f90` translation as an intermediate target.
- Behavior changes or acceptance claims.
- WEPPpy downstream integration/cutover; belongs to WB-06 and WB-08.
- Vendoring binaries into `wepppy`; belongs to a release/cutover package.

## Success Criteria

- [x] Process architecture names every kernel WB-04 is allowed to implement.
- [x] Kernel contracts define explicit inputs, outputs, units, state deltas,
  error/boundary status, and invariants.
- [x] Adapter boundary contract prevents kernels from directly depending on
  common blocks, sentinel files, or scheduler globals.
- [x] Unit-test matrix covers normal, boundary, clamp, conservation, and WB-01
  replay-derived vectors.
- [x] Implementation sequence requires tests to be created with or before each
  kernel implementation.
- [x] WB-04 kickoff checklist names exact source/test deliverables and gates.
- [x] Gate decision memo records WB-03 closeout and WB-04 readiness.

## Deliverables

- `/workdir/wepp-forest/docs/work-packages/20260503-wb03-waterbalance-process-architecture-unit-tests/artifacts/process_architecture.md`
- `/workdir/wepp-forest/docs/work-packages/20260503-wb03-waterbalance-process-architecture-unit-tests/artifacts/process_kernel_contracts.md`
- `/workdir/wepp-forest/docs/work-packages/20260503-wb03-waterbalance-process-architecture-unit-tests/artifacts/adapter_boundary_contract.md`
- `/workdir/wepp-forest/docs/work-packages/20260503-wb03-waterbalance-process-architecture-unit-tests/artifacts/unit_test_matrix.md`
- `/workdir/wepp-forest/docs/work-packages/20260503-wb03-waterbalance-process-architecture-unit-tests/artifacts/implementation_sequence.md`
- `/workdir/wepp-forest/docs/work-packages/20260503-wb03-waterbalance-process-architecture-unit-tests/artifacts/divergence_ledger.md`
- `/workdir/wepp-forest/docs/work-packages/20260503-wb03-waterbalance-process-architecture-unit-tests/artifacts/wb04_kickoff_checklist.md`
- `/workdir/wepp-forest/docs/work-packages/20260503-wb03-waterbalance-process-architecture-unit-tests/tracker.md`
- `/workdir/wepp-forest/docs/work-packages/20260503-wb03-waterbalance-process-architecture-unit-tests/notes/2026-05-03_wb03_disposition.md`

## Dependencies

- Completed WB-02 spec-freeze package:
  - `docs/work-packages/20260503-wb02-waterbalance-spec-freeze/`
- Completed WB-01 baseline characterization package:
  - `docs/work-packages/20260503-wb01-waterbalance-baseline-characterization/`
- Strategy source:
  - `docs/waterbalance-rewrite-strategy.md`
- Migration header schema:
  - `docs/contracts/f90-migration-header-schema.md`

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Rationale**: architecture and test-planning documentation only; no
  auth/session/secret surface is intentionally changed.

## References

- `docs/work-packages/20260503-wb03-waterbalance-process-architecture-unit-tests/prompts/active/wb03_waterbalance_process_architecture_unit_tests_execplan.md`
- `docs/work-packages/20260503-wb03-waterbalance-process-architecture-unit-tests/prompts/active/wb03_waterbalance_process_architecture_unit_tests_agent_prompt.md`
- `docs/work-packages/20260503-wb02-waterbalance-spec-freeze/artifacts/wb03_kickoff_checklist.md`
- `docs/work-packages/20260503-wb02-waterbalance-spec-freeze/artifacts/acceptance_band_manifest.md`
- `docs/work-packages/20260503-wb02-waterbalance-spec-freeze/artifacts/divergence_disposition_policy.md`
- `docs/waterbalance-rewrite-strategy.md`
