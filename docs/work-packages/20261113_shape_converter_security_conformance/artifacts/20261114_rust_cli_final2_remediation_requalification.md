# Rust CLI final-2 remediation requalification

Date: 2026-11-14

Status: local exact-image qualification passed. Independent final re-review and
any production rollout remain open.

## Candidate identity

- Source commit: `f9b92459e6079966e429da34bcfb7c7caa432c4e`.
- Image: `sha256:c1f1e84d6beec7562fc184ab9b5ed48398bb955d938aa139768fcea7da777361`.
- Image size: 397,877,705 bytes.
- Release label: `wepppy-f9b92459e607`.
- Build timestamp: `2026-11-14T16:16:51-08:00`, derived from the commit.
- Debian snapshot: `20261114T120000Z`.
- Build used `SHAPE_PARSER_REQUIRE_RELEASE_PROVENANCE=1`; the installed sidecar
  reports the exact source commit and binds binary SHA-256
  `1b9b719b9b6633684addd117be01dd7754b648f0a45ab27eea644185a30b70b3`.

The no-mount qualification container ran as UID/GID 10001 with a read-only
root, all capabilities dropped, no-new-privileges, 256 PIDs, 1.5 GiB memory,
1.5 CPUs, bounded tmpfs, and network mode `none`. Readiness reported
`binary_binding_verified`. Fiona, GDAL, and pip were absent.

## Final re-review remediation

- Cancellation now drains the offloaded task through a shielded
  `gather(..., return_exceptions=True)`. Repeated cancellation retains ownership,
  and a late worker failure cannot replace the canonical cancellation/timeout
  outcome. Direct and HTTP 408 regressions cover the late-failure path.
- Startup, periodic, shutdown, inspect, relay-encoding, and request-cleanup
  blocking phases all run outside the sole ASGI event loop. A held periodic
  janitor leaves readiness responsive.
- Full deployments require the shape-converter service in the recreated and
  build sets independently of mutable effective build metadata. Missing service,
  missing build, altered image through dirty Compose, dirty Dockerfile-specific
  ignore data, and failed `git status` all stop/verify the converter and prevent
  build/activation. Shape takedown failure retains exit-88 precedence over CAP
  recovery failures.
- MultiPatch ring groups are aggregated into Fiona-compatible MultiPolygon
  output. Mixed triangle/ring collections put triangle surfaces first and ring
  polygons last, matching the retained oracle. Direct comparisons cover
  multiple OuterRing and FirstRing groups, InnerRing, fan, strip, and mixed
  families.
- Multipart PolylineM, PolygonM, MultiPointM, and representative MultiPatch
  families now have parsed public GeoJSON and GeoParquet coverage.
- The Dockerfile-specific ignore file is included in the release clean-input
  gate, closing the prior Low release-hygiene finding.

## Exact-image behavior

The exact image returned a one-feature Point with coordinates `[10, 20]` and
`NAME=demo` in both GeoJSON and parsed GeoParquet. A two-OuterRing MultiPatch
fixture returned one `MultiPolygon` containing two polygons in both formats;
GeoParquet retained valid `PAR1` framing. Scratch was empty after all requests.

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

- Shape-converter unit/integration suite: 296 passed.
- Deploy/Compose contract suite: 58 passed, 3 environment skips.
- Deploy execution suite alone: 49 passed.
- Rust: formatting, 5 unit tests, clippy with warnings denied, and release build
  passed.
- Broad-exception changed-file enforcement, shell syntax, and diff whitespace
  passed.

## SBOM and vulnerability evidence

Pinned Syft 1.57.1 and Grype 0.121.3 scanned the exact image. Grype used valid
database schema v6.1.10 built `2026-11-14T06:19:25Z`.

| Artifact | SHA-256 |
|---|---|
| `20261114_rust_cli_final2_remediation_syft.json` | `734057a2f8a1dc7e53b39a5580bb4f8e8282f617a961ceea6790ce28c3d21586` |
| `20261114_rust_cli_final2_remediation_grype.json` | `df0012d5eb181cac7afda38e28dcdcec9155bddd97ecbaea5fbbae7690cfb46f` |

The result remains 0 Critical, 59 High, 67 Medium, 17 Low, 50 Negligible,
and 16 Unknown package records, collapsing to 96 unique IDs. The 17 unique High
and 37 unique Medium IDs are unchanged, and no ID was added or removed. Unknown
CVE-2026-91094 requires dpkg source-package extraction, which this runtime never
invokes; its non-reachability disposition remains unchanged.

## Remaining gate

No image was published and no production deployment occurred. Independent code,
correctness, QA, operations, and security re-review must accept this exact
candidate before issue #656 or the work package can close. Rollout remains a
separately authorized action and is fail-closed.
