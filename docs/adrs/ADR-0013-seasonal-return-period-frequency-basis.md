# ADR: Seasonal Return-Period Frequency Basis

Status: Accepted  
Date: 2026-07-06  
Review Date: 2026-08-06

## Context

WEPP return-period reports allow users to exclude months from the frequency analysis. In the `unrestrained-irruption` comparison on `wepp1`, excluded winter and shoulder-season months left no top-ranked runoff or peak-discharge events for the undisturbed case. The UI also hid missing measure tables, making it unclear whether no events existed or the report failed to render.

The report already filtered event counts by excluded months before computing `days_in_year` for displayed Weibull return periods. The CTA recurrence-rank helper still used a fixed 365.25-day basis when selecting recurrence rows, so the selected row and displayed seasonal `weibull_T` were not explicitly tied to the same filtered event window.

## Decision

CTA return-period row selection will use the same effective days-per-year basis as the filtered report. When months are excluded, the report computes `days_per_year = filtered_event_count / filtered_year_count` and passes that value into the Weibull rank-selection helper. With no month exclusion, the report continues to use the staged event-count basis for the selected run.

The UI will always render the core return-period measure sections: precipitation depth, runoff, peak discharge, and sediment yield. If a core measure has no recurrence rows after the selected filters, the report shows the measure title and a no-events message instead of omitting the section.

## Decision Provenance

Decision Venue: Codex operator session, 2026-07-06 13:30 PDT  
Participants Present: Roger Lew, Codex  
Decision Owner(s): Roger Lew / WEPPcloud maintainer  
Implementer(s): Codex

## Change Summary

Old behavior:
- CTA row selection used `years * 365.25` samples and divided periods by `365.25`.
- The final row displayed `weibull_T` using filtered report `days_in_year`.
- The UI skipped measure sections missing from `report.return_periods`.

New behavior:
- CTA row selection accepts a `days_per_year` basis.
- WEPP return-period reports pass the filtered report `days_in_year` into CTA row selection.
- Core WEPP return-period measure sections remain visible and show "No events" when filtered recurrence rows are absent.

## Rationale

Month exclusions define a seasonal frequency-analysis window. Users expect both the selected recurrence event and the displayed return-period value to use that same window. Using the filtered event-count basis keeps recurrence selection, displayed `weibull_T`, and `num_events` internally consistent.

Rendering empty core sections makes the report state explicit. For the observed undisturbed run, filtered months still had small modeled runoff and peak-flow values in precipitation rows, but no top-ranked runoff or peak-discharge recurrence rows survived the selected filters.

## Alternatives Considered

1. Keep CTA row selection on 365.25 days and only document that `weibull_T` is seasonalized - rejected because the selected row can differ at rank boundaries and the contract remains surprising.
2. Hide missing measure sections as before - rejected because users interpret the missing section as a broken report or unavailable measure rather than a no-events result.
3. Convert month-excluded CTA to annual-maximum selection - rejected because it changes the requested `cta` method rather than seasonalizing its sample basis.

## Consequences

Seasonal CTA recurrence rows may shift by one or more ranks when the filtered days-per-year basis crosses an integer rank boundary. Existing cached return-period JSON generated before this change can remain stale until regenerated. The UI change is backward-compatible with existing report payloads because missing measure keys now render as empty states.

## Evidence

- Production comparison runs on `wepp1`: `fine-toothed-phosphate` and `unrestrained-irruption`.
- Excluded-month cache inspected: `return_periods__exclude_yr_indxs=0,1__exclude_months=1,2,3,4,5,11,12.json`.
- The undisturbed excluded-month report had precipitation rows but no runoff, peak-discharge, or sediment-yield recurrence rows after rank filtering.
- Regression tests: `tests/test_all_your_base_stats.py`, `tests/wepp/reports/test_return_periods_dataset.py`, `tests/weppcloud/routes/test_wepp_bp.py`, and `tests/weppcloud/routes/test_pure_controls_render.py`.

## Risk and Rollback Notes

Risk: regenerated seasonal CTA reports can select a different event near recurrence rank boundaries. This is intentional for consistency with the seasonal analysis window. Rollback is to stop passing `days_per_year` to `weibull_series` and remove the optional helper parameter, but rollback should only be used if maintainers decide CTA recurrence selection must remain annual-calendar based even when users exclude months.

## Implementation Notes

The shared `weibull_series()` default remains `365.25` days per year for existing callers. The seasonalized basis is only supplied by the WEPP return-period report path.
