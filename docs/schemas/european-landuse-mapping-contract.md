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
