# Rust CLI and Final Image Qualification

Date: 2026-11-14

Scope: local implementation and production-equivalent container evidence. No
image publication or production deployment occurred.

## Candidate identity

- Image: `wepppy-shape-converter:dev`
- Image ID: `sha256:d3605b92360eaf65f8c1c2d72bac0c0d9c44a0c096776e4cb7edebbbde1fca41`
- Image size: 397,852,593 bytes
- CLI: `shape_parser_cli 0.1.0`
- CLI SHA-256: `7d688ebb09867373c513a08cbf894772b7724967a527935fdd50c05a40f8517b`
- CLI source-manifest SHA-256:
  `d1b98b009d89ac84bcf0ed5789119a5f1bcf3959aff4f14623217a1dd635561a`
- Cargo.lock SHA-256:
  `acd609a091cb2ea22de7da983b90587f55a28dc210e1e6eadfffdc97b7d078f6`
- Compiler: `rustc 1.92.0 (ded5c06cf 2025-12-08)`
- Build revision label: `19c0dc107-worktree` (the source manifest, not this
  label, identifies the uncommitted candidate content)

The adjacent `/usr/local/bin/shape_parser_cli.json` uses schema
`shape-parser-binary-provenance-v1`. Build validation and runtime readiness
verified its executable name, size, SHA-256, and version. Tamper tests alter the
binary and prove both standalone and runtime validators reject the pair. This
sidecar is image-internal provenance, not a signature.

## Parser and resource evidence

Locked Rust gates passed: `cargo fmt --check`, 5 Rust unit tests,
`cargo clippy --all-targets -- -D warnings`, release build, and RustSec audit
against 1,509 advisories. The dependency evaluation records 30 locked packages,
licenses, unsafe surface, and the 50,000-feature benchmark.

Direct tests cover valid Point, LineString, Polygon, numeric UTF-8 CPG labels,
counterclockwise rings, Z/null geometry and attributes, MultiPatch, integer/
float/date values, disguised input, and feature/vertex limits. A deterministic
mutation corpus covers invalid magic, declared length, SHX count, DBF count/
record length, and non-finite bounds. The corpus found the declared-length gap;
the CLI now validates both SHP and SHX headers before crate parsing.

Behavioral probes produced no final or temporary output:

| Control | Probe result |
|---|---|
| input bytes | exit 1 before parse publication |
| output/FSIZE bytes | exit 3; atomic temporary removed |
| open files | exit 1 with `RLIMIT_NOFILE=3` |
| feature count | dedicated exit 4 |
| vertex count | dedicated exit 5 |
| address space | 50,000-feature fixture with 16 MiB limit aborted, exit 134, no output |
| CPU | 500,000-feature fixture with one-second limit killed, exit 137, no output |
| wall time/process group | timeout regression sends SIGTERM then SIGKILL and returns canonical 408 |
| core dumps | `RLIMIT_CORE=0` is applied before hostile parsing |

The normal 50,000-feature fixture completed in 0.21 seconds with 84,096 KiB
peak RSS and matched the normalized Fiona oracle. Resource numbers describe this
host only; the pass condition is limit enforcement and semantic equivalence.

## API/image evidence

The exact container readiness payload was:

```json
{"check":"ready","parser":"shape_parser_cli","provenance":"verified","scope":"shape-converter","scratch_root":"/tmp/shape-converter","status":"ok"}
```

Readiness generated and parsed a real fixture through the installed CLI and
strict JSON decoder, then cleaned it. Direct HTTP conversion of the final image
returned semantically parsed GeoJSON and GeoParquet with Point coordinates
`[10.0, 20.0]`, property `NAME=demo`, one Parquet row, and valid GeoParquet
primary-column metadata. Request scratch was empty afterwards.

Runtime inspection proved `importlib.util.find_spec("fiona") is None` and no
case-insensitive Fiona/GDAL filename under `/usr/local`, `/usr/lib`, or
`/opt/venv`. The removed `convert_parser_worker.py` has no production fallback;
Fiona remains only in retained test/oracle history.

## SBOM and vulnerability evidence

Syft 1.57.1 cataloged 109 artifacts. Grype 0.121.3 used valid database schema
`v6.1.10`, built `2026-11-14T06:19:25Z`. Complete reports are checked in:

| Artifact | SHA-256 |
|---|---|
| `20261114_rust_cli_syft.json` | `13a7b489b2c989f28687a7e6ffadadc32dc2b7d876dd59ebf21634e9a50b5a73` |
| `20261114_rust_cli_grype.json` | `431fa62cb14155925658418fffa4bff403200761b30a87a7f9471e1fc590932f` |

Grype reports 0 Critical, 59 High, 72 Medium, 18 Low, 50 Negligible, and
16 Unknown package records, collapsing to 102 unique advisory IDs. Two zlib
High findings were reachable through ZIP/serialization dependencies and had a
fixed Debian build; the image now pins
`zlib1g=1:1.3.dfsg+really1.3.1-1+deb13u1`, and those findings are absent.

The remaining 17 unique High IDs are duplicated across package records. Their
described paths are outside the service behavior:

- ncurses `infocmp`, Perl POD/Archive::Tar, util-linux mount/nsenter hooks, and
  privileged ACL pathname operations are never invoked; the service is non-root,
  capability-free, read-only, and launches only Uvicorn and the fixed CLI.
- system SQLite FTS5/session operations are not used; the service opens no
  attacker database. PyProj's fixed database is separate wheel content.
- glibc findings affect `strfmon`, deprecated DNS printers, or attacker-selected
  `LANGUAGE`; the CLI receives only fixed `LC_ALL=C` and `LANG=C`.
- libstdc++ findings affect priority-queue `erase_if` or integer-overflow-sized
  aligned allocations. No such API is called on Shapefile bytes, and absolute
  input, feature, vertex, memory, output, and wall/CPU limits preclude the stated
  enormous-allocation precondition in conversion libraries.

These are request-path non-reachability dispositions, not claims that the base
packages are vulnerability-free. A future command invocation, database input,
locale passthrough, privilege change, or unbounded native allocation invalidates
the applicable disposition. Independent security signoff remains required.

## Validation receipt

- 193 focused unit/integration tests passed before the final DBF/header additions.
- 17 focused Rust/parser semantic tests then passed, followed by the final
  change-scoped rerun recorded in the QA review.
- Docker Compose config resolves the one-worker command, provenance build args,
  fixed resource variables, read-only root, dropped capabilities, non-root user,
  PID/memory/CPU limits, hardened tmpfs, and internal network in dev and prod.
- `tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
  passed with net delta zero.
- `wctl check-test-stubs` passed.

No full repository suite was run, per the package's explicit validation scope.
