# D8UpstreamRelief terrain contract

## Accepted engineering decision

The command is `D8UpstreamRelief`, with required `--dem`, `--d8_pntr`,
`--output`, `--area`, and `--elevation_units=m`. Optional `--coverage` writes
a propagated potential-truncation flag. The user adopted this engineering
formula in the 2026-09-08 America/Los_Angeles conversation and authorized
continuation; CLI details below are the implementer's bounded choices.

Accepted engineering definition: H(o) = max elevation of all upstream
cells including o, minus elevation at o. Use the raw measurement DEM with
supplied conditioned routing, and A = upstream cell count times projected
cell area, including o. T = H/sqrt(A), with H in m and A in m2.
This is an explicit physical quantity, not demonstrated reproduction of the
predictor used to calibrate Staley M3.

The alternatives differ under conditioned routing over raw elevations:

| Raw chain, evaluated at third cell | Maximum minus outlet | Highest source minus outlet | Catchment maximum minus minimum |
| --- | --- | --- | --- |
| 130, 120, 100 | 30 | 30 | 30 |
| 110, 130, 100 | 30 | 10 | 30 |
| 130, 90, 100 | 30 | 30 | 40 |

These expectations are independently derived arithmetic, not translated
reference code. The manuscript does not resolve these alternatives.
The pinned reference fails even the monotonic case; see
[reference evidence](reference_parity.md). Its behavior cannot adjudicate the
scientific definition. User ratification selects maximum-minus-outlet without
claiming reproduction of the original calibration preprocessing.

## Input and boundary semantics

Initially support single-band GeoTIFFs in WGS84 UTM EPSG:32601-32660 and
32701-32760, the supplied project-grid family. These EPSG definitions establish
horizontal meters even when GeoTIFF linear-unit tags are absent. Reject other
CRSs, non-meter explicit units, rotated/transformation-matrix grids, point
pixels, nonpositive/nonfinite spacing, and mismatched extents/dimensions/CRS.
Require a single top-left tiepoint at raster coordinates 0,0 and positive
original source pixel scales; legacy decoder assumptions do not satisfy this
validation. This is a bounded initial interface, not a silent conversion of
other grids.
Require `--elevation_units=m` as a caller declaration of raw elevation units;
reject contradictory explicit vertical-unit tags. No conversion is performed.

DEM and pointer valid-data masks must match exactly; a mismatch is an error,
not permission to shrink contributing area. NoData may be finite or NaN;
other nonfinite data are errors. WBT encoding is NE=1, E=2, SE=4, S=8,
SW=16, W=32, NW=64, N=128; zero denotes a terminal cell. Reject invalid
codes and cycles before writing outputs. Each valid cell contributes itself.
Routing can cross flat or rising raw elevations without changing the DEM.
Pointers leaving the raster or entering NoData terminate within the supplied
domain. They never subtract a NoData elevation.

Potential truncation is seeded at every valid cell adjacent in D8 to NoData
or the raster exterior and propagated downstream by logical OR. Optional
`--coverage` stores 1 for potential truncation and 0 otherwise, with NoData
outside the joint valid mask. Metadata always records flagged-cell count.
H/A remain within-domain quantities at flagged cells; they must not be
presented as proven complete catchments. A flag is conservative, not proof
of truncation; zero does not prove the supplied routing/source is correct.

Outputs preserve alignment, use Float64 H/A with NoData=-32768, and record
formula, raw DEM, pointer, meter declaration, area inclusion, coverage rule,
and elapsed time. Coverage uses UInt8 with NoData=255. Required output files
must be distinct new `.tif`/`.tiff` paths with existing parent directories;
existing files, symlinks and aliases are rejected before writes. This avoids
source overwrite and stale-output confusion. If I/O fails, previously written
outputs can remain; discard the whole output set and retry with fresh names.
No transactional publication is promised. Both wrappers retain the existing
subprocess boundary and pass path arguments without a shell.

Each individual TIFF is now published by a no-replace atomic hard link from a
private same-parent staging directory. Hard-link support is required; there
is no copy/overwrite fallback. Caller-controlled stable input files and parent
directories are required. This is a local CLI, not an adversarial shared-path
or hostile TIFF decoding boundary. On later failure, earlier published files
remain; discard the set before retrying. Cleanup failures are reported.
TIFF ImageDescription carries the stated metadata; final buffered writes are
flushed through the fallible direct writer before publication.
