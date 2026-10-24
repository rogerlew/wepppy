# Roads dashboard contract decision

Recorded 2026-10-24 05:32 UTC. Starting implementation revision:
`5227cb25831a1f86b2a70dd977d1cdad56a236cf`.

## Operator authority and exact delta

The operator requested road erosion mapping, selected detachment, rejected mapped
MOFE fill/buffer/land-use abstractions, selected the existing sediment palette,
required dashboard switching to Roads scope, and said “for other questions proceed
as recommended.” The next instruction authorized “review and disposition of
findings.” D1–D4 are accepted; review remains independent and implementation pending.

Add a road-centerline overlay with area-weighted full-profile annual detachment,
visible mixed-profile labels, remainder exclusion, jet2 linear project range with
maximum override, and independent visibility. Add a Baseline/Roads scope selector
using existing URLs and data paths. No producer, persisted schema, model, auth, queue or
deployment policy changes. This is an enhancement, not restoration of an already
implemented layer.

## Canonical authority matrix

| Authority | Obligation / amendment |
| --- | --- |
| `docs/schemas/roads-gl-dashboard-contract.md` | New display/navigation specification; D1–D4 accepted; review corrections here. |
| `docs/schemas/output-scope-contract.md` | Expose existing baseline/roads scope selection inside dashboard; no new scope values. |
| `docs/schemas/roads-segment-loss-summary-contract.md` | Unchanged annual units, full modeled areas, profile identity and source lineage. |
| `docs/schemas/roads-preparation-lifecycle-contract.md` | Preserved current-result admission, no-store and invalidation; cross-link one shared-guard materialization for the new map consumer. |
| `docs/schemas/query-engine-catalog-refresh-contract.md` | Unchanged freshness/source authorization for query-backed reads. |
| `docs/schemas/weppcloud-browse-parquet-filter-contract.md` | Preserve existing authorized artifact/schema/CSV behavior. |
| `docs/schemas/rq-response-contract.md`, `docs/schemas/weppcloud-csrf-contract.md` | No new task/mutation endpoint; preserve existing response/auth boundaries. |
| `docs/ui-docs/controller-contract.md` | Preserve existing control behavior and test conventions. |
| `docs/adrs/ADR-0105-roads-dashboard-detachment-display.md` | New display aggregation/default/scaling provenance; no model parameter change. |

The GL user guide is supporting documentation, not a replacement for the
canonical contracts. No feature-registry menu or entitlement change is proposed.

## State and request matrix

| Stored state | Required outcome |
| --- | --- |
| Roads never used / absent | Baseline usable; no result overlay; Roads scope unavailable with reason. |
| Prepared only / non-current | Geometry may be inspected without stale execution coloring; offer fresh run action. |
| Current populated continuous | Validated required artifact set, scoped WEPP views and detachment layer available. |
| Current typed-empty summary | Explicit no completed profiles; do not fabricate zeros. |
| Current single-storm without continuous summary | Upstream mode-specific scope admission; mean-annual detachment unavailable. |
| Reprepared, failed, busy, restored without valid receipt, historic beta | Existing lifecycle response; no historical or baseline fallback. |
| Malformed/hostile input | Bounded layer error without path/auth/HTML escape; preserve unrelated valid views. |
| Unauthorized/transient read failure | Existing auth/error response, not false artifact absence. |

Cross these with baseline/roads/default/invalid scope, root/child/batch context,
base/scenario/comparison selection, overlay on/off, initial/reload/bookmark/back
navigation, and rapid asynchronous transitions. Excluded combinations need clear
unavailability, not guessed parent or scenario data. Review this finite matrix;
do not claim exhaustive runtime coverage before implementation.

## Compatibility, security and regression evidence

Data compatibility is read-only: no key/column renames or summary regeneration.
Use prepared geometry ID to join manifest profiles and summary rows, then verify
mass/area units and actual rendered values. New controls preserve baseline default
and existing independent hillslope/channel behavior. Treat source labels, geometry,
URLs and stale responses as untrusted; auth and lifecycle remain authoritative.

Future validation must exercise actual read boundaries, rendered legend/details,
scope round trips and invalidation races, including negative/zero/empty/partial,
projected CRS, hostile labels and child authorization. The observed 39 lines/34
profiles only demonstrate one populated inslope fixture; mixed-profile and state
tests remain required. No production-equivalent validation claim is made here.


## Reviewed integration refinement

The coherent map consumer uses an additive opt-in `resources/roads.json?view=detachment` response, specified in the canonical dashboard contract. This is an existing-route read extension, not a new endpoint/service. Ordinary geometry callers retain their shape and prepared-only behavior. The response joins and transforms existing artifacts under one shared admission guard; no persisted source schema changes. Exact implementation surfaces include the existing Roads map resource/controller reader and GL data/state/render modules.
