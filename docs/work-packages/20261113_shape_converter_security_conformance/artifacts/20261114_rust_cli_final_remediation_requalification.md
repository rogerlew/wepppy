# Rust CLI final remediation requalification

Date: 2026-11-14

Status: local exact-image qualification passed. Independent re-review and any
production rollout remain open.

## Candidate identity

- Source commit: `ec1916b23971b13a4ba8158e68433e31b4230dce`.
- Image: `sha256:196e83b85b1c88e09999de481fdfc3aee03893e58f751ea6146c9776a99bb5bb`.
- Image size: 397,876,763 bytes.
- Release label: `wepppy-ec1916b23971`.
- Build timestamp: `2026-11-14T15:53:41-08:00`, derived from the commit.
- Debian snapshot: `20261114T120000Z`.
- Build used `SHAPE_PARSER_REQUIRE_RELEASE_PROVENANCE=1`; the installed sidecar
  reports the exact source commit and binds binary SHA-256
  `4e1fcfcac21b3cca5ac94969979d5fbeeb2910262dfdc58a8ccb6aeaa7292c26`.

The no-mount qualification container ran as UID/GID 10001 with a read-only
root, all capabilities dropped, no-new-privileges, 256 PIDs, 1.5 GiB memory,
1.5 CPUs, bounded tmpfs, and network mode `none`. Readiness reported
`binary_binding_verified`. The Rust executable linked only libc, libgcc, and the
loader. Fiona and pip were absent.

## Closed re-review blockers

- Inspect extraction, relay JSON encoding, and material scratch cleanup now run
  outside the sole ASGI event loop. Held-phase regressions prove readiness
  remains responsive.
- Repeated task cancellation is deferred until the offloaded thread exits, so
  admission and scratch ownership cannot be released while blocking work is
  still active.
- Provenance or clean-input failure now invokes the same fail-closed takedown as
  later deployment failures. A failed stop or failed state query returns the
  distinct exit 88. Production Compose definitions are included in the clean
  input set.
- Rust preflight enforces declared MultiPoint and multipart vertex counts before
  crate allocation, including DBF-deleted rows.
- Homogeneous FirstRing/Ring, OuterRing/InnerRing, TriangleFan, and
  TriangleStrip MultiPatch records now match retained Fiona geometry shape.
- The public GeoJSON and GeoParquet matrix now parses MultiPointM, multipart
  PolygonM, and homogeneous MultiPatch artifacts; direct Rust/Fiona comparisons
  cover the same representative families.
- CP1250 LDID `0xC8`, InnerRing, exact resource signals, and corrected base64
  advisory reachability are retained as regression/evidence coverage.

## Exact-image behavior

The exact image returned a one-feature GeoJSON Point with coordinates
`[10, 20]`, `NAME=demo`, metadata feature count one, and bounds
`[10, 20, 10, 20]`. PyArrow/Shapely parsed the GeoParquet response as one Point
row with the same coordinates and property, a present CRS, and valid `PAR1`
framing. Scratch was empty after both requests.

A retained 235,000-record request was paused only for observation. While the
Rust child remained active, readiness returned 200 and a competing conversion
returned 503 `service_saturated`. After continuation, the request failed with a
bounded 400 `invalid_shapefile`; the container stayed healthy and scratch was
empty. Live child limits were:

| Limit | Effective soft/hard value |
|---|---|
| Core file | 0 bytes |
| Address space | 402,653,184 bytes |
| CPU time | 60 seconds |
| File size | 16,777,216 bytes |
| Open files | 32 |

## Validation

- Shape-converter unit/integration suite: 281 passed.
- Deploy/Compose contract suite: 52 passed, 3 environment skips.
- Focused remediation matrix: 173 passed.
- Rust: formatting, 5 unit tests, clippy with warnings denied, and release build
  passed.
- Broad-exception changed-file enforcement, test-stub validation, shell syntax,
  diff whitespace, and package documentation lint passed.

## SBOM and vulnerability evidence

Pinned Syft 1.57.1 and Grype 0.121.3 scanned the exact image. Grype used valid
database schema v6.1.10 built `2026-11-14T06:19:25Z`.

| Artifact | SHA-256 |
|---|---|
| `20261114_rust_cli_final_remediation_syft.json` | `e808c58c0193f846788b1b4150c2f097b65f523e325c53b68c86af0c659c006a` |
| `20261114_rust_cli_final_remediation_grype.json` | `f046d9c11afc5ea8785837dbcf468f2d0721fe2b2c022676ffb7ce3afc32b1d6` |

The result is 0 Critical, 59 High, 67 Medium, 17 Low, 50 Negligible, and
16 Unknown package records, collapsing to 96 unique IDs. The 17 unique High and
37 unique Medium IDs are unchanged from the prior qualified candidate. The
newer database adds one Unknown ID, CVE-2026-91094, against runtime `dpkg`; its
described path requires unpacking an attacker-controlled Debian 3.0 quilt source
package. The runtime never invokes dpkg, accepts only bounded ZIP uploads, and
launches only Uvicorn and the fixed Rust parser, so that path is not reachable.
This is a request-path disposition, not a claim that dpkg is vulnerability-free.

## Remaining gate

No image was published and no production deployment occurred. Independent code,
correctness, QA, operations, and security re-review must accept this exact
candidate before issue #656 or the work package can close. Rollout, if later
authorized, remains fail-closed: an unqualified candidate leaves the converter
stopped and never restores GDAL/Fiona.
