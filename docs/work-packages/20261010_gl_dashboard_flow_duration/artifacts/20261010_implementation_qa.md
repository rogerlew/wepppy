# Flow-duration implementation QA review

Reviewer: independent `/root/fdc_qa` agent, 2026-10-10. Reviewed the working tree
after checkpoint `c63f2cc52` and the independent
[correctness pass](20261010_implementation_correctness.md). No production code
was changed by this reviewer.

## Disposition

**QA pass.** No unresolved blocking maintainability or test-quality findings.
Release validation and final security sign-off remain separate gates.

The new daily-data module keeps population validation, conversion and ranking
outside the DOM. Controls and rendering are separate, bounded modules; existing
graph-loader/controller/rendering seams receive small additions. Raw promises
and ranked curves have explicit per-scenario/source caches. Readiness and outlet
ownership remain in a read-only route helper, with expected failures observable
as named unavailable sources and server logs. The implementation owner formatted
the new modules and tests during review to remove dense multi-statement lines.

## Finding closed during review

The new smoke test originally exported authenticated browser storage to the
fixed `/tmp/fdc-browser-auth.json` path despite never consuming it. QA escalated
the unnecessary session side effect to the implementation owner and security
reviewer. The owner removed both the export and subsequent chmod from the test;
direct source inspection confirms removal. The temporary session/config used by
other live regression tests must be cleaned up by the owner after those tests;
the security review tracks that separate operational residue.

## Test assessment and independent checks

- Focused Jest rerun through `wctl run-npm test`: **15 passed**, two suites.
  Hand-calculated ties/zero ranks, leap-day gaps, synthetic years, null/NaN,
  invalid values, warm-up groups, independent records, source filters, failed
  request retry and deferred activation races test observable behavior.
- Filesystem tests exercise real path/catalog/symlink boundaries. The malformed
  topology test uses the real Parquet reader; replacing NoDb hydration does not
  replace the failure boundary under test. The separate correctness review
  records eight passing pytest cases.
- The browser test exercises real controls, both sources, log-x hover, keyboard
  inspection, warm-up changes, resizing and request reuse. Optional retained
  Parquet-oracle comparison strengthens the recorded integration run. It is
  not a substitute for the small independent ranking oracle in Jest.
- Scoped tracked-file `git diff --check` passed. Broad tests and browser rollout
  claims belong to the orchestrator's final validation record, not this review.

## Non-blocking follow-ups and residual limits

1. `wepppy/weppcloud/static-src/tests/smoke/gl-dashboard-flow-duration.spec.js`
   duplicates the CAP/login machinery from `tests/smoke/a11y/axe-runs0.spec.js`.
   A small shared authenticated-login helper would reduce protocol drift and
   could also honor the existing environment credential convention. Keep that
   behavior-preserving extraction separate from this feature. Fixed `/tmp`
   summary/screenshot filenames should eventually use Playwright output paths
   if this smoke is expanded to parallel projects.
2. The renderer fixture added after the initial review now protects one-point
   zero flow on log x, literal scenario labels, hover, keyboard-readable output,
   all-hidden curves and explicit DOM cleanup. A fully empty population and
   hide/show transitions through the owning timeseries controller remain less
   directly covered than these renderer-level states.
3. The live example and loader timing do not establish browser memory/render
   bounds for arbitrarily large Omni catalogs. Current raw/curve caching avoids
   refetch and reranking for scale-only changes, but a representative large
   catalog browser measurement remains useful before adding approximation or
   more rendering machinery.

Rain-on-snow classification remains outside the delivered capability; this
review does not certify a classifier or working filter. The final operator
instruction removes its control, as recorded below.

## Standalone-child and renderer addendum

Reviewed the bounded follow-up after the initial pass. **QA pass remains.**
`flow_duration_context` recognizes the established
`_pups/omni/scenarios/<child>` lineage for shared parent topology while retaining
child-owned daily files and catalogs. Explicit `queryScenarioPath` metadata
selects that child when a `?pup` URL still names the parent run; composite child
run URLs keep their existing query context. The loader's display-name callback
uses the exact active child name without changing other Omni graph naming.
These small changes preserve the existing helper/loader boundaries.

The two parameterized filesystem cases exercise actual parent-shared topology
links for both query contexts. The focused JS test checks the active-pup selector
passed to the query boundary; the coverage test independently checks that absent
leading days remain inside the post-warm-up horizon. The new renderer fixture
asserts visible text, literal treatment of unsafe-looking labels, hidden-state
feedback and cleanup instead of relying solely on canvas call assertions.
This closes most of the original renderer-fixture follow-up above.

The implementation owner reports **10 boundary pytest cases and 18 focused Jest
tests passed** after these changes. This addendum independently inspects the
code and tests; it does not claim a second execution of that expanded set.
Temporary live-regression authentication cleanup and final security disposition
remain separately tracked.

## Final rain-on-snow control removal

**QA pass remains.** Read-only inspection confirms the final operator request
is implemented by removing the rain-on-snow checkbox, its unavailable message
and its `aria-describedby`/help element together from
`graphs/flow-duration-controls.js`. The daily source, x-scale and year-selection
controls retain their existing handlers and DOM assembly. The browser assertion
now requires zero matching controls, rather than a disabled checkbox. The
canonical contract, ADR-0085, user documentation and requirements register agree
that rain-on-snow exclusion is omitted. No classifier or population logic changed.
No broad test rerun was needed for this bounded removal; the implementation owner
is rerunning the live smoke. Final security disposition remains a separate gate.

## Browser performance instrumentation addendum

**QA pass remains.** Inspected the test-only `requestfinished` measurements and
the explicit redraw/heap snapshot. The installed Playwright type contract
confirms `timing().responseEnd` is elapsed milliseconds from request start and
`sizes().responseBodySize` is the encoded response-body byte count. The added
artifact fields contain aggregate numbers; they do not serialize request bodies,
headers, cookies or authentication state. No production behavior changes.

Interpret retained measurements with these limits:

- Request duration includes backend and transport work, rather than measuring
  server execution alone. Encoded body bytes exclude response headers and do
  not measure decoded JSON size or its memory footprint.
- `redrawMs` measures one synchronous `graph.render()` call in the final cached
  outlet/log-x/all-years state. It excludes subsequent browser painting and
  compositing, initial loading/ranking and a distribution of interaction times.
- `wholePageUsedHeapBytes` is an optional browser heap snapshot, not the FDC's
  incremental allocation, peak memory or total browser-process memory. Null is
  a valid unsupported result. Other dashboard components contribute to it.
- The listener collects matching finished requests. Following review, the owner
  added a polled equality check against the recorded request count before
  `Promise.all`; direct inspection confirms this completeness assertion. A single
  live project/run remains observational evidence, not a general performance
  threshold or a large-catalog capacity guarantee.

The orchestrator owns the active browser rerun and retained numerical results;
this addendum records independent code inspection without claiming that run's
completion.
