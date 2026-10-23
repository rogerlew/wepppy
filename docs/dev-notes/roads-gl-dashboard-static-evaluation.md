# Roads GL Dashboard: static evaluation

Date: 2026-10-22. Scope: source inspection and read-only artifact inspection.
No runtime code changes, model reruns or project mutations.

Proposed behavior and unresolved decisions: [Roads dashboard contract](../schemas/roads-gl-dashboard-contract.md).

## Feasibility

A colored road-line layer fits the existing Deck.gl architecture. GL already has
`output_scope=roads` support for watershed datasets; it does not currently expose
Roads segment summary/geometry as a layer. Reuse existing infrastructure.
The largest correctness work is identity/provenance and multiple-profile semantics,
not drawing the lines. The earlier suggestion to join geometry directly by
segment_run_id needs refinement: prepared features carry segment_id, while result
rows additionally carry their distinct numeric segment_run_id.

## Evidence and integration map

| Source | Observed behavior / implication |
| --- | --- |
| `wepppy/weppcloud/routes/gl_dashboard.py`, `_build_wepp_paths` and `gl_dashboard` | Existing authorized route accepts output scope and injects scoped WEPP paths. Add Roads-specific availability/path context without changing existing scope semantics. |
| `wepppy/weppcloud/templates/gl_dashboard.htm` | Bootstrap contains outputScope. Roads results entry can select the new layer explicitly. |
| `wepppy/weppcloud/static/js/gl-dashboard/data/query-engine.js` | Supports current/base/scenario queries; root-scoped query-engine URLs differ from browse sitePrefix. Roads must not accidentally inherit scenario selection. |
| `wepppy/weppcloud/static/js/gl-dashboard/README.md` | Detector/orchestrator/state/map builder/renderer boundaries support a new vector overlay and legend. Existing scenario geometry reuse applies to hillslopes, not automatically to Roads. |
| `wepppy/nodb/mods/roads/monotonic_segments.py`, conversion loop | Emits generated string segment_id and geometry in input CRS; preserves original input ID separately. IDs can recur after preparation. |
| `wepppy/nodb/mods/roads/roads.py`, prepare_segments | Records CRS/upload hash/parameter signature; clears last-run summary on preparation. Persisted state invalidation alone does not prove surviving result files belong to new geometry. |
| Same controller, outslope-unrutted execution | Emits repeated source_segment_id across segment_hillslope_id/profile runs; synthetic remainder IDs have no road line. |
| `wepppy/nodb/mods/roads/_segment_loss_summary.py` | Correct source-profile annual detachment/full-area density and policy metadata; hashes manifest/PASS/WAT, not prepared geometry. |

## Read-only UM1 artifact audit

Inspected the previously validated copy at
`/wc1/runs/ro/roads-segment-summary-validation`; no artifacts were regenerated.
Prepared `roads.inslope.monotonic.geojson` contains 39 unique LineStrings with
CRS84 metadata. Manifest has 34 completed records and one skipped record. All
34 completed IDs match geometry; no duplicate prepared IDs. The other five lines
have no completed result; absence of a manifest row does not establish a skip reason.
Summary has 34 unique segment_ids, all profile_scope=road; there are no multi-profile
joins or remainders in this case.

Read `soil_loss_density_kg_m2 * 10` from the corrected summary:

| Statistic | Detachment (t/ha/year) |
| --- | ---: |
| Minimum | 0.1025 |
| 25th percentile | 1.9085 |
| Median | 2.4379 |
| 75th percentile | 3.5043 |
| 90th percentile | 6.4557 |
| Maximum | 17.4515 |

No zero or negative values in this sample. A linear scale is feasible, but most
segments occupy its lower range; this is evidence for offering a range override,
not enough evidence to choose universal erosion thresholds. Detachment density
is distinct from the earlier sediment-export totals and long-road mass dominance.

## Implementation risks and limits

1. Geometry IDs are preparation-local. The approved upstream replacement lifecycle
   invalidates prior results before re-preparation and requires a fresh Roads run.
2. A multi-profile aggregate can be a useful segment diagnostic, but cannot locate
   individual profile contributions along the line without further geometry.
3. MOFE modeled area is intentionally independent of mapped line footprint. Label
   full-profile values; do not infer geographic fill/buffer polygons.
4. Existing beta summaries are not automatically admitted as current results.
   Recovery is prepare/run again; no historical admission or migration mechanism.
5. Availability in baseline and Roads views must not cause parent Roads values to
   leak into Omni scenario/comparison displays.

No numerical/native-model change is needed for an individual-profile detachment
rate. Upstream invalidation and publication need runtime conformance work;
no native release is established as necessary by this inspection.
The GL module guide's `wepppy/docs/ui-docs/gl-dashboard.md` pointer is stale;
the existing user specification is `docs/ui-docs/gl-dashboard.md`.

## Reconciliation after operator feedback

The initial fingerprint/legacy-admission proposal and subsequent stable-identity
suggestion are superseded by the [preparation lifecycle contract](../schemas/roads-preparation-lifecycle-contract.md).
Roger rejected that complexity and explicitly waived beta backward compatibility.
The durable rule is replacement plus invalidation and a fresh run, enforced upstream
for every consumer. This note records static findings; it does not certify that
existing runtime invalidation already satisfies the new contract. Dashboard D1–D4
remain separate open decisions.
