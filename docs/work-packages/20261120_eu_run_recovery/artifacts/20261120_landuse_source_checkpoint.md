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
