# Tracker

2026-10-21: Retained-run investigation complete; awaiting Jackson's run/output
family for exact attribution. Confirmed legacy one-day PASS/EBE labeling shift;
146,097 corrected daily reader loads match same-day PASS, including all 147
nonzero surface-runoff days. No new production edits. See
[findings](artifacts/findings.md) and [audit](artifacts/audit-results.json).

2026-10-21: User accepted the date-label defect and requested its patch. Verified
all 16 source hashes against the completed Gregorian repair: unchanged. The
existing source correction fulfills this request; no separate routing offset is
introduced. Completion is source/local validation only, with no vendoring or
deployment. Jackson-specific attribution remains an evidence limitation.

Focused verification rerun: 62 calendar/PASS tests passed in 3.02 seconds.
