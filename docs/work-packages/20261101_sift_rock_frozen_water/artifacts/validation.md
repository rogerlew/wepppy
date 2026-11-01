# Validation and limitations

- Contract ancestor: 6b08f3452, before production edits. Independent scientific
  and implementation reviews cover volume conversion, missing/invalid states,
  canned water ordering, comment formatter and mandatory SAT 0.75.
- Regression proof: original property tests fail on nonzero source volume;
  original actual builder fails on missing prettytable. A separately labeled
  diagnostic bypass of the comment formatter exposes the seven-token OFE
  header. Neither failed artifact is accepted as native input evidence.
- Focused gate: 120 passed, including 43 new SIFT cases and existing ISRIC,
  conversion and horizon-boundary coverage. Test warnings are retained.
- Actual builder: three synthetic conforming source records produce soils and
  unconverted JSON; canonical parsing verifies seven horizons and SAT 0.75.
- Native reader: three complete 16-year histories, 30 initialization layers each,
  17,532 daily water records each. Native mass, density-dependent fine-earth
  fraction, SAT and 1,800 mm profile cap verified. Original report-decoration
  verifier failure retained; reviewed read-only v2 acceptance passes all three.
- Reader controls: four deliberately corrupted disposable copies are rejected:
  numeric stars, stars in a report numeric field, duplicate daily key and zero
  saturation denominator. Original history hashes/sizes/mtimes remain unchanged.
- Complete FRWATC: all 29 processes finish with finite states and unchanged
  inactive-support sentinels. Eighteen normal controls close. Five of 11
  threshold fixtures demonstrate discrepancies, independently reconstructed from
  stdout; these are observations, not conservation acceptance.
- Stub hygiene passes. Changed-exception enforcement initially flags four
  existing handlers because the added import shifts their line-number
  allowlist entries. Only those four coordinates are updated. Both final
  default enforcement and unsuppressed comparison pass; unsuppressed counts
  remain four before and four after. No exception handler changed.
- Broad application suite: 12,634 passed, 423 skipped, 5,830 warnings in
  3,589.92 seconds; command exit status zero. Exact log identity and counts are
  retained in test-results.json. Scoped documentation checks pass; the archive
  receipt and publication manifest record final retention identities.

No API stub surface, UI or RQ wiring changed. Native release/watchlist gates are
not applicable because no production native source or release binary changes.
The standalone probe uses explicit runtime checks; native evidence is not a
release or deployment claim. Actual local BC database coverage, empirical
retention validity, coupled frozen-water/drainage closure and surface-cover
estimation remain outside this acceptance.

Native source-free evidence checkpoint: `add893ad6`. Packaging review verifies
179 staged blobs against the filesystem, 173 manifest entries and 178 checksums.
Verbatim native stdout carries trailing whitespace; it is retained byte-for-byte
and explicitly excluded from prose whitespace cleanup.

Observe-only code quality completed; radon was unavailable, so complexity data
are not reported as measured. No new dependency was installed for telemetry.
