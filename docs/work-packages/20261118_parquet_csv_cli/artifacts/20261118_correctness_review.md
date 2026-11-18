# Correctness and User-Experience Review - Standalone Parquet CSV CLI

## Metadata

- Package: `docs/work-packages/20261118_parquet_csv_cli/`.
- Reviewer: independent Codex reviewer `/root/csv_contract_correctness`.
- Review date: 2026-11-18; final source re-review at 18:57 UTC.
- Scope: `tools/parquet_csv_cli/rust/`, `harness/`, and `tests/`; the standalone
  contract and ADR-0148. No production route, UI, authorization, queue, deployment
  or existing exporter is reviewed as changed behavior.
- Branch: `codex/parquet-csv-cli-package`; scaffold `11ace80c8`, checkpoint
  `f38f8a4bd`, telemetry amendment `23461db56`, compatibility amendment `bba939a47`.
- Canonical intent: `docs/schemas/parquet-csv-cli-contract.md`, especially
  Compatibility, CLI interface, Python harness interface and ownership, Resource
  envelope, and Acceptance; ADR-0148 supplies resource decision provenance.
- Final reviewed implementation is an uncommitted temporary candidate at
  `/tmp/parquet-csv-next/tools/parquet_csv_cli`. Exact transfer and canonical tests
  remain integrator obligations; source-review approval does not attest a later diff.
- Related security review: separate `/root/csv_contract_security` review; its
  verdict must be retained independently. This artifact is not security approval.

## User Outcome

The user can evaluate an owned Rust CSV converter through a standalone async
Python harness before considering WEPPpy integration. Success is a fresh completed
CSV artifact with row/byte counts, input digest and bounded resource telemetry.
It is not HTTP success, deployment, or evidence that production crawling has been
remediated. Failures use the finite CLI/harness codes; cancellation remains
cancellation after owned cleanup. Partial output is not returned as a completed
artifact. Completed artifacts retain admission until explicitly cleaned up.

## Failure-Class Coverage

This is a proactive standalone evaluation, not an incident-repair claim. Review
nevertheless assessed the shared assumptions behind each confirmed defect:
metadata compatibility across schema/field metadata, empty-file handling across
empty and mixed row groups, and typed failures across pre-admission, admitted
scratch creation, child-result verification and metric parsing. The dispositions
below cover all concrete cases found during this review. They do not establish
coverage of every Parquet encoding or operating-system failure.

## Valid-State Matrix

| State | Valid? | Required behavior | Evidence and disposition |
| --- | --- | --- | --- |
| Scratch root absent | Yes | Create private root/request; retain admission | Harness implementation and focused conversion tests |
| Source absent, symlink or nonregular | No | `source_rejected`, no retained request | `test_missing_symlink_and_nonregular` |
| Supported zero-row file | Yes | Header-only CSV with all codec/column policies enforced | `test_units_indices_and_empty`, `test_empty_codec_validation` |
| Empty row group within populated file | Yes | Preserve real rows; scan nonempty page structures | `test_mixed_empty_groups_and_all_null_column` |
| Supported populated data | Yes | Production-Python-3.12 oracle byte parity | All supported types, random floats, integer/float extremes; real-corpus evidence supplied by integrator |
| Legacy units/index metadata | Yes within contract | Preserve label/index projection and Python whitespace | Metadata/index/units tests; whitespace defect fixed |
| Non-UTF-8 metadata or invalid JSON shape | Explicitly excluded | Bounded `input_rejected` | Ratified compatibility amendment; direct exclusion tests |
| Duplicate projected labels | Explicitly excluded | Reject instead of reproducing oracle data loss | Direct duplicate-label fixture and contract amendment |
| Existing unrelated output | No overwrite allowed | Explicit error, preserve bytes | `test_cli_output_collision_preserves_file` |
| Excess concurrency or retained artifacts | Expected limit | `busy`; no queue or early slot release | Artifact-lifetime and cross-process admission test |
| Malformed page/schema/external reference | No | Bounded rejection, no external-file open | Page/schema mutation tests, external-reference canary, offset tests |
| Timeout, cancellation or child failure | Expected exceptional path | Drain/terminate owned process group and clean scratch | Real child tests, repeated/spawn/staging cancellation tests |
| Cleanup failure | Exceptional | `cleanup_failed`; retain capacity | Cleanup-failure test; no claim capacity was reclaimed |

## User-Reachable Error Policy

| Condition | Class | Result | Contract rationale |
| --- | --- | --- | --- |
| Invalid arguments/unsupported input | Expected rejection | Finite CLI code/exit | CLI interface and supported subset |
| Missing or altered provenance | Expected rejection | `provenance_invalid` | Exact source/binary identity required |
| Unwritable scratch or request creation failure | I/O exception | `io_error` after ownership cleanup | Failure must stay within typed harness API |
| Child claims success without regular completed output | Protocol/output failure | `output_invalid` | Exit status alone cannot prove artifact existence or validity |
| Invalid or unrepresentable metrics | Protocol failure | `protocol_error` | Strict bounded JSON and numeric schema |
| Admission full | Expected capacity limit | `busy` | Two shared slots, including retained artifacts |
| Timeout/diagnostic overflow | Expected bounded failure | `timeout`/`diagnostic_overflow` | Supervision and output limits |
| Caller cancellation | Cancellation | `CancelledError` after drainage | No abandoned owned child or premature release |

## Generated Artifact Evidence Chain

| Stage | Expected semantics | Evidence | State at this review |
| --- | --- | --- | --- |
| Request intent | Source path, selected limits and scratch root | Harness API plus fixtures | Reviewed |
| Reloaded application state | None introduced | No NoDb/database/application integration | N/A by scope |
| Prepared input | Private regular snapshot and exact digest | Staging source-mutation/cancellation tests | Reviewed; canonical final rerun pending |
| Exact executable | Contract ancestor plus binary/source provenance | Strict provenance tests and source hashes below | Source reviewed; final binary receipt to attach |
| Execution output | Fresh completed CSV, no partial success | Real-binary byte comparisons and limit/error tests | Earlier canonical candidate passed; final rerun pending |
| User-facing result | Standalone artifact readback | Independent Python oracle bytes and CSV readback | No browser/HTTP workflow in scope |

The reviewer directly reproduced the original metadata, zero-row and raw-exception
failures using actual source files, release binary and subprocess harness. The
fixed source and corresponding regression tests were independently re-reviewed.
The integrator reports matching byte hashes for all three selected real-project
files; final retained manifests, hashes and repeated benchmarks must be attached
before a package go decision. Production-equivalent identity/mount workflow proof
belongs to the separately authorized integration package.

Highest supported review claim: source correctness approved for the declared
standalone subset, with local validation evidence on earlier source and final
canonical-candidate validation pending. No deployed/repaired/incident-resolved claim.

## Review Checks and Limits

Canonical intent and reviewed amendments, rather than accidental oracle failures,
control behavior. Valid empty/mixed/populated states and rejected metadata/type
variants are distinguished. Generated-byte assertions exercise the actual writer.
Fake executable tests exercise the real subprocess lifecycle; they do not replace
real-binary output parity tests. Failure injection is labeled where used and does
not establish actual disk-full or every kernel failure behavior.

The review does not claim exhaustive state or input coverage. Python 3.12 is the
specified oracle; a Python 3.11 bare-CR result is not equivalent evidence. Date/time,
nested/binary/extension types, other codecs, filtered adapters, archive extraction,
and non-UTF-8 metadata are explicit integration blockers where needed downstream.
Successful standalone evaluation does not silently authorize those adapters.

## Findings and Dispositions

| ID | Severity | Surface | Finding and evidence | Disposition |
| --- | --- | --- | --- | --- |
| COR-01 | Medium | Contract: projected names | Oracle `to_pylist()` collapses units-induced duplicate labels; `[1,2]` became `[2,2]` | Closed: explicit duplicate-projection rejection and integration-blocking exclusion; direct regression |
| COR-02 | Medium | Contract: control interfaces | Error vocabulary and provenance wire format were unspecified | Closed: finite codes, exact schema/inventory rules and strict parser tests |
| COR-03 | Medium | Metadata parity | Invalid UTF-8 units/pandas rejected unexpectedly; Python control whitespace retained incorrectly | Closed: reviewed non-UTF-8 exclusion, Python whitespace correction, malformed-shape rejection and regression cases |
| COR-04 | Medium | Empty/mixed row groups | Zero-row early return accepted excluded GZIP; valid `[0,2]` groups rejected | Closed: column policies retained, exact empty-column handling and mixed/empty regressions |
| COR-05 | Medium | Root/result failure | Raw FileExistsError for root-file collision and FileNotFoundError for missing success output | Closed: finite error translation; real filesystem and fake-child result tests |
| COR-06 | Medium | Admitted request creation | Unwritable scratch with existing slots leaked raw PermissionError | Closed in final temporary candidate: translation after cleanup; exact mode-0500 regression and capacity reuse |
| COR-07 | Medium | Numeric result/limits | `cpu_seconds=10**400` escaped as OverflowError | Closed in final temporary candidate: bound before finite conversion; metric/limit regressions |

No unresolved medium/high source-correctness finding remains in the reviewed
candidate. New findings in later tests or diffs must reopen the appropriate gate.

## Validation Identity and Conditions

The reviewer inspected receipt
`.wctl-test-runs/36c013a912e14b9f93818102ff74bdee/receipt.json`: status passed,
pytest exit 0, no source/runtime drift, Python profile, UID 1000/GID 993. The
integrator reported 57 tests for that earlier candidate. Later host exploratory
results of 81 tests and 13 Rust tests are integrator reports, not independently
executed canonical receipts in this review.

Final source hashes observed at 18:57 UTC:

| Relative path in tool | SHA-256 |
| --- | --- |
| `harness/runner.py` | `d2af43edf10e52a36511005632cda177d6948219dccdfcbfa242531497455de1` |
| `harness/provenance.py` | `1a304fdd7e918a11bcd727ced1fa5e6e5149b191c8f5c4583b06b285eb6ffba9` |
| `rust/src/main.rs` | `a28d7a4be187cba9eab4ca93845b5121bfb6cc2bcb3e22055866a6a85e7a5804` |
| `rust/src/preflight.rs` | `e701c07a2b4895cd77990353ee7a9b8a4128a648c4107fd1c5a3519eef7592af` |
| `rust/src/compact.rs` | `a26c408f20dac36a23b794675261f1b7fedd1165893871afe531789f3dd406fd` |
| `rust/src/sha256.rs` | `43d871e94e9332ee742c129e4ecd7d910cdcaced96e6e48904acb5ae991505bd` |
| `tests/test_converter.py` | `3e2f7c80d714fce65e58077dddff33f1dddcf7f11d44e0ec8a912d4d4e6feb5f` |

Integrator must attach exact-copy/build identity, final canonical focused receipt,
broad-suite/preflight outcome, repeated benchmark/parity records, remaining resource
boundary evidence and security disposition. Do not rewrite this review as an
unconditional package acceptance if those gates remain incomplete.

## Verdict

- Source correctness gate: **pass for the reviewed standalone scope**.
- Unresolved source findings: high 0; medium 0; low 0.
- Package/release recommendation: **hold pending final canonical validation,
  benchmark/resource evidence and independent security acceptance**.
- Reviewer sign-off: `/root/csv_contract_correctness`, 2026-11-18 18:57 UTC.
- No approval of WEPPpy integration, publication or deployment is granted.

## Artifact Observability Gate

Production project observability/archive/browser requirements are deferred by the
operator's explicit standalone-only scope, documented in the canonical contract
and package integration boundary. The standalone workflow exposes source manifest,
provenance, bounded failure status, output artifact path and direct content readback.
There is no new hidden project record or download route in this package. A future
integration package must establish normal project authorization, visible outputs,
archive/restore coverage and live workflow evidence; this review does not waive it.

## Mechanical Cleanup Amendment - 2026-11-18 19:03 UTC

The reviewer independently checked the final Clippy/rustfmt delta in the temporary
candidate. The only changes from the previously reviewed Rust source are:

- Nested pandas `if let` expressions collapsed into an equivalent short-circuit
  let-chain; JSON decoding and rejection branches are unchanged.
- `rows < 0 || rows > ROWS_MAX` rewritten as the negation of an inclusive-range
  membership test for the same integer operands.
- The no-data guard rewritten using De Morgan's law; Rust's `&&` precedence over
  `||` preserves the original accepted/rejected states.

As an exact-delta check, reversing only these edits in memory reproduced the
previously recorded SHA-256 values `a28d7a4be187cba9eab4ca93845b5121bfb6cc2bcb3e22055866a6a85e7a5804`
for main.rs and `e701c07a2b4895cd77990353ee7a9b8a4128a648c4107fd1c5a3519eef7592af`
for preflight.rs. The task worktree was not modified by this review.

Updated reviewed source identities:

| Relative path in tool | SHA-256 |
| --- | --- |
| `rust/src/main.rs` | `65d52bb659f8f06ce6dbeccd439b9d16704eca64f87abb8596c902472db53e78` |
| `rust/src/preflight.rs` | `5767dcc11661d0592a7e2ef5c7a4355a9d9ec05e4d8eddae9107e2116a91ad64` |

Source correctness verdict remains pass with no unresolved medium/high findings.
Final exact-candidate rebuild/tests and the acceptance conditions above remain
required. The integrator's reported Clippy `-D warnings` success is supporting
quality evidence, not a substitute for those tests.

## Process-Observation Amendment - 2026-11-18 19:08 UTC

The security reviewer directly reproduced a Linux `/proc/<pid>/stat` lifecycle
race: opening the file while a process lives, reaping that process, then reading
the already-open stream raises `ProcessLookupError` rather than
`FileNotFoundError`. The correctness reviewer examined the bounded fix and direct
regression in the final temporary candidate. `_group_alive` now treats these two
specific disappearance results as exited processes, while other observation
`OSError` failures become `cleanup_failed`. It does not infer safe cleanup from
an unreadable process inventory or release ownership on observation failure.

The real open/terminate/read regression verifies the kernel ESRCH case. A separate
injected enumeration-denial test verifies the fail-closed classification. Restoring
only the prior `_group_alive` body in memory reproduced runner hash
`d2af43edf10e52a36511005632cda177d6948219dccdfcbfa242531497455de1`, confirming the
reviewed runner delta is limited to this function.

Updated reviewed identities:

| Relative path in tool | SHA-256 |
| --- | --- |
| `harness/runner.py` | `3815799fe4258b61b0cb984521efce7bc38f4b735271e65538912937b7b8efa6` |
| `tests/test_converter.py` | `6a9342490c9db994a0c4d5a2e832dac34c2d01787885b561f6a80370002a4e2f` |

This closes the concrete process-observation defect at source review; source
correctness remains pass. The integrator reports an earlier intermittent benchmark
worker failure whose causal relationship to this race was not established.
Retain that failed attempt and subsequent replay/results separately. Neither this
reproduction nor a successful retry proves the earlier benchmark failure's cause.
Final canonical testing on this amended candidate is still required; the newly
expanded exploratory 83-test run was in progress at this amendment.

## Strict JSON Amendment - 2026-11-18 19:18 UTC

Following the user's strict-JSON request, the reviewer examined the temporary
candidate's shared JSON decoder. Subprocess requests remain fixed argv; JSON is
the bounded result/error/provenance format. Bytes are explicitly decoded as UTF-8
before `json.loads`, so Python's automatic UTF-16/UTF-32 detection is not accepted.
The string decoder rejects BOM-prefixed JSON, duplicate keys and extra documents.
A finite-float parser rejects exponent overflow such as `1e999` in addition to
literal NaN/Infinity rejection. Excess nesting is translated from `RecursionError`
to `ValueError`, allowing the existing result/provenance boundaries to emit their
typed errors. The parser-capacity rejection is not a claim of a separately fixed
portable nesting depth.

The reviewer directly exercised malformed UTF-8/BOM, UTF-16, nonfinite/overflow
numbers and 30,000 nesting levels against the temporary module; all rejected with
ValueError-family exceptions, and a valid finite object parsed successfully.
New regression tests include an actual UTF-16-emitting child and a deeply nested
provenance sidecar through the harness, in addition to nine parser cases. The
expanded 94-test result must be attached by the integrator after execution.

Updated reviewed identities:

| Relative path in tool | SHA-256 |
| --- | --- |
| `harness/provenance.py` | `d47916db45de0a16d9bea559148d28626527968737b7d54848ad4b92db8c7d34` |
| `harness/runner.py` | `7d1771a40868cf611592d058b35e6c4f3e05c63290b1898bb0121d46d9376c1b` |
| `tests/test_converter.py` | `a3098d157117f84952f760d12b22c2add2ab5dbb1e7db22f10a9ef1775c9845d` |

The runner delta consists only of two inline broad-exception boundary annotations;
removing them in memory reproduces its preceding reviewed hash
`3815799fe4258b61b0cb984521efce7bc38f4b735271e65538912937b7b8efa6`.
Source correctness approval remains in force for this bounded amendment. Retain
the explicit UTF-8/no-BOM/finite-number/typed-depth wording in the contract before
the final implementation commit, and attach canonical tests for the exact copied
candidate. No new production integration authority is implied.

## Integrator validation attachment - 2026-11-18

Final source transfer preserved the reviewed hashes (runner differs only by the
two reviewed boundary comments). The task-checkout release rebuild exactly
matches binary `2efd194f5842f668687b58659337598b5d3b868151fc12f0d3b837b9313a8b37`
and its Rust source inventory. Canonical wctl focused validation passed all 94
tests with no source/runtime drift; see `focused-receipt-summary.json` and
`validation.md`. Final benchmark/lifecycle/readback records identify this binary
and the strict-JSON harness. All standalone acceptance thresholds pass.

The operator explicitly deferred the broad repository suite until WEPPpy
integration. Its stopped receipt and cancellation-induced failure remain retained;
no full-suite pass is claimed. Integrator accepts the standalone evaluation only.
The source review's historical conditions above are preserved; this attachment
records their final local disposition, not human or production release approval.
