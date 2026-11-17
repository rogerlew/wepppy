# M2 shape-converter candidate validation

## Candidate identity

- Source revision: `e172f9f8a23c10774f87828181048c72188ba78a`.
- Local image: `wepppy/shape-converter:vector-upload-m2-final3`.
- Image ID:
  `sha256:ed4d93692add1f7cd1527ed6948353e584a213865ebcc3006b1adf84f5c62386`.
- Runtime identity: `10001:10001`.
- Resolved production posture: read-only root, `cap_drop=ALL`,
  `no-new-privileges`, 256-PID limit, 1.5 GiB memory, 1.5 CPUs, no volumes,
  isolated internal `shape-converter-sandbox`, and bounded noexec/nosuid/nodev
  tmpfs mounts (`/tmp` 384 MiB and `/run` 8 MiB).

The image is local qualification evidence only. It was not published or
deployed.

## Embedded provenance

The GeoParquet parser sidecar reports:

- binary SHA-256
  `160854839d237acb4c369bc15f97d5e51ae3841aaaca37777ba2353cfdd79c47`;
- Cargo.lock SHA-256
  `ce923427941fabe153c8b282dcfddeb1168b60670055ab34f47911d039748f13`;
- Rust `1.92.0`; and
- source revision equal to the candidate revision above.

The unchanged Shapefile parser sidecar reports binary SHA-256
`1b9b719b9b6633684addd117be01dd7754b648f0a45ab27eea644185a30b70b3`
and Cargo.lock SHA-256
`acd609c82e18c6d64fe50fb27997667d7cb5e62d720d0f76f47233f5f139b6aa`.
The real readiness GeoParquet has SHA-256
`52d6655b9f8e06b01f093670063f37bc3122e4dbaabc804c9f16bb0f9a6a0c69`.

## Direct and exact-image results

- Focused shape-converter Python suite: 19 passed.
- GeoParquet CLI: 30 locked/offline tests; strict Clippy and formatting passed.
- `/health/ready`: HTTP 200 with `geoparquet_parser: ready` and verified binary
  binding.
- Valid and projected GeoParquet inspect/convert controls returned semantic
  WGS84 artifacts with source and canonical digests matching direct readback.
- Exact-image Shapefile inspect and convert controls returned HTTP 200 with
  unchanged feature, geometry, bounds and canonical-digest semantics.
- Missing offline CRS grid returned HTTP 400 `vector_crs_invalid`; footer-size
  bomb returned HTTP 413 `vector_limit_exceeded`.
- A candidate with the GeoParquet parser removed retained HTTP 200 whole-service
  readiness with `geoparquet_parser: unavailable`, returned HTTP 503
  `vector_converter_unavailable` for GeoParquet, and continued to serve the
  Shapefile inspect control. Scratch remained empty.

The reviewed 100,000-row threshold fixture was exercised through the exact HTTP
API. Its source SHA-256 was
`47ad80848213d0da6551eab2d8905104313f524e871652474f2992662678e372`.
Readback returned 100,000 features, 10,288,931 canonical bytes, source digest
equality, and canonical SHA-256
`bbfd3260b5cb06fc097f2f1a777626db2c546d1700320b1c8153a4df863ab57d`.
Sampled container peaks were 293.2 MiB, about one CPU, 50 PIDs, nine PID-1 file
descriptors, and 16,797,373 scratch bytes; post-request scratch was empty.

Four simultaneous near-limit/hostile/valid requests produced one bounded HTTP
200 and three HTTP 503 `service_saturated` responses. A valid control immediately
after saturation returned HTTP 200 with matching source/canonical digests.
Exact executable-path and scratch readback found no parser process or scratch
entry afterward.

A real client abort at 250 ms returned curl timeout 28. The owned request
continued within the one-request admission bound, produced no response to the
disconnected client, and drained its parser/output/scratch within the observed
26-second window. A subsequent valid request succeeded. Unit coverage separately
exercises repeated task cancellation and process-group drainage. This establishes
bounded ownership and cleanup; ASGI does not promise immediate task cancellation
on a TCP client disconnect.

The full local unit suite remains affected by the pre-existing
`TestClient`/lifespan stall at
`test_cleanup_lifecycle.py::test_inspect_success_path_cleans_scratch`. Twenty-seven
preceding cases pass before the bounded run is stopped. Exact-image API controls,
including both formats, cover the shared runtime boundary without counting that
stalled run as green.

## Compose and recovery evidence

Both development and production Compose models resolve successfully with
required local path placeholders. The production model selects the exact image
tag during qualification and resolves the identity, mount, internal-network and
resource posture listed above. Production activation remains fail closed until
the operator supplies a stable `VECTOR_UPLOAD_RUN_FILESYSTEM_ID`; no deployment
was performed.

The missing-parser candidate demonstrates the format-specific disable path and
continued Shapefile availability. Restoring the exact final image restores
GeoParquet readiness and valid conversion without persisted converter state.
Rollout monitoring must assert the readiness body field, not HTTP status alone.

## SBOM and vulnerability disposition

Pinned Syft `v1.57.1` scanned a daemon-free archive of the exact image and
produced SPDX JSON:

- image archive SHA-256:
  `51482dd649745b8dc5a336acc43d5d8cfe8e7379c24b68c698cbf5ead73a910e`;
- `20261116_m2_image.spdx.json` SHA-256:
  `00fad0f0e8c143c47f78b67f6a0706f3d64e0103e4fd8217b10130445799dffa`.

Pinned Grype `v0.121.3` scanned that SBOM. The retained JSON report SHA-256 is
`a359b57d30d90cdbc9e98d06eb80f47a1aeeda281583f56f0de95eb26c163345`.
It reports 59 High, 70 Medium, 17 Low, 50 Negligible and 16 Unknown package
matches. All High matches are Debian `wont-fix` records without an available
package version. They are confined to command/library surfaces the service does
not invoke (mount/nsenter/ACL/ncurses/perl/SQLite session or FTS operations,
monetary formatting, deprecated DNS printing, or attacker-selected locale
catalogs). The runtime is non-root, read-only, capability-free, offline, and
passes a fixed minimal environment to child parsers.

Six Medium CPython records advertise fixes only in later Python branches, not a
fixed 3.12 package; the affected tar, email/URL, TLS-PSK and similar standard-
library surfaces are not used for upload parsing. The remaining Medium records
are Debian `wont-fix` or `not-fixed` entries with no available package update.
These are accepted for this local candidate under its constrained reachability;
a fresh scanner run and any available base-package updates remain mandatory
publication gates. RustSec reports no advisory for the exact GeoParquet lock.

The machine-readable SBOM and full match records are retained beside this
document so the disposition is independently inspectable rather than inferred
from package-count hashes.

## M2 disposition

The exact candidate passes local functional, provenance, containment,
near-limit, concurrency, fail-closed, recovery, supply-chain and cleanup
qualification. Independent code and security reviews pass with no High/Medium
finding. QA/operations re-review must confirm closure of its four Medium
findings. Publication, remote integration and deployment remain outside
authorization.
