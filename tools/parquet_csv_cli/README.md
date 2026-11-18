# Native Parquet CSV conversion

The Rust CLI is the required browse/download CSV backend. Its asynchronous Python
supervisor lives in `wepppy/microservices/parquet_csv/`; HTTP ownership lives in
`wepppy/microservices/browse/parquet_csv.py`. The old Python serializer is retained
only as `oracle.py` for controlled evaluation. There is no production fallback.

## Contracts

The [integration contract](../../docs/schemas/parquet-csv-integration-contract.md)
defines protocol v2, compatibility, fixed paths, error mappings and retention.
[ADR-0149](../../docs/adrs/ADR-0149-parquet-csv-integration-resource-envelope.md)
defines resource budgets. Every source is untrusted, including WEPPpy outputs.
All schema decoding and filter execution occur in the bounded child.

CSV is generated on demand and removed after serving or safe failure cleanup.
It is not a persistent model output: saved server-side copies could become stale
or imply automatic generation. Original project Parquet remains downloadable.

## Build and evaluate

The common production and development Dockerfiles build the locked executable,
install its provenance/source inventory, and require no CSV environment settings.
For local native tests, from the repository root with Rust1.92 and Python3.12:

```bash
cargo build --release --locked --manifest-path tools/parquet_csv_cli/rust/Cargo.toml
cargo test --locked --manifest-path tools/parquet_csv_cli/rust/Cargo.toml
wctl run-pytest tools/parquet_csv_cli/tests/test_converter.py
```

Tests explicitly inject the locally built binary, source root and private scratch.
Production fixes them to `/usr/local/bin/parquet_csv_cli`, `/opt/parquet-csv/`
and `/tmp/wepppy-parquet-csv`. Binary/source/provenance mismatch is an explicit
failure; runtime does not compile, download or search for another backend.

The evaluator `benchmark.py` accepts a controlled corpus and output directory.
Its Python/native-PyArrow comparators are test oracles, not safe service backends.
The generated `rust/src/lowercase.rs` freezes simple Unicode lowercase from the
pinned DuckDB1.1.1 filter oracle. Regenerate with `generate_lowercase.py`, then
`cargo fmt`; do not silently adopt a newer Unicode table.

## Ownership and operations

Two persistent flock slots are shared across all browse workers in one container.
Children inherit the slot descriptor; independent wall alarms and parent-death
termination prevent lost supervision. Fixed per-slot directories are reclaimed
only after acquiring the corresponding lock. Never unlink lock files or remove
a directory owned by a live conversion/response. The slot remains occupied while
a slow client consumes its completed CSV, up to the serving deadline.

Busy requests return503 with Retry-After. Typed input/filter/resource errors,
timeouts and missing provenance produce explicit responses; authorized raw
Parquet remains available. Correlated logs identify outcomes and resource metrics
without rows, credentials or filter values. Failed cleanup is reported explicitly.

Before release activation, `docker/validate-parquet-csv-runtime-contract.sh IMAGE`
checks installed provenance, actual native CSV bytes, eight-worker HTTP delivery,
raw-file availability and private-project denial under the candidate identity.
The canonical `scripts/deploy-production.sh` invokes this gate before stopping
services. Rollback is a whole-release operation through the canonical deployment
workflow, never a CSV environment switch. Package validation does not deploy.

Integration tests use an explicitly built local release binary, or the matching
installed native artifact from `docker/Dockerfile.test`. The test fixture compares
the installed source inventory with the checkout and fails on drift; rebuild the
test image after native changes. No Python serializer substitutes for the child.
