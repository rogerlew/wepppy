# Roads WBT repair tracker

2026-10-26 UTC — Closed: local implementation and isolated-environment validation.
[Completed plan](prompts/completed/implementation_execplan.md).

Checkpoint 3a542d939 passed two independent reviews before implementation.
Native source/release commit 71ec98a contains explicit WBT normalization and
backward-compatible TOPAZ default. WEPPpy always opts into WBT for Roads.

Native 23 tests, focused 108, publication 14 and all 11,947 collected broad nodes
are covered: 11,795 passes, 152 test skips plus one collection-module skip;
no unresolved failures. Two broad failures were retained and resolved: SWAT
fixture isolation (full module 8 passed) and existing browser-cache configuration
(explicit installed cache, 36 passed). No production code was changed for them.
The initial canonical run and slow rest segment were intentionally interrupted
and resumed through complete node accounting; no tests were excluded.

Actual site snapshot: 35 completed versus 30, all five affected roads recovered,
four NoData outlets still excluded. Generated slopes, daily PASS/water, reports
and UI query data read back successfully. Source snapshot and baseline unchanged.
Independent correctness/science reviews PASS with no open medium/high findings.

Durable contract: docs/schemas/roads-flow-direction-contract.md.
Historical publication is explicitly stale for full-project coverage, with exact
reviewed source deltas; original scientific results/provenance remain untouched.
No production deployment, restart or original-project mutation. Preserve unrelated
query-catalog and native interchange work. Paired deployment and regeneration
remain operator follow-ups, not evidence claimed by this closed package.
