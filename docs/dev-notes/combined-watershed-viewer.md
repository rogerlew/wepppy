# Combined watershed viewer

The Portland landing page opens nine Deck.gl collections. Sign in with the existing `PortlandGroup` role. Public runs and independently owned/administered runs also work in explicit collections. A group member's collection must contain only individually admitted runs; sharing a URL does not share credentials or grant access.

## Using the map

Select soil loss, runoff, subsurface runoff, baseflow, or available phosphorus. Choose SI or English units and apply a positive color range maximum. Unit changes convert the range to preserve its physical meaning. Click a hillslope, or use **Inspect a hillslope**, for its result and watershed link. **Create share link** captures the current map position, variable, units, ranges and title. The generator accepts comma- or whitespace-separated run IDs; existing configuration aliases in old URLs are resolved from actual run metadata.

A missing optional phosphorus result disables that choice while retaining the other results. An incomplete required dataset produces a visible collection error; the viewer does not silently omit a watershed. Contact the project maintainer to prepare missing legacy results. Loading the page never runs conversion or changes a project.

## Developer contract

[PCV-01](../ui-docs/contracts/combined-watershed-viewer-contract.md) defines admission, compatibility, exact measures and acceptance. `utils/portland_collections.json` is the explicit, reviewed Portland resource association and landing-page link source. It is not a prefix-based permission. `utils/portland_collections.py` checks current Flask-Security roles and independent grants. Ordinary downstream ownerless-run access remains unchanged.

The route resolves configuration, extents and WEPP/Topaz IDs. The focused controller in `static/js/gl-dashboard/combined-viewer.js` reuses the existing Deck.gl map/basemap controller and colormap library. Its data module directly queries native averaged LOSS Parquet and joins retained subcatchment GeoJSON through composite run/Topaz keys. Repeated polygon fragments are allowed; missing or duplicate identifier mappings are not. Existing single-run and BatchRunner dashboards are separate consumers.

Both combined-viewer URL variants use the same controller. Bounds links keep their Leaflet bounds display with server-validated metadata and DOM text/link creation. `data_uri` collection indirection is rejected: a remote payload cannot bypass per-run server admission.

## Offline preparation and recovery

Use the existing native writer through the bounded offline entry point, within the installed host's `wctl` environment:

```bash
wctl exec weppcloud python -m wepppy.weppcloud.combined_viewer_preparation /resolved/container/run/path
```

Resolve each path with `get_wd(runid, prefer_active=False)` first; production Portland runs use a legacy root. Never append the URL config to the filesystem path. Inventory the exact selected runs and source hashes before preparing them. The command refuses preexisting interchange/catalog files of unknown provenance. It leaves original NoDb files, LOSS text, geometry and READONLY/PUBLIC markers unchanged.

Each run has visible `combined-viewer-preparation/manifest.json` and staging files. The manifest records source/output SHA-256, Python/native writer content identity, state, exact average-value comparison, positive areas and complete identifiers. The writer produces the existing native LOSS Parquet family and a query-engine catalog. Publication is exclusive and atomic on the run filesystem. An interrupted preparation is not reported as success. A completed, unchanged run is reusable.

For a failed or unwanted preparation:

```bash
wctl exec weppcloud python -m wepppy.weppcloud.combined_viewer_preparation --rollback /resolved/container/run/path
```

Rollback validates all original hashes and all present output hashes before removing only the fixed allowed output paths. A changed output or altered original stops recovery for inspection. Retain the manifest/staging directory under a new visible evidence name before retrying; do not delete a whole run. Normal authorized browse/download and archive/restore retain these artifacts.

## Validation and rollout

The [Portland package](../work-packages/20261012_portland_combined_viewer/package.md) retains forest evidence and the [rollout handoff](../work-packages/20261012_portland_combined_viewer/artifacts/rollout-handoff.md). Production code deployment, production preparation, and production acceptance are separate steps. Do not create PUBLIC markers as a repair. Do not extend this preparation helper to unrelated datasets without a compatibility plan.

Focused checks cover route admission, generator bounds/encoding, the real native writer and recovery, and JS normalization/joins. `wctl run-npm smoke combined-viewer.spec.js` exercises all nine real collections using the gitignored dev-agent credentials. Its optional revoked-session check uses a gitignored storage-state file; never retain credentials or cookies in package evidence.

## Dense-map pointer interaction

The combined viewer allows a stationary press/release lasting up to five seconds to select a hillslope. Deck includes synchronous picking time in its gesture duration; forest Chromium software rendering measured about 2.5 seconds for these legacy polygons. The scoped setting preserves drag-distance, pan and double-click behavior and leaves other dashboards unchanged. Very slow devices can use the keyboard hillslope selector if a pick exceeds five seconds. No numeric result, range or model parameter changes.
