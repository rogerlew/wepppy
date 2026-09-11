# Validation

## Regression and gates

- 158 focused tests passed: production upload/model, dNBR, publication, route boundaries,
  migration and canonical archive/restore. The final migration-only suite passed
  21 tests after replacing the installed RQ registry API's implicit cleanup with
  read-only Redis membership inspection.
- The 35-test soil suite passed after retaining `count_keys.tif`; exact values and
  NoData semantics are asserted.
- Full Python suite remains on hold by operator instruction.
- Stub completeness, generated-workflow consistency, changed-file broad-exception
  enforcement, root AGENTS size (160 lines), and scoped documentation lint passed.
- Artifact Observability CI runs these domain/failure/archive tests from the
  canonical forest workflow source and generated workflow.

## Actual worker and project verification

Disposable `artifact-observability-check-79d23f28` passed migration with real Redis
admission/lifecycle exclusion, NoDb locking and registry reads under worker
uid 1000/gid 993. The first disposable check exposed the installed RQ version's
unsupported `cleanup=False` argument; read-only membership inspection repaired it
and a regression covers an earlier active postfire job.

`addicted-reservist` migrated 89 files in 10 attempt directories. All 69 non-JSON
payloads (including raster and parquet files) are byte-identical. Accepted run
`88d613bedab2464b84f752929b86d43c` and completion time
`2026-09-11T03:07:24.767129+00:00` are unchanged. Prerequisites remain ready and
freshness is `current`; no model rerun. Only the exact approved old/new engine
pair was promoted. Audit: `postfire_debris_flow/migrations/9c2c399f071341d7a60d332ac49f7382/`.
No physical dot path remains under the module. Exact original metadata remains
in the visible audit alongside independently validated rebased metadata.

The development web workers were gracefully reloaded and rq-engine restarted
through wctl to load the changed storage paths. No production fleet deployment.

## Browser and archive/restore

Authenticated Playwright verified normal browse listings, downloads and SHA-256
for the four root result files, original uploaded IMG, prepared DEM, WBT summary,
normalized dNBR manifest and historical/current attempt receipts. Reload also
preserves the root listings. See `browser_validation.log` and the reproducible
`browser.cjs`; credentials remain in the established gitignored secret file.

A disposable copy of all 148 migrated module files was archived and restored by
the canonical project archive/restore implementation under the worker identity.
The source and disposable copy are both private. Every module file was present
in the archive and byte-identical after restoration, including after deliberately
altering the copy's root manifest. Archive size: 574142986 bytes. The live project
was not restored or otherwise modified by this test. See `archive_validation.log`
and `check_archive_runtime.py`. Canonical archive traversal already included dot
directories; this work fixes visibility and explicitly proves record preservation.

## Evidence files

`live_validation.json` contains the before/after counters, current API projection
and complete final hash inventory. The project audit retains original NoDb and
JSON bytes, mapping, metadata checksums and migration phases. Failed/partial
writer, interrupted recovery, tampering and archive restoration are covered by
real filesystem tests rather than documentation assertions.
