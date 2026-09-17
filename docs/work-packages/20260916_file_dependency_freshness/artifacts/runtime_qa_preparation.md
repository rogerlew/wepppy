# Prepared QA runtime acceptance

Status: **executed after the root-authorized restart**. See
[runtime acceptance](runtime_features_dtale_qa_acceptance.md) for outcomes,
retained failures, actual commands, and scope limits. Python compilation and
`--help` checks passed during preparation. These scripts contain no production
changes.

## Public browse and D-Tale

```bash
wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/runtime_dtale_public.py --execute --label initial
```

The harness creates `/wc1/runs/qa/qa-freshness-dtale-<unique>`, independently
copies the named Grizzly `config.cfg`, `ron.nodb`, and `watershed.nodb`, and
rebases only the copied metadata. It hydrates the copied Watershed to select
the actual overlay paths, then writes two-row Parquet and small GeoJSON fixtures.
Named source files are never hydrated or written, and their hashes/versions are
checked afterward. All files and failed attempts remain available.

The real authenticated public path covers browse preview, loader redirect,
viewer HTML, grid and dtype responses, metadata-only touch, identical-byte
rewrite, and equal-size changed Parquet with restored mtime. Before relaunch,
the old lazy grid must return HTTP200 `success=false,code=changed_source`
without successful row/column data. Reopening must expose the new schema and
rows under the **same shared logical dataset ID**, as required by the canonical
contract. The separate dtype endpoint describes the old shell until relaunch;
it does not independently acquire file content.

Actual public Dash callbacks verify the registered overlay choice and parsed
feature properties, then their refresh after an equal-size/restored-mtime
GeoJSON rewrite. Optional overlay removal must preserve table access and the
remaining channel registration. This tests actual server registration and
selection callbacks, not rendered map pixels or automatic default selection.

Authentication uses `runtime_http.session()` with the existing private host or
container auth file. Headers, cookies, tokens, HTML, and arbitrary error bodies
are excluded from evidence. No internal loader endpoint, service import,
response interception, or HTTP stub substitutes for the public workflow.
The only POST is the maintained read-only Dash callback with this harness's
disposable dataset ID.

Evidence will be `dtale_public_runtime_initial.json` plus retained files under
the new disposable run. Reattempts require a new label and a new run. An HTTP
authorization or proxy failure remains a visible blocker, not a fallback to
internal service access.

## Shipped mixed Features profiles

```bash
wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/runtime_features_mixed.py --execute --label initial
```

The full independent copy uses `runtime_project_copy.py` and a globally unique
leaf `/wc1/batch/qa-features-mixed-<unique>/runs/qa-features-mixed-<unique>-grizzly`.
The leaf matters because RedisPrep state uses the basename. No queued job is
submitted by this local native acceptance harness.

Real shipped `prep_details`/`post_wepp` profiles exercise CSV/GPKG export,
maintained catalog selection, actual Parquet/GeoJSON reads, and copied
Watershed/Unitizer owners. Touch and identical-byte controls must hit; changed
numeric rows, geometry, and units must miss and match independently forced
fresh native exports. The fresh control invokes the existing private miss
executor because the public service has no force-rebuild option; it does not
replace a producer or reader. Prior artifacts, semantic snapshots, native
reader records, and full source verification remain retained.

Evidence will be `features_mixed_runtime_initial.json` and the full disposable
copy/output tree. This is native owner acceptance, not HTTP/RQ dispatch or proof
of every catalog profile's transitive dependency closure.
