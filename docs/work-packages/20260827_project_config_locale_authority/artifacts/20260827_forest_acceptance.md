# WP12B Forest Acceptance Evidence

**Observation time**: 2026-08-27 13:21 UTC
**Host**: `forest`
**Branch**: `feature/project-owned-config`
**Deployment revision**: `3e8d0d09bcf5`
**Registry revision**:
`e72c92cc2b46422645924e5c732ca8796b8dff7b219b6933c42248c08dfd0388`

## Deployment and Health

The exact Forest development stack was restarted from the checked-out source
without an image build:

    docker compose --env-file docker/.env \
      -f docker/docker-compose.dev.yml restart weppcloud rq-engine

The existing `weppcloud` and `rq-engine` images were retained. After restart,
rq-engine `/health` returned HTTP 200 with `{"status":"ok","scope":"rq-engine"}`,
the direct WEPPcloud listener on port 8000 returned HTTP 200, and the Caddy
listener on port 8080 returned its expected redirect. Production was not
changed.

## Registry and Builder Profile

The authenticated Builder schema returned the complete validated registry:

- one capability component;
- four climate components;
- two delineation backends;
- two DEM components;
- one landuse, locale, and soil component;
- two watershed representations; and
- all 72 unique values from the default WEPP binary provider.

The defaults were `wbt`, `single-ofe`, and `wepp_260803`. The only Multiple OFE
tuple was `wbt | multiple-ofe | wepp_260803`, and its landuse methods were
exactly `gridded` and `upload`. The binary labels contained no legacy-parity
annotation.

`continental-us` is the only profile marked `builder_exposed`, so it is the
complete Forest profile-creation population for WP12B. Authenticated validation
returned HTTP 200 and creation returned HTTP 201 for run `matted-smooth` at:

    /wc1/runs/ma/matted-smooth/config.cfg

The materialized run records stable locale profile `continental-us`, runtime
locale token `us`, capability schema version 2, and provider revision
`5e60cccfa40a5f880179fffb4de8d9e8315c7ae3aec42dd4e0078b5a68e2272b`.
It resolved the expected defaults: USGS NED1 2024 at 30 metres, WBT, Single
OFE, `wepp_260803`, SSURGO gNATSGO 2025, NLCD 2019, and vanilla CLIGEN.

## Stored Authority and Mutation Boundary

Run-scoped pipeline, readiness, and climate, landuse, soils, WEPP, and
watershed discovery endpoints all returned HTTP 200 using a run-authorized
service principal. The returned climate relationships contained only the four
stored datasets and their valid station/spatial methods. WEPP discovery
returned all 72 stored binaries and stored tuple authority.

A direct attempt to select `australia-dynamic-landcover` returned HTTP 400 with
`unsupported_capability` and diagnostic details:

    Landuse dataset is not supported by this project.

The complete controller state, revision, ETag, and `nlcd/2019` selection were
identical before and after the request. No mutation occurred.

## Provider and Real-Execution Evidence

Every provider advertised by the sole Builder-exposed profile was checked on
the deployed host:

- both USGS DEM VRTs opened successfully through real `gdalinfo`;
- the NLCD 2019 VRT opened successfully through real `gdalinfo`;
- the gNATSGO 2025 VRT and its 2.8 GB TIFF were present;
- the Daymet v4 store was present, and the CLIGEN station database returned
  2,765 stations;
- WhiteboxTools reported version 2.4.0;
- all four TOPAZ executables were present and executable; and
- all 72 WEPP values resolved both roles: 144 role paths, 99 distinct regular
  executable files, with no missing or non-executable target.

The real GDAL SBS conversion integration test passed when invoked directly on
Forest. Direct WBT channel delineation with the fill method created `netful`,
`flovec`, and `relief` rasters of 388,294, 388,294, and 1,541,554 bytes. The
installed WBT `TopazConditionDem` integration test also passed. A direct TOPAZ
channel build created `NETFUL.ARC`, `FLOVEC.ARC`, and `RELIEF.ARC` outputs of
384,948, 384,948, and 2,114,838 bytes.

The existing `p41` model fixture was then run directly, without an executable
mock, through both `wepp_260803` watershed and hillslope role binaries. Both
returned zero and reported successful completion through 100 simulation years.
These are the representative real executions for the raster, terrain, and
model provider/method families required by WP12B. The wider contract's
per-binary Single OFE and WBT Multiple OFE project executions remain part of
WP12 production acceptance and are not claimed here.

## Validation and Disposition

Revision `3e8d0d09b` passed 533 touched Python tests, the full suite with 7,034
passed and 63 skipped, frontend lint, all 107 frontend suites and 792 tests,
stub/API checks, RQ contract checks, and five seeded suite orders. Independent
correctness, governance, and security reviews returned Ready with no unresolved
medium or high findings.

The repository-wide parallel file-isolation audit is not claimed as passing.
Every WP12B project-config and locale-authority module reported `Isolated OK`
before the tool aborted on an unrelated profile-recorder Flask stub and then
failed to serialize its own error result. This tooling defect is a nonblocking
follow-up because the WP12B scope passed focused isolation, all seeded orders,
and the full suite.

An additional direct TerrainProcessor BLC test exposed a pre-existing test
contract mismatch: the helper test requests `blc_fill=false` without requesting
fail-on-unresolved, while the diagnostics reader intentionally rejects that
unsafe combination. A direct production delineation call using BLC correctly
failed closed on the fixture with 377 unresolved depressions, and the same WBT
path completed with the fill method as recorded above. Running the GDAL test
separately passed; after the failed combined WBT invocation, process working
directory leakage caused its relative fixture to resolve through the WBT mount.
These test/isolation defects are recorded for follow-up and are not represented
as successful BLC execution. WP12 must use a suitable real project for its WBT
Multiple OFE/BLC acceptance.

WP12B Forest acceptance is **Ready**. This evidence authorizes handoff to WP12;
it does not authorize or record a production deployment.
