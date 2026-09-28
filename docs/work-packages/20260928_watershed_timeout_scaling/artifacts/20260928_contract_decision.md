# WRT-01 contract checkpoint

Starting revision: a3a3b87b6. Operator explicitly approved the proposed year-plus-
hillslope timeout on2026-09-28. Commit authority persists from this session.
Classification: intended bounded workflow-parameterization change.

Amended authority: docs/schemas/wepp-run-input-contract.md WRT-01 and ADR-0076.
Unchanged shared authority: RQ response, CSRF, NoDb persistence/concurrency and
Pure controller contracts; input/output authority and bootstrap no-prep retention
remain unchanged. New policy is additive metadata plus selected child timeout;
no NoDb or model-artifact schema mutation. Archived assessment is evidence, not
authority. Proposed implementation scope: wepp_rq_pipeline helper/enqueue sites,
small owned prepared-workload reader, catalog, tests and user/operator docs.

State matrix: valid populated controller data and prepared input succeed;
legacy integer years and legacy/modern prompt layouts succeed; absent unused
workload (hillslope-only, prep-only, single-storm) is not read; absent required
continuous workload errors before children; stale NoDb during no-prep uses actual
prepared workload; malformed/hostile bounded input fails; missing optional fork
lineage is normal; valid lineage survives metadata addition. Existing stopped,
failed and successful outcomes remain unchanged. Archive paths are unchanged;
no-prep source hashes must remain equal before/after enqueue/execution.

No scientific parameterization, topology, job names, auth, locks, dependencies,
outputs, retry behavior, subprocess cleanup or deployment changes. Longer runtime
is an authorized bounded resource allowance; coefficient/floor/range are explicit
in WRT-01. Two independent reviews and ancestor commit precede implementation.
