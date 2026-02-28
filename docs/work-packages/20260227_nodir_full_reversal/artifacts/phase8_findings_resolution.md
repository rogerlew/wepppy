# Phase 8 Findings Resolution

- Date: 2026-02-28
- Scope: findings raised by mandatory `reviewer` + `test_guardian` loops through Phase 8 Phase 7 closeout.

## Resolved Findings

1. `apply_nodir` resolution failures were reported as skips instead of errors.
   - Resolution: unresolved config/ron parsing now yields explicit run `error` status.

2. Dry-run conflict accounting mismatch.
   - Resolution: dry-run conflict actions now increment run/file conflict counters consistently.

3. Silent I/O drops during resource discovery.
   - Resolution: `discover_root_resources` no longer swallows `OSError`; `_process_run` records scan failures as explicit run errors.

4. Dry-run file-action errors not escalating run status.
   - Resolution: dry-run sets run `final_status=error` when file-action errors are present.

5. `main()` summary read path mismatch for `~` paths.
   - Resolution: main now resolves `--summary-json` once and reads back from the same resolved path.

6. Catalog refresh boundary could propagate unexpected exceptions.
   - Resolution: refresh boundary now catches unexpected exceptions explicitly as best-effort deferrals.

7. Test coverage gaps for contract/edge branches.
   - Resolution: expanded targeted suite to `26` passing tests, including:
     - eligible dry-run non-mutation + conflict accounting
     - mapping coverage for watershed/csv + sort order
     - summary/audit contract assertions
     - wepp1 mode/approval gate variants
     - lock contention + FileExists conflict race branch
     - unresolved `apply_nodir` paths
     - scan I/O and dry-run error-escalation branches
     - root validation/discovery failure summaries
     - CLI invalid roots parsing and `~` summary path
     - catalog refresh unexpected-exception boundary
     - direct success-path coverage for `find`-based discovery command assembly/parsing.

8. Phase 4 disposition semantics for wepp1 dry-run run errors.
   - Resolution: approval packet and active ExecPlan now explicitly mark Phase 4 complete-by-contract while carrying `460` run errors as Phase 5 approval disposition items.

9. Phase 6 scope reconciliation gap between historical dry-run and current apply snapshot.
   - Resolution: added same-root post-apply reconciliation dry-run evidence (`1858` discovered, `2` eligible, `2` predicted conflicts, `3` errors) and propagated reconciliation notes to apply report, validation log, active ExecPlan living sections, and tracker.

10. Validation evidence mismatch with active ExecPlan gate list.
   - Resolution: ran/logged missing doc-lint gates (`wctl doc-lint --path docs/schemas`, `wctl doc-lint --path PROJECT_TRACKER.md`) so validation log now covers the full gate list.

11. Phase 7 closeout consistency recheck.
   - Resolution: closeout review loop surfaced two medium doc-consistency findings (risk-table status sync and validation-log doc-lint count sync), then rerun verified no remaining high/medium findings.

12. Tracker risk register status/closeout mismatch.
   - Resolution: updated tracker risk table to mark Phase 1-8 program risks as mitigated by completed phases and retained only explicit residual migration follow-up risk as open.

13. Validation log doc-lint evidence drift.
   - Resolution: synchronized `phase8_validation_log.md` package doc-lint entry to current verified result (`44 files validated, 0 errors, 0 warnings`).

14. Phase 7 closeout final confirmation loop.
   - Resolution: executed final reviewer/test_guardian confirmation pass over closeout docs; unresolved counts remained `high=0`, `medium=0`.

## Verification of Resolution

- Final reviewer unresolved counts: `high=0`, `medium=0`
- Final test_guardian unresolved counts: `high=0`, `medium=0`

All mandatory subagent findings are resolved to closure criteria.
