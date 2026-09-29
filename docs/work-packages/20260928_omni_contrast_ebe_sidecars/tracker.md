# Tracker - Omni Contrast EBE Sidecar Integrity

## Quick Status

**Started**: 2026-09-29 00:00 UTC  
**Current phase**: Implemented; awaiting Jackson's production rerun  
**Security impact**: `none`

## Task Board

### In Progress

- [ ] Run broad applicable validation (10,080-test suite started and passed through 22% before production handoff; focused suite and static gates complete).
- [ ] Regenerate and verify all 69 `strategic-eloquence` contrasts on `wepp1`.

### Done

- [x] Confirmed all 69 historical contrast EBE Parquets contain zero rows while annual outlet discharge is positive.
- [x] Ruled out pathname length: maximum observed length is 96 versus WEPP `CHARACTER*111`.
- [x] Traced the first-loss boundary to missing `chan.inp` and WEPP `nchnum = 0`.
- [x] Audited historical parent/contrast sidecars: only `chan.inp` and `tc.txt` were missing; the July 6 preservation fix already prevents output switches from deleting inherited files.
- [x] Completed production A/B comparison: `honeyed-marathoner` has `chan.inp` and nonzero EBE rows in 100/100 contrasts generated July 14; `strategic-eloquence` has neither in 69/69 contrasts generated June 29. Both persist `chan_out=False` and `ebe_pw0=True`.
- [x] Scaffolded this package and active ExecPlan.
- [x] Made EBE-only contrast preparation require `chan.inp` and propagate preparation failure.
- [x] Added EBE-only, failure-propagation, inherited-sidecar, and contrast-owned-file regression coverage; 83 focused Omni tests pass.
- [x] Passed work-package doc lint and changed broad-exception enforcement; the code change removes one suppressed broad catch.
- [x] Initially enqueued 69 contrast-only production repair jobs plus a finalizer behind the active `squared-evolution` batch.
- [x] Canceled all 70 deferred repair jobs before any started after the operator assigned the rerun to Jackson; no `strategic-eloquence` artifacts were changed by Codex.

## Decisions

- **2026-09-29 00:00 UTC** – Treat this as conformance hardening against the unchanged Omni sidecar contract. Require `chan.inp` for either channel diagnostics or EBE because both consumers depend on its selected-channel list.
- **2026-09-29 00:00 UTC** – Preserve all inherited regular run sidecars except contrast-owned `pw0.run` and `pw0.err`; do not introduce a speculative filename allowlist.

## Notes – 2026-09-29 00:00 UTC

- Production code includes commit `ac28941c8`, which preserves inherited sidecars, but the affected June 29 artifacts predate it.
- Direct source evidence is in `/workdir/wepp-forest_260430_baseline/src/wshinp.for` and `sedout.f90`.
- `honeyed-marathoner` is the positive production control and demonstrates that the unchanged flags work after sidecar preservation; no pathname hypothesis is needed.
- Historical queue record: first repair job `1b33c3e4-2ffd-4e54-8fe7-6b102a5dde07` and repair finalizer `dd705c3d-bcc6-4705-a6e4-7ed5cfd484ef` were canceled while deferred. Production verification now follows Jackson's rerun.
