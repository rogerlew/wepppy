# Roads preparation lifecycle implementation

Status: closed, 2026-10-23 UTC; implementation and local environment validation complete. Owner: Roger. Starting revision: c3ac573e3.

Implement the operator-approved replacement lifecycle: preparation replaces the
segment set, old Roads results cease to be current for every consumer, and only
a fresh successful Roads execution restores current results. Keep baseline intact
and preserve old diagnostic files as historical artifacts. No stable-ID migration,
geometry lineage subsystem, native-model change, deployment or original UM1 repair.
The GL detachment layer and its open D1–D4 decisions are outside this package.

Execute [the plan](prompts/completed/repair_execplan.md); maintain [tracker](tracker.md).
Authority: [canonical lifecycle](../../schemas/roads-preparation-lifecycle-contract.md).
Existing task-scoped commit authority persists. User requested scaffold and execution.

Compatibility: beta output admission intentionally changes. Old files cannot become
current by reading or postprocessing them; prepare/run is supported recovery.
Retain current output names; add only publication/retention artifacts if required.
Regression plan: validate real filesystem invalidation and publication, old catalog
entries, direct report/download/query reads, failed preparation/run, rerun, archive
and baseline identity. Exercise isolated UM1 only, using existing local runtime.
Security impact: high, shared publication/consumer boundaries. Independent correctness
and dedicated security review are required, plus two independent contract reviews.

## Outcome

Contract checkpoint `1270c209f`; runtime/evidence commit `e4d28c9ad`. Replacement,
retention, atomic publication and shared reader admission are wired and validated
through actual model execution, live services and canonical archive/restore.
Independent correctness and security reviews pass. Broad coverage completed in
segmented runs (11,115 unique passes/126 skips); frontend 990 tests passed.
See [validation and limitations](artifacts/20261022_validation.md). Original UM1
and production remain unchanged. GL detachment choropleth D1–D4 remain separate.
