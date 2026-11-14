# Dedicated shape-converter image qualification

Date: 2026-11-14 UTC

Status: local one-worker candidate qualified; independent correctness, QA, and
security reviews passed; not deployed

## Candidate identity

- Contract checkpoint: `613e832fc`
- Base: `ghcr.io/osgeo/gdal:ubuntu-small-3.12.4@sha256:9acfdf967ece13a9a1d9622a494d726aad6b9759aeaae40bbd4d8cb74c843971`
- Final local image: `sha256:d515d75ea603f174aa7b6b36c075f42fb0406cdb17901d60997aa0bbdbb0dff6`
- Uncompressed Docker image size: 744,851,897 bytes
- Runtime identity: `10001:10001`
- Dockerfile-specific allowlist context sent 1.84 kB for the final rebuild.
- Both build stages use the immutable base digest directly; Compose cannot
  override it. Ubuntu packages are resolved from snapshot
  `20261114T060000Z`, recorded in the image label.
- Python inputs are transitively resolved and hash locked. Fiona 1.10.1 is
  source-built against the base image's `gdal-config`; build-only Cython, pip,
  and setuptools are removed from the copied virtual environment. A final-stage
  assertion verifies that copied Fiona and `gdal-config` both report GDAL 3.12.4.

The runtime image copies only the shape-converter package, the required
observability package, and package initializers. Inspection found no `/run/secrets`,
`/wc1`, `/geodata`, or `/opt/app/.env` path.

## Runtime inventory and linkage

| Component | Final candidate |
| --- | --- |
| GDAL / `ogr2ogr` | 3.12.4 |
| Fiona | 1.10.1, linked to `libgdal.so.38`; reports GDAL 3.12.4 |
| base-image PROJ CLI | 9.8.1 |
| PyProj | 3.7.1 |
| Shapely / bundled GEOS | 2.0.4 / 3.11.3 |
| NumPy | 1.26.0 |
| PyArrow | 23.0.1 |
| Starlette | 1.3.1 |
| Uvicorn | 0.30.6 |

Fiona linkage also resolved GDAL's internal PROJ and GEOS libraries. The common
WEPPpy image and its dependency set were not changed.

## Resolved Compose boundary

Resolved production, wepp1, and development Compose configurations use
`docker/Dockerfile.shape-converter` and the dedicated image. Production and
wepp1 contain no `secrets`, `env_file`, datastore `depends_on`, host data mount,
Docker socket, or common application environment. They retain the fixed UID,
read-only root, `cap_drop: ALL`, `no-new-privileges`, process/memory/CPU/file
limits, hardened tmpfs, and the internal `shape-converter-sandbox` network.
Development mounts only the shape-converter and observability source directories,
both read-only.

A disposable final-image container ran the production one-worker command with no
network, a read-only root, no mounts, two hardened tmpfs mounts, all capabilities
dropped, no-new-privileges, and the declared resource limits. Container inspection
confirmed those effective settings. The `/health/ready` response still reports configured
`container/container` strings; its `200` is service-health evidence only and is
not evidence for the required second parser sandbox.

## Behavioral and artifact checks

The first Starlette 1.3.1 image failed at startup because Starlette removed the
`@app.middleware` convenience decorator. The application now registers the same
two dispatch functions explicitly through `add_middleware(BaseHTTPMiddleware,
dispatch=...)`. This is the implementation used by the former decorator and
preserves abuse-control/CORS ordering. Runtime inspection shows abuse control as
the outer middleware and relay CORS as the inner middleware, matching the former
decorator order. The common-runtime focused suite passed after the refactor, and
the rebuilt exact image then passed:

- live and ready health routes: HTTP 200;
- real multipart point conversion to GeoJSON: HTTP 200, one Point feature;
- real multipart point conversion to GeoParquet: HTTP 200, one row with the
  expected `NAME` and `geometry` columns;
- allowed-origin preflight: HTTP 204 with the expected allow-origin and methods;
- disallowed-origin preflight: HTTP 405 without an allow-origin header;
- one-worker rate limiting with count one: HTTP 200, 429, and 429, with canonical
  `rate_limited` and `Retry-After` on rejection;
- one-worker global-inflight limiting with limit one: a deliberately incomplete
  but valid request held the slot, a competing request received canonical HTTP
  503, the held request completed with HTTP 200, and a subsequent request was
  admitted with HTTP 200. Completing rather than disconnecting the held request
  produced no exception-group traceback;
- twenty consecutive metadata reads for the converted request: HTTP 200;
- request scratch cleanup after both conversions;
- inert legacy pickle payload: canonical `invalid_shapefile`. The earlier
  disposable executable-canary evidence remains the retained no-side-effect
  regression; the final image was not asked to execute a command-bearing probe.

Focused automated validation:

- 37 passed:
  `test_health_routes.py`, `test_runtime_hardening.py`,
  `test_convert_api.py`, `test_parser_ipc_semantics.py`, and
  `test_runtime_hardening_api.py`;
- 61 passed: `test_convert_endpoint.py`, `test_abuse_controls.py`, and
  `test_abuse_controls_api.py`, covering middleware semantics in the common
  runtime after explicit registration;
- 11 passed on the host for
  `tests/docker/unit/test_project_config_rollout_contract.py`, including fully
  resolved production, wepp1, and development Compose configurations. The same
  test module under `wctl` reported 8 passed and 3 explicit skips because the
  test container has no Docker Compose executable.

No full repository suite was run, per the work-package validation decision.

## Vulnerability scan and disposition

Acceptance inventory and scan used Syft 1.57.1 and Grype 0.121.3. The Grype
database was schema `v6.1.10`, built `2026-11-13T15:40:34Z`, with source checksum
embedded in the retained database-status record. The exact Docker archive,
Syft JSON, native-cataloger JSON, CycloneDX, Grype JSON, Grype log, and database
status were hashed as follows:

| Artifact | SHA-256 |
| --- | --- |
| exact image archive | `374e797d18b0ff35cf299d25267b720dbbccfd35f51031eaa288fced3b7802c4` |
| Syft JSON | `39159d92775a56598c68fd9a8eed9cb5eea733d38e40d8821d451732708c8b7f` |
| Syft native-cataloger JSON | `aa45d2aea21392d0cfca7deca6ff3a62bc177f1affc8d9f095d52111bd336f3d` |
| CycloneDX JSON | `773eabad683c0b81632ee567a247321617a67ee106f460aed5e259b272dd6c87` |
| Grype JSON | `dfbff313e8875bc69ae1873c0e79e538def63e4a93ce93e9bef1cb620b387b28` |
| Grype log | `1d849508c5845a101dbf8203e22e162048c03acbc829b4f8a3c2a02f97986d9a` |
| Grype database status | `9dfa76e807cf3909449da58382531221f7d3c3b1e99606dad502a9b1e7e93f01` |

Grype reports 332 package records: 0 Critical, 1 High, 315 Medium, 13 Low,
and 3 Negligible. The 315 Medium records contain extensive duplication across
binary packages from the same source and collapse to 105 unique advisory IDs.
Syft identified 178 artifacts. Wheel-native inspection separately records PyProj
with PROJ 9.5.1 plus bundled curl/nghttp2/sqlite/tiff, Shapely with GEOS 3.11.3,
and PyArrow native libraries matching Python package 23.0.1.

Trivy 0.76.2 was retained only as a supplemental comparison. It reports 0
Critical, 1 High, and 34 Medium, but logs a Python constraint matcher error and
misses `CVE-2026-8212`; its JSON hash is
`488a53108e4f349758958a427220c282807e3904e6a7b42a31d2462865f1062f`.
It is not the acceptance scanner.

The High finding is `CVE-2026-49014` / `GHSA-wphc-7cm7-8mf7` in GDAL 3.12.4,
fixed in 3.13.1. It is a
NetCDF geometry-container parsing flaw. It is not reachable through this service:
archive admission permits one shapefile dataset, the worker calls Fiona with
`enabled_drivers=["ESRI Shapefile"]`, and it asserts the opened driver is exactly
`ESRI Shapefile` before reading dataset content. `GDAL_DRIVER_PATH` is disabled.
This is a non-reachability disposition, not operator risk acceptance. Moving to
GDAL 3.13.1 would also move the official image to a newer Ubuntu/Python baseline
and is outside the bounded compatibility choice.

The 315 Medium package records have no fixed Ubuntu package version in this
snapshot and group as follows. These groups are tied to the full hashed Grype
report rather than presented as a substitute advisory database:

| Finding group | Request-path disposition |
| --- | --- |
| OpenJPEG (`CVE-2023-39328`, `CVE-2023-39329`) | JPEG2000 drivers are outside the exact Shapefile driver allowlist. |
| Python ZIP preallocation (`CVE-2026-15310`) | The affected BZIP2/LZMA/Zstandard methods are rejected before extraction; only Stored and Deflate are admitted. |
| Other Python standard-library findings | The affected base64 alternate-character, IMAP/POP/urllib/cookie/TLS, tarfile, CSV Sniffer, XML/XPath, pybddisasm, social-auth, Scrapy, and FIPS-mode paths are not called by request handling. Uvicorn/Starlette serve HTTP rather than the affected stdlib client/server helpers. Absolute ZIP and scratch quotas remain enforced. |
| Python/Expat XML and system Expat | Conversion does not parse XML: general XML is rejected, `.shp.xml`/`.qmd` are removed without parsing, and `.prj` is WKT. |
| OpenSSL, GnuTLS, Kerberos, SASL, and RTMP | The runtime has no request-path authentication/TLS client; TLS terminates outside the service and the service network is internal/no-egress. |
| `util-linux`, mount, PAM, ACL, glibc tools, dash, and tar | The service does not invoke these tools on uploads; the runtime is non-root, read-only, capability-free, and starts Python directly. Archive handling uses Python ZIP code, not `tar`. |
| system SQLite/SpatiaLite | No SQL or SpatiaLite request path exists. PyProj's separately bundled SQLite is inventoried with the wheel and reads its fixed PROJ database. |
| TIFF/JPEG/OpenJPEG and other GDAL driver dependencies | Raster and alternate vector drivers are outside the exact Shapefile driver allowlist and the opened driver is asserted before feature reads. |
| `python3-pkg-resources` (`CVE-2026-59890`) | The affected source-distribution build behavior is not a runtime request path; the candidate is Linux and the copied virtual environment has no pip/setuptools. |

Grype also detects three Low GDAL advisories, including `CVE-2026-8212` /
`GHSA-r5m4-5vww-w9f5`, that Trivy omitted. Their affected drivers/operations are
outside the exact Shapefile-only open path; they remain recorded in the hashed
report rather than being hidden by the acceptance threshold.

These are non-reachability dispositions, not accepted reachable risk. Any later
driver expansion, XML parsing, subprocess/tool invocation, network egress, or
runtime build behavior invalidates the relevant disposition and requires a new
scan/review.

## Remaining gates

Independent re-review after the one-worker repair passed:

- correctness: PASS, with the command, resolved Compose regression, canonical
  contract, plan/tracker, and runtime evidence consistent;
- QA: PASS, with no unresolved Medium/High finding; observe capacity/latency in a
  separately authorized rollout;
- security: PASS for the dedicated-image gate, with no reachable Medium+ finding
  under the current exact-driver, Stored/Deflate-only, no-egress, hardened
  one-worker contract.

Before full package closeout, move the complete scan report or a complete
105-unique-advisory appendix out of temporary storage and explicitly retain that
the embedded PyProj/Shapely/PyArrow native libraries were inventoried but were
not all independently vulnerability-matched by native package identity. This is
a Low provenance follow-up, not a dedicated-image release blocker.

Exact-command QA first proved that the former two-worker command multiplied
process-local rate/in-flight limits and made conversion metadata nondeterministic.
The operator approved the bounded repair on 2026-11-14. Production now runs one
Uvicorn application worker, and the resolved Compose regression asserts the full
command. Requalification demonstrated one authoritative limiter/metadata state:
the rate and inflight outcomes above, twenty consecutive metadata HTTP 200s, and
successful health, CORS, GeoJSON, GeoParquet, cleanup, and post-release requests.
Increasing the worker count now requires a reviewed shared-state contract.

This candidate reduces dependency and cross-service exposure but does not create
an effective second parser sandbox. M4, runtime-derived sandbox readiness, the
remaining semantic/compression decisions, independent final reviews, and a
separately authorized rollout remain open. No production image publication,
deployment, or issue closure occurred.
