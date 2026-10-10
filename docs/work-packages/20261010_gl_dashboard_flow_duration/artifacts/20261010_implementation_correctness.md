# Flow-duration implementation correctness review

Reviewer: independent `/root/fdc_contract_correctness` agent.
Date: 2026-10-10 21:29 UTC. Reviewed uncommitted implementation after checkpoint
`c63f2cc52`, whose parent is the recorded starting implementation `189d10649`.
Canonical authority: the FDC contract and ADR-0085 committed in that checkpoint.
Scope: route/bootstrap readiness, daily loader/ranking, controls, renderer,
controller/layout seams and focused tests. Production edits were read-only during
this review; findings were corrected by the implementation owner.

## Findings and resolution

| ID | Severity | Surface and evidence | Disposition |
| --- | --- | --- | --- |
| FDC-I01 | High | `routes/gl_dashboard_flow_duration.py` initially allowed DuckDB parser errors from the real watershed translator to escape the optional FDC readiness check. One scenario with malformed topology Parquet could fail the entire existing dashboard route before graph selection. Reproduced with real malformed files and `WatershedOperationsMixin.translator_factory`. | Resolved: per-scenario outlet boundary catches narrow `duckdb.Error` and marks only that source unavailable. Added real parser-boundary regression, which passed independently. |
| FDC-I02 | Medium | `graphs/controller.js::activateGraphItem` initially checked stale generations only for truthy data. An older null result hid a newer FDC; independent deferred-promise reproduction returned `hide, new FDC, hide`. | Resolved: stale check precedes both data and empty branches. Deferred old-null and forced same-key regressions passed independently. |
| FDC-I03 | Low | All-hidden legends left inspection output blank because bounds existed with an empty series list. | Resolved: renderer reports `No visible daily values` for an empty visible-series list. |

No unresolved high or medium findings remain in the reviewed implementation.

## Independent checks

- `wctl run-pytest tests/weppcloud/routes/test_gl_dashboard_flow_duration.py -q`:
  **8 passed** after an outdated error-message assertion was corrected. Tests
  exercise actual file/catalog/symlink boundaries and the real malformed-Parquet
  reader; hydration alone is replaced in the focused translator test.
- Focused `wctl run-npm test` on `flow-duration.test.js` and
  `flow-duration-controller.test.js`: **15 passed**. Covers ties/zeros, Gregorian
  leap gaps, synthetic years, null/NaN, invalid values, year-group exclusions,
  independent records, both outlet-ID filters, failed-query retry and races.
- Direct review/reproduction confirms fixed m³/s conversions, full-population
  Weibull ranking, source-specific caches and no date intersection. Query flow
  and area are VARCHAR so NaN/Infinity reach the explicit client classification.
- Node timing with 20 scenarios each containing the 1980–2024 daily population:
  initial ranking approximately **928 ms**; cached x-axis-only load below 1 ms.
  This isolates loader work and is not a browser/network performance claim.
- Scoped `git diff --check` passed. Checkpoint ancestry and preimplementation
  review artifacts are present before production changes.

## Valid-state and compatibility assessment

Missing one source/scenario remains a named unavailable curve; missing Omni
still includes the baseline. Empty or warm-up-exhausted records remain empty;
zeros and one-point records remain valid. Legacy source absence does not create
an alternative flow population. Roads reports explicit scope unavailability.
Malformed daily values invalidate only their curve. Readonly is not a completion
gate. Source identity, baseline labels and colors are reused without tying graph
comparison to the map's current scenario.

The renderer is selected only for the new graph type. Existing line/boxplot
paths retain their behavior. The generation guard now protects empty as well as
populated late responses. Axis and legend changes reuse ranked values; layout
changes preserve settings. Controls expose no seasonal or export options.

## Residual evidence and release recommendation

Correctness review gate: **pass for implementation**, with release evidence
still owned by the orchestrator. At review completion the real forest browser
integration, final broad tests, final security review and delivery documentation
were still being completed; this artifact does not certify deployment success.

Retain real-source graph/tooltip comparisons for both sources/scales and normal
layout/keyboard behavior. The production example has no zero hillslope days;
zero correctness is therefore established by fixtures, not that project. Larger
browser memory/render workloads and dedicated all-hidden/one-point renderer
fixtures remain less covered than loader mathematics. Source/catalog ownership
is a page-load snapshot by contract; reload is required after regeneration.
Rain-on-snow exclusion is explicitly unavailable pending a verified classifier.

No new persisted model artifact is produced. The observable chain is existing
source Parquet, authorized query, ranked payload and visible graph; source and
browser numerical evidence must accompany final delivery claims.

## Final conformance addendum, 2026-10-10 21:38 UTC

Reviewed the bounded follow-up changes; correctness approval remains **pass**.

- Reported start/end now use the same calendar horizon as missing-day counts.
  The new leading-gap oracle excludes 2000 and correctly reports January 1–4,
  2001 with three missing days when the sole retained observation is January 4.
- Standalone Omni child dashboards may use topology within their established
  parent project while daily files and catalogs remain owned by the child.
  Canonical `_pups/omni/scenarios/<name>` ancestry bounds this compatibility.
  Parent URLs with a `pup` selector send the active scenario through the existing
  Query Engine body; composite Omni-child URLs retain their child endpoint.
  The active child's exact name drives the curve label and color.
- The route identifies composite child endpoints by the terminal `omni` owner
  segment, not any `;;` delimiter. A preliminary concern about grouped-parent
  `pup` requests was withdrawn after checking `_run_context.py`: those requests
  already ignore `pup`. No grouped-route behavior was expanded by this feature.
- Independent focused Jest rerun: **18 passed** across three suites, including
  leading coverage, child query identity, one zero point, safe scenario labels,
  all-hidden inspection and renderer cleanup. These fixtures close the earlier
  one-point/all-hidden renderer coverage gap.
- Independent final route/boundary pytest rerun: **32 passed** across
  `test_gl_dashboard_flow_duration.py` and `test_gl_dashboard_route.py`, including
  both child endpoint forms and plain/batch parent identity cases.
- Read retained parent browser evidence: Burned/undisturbed labels and colors,
  both daily sources, N=15,706 after warm-up and extrema agree with the direct
  source oracle. The orchestrator reports both standalone child URL forms also
  passed live integration; retaining that evidence remains its delivery task.

No new unresolved correctness finding was introduced. Larger browser memory and
render workloads remain less characterized than cached-loader performance.
