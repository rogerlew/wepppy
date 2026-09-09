# Peridot centroid projection release

## Behavior and provenance

The Peridot release at `3cef07bdc93a595016d80d0619718809a1bdccc8` converts each exported pixel centroid through the source raster affine transform and CRS into WGS84. It replaces independent-axis interpolation between two raster corners, which displaced Portland sampling locations by hundreds of meters.

The geographic columns in hillslope/channel/flowpath Parquet and sub-field CSV now use pointwise PROJ. Pixel centroid indices and their existing corner-based affine convention remain unchanged. One transformer is reused within each writer. Projection failures are explicit errors; no approximate fallback is used. Bedrock classes, kslast fallback values, and nearest-cell sampling policy are unchanged.

The three vendored binaries are `abstract_watershed`, `wbt_abstract_watershed`, and `sub_fields_abstraction` under `wepppy/topo/peridot/bin/`. Build command: `cargo build --release --bin abstract_watershed --bin wbt_abstract_watershed --bin sub_fields_abstraction` in the Peridot repository. Copy the resulting binaries from `target/release/` using Peridot's operations runbook. [Release hashes](../work-packages/20260909_peridot_centroid_projection/artifacts/release_manifest.json) identify this build.

## Existing runs

Installing these binaries does not rewrite stored run metadata or model inputs. Existing source soil files may still show 0.01; the bedrock override is applied later to `wepp/runs/p*.sol`. Repair an affected run only through an operator-authorized workflow: preserve old outputs, regenerate abstraction, and rebuild dependent location-based inputs and simulations. Coordinate correction can affect consumers beyond bedrock conductivity.

Validate regenerated centroids against the source raster affine transform plus an independent CRS transformation. Do not adjust the conductivity raster to compensate for displaced centroids. The separate Python raster sampler rounding issue remains a follow-up.

## Evidence and limitations

All tested geographic outputs match pyproj within 1e-8 degrees. All three binaries execute inside the WEPPcloud container; real MOFE preparation on eight isolated Portland hillslopes writes the expected 0.0001 conductivity. See [validation](../work-packages/20260909_peridot_centroid_projection/artifacts/validation.md).

The source-baseline comparison preserves WBT/sub-field non-coordinate columns and slope bytes. TOPAZ geometry is already nondeterministic on this project: repeated unchanged-binary executions differ, so TOPAZ byte parity is not claimed. Investigate traversal ordering separately before relying on exact whole-run reproducibility.

The previous WEPPpy sub-field binary also predates the explicit flowpath CSV schema already committed in Peridot; rebuilding current source brings that existing release drift forward. The projection patch itself changes no column names. Production deployment and live-run repair were not performed by this package.

Decision and rationale: [parameterization ADR](../adrs/20260909_peridot_centroid_projection.md). Canonical centroid authority lives in Peridot `docs/contracts/watershed-output-contract.md`, “Centroid coordinate authority.”
