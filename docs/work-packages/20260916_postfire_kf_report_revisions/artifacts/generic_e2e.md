# Generic no-RUSLE acceptance

PASS: disposable `pfdf-kf-e5c25f5b`, configuration `disturbed9002_wbt`.
Synthetic Nevada terrain and CLIGEN-format climate are explicitly test fixtures;
Kf came from the actual bounded public KFFACT source, through the normal worker.
The 1,156-cell basin differs materially from nervous-mesquite's 77,669 cells and
has source Kf 0.200000003 rather than 0.139396006. This is workflow/source
acceptance, not a second scientifically calibrated real-fire study.

`setup_fixture.py` creates only the disposable project's upstream inputs. At
browser upload/run submission there was no `rusle/` or `polaris/` directory and
no completed RUSLE/POLARIS task. The browser uploaded dNBR and clicked Run.
RQ job `087cf30a-db0d-4ffa-afc2-7c9ea4e70a7a` accepted attempt
`089792b89459438ebd5de3f2c4b972c0` at 23:13:17 UTC, with full common support.
No operator-prepared Kf artifact was supplied. Six bounded requests transferred
262,144 bytes for a 17 × 17 native window.

Independent raster means and 90 events, 12 design values, three inverse values
and four curve CSVs pass coefficient checks. Evidence:
[fixture numeric validation](pfdf-kf-e5c25f5b_numeric_validation.json).

`browser/pfdf-kf-e5c25f5b/evidence.json` and `browser_e2e.cjs` retain the actual
UI/RQ/report/download assertions. After completion the harness enabled and
removed RUSLE through the normal Project controller. The post-fire checkbox
remained checked, controller visible and results current immediately, after one
reload and after a second reload. This directly tests the reported regression.

Both Kf manifests, original request bodies, metadata, all rasters and results
survive canonical archive/restore: 62 exact files on an isolated module copy.
See [archive evidence](fixture_archive_roundtrip.json). Earlier missing CLI header
and noninteger fixture timestamps were setup defects, corrected before a model
submission. The failed rendering evidence is retained; no application workaround
or hidden source substitution was added.

M3 compatibility separately passed the existing read-only browser acceptance on
`pfdf-m3-validation-20260914b`, including events, Unitizer, CSV, keyboard selection,
controlled request failures, themes, narrow viewport and ordinary browse/download.
All 23 protected files remained byte-identical; see `browser_m3/browser.json`.
