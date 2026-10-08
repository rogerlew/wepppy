# Tracker

Closed (code/local), 2026-10-08 UTC.

## Completed

Implemented the raw 800 m cell-keyed bulk client, strict parser, manifest freshness checks, immutable source cache and atomic references. Docker defaults/shared environment mappings and local `.env` configure `PRISM_CACHE_DIR=/wc1/cache/prism`. The canonical client contract and ADR-0081 capture scope, rationale, units, failures and recovery.

Focused tests: 39 passed. Stub/API comparison and test-stub completeness pass. Changed-file broad-exception enforcement passes. Live worker cold/warm extraction, year boundary, provisional interval, independent prior-source parity, alias deduplication and second-worker cache reuse pass. Exact final candidate source hashes are retained. The 500-cell/183,000-row recorded payload passes every-value parity; parser grouping reduces measured time from 8.23 to 2.35 seconds. Datum-transform reuse reduces 100-point mapping from 3.17 to 0.050 seconds. Source attempt evidence, including the initial keep-alive failure, is archived in `artifacts/live-cache-evidence.tar.gz`.

## Validation outcome and follow-up

The required full suite stopped at 98%: 10,253 passed, 126 skipped, one failure in the unchanged PostgreSQL marker-write latency test (64 ms incremental p95 against a 50 ms limit). Rerunning the entire failed module and the remaining test modules passed all 207 tests in 60.10 seconds. The original full invocation was not green; no unrelated timing threshold was changed. Focused tests, API/stub checks, broad-exception enforcement and Markdown checks pass. See `artifacts/validation-summary.json` for exact outcomes.

No production deployment or climate-mode integration is part of this delivery. Existing containers receive the new environment setting on normal recreation. Future integration must retain project-owned source/provenance and validate resulting model inputs. Wind, radiation conversion, precipitation disaggregation and climate UI wiring remain separate work.

## Review notes

See [correctness review](artifacts/correctness-review.md). Provider keep-alive expiry was reproduced during first live polling; explicit connection closure resolved it. The stub checker exposed an unnecessary ordered-dataclass generated TypeVar; plain frozen cells with explicit row/column sorting preserve behavior and pass the API check. Observe-only quality tooling compares committed base-to-HEAD, so its changed-file report does not cover uncommitted edits; no quality-delta claim is made from that output.
