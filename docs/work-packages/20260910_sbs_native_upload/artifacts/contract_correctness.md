# Native SBS contract correctness review

Independent reviewer: Codex correctness reviewer. Date: 2026-09-10.
Scope: proposed raster/control contracts, ADR-0065, shared-controller exception,
existing native APIs, upload callers and Disturbed/BAER UI integration.
Runtime inspection was read-only; no full suite or live-project mutation.

## Findings and disposition

1. **Medium: a batch-upload boundary can still conceal native failures.**
   `wepppy/microservices/rq_engine/upload_batch_runner_routes.py:336` calls
   `sbs_map_sanity_check` without translating processing exceptions into the
   canonical response. Lines 340-345 catch every exception from constructing
   `SoilBurnSeverityMap` and computing burn-class counts, log a warning and
   continue publishing a successful upload. For example, available summary
   helpers plus a missing native `read_color_table` API pass the first check,
   fail construction and can still produce success. The new unconditional
   native-failure contract therefore needs this caller included in the narrow
   compatibility work. Require explicit canonical failure for native dependency
   or execution errors; retain unrelated established optional-metadata policy.
   Include project and HUC upload callers in focused failure tests as well.
   **Resolved in contract:** the new Caller failure boundaries section explicitly
   covers run, HUC, batch and Flask operations and prohibits incomplete success.

2. **Low: previous-result behavior is underspecified.** The checkpoint lists
   prior results during a failed replacement, but the normative UI contract only
   prohibits putting errors into Summary. Both `Disturbed.startTask`
   (`controllers_js/disturbed.js:438`) and `Baer.startTask`
   (`controllers_js/baer.js:396`) currently erase Summary at submission time.
   State whether the previous accepted Summary remains while upload is pending
   and after failure, and whether a successful mutation followed by a failed
   summary fetch clears or retains the previous display. This avoids inventing
   conflicting UI behavior during implementation. Timeout text must continue
   to avoid asserting server rollback or cancellation.
   **Resolved in contract:** retain the last accepted Summary through replacement
   and failure until a successful result refresh; absent Summary stays empty.

## Confirmed feasibility and implementation obligations

- All five required functions exist in the current native module: raster
  summary, color-table read, color-table summary, reclassification and four-class
  export. Their current Python wrapper arguments match the native signatures.
  Removing the duplicate fallback engines requires no new dependency or native
  formula change.
- The native reclassification array is transposed into the existing WEPPpy
  convention; the native GeoTIFF writer preserves the source dimensions,
  transform and projection. Validate a nonsquare analytical raster so a transpose
  defect cannot hide in a square fixture.
- Four-class export accepts the original-source/current-display NoData union
  directly. Native export writes masked cells as 255; model reclassification
  retains its existing offset semantics. Do not change the latter while fixing
  exported masks. Verify source NoData, display NoData, white palette entries,
  unknown palette values, numeric breaks and both export palettes.
- Native NoData conversion currently casts values to integers. Test fractional
  and NaN metadata/pixels against the accepted upload validation boundary and
  prior behavior; do not turn formerly rejected inputs into silently masked
  successful rasters. The checkpoint now explicitly requires this evidence.
- Remove the caller-level fallback branches as well as the five exception-
  swallowing wrappers. `get_sbs_color_table` currently scans pixels if its counts
  summary is absent, and `sbs_map_sanity_check` has a full second raster path.
  Retain the explicit custom-color mapping interpretation and scalar helpers.
  A malformed native response must not trigger an alternate raster engine or
  become a cached successful result.
- Successful `loadModifyClass` currently uses the HTML adapter correctly.
  Preserve that result path. Its failure path calls the shared stacktrace helper,
  which also writes Summary; the SBS-only error path must avoid that side effect.
- Disturbed upload currently schedules BAER map/summary refresh on a timer and
  reports completion first. Verify actual refresh completion and rendered values,
  not only the upload response or a prior table. Native BAER upload has a separate
  event path that also needs coverage.
- Preserve the raw HTTP response metadata until distinguishing gateway HTML
  from JSON error messages. A JSON message containing angle brackets remains
  text. Formatted Details must use reconstructed inert elements, strip attributes,
  reveal its containing Details panel and clear stale errors after recovery.
  The dedicated security reviewer owns sanitizer/resource-loading acceptance;
  off-document parsing alone is not proof that parsing performs no network work.

## Disposition

Native-only raster processing and the bounded SBS Details exception are feasible
and consistent with the owner instruction. Approve the amended contract checkpoint.
The batch failure boundary and prior-result display findings are resolved by the
canonical amendments. The finite tag list, detached template, fresh element
construction and raw HTTP Content-Type discriminator also incorporate the
security review's clarifications. No remaining contract blocker was identified.

Final implementation review still requires focused native-failure tests, actual
Wallow pixel/mask parity and upload timing, hostile-HTML browser checks, failed
replacement/summary-fetch recovery and successful filename/table/map reload.
The full suite remains excluded by operator instruction.
