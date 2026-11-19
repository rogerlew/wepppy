# Launch both I-CREWS presets from Site Specific Resources

Local implementation completed on 2026-11-19. The repository gate is
blocked by the existing SSURGO fixture, documented in the
[validation record](../../artifacts/20261119_validation.md).

## Purpose

A visitor can start either an Idaho-centered WEPPcloud WBT run or an Idaho-centered
Multiple OFE run from the same card. Both use WBT and the same state outline for the
map overlay and for channel admission. A selected extent may cross the state
line and is accepted in full when it touches or overlaps Idaho.

## Progress

- [x] 2026-11-19 20:15 UTC. Scaffold the package and trace the assets, launch path and preset lineage.
- [x] Ratify the launch contract in `9867163fb` and the corrected WBT-MOFE lineage in `ac1e41236`.
- [x] Implement the card, assets, presets and attribution.
- [x] Validate both presets through artifact readback and complete independent review.
- [x] Record the unchanged SSURGO failure that blocks broad repository acceptance.

## Surprises & Discoveries

The operator corrected the MOFE lineage to
`wepppy/nodb/configs/disturbed9002-wbt-mofe.cfg`. It explicitly selects WBT,
sets `[wepp] multi_ofe = true`, uses `wepp_261118`, and includes RAP time series. A new config without a matching entry in
`wepppy/nodb/config_builder/preset_policies.toml` causes the shared
snapshot loader to reject the preset corpus, which can affect other presets.
The production-compatible legacy create mode accepts inline overrides. Use
the named-preset resolver for these two IDs in both modes and preserve allowed
unit and model overrides. The authenticated run map already passes a boundary
URL to the controller, but the deferred overlay hook has no implementation.
Use the existing deck.gl layer registry for the Idaho outline on these runs.

## Decision Log

Use the two requested source presets as written and change their map sections
to the shared Idaho settings. The card discloses that both choices use WBT and that the second models
hillslopes with multiple overland flow elements. The two presets use public
Preview access and the established creation and CAPTCHA behavior. The card
and run footer use the I-CREWS product acknowledgment and Idaho EPSCoR
disclaimer. See the [contract decision](../../artifacts/20261119_contract_decision.md).

## Outcomes & Retrospective

The interface is implemented and locally validated. Both WBT variants
produced channel artifacts on each side of the Idaho border. A disjoint
request preserved the previous artifacts and a retry succeeded. Real WEPP
preparation retained two overland flow elements from a seeded hillslope.
See [validation](../../artifacts/20261119_validation.md) for browser,
creation, artifact evidence and the broad gate.

## Milestone 1. Ratify the launch and attribution contract

Read the nearest Weppcloud and NoDb guides, the contract-first standard, the
feature registry specification, and the existing
`docs/schemas/channel-delineation-map-boundary-contract.md`. Record the
operator's launch requirements and review the proposed copy in `package.md`.
Define the mapping from each button to its preset, role and maturity policy,
and where to show program attribution. Use the existing extent semantics.
Complete the reviewed, standalone canonical checkpoint before editing
launch templates, configs, or runtime code.

## Milestone 2. Wire the existing interface and presets

Add an I-CREWS article under `section-site-resources` in
`wepppy/weppcloud/templates/interfaces.htm`. Follow the Disturbed WBT
creation form for user preference handling, authenticated submission and the
existing anonymous CAPTCHA flow. Give both visible launch choices their own
form and preset value. Use the supplied river-and-dam illustration. Preserve
the card's responsive behavior and keep button labels and funding credit in
page text. Use the established run title/interface metadata and place the
credit where either preset's direct run URL can expose it. Enable Idaho's
outline on both run pages in the map bootstrap and wire the existing map
controller layer helper to render it. Test layer visibility and repeated
bootstrap without duplicate layers.

Copy `disturbed9002_wbt.cfg` to `i-crews.cfg` and `disturbed9002-wbt-mofe.cfg`
to `i-crews-mofe.cfg` under `wepppy/nodb/configs/`. Preserve each source's
effective model settings. Set both map sections to:

    [map]
    center0 = [45.6, -114.15]
    zoom0 = 5
    boundary = "static/mods/i-crews/idaho-boundary.geojson"
    boundary_check = "intersects"

Use the relative static prefix so the run map builds its URL under the
configured site prefix. Register both IDs in
`wepppy/weppcloud/feature_registry/config_registry.yaml` and in
`wepppy/nodb/config_builder/preset_policies.toml` together. Mirror each
source's permitted launch overrides. Keep the boundary and its check mode
preset-owned. Choose WBT backend metadata for both. Enforce the two
new presets' allowlists in legacy creation as well as snapshots before run
allocation. Keep other presets on their current creation path.

Install the verified GeoJSON under `wepppy/weppcloud/static/mods/i-crews/`.
If the candidate is missing, download the Census 2025 national 1:500,000
state shapefile archive and extract Idaho, state FIPS 16, as WGS 84 GeoJSON.
Run in a scratch directory with GDAL:

    curl -fLO https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_state_500k.zip
    ogr2ogr -f GeoJSON -t_srs EPSG:4326 -where "STATEFP = '16'" -select NAME,STATEFP -lco RFC7946=YES -lco COORDINATE_PRECISION=6 idaho-boundary.geojson /vsizip/cb_2025_us_state_500k.zip

Use an absolute ZIP path after `/vsizip/` if the installed GDAL cannot resolve
the relative path. Retain source vintage, filter, coordinate precision and
output checksum. Confirm one valid polygon and keep the boundary reasonably
close to the tested 91 KB export.

## Milestone 3. Verify both run flows

From the task worktree, start with:

    wctl run-pytest --profile python -- tests/weppcloud/routes/test_feature_registry_runtime.py tests/microservices/test_rq_engine_project_routes.py tests/nodb/test_channel_boundary.py
    wctl run-pytest tests --maxfail=1

Run frontend lint and tests if frontend assets or behavior change. Verify
the card on desktop and narrow screens and both buttons under the resolved
creation policy. Create two disposable projects through the UI and reload
each persisted config and map. Exercise inside, disjoint and cross-border
requests for both presets. Test Upload DEM where used by the normal run flow.

Read the channel artifacts consumed by the map and the exact prepared
multiple-segment input produced by the MOFE run. Use the installed WBT executable selected by the two runs. Capture semantic output and
rejection noninterference evidence. Complete independent correctness and security reviews
and document any baseline regression blocker without claiming a green suite.

## Idempotence and recovery

Run acceptance in disposable projects and retry rejected extents on the same
project to verify recovery. Before any rollout, verify the shared asset is
available to the web, API and workers at the same revision. If an
environment cannot use one of the inherited executables, record it and
resolve that runtime prerequisite before claiming the corresponding native
workflow works.
