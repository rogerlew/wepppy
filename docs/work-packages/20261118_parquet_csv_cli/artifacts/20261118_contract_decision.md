# Contract decision checkpoint: Parquet CSV CLI

**Status**: Draft; NOT ratified; implementation gate CLOSED.
**Recorded**: 2026-11-18 18:13 UTC
**Starting revision**: `dff2f29f74158857da3b0c313e7ec7194501ed76`
**Amendment ID**: PARQUET-CSV-CLI-01

## Authority and rationale

The operator requested a contract-first work-package scaffold and explicitly
made WEPPpy integration contingent on CLI and Python-harness success. Rust and
the shape-converter asynchronous subprocess pattern are the selected evaluation
direction. This is scaffold authority, not approval of unresolved interfaces,
limits, implementation, deployment or integration.

The intended delta is a standalone bounded converter/harness with contracted CSV
semantics, reproducible performance evidence and explicit failure behavior.
Existing HTTP routes, permissions, download behavior and runtime topology remain
outside the amendment. Current code is evidence for compatibility discovery, not
a substitute for ratifying the intended standalone contract.

## Applicable authority

The proposed durable contract is `docs/schemas/parquet-csv-cli-contract.md`.
Apply dependency evaluation, generated-artifact validation, parameterization ADR
and integration-history standards. Adopt the contract-first checkpoint sequence
for standalone implementation. A later integration package must inventory and
amend affected browse/download, authorization and response contracts separately.

## Required before implementation

- Enumerate real input types/codecs, ordinary and filtered exports, archived
  sources, valid empty files, legacy metadata, malformed inputs and failure states.
- Resolve exact argv/IPC schema and exit mapping, CSV compatibility, source
  ownership/immutability, atomic output, overwrite, cancellation and cleanup rules.
- Fix numeric acceptance thresholds and the resource-envelope ADR with rationale.
- Evaluate the exact minimum Rust dependency graph, including allocation bounds.
- Obtain operator approval of the exact contract revision and two independent
  read-only reviews; record reviewer identities, revisions and dispositions.
- Commit contract, decision, ADR and review dispositions as a standalone ancestor;
  record the full SHA in tracker and verify ancestry before code edits.

## Compatibility and regression plan

No persisted project schema or production behavior changes in this package.
Compare fresh outputs with the current Python oracle and independently parse
headers and cells. Preserve null/NaN handling, numeric precision, date/time and
nested/binary behavior where supported, units labels, index omission, ordering,
quoting and empty-file behavior. Unsupported or excluded variants must be explicit
and must block any successor integration that needs them.

Exercise actual binaries and subprocesses for all filesystem/resource boundaries.
Measure whole process-tree memory/CPU, latency, output and scratch bytes, and
cleanup under success, failure, cancellation, concurrency and repeated use.

## Approval and reviews

Operator approval of concrete contract: **pending**.
Independent contract review A: **not performed**.
Independent contract review B: **not performed**.
Checkpoint ancestor commit: **none**.
No acceptance verdict or zero-findings claim is implied by this scaffold.
