# Climate scale-map authority tracker

## Progress

- [x] Confirm deployed parser still trusts submitted map and read-only form submits it.
- [x] Identify Marta Basso's owner account with 14 `portland-10-mofe` runs.
- [x] Raw disk inventory: four corrupt maps (`under-fecundity`, `seductive-sabra`,
  `warming-championship`, `asteroid-hindrance`), nine correct, and one missing
  canonical climate.nodb (`free-sally`). Config and active-job checks continue.
- [x] Ratify and commit canonical contract checkpoint `acf04419c`.
- [x] Implement configuration authority/browser omission; focused checks and reviews pass.
- [x] Repair four production records with protected backups and verify no-op replay.
- [ ] Activate code in both request handlers and RQ workers.
- [x] Verify disk/cache, real raster/CLI/WEPP-prep canary, and rebuild disposition.
- [x] Broad suite: 8,145 passed, 72 skipped; added real replay test passed separately.
- [ ] Repeat repair after later user submissions and matching code activation.

## Decision log

- Preserve legacy Daymet-over-Gridmet-over-generic precedence and scientific
  inputs. Ignore obsolete client map fields so stale pages can rebuild safely.
- Persist repairs under canonical NoDb locks after backups and fresh hydration.

## Validation and outcome

Initial four maps repaired at 2026-09-09 22:19 UTC; disk/cache and no-op verified.
At 22:32 UTC three new user build payloads again carried map `"1.1"`, alongside
new user-selected scalar modes. Preserve those choices. Full evidence, tests,
and revised rebuild disposition: `artifacts/20260909_live_evidence.md`.

Permanent code activation and final repeat repair are pending the production
job gate. Active jobs prevent deployment without explicit operator approval;
canonical cutover additionally requires drained default/batch jobs. All local
implementation, focused/broad validation, and independent reviews are complete.

22:52 UTC follow-up: two active climate jobs stopped on explicit request;
warming-championship climate had finished and WEPP was active. Seductive-sabra
and asteroid-hindrance maps repaired again. Warming map and code activation
remain pending; see the live evidence cancellation section.

22:55 UTC: under-fecundity and warming-championship map repairs completed on
explicit follow-up, preserving scalar settings. The under climate job was stopped;
verified non-writing warming model jobs continued. Code activation remains pending.
