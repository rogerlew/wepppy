# D-Tale implementation QA

Date: 2026-09-16. Scope: current service/stub, local AGENTS/README, browse harness
and native freshness regressions after checkpoint `fbac92404`.
**Disposition: scoped QA PASS.** No blocking maintainability or test-quality
finding remains. Full runtime/browser, mount and archive acceptance remain open.
No production or test edits were made by this reviewer.

## Evidence and resolved findings

- `dtale_affected_tests_revision2.log`: **22 passed, zero skipped**.
- `dtale_stubtest.log`: successful stubtest; the additive `DatasetMeta.resolved_path`
  field matches the runtime default.
- `broad_exceptions_dtale_revision2.log`: changed-code exception gate passes.
- Reviewed the correctness after-probe and native regression assertions for
  shared overlay identifier refresh, surviving overlay defaults and eager
  partial-registration cleanup. All three prior findings are resolved.
- Reviewed the real security after-probes for read denial, count-query failure,
  absent optional controllers, alias selection and partial registration. The
  final durable symlink-loop test now asserts the visible grid error envelope.

The freshness tests run actual pandas/Parquet readers, DuckDB queries, upstream
D-Tale state and Flask endpoints against disposable files. Their substitutions
are bounded: run-root selection, optional map discovery for table tests, and
specific mutation/failure timing. They assert actual values, stable dataset IDs,
source identity, HTTP/error payloads, and absence of rejected partial state.
This is materially stronger than fingerprint predicate-only testing.

The browse harness correction stops automatic redirect following before checking
303 and removes 404-as-unavailable skips. Its config-path test now distinguishes
the browse bridge's logical path from the loader's legacy config fallback;
the latter has a separate actual loader regression. The harness still replaces
the internal HTTP client, so 22 passing tests do not imply live bridge acceptance.

## Maintainability and valid-state coverage

Source identity and drift translation are concentrated in `_fingerprint`,
`_resolve_source_path` and `_verify_source`. The lazy class uses one
`_assert_current` guard at schema/count/page boundaries. `finally` checks preserve
stable native errors while giving observable source drift the intended
changed-source result; counts are assigned only after the post-read check.
Cached counts and samples remain guarded. Same-byte selected-path rebinding is
tested independently from changed-byte invalidation.

The route adapters keep their distinct client contracts: loader acquisition
errors use HTTP409 plus structured error/description; the grid uses the proven
upstream HTTP200 `error:string` envelope without successful rows. Existing
non-lazy delegation and bounded Parquet reads remain structurally intact. The
README gives a clear reopen action, explains shared-tab state and preserves
invalid-filter behavior. The filter regression proves matching rows change from
one to two, then a removed field yields 422 without silently broadening selection.

Overlay cleanup is centralized and preserves unrelated keys. Replacement updates
all dataset references to a shared overlay, deduplicates matching choices and
refreshes its feature identifier. Removal restores a registered surviving
default with its location candidates. The corresponding regression covers two
dataset IDs, not only one caller. Missing/malformed/absent overlay tests use the
real JSON parser and assert cleanup from the maintained registries.

The new broad eager initialization catch is narrowly scoped to third-party
publication, logs the affected dataset, discards its partial state and rethrows.
The test fails after real upstream registration and verifies cleanup. It is an
explicit cleanup boundary rather than a recovery fallback.

The service grows by 173 added / 33 removed lines, primarily explicit generation
and shared-reference handling. Its existing upstream patches are not duplicated
or expanded into another transport layer. The helper boundaries keep this diff
reviewable. Residual debt is the original large module and four related in-memory
map registries; further map features should reuse the removal/update helpers
rather than add additional registry mutations at call sites. No current refactor
is needed to accept this correction.

## Performance and non-blocking follow-ups

The retained 77.39 MiB benchmark remains applicable: final review corrections
change overlay bookkeeping, cleanup and resolution-error translation, not the
count/page guard sequence. A normal page retains exactly three checks; settled
pages read zero bytes for hashing and average about 55 ms. Settled helper calls
average 0.116 ms. Admission/eviction adds roughly 0.8 seconds and is documented
in `dtale_large_parquet_performance_qa.md`; no repeat was warranted here.

Promote the retained actual read-denial, absent-controller and count-query-error
security cases into the ordinary regression suite when extending this module.
They are currently executable retained evidence, but not part of the 22-test
durable gate. Empty-but-reader-valid input and initial malformed-source cases
are useful remaining compatibility coverage, without evidence of a current
regression.

The prior Chromium probe proves the error envelope is rendered by installed
upstream UI. It intercepts the response and does not replace actual restarted-
service source-change testing. Normal authenticated browse launch, changed
backend/schema/filter behavior reaching the UI, map rendering/defaults, large
GeoJSON and NFS costs, and archive restoration remain package acceptance gates.
