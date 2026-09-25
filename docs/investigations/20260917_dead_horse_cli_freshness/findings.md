# Dead Horse Creek: changed rainfall versus CLI freshness

2026-09-17 UTC. Read-only follow-up to the owner's observation that the report
changed after rebuilding climate. Closed audit packages remain unchanged.

## Conclusion

The report changed because the accepted climate changed from PRISM to
GridMetPRISM. The old/new accepted climate-parquet SHA-256 values are
`a52260f4d7ea269d97a718033bf9ac712eb545f7daf4659e473656f82020081d` and
`59cdde438ef650dd150abf8219b867cd531b8ab781679c9bd1e0fd4124a6a189`.
That expected climate replacement is distinct from the later stale-status flag.

A fresh parse of the current `climate/wepp.cli`, including recalculated peaks,
exactly matches every shared column of the accepted parquet over all 16,802
rows. The parquet hash still matches accepted attempt
`f493a714df9d4fbfbfd4370c46ad54f8`. Thus the current CLI's parsed climate values
agree with the input behind the changed report. This does not establish its
acceptance-time byte hash or rule out harmless header differences.

## Evidence for the later ctime mismatch

The active CLI and `wepp/runs/pw0.cli` share the same inode and have link count
2. Current mtime is 00:55:08.469623 UTC; ctime is 00:59:33.014495 UTC.
M3 completed at 00:57:50 UTC. The WEPP log records watershed preparation
starting at 00:59:32 UTC. `_prep_channel_climate` in
`wepppy/nodb/core/wepp.py` calls `copy_input_file`, whose directory-backed path
in `wepppy/runtime_paths/wepp_inputs.py` uses `os.link`.

The earlier freshness audit found only a ctime difference for the active CLI;
size and mtime remained equal. The current semantic equality, hard-link identity,
code path and timing strongly support WEPP hard-link preparation causing the
later freshness mismatch without changing scientific inputs. This is evidence
of a metadata-driven stale indication, not evidence that the changed report
failed to consume the GridMET rerun. No syscall trace or acceptance-time CLI
content hash exists, so exact historical attribution remains an inference.

## Reproduction and disposition

`wctl exec -T weppcloud python /workdir/wepppy/docs/investigations/20260917_dead_horse_cli_freshness/check.py`

[evidence.json](evidence.json) records all shared-column comparisons, the current
CLI hash and link identity. The script writes only local investigation evidence.
No run, parameter, freshness state or production code was changed. If repairing
freshness behavior, preserve detection of actual content changes while avoiding
hard-link/metadata-only invalidation; simply removing ctime without an equivalent
content check would weaken the existing contract.
