# Preparatory unchanged common-image baseline

**Status**: Build succeeds; inventory/scan in progress; M0 full baseline and M1
acceptance remain pending. This does not authorize deployment.

## Source and build

Clean detached checkout: `/workdir/wepppy-security-baseline-20261111`, revision
`2041fb8e267de3a1572d9fb4f4a62e725b75cc91`. The original master working tree and
unrelated changes remain intact. `git lfs checkout`, `git lfs fsck`, and
`python3 tools/verify_lfs_materialized.py --tracked` all pass; checkout status
is clean before building. This contains the unchanged production source, before
the test-only M0 baseline correction. Compare build-context differences against
the reviewed M0 checkpoint before reusing evidence.

The canonical production and wepp1 Compose overlays build only `weppcloud`,
without cache, under candidate tag
`wepppy-security-baseline:2041fb8e2-20261111`. No service starts or production
activation occur. The resolved build user/group is roger/docker, UID 1002/GID
130. Build succeeds in 599.73 seconds, finishing 2026-11-11 06:31:15 UTC.
Exact image ID:
`sha256:1819856096bf838cdf32fe52b035d13971e6aaa3aad4652b63759926fae23d74`.

The first invocation failed before building because an unnecessary
`--project-directory` changed Compose's relative context resolution. The retry
uses canonical Compose-file-relative paths, with explicit context readback.
Both command receipts/logs are retained. No Dockerfile change was needed.

Resolved immutable amd64 bases:

- Node: `sha256:afdf98210b07b586eb71fa22ba2e432e058e4cd1304d31ed60888755b8c865fb`.
- Python: `sha256:05a994d2344eb364cc186910f4fc8786a38215f39f00d0acc25bff33a08f4177`.

Vendor commits passed through existing Dockerfile arguments:

- WBT: `abdaa98fa10316796a58de9aa74bdad4a751faee`.
- WEPPcloud2: `7c92e33cd6c6b8d33732edd943f9840834d88b34`.
- WEPPpyo3: `5e3540f684c8606f4140afcd72ed5a21df5ab85f`.
- Rosetta: `1c22335ee0e4055f45adb3e597e5bf49cd9a2c88`.

Other downloads and apt resolution remain governed by the existing Dockerfile;
recording these inputs does not claim a hermetic/reproducible build.

## Protected evidence and preliminary lock audit

Raw root:
`/workdir/weppcloud-deployments/.local/dependency-security/evidence/baseline-2041fb8e2-20261111/`.
The exported image, native SBOM, direct inventories, scanner/database bytes,
commands, and logs stay private. No public raw artifact upload is used.

The primary lock hash remains
`2ddc0117c0bf2c559d2509bded8964801092fe68e4046ec3c8fa3df9c6877a92`.
A temporary copy audited with host Node 25.0.0/npm 11.6.2 reports 19 dependency
findings across all dependencies (4 High, 11 Moderate, 4 Low), and zero with
`--omit=dev`. These are exact-lock audit results, not tests of the Node 20 build
runtime. Both native JSON reports and command/hash receipts are retained in
`npm-audit/`; transferred bytes were read back and hash-compared. No audit-fix
or dependency mutation was performed.

## Direct native readback

Python and dpkg inventory commands exit zero. A no-network, read-only container
with capabilities dropped imports GDAL, Fiona, Rasterio, PyProj and WEPPpyo3 as
UID 1002/GID 130. Python is 3.12.16; GDAL/Fiona link GDAL 3.10.3, while Rasterio
1.3.10 bundles GDAL 3.8.4. PyProj is 3.7.1 and WEPPpyo3 resolves through the
canonical vendored symlink. Separate native copies require coverage; this import
check does not establish scientific output parity or vulnerability clearance.

## Open acceptance conditions

The successful database refresh at 06:26 UTC returned build timestamp
2026-11-10 06:21:20 UTC, outside the ratified 24-hour window. Its unchanged
immutable download reference is retained in `grype-db/6/import.json`. Scanning
with it is diagnostic triage only; it cannot release the gate. A fresh database
and successful refresh are both required for acceptance.

Direct inventory reconciles all 308 Python and 432 Debian package/version pairs.
The initial native SBOM has 2,099 unidentified executables and 15,574 Java-archive
parser errors. The latter are verified CLIGEN `.par` text files: exact-image
hashes equal clean source, all are regular UTF-8/no-NUL/non-ZIP files with
scientific labels. Independent review records 11 existing numeric-format anomalies;
this classifies file type, not scientific correctness.

A naive 26-parent-glob exclusion failed exact-set validation because it also
matched 12,703 symlink aliases. Replacing the `all_years/*.par` glob with its one
validated regular-file path yields 25 parent globs plus one exact file. Exact-image
readback proves 15,574 expected/actual matches, no extra/missing/nonregular paths,
and no symlinked ancestors. Rescan uses this verified set with Java scanning still
enabled. Initial reports and failed-first-pattern evidence remain retained.

The diagnostic Grype run retains 2,894 matches and 327 ignored matches, including
114 Critical, 748 High, 568 Medium, 142 Low, 1,496 Negligible, and 153 Unknown
records. These are raw records, not deduplicated/applicable vulnerability counts.
All 3,221 records have draft disposition rows with source record, aliases,
ecosystem/package/version/path identity, range/fix, layer and advisory references;
all remain explicitly pending review. Database bytes match before/after scanning.

Native-analysis uncertainty, every finding's disposition, unmanaged/vendor
coverage, and independent M1 review remain open.
No production applicability conclusion is imported from the earlier dev-image
qualification counts.
