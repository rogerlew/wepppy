# Correctness review: Peridot centroid projection

## Metadata and user outcome

Reviewer: Codex (self-review; no independent agent review). Date: 2026-09-09 UTC. Scope: Peridot raster projection helper, eight Parquet/CSV writers, TOPAZ/WBT/sub-field callers, and WEPPpy vendored executables. Authority: Peridot docs/contracts/watershed-output-contract.md, Centroid coordinate authority; WEPPpy docs/adrs/20260909_peridot_centroid_projection.md.

The user expects mapped conductivity at the real hillslope location. The geographic coordinate now follows the raster's affine transform and actual CRS, with unchanged pixel indices and corner convention. One transformer per writer avoids sharing native PROJ contexts between Rayon tasks.

## Valid-state and input review

| State / input | Expected behavior | Evidence |
| --- | --- | --- |
| Populated projected raster, TOPAZ | Exact geographic centroids | 505 hillslopes and 220 channels from rebuilt binary; independent pyproj equality |
| Populated WBT raster with full flowpaths | Exact coordinates, unchanged other outputs | 7 channels, 17 hillslopes, 2291 flowpaths; non-coordinate columns and slopes identical |
| Sub-field raster | Exact CSV coordinates and stable schema | 17 fields, 2291 flowpaths; non-coordinate columns and slopes identical |
| Southern UTM / rotated affine | Use hemisphere and all affine coefficients | Rust reference-coordinate regression tests |
| Missing or invalid CRS | Explicit writer initialization error | Rust error tests, no approximate fallback |
| Invalid transform / failed projection | Explicit input/data error | Nonfinite geotransform and out-of-domain UTM tests |
| Existing saved run | Readable, not automatically migrated | Schema retained; production run unchanged |
| Optional full flowpaths disabled | Required tables only | Isolated TOPAZ --skip-flowpaths execution |

## Error and partial-state policy

PROJ initialization errors are InvalidInput; conversion/nonfinite-output errors are InvalidData, with pixel context. Parquet writers project before creating the output file. CSV writers may leave partial CSVs on conversion failure, as other existing write failures do; caller receives an error. CLI errors remain propagated through the existing contract. Abstraction still recreates its output directory; tests used isolated copied inputs exclusively.

## Findings and disposition

No open medium/high findings introduced by this patch. The two-corner approximation is no longer used by any metadata writer. All eight writers have direct output regression coverage. No dependency, permission, locking, authentication, or queue changes.

Confirmed preexisting limitation: TOPAZ regenerated geometry is nondeterministic on seductive-sabra. A second run of the unchanged source-baseline executable changes the same non-coordinate column set (channel slope/length/direction/area and dependent hillslope dimensions/mode/area). Therefore TOPAZ geometry byte parity is not claimed. The production diff changes only coordinate export, while deterministic WBT/sub-field comparisons preserve all other columns and slope bytes. Follow-up investigation should address TOPAZ traversal determinism; this package does not silently expand into that refactor.

Confirmed release provenance difference: the old WEPPpy sub-field binary predates the already-committed explicit flowpath CSV schema. Source-baseline comparisons use Peridot 98e8a43, whose only difference from pre-task 495abd5 is the contract checkpoint. This package vendors current source, so it also brings that existing source/binary drift forward. No columns were changed by the centroid patch itself.

## Validation conclusion

Corrected container-generated coordinates agree with independent pyproj within 1e-8 degrees (observed maximum 1.42e-14). Real MOFE preparation inside the WEPPcloud container produces 0.0001 for all OFEs on eight previously mis-sampled hillslopes. All three vendored binaries execute successfully in the existing container runtime. Unit and full-suite results are recorded in validation.md.
