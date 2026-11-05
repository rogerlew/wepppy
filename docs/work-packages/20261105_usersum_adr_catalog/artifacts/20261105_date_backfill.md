# ADR date metadata backfill

Date: 2026-11-05. Operator direction: “backfill the dates please.”

## Scope and method

Add an explicit preamble `Date: YYYY-MM-DD` to the 47 ADRs lacking one. The date
comes from each record's original decision/venue evidence, not a later amendment,
implementation validation, file modification time, or numeric identifier. All 47
have documentary evidence; no invented date or git-timestamp fallback is needed.
Git creation history was checked as corroboration only.

Where the original venue records both local and UTC dates, preserve the first
calendar date in that venue statement. Original timezone/provenance prose remains
unchanged. This explains ADR-0053 (September 8 Pacific), ADR-0055 (September 9 UTC),
and ADR-0134 (November 3 UTC). Original decision dates remain distinct from later
acceptance/validation, including ADR-0069, ADR-0075, ADR-0088 and ADR-0129.

Compatibility and validation: metadata-only additions, with every prior byte of
ADR content retained. The existing catalog date parser/order is unchanged. Verify
all 138 dates with that parser and read back the live catalog's complete set,
dates and order; check all changed live detail pages expose their Date field.
No tests or runtime code are changed. No worker reload or index rebuild is needed.

## Source evidence

| ADR source | Backfilled date | Evidence already present in that source |
| --- | --- | --- |
| [ADR-0048-mofe-per-ofe-hillslope-clipping](../../../adrs/ADR-0048-mofe-per-ofe-hillslope-clipping.md) | 2026-09-04 | Decision Venue: 2026-09-04 04:31 PDT (11:31 UTC). |
| [ADR-0049-fork-preparation-read-retry](../../../adrs/ADR-0049-fork-preparation-read-retry.md) | 2026-09-07 | Decision venue: incident-remediation session, 2026-09-07 UTC. |
| [ADR-0052-staley-m3-upstream-terrain](../../../adrs/ADR-0052-staley-m3-upstream-terrain.md) | 2026-09-08 | Original engineering terrain approval and decision venue, 2026-09-08 America/Los_Angeles. |
| [ADR-0053-staley-m3-offline-soil-thickness](../../../adrs/ADR-0053-staley-m3-offline-soil-thickness.md) | 2026-09-08 | Original venue: 2026-09-08 Pacific / 2026-09-09 UTC; retain its first calendar date, not the subsequent owner decision. |
| [ADR-0054-staley-dnbr-normalization](../../../adrs/ADR-0054-staley-dnbr-normalization.md) | 2026-09-09 | Status and provenance: accepted for backend implementation, 2026-09-09. |
| [ADR-0055-staley-project-watershed-scope](../../../adrs/ADR-0055-staley-project-watershed-scope.md) | 2026-09-09 | Original venue explicitly recorded 2026-09-09 04:18 UTC (2026-09-08 Pacific); retain its recorded UTC date. |
| [ADR-0058-staley-horn-slope](../../../adrs/ADR-0058-staley-horn-slope.md) | 2026-09-09 | Status and provenance: conversation recorded 2026-09-09 UTC. |
| [ADR-0059-staley-m1-prepared-predictors](../../../adrs/ADR-0059-staley-m1-prepared-predictors.md) | 2026-09-09 | Accepted status and decision venue, 2026-09-09 America/Los_Angeles. |
| [ADR-0060-pseudo-barc256-fixture-derivation](../../../adrs/ADR-0060-pseudo-barc256-fixture-derivation.md) | 2026-09-09 | Accepted test-artifact status and decision venue, 2026-09-09 America/Los_Angeles. |
| [ADR-0061-gridmet-persistent-queue-recovery](../../../adrs/ADR-0061-gridmet-persistent-queue-recovery.md) | 2026-09-09 | Accepted status and incident decision venue, 2026-09-09 PDT. |
| [ADR-0062-staley-local-rainfall-results](../../../adrs/ADR-0062-staley-local-rainfall-results.md) | 2026-09-09 | Decision Venue: execution conversation, 2026-09-09 America/Los_Angeles; commit occurred the next day. |
| [ADR-0064-builder-disturbed-default](../../../adrs/ADR-0064-builder-disturbed-default.md) | 2026-09-10 | Original accepted status and venue, 2026-09-10; later Builder exception does not replace it. |
| [ADR-0065-sbs-native-required](../../../adrs/ADR-0065-sbs-native-required.md) | 2026-09-10 | Status and provenance: project-operator acceptance, 2026-09-10 America/Los_Angeles. |
| [ADR-0066-staley-valid-support](../../../adrs/ADR-0066-staley-valid-support.md) | 2026-09-11 | Original accepted direction, 2026-09-11; later analysis-support ratification is 2026-09-14. |
| [ADR-0069-mofe-ground-cover-propagation](../../../adrs/ADR-0069-mofe-ground-cover-propagation.md) | 2026-09-18 | Original decision venue, 2026-09-18 America/Los_Angeles; execution continued on 2026-09-19 UTC. |
| [ADR-0070-cover-defaults-and-kslast-omission](../../../adrs/ADR-0070-cover-defaults-and-kslast-omission.md) | 2026-09-19 | Original decision venue, 2026-09-19 America/Los_Angeles. |
| [ADR-0071-omni-thinning-30-50](../../../adrs/ADR-0071-omni-thinning-30-50.md) | 2026-09-20 | Original decision venue, 2026-09-20 America/Los_Angeles. |
| [ADR-0072-continuous-hillslope-timeout](../../../adrs/ADR-0072-continuous-hillslope-timeout.md) | 2026-09-23 | Accepted status and operator decision venue, 2026-09-23 America/Los_Angeles. |
| [ADR-0073-disturbed-thinning-soil-lookup](../../../adrs/ADR-0073-disturbed-thinning-soil-lookup.md) | 2026-09-25 | Accepted status, decision venue and reviewed checkpoint, 2026-09-25 UTC. |
| [ADR-0074-omni-thinning-60-70](../../../adrs/ADR-0074-omni-thinning-60-70.md) | 2026-09-25 | Accepted status and decision venue, 2026-09-25 America/Los_Angeles. |
| [ADR-0075-single-user-defined-inputs](../../../adrs/ADR-0075-single-user-defined-inputs.md) | 2026-09-25 | Original product-direction acceptance and venue, 2026-09-25; ignore later September and October amendments. |
| [ADR-0076-watershed-runtime-budget](../../../adrs/ADR-0076-watershed-runtime-budget.md) | 2026-09-28 | Original accepted status and decision venue, 2026-09-28; ignore October amendment. |
| [ADR-0082-prism-historic-wepp-forcing](../../../adrs/ADR-0082-prism-historic-wepp-forcing.md) | 2026-10-08 | Accepted status and decision venue, 2026-10-08 America/Los_Angeles. |
| [ADR-0088-soil-anisotropy-overrides](../../../adrs/ADR-0088-soil-anisotropy-overrides.md) | 2026-10-12 | Original Decision provenance venue, 2026-10-12; DM-01 amendment on October 28/29 is separate. |
| [ADR-0092-prism-temperature-inversion-midpoint-proposal](../../../adrs/ADR-0092-prism-temperature-inversion-midpoint-proposal.md) | 2026-10-13 | Operator acceptance and decision venue, 2026-10-13; later UTC validation is separate. |
| [ADR-0094-wmesque-priority-and-sync-policy](../../../adrs/ADR-0094-wmesque-priority-and-sync-policy.md) | 2026-10-14 | Accepted status and decision venue, 2026-10-14 UTC. |
| [ADR-0095-terrain-helper-strict-least-cost-breach](../../../adrs/ADR-0095-terrain-helper-strict-least-cost-breach.md) | 2026-10-16 | Accepted status and decision venue, 2026-10-16 UTC. |
| [ADR-0096-new-project-no-scaling-default](../../../adrs/ADR-0096-new-project-no-scaling-default.md) | 2026-10-16 | Decision venue: conversation recorded 2026-10-16 17:57 UTC. |
| [ADR-0097-maca-projection-selection-and-ccsm4-member](../../../adrs/ADR-0097-maca-projection-selection-and-ccsm4-member.md) | 2026-10-16 | Decision and provenance: operator conversation, 2026-10-16 UTC. |
| [ADR-0099-mofe-physical-water-consumers](../../../adrs/ADR-0099-mofe-physical-water-consumers.md) | 2026-10-20 | Accepted status and decision venue, 2026-10-20. |
| [ADR-0100-wepp-gregorian-execution-calendar](../../../adrs/ADR-0100-wepp-gregorian-execution-calendar.md) | 2026-10-21 | Accepted status and engineering decision venue, 2026-10-21 America/Los_Angeles. |
| [ADR-0101-physical-water-allocation-and-routing](../../../adrs/ADR-0101-physical-water-allocation-and-routing.md) | 2026-10-21 | Original partial acceptance and decision venue, 2026-10-21 America/Los_Angeles. |
| [ADR-0102-roads-modeled-area-accounting](../../../adrs/ADR-0102-roads-modeled-area-accounting.md) | 2026-10-22 | Reviewed acceptance checkpoint and decision venue, 2026-10-22 UTC. |
| [ADR-0103-roads-segment-loss-source-attribution](../../../adrs/ADR-0103-roads-segment-loss-source-attribution.md) | 2026-10-22 | Accepted status and decision venue, 2026-10-22 America/Los_Angeles. |
| [ADR-0106-culvert-jwt-renewal](../../../adrs/ADR-0106-culvert-jwt-renewal.md) | 2026-10-26 | Accepted status and decision venue, 2026-10-26 UTC. |
| [ADR-0121-depend-bounded-root-search](../../../adrs/ADR-0121-depend-bounded-root-search.md) | 2026-10-31 | Original decision venue and revision-4 acceptance, 2026-10-31 America/Los_Angeles. |
| [ADR-0122-erod-subgrid-interval-support](../../../adrs/ADR-0122-erod-subgrid-interval-support.md) | 2026-10-31 | Original decision venue and revision-4 acceptance, 2026-10-31 America/Los_Angeles. |
| [ADR-0123-roads-nonzero-inflow-sediment-boundary](../../../adrs/ADR-0123-roads-nonzero-inflow-sediment-boundary.md) | 2026-10-31 | Original user/Codex decision session and revision-4 acceptance, 2026-10-31 America/Los_Angeles. |
| [ADR-0124-param-rounded-continuity-denominator-sign](../../../adrs/ADR-0124-param-rounded-continuity-denominator-sign.md) | 2026-10-31 | Original decision venue and revision-4 acceptance, 2026-10-31 America/Los_Angeles. |
| [ADR-0127-retention-volume-prototype](../../../adrs/ADR-0127-retention-volume-prototype.md) | 2026-11-01 | Original bounded-experiment decision venue, 2026-11-01 America/Los_Angeles. |
| [ADR-0128-retention-frost-consumer-experiment](../../../adrs/ADR-0128-retention-frost-consumer-experiment.md) | 2026-11-01 | Original bounded-experiment decision venue, 2026-11-01 America/Los_Angeles. |
| [ADR-0129-conservative-interception-allocation](../../../adrs/ADR-0129-conservative-interception-allocation.md) | 2026-11-01 | Original decision venue and integration admission, 2026-11-01; final compatibility acceptance on November 2 is separate. |
| [ADR-0131-donor-limited-freeze-restoration](../../../adrs/ADR-0131-donor-limited-freeze-restoration.md) | 2026-11-02 | Original decision venue and bounded integration acceptance explicitly say November 2, 2026. |
| [ADR-0132-optional-ssurgo-retention-builder](../../../adrs/ADR-0132-optional-ssurgo-retention-builder.md) | 2026-11-02 | Original decision authority, venue and bounded acceptance, 2026-11-02 America/Los_Angeles. |
| [ADR-0133-native-mofe-coefficient-ownership](../../../adrs/ADR-0133-native-mofe-coefficient-ownership.md) | 2026-11-02 | Decision and provenance: repository session, 2026-11-02 America/Los_Angeles. |
| [ADR-0134-specialized-revegetation-reference-port](../../../adrs/ADR-0134-specialized-revegetation-reference-port.md) | 2026-11-03 | Decision venue explicitly records 2026-11-03 UTC (2026-11-02 America/Los_Angeles); retain its recorded UTC date. |
| [ADR-0135-roads-settings-controls](../../../adrs/ADR-0135-roads-settings-controls.md) | 2026-11-03 | Accepted status and original decision venue, 2026-11-03 America/Los_Angeles. |

## Validation

- All 47 edits add only a Date field and blank line. Removing that insertion
  reproduces each original file byte-for-byte.
- Existing parser: 138/138 records have valid explicit dates.
- External forest catalog: HTTP 200; all 138 filename/date pairs match the source
  parser in exact chronological order; zero “Date unavailable” entries.
- All 47 changed live detail pages return HTTP 200 and contain their Date field.
- Live catalog retained at `/tmp/usersum-adr-backfill-live.html`.
- No Python/frontend tests run for this metadata-only follow-up; executable logic
  is unchanged.
- `wctl doc-lint --path <ADR>`: all 47 changed ADRs pass. Work-package docs
  also pass lint, and `git diff --check` is clean.
