# Default workflow validation and correctness review

Primary integrator self-review, 2026-11-18 UTC. User authority is recorded in
package.md. This is a test-execution/selection change, not a scientific change.

- New default command: 113 passed, 99 deselected in 14.37 seconds. This includes
  both CLI command paths, existing shared/sharded checks, real subprocess policy
  tests and all lightweight Disturbed contracts.
- Default real Disturbed collection: 16 of 115 selected, 99 deselected.
- Explicit --run-disturbed-matrix collection: all 115 selected (96 native
  simulations, three summaries and 16 lightweight checks).
- Roads matrix collection remains 516 cases. No other native selection changed.
- Broad default invocation attempts preflight, reports missing runtime donors and
  stale database columns, and starts no pytest. This is not a broad-suite pass.

The real native Disturbed matrix was deliberately not executed for this metadata
policy change. A temporary pytest sentinel proves marked test bodies do not run
by default and do run with the flag; actual collection verifies all real cases.
The published report/source-currentness contract passes. The initial failed
attempt placed a marker in the producer, triggering its pinned source hash. That
change was removed; external selection now preserves the producer exactly, as
recorded in validation_receipt.json. Historical receipts/reports were not edited.

Both run-pytest and its worktree alias execute the same function and pass the
same options. run-pytest-shared retains the original Compose exec and nonce;
run-pytest-sharded remains an explicitly selected shared path. Selection is a
pytest plugin, so the Disturbed opt-in applies consistently to all these paths.
The try-first hook assigns the marker before ordinary marker filtering.

No service, schema, native binary, model input, threshold, assertion or
parameterization changed. No new security boundary was introduced beyond the
previously reviewed isolated runner. No unresolved correctness finding remains
for this policy; broad database readiness and latency remain separate concerns.

Compressed original logs and receipts are roundtrip verified, with decompressed
SHA-256 values in validation_receipt.json. Failed attempts remain retained.

Final gates: all 13 changed Markdown files pass lint; root AGENTS remains at
160 lines. Changed-file broad-exception enforcement passes with zero increases,
and staged whitespace validation passes.
