# GridMET follow-up audit tracker

Complete, 2026-09-17 UTC.

- [x] New attempt and prior comparison identified.
- [x] All 25,143 event, 12 design and three inverse rows verified.
- [x] Identical T/F/S, coverage and P50 values; design differences retained.
- [x] Original GridMET and CLI daily series compared; August 5–12 all zero.
- [x] Authenticated report/payloads/downloads/reload verified; actual current=false.
- [x] Freshness difference isolated to active CLI ctime; cause unproven.
- [x] Findings, 266-file preservation and documentation checks retained.

## Decisions and limitations

The prior closed audit remains unchanged. This package records the owner's
new climate/M3 attempt. Calendar dates improve temporal interpretation but
modeled subdaily peaks do not become measured intensities. No storm pairing
is established for the approximate deposition window. No live mutation or
freshness override is performed. The initial browser currentness assumption
failed and was replaced with explicit evidence of actual stale-input status.

[Findings](artifacts/findings.md) and [final checks](artifacts/closeout_checks.json).
