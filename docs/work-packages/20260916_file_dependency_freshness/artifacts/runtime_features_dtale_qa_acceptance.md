# Independent Features and public D-Tale runtime QA

Disposition: **PASS for these bounded native and public workflows after the
coordinated development service restart**. No production or repository tests
were changed by these probes. Parent restart parity evidence is
`runtime_restart_verification.json`. Concurrent runtime work was allowed;
elapsed values here are not new performance acceptance measurements.

## C02 shipped mixed Features exports

Command:

```bash
wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/runtime_features_mixed.py --execute --label revision2
```

Evidence: [result](features_mixed_runtime_revision2.json),
[log](features_mixed_runtime_revision2.log), and
[retained harness](runtime_features_mixed.py). Full inputs and native output
snapshots remain under `/wc1/batch/qa-features-mixed-de5549eede4b/`; its
`full-project-copy.json` records the complete independent copy. The controller
root is `runs/qa-features-mixed-de5549eede4b-grizzly`, giving RedisPrep a unique
leaf namespace as well as a unique batch identity.

The actual maintained `prep_details` CSV and `post_wepp` GeoPackage profiles
produced 217 hillslope and 87 channel rows. Their selected dependency sets
contained 10 and 14 unique paths respectively: two WBT GeoJSON files, real
watershed/landuse/soil Parquet, relevant NoDb owners and Unitizer state, and
post-WEPP interchange Parquet/manifest. Instrumentation delegated every read
to the real reader and recorded 240 calls over eight actual native source paths;
GeoJSON was the actual GDAL vector driver. Every native input resolved inside
the disposable copied root.

| Control | Both shipped profiles |
| --- | --- |
| Baseline ordinary export versus independently forced native export | Same semantic output |
| Metadata-only touch of all selected ordinary dependencies | Existing artifact reused, output unchanged |
| Equal-byte atomic replacement of those dependencies | Existing artifact reused, output unchanged |
| Changed hillslope `slope_scalar`, restored mtime | Miss, changed attributes, unchanged geometry, matches fresh native export |
| Changed subcatchment geometry, restored mtime | Miss; GeoPackage geometry changes, attributes remain unchanged; matches fresh native export |
| Actual `Unitizer.set_preferences` changes | Miss, changed converted attributes, unchanged geometry, matches fresh native export |

The numeric mutation changed Parquet size from 32,414 to 32,415 bytes; this is
**not** an equal-size mutation claim. The public D-Tale probe below separately
tests equal-size Parquet replacement. CSV is geometryless; its geometry-change
miss agrees with its declared dependency policy and fresh output.

All 16 historical export artifacts retained their original SHA-256. Production
module/catalog/profile hashes stayed unchanged. The final independent source
verification rehashed all **3,916 files / 6,375,730,842 bytes** and verified their
original generations, confirming the named Grizzly source was unchanged.

The initial attempt stopped before any copy because the shared utility had
just tightened its leaf-name guard to include the complete batch name. Its
[result](features_mixed_runtime_initial.json) and
[log](features_mixed_runtime_initial.log) remain retained. Revision2 changes only
the fixture identity to satisfy that guard. Real GDAL Polygon-to-MultiPolygon
GeoPackage warnings occurred during ordinary and fresh controls; outputs were
readable and semantically equal. That existing geometry conformance warning is
a separate low-priority export follow-up, not a freshness regression.

This closes the missing representative **shipped mixed-profile native output**
evidence described in `features_omni_remaining_closure_qa.md`. It does not prove
all catalog profiles, arbitrary multi-file driver closure, external aliases,
or concurrent-writer snapshot isolation. The forced control uses the existing
private cache-miss executor because the public service has no force option;
this probe does not claim HTTP/RQ dispatch acceptance.

## C11 authenticated public browse, D-Tale, and maps

Commands:

```bash
wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/runtime_dtale_public.py --execute --label initial
node docs/work-packages/20260916_file_dependency_freshness/artifacts/runtime_dtale_public_browser.cjs revision3
```

Evidence: [HTTP result](dtale_public_runtime_initial.json),
[HTTP log](dtale_public_runtime_initial.log),
[browser result](dtale_public_browser_revision3.json),
[browser log](dtale_public_browser_revision3.log), and their retained harnesses.
The unique run is `/wc1/runs/qa/qa-freshness-dtale-aecf4f938bd0`; before/after
Parquet and GeoJSON plus the removed overlay remain in `acceptance-evidence`.
Three independently copied source metadata files were hashed and generation
checked afterward; their named originals were unchanged.

The real public browse URL is
<https://wc.bearhive.duckdns.org/weppcloud/runs/qa-freshness-dtale-aecf4f938bd0/config/dtale/table.parquet>.
It redirects to the shared viewer
<https://wc.bearhive.duckdns.org/weppcloud/dtale/main/7f203385a58d>.
This is retained development-canary data; authenticated access remains required
by the browse bridge. No credentials, auth headers, cookies, or arbitrary HTML
were written into evidence.

All **65 checks across 28 actual HTTP requests** passed. Metadata-only touches
and identical-byte rewrites reused the logical ID and exact row response.
Equal-size Parquet with restored mtime changed column `a`/rows `[1,2]` to
column `z`/rows `[8,9]`. The already-open lazy grid returned HTTP200
`success=false,code=changed_source` with reopen guidance and no successful
rows/columns. Its old shell dtype metadata remained unchanged until explicit
relaunch. The next public browse launch rebuilt current rows/schema under the
same logical ID, exactly as the reviewed contract requires.

Actual maintained Dash callbacks showed registered subcatchment/channel
choices. Selecting the subcatchment overlay exposed its parsed properties;
equal-size/restored-mtime GeoJSON replacement changed `mark_old` to `mark_new`
in that real service registry. Removing the optional overlay removed its choice
while preserving the channel registration and usable table. This proves actual
registration and selection behavior; it does not assert rendered geographic
pixels or automatic map-default selection.

The real public browser then completed current → stale → reopened → restored
phases with **zero page errors and no intercepted responses**. The stale grid
displayed the service's reopen guidance visibly; the two reopened generations
displayed the expected row values and schemas. Screenshots:

- [Current rows](dtale_public_browser_revision3_current.png)
- [Visible changed-source guidance](dtale_public_browser_revision3_stale.png)
- [Reopened generation](dtale_public_browser_revision3_reopened.png)
- [Restored final generation](dtale_public_browser_revision3_restored.png)

The first two browser attempts timed out because the probe matched an old
prototype phrase, “Reopen the dataset,” while the actual service correctly says
“Reopen this dataset.” Both failed logs/results remain retained; revision2's
failure screenshot and visible alert text show the working UI. Revision3
changes only the harness to match the returned guidance string. No transport,
service, or frontend fix was needed.

These actual public HTTP/browser/map checks close the prior internal-only,
pre-restart D-Tale runtime evidence gap. They do not replace the separate
77 MB paging performance evidence, broader package acceptance, or the
explicitly unresolved active GL/browser-generation contract gap.
