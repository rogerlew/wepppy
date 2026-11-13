# GDAL and Rasterio remediation qualification

Status: custom native implementation deferred after operator scope concern.
Clean build stopped with exit 130; no accepted final native image or activation.
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
The confirmed Medium finding on the rejected 1.4.4 trial is closed by
supersession for the exact 1.3.10 TLS trial described below. The rejected 1.4.4
implementation remains unsuitable without its own repair.

## Compiled TLS and package qualification (2026-11-13 UTC)

Private trial image
`0ef9fdc408506c8fa677c6ade83ef0092b9b7141149c61e4614967d1b712a2c1`
contains the qualified staged GDAL and compiled three-file Rasterio 1.3.10 patch.
All nine global/TLS state combinations pass, including nested/exception cleanup,
restoration of absent TLS and deterministic child-thread raw-memory denial while
the parent scope is held open. A real two-thread warp exposes no global access
window. Installed extension hashes match the reviewed wheel; only the repaired
system GDAL is mapped. PROJ_LIB and GDAL_DATA remain unchanged. Eight generated
array hashes and metadata match the baseline. All 53 selected WEPPpy consumer
tests pass in 64.78 seconds.

Independent security closure addendum SHA-256:
`aad8c0733019d0de340d8dd09a0be87249b857196edabcf1d7eec17ddda7f6d0`.
This closes F6-NATIVE-SEC-01 by supersession only for this exact private trial;
it is not final-image acceptance or risk acceptance. Readback and logs live in
`rasterio-system-link-trial-20261112/tls-runtime/`.

Upstream warp/GCP/RPC/features/VRT selection: 315 passed, two skipped, seven
expected failures, two unexpected passes, one deselected, one failed. The failure
expects two HTTP retry log messages but receives three; the expected warp error
still occurs. The same count mismatch reproduces on the independent Rasterio
1.4.4/system-GDAL trial. Retain this compatibility difference explicitly; do not
claim an all-green upstream suite. Initial harness failures (missing optional
boto3, obsolete fixture-mark warning and local hostname resolution) are retained.
Optional test dependencies are separate from runtime site-packages and tests
have no external network. Registered driver delta is 67 added names and ARG
removed; added names include vector drivers.

Repackaging the staged GDAL installs only the intended two package-version
changes. Runtime payload comparison permits only the repaired shared library
and added provenance; all 81 development-package members remain identical.
Receipts are under `gdal-repair-input-review-20261112/package-trial/`.
Full build-helper execution initially found absent APT indices in the final
image; explicit signed-metadata refresh now precedes exact package resolution.
The corrected full helper and owned Rasterio wheel helper are being qualified.
Candidate helper sources/tests/docs are staged; Docker wiring, final rebuild,
installed-byte acceptance and complete gates remain open.

## Candidate implementation checkpoint

The detached candidate now wires both helpers into common/development builds.
The owned Rasterio wheel is installed in the requirements layer, then staging
and APT indices are removed. Shared host requirements/installers stay unchanged.
Private owned-wheel image `d6798f60b22a` passes 57 focused tests, including four
installed-provenance/import-order/isolation cases. All 71 wheel RECORD entries
validate. The added GDAL regression module passes 13 cases (12 bounded malformed
HDF4 reads plus valid Deflate64 seek/read control). The wheel helper subsequently
adds compiler identity/config/environment provenance; final-image validation must
exercise that latest source. Full GDAL helper execution now passes, including exact unrelated-package and
APT-selection restoration. The installed shared-library hash is
`9571b83b5c12dbba8202da893dc4af8ff8c46316fb42e7a218a9cd6b1a97a297`;
this independently built artifact differs from the earlier staged prototype,
so final-image runtime probes remain required. Receipts and both attempt logs
are retained under `gdal-repair-input-review-20261112/full-helper-trial/`.

Independent correctness source review has no remaining Medium/High findings;
packet SHA-256
`6fe6e854acf02cb9752e64aeee61e9b18a4e225333acf7663120693223459cf2`.
The review is bounded source/artifact evidence, not release acceptance.

The review also found the valid Deflate64 archive was excluded by the root ZIP
ignore rule. The exact fixture is explicitly force-added; the ignore rule is
unchanged. Closure addendum SHA-256:
`a83c0a6a3753623a57e6d5071684a1c75ce0bcf47bbf394a766ab9f46c106215`.

Owned `raster_stacker` comparison on an 8192-by-8192 categorical raster matched
to a 4096-by-4096 grid preserves exact arrays/metadata across three runs each.
Median operation time is 0.907 seconds baseline versus 0.958 seconds candidate;
peak process RSS is 1,733,460 versus 1,720,808 KiB. Output I/O is 53,688 blocks
for both; input I/O is zero versus 1,640 blocks (cache conditions differ).
This bounded synthetic workload is consumer evidence, not a general performance
guarantee. Smaller 2048-grid receipts are retained separately. Private evidence:
`rasterio-system-link-trial-20261112/consumer-benchmark8192/comparison.json`.

## Frozen clean-build candidate

Implementation commit `967a085f4` remains isolated from the live main checkout.
The clean common-image build was stopped with the retained immutable base/vendor
inputs under `gdal-rasterio-batch-20261113/`. Node 20 lint and all 1,079 frontend
tests pass for that source. Scoped broad-exception enforcement covers all six
new Python files and passes with zero broad handlers. Observe-only quality
telemetry reports one yellow 104-line build function; its sequential validation,
compilation and wheel packaging keep fail-closed steps in execution order.

Independent security implementation packet SHA-256:
`826d89fbe9a000501d914a172350bc66b1b77265f932d673c0d89d7823312c53`.
The Low linkage-check gap is closed: parse exact NEEDED names, reject every other
GDAL name and require both core extensions to link libgdal.so.36. No open
Medium/High source findings. Final build must exercise the latest guard and
compiler provenance; earlier wheel tests are not relabeled as that proof.

## Scope correction after operator concern

The operator questioned both compiling GDAL and the expansion into a rabbit
hole. The agent stopped the clean build at GDAL compilation and retained its
exit-130 receipt. No compilation remains active. Custom native implementation
`967a085f4` is deferred; Python candidate `64cc736c2` and image `af7643725c95`
remain the separate completed-upgrade checkpoint (full Python gate still open).

The reason for compiling was to apply upstream fixes while retaining the
existing GDAL ABI and scientific stack: the original native library crashes on
retained inputs, and Python pin changes cannot replace that code. The resulting
custom GDAL packages, Rasterio patch/build, ongoing backport upkeep and expanded
acceptance burden exceeded a routine dependency update. Prefer evaluating a
compatible supported binary package set next; if no such set is qualified,
retain an explicit blocker and make the maintenance tradeoff a separate scope
decision. Do not restart this custom build automatically. No risk waiver or M4
closure is implied. Deployment resume and manual-only NFS recovery are unchanged.
