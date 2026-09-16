# Report field, interaction and valid-state matrix

Status: proposed implementation acceptance, not test results.
Authority: [report contract](../../../ui-docs/contracts/postfire-debris-flow-report-contract.md).

| Surface | Data/interaction authority | Required evidence |
| --- | --- | --- |
| Summary model/time | Accepted attempt, not selector or latest job | M1 accepted while M3 selected/running/failed; no relabeling |
| Coverage/area | v2 common support; v1 independent support; full area warning | Partial, complete, legacy, 41 km² and another basin; no confidence claim |
| Source/record | Accepted source/climate mode; frequency represented_years/year_min/year_max, wet_years separately | CLI and NOAA; no inferred continuous completeness, NOAA never named event catalog |
| Duration | One Rainfall window selector, initially 15; read-only window in section headings | Design/events and headings change together, fixed all-three-window threshold comparison |
| Design | `source`, `duration_minutes`, `return_interval_years`, intensity, accumulation, probability, status/reason | Exact saved values; unavailable stays unavailable; marker/row keyboard linkage |
| Inverse | `target_probability`, intensity, accumulation, status/reason | Null `probability` not confused with missing threshold; no source-derived return interval |
| Events | `event_id`, `row_ordinal`, date fields/status, intensity, window and total rainfall, probability | Unique count per duration; duplicate dates preserved; no observed-date inference |
| Event detail | `get_event` for exact ID, three duration rows inline after selected event | Stable focus and expanded/controlled relationship; first/last rows equally usable; unavailable duration visible |
| Filters/page | Minimum likelihood, year, allowlisted sort, existing bounded limit/offset | Blank filter keeps unavailable; numeric filter explains exclusions; Reset restores baseline |
| Units/precision | Unitizer, canonical mm/mm h⁻¹ probabilities 0–1 | SI/English update all views, exact probability invariant, tiny/saturated/null values |
| Race handling | Accepted assessment identity plus request generation | Late filter response and replaced attempt cannot mix rows/detail/summary |
| Saved-table projection | Planned additive reader; current catalog discards validated design/inverse rows | Same pinned snapshot, backward-compatible queries, preserved scalar/mask validation, corrupt/racing tables rejected |
| Empty/failed/stale | Existing publication/currentness contract | Never run, empty wet record, zero matches, partial, stale, prior accepted + failed new attempt |
| Invalid/hostile | Existing run access + bounded local validator | Unauthorized GET/query/download; path/event/filter abuse; corrupt hashes; sanitized errors |
| Downloads | Displayed CSV versus full canonical artifacts | Exact page/filter/units/identity context, null preservation, no truncated-full claim, hostile text cannot become formulas |
| Cache/privacy | No-store report/query/detail/CSV; inspect reused artifact downloads | Header tests, no persistent browser cache, unauthorized repeat denied |
| Observability | Existing module artifacts and archives | Authorized browsing; failed/partial records retained; restore gives same report identity |
| UX/shell | Existing Pure shell, tables, Unitizer and native controls | Desktop/narrow, keyboard, themes, no duplicate initialization/controls, readable warnings |
| Chart meaning | Intensity x-axis, fixed 0–100% likelihood y-axis, labeled saved markers | Near-100% points not exaggerated; window/recurrence/rainfall/likelihood understandable without hover |

Input matrix: M1/M3 × CLI/NOAA × 15/30/60; simulation/calendar/invalid labels;
v1 M1/v2 M1/v2 M3; numeric endpoints/interior/null; default/filter/sort/page/unit
actions. Runtime-state matrix is the report contract's Valid states table.
Use targeted pairwise fixtures plus explicit high-risk combinations above; do
not call a request-parameter matrix exhaustive runtime-state coverage.
