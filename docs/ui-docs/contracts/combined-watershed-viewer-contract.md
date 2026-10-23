# Combined watershed viewer contract (PCV-01)

## Status and authority

Prepared 2026-10-12 for the operator-authorized forest repair. Implementation follows accepted checkpoint `d75460acc`; forest validation and separately authorized production rollout are tracked in the Portland work package. The operator requires existing PortlandGroup members to see the Portland collections and authorized forest execution, stack restarts, and dev-agent permission changes. Production deployment and production data writes remain outside this execution authorization.

## Collection admission

The existing `PortlandGroup` Flask-Security role grants collection read access to exactly the 63 run IDs registered in the server-owned Portland collection catalog extracted from the nine existing Portland interface links. The catalog is version controlled; maintenance adds/removes explicit IDs and is reviewed as a resource-access change. No prefix, submitted config, feature-mod flag, or JWT group string establishes that association. Membership is evaluated from the current authenticated account on each collection request. No new feature-action group is introduced.

Each run must independently be PUBLIC, be in the Portland catalog for a current PortlandGroup member, or be explicitly owned by the authenticated caller or admitted by existing Admin/Root roles. The ordinary ownerless-run rule is not a collection-entry grant: anonymous admission to this entry remains PUBLIC-only. Reject the whole requested collection when any run is unauthorized. Bounds viewer and URL generator use the same admission. Bounds retains its bounds display with server-resolved configuration and safe DOM rendering; `data_uri` indirection is rejected because it bypasses inspection of the explicit run list. Membership grants no mutations, membership administration, unrelated private runs, or public publication.

## Existing resource visibility and downstream consumers

The 63 incident runs are ownerless and already readable through ordinary geometry/report/query paths. PCV-01 preserves that existing access: denying anonymous collection entry does not turn these historical artifacts into private data. No general ownerless-run lockdown, query-engine authorization rewrite, or new result embargo is authorized. Existing independently valid public, owner, admin, service and resource grants remain unchanged. If inventory finds an actually private downstream resource that a member cannot read, extend the checkpoint with its exact read-only surface before patching it; never grant mutation access through general `authorize()` changes.

This bounded collection admission is distinct from feature-action governance in [the feature access contract](../../schemas/feature-access-governance-contract.md). Existing query-engine and browse transports retain their current identity, scope, sensitive-file and path containment rules under [browse authorization](../../schemas/weppcloud-browse-auth-contract.md). No credentials may appear in a share URL or a saved browser artifact.

## Inputs, errors, and generator

Existing `/combined_ws_viewer/` and `/combined_ws_viewer2/` links render the repaired Deck.gl collection. Preserve the `ws` list of runid/cfg objects, title, center [latitude,longitude], zoom, units SI/English, varname, and varopts. Resolve the actual config from run metadata; historic URL config aliases are not authoritative. Deduplicate run IDs preserving order. Bound a request to 100 runs; reject malformed JSON, invalid IDs, nonfinite/out-of-range view values, unknown variables/units, and nonpositive ranges with HTTP 400. Unauthorized lists return 403 without naming the denied run. Empty entry renders an explanatory empty state with a generator link. Missing runs/required data return a bounded readiness error to authorized callers, never a success-colored empty map.

The generator GET without inputs renders an empty form. Submitted empty/invalid lists return actionable 400 responses; unauthorized lists return 403. POST remains protected by the [CSRF contract](../../schemas/weppcloud-csrf-contract.md). Generator does not assign roles. Encode title, IDs, and JSON through normal URL encoding; use safe JSON/DOM rendering. Union bounds must include every run without mutating NoDb extents. Preserve existing numeric display defaults and established unit factors.

## Data and display

Use retained geometry and WEPP loss output, existing native interchange converters and query-engine directly. No Flask wrapper around query-engine and no conversion on page GET. A focused combined-viewer controller may reuse the existing Deck.gl map controller, basemap pattern, composite feature keys, and colormaps without enabling the full dashboard's unrelated graphs or BatchRunner readiness filtering. Do not force legacy collections into BatchRunner projects.

Runoff, subsurface runoff and baseflow display average annual depth; loss displays hillslope soil loss density, not outlet sediment yield. Phosphorus displays total phosphorus density when every selected run has valid phosphorus output. Missing optional phosphorus disables that choice with an explanation and preserves the other variables; an explicitly selected unavailable variable reports its unavailability rather than relabeling another measure. Missing required rows/geometry/values identifies incomplete readiness to authorized callers, and no watershed is silently omitted. Use composite run/hillslope keys. Preserve zero values and treat nonfinite/missing required values as errors. Popup numeric values and run-specific links must match the selected feature.

Legacy display factors remain 25.4 mm per inch and 1.12085 kg/ha per lb/acre; ranges and legends use the selected unit system. Preserve winter, jet2, and viridis colormaps and the existing phosphorus color normalization. Unit changes convert the range without changing physical values. Share links record current center/zoom, selected variable, units, ranges and title.

## Artifact compatibility and observability

Prepare derived artifacts offline, starting with a forest copy. Preserve source NoDb/model outputs and PUBLIC markers. Record source hashes, exact writer revision, new paths and semantic comparisons before rollout. No new scientific schema/formula or model rerun is authorized. Use existing Parquet schemas when needed; existing geometry properties or NoDb summaries may provide the WEPP-to-Topaz mapping if they suffice, avoiding unnecessary conversion. Query-engine must consume exact validated files. Keep provenance/failure evidence and prepared artifacts inspectable under normal authorized browse/archive tooling; do not introduce hidden-only project state.

Preparation must be repeatable, refuse unexpected existing outputs, record before/after hashes, and remove only package-created files on rollback. Missing required source data is an explicit failure. A live collection must display all requested watersheds or an explicit incomplete/error state, not partial success.

Stationary pointer releases may select a hillslope for up to five seconds; movement/drag thresholds and double-click behavior remain Deck defaults. The focused viewer uses Deck's documented click-recognizer time option because measured synchronous picking of dense legacy geometry on a software GPU took about 2.5 seconds, which otherwise counted against the default 250 ms gesture limit. This is a finite UI allowance, not a model/display parameter change; stalls longer than five seconds still require keyboard hillslope selection. Other dashboards retain their default recognizer settings. Decision provenance: [ADR-0087](../../adrs/ADR-0087-combined-viewer-pointer-duration.md).

## Acceptance

Verify all nine real Portland links on forest with a non-admin PortlandGroup member, revoked member, anonymous/nonmember and existing independent grants. Verify unrelated private/mixed lists fail, special-character titles are safe, all variables/units/ranges and share/reload work, composite identifiers do not collide, original files remain unchanged, and query values agree with legacy outputs. Test absent, empty, populated, supported legacy and hostile states separately from request combinations. Retain direct writer/query/browser evidence and independent correctness/security reviews. Forest readiness and production repair are separate claims.

Offline maintenance may prepare derived outputs for READONLY legacy runs without removing their READONLY marker: run the native writer against a visible staging copy, validate it, then publish only the manifest-owned derived files and a catalog built with the existing catalog-entry builder. This is explicit operator-invoked preparation, not ordinary activation or a request-time bypass. Refuse to overwrite an existing catalog/output of unknown provenance; preserve the marker and original files byte-for-byte. Retain staging/failure evidence through normal project inspection and document rollback.

Exact preserved measures come from the already averaged `wepp/output/interchange/loss_pw0.hill.parquet`: key `wepp_id`, area `Hillslope Area` (ha), runoff/subrunoff/baseflow from their `* Volume` columns (m³) divided by `(area_ha * 10)` to obtain mm; loss from `Soil Loss` (kg) divided by area_ha; phosphorus from native `Total Pollutant` (kg) divided by area_ha for runs whose valid phosphorus options establish pollutant meaning. Do not average these rows again or substitute sediment yield/tonnes-per-hectare. Reject zero/nonfinite area. Match `wepp_id` to TopazID through existing watershed metadata or geometry; verify a one-to-one complete join. These formulas preserve the legacy report/viewer semantics and native schema rather than introducing parameterization.

## Query catalog coordination (specified; implementation pending)

[Query-engine catalog refresh](../../schemas/query-engine-catalog-refresh-contract.md)
requires a stable shared lifecycle/publication guard. This does not revoke this
contract's explicit operator-invoked READONLY preparation exception or grant it
to generic refresh workers. Preparation and manifest-owned rollback join that
guard while preserving staged exclusive publication, refusal to overwrite
unknown outputs and hash-owned rollback. Generic async migration of this
preparation workflow is excluded.
