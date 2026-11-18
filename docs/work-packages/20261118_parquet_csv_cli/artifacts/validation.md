# Validation and artifact identity

Scope: isolated standalone evaluation; no production imports, routes, data, images
or orchestration changes. Final canonical receipt and broad-suite disposition are
recorded below by the integrator before closeout.

## Build and focused tests

Toolchain: rustc/cargo 1.92.0 on Linux x86-64. Commands:

```bash
cargo build --release --locked --manifest-path tools/parquet_csv_cli/rust/Cargo.toml
cargo fmt --manifest-path tools/parquet_csv_cli/rust/Cargo.toml -- --check
cargo clippy --locked --manifest-path tools/parquet_csv_cli/rust/Cargo.toml -- -D warnings
cargo test --locked --manifest-path tools/parquet_csv_cli/rust/Cargo.toml
wctl run-pytest --checkout /home/workdir/wepppy-parquet-csv-cli-package --profile python -- tools/parquet_csv_cli/tests -q
```

Final task checkout: 13 Rust tests and 94 Python tests passed; Rust formatting
and Clippy passed. `rust-tests.txt` and `exploratory-tests.txt` retain output. The
exploratory Python run used 3.12.3; the canonical container uses Python 3.12.16.
The earlier canonical 57-test receipt was an intermediate candidate and is not
relabeled as final evidence. `binary-provenance.json` and `source-inventory.json`
supplement wctl fingerprints, which do not cover the Rust sources/ignored binary.

Final canonical receipt: `.wctl-test-runs/f32a93cf14ef4442bac54f4021277570/receipt.json`;
94 passed in 7.92 seconds, Python 3.12.16, UID 1000/GID 993; no source or runtime
drift. `focused-receipt-summary.json` retains the receipt identity and checks.
Final rebuilt binary SHA-256:
`2efd194f5842f668687b58659337598b5d3b868151fc12f0d3b837b9313a8b37`,
4,400,000 bytes. The task-checkout rebuild and regenerated full provenance exactly
match the evaluated temporary build and all Rust source hashes.

Two final inline comments label already-reviewed BaseException ownership/cleanup
boundaries for the repository exception checker. They change no Python AST or
runtime behavior; final source inventory includes them. The final benchmark runner
also retains failed-worker stderr rather than discarding it. Source review
amendments retain the actual code fixes and their before/after identities.

## Broad repository gate

Command against frozen task source and the existing read-only runtime:

```bash
wctl run-pytest --checkout /home/workdir/wepppy-parquet-csv-cli-package \
  --runtime-root /home/workdir/wepppy \
  --shape-parser /tmp/vun-final4-binaries/shape_parser_cli \
  --geoparquet-parser /tmp/vun-final4-binaries/geoparquet_parser_cli \
  -- tests --maxfail=1
```

Receipt `.wctl-test-runs/167a933af0424a67a9268c42c92392a8/receipt.json`:
Operator-deferred and stopped by SIGINT after 10,097 passed, 497 skipped and
99 deselected. The signal hit an installed RQ worker handler, raising StopRequested
inside an active Rosetta/DuckDB query; pytest recorded one `Query interrupted`
failure in `test_actual_treatment_rejects_density_changes_or_invalid_values[True]`.
This is cancellation-induced, not an observed pre-cancellation test regression.
The wrapper receipt status is `failed`, exit 1; preserve that raw status rather
than calling the full suite passed. Source/runtime changes were both empty.
Per the operator's latest instruction, broad pytest is deferred until integration
and will not be rerun for this standalone package.

Preflight verified controllers, browser dependencies, both parser
identities and database columns; UID 1000/GID 993. An earlier attempt failed
before pytest because parsers were unavailable; the explicit compatible borrowed
binaries resolved that prerequisite. Nothing was deployed or remounted in the
shared running services. The selected suite collected 15,115 tests, deselected 99,
and skipped one at collection (15,016 selected).

The broad checkout stayed unchanged during execution. Final standalone fixes were
prepared in `/tmp/parquet-csv-next` and transferred only after the receipt completed.
The production `wepppy/`, `tests/` and `docker/` trees are byte-unchanged from base
`dff2f29f74158857da3b0c313e7ec7194501ed76`. Final focused validation covers the
isolated tools delta. A broad failure must remain visible; it is not a green gate.

## Generated artifacts and resource evidence

The immutable three-file corpus manifest links source paths, sizes, hashes and
schemas. `binary-provenance.json` links the executable to Rust source and lock.
The harness stages the exact regular input, checks identity and hashes the consumed
snapshot. Fresh output hashes match the Python oracle in every final repetition.
`readback-results.json` independently parses all output rows, headers and field
counts and compares first/last values to the Arrow projection. No database state,
exit code or file-existence check substitutes for content readback.

`benchmark-summary.json` verifies the predeclared 2x and 512 MiB thresholds for
all three files. `lifecycle-results.json` records CPU, staging, wall and output
limits, cleanup, concurrent large files and retained-artifact admission. Real
/dev/full, FIFO, symlink, external-column inotify, disappearing /proc descriptor,
input mutation and process cancellation tests exercise actual boundaries.
Permission/cleanup denial injection is labeled in tests; no full-filesystem or
uninterruptible-kernel-wait claim is made.

## Independent reviews and final disposition

Source correctness and security verdicts pass, with all medium/high findings
closed and final amendments retained. These are independent agent reviews, not
human GitHub approvals. No separate production UI/QA gate applies to this isolated
CLI; canonical focused tests and artifact readback supply executable validation.

Integrator final acceptance: standalone go. Final canonical tests, exact rebuilt
binary/source provenance, three-way benchmarks, real lifecycle probes and CSV
readback satisfy the independent source reviews' validation conditions. Broad
pytest is deferred by explicit operator instruction until integration.
Documentation lint passed on the package, contract, dependency registry, README
and project board. Changed-file exception enforcement passed (five Python files,
no unsuppressed broad catches). Rust formatting and Clippy with warnings denied
passed. Source-only commit identity is attached in closeout. Remote integration,
publication and deployment: not performed.

## Observe-only tooling and spelling

Code-quality observability ran successfully in observe-only mode. Its configured
production scan excludes this tools subtree, so it reported no analyzable changed
production files; radon was unavailable. This is not a cyclomatic-complexity pass
for the new tool. No unrelated production hotspot refactor was attempted.
Spelling previews were reviewed; existing project-board terminology and the valid
word "oversized" were retained. Final staged whitespace checks passed.
