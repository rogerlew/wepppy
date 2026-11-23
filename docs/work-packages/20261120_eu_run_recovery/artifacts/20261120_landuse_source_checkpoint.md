# CORINE provider mapping checkpoint

Starting revision `178bfc90c`. The operator requested land-cover source isolation and an ESDAC management
and mapping audit as part of the forest replay. This checkpoint covers
provider mapping resolution. Incompatible user-defined raster admission and
management scenario changes remain separate checkpoints. The other catalog
corrections have an independent audit and generated-artifact milestone.

The archived `studded-stranglehold` job persisted CORINE classes 12, 20,
23, 24 and 25 with the upload's stale `esdac` mapping. Direct management
resolution confirms `eu-disturbed` class 25 is Mixed forest, with
`UnDisturbed/Old_Forest.man`, while plain ESDAC has no key 25.
The [European land-cover mapping contract](../../../schemas/european-landuse-mapping-contract.md) binds the built-in
map to the provider. It keeps the existing stored upload selection and
run-owned custom path contract. Keep the previously selected mapping visible in
the upload selector and preserve treatment operations that explicitly use
their selected source map. A compatible configured map file means a declared
path for the same CORINE dataset in the effective project configuration. Stored
built-in values alone are ambiguous. No persisted schema changes are needed.

Cover current and legacy saved mode/mapping combinations, including a
same-mode retry, all CORINE years and both configured spellings, related
non-CORINE gridded projects, user-defined raster re-entry, a compatible
run-owned override and old nonempty and empty assignments. Verify the
effective class, generated management and Parquet from actual CORINE
inputs. The original user-uploaded `LandCover25m.tif` is unavailable for
exact replay at this time.

## Deferred upload admission findings

The current set-mode and dataset UI routes persist selection independently
of build admission. A future contract must distinguish selected inputs from
the last applied artifacts before specifying preservation. In Disturbed,
the current lookup requires a string on every effective map row and all nine
forest, shrub and grass severity destinations even without an SBS raster.
Preflight must also use the exact hillslope and MOFE assignment paths,
including codes contributed only by an OFE. Bind accepted clipped raster
and effective map identities across the route and RQ job before claiming
that preflight preserves the previous applied artifacts across retries or
concurrent changes.

## Independent review disposition

Both reviewers cleared the narrowed provider checkpoint after checking
archive compatibility, the run-owned override, source identity and
effective-map callers. Store no new fields. Keep the existing mapping
accessor for input selectors and explicit treatment selection. Apply
provider precedence to the land-use build, effective-map snapshot, and
Disturbed consumers. Match a configured map file to the same canonical
dataset, including its alias. Current gridded cleanup can remove the
previous raw upload while retaining its selection. An arbitrary custom
map path under the cleanup root needs the applicable override retention
rules and its own regression test.

## Candidate readback

On a private copy of `studded-stranglehold`, the retained CORINE raster
contained every archived dominant code. Existing management generation used
those 58 assignments and the archived hillslope and channel Parquet instead
of extracting new assignments. The normal writer produced 58 land-use Parquet
rows. Sixteen hillslopes used management key 25, Mixed forest, with
`Old_Forest.man`. The constructor used the saved project configuration to
initialize the otherwise unretained WEPP metadata, and a companion archived
Climate state satisfied its initialization dependency. The original ESDAC
selector value stayed available. No original run was changed.

Review found shared numeric keys in MOFE management generation. The candidate
resolves base CORINE templates before classifying fire or composing management.
A regression fixture starts with the previous map's class 23 and verifies
that the segment writer is passed the CORINE Broad-leaved forest template.
Additional focused cases cover both provider spellings, every exposed year,
requested buffer validation, and retaining case-sensitive override paths.
An explicit treatment raster keeps its selected map for treatment templates,
including 65% thinning from the Disturbed map. Untreated base classes retain
their CORINE source map. Focused validation passed 140 cases. The deployed workflow and exact original
user upload replay remain open.
