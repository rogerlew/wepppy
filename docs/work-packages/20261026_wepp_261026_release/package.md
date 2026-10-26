# WEPP 261026 release and revised scientific report

Status: closed 2026-10-26. Released as a selectable paired binary; no production
deployment or default switch. Issued 261010 and 261021 reports are preserved.
[Completed plan](prompts/completed/release_execplan.md) · [Tracker](tracker.md) ·
[Validation](artifacts/validation.md).

The independently reviewed late terminal return-source metadata repair is
released from native model commit b73e93b19a724d1991d341d38a18d11e742231bd.
Native release/artifact commit: 8d89b0c194e09504f6d4bba0a985ce48debdea86.
Paired binaries, synchronized sidecars and a reviewed 49-page cumulative report
are vendored in WEPPpy. The report re-versions 261010, covers inherited 261021
repairs and distinguishes historical studies from fresh 261026 evidence.

All release gates pass: 534 native tests, 12 watchlist cases, 89 compatibility
tests (one existing skip), 40 selection tests and complete segmented WEPPpy
coverage (11,791 passes, 150 test skips, one additional collection-module skip).
Both reported watersheds complete; production-container readers validate all
16 retained Parquet artifacts. Scientific, implementation and disclosure reviews
pass. Local report download is HTTP 200 with the frozen PDF hash.

The normative decision and rationale are in
[ADR-0107](../../adrs/ADR-0107-late-return-source-effective-support.md), and native
`docs/contracts/physical-water-routing-contract.md#late-hourly-return-metadata-261026`.
Effective support still begins at midnight; actual within-day timing and universal
water conservation are not established. Signed channel exchange/clipping remains
separate work. ASCII PASS v3, capacities, banner and project defaults are retained.

Security impact is low: no authority, authentication or runtime-identity changes.
No new service, dependency, protocol or datastore. Original production runs,
unrelated query-catalog work and the separate HBP checkout were preserved.
