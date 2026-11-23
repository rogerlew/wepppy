# Independent security review

**2026-11-23 UTC · High impact · Hold**. The security reviewer examined the serving common image, source batches through `65084ea5a`, the repaired frontend lock and the private evidence below. Login, signed identity tokens, request-path checks, compressed transfers, image decoding and report rendering cross trust boundaries. Roger Lew owns the release risk decision.

## Serving image

The reviewed image is `sha256:b6e0462f8a749eabb168ea398a4f8056c46305f2a003e04b026c0d5623567c94`. The package-pinned manifest verifies the retained SBOM, scan, direct inventory, lock and npm report. The private review directory on forest is `evidence/grype-remediation-20261123/security/` under the dependency-security store. Its baseline ledger SHA-256 is `724a77e04cd1046f12a60e395f3918788725d195626985f0bceb9893bbd6d436`. Each row retains original scan position, advisory aliases, installed paths, source component, revision, fix state, prior review reference and current assessment. The companion platform-disposition supplement binds ten rows to the reviewed platform, SHA-256 `6c33d41488fdfb021ae3f5c6c12f5f3777901373c131719c37de4458ceae6bc9`. Open applicability requires further evidence or an explicit release decision.

| Evidence | Result |
| --- | --- |
| Grype inventory | 3,002 primary rows, including 87 Critical and 679 High. Another 516 rows were suppressed by the scanner for the Linux UAPI header package. All 3,518 rows appear in the ledger. |
| Known-exploited flags across all severities | Six primary rows. Starlette has one applicable installed match and one build-cache match. Python Brotli has three verified patched copies. The OpenSSH client match requires an absent daemon and different libc. |
| Fixed-version availability | 99 Python and 108 Go primary High/Critical rows outside the uv cache have scanner-listed fixes and open applicability after platform review. Repeated paths, advisory aliases and embedded modules are included in those counts. |
| Debian | 61 source packages. Comparing the installed source revisions with Debian's trixie fixed versions establishes 60 backported primary High/Critical rows. The database labels these rows unresolved. The ledger preserves both results. |
| Cache | 173 primary rows have only uv-cache paths, including 15 Critical and 89 High. Removing those paths reduces packaged copies. Assess installed code independently. |
| Embedded Go | Docker CLI has 74 primary matches, git-lfs 62 and Quarto esbuild 61. WEPPcloudR uses the Docker CLI for its docker-exec backend, git-lfs materializes build assets and esbuild ships with Quarto. The scanner lacked function symbols. All 75 Go advisory records were checked against linux/amd64. Six rows specify a different OS or CPU, including three Critical Windows-only rows. |
| Native coverage | 3,422 native file identities and 15,574 verified scientific data files. Hash inventory does not map every WEPP, WhiteboxTools, GDAL, rasterio or vendor extension to every affected upstream function. |
| Prior acceptance | All three hosts retain the same serving-image approval, owned by Roger Lew, expiring 2026-11-24 06:23:17.979322 UTC. Its scope is the pinned serving artifact. |

Archive readback on wepp2 bound Python Brotli's installed extension to its wheel RECORD, the exact source commit and the previously reviewed decoder source hash. Both cache copies match the installed binary. The system Brotli revision independently meets Debian's trixie fix. Pillow and PyCurl each ship a separate private decoder. OpenSSH archive inspection found no sshd executable and the runtime reports glibc 2.41. Host kernel and host SSH are outside the common-image assessment. [Debian Brotli record](https://security-tracker.debian.org/tracker/CVE-2026-111497), [Debian OpenSSH record](https://security-tracker.debian.org/tracker/CVE-2026-123158).

## Repair review

The query middleware registration preserves ordering and the OAuth callback catches the migrated JOSE validation exception inside the existing login error boundary. Source review found no new credentials, permissions, deployment authority or expanded access checks. Artifact validation must exercise the actual verifier, valid login, rejected claims and redirect. Local npm audit comparison removed 17 concrete package/advisory/severity tuples and retained four. The audit lists zero new concrete advisory tuples despite changed counts of transitive dependency labels.

The original repair selects OAuthlib 4.0.0, which enters the affected range for a High device authorization endpoint advisory. The prior 3.2.2 was outside that particular range. Review prompted correction to 4.0.1 in `50de1db06`. The PyPI release records for all 13 selected package versions on `65084ea5a` list zero advisories. The image scan assesses the installed versions. [Upstream advisory](https://github.com/oauthlib/oauthlib/security/advisories/GHSA-3jp2-3mrg-2vxc).

## Exact candidate readback

The forest1 build from `65084ea5a1587cde24f8f9612ed87e70d5a8fd6b` produced `sha256:a116e2d21457a0e33a6070ab42518be0adead13ea9b53db5c55d9f7dfa8871d0`. The reviewer verified the stopped container identity and read the filesystem export as data. Its SHA-256 is `2540298cf0fb9df14889c9cdf0692d6f1fd0b3c757861ff9684d3629bcd4564b`. The readback packet `security/forest1/archive-verified.json` hashes to `66b87b946474f570037a91fb0348092c89b23954e68e6b6c0599032277b618e2`.

The image contains the selected Python versions. The Python Brotli source pin, Pillow repair provenance and native hashes match the installed files and wheel RECORD entries. PyCurl ships separate 1.2.1 decoder/common libraries. There are zero uv cache files and zero sshd executables. All 432 Debian package versions and the three Go binary hashes match the serving image. The inventory contains 2,455 native paths and verifies 15,574 scientific data files. Eight Python metadata paths from the earlier checkout’s `.wctl` directory disappear independently of installed runtime repairs.

The local production-only npm audit returned zero findings. All 24 full lock reports belong to development dependencies. Four concrete advisories remain in build/test packages. The production static script copies fixed asset paths and the evidence record identifies all 16 emitted files.

## Release gate

Hold pending the exact candidate scan, same-database comparison, native and authentication evidence, full regression result, and independent correctness review. An image-scoped operator decision must cover any accepted residuals. The underlying protected ledger contains advisory details and remains available for the release decision.
