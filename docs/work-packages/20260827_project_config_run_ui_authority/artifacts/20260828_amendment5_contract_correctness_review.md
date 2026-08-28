# Amendment 5 Contract Correctness Review

**Amendment**: `PC-24/WP12D-20260828-5`
**Baseline**: `0ad76c547145bbe323148bac73410ff9cfcd01ef`
**Review mode**: independent, read-only
**Advisory verdict**: READY, 2026-08-28 10:45 UTC
**Binding verdict**: READY, 2026-08-28 16:35 UTC; no correctness findings
**Implementation verdict**: READY, 2026-08-28 18:16 UTC; High 0 / Medium 0 /
Low 0

## Advisory disposition

The reviewer reported no remaining High or Medium correctness findings after
the contract closed these findings:

- the old schema-v1/no-live-registry surface matrix and historical illustrative
  schema-v3 graph were explicitly superseded without invalidating stored graphs;
- preset projection eligibility became exact and hostile-state complete;
- the source/test boundary uses real repository paths and includes registry,
  Builder API, upload, render, Flask, and rq-engine consumers;
- User-Defined upload is authority-gated before file or queue side effects;
- the stale event/upload/future deferral was corrected;
- exact synthesized component/digest and non-default land-cover Builder-create
  coverage was added; and
- exact-candidate Forest evidence requires real, unmocked DEP NEXRAD, Future
  CMIP5, User-Defined upload/build, and representative US land-cover provider
  executions.

The final advisory found the matrices, schema-v1 boundary, structural
identities, state handling, source scope, rollback order, Builder API coverage,
and Forest gates internally consistent. Residual risk is implementation-only:
the specified hashes, provider executions, rollback, and no-side-effect tests
must pass.

## Binding disposition

After exact operator ratification, the independent reviewer re-read the
ratified canonical diff against baseline
`0ad76c547145bbe323148bac73410ff9cfcd01ef` and reported BINDING READY. All
advisory closures remain intact; no `wepppy/`, `tests/`, or `.cfg` path differs
from baseline; unrelated dirty paths remain excluded; and the documentation-
only checkpoint is safe with exact path staging.

## Implementation disposition

The initial implementation review identified one evidence gap: the Europe
preset needed to exercise the production projection resolver through the
actual presentation, Flask mutation, and RQ mutation consumers rather than
only their shared lower-level helpers. The final tree closes that gap with a
materialized `eu-disturbed` schema-v1 named preset and proves:

- rendering exposes exactly Vanilla, E-OBS Modified (Europe), and User
  Defined;
- Flask discovery and mutation accept User Defined and reject PRISM; and
- the RQ route accepts User Defined and rejects PRISM before mutation.

The reviewer independently reran those three tests; all passed. The scoped
diff check also passed. No production correctness finding remains. Exact-host
`forest` acceptance is retained as a deployment gate rather than an
implementation defect. Merge and production remain reserved to parent WP12.
