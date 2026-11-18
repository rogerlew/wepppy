# Standalone evaluation decision

Date: 2026-11-18 UTC. Decision: **go for the standalone CLI and Python harness**,
subject to the final validation receipt recorded in [validation](validation.md).
This recommends a separately authorized integration package; it does not authorize
runtime wiring, image publication, deployment or a production repair claim.

## Delivered boundary

`tools/parquet_csv_cli/` contains the locked synchronous Rust executable, stdlib
asynchronous Python supervisor, provenance generator, adversarial/parity tests,
benchmark runner and usage documentation. No production imports or runtime paths
were changed. Scaffold `11ace80c8` and contract checkpoint
`f38f8a4bd9d08b8582fbca8dcd7284a2eef87fb2` preceded implementation. Reviewed
amendments pinned telemetry and metadata exclusions before corresponding changes.

The operator's zero-trust requirement is durable in
`docs/schemas/parquet-csv-cli-contract.md#zero-trust-input-policy`: WEPPpy origin
never grants an exemption. Limits and structural checks cover empty files and
omitted index columns as well as exported fields. External-column fixtures prove
the referenced canary is not opened. Resource settings follow ADR-0148; they can
only tighten at invocation time.

## Measured result

All values below are three warm repetitions per method/file on forest, Linux
x86-64, Rust 1.92.0 and Python 3.12.3. The broad repository suite also ran on this
48-CPU host; these are local observations under background load, not isolated-host
or production latency promises. Ranges and individual samples are retained in
`benchmark-summary.json`, `benchmark-baselines.jsonl` and `benchmark-rust.jsonl`.
No statistical p95 claim is made from three samples.

| File | Python median seconds | Native PyArrow median seconds | Rust+harness median seconds | Speedup over Python | Rust parent+child peak upper bound MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| H.wat, 3,004,240 rows | 300.567 | 6.785 | 16.838 | 17.85x | 55.86 |
| chnwb, 157,788 rows | 14.796 | 0.340 | 0.980 | 15.10x | 60.85 |
| pass_pw0.events, 385,704 rows | 38.150 | 0.700 | 3.130 | 12.19x | 68.58 |

Predeclared acceptance was at least 2x faster than Python on **each** file and
at most 512 MiB parent-plus-child RSS. Both pass without changing thresholds.
Peak memory is the conservative sum of independent process high-water marks,
not a synchronized whole-tree sample. Python H.wat peaked at 1,503,056 KiB.
Rust timing includes provenance validation, admission, staging, process startup,
decoding, writing, finalization and child drainage. Readback is outside conversion
timing. The outer `process_wall_seconds` also includes benchmark interpreter
startup and output hashing; it is not the acceptance metric. Baseline CPU includes
interpreter/import/readback work, whereas Rust child CPU covers that child only;
do not compare these as identical CPU scopes.

The resource envelope applies to the Rust/harness conversion path. Python/native
benchmark comparators intentionally reproduce the old allocation behavior and
are evaluation recipes, not resource-isolated services.

Native PyArrow is faster but has different output hashes and formatting/precision.
It is a necessary comparator, not a compatible replacement. Rust matches the
Python oracle's full output hashes on all three files. Independent CSV readback
parses every row and verifies header/field counts, total rows and first/last cell
values against Arrow projection. See `readback-results.json` and the immutable
`corpus-manifest.json`; project files and large outputs are deliberately not in Git.

## Lifecycle, dependencies and review

`lifecycle-results.json` retains real CPU/wall/staging/output-limit failures with
cleanup, two concurrent large conversions, rejection of a third request while
artifacts hold capacity, and a separately labeled advisory cold run using
POSIX_FADV_DONTNEED. The hint does not guarantee physical cache eviction. Focused
tests cover provenance FIFOs, malformed/oversized control messages, repeated and
spawn-time cancellation, cross-process admission, source mutation, invalid
metadata/pages/Snappy/dictionaries/offsets, hidden unsupported types and valid
empty/legacy inputs. A Rust /dev/full test checks an actual writer I/O error; this
is not a full-filesystem exhaustion deployment test.

The final graph has 81 third-party packages; the earlier 83-dependency probe is retained
separately, and no csv/csv-core dependency. The final audit reports zero known
vulnerabilities and the unsuppressed informational Chrono maintenance warning
RUSTSEC-2026-0543. `dependency-final-inventory.json` retains version/license/source
inventory. This is bounded evaluation acceptance, not blanket production approval
of Arrow IPC/FlatBuffers or a guarantee of upstream memory safety.

Independent [correctness](20261118_correctness_review.md) and
[security](20261118_security_review.md) reviews have no unresolved medium/high
source findings. Their initial conditional verdicts and subsequent amendments
remain intact; the integrator's final receipt closes the local validation
conditions separately. A confirmed process-disappearance race in /proc reads was
fixed and directly regressed with a real child. One earlier benchmark worker
failed without a retained stderr because the original benchmark runner discarded
it. Its cause remains unknown; `benchmark-interrupted.md` retains that limitation.
The runner now retains failure details. Subsequent full repetitions passed;
this does not retroactively prove the cause of the earlier failure.

## Exact artifact identity and reproduction

Accepted release SHA-256:
`2efd194f5842f668687b58659337598b5d3b868151fc12f0d3b837b9313a8b37`.
`binary-provenance.json` pins every Rust source, manifest and lock digest;
`source-inventory.json` additionally pins harness, tests and benchmark sources.
The recorded Git SHA in benchmark environment files is the contract ancestor;
implementation was uncommitted then. These inventories, not that ancestor alone,
identify the evaluated source. Final build size and canonical checkout validation
are recorded in `validation.md`.

From the task checkout, build and generate provenance using
`tools/parquet_csv_cli/README.md`. Run the focused tests and benchmark commands
there, using a fresh output directory and verifying the corpus manifest first.
`lifecycle-replay.py` and `readback-replay.py` retain the exact evaluation recipes;
set their tool/evaluation-root paths to your controlled local copies before reuse.
They are historical experiment recipes, not production entry points.

## Explicit successor obligations

No-go for production integration under this package. A successor must resolve any
required nested/binary/date/decimal/extension/other-codec or metadata compatibility,
filtered exports and archives, eight-worker service admission, authorized source
resolution, HTTP/error/download contracts, visible project artifacts, serving and
cleanup, production identities/mounts/umask/configuration, rollout and rollback.

Same-UID malicious replacement and arbitrary native-code execution are outside
this boundary. Child limits are not an OS capability sandbox or egress filter.
Parent SIGKILL can leave a child and abandoned scratch; explicit reconciliation is
required before root reuse. The live 5 GiB scratch cap is per shared root and
excludes abandoned crash artifacts. No real uninterruptible kernel-wait test or
exhaustive fuzzing claim is made. The operator explicitly deferred broad repository tests until after integration.
The stopped run and its cancellation-induced failure remain recorded; no green
full-suite claim is made. This deferral does not weaken the standalone tests or
artifact acceptance criteria.
