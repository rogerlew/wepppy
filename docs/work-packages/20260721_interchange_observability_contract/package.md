# Interchange Parser Observability Contract

**Status**: Complete (2026-07-21; release deployment pending)
**Timezone**: UTC

## Overview

The WEPPpyo3 interchange layer converted a 27-field `chnwb.txt` file into a valid-looking but empty Parquet dataset because its parser silently skipped rows unless they had an obsolete 22-field layout. This package restores the channel-water-balance interchange and establishes a strict parser-observability contract: after a data table begins, malformed candidate records must produce a contextual error rather than disappear.

## Objectives

- Restore `chnwb.parquet` production of one row per valid `chnwb.txt` data record, including the current optional profile-storage fields.
- Audit every WEPPpyo3 interchange reader for silent candidate-row loss and replace it with explicit, contextual failure or a documented non-data classification.
- Require parser admission, rejected-row accounting, and zero-row output behavior to be observable and regression-tested.
- Publish the governance standard and developer documentation that make this behavior mandatory for future interchange work.

## Scope

### Included

- `/home/workdir/wepppyo3/wepp_interchange/src` parser audit and fixes.
- The Python/RQ integration boundary in `wepppy` when it needs to surface native interchange summaries or errors.
- Regression fixtures and tests for valid current `chnwb.txt`, obsolete compatible layouts, malformed candidate records, missing headers, and no-record outputs.
- `docs/standards/interchange-observability-standard.md`, this work package, and affected interchange developer documentation.

### Explicitly Out of Scope

- Changing WEPP-Forest water-balance formulas, runoff values, or output meanings.
- Regenerating all historical run artifacts in place.
- Adding a fallback parser that conceals a format mismatch.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful extraction.
- **Authoritative source paths**: `/home/workdir/wepp-forest_260430_baseline/src/outfil.for` and `watbalprint.for` define the current CHNWB producer format; `/home/workdir/wepppyo3/wepp_interchange/src` consumes it.
- **Cutover proof required**: a fresh parse of the affected run's 34,192,070 CHNWB records must produce a non-empty Parquet file with matching row count; malformed fixtures must fail with path, line, expectation, and preview.
- **Acceptance evidence type**: both fixture-only and generated-output.

## Stakeholders

- **Primary**: WEPPcloud operators and users consuming run-scoped interchange datasets.
- **Reviewers**: WEPPpyo3 and WEPPpy maintainers.
- **Informed**: Marta and model-output/report maintainers.

## Success Criteria

- [x] Current 27-field CHNWB fixtures and the affected run parse without dropped rows.
- [x] Every audited interchange reader rejects malformed candidate records explicitly; intentional non-data lines are documented and covered by tests.
- [x] A parser cannot publish an empty dataset when candidate rows were encountered but rejected.
- [x] Native summaries expose accepted and rejected row counts at the Python boundary.
- [x] Governance and developer documentation describe the mandatory contract and validation gate.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no.
- **Decision provenance captured**: yes; this package and active ExecPlan record the user-authorized contract.

## Dependencies

### Prerequisites

- The checked-out WEPPpyo3 source at `/home/workdir/wepppyo3`.
- The affected completed production run at `/wc1/runs/be/beneficiary-forfeit/` for generated-output validation.

### Blocks

- Trustworthy CHNWB-based reports, exports, and downstream analysis for current water-balance output layouts.

## Related Packages

- **Related**: [WEPPpyo3-Only Interchange Cutover](../20260715_wepppyo3_only_interchange/package.md).
- **Related**: [WEPP Interchange Dependency Race Guard](../20260428_wepp_interchange_dependency_race_guard/package.md).

## Timeline Estimate

- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium-High.
- **Risk level**: Medium; failure semantics change from silent empty output to explicit job failure.

## Security Impact and Review Gate

- **Security impact triage**: none.
- **Dedicated security review required**: no.
- **Triage rationale**: the change only parses model-produced, run-scoped text and improves error reporting; it introduces no route, permission, secret, queue, subprocess, or external-egress behavior.

## Hardening and Callus Softening

- **Failure signature**: a valid 27-field `chnwb.txt` produced `chnwb.parquet` with zero rows because the parser required exactly 22 tokens and continued silently.
- **Health signals**: accepted-row counts match known source rows; malformed candidate records fail with a path and line; no valid input silently publishes an empty dataset.
- **Danger signals**: parser acceptance becomes overly permissive, a valid intentional-empty output starts failing, or parser overhead materially delays large runs.
- **Observation window**: validate the affected production artifact and retain accepted/rejected counts in normal job logs for 30 days after deployment.
- **Temporary calluses introduced**: none. The remedy is an explicit contract, not a fallback.

## References

- `/home/workdir/wepppyo3/wepp_interchange/src/chnwb.rs` - current silent 22-token admission gate.
- `/home/workdir/wepp-forest_260430_baseline/src/outfil.for` - current producer header and field layout.
- `/home/workdir/wepp-forest_260430_baseline/src/watbalprint.for` - channel-water-balance row writer.
- `docs/standards/hardening-lifecycle-standard.md` - incident hardening lifecycle.

## Deliverables

- Parser and caller changes with regression tests.
- `docs/standards/interchange-observability-standard.md`.
- Generated-output validation artifact and closure notes.
