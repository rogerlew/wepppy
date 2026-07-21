# Make WEPP interchange parsing observable and lossless (completed 2026-07-21)

This ExecPlan is a living document. Maintain its `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` sections as work proceeds. It follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Users and operators must be able to trust that a Parquet interchange dataset represents the WEPP text output it claims to convert. After this work, a current 27-field channel-water-balance file produces rows, while a malformed data row fails the RQ/native conversion with enough context to correct the producer or parser. The work also prevents every other native interchange reader from quietly converting a non-empty source into a partial or empty dataset.

## Progress

- [x] (2026-07-21 18:46 UTC) Captured the production signature: `chnwb.txt` has 34,192,070 data rows and its Parquet output has zero rows.
- [x] (2026-07-21 18:46 UTC) Identified the immediate cause: `chnwb.rs` requires exactly 22 tokens while the current producer writes 27.
- [x] (2026-07-21 19:03 UTC) Audit every native reader's header detection, candidate-row admission, row accounting, and intentional-empty behavior.
- [x] (2026-07-21 19:03 UTC) Define and implement strict admission/accounting at the native/Python boundary.
- [x] (2026-07-21 19:03 UTC) Add CHNWB current-layout and malformed-candidate regression tests.
- [x] (2026-07-21 19:03 UTC) Repair every audit-confirmed silent-loss site and add malformed-candidate coverage for the affected row classes.
- [x] (2026-07-21 19:03 UTC) Reparse the affected production artifact, run native and WEPPpy validation, update governance, and close the package.

## Surprises & Discoveries

- Observation: The silent failure is complete rather than intermittent.
  Evidence: the 8.8 GB source contains 34,192,070 records; `chnwb.parquet` contains zero rows because every 27-token row hits `if tokens.len() != 22 { continue; }`.
- Observation: The native parser returns a row-count summary, but the Python wrapper only logs completion and no contract asserts that source candidates became rows.
  Evidence: `wepp_interchange/src/lib.rs` returns `rows_written`; `wepppy/wepp/interchange/watershed_chnwb_interchange.py` does not validate it.
- Observation: A disposable parse of the original 8.8 GB source completed with exactly 34,192,070 rows and 137 row groups.
  Evidence: `/tmp/chnwb-observability-e8XDPX/chnwb.parquet`, created with the rebuilt release library; the production artifact was not overwritten.

## Decision Log

- Decision: Preserve the existing CHNWB Parquet schema for the legacy 22 fields in the first repair and accept the five trailing current producer fields only when their layout is explicitly recognized.
  Rationale: this restores compatibility without silently reinterpreting fields or forcing a consumer-breaking schema expansion. A separate additive schema change can expose profile-storage fields after its contract is defined.
  Date/Author: 2026-07-21 / Codex
- Decision: A candidate row is any nonblank, nonseparator row after a recognized data header whose first token indicates the table's record type. Candidate rows may not be silently skipped for width or value errors.
  Rationale: headers and separators are intentionally non-data; anything else could be lost scientific output and must be observable.
  Date/Author: 2026-07-21 / Codex

## Outcomes & Retrospective

Completed 2026-07-21 19:03 UTC. The parser now accepts both CHNWB layouts and
rejects every audit-confirmed malformed candidate contextually. Successful native
summaries expose `candidate_records`, `accepted_records`, and `rejected_records`,
and the Python boundary logs those counts with source and target paths. The
disposable production reparse produced 34,192,070 rows (137 row groups), exactly
matching the raw source count; the known 2012-01-19 channel 2035 and 776 records
were present. `cargo test -p wepp_interchange_rust --lib` passed 82 tests,
`--test tc_out` passed 17, and `wctl run-pytest tests/wepp/interchange/test_rust_interchange.py --maxfail=1` passed 6.

## Context and Orientation

WEPP-Forest is the numerical model. Its watershed binary writes `wepp/output/chnwb.txt`, a daily channel water-balance table. WEPPpyo3 is the native Rust interchange library that converts WEPP text output to Parquet. WEPPpy calls that library from Python after a run completes and exposes the generated Parquet artifacts to reports and exports.

The affected run is `/wc1/runs/be/beneficiary-forfeit/`. It used `/workdir/wepppy/wepp_runner/bin/wepp_260430`; the matching source checkout is `/home/workdir/wepp-forest_260430_baseline`. Its CHNWB writer appends five profile-storage fields to the historical output. `wepp_interchange/src/chnwb.rs` accepts only 22 whitespace tokens, silently skips all current 27-token records, and deliberately writes an empty Parquet file when no rows were accepted.

The governing outcome is not a fallback parser. A supported input layout must parse completely. An unsupported or malformed candidate row must return an `InterchangeError::Parse` containing the source path, one-based line number, expected layout, and a bounded source preview. A source that has no recognized data header must fail. A recognized header with zero valid data rows is valid only when that output type's documented contract permits emptiness; otherwise it must fail.

## Plan of Work

First inventory every parser module under `/home/workdir/wepppyo3/wepp_interchange/src`. For each reader, record the header marker, the intentional non-data lines it skips, the candidate-row predicate, supported token layouts, its response to malformed candidates, and its empty-output contract. Add the completed inventory to this package's tracker or an artifact before changing behavior.

Next add a small shared Rust helper or consistently applied local helper that creates `InterchangeError::Parse` for malformed candidate records. It must not convert malformed text to default values or continue. Keep intentionally skipped headers, separators, and documented comments distinct from candidates. Preserve streaming behavior so large production files do not need to fit in memory. Extend native write summaries with accepted and rejected candidate counts if the existing `rows_written` value cannot prove full admission; propagate those counters through the Python binding and log them at the WEPPpy integration boundary.

Repair `chnwb.rs` first. Recognize both the historical 22-token layout and the current 27-token layout. Parse the common fields identically, retain trailing current fields only under an explicit schema/version decision, and fail on any other candidate width. Reject missing headers and non-empty candidate sets that result in zero writes. Add tests that prove a current-layout fixture creates rows and an invalid-width or invalid-number row fails at the correct line.

Apply the same audited contract to each confirmed silent-loss reader. Do not blindly replace every `continue`: a separator before a header is not a candidate. Add a compact table to the standard naming each supported no-data exception and its proof. Update the Rust README/API documentation and WEPPpy caller behavior so an operator can see source rows accepted and rejected.

Finally use a disposable output path to reparse the affected production `chnwb.txt`; never overwrite its existing artifact during diagnosis. Compare the Parquet row count with the raw data row count, spot-check the known 2012-01-19 records, and run the native and WEPPpy test suites. Update this plan, package tracker, package brief, root project tracker, and the governance standard with actual results before closure.

## Concrete Steps

From `/home/workdir/wepppyo3`, inspect candidates with:

    rg -n -C 3 'tokens\.len\(|continue;|row_counter == 0|empty_chunk' wepp_interchange/src
    cargo test -p wepp_interchange

From `/home/workdir/wepppy`, run targeted integration tests after native changes are built into the local environment:

    wctl run-pytest tests/wepp/interchange tests/rq/test_wepp_rq_stage_post.py --maxfail=1

For generated-output evidence, create a uniquely named disposable target under `/tmp`, invoke the installed/native CHNWB interchange against `/wc1/runs/be/beneficiary-forfeit/wepp/output/chnwb.txt`, then use PyArrow metadata to require `34,192,070` rows. The source artifact and production Parquet file remain untouched.

## Validation and Acceptance

Acceptance requires all of the following observable behavior:

- A synthetic legacy 22-token CHNWB row and a current 27-token row both create the expected Parquet row(s).
- A malformed candidate width, invalid numeric token, or missing required header fails with contextual `InterchangeError::Parse`; no empty output is published as success.
- Every audited parser has a tested candidate-row rule and documented empty-output contract.
- The affected production source reparse returns 34,192,070 rows, and known channel 2035 / 2012-01-19 data is present.
- Native Rust tests, affected WEPPpy tests, broad-exception enforcement, and documentation lint pass.

## Idempotence and Recovery

All parser tests write to temporary directories. Generated-output validation writes only under `/tmp` with a unique name and may be rerun. Do not overwrite `chnwb.parquet` in the production run during this package. If a parser change rejects a legitimate producer variant, retain the failing fixture, add that variant deliberately to the supported-layout contract, and rerun the native suite before retrying the production reparse.

## Artifacts and Notes

The initial production evidence is recorded in `package.md` and `tracker.md`. Add an artifact only for the completed audit inventory or generated-output validation summary; do not check in multi-gigabyte run output.

## Interfaces and Dependencies

At completion, the native public conversion functions must either return a `WriteSummary` that includes accepted/rejected candidate counts or return `InterchangeError::Parse` before publishing an incomplete output. The Python binding dictionary must surface the same counters. `wepppy/wepp/interchange/*_interchange.py` functions must log the returned summary and reject a zero-row result whenever that output's documented contract requires data.

The canonical future policy is `docs/standards/interchange-observability-standard.md`. It applies to all WEPPpyo3 text-to-Parquet interchange readers and their WEPPpy callers.

Revision note (2026-07-21): Created from the observed CHNWB all-row silent discard; it establishes the audit and implementation sequence before code edits.
