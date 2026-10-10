# Flow-duration preimplementation correctness review

Reviewer: independent agent `/root/fdc_contract_correctness`.
Reviewed: 2026-10-10 21:20 UTC, master starting revision
`189d10649793f0be1bdae5aeb90e8af9a810d977`; production implementation is unchanged.
Scope: the draft canonical FDC contract, ADR-0085, checkpoint and active package;
read-only source investigation. This review does not claim runtime conformance.

## Findings and disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| FDC-C01 | Medium | Requiring `Watershed.outlet_top_id` alone rejects valid peridot projects: the actual baseline has no value. | Resolved in contract execution boundary: registered explicit outlet, sole registered channel, or unique downstream root from network; then verify both translated ledger IDs. |
| FDC-C02 | Medium | Missing-day horizon and invalid-record precedence relative to warm-up were underspecified, allowing different populations under apparently identical controls. | Resolved in contract quality accounting: original date horizon and source year inventory; duplicates/dates checked before filtering; invalid flow/area affects eligible dates; absent dates and null/NaN counted separately from valid N. |
| FDC-C03 | Medium | Native NaN/Infinity cannot pass the existing Query Engine JSON response, so a naive numeric projection defeats the promised missing-versus-invalid policy. | Resolved in contract quality accounting: project flow/area as VARCHAR to preserve nonfinite tokens, then classify before conversion in the loader; preserve normal Query Engine behavior. |
| FDC-C04 | Low | Earlier scaffold-only authorization text conflicted with execution authorization. | Resolved: checkpoint now records authorized execution after the required ancestor commit. |

Post-fix review of the canonical contract completed after all four dispositions.
No unresolved high or medium contract findings remain.

## User outcome and valid states

Users compare independent daily scenario distributions, select hillslope or
routed outlet flow, choose familiar warm-up exclusions and linear/log x, and
inspect probability and discharge. Existing output files remain unchanged.

| State | Contracted outcome | Required implementation evidence |
| --- | --- | --- |
| No Omni / feature never used | Baseline curve, default two-year exclusion | Baseline-only browser and loader tests |
| Missing daily source or unresolved outlet | Named unavailable status; other sources/scenarios still usable | Actual file absence and topology tests |
| Empty source or warm-up exhaustion | Explicit empty status; no relaxed filter or invented zero curve | Empty/all-excluded fixtures |
| Populated writable or readonly source | Same readable curve semantics | Direct source ownership and query tests |
| Legacy source without chanwb | Hillslope still available | Legacy readiness fixture |
| Malformed records | Affected curve invalid; valid curves remain visible | Dates, duplicates, area, nonfinite and negative fixtures |
| Escaping path or mismatched catalog | Explicit unavailable state within existing authorization | Direct filesystem/catalog tests; security review |
| Archived source | Existing restore workflow required | Verify no hidden regeneration is introduced |
| Roads dashboard | FDC unavailable with explanation | Scope-specific browser/route test |

Input combinations are separate: both sources, all four year options, linear/log
x, visible/hidden scenarios, layouts, rapid changes and keyboard/touch inspection.
No claim of exhaustive runtime coverage is made before implementation.

## Independent source evidence

- `wepppy/nodb/core/watershed.py` peridot abstraction does not populate
  `_outlet_top_id`; its minimal one-channel case may omit `network.txt`.
- `wepppy/topo/peridot/peridot_runner.py::read_network` returns downstream Topaz
  channels mapped to upstream channels. The unique registered channel absent
  from upstream references identifies the outlet without numeric-order guesses.
- Direct PyArrow reads of `/wc1/runs/ei/eighty-five-synthetic` establish Topaz 24,
  WEPP element 412 and channel enumeration 128. Both baseline and `undisturbed`
  chanwb files contain `Elmt_ID=412`, `Chan_ID=128`.
- The model writer `/home/workdir/wepp-forest/src/wshchr.f90` writes `ielmt` and
  `idelmt(ielmt)` to those columns; `wshinp.for` assigns channel enumeration to
  `idelmt`. This agrees with the translator and actual Parquets.
- Actual metadata reports Streamflow in mm, Area in m² and Outflow in m³. The
  accepted conversions yield daily mean m³/s and preserve source volume.
- A direct `format_table` and Starlette `JSONResponse` experiment with NaN,
  Infinity and null reproduces the nonfinite transport failure behind FDC-C03.

## Residual risks and release gate

Contract gate: **pass**. Production release remains pending numerical, browser,
performance and direct filesystem/query tests, independent implementation review,
and the authorized forest restart/integration evidence. Commit the checkpoint
and this disposition as the required ancestor before production edits.

Particular coverage risks: actual fixture lacks zero-flow hillslope days;
`tests/wepp/interchange/test_watershed_chanwb_interchange.py` currently exercises
the different chnwb depth interchange, so its name is not evidence for the routed
volume source. Retain explicit zero/tie/one-point and multi-channel oracle tests,
independent-record date coverage, synthetic years 1–99, nonfinite JSON transport,
all-hidden legends and inverse-log hover tests.

Rain-on-snow remains visibly unavailable pending a verified classifier. Source
ownership checks are a page-load snapshot; the contract explicitly requires
reload after output regeneration and does not claim query-time race protection.
No new persisted or generated model artifacts are introduced; the observability
chain for this feature ends in source readback, query payload and visible graph.
