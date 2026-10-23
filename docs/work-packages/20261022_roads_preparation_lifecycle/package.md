# Roads preparation lifecycle implementation

Status: implemented and locally validated; full regression gate running. Owner: Roger. Starting revision: c3ac573e3.

Implement the operator-approved replacement lifecycle: preparation replaces the
segment set, old Roads results cease to be current for every consumer, and only
a fresh successful Roads execution restores current results. Keep baseline intact
and preserve old diagnostic files as historical artifacts. No stable-ID migration,
geometry lineage subsystem, native-model change, deployment or original UM1 repair.
The GL detachment layer and its open D1–D4 decisions are outside this package.

Execute [the plan](prompts/active/repair_execplan.md); maintain [tracker](tracker.md).
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
