# Rejected Plan - Batch Runner OMNI scenario-selective retry

**Outcome**: Rejected before implementation on 2026-08-06 UTC.

This ExecPlan proposed preserving completed OMNI leaf scenarios and rerunning
only scenarios whose definition, dependency, modeled years, or required outputs
were stale. It also proposed a bounded administrative invalidator.

## Decision

The repository operator did not approve the final selective-retry matrix. The
required behavior is a full OMNI scenario rerun when scenario results must be
regenerated.

## Rationale

Checkpoint review exposed strong coupling among stage-1 and dependent stage-2
scenarios, aggregate outputs, and OMNI contrasts. A sound selective path would
also need new execution-admission locking, path containment, durable recovery,
and compatibility rules. Validating those interactions at production
multi-watershed scale would have a slow iteration cycle and unacceptable
residual risk.

The accepted tradeoff is additional model execution in exchange for a simpler,
coherent whole-stage regeneration boundary.

## Work Performed

- Characterized current Batch Runner reset and OMNI freshness behavior.
- Drafted an execution plan and contract/security checkpoint.
- Obtained initial independent governance and operations/security reviews.
- Stopped before checkpoint commit or production implementation.
- Withdrew the proposed SURF-02D/GOV-00A-M1H canonical amendments.

## Production and Data Impact

- No production implementation changed.
- No tests, schemas, parameters, formulas, defaults, or queue topology changed.
- No deployment, production invalidation, or production batch execution
  occurred.
- No selective invalidation command was created.

## Final Operational Contract

When OMNI scenario regeneration is required, rerun the complete OMNI scenario
stage for the affected leaves and treat OMNI contrasts as downstream of the
complete regenerated scenario set. Do not invalidate or preserve individual
scenarios across that rerun.
