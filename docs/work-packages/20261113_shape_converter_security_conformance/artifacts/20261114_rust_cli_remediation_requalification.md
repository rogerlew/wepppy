# Rust CLI remediation requalification

Date: 2026-11-14

Status: local exact-image requalification passed; independent re-review and
production rollout remain open.

## Candidate identity

- Source commit: `21a12c9d0f687b0df407458b042db17850c5c7ad`.
- Image: `sha256:ec4872021957fd5cb37b3a554537051bf5843be533dbb30276a014e328ab3921`.
- Release label: `wepppy-21a12c9d0f68`.
- Build timestamp: `2026-11-14T12:02:16-08:00`, derived from the commit.
- Debian snapshot: `20261114T120000Z`.
- Rust compiler artifact:
  `/usr/local/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc`.

Production provenance mode rejected development metadata during the image build.
The installed sidecar's Cargo.toml, Cargo.lock, and `src/main.rs` hashes exactly
match those paths at the source commit. Runtime validation recomputed the
sidecar's source-manifest digest, required the Cargo.lock entry to match the
build lock digest, bound the executable hash/size/version, and ran a real parser
fixture during startup.

## Runtime and semantic evidence

The candidate ran as UID/GID 10001, read-only root, all capabilities dropped,
`no-new-privileges`, PID limit 256, 1.5 GiB memory limit, hardened 384 MiB tmpfs,
and the dedicated internal Compose network. Readiness returned
`provenance=binary_binding_verified`. No Fiona/GDAL module or filename was found,
and the Rust binary links only the loader, libc, and libgcc.

Direct HTTP readback through the exact running image proved:

- GeoJSON: one Point at `[10.0, 20.0]` with `NAME=demo`.
- GeoParquet: one row, `NAME` and primary `geometry` columns, and GeoParquet
  `geo` metadata.
- Request scratch was empty after both conversions.

A 235,000-record fixture exercised the configured parser-payload/value boundary.
The request failed closed with HTTP 400 `invalid_shapefile`, peak cgroup memory
was 453,931,008 bytes, a competing request received HTTP 503 under the
single-flight invariant, the container was not OOM-killed, readiness immediately
returned HTTP 200, and request scratch was empty. This proves bounded rejection
and recovery near the active parser envelope; it is not a throughput claim.

## Focused validation

- Shape-converter unit/integration suite: 242 passed.
- Deploy/Compose contract suite: 47 passed, 3 environment skips.
- Single-flight/Compose focused rerun: 18 passed, 3 environment skips.
- Rust: `cargo fmt --check`, 5 tests, and clippy with warnings denied passed.
- Broad-exception changed-file enforcement and test-stub validation passed.
- ADR date validation and four scoped Markdown validations passed.
- `bash -n scripts/deploy-production.sh` passed.

The deployment contract derives parser provenance from `git rev-parse HEAD`,
requires the public readiness endpoint after activation, and on candidate failure
stops `shape-converter` and verifies no running container remains. It never
restores GDAL/Fiona, PyO3, or another unreviewed parser.

## SBOM and vulnerability evidence

Pinned Syft 1.57.1 and Grype 0.121.3 scanned the exact image using Grype database
schema v6.1.10 built `2026-11-14T06:19:25Z`.

| Artifact | SHA-256 |
|---|---|
| `20261114_rust_cli_remediation_syft.json` | `7c2fb79f74b9c8be36f5596e8c0c732f6625a263979f713bf56da0a79b78f377` |
| `20261114_rust_cli_remediation_grype.json` | `f3833e8ab21160a3e50ae0de0e0469d922215134c2bfcad5017697264ea96f64` |

The result is unchanged in substance from the independently reviewed prior base:
0 Critical, 59 High, 72 Medium, 18 Low, 50 Negligible, and 16 Unknown package
records, collapsing to 102 unique advisory IDs. The fixed zlib build remains free
of the two reachable zlib High findings. The remaining 17 unique High IDs retain
the reviewed request-path dispositions: they concern unused Perl POD/Tar,
ncurses tooling, privileged util-linux/ACL operations, system SQLite database
features, fixed-locale-unreachable libc paths, or libstdc++ APIs/allocation
preconditions not invoked by the bounded parser. These dispositions depend on
the current command, non-root/capability-free/read-only runtime, fixed child
locale, no attacker database, single-flight admission, and hard input/resource
ceilings; changing any of those assumptions requires fresh review.

## Remaining gates

No production deployment or image publication occurred. #656 remains open until
independent correctness, QA, security, and operations re-review accepts this
candidate and the operator explicitly authorizes rollout. If those gates fail,
the approved recovery is converter takedown, not an older parser fallback.
