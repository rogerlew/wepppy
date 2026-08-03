# Tracker - Stevens Canyon Contributor-Indexed `htcs` Ensemble

**Started:** 2026-08-03
**Current phase:** Complete
**Security impact:** none

## Task Board

### Done

- [x] Created a pass-compatible isolated build and proved focal-event parity.
- [x] Activated contributor-indexed `htcs` with numerical bounds.
- [x] Ran direct-`htcs` and 300 deterministic ensemble realizations.
- [x] Validated routed volume and full-period completion.
- [x] Analyzed day 203 and comparable events at reaches 169, 172, 173, and 193.
- [x] Produced figures, Markdown sidecars, and conclusions.
- [x] Ran cleanup and verified baseline source integrity.

## Decisions

- **2026-08-03** - Use a separate follow-on package because the preceding
  synchronization-dispersion study is complete and its rejected direct-`htcs`
  lane must remain historically accurate.
- **2026-08-03** - Copy the baseline build artifacts into the ablation root and
  relink there. Never compile, patch, clean, or relink in
  `/workdir/wepp-forest_260430_baseline`.
- **2026-08-03** - Rejected the first batch because an incorrect field width
  shifted subsequent fixed columns. Accepted only the corrected, field-isolated
  batch.
- **2026-08-03** - Restricted full-record inference to the same-build pair;
  focal production parity is exact, but full-record rebuild drift is disclosed.
