# Rust CLI second remediation requalification

Date: 2026-11-14

Status: local exact-image qualification passed. Independent re-review and any
production rollout remain open.

## Candidate identity

- Source commit: `be7848eb75804bb7b021427b26a3466b52f3a3b7`.
- Image: `sha256:553a8a1c00468cdc28cc78bb98ef47382e6179be33a55b5c026d6605e7ff39a8`.
- Release label: `wepppy-be7848eb7580`.
- Build timestamp: `2026-11-14T15:24:26-08:00`, derived from the commit.
- Debian snapshot: `20261114T120000Z`.
- Build used `SHAPE_PARSER_REQUIRE_RELEASE_PROVENANCE=1`; the installed sidecar
  reports the exact source commit and binds binary SHA-256
  `060620803977c7e3743359f472c4e8b8f5b4594806598994673a8d86f5c80289`.

The no-mount qualification container ran the exact image as UID/GID 10001,
read-only, all capabilities dropped, no-new-privileges, 256 PIDs, 1.5 GiB
memory, 1.5 CPUs, bounded tmpfs, and network mode `none`. Readiness reported
`binary_binding_verified`. The Rust executable linked only libc, libgcc, and the
loader. Fiona and pip were absent from the final runtime.

## Closed re-review blockers

- Blocking conversion phases execute off the ASGI event loop. Cancellation of
  an offloaded phase retains scratch and single-flight ownership until its
  thread exits. A held conversion left readiness responsive and rejected a
  competing conversion with 503.
- Startup rejects unsafe effective overrides and requires global/per-client
  in-flight limits of one.
- Rust applies core, address-space, CPU, file-size, and open-file limits before
  hostile path/record traversal. Feature scanning stops at the ceiling.
- Independent pre-parser validation now rejects malformed multipart part tables.
  The added regression first reproduced silent point loss when part zero began
  at offset one.
- The semantic matrix now directly covers MultiPoint and M variants, multipart
  line/polygon, logical and supported-LDID DBF values, deleted rows, and
  FirstRing/Ring/TriangleFan/TriangleStrip MultiPatch policies.
- Retained 50,000- and 235,000-record generators exercise address-space and CPU
  exhaustion without publishing output. A parser abort returned a bounded 400,
  left readiness at 200, and created no core or partial artifact.
- Fault-injected deployment tests prove readiness failure stops and verifies the
  converter, suppresses prune/success, preserves unrelated services, and returns
  a distinct failure when takedown itself fails. Release builds reject dirty
  relevant inputs even under `--skip-pull`.

## Exact-image behavior

The no-mount candidate returned a valid one-feature GeoJSON Point with
`NAME=demo`, metadata feature count one, and bounds `[10, 20, 10, 20]`; request
scratch was empty afterwards. The same image also returned a 2,435-byte
GeoParquet artifact. Independent PyArrow/Shapely readback confirmed one row,
Point coordinates `[10, 20]`, `NAME=demo`, a present CRS, feature count one,
and bounds `[10, 20, 10, 20]`; `PAR1` framing was also present.

A retained 235,000-record request exercised the active aggregate envelope. While
it ran, readiness returned 200 and a competing conversion returned 503
`service_saturated`. The first request failed closed with 400
`invalid_shapefile`; the container remained healthy and scratch was empty. A
live `/proc` observation of its Rust child reported:

| Limit | Effective soft/hard value |
|---|---|
| Core file | 0 bytes |
| Address space | 402,653,184 bytes |
| CPU time | 60 seconds |

## Validation

- Shape-converter unit/integration suite: 264 passed.
- Deploy/Compose contract suite: 50 passed, 3 environment skips.
- Rust: formatting, 5 unit tests, clippy with warnings denied, and release build
  passed.
- Broad-exception changed-file enforcement and test-stub validation passed.
- `bash -n scripts/deploy-production.sh` passed.
- Changed specification and evidence Markdown validation passed.

## SBOM and vulnerability evidence

Pinned Syft 1.57.1 and Grype 0.121.3 scanned the exact image with valid Grype
database schema v6.1.10 built `2026-11-13T15:40:34Z`.

| Artifact | SHA-256 |
|---|---|
| `20261114_rust_cli_second_remediation_syft.json` | `6e8a64a7219f2b6f832490b7ae5d8b7f9923fb07730dbf229f20845e51c5795b` |
| `20261114_rust_cli_second_remediation_grype.json` | `81c023b8927bc6d48e1c8c2a3f7ab09aabbc05794524c2817c72a4b3ca2c7129` |

The result is 0 Critical, 59 High, 67 Medium, 17 Low, 50 Negligible, and
15 Unknown package records, collapsing to 95 unique IDs. There are 37 unique
Medium IDs. Removing runtime pip eliminated all five pip Medium advisories plus
two lower-severity pip advisories; the scan added no ID. Every remaining Medium
ID has an explicit request-path disposition in
`20261114_rust_cli_medium_advisory_dispositions.md`. The prior 17 unique High
IDs retain their independently reviewed non-reachability assumptions; a changed
command, parser linkage, input type, privilege, mount, locale, or service role
invalidates that disposition.

## Remaining gate

No image was published and no production deployment occurred. Independent code,
correctness, QA, operations, and security re-review must accept this exact
candidate before issue #656 or the work package can close. Rollout, if later
authorized, remains fail-closed: an unqualified candidate leaves the converter
stopped and never restores GDAL/Fiona.
