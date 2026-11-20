# European land cover and management mapping contract

## CORINE provider mapping

A shipped CORINE gridded source uses
the European CORINE management table (`eu-disturbed`) for each supported year
and existing runtime spelling. Provider identity comes from the land-cover
catalog, without guessing from a class number or the run's locale. Class 25
uses the table's Mixed forest management. The stored upload/treatment selection
remains available to those input controls and their corresponding operations.
A gridded CORINE build does not use that stored selection. Preserve this
precedence for CORINE. A valid existing run-owned custom map remains the
explicit override. A map file explicitly configured for the same CORINE
provider retains its current support. The built-in `eu-disturbed` table supplies
the default in other cases. A stale stored built-in upload token cannot serve
as an explicit override. Existing built assignments
and management summaries remain readable without schema migration.

The Landuse form retains the stored value for the upload selector. The build
route, controller and downstream generation use the map for their effective
source. The current standalone mode and dataset controls still persist their
selections independently of a build attempt. A hidden upload mapping
selection submitted with a gridded build must not override the gridded
provider. Detect the source/mapping mismatch for an existing affected run
on its next build; the run page does not write the controller on read.
A successfully rebuilt CORINE run produces management summaries and
Parquet from its actual raster assignments. Existing non-CORINE builds,
edited custom mapping tables, and legacy projects retain their modes
and map semantics.

Validate a requested build's MOFE buffer against its requested dataset and
mode before setting the selection. MOFE base managements must be resolved
before burn classification and deck synthesis. A same-number class from an
earlier source cannot supply its management. Preserve compatible cover
overrides when the management template and disturbance class match.
An uploaded treatment raster uses its explicit mapping to interpret treatment
codes and resolve applied treatment templates. Keep the provider map for the
unmodified base classes. Treatment selection on the active land cover resolves
its destination and template through the same effective provider map.

## Separate source catalogs

Use the plain ESDAC ESDB USE-DOM table only for the ESDAC code namespace.
Its class numbers do not identify CORINE classes. Keep audited management
template and scenario changes under their own compatibility and generated
artifact validation, including the separate European Disturbed ESDAC table.

### Management reference compatibility

For keys 115, 116, 117 and 124 in the Disturbed ESDAC, Canada,
Palouse and Virgin Islands tables, resolve the exact same management assets
through their current names. Use `Thinning_40_93.man`, `Thinning_40_90.man`,
`Thinning_40_85.man` and `Thinning_40_75.man` in `UnDisturbed/`,
respectively. Existing class identifiers, names, Disturbed classifications
and model parameters retain their meaning. These four assets moved with
byte identity in revision `fc183b0a6`. Keep the exact-name routing and
scenario choices for the currently separate ESDAC tables under independent
audit and ratification.

### Existing generic thinning classification

Retain the exact `thinning`
classification for the historical catalog rows that already use it.
Management summary validation must accept this existing default Disturbed
soil-lookup key. Keep each row's management file and treatment type,
including the distinct 96% cover scenario. Continue resolving the soil
parameters from the selected run lookup. The default lookup has one generic
thinning row for each of its four supported textures. Do not infer a
percentage-specific soil scenario from a management filename.

### Uploaded raster compatibility

The Disturbed table check is implemented. Aligned-raster compatibility,
admitted worker publication and batch replay remain pending. Use the normal upload authorization,
raster validation, and selected base or run-owned override map. For a
delineated run, validate a private new or reused raw raster and its aligned
TIFF against the current watershed. Use the same classification and NoData
flags as the land-use builder. Require complete coverage of the authoritative abstracted hillslope IDs and,
in Multiple OFE, all modeled segment IDs. Raster pixels alone cannot define
the expected set. Resolve every
resulting management code and the effective buffer key, including a retained
buffer when the request omits it. In Disturbed projects require string
`DisturbedClass` metadata on every table row consulted by the lookup and
all nine required wildfire destinations, even without an SBS map. Preserve
the meaning of intentional blank strings and ordered first-match grouping.

Return HTTP 400 with `error.code="incompatible_landuse_mapping"` for an
incompatible source and map. Show the
selected map, safe source basename and offending codes or missing metadata,
with instructions to select a compatible map or replace the raster.
At build-request entry, the prior accepted source, aligned raster, mode,
map, buffer, burn settings, build timestamps, and usable outputs are the
baseline. A rejection, active-job conflict or definite enqueue failure
leaves them unchanged. Independent mode and dataset controls still persist
their own selections.

Keep asynchronous attempts private to the run and bind them to the tracked
job. The route validates before acceptance and defers active file and
selection changes to the worker. A worker verifies the current admitted job,
raw and aligned raster identities, ordered effective mapping, effective
build settings, and watershed geometry before consuming them. Watershed
identity includes SUBWTA and, in Multiple OFE, the OFE map and modeled
segment definitions. A stale or drifted attempt fails before applying
settings or writing managed files. Hold the existing supported watershed and land-use leases in their
documented order through actual consumption and publication, or consume
immutable verified dependencies through that boundary. A one-time path
recheck followed by unprotected reads does not establish identity. A previous VRT build must switch to the validated TIFF and
consistent raster state together. A fresh Multiple OFE build resolves
management from the current uploaded source before burn classification and
synthesis, even where numeric codes match prior summaries.

Keep the legacy RQ worker arguments valid. Keep authenticated batch
configuration usable before delineation. Validate the table at admission
there and run the same full raster compatibility check when the batch
workflow has all watershed inputs, before its active build. Each batch leaf
aligns retained raw bytes to its own delineation. Where all watershed
dependencies are already available, batch configuration can validate
synchronously. Existing direct and legacy queued builds with a usable
prealigned input can build without a raw receipt. This legacy behavior
does not apply to a newly admitted raster or pending batch association. Job-bound evidence and private attempts follow the
existing climate upload receipt and archive visibility conventions.

Apply the [raster driver and upload contract](upload-endpoint-contract.md#raster-content-and-driver-boundary),
[RQ response envelope](rq-response-contract.md#job-submission-responses),
[controller state contract](rq-controller-state-contract.md#uploaded-landuse-attempts),
and [NoDb derived byte verification](nodb-persistence-concurrency-contract.md#derived-input-byte-verification-implemented).
