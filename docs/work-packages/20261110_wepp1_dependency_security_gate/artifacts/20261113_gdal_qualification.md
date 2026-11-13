# GDAL and Rasterio remediation qualification

Status: private qualification and packaging drafts; not integrated or activated.
Deployment resume remains deferred. No M4 closure or risk acceptance.

## System GDAL

Debian GDAL 3.10.3 is retained with six upstream security backports and the
existing Debian repack patch. All seven changed files have exact original and
patched hashes. The first trial revealed two build defects: a zero-fuzz hunk
landed in a repeated block in the wrong function, and CMake ignored CPPFLAGS,
omitting FORTIFY. Correct function placement and explicit C/CXX flags resolve
both. The consolidated integration patch rejects relocated hunks and validates
every resulting source hash.

The raw build library also contained a trailing-empty RUNPATH. Root-local CMake
installation removes the build path and strips the staged library. The staged
artifact SHA-256 is
`67d92bc35ff7fc88779e5b7863033a3103ad36b000cc8ae0742386f0cd3a12d4`.
All 10,598 named dynamic-symbol contracts match Debian, including GNU_UNIQUE
objects, imported symbol versions and object sizes. NEEDED, SONAME, flags,
non-executable stack and RELRO match; RPATH/RUNPATH are absent.

All six upstream hostile HDF4 fixtures crash the original library through both
raster and multidimensional reads. All twelve probes complete with the staged
repair. The 221 driver names, valid Deflate64 bytes, GeoTIFF/NetCDF/HDF4 array
values and reprojection values/metadata match the original. Deflate64 is a valid
control, not a vulnerability-specific negative reproducer. Malformed fixtures
run in bounded private processes; normal controls run as UID 1002/GID 130.

Independent closure addendum SHA-256:
`7eabea4f0f29f3fd48ce61dc0b6da1d11ac2493e94eb751ed57ff0eb25fcbeb5`.
Private evidence: `gdal-repair-input-review-20261112/`, including
`correctness-source-review-20261112/staged-closure/`.

The private integration draft rebuilds coherent libgdal36/libgdal-dev packages
with version suffix +wepp1, retains original headers/development links and
replaces only the shared library plus provenance. It restores build-only package
changes and APT manual/automatic selections. Actual helper execution, installed
package-content comparison and final-image acceptance remain required.

## Rasterio alternatives and selected private direction

The official Rasterio 1.4.4 wheel fails with the current PROJ_LIB setting because
its bundled PROJ expects a newer coordinate database. A source build against
system GDAL preserves that setting and the tested raster values, but introduces
a confirmed shared-library isolation problem: a main-thread warp temporarily
sets GDAL_MEM_ENABLE_OPEN globally. A concurrent thread successfully opens a
synthetic owned memory buffer during that window, despite rejection before and
after the operation. This candidate is not accepted.

The smaller private draft retains Rasterio 1.3.10 and wraps only its internal
NumPy-buffer constructor with thread-local MEM access. It copies the exact prior
TLS value, including absence, before mutation and restores it in finally.
Public Env behavior, warp code and parameterization remain unchanged. This
avoids introducing the newer geolocation-array API and its cross-thread reopen
requirements. Source review finds only the intended three changed files; runtime
acceptance remains open. No global flag override or silent fallback is allowed.

Required proof includes exact TLS/global-state combinations, nested and exception
cleanup, a deterministic concurrent-thread check, ordinary GCP/RPC and threaded
warps, real owned raster consumers and artifact/performance comparisons. Final
linkage must use the patched system library without the old private GDAL copy.
The system-linked trials lose ARG; no owned ARG consumer was found, but a bounded
source search is not proof about all operator workflows. Preserve any confirmed
established workflow or obtain explicit approval for its change. Added registered
driver names also include vector drivers; classify actual raster reachability.

Private evidence: `rasterio-system-link-trial-20261112/`. Security design packet
SHA-256 `2e3ce6002b58d2267a6cbaaa8ed86adfec55030584427d1a0324e7fdc8f10f0b`;
1.3.10 source-design addendum
`5eeba26dbbc93ecbc40627e5e0954624a5d135dc525d1904070e817dfed65d63`.
The confirmed Medium finding on the rejected 1.4.4 trial remains open until the
alternative's runtime isolation is demonstrated and its supersession recorded.
