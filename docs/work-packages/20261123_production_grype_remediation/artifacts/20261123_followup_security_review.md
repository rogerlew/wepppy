# Independent security review of the follow-up image

**Hold production release pending an operator decision.** The clean build of `cc335e36555a8ae3af65eaba12b1080b8a16b57d` produced `sha256:27f3c409f45318dff99756cd854b7a03395f406da82c26dd3c0b6f9efbd4135b`. On 2026-11-23 UTC the reviewer verified the repairs for all three Go executables and both setuptools dependencies. **Zero applicable known-exploited findings and one applicable fix-listed High finding remain.** The High finding affects two installed GDAL libraries. Another 385 Debian High/Critical rows remain open. [GDAL qualification](20261123_gdal_followup.md) · [Release policy](../../../infrastructure/production-deployment-policy.md)

## Same-database comparison

| Primary Grype rows | Serving image | First candidate | Follow-up candidate |
| --- | ---: | ---: | ---: |
| Critical | 87 | 59 | 49 |
| High | 619 | 445 | 342 |
| Medium | 533 | 428 | 347 |
| Low | 151 | 131 | 127 |
| Negligible | 1,431 | 1,431 | 1,431 |
| Unknown | 3 | 3 | 3 |
| **Total** | **2,824** | **2,497** | **2,299** |

The serving SBOM was rematched on wepp2. The first candidate’s retained scan verified against its original manifest and the identical database. From serving to follow-up, 525 primary rows disappear, representing 520 groups. From first candidate to follow-up, 198 primary rows disappear, comprising 196 embedded Go standard-library rows and two setuptools vendor rows. Both comparisons add zero groups. Six retained groups change package version while preserving severity. All three scans have 334 suppressed Linux UAPI header rows, individually reviewed. [First image review](20261123_security_review.md) · [Go reachability review](20261123_go_reachability_review.md)

## Remaining exposure

| Follow-up disposition | Verified result |
| --- | --- |
| Known exploited | The two flags are the source-patched Python Brotli extension and an OpenSSH server advisory. Its compiled extension matches the installed wheel RECORD, its pinned source commit contains the repair, and the Pillow and PyCurl private decoders remain separate. The filesystem contains no sshd, sshd-session or sshd-auth and uses glibc. |
| Fix-listed High | GDAL `GHSA-wphc-7cm7-8mf7` / `CVE-2026-49014`. Debian GDAL 3.10.3 and Rasterio's bundled GDAL 3.8.4 are byte-identical to the reviewed netCDF-capable libraries. The qualified private replacement changes Rasterio's available formats. Roger Lew must decide whether to qualify that scientific behavior change, wait for compatible packages or accept a time-bounded exception for this image. |
| Other open Critical/High | 48 Critical and 337 High Debian rows remain without a scanner-listed fix. Grype labels 328 wont-fix and 57 not-fixed. Together with GDAL, 386 open rows represent 98 advisory IDs. Counts include aliases and multiple packages built from the same Debian source. The native inventory cannot establish advisory coverage for every scientific binary. |
| Four other raw High rows | Grype continues to flag the Debian git-lfs package against trixie. The installed binary matches the reviewed 3.8.1 source-built package. The upstream 3.8.1 release identifies all four as corrected, and Debian records the fix in 3.8.1-1 on sid. [Upstream release](https://github.com/git-lfs/git-lfs/releases/tag/v3.8.1) · [Git LFS package review](20261123_git_lfs_build.md) |
| Go and Python | The Docker CLI, Git LFS and Quarto esbuild hashes match their independently qualified executables. The only remaining Go row is a Windows-only x/sys Low on Linux. The Docker CLI’s compiled URL-query-limit override remains scoped to the reviewed renderer workflow. Setuptools 80.10.2 contains jaraco.context 6.1.0 and wheel 0.46.3. Its own previously reported Medium and Low scanner rows remain open. [Go review](20261123_go_reachability_review.md) · [Setuptools review](20261123_setuptools_followup.md) |
| npm | Full-lock audit reports 12 moderate and one low, unchanged from the first candidate. Four concrete advisory URLs persist. All 16 emitted primary static assets match their reviewed hashes, and the primary frontend node_modules directory is absent from the runtime. The itemized ledger tracks the build and test dependencies. |

The collector verified 15,574 scientific files and 2,455 native paths in a never-started container's filesystem export. Its SHA-256 is `85f23517c05e3437619a9d585f955594283503e1c8bdfe7a171df7a5d4a511a4`. The exact image also contains an incidental transitive Blosc2 change from 4.15.0 to 4.16.1. All four changed Blosc2 native files matched the published wheel. An ordinary NumPy compression roundtrip and PyTables Blosc2/Zstd HDF5 roundtrip returned identical data under UID 1002 and GID 130. [Blosc2 release files](https://pypi.org/project/blosc2/4.16.1/#files)

## Evidence and authority

The wepp2 importer retained the complete protected bundle under `grype-remediation-cc335e365/8a9c94370963e38f84c136c43e5fc6d073e2e249f8519afa2244f6b5102a9b7f/bundle`. Forest independently verified the manifest and source, image, build receipt and report hashes before import. Syft 1.57.1 and Grype 0.121.3 used database SHA-256 `cb2940548440e727d0614b801e7e9d634931107592117c5feae46e085f533faa`. Collection reported zero analysis errors and two previously qualified diagnostics.

Forest's protected `grype-remediation-20261123/gate2/review/disposition-final.json` itemizes all 2,299 primary rows, all 334 suppressed rows and all 13 npm package records. Its SHA-256 is `d1f6d1a2b8def12a9204a6be0778233e68d1726b5f6f12631aea64b805995ac7`. The same directory retains both normalized deltas and native component comparisons. The wepp2 release-decision store contains no approval for the follow-up image. The serving-image approval expires **2026-11-24 06:23:17.979322 UTC**. Production activation and acceptance of the open residual risk belong to the operator.
