# Tracker - Stevens Canyon Hillslope Synchronization Sensitivity

**Started:** 2026-08-03 16:48 UTC
**Current phase:** Complete
**Security impact:** none

## Task Board

### In Progress

None.

### Done

- [x] Reviewed `chrqin`, `wshpas`, pass records, and source history.
- [x] Verified production and hillslope-fixture `wepp_ui.txt` files exist and
  have SHA-256 `e3b0c442...b855` (intentional empty presence flag).
- [x] Staged all 138 pass shards and required sidecars from WEPP1 read-only.
- [x] Reproduced the undisturbed day-203 peaks exactly in a 100-year baseline.
- [x] Completed low, medium, and high volume-preserving timing lanes.
- [x] Generated three figures, sidecars, compact data, and interpretation.
- [x] Rejected the incompatible source-level `htcs` lane without using its
  output as evidence.
- [x] Verified baseline source clean at commit `2f65506d239b...`.

## Decisions

- **2026-08-03 16:48 UTC** - Keep `/workdir/wepp-forest_260430_baseline`
  pristine. Build source mutations in a disposable git worktree and retain a
  pre/post baseline commit and status audit.
- **2026-08-03 16:48 UTC** - Treat all behavioral lanes as exploratory upstream
  mutations requiring mass-conservation checks and scientific review before
  any production consideration.
- **2026-08-03 17:21 UTC** - Close the sensitivity package with the direct
  `htcs` implementation deferred. Current source expects binary HBP shards;
  the public production fixture uses legacy text shards, so combining those
  contracts would invalidate attribution.
