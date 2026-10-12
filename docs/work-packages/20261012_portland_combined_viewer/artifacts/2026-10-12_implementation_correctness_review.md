# PCV-01 implementation correctness review

## Metadata and current verdict

- Reviewer: independent `contract_correctness` agent.
- Initial review: 2026-10-12 16:48 UTC.
- Accepted ancestor: `d75460acc4d73d0d890019f332b8c1965bf6362a`, committed 2026-10-12 16:33:30 UTC; it precedes the currently uncommitted implementation.
- Scope: combined route/options, generator, Portland catalog integration, focused Deck.gl controller/data module, offline native preparation, corresponding tests and retained evidence. Unrelated `docs/projects/i-crews/st_joe/` changes excluded.
- Authority: [PCV-01](../../../ui-docs/contracts/combined-watershed-viewer-contract.md); unchanged shared controller, CSRF, output-scope, artifact observability, and generated-artifact validation contracts.
- Rechecks: 2026-10-12 16:53 UTC, 17:05 UTC, 17:30 UTC, and 17:33 UTC; final role and fixture recheck 17:35 UTC. All six medium findings are resolved. Final UI changes, real pointer acceptance, and same-session role revocation also pass. **Code correctness and QA pass; full forest-readiness verdict remains conditional on the corrected broad-test receipt below.** Independent security review remains separate.

## Findings

| ID | Severity | Surface and evidence | Required correction | Status |
| --- | --- | --- | --- | --- |
| PCV-I01 | Medium | `static/js/gl-dashboard/combined-viewer.js`, `initialize()` and control handlers: controls initially remained usable while sequential loading appended partial features. A unit/variable/range event could call `render()` before completion, draw partial data, and report the full requested watershed count as loaded. | Disable result controls until all runs load, or gate rendering on an explicit ready state; regress the deferred second-run boundary. | Resolved: controls are disabled until complete; independent actual-module deferred-network probe confirms no partial layer or loaded status. |
| PCV-I02 | Medium | `combined_viewer_preparation.py`, publication loops and `rollback()`: expected full hashes were saved before copying directly into final paths. An interrupted copy leaves a partial file whose checksum prevents the advertised rollback and retry. | Publish completed files atomically without overwriting unknown files; retain failure evidence and test interruption at the real publication boundary. | Resolved: exclusive atomic `os.link` publication; reviewer reran real native writer with interruption before and after publication, and both rollbacks succeeded. |
| PCV-I03 | Medium | `combined-viewer-data.js:joinRun()` requires a finite `Total Pollutant` whenever NoDb options say phosphorus is valid. Missing/null optional output throws before required runoff/loss data can render, and the controller disables the entire collection. | Base phosphorus availability on valid options plus actual finite output, preserving all-zero configured output. Missing optional phosphorus must disable only that choice, with explicit unavailable selection behavior. | Resolved: actual rows refine phosphorus availability, controller updates choice after loading; direct module probe preserves the four measures and configured zero phosphorus. |
| PCV-I04 | Medium | `combined-viewer-data.js:joinRun()` checks seen WEPP IDs against native rows but not a bijection of unique Topaz IDs to WEPP IDs. Two different TopazIDs mapped to one WEPP row pass and receive the same value. Offline preparation catches this for its own runs, but general admitted public/owner collections also use this runtime path. | Require a complete one-to-one unique-identifier mapping while retaining all polygon fragments belonging to the same TopazID. Test duplicate mapping and legitimate fragments separately. | Resolved: mapping uniqueness and complete metadata/native/geometry coverage checked; direct duplicate, missing-metadata-row, and legitimate-fragment probes pass. |
| PCV-I05 | Medium | `combined_watershed_viewer_generator.py:collection_metadata()` dereferences `ron.map.extent`; `Ron` initializes a valid new run with `_map=None`, and its map property explicitly permits None. The resulting AttributeError escapes both viewer and generator readiness handling. | Validate absent map/extent and absent/empty watershed summaries before dereferencing them; surface an explicit actionable readiness result from both routes. | Resolved: explicit absent-map/summary validation and HTTP 409 handling in viewer and generator; focused generator and route regressions added. |
| PCV-I06 | Medium | Real non-admin browser audit renders polygons and native pointer events reach the canvas, but Deck never emits the layer click. The reviewer confirmed loaded Deck 9.4/Mjolnir assigns processing wall time to inputs; synchronous software-GPU picking takes about 2.5 s, exceeding its 250 ms tap duration despite a native down/up gap of 0.3 ms. | Retain the measured failure, apply a documented viewer-scoped gesture correction, and repeat real picking plus drag/pan/zoom acceptance. | Resolved: focused 5000 ms click duration; actual wrapper default-isolation probe and non-debug mouse/drag/pan/zoom audit pass. ADR-0087 records the bounded tradeoff. |

Paths in the table are relative to `wepppy/weppcloud/`. Source line numbers may shift while the author addresses findings.

## Direct review probes

The reviewer executed the production `joinRun` module through Node, changing only its import URL for the Node loader. A configured run with finite required values and null total pollutant threw `proof: phosphorus is missing for hillslope 1.` A run with mapping `{22: 1, 33: 1}`, two valid polygon features, and one native row returned both TopazIDs with loss `20`, demonstrating PCV-I03/I04 independently of mocks for the join function.

The reviewer ran the real native writer through `wctl exec weppcloud python` on a temporary three-hillslope fixture, injecting an `OSError` only after the final publication stream wrote partial bytes. Preparation reported the injected failure and preserved READONLY. Calling the real rollback then raised:

    Changed or missing manifest file: wepp/output/interchange/loss_pw0.hill.parquet

Temporary review fixtures were removed by their temporary-directory context. No production writes, repository runtime edits, or account changes were performed by this reviewer.

Post-fix independent probes:

- Real native writer, injected interruption before atomic publication: rollback `rolled_back`, published directory absent, READONLY unchanged, native writer identity present.
- The same probe immediately after a real atomic publication: identical successful recovery and preservation results.
- Actual data module: null optional phosphorus leaves runoff `5`, subrunoff `1`, baseflow `0`, loss `20`; configured phosphorus `0` remains `0`. Duplicate and incomplete mappings raise explicit errors; two fragments of one TopazID remain two geometries.
- Actual controller/data/map modules in jsdom, with Deck and network adapters isolated: while the second run is pending, selector disabled, status `Loading`, and no hillslope layer; after completion, selector enabled and status `2 watersheds · 2 hillslopes loaded.` with exactly two features. This exercises the changed asynchronous controller boundary, not a replacement initialization function.
- Final controller recheck: unit changes retain the exact same FeatureCollection object, allowing Deck to reuse geometry while `getFillColor` update triggers refresh colors. An explicitly unavailable phosphorus state clears old details, legend canvas and legend text, disables the feature selector, and leaves no hillslope layer. Both behaviors were exercised through the actual controller module in jsdom.
- Actual map-wrapper recheck through Node confirms ordinary callers still omit `eventRecognizerOptions` from Deck construction, while the focused viewer's explicit option passes unchanged. All 13 hashes in `evidence/runtime-source-identity.json` match the reviewed runtime files, including the shared wrapper.

## Confirmed behavior and evidence limits

- Canonical checkpoint chronology is correct: source baseline `dc6f3879e`, then reviewed standalone checkpoint `d75460acc`, then implementation.
- Entry authorization remains bounded to explicit PUBLIC, catalog/member, owner, or Admin/Root grants. Ordinary ownerless data authorization was not edited. Generator no longer assigns roles.
- Route parsing rejects malformed collection JSON, invalid view values/ranges, unknown variables/units, and oversize unique collections. Titles/config JSON use safe template/DOM serialization; generated URLs use URL encoding.
- Extent union now expands across all runs using a copy of source bounds, with actual configuration from NoDb. Existing link fields and encoded title are preserved.
- The data module correctly uses already averaged native volume/mass fields, native area in ha, exact water and mass unit factors, and preserves numerical zero. Soil loss is not confused with sediment yield or the full dashboard's t/ha display.
- Sequential per-run loading bounds service concurrency to one run's geometry/query pair. Successful loading preserves polygon fragments and creates composite feature keys.
- The reviewer parsed `evidence/forest-preparation.jsonl`: 63 complete runs, 24,669 average hillslope rows, minimum native area 0.09 ha, exact source-decimal comparison and complete geometry join recorded for every run. This resolves the contract review's real-Portland area-fallback risk. The reviewer inspected the comparison implementation but did not independently rerun all 63 conversions.
- `evidence/browser-member.log` now completes successfully: one browser test passed in 9.9 minutes. It covers all nine real collections, each of five variables in both units, numerical samples, generator and share/reload, anonymous entry denial, and normal preparation-manifest/Parquet browse/download byte parity. The reviewer also inspected `current-conditions.png`: colored watershed polygons and the requested English loss legend are actually rendered, not just a basemap canvas.
- Focused Python log `/tmp/pcv-target-tests.log`: 32 passed, four existing dependency deprecation warnings. Full Jest log `/tmp/pcv-npm-test.log`: 118 suites and 965 tests passed. Final receipts should be retained in the package before handoff.
- `evidence/source-parity.json` records all 919 source files across 63 production/forest runs matching, 24,669 hillslope rows, and one writer identity. Current preparation manifests were regenerated rather than assigning a new writer identity to old files.

## Valid-state and failure review

| State | Current assessment |
| --- | --- |
| Empty viewer / empty generator GET | Explicit empty viewer and form paths present. |
| Missing required data / failed data request | Main loading error clears rendered features and displays an actionable incomplete-collection message. |
| Populated native average output | Correct fields, dimensions, zero behavior, and legacy colormap/range normalization by inspection and focused tests. |
| Legacy polygon fragments | Preserved as multiple geometries sharing one unique hillslope value; this is compatible with one-to-one identifier mapping. |
| Optional phosphorus missing with valid options | Corrected under PCV-I03; required variables remain usable. |
| Partial asynchronous loading | Corrected under PCV-I01; deferred-network probe confirms no premature success. |
| Interrupted final publication | Corrected under PCV-I02; atomic publication permits bounded rollback before/after interruption. |
| Unknown or externally changed derived output | Refused; rollback verifies all known present outputs before deleting any. |
| READONLY preparation | Staging/native conversion and source hashes preserve READONLY; final permission/browser evidence remains a deployment-readiness gate. |

Input and identity combinations are separately covered by route tests and the authenticated browser matrix. Unit tests stub route metadata and account objects; they cannot substitute for real membership revocation or actual geometry/query consumption. Completed browser evidence covers actual geometry/query/display consumption and the final mouse audit. `evidence/browser-revoked.log`, `browser-restored.log`, and `account-restoration.json` establish member 200, revoked 403, then restored independent Admin 200 in the same session without relogin. The forest dev-agent's exact original roles were restored; no production membership was changed.

## Maintainability and test-quality assessment

QA pass with no high/medium maintainability finding. The change keeps collection admission, metadata/URL construction, data normalization/joins, map wiring, and explicit offline preparation in small bounded modules. Existing Deck/basemap/key helpers and the native writer are reused without changing unrelated dashboard or general authorization behavior. Stable FeatureCollection identity addresses repeated geometry processing without introducing a second cache or invalidation mechanism.

Tests exercise meaningful behavior rather than literal constants alone: known independently computed volume/area values, zero versus missing optional state, identifier uniqueness/completeness, repeated geometry fragments, special-character URL encoding, source preservation, exclusive publication interruptions, changed-output refusal, and forged rollback manifests. The native preparation tests use the real writer and real filesystem; failure injection is placed at publication before/after the actual link primitive. Canonical archive/restore is also real at the content boundary. Route stubs are acceptable for request/error combinations because real browser evidence separately covers session and data delivery boundaries.

The first broad Python run exposed test import isolation in one new bounds fixture after 8,764 passes and 126 skips. Its dotted module import patched a stale parent-package attribute while the route's lazy from-import resolved the current `sys.modules` object, reaching a real fixture path and returning 409. The reviewer approves the three new route-fixture changes to `importlib.import_module`, matching the preexisting generator-route test. They patch the actual dependency used by the route without weakening assertions or changing runtime code. A corrected broad result is still required; the stopped run is not a pass.

Residual test-maintenance gap: deferred controller loading and unavailable-phosphorus UI cleanup currently have independent actual-module reviewer probes, while the committed Jest cases target the data module. If this controller grows, preserve those small DOM scenarios as focused automated regressions; the long all-nine smoke test should not become the only place to diagnose controller state failures. This is a low-risk follow-up, not a request to duplicate successful broad suites or block this bounded repair.

## Pointer acceptance investigation

The real mouse audit found a distinct interaction failure after the all-nine numerical acceptance passed. The reviewer inspected the actual loaded Deck 9.4 source retained at `/tmp/pcv-deck.pretty.js`, the native-event/recognizer timings in `/tmp/pcv-debug-handler.log` and `/tmp/pcv-debug-async2.log`, and the production map/layer callback wiring. Picking identifies the polygon correctly. Mjolnir overwrites its input time with `Date.now()` before computing `deltaTime`; synchronous drawing during pointerdown therefore inflates the recognized press duration to 2346–2479 ms. Native pointerdown/up timestamps differ by only 0.3 ms. The attempted asynchronous pick still incurs the synchronous draw stall. No callback or container wiring defect was found.

Deck exposes this setting through its documented [eventRecognizerOptions API](https://deck.gl/docs/api-reference/core/deck#eventrecognizeroptions-object); Mjolnir documents [Tap.time](https://visgl.github.io/mjolnir.js/docs/api-reference/tap) as maximum press duration. The reviewer approves testing `click: {time: 5000}` only for this combined viewer, supplied at Deck construction with the shared wrapper's optional argument defaulting to undefined. Preserve pointer count, movement thresholds, pan arbitration, and double-click settings. This is smaller than intercepting DOM events, duplicating GPU picks, or patching third-party internals.

The bounded accommodation changes a stationary release of up to five seconds into a selection; it does not solve stalls longer than five seconds or the software-GPU cost itself. Infinity would additionally remove the held-press cutoff without evidence that this broader behavior is needed. Retain the measured timings and a concise threshold decision record. Acceptance must demonstrate a real click populates correct run-specific details, dragging pans without changing the selected details, and wheel/view sharing remains correct. Numeric rendering and programmatic `pickObject` alone cannot close PCV-I06.

Final disposition: [ADR-0087](../../../adrs/ADR-0087-combined-viewer-pointer-duration.md) and `evidence/pointer-diagnosis.json` retain the scope and observed timings. The non-debug served-code audit `/tmp/pcv-final-audit.log` passed in 2.0 minutes: real polygon click, selection unchanged after drag, pan/zoom/share, final manifest/Parquet download byte parity, and matching final query samples for all nine rendered collections. PCV-I06 is closed. The finite-duration/software-renderer limitation remains explicit.

## Remaining release evidence

1. Retain the corrected broad Python result; the first run stopped on the repaired route-fixture import issue after 8,764 passes and 126 skips. All six implementation findings and the 32 focused Python/965 Jest tests pass. The author is running the full WEPPcloud subtree and then the required broad gate after the fixture correction.
2. Final writer identity is reconciled through actual 63-run regeneration: `evidence/source-parity.json` names preparation hash `71f9a2e5f922bc7f830670a27bd55bee8057a812e7c3ed1c660df040e8383b2b`, matching the current helper. Final query samples and served artifact bytes match the regenerated files.
3. Same-session revoked-member, restored independent Admin, and final member-audit receipts are accepted, including pan/zoom sharing, owner/public grants, aliases, mixed denial and CSRF. Member all-nine numerical, generator, share/reload and normal browse/download evidence also passed. Verify sample run links against the full production run workflow during rollout; forest copies are intentionally partial model clones.
4. Canonical archive/restore evidence is accepted: `evidence/archive-check.py` uses actual `archive_rq`/`restore_archive_rq` on an isolated real-run copy, with queue/status/lock adapters isolated; final `evidence/archive-restore.json` records 70 files with exact byte parity, including the current preparation manifest and consumed Parquet. Those two hashes also match the final browser audit's download checks. No hidden-only artifact exception is approved.
5. `evidence/runtime-identity.json` records an isolated forest preparation under production UID/GID 1002:130 and umask 0022, then successful native Parquet readback by forest UID/GID 1000:993. This supports forest readiness; actual production mount/native/image parity remains an explicit rollout preflight in `rollout-handoff.md`. Retain required broad/frontend checks and the dedicated security review. Forest readiness is separate from a completed production repair.

Residual coverage gap: runtime geometry checks currently establish nonempty feature lists and truthy geometry objects, not complete polygon topology validity. The all-nine real-render evidence must establish actual retained geometry renders; do not infer that from synthetic empty-coordinate test fixtures or row counts alone.
