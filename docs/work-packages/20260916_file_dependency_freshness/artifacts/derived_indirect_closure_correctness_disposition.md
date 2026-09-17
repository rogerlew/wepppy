# C01 indirect closure: correctness disposition and full RAP evidence

**Recommendation: retain C01 indirect native dependencies as a justified
unresolved finding, explicitly unfixed.** The bounded main-file correction is
implemented; its missing complete-set/held-lock measurement is now supplied for
one actual small cropped RAP workflow. Neither that pass nor the C03/C04 cache
observer proves generic RAP raster closure. No production/test edits, new input
restriction, new scanner or native replacement is proposed here.

## Actual consumer scope

`rap_ts_build._inputs(analysis=True)` captures configured years, extent/cellsize,
manager provenance, six bands, subwta, optional MOFE and each selected annual
raster. Each manager path is resolved under the run RAP directory and signed
with `_derived_build.file_signature`. `analyze` passes those captured paths to
the owned native median reader outside the lock, then reacquires the complete
snapshot under `finalize` before parquet/NoDb publication. Required main-file
bytes are freshly hashed once at collection and once at finalization.

RAP's native functions read key arrays, selected parameter-band arrays and
NoData, then zip their cells for aggregation. Owned source is
`wepppyo3/raster_characteristics/src/lib.rs:471` and `:568`, using
`wepppyo3/raster/src/raster.rs:344`. The dataset reader also obtains raster size,
geotransform and projection. It does not apply GDAL external masks in these
median functions. Thus a sidecar that affects Geneva's masked geometry is not
automatically a proven RAP numerical dependency; native effects must be traced.

PRISM has a different binding: `climate_observed_build._spatial_inputs` signs
the source CLI **text file**, plus copied coordinates/settings. Its ppt/tmin/
tmax TIFFs are freshly retrieved into each unique `.prism-build-*` stage by
`_retrieve_prism_revision_tiles`; they are not reused persistent raster inputs
from a catalog. No retained evidence establishes a supported ordinary writer
changing those owned private intermediates concurrently. Sending the CLI text
through a raster observer would be wrong. The restored-time CLI defect is the
already fixed main-file case, not an outstanding recursive-raster case.

Direct VSI roots require a distinction: the low-level native probes establish
`/vsizip`/`/vsimem` capability, but RAP's wrapper already requires a local stat-
able path contained under `rap_dir`. This review does not claim the wrapper
currently accepts an arbitrary direct VSI root. Local VRT roots can still
reference virtual/archive/nonlocal children; local directory-backed stores are
already demonstrated valid by the actual directory regression.

## What remains confirmed and unfixed

- `derived_gdal_closure_probe.py/.json` shows a valid local
  `outer.vrt -> inner.vrt -> base.tif`: the flat list omits the leaf, all listed
  signatures stay equal after restored-time leaf edits, but the actual owned
  median changes from 3 to 7.
- `raster_recursive_correctness_probe_revision6.json/.log` independently shows
  nested VRT and local Zarr medians changing from 25 to 75. Zarr's native list
  omits chunk leaves; directory metadata is not their byte identity. A linked
  array also changes output while naive non-following directory enumeration
  remains unchanged.
- The same retained native probes show that a VRT inside a local ZIP can read a
  file outside the archive; hashing only the container misses the changed data.
- Security's `raster_discovery_security_probe_revision2/3/4` evidence shows that
  eager VRT and even TIFF auxiliary inventory can open nonlocal children before
  reporting them. Generic recursive `Open/GetFileList` would add remote reads
  during freshness observation unless a separately reviewed authority mechanism
  constrains it. A driver-name gate alone was disproved.

These are native counterexamples, not a claim that the maintained RAP download
writer produces VRT/Zarr today. That writer uses `gdalwarp` to local annual TIFFs;
the measured real run below consists of ordinary local GTiffs. The finalizer's
current broader accepted local-native inputs nevertheless lack complete
indirect-byte verification. Keep the limitation visible, rather than inferring
universal safety from the usual producer.

## Smallest alternatives and why no new runtime fix is recommended now

The existing GTiff/AAIGrid observer can classify a bounded graph for numerical
cache reuse. An initially unverified cache input can execute natively without
reuse. **That remedy is not a RAP finalization proof:** RAP already computes
natively outside the lock, and rerunning its computation does not prove the
outside-lock result stayed current at publication. Returning an unverified
sentinel that compares equal would conceal the unresolved case.

A reviewed future RAP-only extension could reuse the bounded observer's known
membership, while freshly hashing every member with uncached transaction
semantics and preserving path/settings/strict publication checks. It would need
an explicit unverified disposition and full-set timing. Such a GTiff-only
extension would still not repair the retained nested-VRT, directory-store and
archive-child counterexamples. Adding it now as “C01 closure” would make a false
completion claim, and adding a generic URI/XML/store scanner would exceed the
smallest-fix discipline without complete authority/reader parity evidence.

Blanket rejection of previously accepted local VRT/directory inputs narrows
working behavior. Holding the NoDb lock around all native work does not serialize
arbitrary filesystem writers and increases lock residence without proving
closure. An ordinary digest cache cannot supply omitted dependency membership;
C01 explicitly requires uncached transaction hashes. No new dependency, cache,
service, remote validator or ownership/locking protocol is justified by the
evidence. A future owned-native read-set/snapshot evaluation is appropriate if
complete proof for those inputs becomes an authorized requirement.

This recommendation follows the canonical NoDb contract's “Derived input byte
verification” clauses: the amendment covers only the existing main-path set,
directory stores retain explicit absent digests, no new format restriction is
authorized, transaction hashes are uncached, and existing atomic-producer/
locking assumptions remain. The package allows explicit justified-unresolved
inventory entries. Parent closeout must amend the earlier blanket C01 blocker
wording if adopting this recommendation, and must state that indirect native
changes can still evade finalization checks. **Unresolved is not safe, fixed or
runtime-accepted.** Existing strict finalizers/rollback guards remain unchanged.

## Actual complete-set and held-lock evidence

`derived_rap_complete_set_probe.py`, its JSON and `_initial.log` retain an actual
successful workflow under UID 1000/GID 993. Large inputs, module snapshots,
generated output and benchmark manifest are preserved at
`/wc1/batch/qa-derived-rap-daa5702c3380/`. All 46 named input files were accessed
only by ordinary reads/copy; final version/hash checks confirm them unchanged.
An audit hook rejects named-root mutation. Controller state was rebased only in
the disposable copy; actual native arguments were checked to remain there.

| Measured boundary | Actual result |
| --- | --- |
| Selection | 1986–2024, 39 annual rasters, all six RAP bands, single OFE |
| Complete raster set | 40 files: annual rasters plus WBT subwta, 576,244 bytes |
| Native layout | 53 × 52 cells; annual files six-band GTiff, key one-band GTiff; each copied native file list contains only its main path |
| Native work | 234 real `identify_median_single_raster_key` calls; observed native path union exactly the 40 signed inputs |
| Signature work | Exactly 80 uncached calls: 40 collection and 40 while finalization lock is held |
| Finalizer hash work | 0.0533 s, below the retained 10-s hash-work budget |
| Complete finalizer input validation | 0.0765 s |
| Actual lock residence | 3.9679 s, including durable hydration, validation, publication and persistence |
| Whole actual analysis | 22.0901 s |
| Published output | 1,638 rows, exactly equal to the copied prior parquet after key sorting |

The probe uses actual NoDb hydration, Redis lock/unlock, thread-pool native work,
parquet publication and durable controller persistence. Wrappers only record
elapsed time, paths and calls; they do not replace locks, readers, numerical
results or finalization. It is stronger than the earlier 39-file hash-only
sample, which omitted the key raster and took no lock.

This is one complete **small cropped single-OFE** workflow on filesystem-warm
copies, not a mean/percentile, storage-cold, large-watershed, MOFE, recursive-
format or HTTP/RQ acceptance claim. It establishes no universal file-access
trace beyond the observed native arguments and reported immediate lists.
Larger operational sets and any later closure implementation still require
their own budget and lock evidence. PRISM's restarted build/archive and all
package runtime gates are separate. The original script/log is named “initial”
because it is the first retained run; it passed without fixture correction.
