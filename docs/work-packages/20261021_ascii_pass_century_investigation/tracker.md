# Investigation tracker

2026-10-21: Completed investigation and robust repair identification.

All 104 hillslope PASS files plus master have 73,050 legacy days against 73,048
Gregorian climate rows. H1 water balance confirms the post-century date shift
and two stale-buffer precipitation values after EOF. CLIGEN is already Gregorian.

Both isolated full-request replays stop at the predicted key mismatch:
requested `(103,365)`, stored `(102,365)`. All six watershed files match between the
release/probe replays; original master PASS and plot output match, while four
original numerical outputs differ (cause unresolved); all 104 hillslope inputs are unchanged.
See [findings](artifacts/findings.md) and [comparison](artifacts/replay-comparison.json).

User-requested [robust repair design](artifacts/repair-design.md) covers shared
Gregorian execution, daily date guards, EOF tracking, HBP policy compatibility,
regeneration and regression gates. Follow-up implementation must preserve legacy
policy identities and validate regenerated 200/400-year artifacts before release.
No production source changes, deployment or live-run recovery were performed.
