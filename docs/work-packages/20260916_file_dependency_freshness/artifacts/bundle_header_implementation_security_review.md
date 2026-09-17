# Controller bundle header implementation security review

## Findings and disposition

**PASS for the scoped C10 implementation; no open scoped findings.** Reviewed
2026-09-17 UTC against contract ancestor
`984023c180f7fda01dfd0abfd9f879d01ca7dfd3`. This does not close the repository
package or approve its outstanding restarted-runtime acceptance.

Reviewed production file `wepppy/weppcloud/utils/assets.py` SHA-256:
`0ac52522e8bc0cf7d6ac3284f2e292a21fed7724b7afd6dc2fa8e9fdc6ba51c5`.

The production diff removes only `_CONTROLLERS_GL_BUILD_ID_CACHE`, the initial
stat/cache lookup, and the result insertion. The existing file-open/parser and
OSError-to-unknown boundary are unchanged. The expected ID is now read on every
lookup. The adjacent asset-version subprocess fallback is unchanged. No path,
authorization, serialization, static-serving or frontend comparison behavior
was broadened.

## Evidence

The author-run `bundle_header_tests.log` records **12 passed**, 2 warnings,
9.80 seconds. Source review confirms real equal-size/restored-mtime overwrite
and `os.replace` cases invoke the production resolver twice in one process,
then remove the input and observe `None`. Compatibility cases exercise empty
input, first empty date, the 80-line boundary, replacement decoding and
whitespace. A prior successful read followed by an injected `PermissionError`
returns unknown rather than a cached success. The permission test characterizes
the error branch; it is not a real filesystem identity/permission parity test.

`test_context_refreshes_restored_bundle_but_keeps_one_request_id` additionally
checks the actual Flask context processor: one request retains a consistent
expected ID and `cg` value, while the next request sees a metadata-preserved
new header. This preserves request consistency without process-wide stale
reuse. Existing missing-header and URL parameter tests also pass.

The inspected `benchmark_bundle_header.py` executes 1,000 production lookups
against the actual 2,195,371-byte bundle. `bundle_header_benchmark.json` reports
mean **42.68 microseconds**, below the checkpoint's 1 ms local-mount budget.
This is header-read latency, not proof that every possible 80-line file is a
fixed byte count or that other mounts have identical performance.

No reviewer production/test edits or duplicate test run were needed after
inspecting this narrow diff and the retained test/benchmark evidence. The
checkpoint's trusted generated-asset and point-in-time read limits still apply.
Final expected/served-header alignment on the rebuilt/restarted stack remains
the package's runtime gate.
