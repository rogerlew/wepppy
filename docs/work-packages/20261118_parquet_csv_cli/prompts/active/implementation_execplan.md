# Evaluate a bounded Rust Parquet CSV CLI and Python harness


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective
current together with the package tracker. Execution was authorized by the operator after scaffold commit 11ace80c8.
Implementation remains gated on the M0 ancestor and independent reviews.

## Purpose / Big Picture


Produce an independently usable Rust converter and asynchronous Python process
harness whose correctness, resource bounds and performance can be demonstrated
without a running WEPPpy application. The operator wants evidence before any
integration. Successful evaluation ends in a go/no-go handoff, not route wiring.

## Progress


- [x] (2026-11-18 18:13 UTC) Scaffold scope, draft contract, checkpoint and plan.
- [x] (2026-11-18 UTC) M0: Ratified contract/ADR and conditionally accepted dependency selection; two independent reviews closed.
- [ ] M1: Build standalone CLI and prove fresh generated-output parity.
- [ ] M2: Build standalone harness and prove resource/lifecycle behavior.
- [ ] M3: Benchmark current Python, native PyArrow and Rust plus harness.
- [ ] M4: Independent reviews, decision and deferred-integration handoff.

## Surprises & Discoveries


The existing exporter reads Arrow batches but converts them with `to_pylist()`,
formats cells in Python and retains a complete StringIO plus encoded CSV bytes.
A native streaming writer is therefore an essential comparison baseline. Existing
GeoParquet dependency approval is narrow and conditional; adding Arrow support
or codecs is a new evaluated graph. Production browse has eight workers, so a
per-worker limit is not a host-wide concurrency bound.

## Decision Log


2026-11-18, operator/Codex: scaffold a contract-first standalone Rust CLI and
Python harness evaluation. Defer all WEPPpy integration, even if evaluation passes,
to a separately authorized successor. This avoids committing runtime changes
before the candidate proves useful. Use a synchronous CLI and asynchronous Python
supervision; no Rust async runtime is needed for bounded local file conversion.

## Outcomes & Retrospective


M0 concrete contract, resource ADR, dependency probe and baseline measurements
are in progress. No CLI/harness implementation or runtime integration exists yet.
Scaffold completion must not be reported as implementation completion.

## Context and Orientation


The baseline is `wepppy/microservices/browse/_download.py`, especially
`download_response_file` and `_parquet_file_to_csv_bytes_with_schema`, and
`wepppy/microservices/browse/parquet_tables.py`, especially index projection,
units labels and `_format_csv_cell`. Filtered exports first materialize a table;
archived exports use a file-like input. Inventory both before declaring parity.
The shape-converter lifecycle lives in
`wepppy/microservices/shape_converter/convert.py`: subprocess process groups,
minimal environment, bounded IPC, timeout, cancellation drainage and cleanup.
Its resource assumptions are precedent, not transferable CSV defaults.

Use `docs/schemas/parquet-csv-cli-contract.md` as the draft durable contract and
this package's `artifacts/20261118_contract_decision.md` as the pending checkpoint.
Starting source revision is `dff2f29f74158857da3b0c313e7ec7194501ed76`.
Read nearest AGENTS before future code edits. Proposed isolated evaluation root
is `tools/parquet_csv_cli/`, with `rust/`, `harness/`, `tests/` and benchmark
support; M0 must finalize placement without importing it into production modules.

## Plan of Work


### M0: Ratify the contract before implementation


Inventory inputs using retained read-only project copies, with immutable manifests
and hashes; do not stress production. Record schema/type/codec coverage and valid
absent, empty, populated, legacy and malformed states. Extract oracle behavior
from the baseline revision and identify discrepancies explicitly. Specify exact
CLI argv, versioned diagnostics/result schema, exit codes, output publication,
source immutability and error behavior in the standalone contract. Fix numerical
latency/memory acceptance and a resource ADR before candidate benchmarking, using
baseline workload measurements to avoid limits that exclude legitimate exports.
Evaluate the minimal dependency graph against the existing conditional Parquet
precedent; resolve allocation and codec requirements rather than copying its lock.

Obtain explicit operator approval of the concrete contract and two independent
read-only reviews with dispositions. Retain them and the amended contract/ADR in
a standalone ancestor commit. Record its full SHA in tracker; implementation
cannot start without it. The subsequent operator instruction to implement the package supplies authority
for bounded standalone choices; both independent reviews must verify that scope. M0 passes when all contract decisions and acceptance thresholds are
resolved and the checkpoint ancestry is verifiable.

### M1: Implement and validate the standalone CLI


Create the isolated Rust crate, locked dependency graph and provenance mechanism.
Read authorized local Parquet inputs in bounded batches and write a private CSV
file incrementally. Never convert rows through Python or return the complete CSV
in IPC. Establish memory/CPU/file/output bounds before decoder work and retain
allocation preflight required by dependency review. Preserve the ratified CSV
semantics. Publish success only after complete output finalization; failures must
not expose partial output as success or overwrite unrelated files.

Build fresh artifacts and read generated CSVs independently. Cover nulls, NaNs,
precision, timestamps, quoting, Unicode, units, index metadata, zero rows, legacy
inputs and every supported codec/type. Explicitly disposition filtered and archived
inputs; no silent fallback or claim that unsupported variants are integrated.
M1 passes on exact-binary generated-content evidence, not compile success.

### M2: Implement and validate the standalone Python harness


Implement asynchronous launch without a shell, minimal inherited environment,
private scratch, explicit admission, bounded diagnostics and result parsing.
The CLI remains a synchronous child. Kill and reap the owned process group on
wall timeout, cancellation or fatal error, including repeated cancellation and
cancellation during startup/cleanup. Hold admission until children are reaped.
The harness must not import Flask or require Redis, Postgres or live run state.

Use actual child processes and files to test CPU/memory/output exhaustion,
missing binary, invalid provenance, malformed IPC, source changes, denied paths,
disk exhaustion, output collisions and cleanup. Cover both valid large exports
and hostile allocation requests. Demonstrate the declared aggregate scope of
admission across harness callers; do not label an in-process semaphore a global
limit. Produce artifacts and bounded machine-readable metrics, not HTTP responses.

### M3: Measure the complete conversion boundary


Benchmark the original Python exporter, incremental native PyArrow CSV, and the
Rust CLI through its Python harness on the same retained inputs and host. Include
small and large real project examples such as channels, H.wat, chnwb and event
Parquet files; select exact cases from observed inventory rather than filenames
alone. Include codec variants, cold/warm reads, concurrent jobs, repeated requests,
cancellation and oversized hostile metadata. Keep fixture generation outside
measured conversion time; include launch, decoding, writing and finalization.

Retain raw repetitions, source/binary/harness identities, environment, cache
conditions, wall/CPU time, peak whole-process-tree memory, output/scratch bytes,
row counts and independent CSV parity. Report medians and tails with sample
counts; do not infer peak memory from end-minus-start RSS. Apply M0 thresholds
without relaxing them after seeing candidate results. Failure produces no-go
or a bounded follow-up proposal, not an automatic C++ rewrite or service redesign.

### M4: Review and hand off a go/no-go decision


Create independent correctness and security artifacts from the repository
templates. Close medium/high findings with direct tests and retain limitations.
Write `artifacts/decision.md` identifying the accepted binary/harness/contract,
measured benefits versus both baselines, dependency cost, resource envelope,
compatibility exclusions and reproducible commands. If acceptance fails, retain
the no-go evidence and next smallest experiment.

A go result authorizes only a recommendation for a separately scoped
`parquet_csv_wepppy_integration` package. That successor must own HTTP/auth contracts,
filtered/archive adapters, service-wide admission across eight workers, output
serving and cleanup, operator/user docs, deployment identity/mount parity and
rollback. Do not implement those here. Update package, tracker and project board
with the precise standalone outcome, leaving production repair unclaimed.

## Concrete Steps


Run from the task checkout. Begin with `git status --short`, `git rev-parse HEAD`
and the package/contract reads; protect unrelated work. During scaffold validation:

    wctl --project-dir "$PWD" doc-lint --path docs/work-packages/20261118_parquet_csv_cli
    wctl --project-dir "$PWD" doc-lint --path docs/schemas/parquet-csv-cli-contract.md
    wctl --project-dir "$PWD" doc-lint --path PROJECT_TRACKER.md
    git diff --check

After M0 finalizes paths, add exact runnable CLI/harness/benchmark commands here
before M1. Planned Rust checks use `cargo test --locked --manifest-path
 tools/parquet_csv_cli/rust/Cargo.toml` and a release build with the same manifest.
Use canonical `wctl run-pytest` for Python tests and prove checkout identity. Run
the required broad repository test gate before implementation handoff; no pytest
is needed for this documentation-only scaffold. Do not fabricate executable
commands or pass counts for files that have not been created.

## Validation and Acceptance


The contract checkpoint is the first acceptance boundary. M1 proves output parity;
M2 proves real lifecycle/resource boundaries; M3 proves predeclared performance
and memory goals; M4 proves reviewed standalone suitability. Every boundary must
retain both valid-state success and explicit bounded failures. No browser or
production repair claim is possible in this package because nothing is wired.

## Idempotence and Recovery


Use fresh private scratch directories and preserve source copies. Repeated tests
must not overwrite inputs, previous evidence or unrelated output. Clean only
scratch owned by a completed/reaped invocation. Retry failed benchmarks with a
new evidence identity. Recovery is removal of the isolated evaluation artifacts;
there is no production rollback or stack restart in scope.

## Artifacts and Notes


Keep contract approval/reviews, dependency inventory, corpus manifest, resource
ADR reference, parity results, raw benchmark records, lifecycle results and final
decision under this package's artifacts. Keep large/private project data outside
Git and record controlled locations and digests. Redact credentials and account
data. Record repository integration separately from runtime integration.

## Interfaces and Dependencies


The draft contract defines proposed CLI input/output and harness result concepts;
M0 must replace unresolved wire details with exact schemas before code exists.
Candidate libraries are Apache Rust Parquet and Arrow CSV with minimum evaluated
features. Reuse native PyArrow only as a comparator/oracle in the harness tests.
Do not add a query engine, network fetcher or runtime compatibility fallback.

Revision note: 2026-11-18 scaffold created at the operator's request; implementation
and integration gates intentionally remain closed.
