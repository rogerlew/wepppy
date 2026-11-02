# Surface support contract implementation review

Disposition: **PASS for the clarified metadata-only contract ancestor.** Review only; no production code or tests were edited or executed. The inspected change set currently touches canonical documentation only under the RUSLE implementation scope.

The additive support object, explicit source-area units, null denominator behavior and distinction between known-area fraction and full footprint coverage are appropriate. Existing row_count/proxy keys remain intact; source precedence, finite out-of-range inclusion, final clipping, overrides, fallbacks and raster values are explicitly unchanged. Empty/all-unusable recognized columns retain diagnostics; absent files/columns retain existing unavailable reasons. Old manifests remain readable and explicit recalculation may add metadata. This is provenance/schema work rather than a parameter-formula change; the metadata-only ADR disposition is reasonable.

## Compatibility finding and closure

The existing weighted query filters NULL cover before conversion. Its comprehension also short-circuits on missing area and nonfinite cover. Consequently NULL cover with nonnumeric area, nonfinite cover with nonnumeric area, and nonnumeric cover with NULL area can be harmless excluded rows today. An all-row diagnostic pass could introduce conversion failures and change an otherwise valid weighted mean/fallback outcome. The current broad statement that malformed inputs retain the existing error contract does not fully specify these formerly unexamined values.

The revised canonical specification closes this finding: unparseable_cover_rows is explicit; excluded unparseable area counts as unknown; all three original short-circuit combinations are preserved. Original numerical aggregation determines query/parse failure before diagnostics attach. Consumed malformed inputs retain the prior unavailable/error outcome without partial support. Empty/all-NULL numerical data still receive complete support diagnostics. The decision adds actual-parquet regression states for each excluded malformed combination. No numeric policy or existing error selection changes are authorized.

## Implementation validation expectations

Use real DuckDB parquet reads, preserve order/selection for the existing numerical aggregation, and independently assert the frozen mean/clamp values. Include missing-file/column, empty, all-NULL, measured zero, finite out-of-range, nonfinite, mixed usable/excluded and area-absent cases; positive, zero, negative, NULL/nonfinite and unparseable area support; and the excluded malformed combinations above. Counts can overlap (used is not a disjoint cover-value class); do not sum all counters as if they partition records. Known positive area includes all eligible area observations, not only usable cover rows.

Check recognized-column precedence when an earlier alias is unavailable and a later alias is populated, so metadata work does not silently introduce a new fallback heuristic. Both RAP and SBS must propagate support into actual generated manifests while preserving raster values and existing auto/manual semantics. No new persisted NoDb, queue, locking, permission or native-input contract is involved. Broad application validation remains required after substantive production implementation, not for this documentation-only checkpoint.

Inspected starting production loader: _load_cosurffrags_surface_proxy_from_soils_parquet in c_integration.py. The canonical specification remains marked implementation pending. After the clarification and two independent approvals, commit the contract/decision/reviews as an ancestor before production edits, then record that revision in the active tracker.

## Approved canonical identities

SHA-256:

- wepppy/nodb/mods/rusle/specification.md: `0130e56ad8b72bffca4935cbd467de60529cf51cd1d58a7aa43359b183360b99`.
- docs/schemas/rock-fragment-representation-contract.md: `2560586e2f1b734ac351bf5f213411f18d9e3c8740c7e1e81e91ce7aeb498eac`.
- docs/work-packages/20261101_rock_water_development/artifacts/20261101_surface_contract_decision.md: `8d08c323447ed4629cca5d001f34ed2c2059fb9ba79e38acfdf87996559e889b`.

Ancestor approval covers this additive metadata contract only. Production implementation and actual artifact propagation require subsequent independent review. Reviewer writers clear after scoped lint.
