# Batch Runner OMNI Selective Retry

**Status**: Closed - design rejected (2026-08-06)
**Timezone**: UTC

## Outcome

The proposed scenario-selective Batch Runner OMNI retry was reviewed but not
approved. No production implementation was started and no checkpoint was
committed.

The accepted operator decision is to require a full rerun of OMNI scenarios
when OMNI results must be regenerated. Batch Runner may replace/reset the leaf
OMNI scenario state from `_base` under its existing full-rerun behavior. It
must not preserve individual completed scenarios or provide scenario-selective
administrative invalidation.

## Rationale

OMNI scenario outputs feed dependent scenarios, aggregate reports, and OMNI
contrasts. Proving selective freshness across those relationships would require
slow production-scale iteration over multi-watershed batches and substantially
more admission, recovery, and compatibility machinery. The operator judged
that complexity and residual inconsistency risk to outweigh the avoided model
execution.

A full scenario rerun provides one coherent scenario set before contrasts are
rebuilt or rerun. This intentionally favors predictable correctness and simpler
operations over partial reuse.

## Required Operational Behavior

1. An operator requesting OMNI regeneration must select/rerun the complete OMNI
   scenario stage for affected leaves.
2. Scenario-level dependency entries or outputs must not be administratively
   invalidated in isolation.
3. OMNI contrasts must be treated as downstream of the complete regenerated
   scenario set; stale contrasts must not be reused across a scenario rerun.
4. Production deployment, invalidation, and batch execution remain separately
   authorized operations.

## Scope Disposition

### Rejected

- Preserving completed leaf scenario projects during Batch Runner retry.
- Missing-output scenario-level freshness checks.
- Post-stage selective dependency evaluation across scenario tiers.
- A dry-run/apply selective invalidation command.
- SURF-02D/GOV-00A-M1H registration or canonical contract amendments.

### Retained

- Existing full-rerun behavior and whole-stage operational recovery.
- Existing OMNI scenario and contrast orchestration contracts.
- The option to create a future, separately approved package for clearer
  full-rerun operator tooling or scenario-plus-contrast reset semantics.

## Security and Parameterization

- **Security impact**: none; the proposed mutation surface was not implemented.
- **Dedicated security review**: not applicable after rejection.
- **Parameterization change present**: no.
- **ADR required**: no.

## References

- `wepppy/rq/batch_rq.py::_reset_omni_nodb_from_base`
- `wepppy/rq/omni_rq.py::run_omni_scenarios_rq`
- `wepppy/nodb/mods/omni/omni_run_orchestration_service.py`
- `prompts/completed/batch_runner_omni_selective_retry_execplan.md`

## Closure Notes

**Closed**: 2026-08-06

**Summary**: Selective retry was rejected before implementation. The operator
requires complete OMNI scenario reruns because scenario/contrast interaction is
too costly and risky to validate incrementally at production multi-watershed
scale.
