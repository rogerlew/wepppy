# Roads GL Dashboard contract: independent correctness review

Reviewer: `/root/roads_dashboard_correctness`. Review date: 2026-10-24 UTC.
Starting implementation revision: `5227cb25831a1f86b2a70dd977d1cdad56a236cf`.
Scope: contracts, source inspection and read-only persisted artifact inspection.
No controller methods, model execution, project mutations or runtime tests were
performed. This reviewer edits only this review artifact, not the proposed rules.

## Findings

| ID | Severity | Finding and concrete evidence | Smallest correction | Required validation |
| --- | --- | --- | --- | --- |
| COR-01 | High | Initial `roads-gl-dashboard-contract.md`, **Dashboard output-scope switch**, and `output-scope-contract.md`, **GL Dashboard scope discovery**, say a missing segment summary alone must not disable valid Roads scope. The lifecycle contract, **Diagnostic and restore details**, makes that summary mandatory for continuous mode. The actual continuous receipt below includes it. A consumer must not bypass mode-specific admission to implement overlay independence. | Qualify independence by upstream admission: a valid single-storm run may omit this mean-annual summary; a typed-empty continuous summary remains present and valid. Missing mandatory continuous resources make Roads unavailable. | Missing continuous summary yields the established 409/code even with a remaining receipt; valid single-storm results retain their contracted scope behavior without a mean-annual overlay; typed-empty continuous results show no completed profiles. |
| COR-02 | High | Initial **Inputs, identity and provenance** and **Integration and acceptance boundary** allow separate existing geometry/metadata/manifest/query fetches but do not establish a single materialized set. Each fetch may pass its shared guard while another session completes prepare/run between requests. Reused sequential segment IDs then allow old geometry to color with new output; canceling this client's old requests does not detect that sequence. | Materialize geometry, effective CRS, manifest and summary under one existing shared Roads admission/read guard, or prove equivalent binding with an existing mechanism. Prefer extending an existing authorized read surface; do not add a persistent generation/fingerprint subsystem. Apply targeted catalog freshness where query selection is used. | Interleave other-session prepare/run between component fetches with reused IDs. The consumer must return one coherent set or the canonical explicit busy/unavailable response, never mixed geometry and result values. Archive/restore and stale query selection participate. |
| COR-03 | Medium | Initial **Inputs, identity and provenance** calls prepare metadata “source CRS” and leaves the field to confirm during implementation. `roads.py` prepares coordinates using effective `input_crs_value`, including inferred/DEM fallback, then persists it as `roads.inslope.summary.json.input_crs` at the prepare-summary publication. `source_crs` and `configured_input_crs` can differ. The existing `query_map_segments_geojson` also omits the original CRS member. | Name the persisted effective `input_crs` as prepared-coordinate authority from the same coherent set; do not substitute original/configured CRS. Specify consistent longitude/latitude axis order and explicit rejection of unresolved/conflicting effective metadata. | A projected fixture and an inferred/DEM-fallback fixture whose effective CRS differs from configuration render in the correct location; unresolved/conflicting declarations fail explicitly. The current CRS84 fixture alone cannot prove this. |

These findings concern contract consistency and scientific identity; they do not
reopen the accepted display decisions. COR-02 overlaps the security review's
coherent-read finding and should be dispositioned once across both reviews.

## Scientific and schema assessment

The selected `soil_loss_kg / modeled_area_m2 * 10` conversion correctly expresses
the source's already annual kg/m² as t/ha/year. Multiple profiles require summed
annual mass divided by summed full modeled area, not averaged densities or a
second inclusion-ratio/duration adjustment. Mixed-profile labeling, no inferred
MOFE footprint, remainder exclusion and the explicit non-incremental interpretation
agree with the upstream segment-summary contract and ADR-0105.

Geometry joins on prepared `segment_id`; distinct profile identity remains
`segment_run_id`. Receiving hillslope IDs are attribution context, not map keys.
Manifest status defaults/legacy parsing cannot authorize a historical current set.
Partial successful diagnostics do not override whole-run lifecycle failure. Empty
data, zero detachment and missing results remain different states. Negative values
need signed details and a separate legend state even when another profile on the
same line has positive mass.

Existing implementation risks for the later implementation plan:

- `static/js/gl-dashboard/data/query-engine.js::createQueryEngine` currently has a
  shared `roadsUnavailable` latch; `gl-dashboard.js::ctx.onRoadsUnavailable` reloads
  the dashboard. An optional Roads query in Baseline must not poison other queries
  or cause a reload loop. Scope transitions and overlay-specific errors need direct
  noninterference tests, including subsequent successful baseline queries.
- `Roads.query_map_segments_geojson` writes an access log and strips the input CRS
  member. It was inspected as source, not called for this read-only audit. Reusing
  its response without effective preparation CRS would be unsafe for projected data.
- A query-engine catalog entry being present is not evidence of current schema or
  physical source. The existing targeted freshness barrier and Roads source
  authorization must remain effective within joined materialization.

## Read-only artifact evidence

Inspected `/wc1/runs/cl/clogging-starch` through JSON/PyArrow reads in the existing
weppcloud container. Files were not rewritten and no NoDb instance was created.
This is a static fixture observation, not a concurrency or browser validation.

| Check | Observed result |
| --- | --- |
| Prepared geometry | 39 LineString features; 39 distinct generated segment IDs |
| Manifest | 34 completed, 1 skipped; four prepared lines have no manifest record |
| Segment summary | 34 rows, 34 distinct profile IDs; all `profile_scope=road` |
| Join coverage | No completed profile missing a summary row; no summary segment missing geometry |
| Duration | Every row has `simulation_years=16` |
| Annual density identity | Maximum absolute `soil_loss_density_kg_m2 - soil_loss_kg / modeled_area_m2` difference: 0 |
| Display range | 0.10250644089062491 to 17.451505244860165 t/ha/year |
| CRS | Geometry and prepare effective `input_crs` both `urn:ogc:def:crs:OGC:1.3:CRS84`; prepare source is `geojson_crs` |
| Current receipt | `roads_current_v1`, `is_single_storm=false`; mandatory list includes summary and corrected water-accounting resources |

SHA-256 at readback (paths relative to the run root):

| Artifact | SHA-256 |
| --- | --- |
| `wepp/roads/segments/roads.inslope.monotonic.geojson` | `a82879942857cab0ffe4b690f51bbcc66d0565f59e23886f7288e87a7ba5e51d` |
| `wepp/roads/segments/roads.segment.pass.manifest.json` | `8b76b817ac209d4343ccfead048b6a0124556268c07be888ffce10973f73bddf` |
| `wepp/roads/segments/roads.inslope.summary.json` | `fcb72b2edeaceff90208da8f8ef17e3c1120e636b15ba4f28c5412ccd9b839ea` |
| `wepp/roads/output/interchange/roads_segment_loss_summary.parquet` | `d661ca3fd40d915bf9d6b82d4468b4223956f62149dc15d171432eac45a8c845` |
| `wepp/roads/output/roads.current.json` | `c9053d4b52365b878e3ac6bac6fbe24bba087608e08ce285bdf8f843209a247e` |

This fixture establishes one-to-one inslope feasibility only. It does not validate
mixed profiles, multiple profiles per line, remainders, negative values, projected
coordinates, stale generations, current typed-empty/single-storm behavior, or
rendering/keyboard interactions. Those remain explicit implementation acceptance.

## Valid-state and transition assessment

| Stored state | Correct outcome |
| --- | --- |
| Never used or absent | Baseline remains usable; no detachment result; scope unavailable with reason |
| Prepared only | Prepared geometry remains inspectable; no current detachment coloring |
| Current continuous with populated valid summary | Current scoped resources and correctly joined layer available |
| Current continuous with typed-empty summary | Current scope retains upstream availability; explicit no completed profiles |
| Current continuous with missing mandatory summary | Existing current-result 409/code; cannot treat this as optional overlay absence |
| Current single-storm without summary | Existing mode-specific scope admission; no mean-annual detachment layer |
| Reprepared, failed, legacy without valid receipt | No old current-result admission; fresh full execution required |
| Busy writer | Existing explicit 409 busy response; no synthetic no-results success |
| Malformed join/metrics/CRS | Actionable layer error, with no fabricated values or effect on valid Baseline data |
| Unauthorized/transient read failure | Existing auth/error semantics; never classify these as absent artifacts |

Cross these with Baseline/Roads, base/Omni scenario/comparison, root/child,
overlay on/off, direct link/reload/scope switch, and late asynchronous responses.
Combined/batch semantics stay excluded. The parent decision matrix and ADR cover
the same boundaries. Back-to-Baseline navigation must survive Roads invalidation;
incompatible graphs/scenarios must not retain old data under a new label.

## Initial verdict

Contract gate: **hold for COR-01 through COR-03 correction and independent
re-review**. Upstream units, geometry abstraction policy and accepted aggregation
are otherwise compatible. No runtime implementation or deployment approval is
implied. Post-amendment disposition and reviewed-file hashes will be recorded
here when the author requests re-review.

## First post-amendment review

The author's mode-specific scope rule, single guarded map materialization and
effective `input_crs` authority close COR-01, COR-02 and COR-03 at contract level.
The additive opt-in `resources/roads.json?view=detachment` response preserves the
ordinary map response when the new view is omitted. Its explicit single-storm,
typed-empty, complete/partial/no-results states and reserved computed namespace
are consistent with the accepted semantics. Query failures now explicitly remain
isolated from baseline requests, addressing the observed global-latch risk.

One medium follow-up arose from the newly explicit response projection:

| ID | Severity | Finding | Smallest correction and validation |
| --- | --- | --- | --- |
| COR-04 | Medium | **Coherent detachment view payload** omitted `segment_length_m`, while **Display and interaction** requires road length in details. Monotonic geometry preserves arbitrary uploaded attributes but guarantees no per-prepared-line length property; an uploaded `Length` may refer to an unsplit source feature. A client cannot recover the required modeled segment length from the specified profile fields. | Include nullable existing summary field `segment_length_m` per constituent and label it modeled road-segment length. Never sum repeated profile lengths or substitute an uploaded source length for it. Verify a split line and multi-profile line display their actual source-profile lengths and retain null when unavailable. |

The checkpoint's compatibility statement should also say no *persisted* schema
change, distinguishing that promise from the explicit additive response shape.
The follow-up does not require new source artifacts or a model calculation.

## Final independent disposition

Rechecked 2026-10-24 05:39:14 UTC after the author's COR-04 amendment.
**Contract correctness gate: pass. No open high or medium correctness findings.**

| Finding | Disposition confirmed by reviewer |
| --- | --- |
| COR-01 | Closed: dashboard and output-scope contracts preserve mandatory continuous summary admission and explicitly separate valid single-storm/typed-empty cases. |
| COR-02 | Closed: joined detachment response is materialized under one existing shared guard; all display surfaces consume that response; lifecycle cross-reference and race acceptance agree. |
| COR-03 | Closed: effective persisted `input_crs`, axis order, conflict rejection and inferred/fallback acceptance are explicit. |
| COR-04 | Closed: payload includes nullable per-profile `segment_length_m`; details label modeled source length, do not sum it or substitute uploaded unsplit lengths, and preserve missingness. |

The new read projection introduces no persisted schema/model changes. ADR-0105,
the decision checkpoint, scope amendment and UI-guide pending implementation
notice agree with the reviewed behavior. The author also recorded actionable
Baseline escape, optional Roads error isolation and incompatible scenario/graph
handling. No additional correctness blocker was found in those amendments.

Residual coverage remains the future implementation evidence already specified:
direct guarded readers during real writer/archive transitions, mixed/multiple
profiles and remainders, projected/fallback CRS, adverse numeric/missing states,
browser scope transitions and accessible details. The current production fixture
and documentation lint cannot establish those runtime guarantees. Implementation,
standalone checkpoint commit and deployment remain separate steps.

Reviewed-file SHA-256 at this confirmation (repository-relative paths):

| File | SHA-256 |
| --- | --- |
| `docs/schemas/roads-gl-dashboard-contract.md` | `e86c6690390c1b84e8402d05d9712f6265486ea8319568d2d90d3814dda7b54f` |
| `docs/schemas/output-scope-contract.md` | `1b01fca3fbf792267764fa6df34fc535f7bed6e7f96a347c2a3a3335ca196358` |
| `docs/schemas/roads-preparation-lifecycle-contract.md` | `6ab24cf434a78db908c50509ccb9ef9588dc38128732f1ec94f4d3da4bea384a` |
| `docs/schemas/roads-segment-loss-summary-contract.md` | `edf90ac20d033dc77ddaf79f32d206bee048778d5c88f2514d3b132cb5cddbd6` |
| `docs/schemas/query-engine-catalog-refresh-contract.md` | `79db9d3956cdcb47796190d8d4baceb6d67b3f1d200323b0fb21213cfe83365c` |
| `docs/ui-docs/gl-dashboard.md` | `8d1fd959ee1b7a08def7a46c083aa58fd7b22972e3412b73d0e1e10f14d440d6` |
| `docs/adrs/ADR-0105-roads-dashboard-detachment-display.md` | `7f9b3dae18eea5c803c235a1ab6babfdba8ec85c7a1f3d2f7c84610f0343dd60` |
| `docs/work-packages/20261023_roads_gl_dashboard/artifacts/2026-10-24_contract_decision.md` | `b0cc22242111f4174253d1da2785a4240b1a42752d81651e5d90680648621da7` |

Documentation check: `wctl doc-lint --path` on this review artifact passed with
zero errors/warnings. Spelling normalization was previewed; only “canceling” was
normalized. No runtime tests were run or claimed for this contract review.

## Final status-only confirmation

At 2026-10-24 05:40:51 UTC, independently checked the final contract, ADR, guide,
package and review-plan status wording. Each distinguishes completed contract
review from unimplemented runtime behavior and the uncommitted standalone
checkpoint. Reconstructing the prior status paragraphs reproduces the three
previously reviewed hashes, confirming no normative change in those documents.
All other hashes in the preceding table remain unchanged.

The final canonical-document hashes superseding that table are:

| File | Final SHA-256 |
| --- | --- |
| `docs/schemas/roads-gl-dashboard-contract.md` | `3cfb9eb59529fe226551ccfa904da42752b6522c61616f8dcab055f848e2d926` |
| `docs/ui-docs/gl-dashboard.md` | `09085bf65fc2ebfecb32010dd90af2148ef06711460e44e5d18987666646cc75` |
| `docs/adrs/ADR-0105-roads-dashboard-detachment-display.md` | `f631859edeebcf206dbd637a0392b11958e2b28a0720e9b67c53b53bcab0f178` |

Correctness approval remains contract-only, with COR-01 through COR-04 closed.
