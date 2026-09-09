# Climate scale-map authority tracker

## Progress

- [x] Confirm deployed parser still trusts submitted map and read-only form submits it.
- [x] Identify Marta Basso's owner account with 14 `portland-10-mofe` runs.
- [x] Raw disk inventory: four corrupt maps (`under-fecundity`, `seductive-sabra`,
  `warming-championship`, `asteroid-hindrance`), nine correct, and one missing
  canonical climate.nodb (`free-sally`). Config and active-job checks continue.
- [ ] Review and commit canonical contract checkpoint.
- [ ] Implement and validate configuration authority and browser omission.
- [ ] Apply bounded production fix and reset affected NoDb records.
- [ ] Verify disk/cache/artifact propagation and document rebuild disposition.

## Decision log

- Preserve legacy Daymet-over-Gridmet-over-generic precedence and scientific
  inputs. Ignore obsolete client map fields so stale pages can rebuild safely.
- Persist repairs under canonical NoDb locks after backups and fresh hydration.

## Validation and outcome

Pending. No production NoDb files have been changed by this task.
