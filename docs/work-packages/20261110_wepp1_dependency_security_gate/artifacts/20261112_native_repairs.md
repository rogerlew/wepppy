# MariaDB and Pillow native repairs

Status: combined clean image, installed readback and real PATH report pass;
fresh collection passes; complete gates remain open. No
activation or risk acceptance. Resume remains deferred; NFS failures require
manual intervention without waits.

## MariaDB

The exact three-line upstream Big5 correction fixes the original escaping
regression in both shared and static libraries. Original binaries return the
wrong bytes and fail; rebuilt libraries return the required exact bytes. GBK
full input, UTF-8 escapes, Big5 lead/trail boundaries, truncated leads, signed
byte callbacks and no-backslash behavior are covered separately.

Trial package image
`sha256:bd72f55de1951fad2713b8e3d984bfd073f2150d25d84b980449aef5de5c5335`
contains coherent `1:11.8.6-0+deb13u1+wepp1` client packages. Before/after file
readback changes only the shared/static libraries and package-owned provenance.
All existing plugin/header/link/mode/ownership records match. Six authentication
plugins load. Package audit and dependency check pass; package verification
matches baseline's existing excluded documentation entries. No server connection
or server deployment is claimed. The committed five shared/static/GDAL tests
pass in this image; 17 Pillow normal-consumer controls also pass on its old
Pillow 12.2.0 runtime (22 tests total).

The standalone build initially exposed different defaults (dynamic columns,
version metadata and large-file imports). The qualified recipe restores the
Debian parent settings and rejects import/export ABI or loader differences.
Matching Debian packaging patches do not modify the client runtime subtree.
A package trial also exposed slim-image documentation exclusion: provenance now
lives under `/usr/share/wepppy/dependency-provenance/`, is package-owned and is
present in the actual image. Failed trials remain retained; none was deployed.

## Pillow

The official 13.0.0 wheel contains an unfixed bundled Brotli decoder, so changing
only the Pillow pin is insufficient. The owned wheel rebuilds Brotli decoder
and common from exact 1.2.1 source, preserves the private loader aliases and the
other 24 native members, and sets distribution version `13.0.0+wepp1`. Pillow
Python/native runtime version remains 13.0.0. Actual source/version/hash records
are authoritative; the retained `.1.2.0` filenames are compatibility aliases.

The source helper's trial image
`sha256:5e65fb24ef7dfa49cdf7c02bada9c8bbdc38912429d9a3b10abb5f71cbb688c1`
passes 16 native codec, alpha, multiframe, ICC, WOFF2 and Agg consumer checks.
Fifteen selected upstream 13.0.0 regressions pass under a 90-second deadline and
4 GiB virtual-memory limit, with no skips. These cover TIFF geometry/colormap,
JPEG tiles/short strips, BytesIO buffer/error cleanup, shared IFD data, image
storage transitions, JPEG metadata/tile bounds and APNG disposal-bomb rejection.
The first invocation's incorrect upstream class selectors collected no tests;
the retained second invocation uses the actual classes and passes all 15.

WOFF2 BASIC output pixels and geometry match the 12.2.0 baseline exactly.
Both environments lack RAQM; earlier requested-RAQM output was a silent BASIC
fallback and is not counted. Revised receipts record effective layout explicitly.
Actual mapped decoder version is 1.2.1 and exposes the repaired block-switch
error contract. No exact hostile Brotli stream reproduction is claimed.

Trial2 ABI readback shows identical imports/exports, dependencies, SONAMEs and
RPATHs; only decoder/common change among 26 ELF members. Highest imported GLIBC
version is 2.14, within both retained wheel tags. The final helper additionally
enforces imported-symbol equality and deterministic generated ZIP timestamps;
the final image must bind that revised helper, not reuse the older trial hash.

## Evidence and durable contract

Private roots are `mariadb-batch-20261112/` and `pillow-batch-20261112/` under
`/workdir/weppcloud-deployments/.local/dependency-security/evidence/`. Retained
files include original negative controls, installed package readback, trial2
ABI/font receipts, upstream source hashes, review packets and validation log
hash indexes. Raw evidence remains private.

The ongoing developer/operator contract is
[Owned native dependency repairs](../../../dev-notes/dependency-native-backports.md).
The exact-version guard must be requalified when Debian changes; retirement
requires proving upstream artifacts pass these same real regressions.

Pillow source security review has no unresolved Medium/High findings. The retained
packet `pillow-batch-20261112/validation/implementation-security-review.json` has
SHA-256 `0b1b1ababf07fddf845df7c0bd20694e685fde1573a4977b81550c480fa122af`.
Independent MariaDB implementation review likewise approves the bounded source
for combined construction; final installed evidence remains required.

## Combined clean image validation

Source `555ab5c02795caff69935ed021ded7f89a70f41b` builds in 513.526 seconds as
`sha256:37e7dd311bbd799b9559791cb6fd49a7940c38154321e39c17ffab7f4548c08d`.
The isolated UID 1002/GID 130 runtime passes 110 focused tests in 14.27 seconds.
The actual Quarto PATH report passes in 54.25 seconds, including HTML, local
assets and CSV values. Its embedded PNG decodes to 864 by 1127 pixels with
nonconstant content. Installed MariaDB and Pillow library hashes match their
provenance records. No production service was activated.

Logs, generated-image readback and their hash index are retained under
`native-repairs-batch-20261112/validation/`. Fresh collection completes with 2,799 matches and 332 ignored matches. Pillow
has zero findings; MariaDB backports still require hash-bound dispositions.
Manifest SHA-256 is `de85377e5a1084a3a125af4f31037a2a87b08ad7ef8f522efca719f90075970c`;
scan SHA-256 is `b4173485bfcf707a08574bf0231a38b843ee62785971d90ecc7e13f4b702caac`.

full pytest/npm acceptance and further Python/GDAL repairs remain open.
