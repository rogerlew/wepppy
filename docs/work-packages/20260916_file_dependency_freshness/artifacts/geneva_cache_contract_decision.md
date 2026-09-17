# C05/C06 Geneva derived-cache checkpoint

Status: draft, implementation pending. Independent correctness/security review
required before ancestor commit; performance proposal derives from actual
copied native workload, not a format-wide guarantee.

Confirmed existing failures: restored-time HRU/mask/legend edits retain old
geometry; changed burn bytes, older alternate source and changed bound transform
retain old alignment. Owner:`mods/geneva/specification.md`, sections8.1/12.4.6
and new derived-freshness subsection. Preserve availability envelopes, public
filenames, feature schema, native vectorization/nearest-neighbor algorithms and
explicit override pass-through. No scientific parameter/default is changed.

## Compatibility and data propagation

Add embedded version1 provenance to generated GeoJSON foreign metadata and GTiff
metadata. No public column/key removal or NoDb migration. Legacy or invalid proof
is a conservative normal rebuild; historical geometry requires its sources as
before. Prove actual changed geometries, legends, pixel arrays and target profile,
then their normal query/kernel request consumption. Use actual native readers,
not mocked GDAL conversion. Archive restore preserves attempts; relocated source
selection may conservatively rebuild instead of fabricating portable history.

Observe HRU local raster closure+legend bytes. Observe burn local source closure
and actual bound profile (including its selected/resolved path) as numerical
identity, excluding driver/count/compress/nodata/dtype that the stacker overrides.
Keep all other profile fields passed through to native output creation. Guard native reads with before/after observations. Bound pixels/mask
are not alignment inputs; do not place their hashes into accepted numerical
identity. Unverified source layouts bypass reuse and keep the existing native
operation; do not expand the bounded observer into recursive VRT/Zarr transport.
The existing stacker forces GTiff output for every bound input driver. Preserve
single-TIFF candidate publication even for unverified native-successful inputs,
but do not attach verified reuse proof. No new format rejection is introduced.

For supported single-file outputs, write unique visible attempt candidates,
retain status and partials, preserve target write access/mode, validate source
selection/bytes/profile before atomic replacement. GeoJSON proof and features
are one publication; TIFF proof and pixels are one publication. Failed native or
validation work preserves prior accepted output. Read a cached GeoJSON once,
validate its embedded proof against before/after dependencies, and return that
same payload. No generic ArtifactIO behavior changes for other Geneva artifacts.

## Evidence and proposed gates

Independent copied990-feature project: full geometry miss884ms/hit16.15ms;
composed guarded hit24.03ms settled/25.60ms helper-cold and miss940ms. Alignment
miss29.35ms/hit0.91ms; composed hit14.19/14.32ms and miss34.19ms. Six named files
were audited unchanged; native operations only touched copies. Ratify full
geometry hit40/75ms settled/cold-or-actual-evicted and miss-added100ms; alignment
hit25/40ms and miss-added35ms. Repeat actual final implementation, real512-entry
pressure, native parity, generated artifact proof and permissions. Original
baseline/composition artifacts remain evidence, not final acceptance.

## Review refinements before checkpoint

Actual old external-mask test fails main-only publication: native direct overwrite
clears the mask, candidate+replace retains its all-zero bytes. Therefore coherent
atomic alignment publication is bounded to clean canonical target auxiliaries;
old auxiliary-bearing targets retain original uncached native overwrite semantics
with explicit weaker failure guarantee and retained attempt evidence. No strong
proof is stamped in that branch. Original failing probe remains retained.

Pin metadata names/shape in canonical spec, private candidates from creation,
existing read/write/mode/symlink authority, restricted target-tag discovery,
complete-set read guards, in-boundary auto-selection recheck, typed409 changed
source errors, and replace as the irrevocable commit point. Post-commit status
failure logs without misreporting rejected publication. These are required
implementation/test boundaries, not optional documentation notes.

An unverified bound returns uncached before added profile inspection. Final
publication acceptance includes supported service UID/GID/group as well as mode;
replacing an existing inode cannot be assumed ownership-equivalent from mode
alone. No new ownership restriction is authorized without a confirmed need.

The confirmed C03/C04 old→new(native read)→old race requires retaining physical
versions/context from the same verified acquisition across native work, separate
from numerical identity. Geneva complete-set guards must span materialization,
not merely each observation. Create attempt directories before acquisition so
owned setup does not itself invalidate the source-parent directory guard.
