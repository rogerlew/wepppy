# ADR-0100: Gregorian WEPP execution calendar

Status: Accepted for implementation, 2026-10-21.

## Decision provenance

Decision venue: this engineering conversation, 2026-10-21, America/Los_Angeles.
Participants: Roger Lew (user/decision owner), Codex (implementer). Roger requested
identification of the robust century repair and then authorized carrying it out.

## Context and decision

CLIGEN continuous output follows Gregorian leap years. WEPP's legacy century
override requested 366 days in years divisible by 100 but not 400. Use Gregorian
execution everywhere: divisible by 4 and either not divisible by 100 or divisible
by 400. Validate daily climate/PASS dates before physical-state advancement and
reject EOF without complete records. Do not synthesize weather. Explicitly label
new HBP data `wepp-gregorian-v1`; retain legacy policy meaning and explicit
inspection support while rejecting legacy data in corrected runtime routing.

## Evidence and alternatives

[Investigation](../work-packages/20261021_ascii_pass_century_investigation/artifacts/findings.md)
reproduced the year-102 guard in a 200-year project and two stale weather records
beyond EOF. Suppressing the guard, changing CLIGEN to legacy leap years, dropping
PASS records or relabeling dates would preserve incorrect physical evolution.

## Compatibility, risk and rollback

ASCII stays v3 with strict Gregorian daily keys. Both binary schema layouts retain
their layout; calendar policy changes explicitly. Regenerate all hillslopes and
watershed/interchange data together. Century monthly/yearly accounting changes
intentionally; unaffected periods require regression parity. Preserve legacy
artifacts for diagnosis. Roll back paired binaries and regenerate together if
validation fails; never combine policies or relabel existing payloads.

Implementation and validation: [repair package](../work-packages/20261021_gregorian_calendar_repair/package.md).

## Downstream padding

Generated-output validation found that the HBP converter exported all schema-2
slots, including non-leap day 366. For `wepp-gregorian-v1`, interchange validates
then omits those NO EVENT padding slots. It retains real leap-day rows, all columns
and historical-policy behavior. Filtering by explicit policy prevents silently
reinterpreting legacy artifacts. Existing climate supplies the actual date sequence.
