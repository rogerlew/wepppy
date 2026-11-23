# Independent correctness review, 2026-11-23 UTC

## Scope

The production baseline is common image `b6e0462f8a74`. Its build on wepp1 used source `dacf4185d`, `docker/Dockerfile`, and user and group `1002:130`. BuildKit record `y5izgeviowf6ifn1eyp4gpsds` binds the image to its Node, Python and Rust materials. The archived root filesystem digest matches the retained receipt. Full hashes and command results live in the private evidence store under `grype-remediation-20261123/correctness/`.

## Consumer review

Docker CLI is required by the Compose WEPPcloudR backend. The worker sends a render request through `docker exec --user` and reads back the published HTML. Git LFS materializes Rosetta and three vendored repositories during the common-image build. Quarto renders the PATH report and ships its own esbuild executable. The 197 baseline Go matches resolve to 74 at the Docker CLI, 62 at Git LFS and 61 at Quarto esbuild. The presence of these consumers prevents blanket dismissal of their bundled Go findings.

The earlier `63ae6f940` framework trial predates current Google and CILogon account binding. The candidate adapts the current callback to joserfc and preserves the explicit nonce, issuer, subject and mailbox checks. The independent provider fixture replaces outbound HTTP and records identity writes while exercising actual PKCE, discovery, JWKS, signature verification and redirects. A disposable DEVAL fixture copies the existing forest canary inputs into owner-only scratch space under the production worker identity. It exercises real report publication without writing to the original run.

## User states and failures

| Workflow and state | Observable result checked |
| --- | --- |
| Google and CILogon with a valid local session, signed identity and matching subject | The callback returns to the requested page and submits one identity resolution and one remembered login. |
| Expired provider credential | The callback returns to the configured login page before userinfo, identity resolution or login. |
| Missing authorization state or nonce, mismatched issuer, audience, subject or signature | The current route suite exercises rejection. The independent exchange uses ordinary and expired credentials. |
| PATH with populated, existing Parquet, geospatial and contrast inputs | The real controller renders HTML with local assets and checks the configured-threshold CSV against its solve result. |
| WEPPcloudR with existing owner-only run inputs and empty scratch output | The default Compose command regenerates and publishes a fenced report. The original forest canary is read only. |
| Framework, OS and scientific states outside these selectors | The exact-image regression suite and coverage disclosures determine the remaining release hold. |

The private checker receives candidate tests on a read-only mount and imports the installed application from the image. It also exercises ordinary local Git LFS clean/smudge, CSV, byte-range and NetCDF consumers. Its renderer uses the candidate Docker CLI to reach a disposable local service. Existing route tests cover datastore behavior separately from the independent provider fixture.

## First candidate evidence

The integrated image is `sha256:a116e2d21457a0e33a6070ab42518be0adead13ea9b53db5c55d9f7dfa8871d0` from `65084ea5a1587cde24f8f9612ed87e70d5a8fd6b`. A stopped-container export matched every baseline file and link in the four scientific source trees, including 1,206 WBT, 1,545 wepppyo3, 44 Rosetta and 11 weppcloud2 entries. The three Go executables and generated archive console bundle also match baseline bytes.

All 18 shared static vendor files match their baseline hashes. The serving image also contains nine legacy Bootstrap, jQuery, DataTables and Bootstrap TOC files from its ignored host build context. Neither the current frontend build nor its tracked callers require them. The wepp1 Caddy static route serves a host bind mount. All nine files remain there and match their baseline bytes. The canonical deployment regenerates controllers and themes on the host.

The candidate Docker CLI sent the production renderer command to a disposable forest WEPPcloudR service. A copied Parquet and GeoJSON fixture produced a 14,076,819-byte DEVAL HTML file. It contains the run identifier and published under UID 1002, GID 130 and mode 0644. The SHA-256 is `21d0b73b5d19d4685990ed5c958df4437b1fcb8a744d268b0bb11c3711847f75`. The original scientific input files remained read only. Both images used by this test have immutable identity records in the protected evidence directory.

The first direct PATH invocation on forest1 stopped at OCI container creation. The host systemd D-Bus service timed out before Python started. The same immutable image was loaded on forest. Only the tests were mounted, read only, and the application and dependencies ran from the image under UID 1002 and GID 130.

The real PATH controller produced a 2,137,819-byte HTML report with local browser assets and an 864 by 1,127 PNG using all three RGB channels. For the 15.0 and 48.2 thresholds, the CSV selected hillslope 12 and reported a cost of 513,272.60634374997, matching the controller result within the existing test tolerance. The report SHA-256 is `3957036f23df6977cd57ac410f7823bc9950c2c0ec29b3fae4e05885f8dfa12b`.

On the same image, three query route cases, four full Google/CILogon provider exchanges and four file-consumer cases passed. The IO checks exercised on-disk and in-memory CSV, reference-file byte ranges and generated NetCDF values. The Git LFS clean/smudge fixture reproduced the source bytes. The independent provider tests stub outbound HTTP, the datastore and login sinks. Live provider/network availability and production deployment behavior remain outside this review.

The exact-image framework and codec selection passed 194 tests in 20.35 seconds. It includes current callback redirects and account linking, query and MCP access, actual Pillow codec use and real loopback compressed HTTP/TLS transfer. The private checksum index is `review-evidence-sha256.json`, SHA-256 `12364ad2e75185e6079f795c86f1867f0d52c1eeeddce201155c8964ab461b05`.

## First candidate verdict

Independent correctness review passes for the tested candidate workflows. The host installation instructions now cover the required owned Pillow wheel. No unresolved correctness defects were confirmed in these repairs. Hold release pending the package-wide regression results, security dispositions and production operator decision. Review completed by the independent correctness agent on 2026-11-23 UTC.

## Follow-up candidate, 2026-11-23 17:29 UTC

**Independent correctness review passed for image `sha256:27f3c409f45318dff99756cd854b7a03395f406da82c26dd3c0b6f9efbd4135b`.** The clean production Compose build used source `cc335e36555a8ae3af65eaba12b1080b8a16b57d` and the same Python and Node base digests as the serving build. A standalone container preflight on forest1 timed out while creating its systemd scope. BuildKit ran the application and scientific probes from the immutable candidate under UID 1002 and GID 130 with networking disabled and read-only test inputs. The extracted candidate CLI drove a disposable renderer on forest.

| Workflow | Follow-up artifact readback |
| --- | --- |
| Quarto PATH | The actual controller produced a 2,137,819-byte HTML report with local browser assets and a nonblank 864 × 1,127 RGB map. The threshold CSV matched the previous candidate byte for byte. The 15.0 and 48.2 thresholds selected hillslope 12 at cost 513,272.60634374997. |
| Docker CLI and WEPPcloudR DEVAL | CLI 29.10.0 executed the configured renderer under the worker identity. The published 14,076,832-byte HTML contains the expected run identifier and has UID 1002, GID 130 and mode 0644. |
| Git LFS and Rosetta | Git LFS 3.8.1 materialized all 15 assets from an ordinary local Git/LFS source at the pinned commit. Every byte matched the installed assets, object verification passed, and Ann.parquet contained 4,640 rows. |
| GDAL, Rasterio, Fiona, Pyogrio and DuckDB | All six readbacks matched the previous scientific trial, including netCDF values, GeoTIFF round trip, transformed coordinates, GeoJSON attributes, library maps, CLI checksum 10 and all 1,048,576 cells of a two-thread warp. The Debian and Rasterio copies still register the affected netCDF driver. |
| External scientific sources and frontend assets | All 1,206 WBT, 1,545 wepppyo3, 44 Rosetta and 11 weppcloud2 file/link entries matched the serving inventory. The generated archive console and 18 shared vendor files matched serving hashes. The nine historical vendor files documented above account for the entire image-only difference in that directory. |
| Auth, file and packaging consumers | Three query route cases, four signed provider exchanges and four file-consumer cases passed. Setuptools 80.10.2 generated both expected run-ID prefixes, supported a registered filesystem round trip, and built a wheel with identical module bytes. All three embedded Go executables matched their independently qualified replacement hashes. |

The protected evidence index is `grype-remediation-20261123/gate2/correctness/review-receipt.json`, SHA-256 `a7c69b2b19b17e75b5da4af45da73b58a85f1fe1fed0c5c79b65a3b73cf5fa1e`. It binds the PATH and DEVAL outputs, scientific and source manifests, runner logs and build receipt to this exact candidate. The open GDAL finding and the package-wide security decision remain release considerations. [GDAL follow-up](20261123_gdal_followup.md) · [release decision](20261123_release_decision.md)
