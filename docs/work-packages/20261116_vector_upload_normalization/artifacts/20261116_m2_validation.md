# M2 shape-converter candidate validation

## Candidate identity

- Source revision: `0e58feced8ec5a0274bc38113a55b73b84572dc9`
- Local image: `wepppy/shape-converter:vector-upload-m2`
- Image ID: `sha256:d131f3df03a12083c138c0ebc65a4576390d90c3ad80352f62a041405b102df4`
- Runtime identity: `10001:10001`
- Runtime posture: read-only root, `cap_drop=ALL`, no-new-privileges,
  128-PID limit, 512 MiB memory limit, one CPU, bounded noexec/nosuid/nodev
  tmpfs. The local API qualification used loopback publication only.

The image was built with release label `vector-upload-m2`. It is local
qualification evidence only; it was not published or deployed.

## Embedded provenance

The GeoParquet parser sidecar reports:

- binary SHA-256
  `160854839d237acb4c369bc15f97d5e51ae3841aaaca37777ba2353cfdd79c47`;
- Cargo.lock SHA-256
  `ce923427941fabe153c8b282dcfddeb1168b60670055ab34f47911d039748f13`;
- source manifest SHA-256
  `89e340623bf2ed740cc119c183e0e2fba2b4112977088b20e49ee62cb9b2e920`;
- Rust `1.92.0`; and
- source revision equal to the candidate revision above.

The unchanged Shapefile parser sidecar reports binary SHA-256
`1b9b719b9b6633684addd117be01dd7754b648f0a45ab27eea644185a30b70b3`
and source manifest SHA-256
`666011b8cc98c9926fd697cd7b63944b0a52ddc8ef2fc0afe76e5c75ffdb5ac3`.
The real readiness GeoParquet has SHA-256
`52d6655b9f8e06b01f093670063f37bc3122e4dbaabc804c9f16bb0f9a6a0c69`.

## Direct and exact-image results

- `pytest -q tests/shape_converter/unit/test_geoparquet_input.py`: 7 passed.
- `cargo test --locked --offline`: 30 passed.
- strict clippy and `cargo fmt --check`: passed.
- `/health/ready`: HTTP 200 with `geoparquet_parser: ready` and
  `provenance: binary_binding_verified`.
- Valid polygon GeoParquet: HTTP 200, one polygon, correct bounds, source
  SHA-256 equal to the uploaded 361-byte file, and canonical SHA-256
  `e04e107a7c783aa263172fc22d1e63d97813f79ec40ca605a0ead0fa0f532797`.
- Projected EPSG:32611 GeoParquet: HTTP 200 and artifact readback at
  approximately `[-116, 44]` in WGS84.
- Inspecting `.geoparquet`: HTTP 200 with the same feature count, bounds,
  source digest, and canonical digest as conversion.
- A CRS requiring an unavailable offline grid: HTTP 400
  `vector_crs_invalid`; no ballpark transformation was accepted.
- Footer-size bomb: HTTP 413 `vector_limit_exceeded`.
- Scratch readback after all requests: no entries under
  `/tmp/shape-converter`.
- Idle post-request runtime readback: 41.5 MiB of the 512 MiB limit and 49
  processes/threads of the 128 PID limit.

These are response-artifact and filesystem readbacks, not job-success or file-
existence claims.

## Dependency inventory and advisory evidence

`cargo audit` refreshed 1,509 RustSec advisories and reported no vulnerability
for the exact 64-package GeoParquet Cargo.lock. Exact package inventories were
captured from the candidate runtime and locked Rust graph:

- Rust tree: 46 lines, SHA-256
  `7ff2e198354765cabc9bbac1ebe270b937d6af8ce2fc2b666c94ee54d71e5d7d`;
- Debian packages: 87 lines, SHA-256
  `dc361cbf267d6765cc5cbada311632dc02565dbc6bbd21224f0f56704a6e73d1`;
- Python distributions: 14 lines, SHA-256
  `14d6731af353942c059eb6cedf4c4884efb68938391f1fadb294815b1b3180a1`.

The installed Docker CLI has no `docker sbom` plugin and no local Syft, Grype,
or Trivy executable. The explicit three-ecosystem inventories are the retained
local substitute; a publication pipeline SBOM/vulnerability gate remains a
separate rollout prerequisite.

## M2 disposition

The committed shape-converter candidate passes local M2 functional, provenance,
containment, hostile-input, CRS, and cleanup qualification. Independent code,
security, and QA/operations review is still required before M2 is closed. Image
publication, remote integration, and deployment remain outside authorization.
