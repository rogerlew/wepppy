# Native SBS implementation correctness review

**Final correctness gate: pass.** All findings below are closed. Final acceptance
and the request-admission re-review record the proxy/browser and locking evidence.

Independent reviewer: Codex correctness reviewer. Date: 2026-09-10.
Contract ancestor: `328db92dd`. Scope: native helper/fallback removal, NoData
handling, batch failure translation, SBS error renderer and Disturbed/BAER
upload/summary integration. Runtime source inspection was read-only. One small
analytical raster probe ran in the development container using temporary files;
no live project was modified and no full suite was run.

## Initial findings and disposition

1. **High: fractional/NaN NoData metadata can mask valid unburned cells.**
   Independent container reproduction used a projected Float32 raster containing
   `[[0, 1, 2, 3]]`, first with NoData metadata `NaN`, then `0.5`. Both passed
   `sbs_map_sanity_check`. Native four-class export returned `[[255, 1, 2, 3]]`.
   Native `nodata_to_i64` previously cast these metadata values to zero.
   Fractional metadata need not appear as fractional raster pixels, so the
   integer-class sanity check does not exclude this case. The old Python export
   with metadata `0.5` returned class 0 for the valid zero cell, not a masked cell.
   The implementer has added finite/integral filtering to the Rust conversion;
   rebuilt-binary and real-raster regression evidence remain required.

2. **Medium: map refresh failures still overwrite Summary.** At initial runtime
   review, `Baer.showSbs` retained Summary at task start but its four failure
   branches still invoked the shared stacktrace renderer with the complete
   controller (`controllers_js/baer.js`, `showSbs`). This can overwrite a
   successful classification table when the parallel map request fails.
   These branches need the SBS error path, and summary/map completion-order tests.
   Separately, `map_gl.js:1436` logs refresh errors and resolves `undefined`;
   BAER then reports map absence instead of the underlying fetch failure.
   Preserve accepted Summary and avoid claiming map absence after an unavailable
   fetch. Do not claim gateway detail preservation where the map helper has
   already discarded the original HTTP error.

3. **Medium: summary recovery and status are incomplete.** Initially,
   `loadModifyClass` failure showed Details without setting failure status;
   its later successful retry replaced Summary but left stale error Details.
   A parallel successful map request could consequently leave Status showing
   success while summary retrieval had failed. Validate summary-success/map-
   failure and summary-failure/map-success ordering, followed by successful retry.

4. **Low: existing CLI entry point was removed.** The initial fallback deletion
   also removed the `__main__` export command. The implementer restored it during
   review; this finding is closed in source.

## Contract clarification

The initial source/display NoData wording did not describe the existing code:
`export_wgs_map` writes display NoData to `_nodata_vals`, while public
`nodata_vals` remains the configured/source list. Four-class export reads the
original raster, where 255 may be a valid source class. Adding display 255 to
its mask would change prior output. The implementer is clarifying the canonical
contract and source comment to preserve source/configured masks and keep display
NoData separate. Add a valid source-255 regression to prevent conflation.

## Confirmed implementation properties

- The five native wrappers now fail on missing APIs and propagate execution
  exceptions. Duplicate Python raster summary, sanity, reclassification and
  four-class export engines are removed. Scalar helpers and explicit custom
  color-table interpretation remain.
- Batch upload now translates sanity/summary exceptions into an explicit error
  and does not publish incomplete success metadata. Existing authentication and
  upload boundaries remain intact.
- The HTML renderer selects only raw string HTTP `text/html` failures. It parses
  into an inert template, constructs fresh allowlisted HTML/text nodes, strips
  attributes and discards foreign/active/resource/custom subtrees. JSON errors
  use the shared escaped-text renderer without Summary targets. Dedicated
  security review and real-browser resource checks remain separate gates.
- Upload error bodies no longer enter hints, and upload start preserves the
  previous accepted Summary. Successful classification markup remains HTML.
- The native refresh artifact records the original and replacement binary
  digests, source commit and development-only installation. The implementer
  reports Wallow pixel/geometry/NoData parity for the rebuilt existing source,
  approximately 0.41 seconds versus 54.09 seconds for the saved Python output.
  The subsequent Rust metadata fix needs its own final binary provenance and
  parity evidence; the earlier artifact alone does not establish that fix.

## Initial acceptance conditions

Final signoff is pending closure of the native metadata and UI ordering findings,
focused Python/transport tests and actual Wallow upload/table/map/reload evidence.
The initial 24 Jest tests passed according to the implementer, but did not cover
the identified cross-request failure orderings. No full-suite execution is needed
or authorized for this package.

## Final source re-review

Findings 1-4 above are closed in the updated source and focused evidence:

- Finite/integral native filtering preserves valid zero and source-255 pixels.
  The final installed binary digest is
  `69119d84349a1e60d4290aa583c79419a0f22ecac416f3c26b60ada34a8eec45`.
  `/tmp/sbs-native-tests-final.log` records 78 passing focused tests, including
  metadata regressions and explicit batch failure responses. The native refresh
  artifact records the source delta as well as its base commit.
- BAER map failures now use the SBS error renderer. `map_gl.loadSbsMap` offers
  opt-in propagation for BAER while retaining default caller behavior.
- Errors are tracked by request source on the shared form. Successful map or
  summary refresh clears only its own error and retains the other failure.
  `/tmp/sbs-ui-races.log` records 28 passing tests, including both failure sources
  and recovery. The CLI is restored.
- The canonical raster contract now distinguishes original/configured source
  masks from the separate WGS display sentinel. The metadata test explicitly
  preserves a valid source-255 pixel.

One additional medium finding remains: `loadModifyClass` treats HTTP-200 JSON
errors as successful HTML. `query_baer_class_map` returns
`error_factory('No SBS map has been specified')` when no map exists
(`routes/nodb_api/disturbed_bp.py:598`). The factory defaults to status 200, so
WCHttp resolves with a JSON error object. The current success handler writes
`[object Object]` into Summary, clears errors and reports success. Check
`error`/`errors` before HTML insertion, preserve prior/empty Summary and render
the JSON error in Details. Cover both previous-result and initial-absence cases.
Final acceptance also awaits the real proxy/browser gate.

The additional HTTP-200 JSON finding is now closed: `loadModifyClass` checks
error payloads before assigning HTML and uses the source-keyed Summary error
path. Two regressions preserve a previous table and an initially empty Summary.
`/tmp/sbs-ui-final.log` records 30 passing JavaScript tests. No unresolved
implementation finding remains in the reviewed scope. Approve source correctness,
contingent on the final real-proxy upload/reload/recovery evidence and dedicated
security/browser gate; neither is inferred from the earlier upload-only smoke.

## Final acceptance

Approve the completed implementation. No unresolved correctness finding remains.
The retained [proxy browser log](proxy_browser.log) proves actual Wallow upload
through the authenticated development proxy in 5.597 seconds, completed
classification-table and map queries, formatted injected HTTP-504 Details with
Summary retained, successful retry and filename/table reload. The corresponding
script and screenshots are retained in this artifact directory.

The final filename change always creates the Current SBS map display, uses
`code.textContent` for uploaded filenames and restores the empty text on removal.
Source inspection and the filename-markup regression confirm that filenames are
not interpreted as HTML. [Template tests](template_tests.log) cover both absent
and accepted-map rendering. [Frontend validation](npm_tests.log) records all
110 suites and 852 tests passing; focused native/transport tests and binary
provenance are retained in [python_tests.log](python_tests.log),
[rust_tests.log](rust_tests.log), [native_parity.log](native_parity.log) and
[native_refresh.json](native_refresh.json).

Residual limits: this evidence covers the development proxy and installed
Python/GDAL/native combination, not other hosts. Native-required installations
must use a compatible binary; no Python fallback remains. The dedicated security
review owns the separate hostile-HTML containment gate. No production deployment
or full Python suite was performed for this package.

## Request-admission re-review

The repeated-upload HTTP409 failure is closed by the scoped request-boundary
correction. A copied context retained a prior request's released lifecycle lease;
the captured [failure stack](admission_failure_stack.log) identifies the failing
parent checkpoint before SBS raster processing.

Reviewed `wepppy/rq/submission_recovery.py`, its stub, the rq-engine HTTP middleware
and the four new ownership regressions. `inherit_lifecycle=False` at HTTP
admission creates a fresh context and acquires both Redis and filesystem fences.
The default remains `True` for nested operations, which continue checking their
parent lease. Context reset and ownership-safe release remain in `finally`.
An active owner still produces the existing conflict response; no ownership
check, timeout or authorization boundary was relaxed. The companion stub now
also includes the existing M1 `on_job_id` callback; the
[submission helper stubtest](admission_stubtest.log) passes.

[Ten focused tests](admission_tests.log) pass, including the actual middleware
under a copied closed context, active-owner rejection and nested lost-parent
rejection. The [independent real Redis/flock probe](security_admission_probe.log)
also verifies the filesystem fence after Redis ownership loss and cleanup.
The final [proxy browser log](proxy_browser.log) records three additional
consecutive successful uploads after failure recovery and reload.

No remaining correctness finding in this delta. Evidence covers the development
request path and owner-loss cases above; it does not establish performance under
production concurrency. The earlier native/UI and deployment limits still apply.
