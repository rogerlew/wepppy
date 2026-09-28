# ADR-0076: Continuous watershed runtime budget

## Status and provenance

Accepted direction, 2026-09-28; implementation pending. Decision venue: this
Codex/operator conversation (America/Los_Angeles). Participants: operator and
Codex. Decision owner: operator (“let's implement the year plus hillslopes timeout
please”). Implementer: Codex. Existing session commit authority applies.

## Decision

Replace the fixed12-hour continuous watershed child allowance with0.05seconds
per hillslope-year, rounded up to whole hours, retaining12 hours and any larger
caller pipeline allowance as floors. Use controller workload for preparation,
checked-out native run-file workload for no-preparation. Preserve all unrelated
stages, single-storm limits and graph dependencies. Record budget inputs in child
metadata. Exact contract: [WRT-01](../schemas/wepp-run-input-contract.md#continuous-watershed-runtime-budget-wrt-01).

## Rationale and alternatives

[Read-only wepp1 evidence](../investigations/20260928_wepp1_watershed_timeout_scaling/assessment.md)
matched123 successes to consumed artifacts. Years plus hillslopes explained
runtime much better than years alone; channels were nearly collinear with hills.
The observed same-binary95th-percentile rate was0.047seconds per hillslope-year.
A1,908-hillslope500-year run took8.76hours;1,000years reached year698 at12hours.
The policy allows27hours for the latter. Reject global timeout increases and
separately fitted channel weights. No scientific inputs/formulas are changed.

## Compatibility, risk and rollback

Metadata is additive. Valid prepared no-prep inputs take precedence over stale
NoDb values; legacy and modern prompt layouts remain supported. Invalid workload
fails before enqueue. Longer jobs occupy workers longer; the measured sample
is mostly one binary and100-year runs, with successful-job selection bias.
Runtime cleanup on timeout remains a known separate issue. No new dependencies,
services, automatic retries or deployment are authorized by this change.
Rollback restores enqueue defaults for new jobs; existing queued/failed jobs
retain their saved timeout. Do not mutate those jobs as part of rollout.
