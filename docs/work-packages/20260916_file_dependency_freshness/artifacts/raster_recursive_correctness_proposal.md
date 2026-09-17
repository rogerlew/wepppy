# Recursive raster discovery: independent correctness proposal

Reviewer: `freshness_correctness`, 2026-09-17. Discovery/probes only; no production
or test changes. **A bounded recursive implementation is feasible. A universal
GDAL dependency-completeness claim is not supported.** This is input to the next
contract checkpoint, not implementation approval or package acceptance.

## Confirmed constraints and retained evidence

`raster_recursive_correctness_probe.py` creates disposable datasets using the
installed GDAL and invokes the actual `wepppyo3` median reader. Revision 6 JSON/
log retains the completed characterization; earlier logs remain, including the
initial uncaught native error. The graph routine is deliberately diagnostic:
ZIP backing associations are fixture-owned facts, not a proposed URI parser;
the link-following control assumes its known acyclic fixture.

| Case | Actual result | Required treatment |
| --- | --- | --- |
| Two-level VRT | Native median 25→75 after restored-time leaf rewrite; recursive discovery sees the changed leaf omitted by the root file list | Follow dataset edges recursively, not just one `GetFileList()` |
| External TIFF mask | Addition, changed mask bytes and removal each change the observed graph | Rediscover optional members on reuse; cached root metadata cannot establish membership |
| PAM sidecar | Read-only TIFF metadata update creates a reported `.aux.xml` leaf | Hash reported ordinary auxiliary files even if they are not raster datasets |
| TIFF world file | `.tfw` changes origin 500000→600000 with unchanged TIFF; discovery includes the world file | Georeferencing participates in identity, not just pixel storage |
| Local Zarr | Native median 25→75; native list names the store and `.zarray`, omitting chunk leaves | Enumerate the full physical store and its membership |
| Symlinked Zarr array | Native median 75→33 while `GetFileList` plus `Path.rglob` hashes remain identical | Follow readable directory links; the link-following control detects the change |
| Plain/braced local ZIP | Both `/vsizip/path/archive.zip/...` and `/vsizip/{path/archive.zip}/...` work natively with nested VRTs | Preserve accepted native path forms and hash the actual local backing container |
| VRT inside ZIP references outside file | Native median 75→99 while the ZIP hash stays unchanged | Container hashing must accompany recursive virtual-child traversal; it cannot replace traversal |
| Invalid raster bytes | Installed median reader raises `pyo3_runtime.PanicException` | Preserve the existing reader/error boundary; discovery must not silently substitute another engine or generic error |

`derived_gdal_closure_probe.*`, `derived_gdal_security_probe*`,
`derived_main_security_probe*` and `c03_c05_c06_native_probe.*` retain the earlier
actual failures. The latter proves C05 feature geometry changes from an external
mask while the old geometry cache remains stale; a list-only probe is not the
sole evidence that sidecars matter to a supported consumer.

The installed Python GDAL is 3.10.3; rasterio embeds GDAL 3.8.4. Actual rasterio
reads of nested VRT, the world-file TIFF, symlinked Zarr and ZIP VRT succeed and
report the same relevant immediate members in these fixtures. This is useful
parity evidence, not an assertion that every driver/option behaves identically.
`raster_native_linkage.txt` records the native median extension's system
`libgdal.so.36` linkage. Reader environment/version belongs in review evidence.

GDAL describes `GetFileList()` as files believed to belong to the dataset, not a
complete transitive read-set guarantee. An empty list is also a meaningful native
state. Do not turn successful recursion into an all-driver theorem.
[GDAL Dataset API](https://gdal.org/en/stable/doxygen/classGDALDataset.html).

## Smallest shared primitive

Use existing GDAL for discovery and the existing verified ordinary-file digest
for content. No Python raster decoder, external dependency, alternate scanner,
new aggregate cache or native algorithm replacement is justified by this work.

1. The caller identifies an actual raster input and retains its existing path,
   reader options and authority. Traverse reported child datasets with stable
   logical edge identities and visited physical/dataset identities. Hash ordinary
   reported leaves that are not datasets; they are not discovery failures.
2. Enumerate directory-backed storage fully. Record membership and directory-link
   edges; follow readable links as the existing native reader does, while visited
   identities prevent cycles. Retain the distinction between an alias and an
   omitted subtree. Do not add run-root restrictions that the caller never had.
3. For a supported local virtual archive form, observe the physical backing
   container with the ordinary digest helper and traverse virtual child datasets.
   Deduplicate a shared backing container across members. Native URI parsing must
   preserve accepted braced/plain forms; the probe's prefix map is not sufficient
   implementation. No blanket `/vsi` rejection is compatible with the evidence.
4. Return deterministic members/edges and content identity, plus explicit
   discovery coverage. Retain selected/resolved paths and errors as diagnostics.
   Reevaluate membership on reuse; a settled digest cache only avoids rereading
   file bytes, not native discovery or directory enumeration.
5. Guard discovery observations against changed files/membership, then repeat
   the complete observation after native materialization before reuse/publication.
   Never label an old result with a later graph. Preserve caller-specific strict
   finalization checks; C01's uncached verification remains distinct from a
   numerical-cache optimization. This does not promise arbitrary producer
   transaction isolation, consistent with the existing point-in-time contract.

The exact coherence/error/publication API and digest marker schema still require
the next checkpoint. Mixed observation races, changed membership during traversal,
cycles and denied links need deterministic implementation regressions.

## Compatibility policy for uncovered drivers and virtual paths

Limit **verified reuse coverage**, not accepted native input formats. An ordinary
extension allowlist is unsuitable: VRTs can use arbitrary names, raster support
belongs to the installed reader, and native-readable directory/ZIP inputs are
already demonstrated. Generic native discovery is preferable to guessing from
suffixes, but cannot certify unsupported backing relationships merely because
an initial open succeeds.

A nonlocal/other VSI node or unavailable native dependency inventory should be
an explicit unverified observation with a reason. For cache consumers, that means
no numerical-cache reuse based on incomplete evidence; run the existing native
operation and preserve its existing errors. Do not invent remote validators,
downloaders, path restrictions or fallback scanners. Missing, denied or malformed
dependencies are not interchangeable with unsupported discovery and cannot
authorize a historical/current cache hit.

C01 needs a separate honest disposition: bypassing a numerical cache does not
prove an outside-lock result's inputs stayed current at finalization. Retain the
uncovered case as OPEN unless an actual supported workload and an owned native
extension establish its dependency proof. Do not claim complete C01/package
closure by silently retaining main-file-only protection for that case. Any newly
rejected previously accepted input would require a behavioral checkpoint.

## Consumer binding precision

| Consumer | Relevant existing boundary |
| --- | --- |
| C01 | `mods/rap/rap_ts_build._inputs`: selected yearly raster, subwta and MOFE inputs. `core/climate_observed_build._spatial_inputs` signs a CLI text file; do not send it through raster discovery |
| C02 | `features_export.dependency_tracker` signs a mixed catalog set. Maintained materializers currently read Parquet and vector geometry; catalog `subwta_shp`/`channels_shp` properties return JSON/GeoJSON for all Watershed backends. No direct raster binding was found in this bounded trace. Establish the actual indirect consumer before claiming this raster primitive closes C02; vector/directory closure is separate |
| C03 | `Landuse._build_mofe_pair_count_signature` needs both native pair-count raster closures and its existing MOFE semantic structure digest |
| C04 | `_summary_cache_key/_summarize_sbs_raster` needs the raster closure before cached native summary reuse, with post-summary recheck. Native calls also receive the bundled SBS color-map JSON; that static code/config input is outside raster discovery, with no runtime writer defect established here |
| C05 | `GenevaHruMapGeometryService`: rasterio masked raster closure plus ordinary legend bytes; preserve prior GeoJSON on failed work and bind the accepted feature generation |
| C06 | `GenevaHsgAssignmentService`: source raster closure, bound-grid closure, selected source path and alignment settings; bind the actual accepted target generation |

## Actual cost and remaining gates

`raster_recursive_correctness_benchmark.*` reads actual named NFS inputs and
verifies all observed bytes unchanged. It performs no model work or writes to
named runs. OS caches were not dropped. Twelve passes per set separate cold,
normal one-second admission and ten settled observations. The initial admission
wait occurs with immutable sources and does not conceal a changed-byte test.

| Input set | Bytes / files | Cold total | Settled total mean | Settled discovery mean |
| --- | ---: | ---: | ---: | ---: |
| Original SBS | 599,196 / 1 | 4.87 ms | 2.10 ms | 1.87 ms |
| Cropped SBS | 424,964 / 1 | 4.57 ms | 2.09 ms | 1.85 ms |
| DEM with auxiliary file | 26,411,260 / 2 | 99.83 ms | 3.67 ms | 3.21 ms |
| Cropped RAP, 39 years | 564,058 / 39 | 89.78 ms | 77.51 ms | 68.49 ms |

Every settled observation performs zero digest computations. These costs support
always rediscovering this measured local graph, rather than adding an aggregate
cache now. They are not end-to-end consumer or lock-occupancy acceptance, and the
RAP set is explicitly a small cropped set.

The actual GDAL-created 24×24 Zarr with 1×1 chunks has 580 files totaling 1,269
bytes. All three immutable passes compute all 580 hashes because sequential
traversal exceeds the existing 512-entry observation cache (about 151–165 ms).
A controlled monotonic clock separates this capacity effect from the admission
interval. Retain the current cache bound; this synthetic mechanism is an
acceptance risk, not evidence that a real supported store misses an agreed
budget. Measure a representative store before proposing a new aggregate cache.

Required next evidence: actual consumer outputs and prior-artifact retention;
fresh membership and link-cycle/error handling; reader-version parity; coherent
pre/post observations; source/output generation binding; representative whole-set
lock time; and real directory/chunk/archive workloads. No remote network probe,
universal driver certification, deployment or package closure is claimed.
