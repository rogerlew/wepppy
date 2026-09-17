# Remaining services, tools and browser freshness inventory

## Findings first

**B-F01 — Medium, OPEN: active GL Dashboard can combine different generations of
one scientific Parquet in its yearly cache.** `data/wepp-data.js`:
`loadBaseWeppYearlyData` returns `baseWeppYearlyCache[year]` without observing the
source; `refreshWeppYearlyData` and `refreshWeppYearlyChannelData` have the same
year-keyed reuse shape. `scenario/manager.js:setScenario` clears yearly caches
only when the selected scenario changes; selecting the same scenario returns
early. `gl-dashboard.js` actually instantiates these modules and supplies
`requireWeppPath('lossAllYearsHill')`, preserving baseline/roads output scope.

The supported producer is `rq/wepp_rq_stage_post.py`: completed model output is
converted by `run_wepp_watershed_interchange`, then the query-engine catalog is
force-refreshed. `watershed_loss_interchange.py` sends `loss_pw0.txt` to owned
native `watershed_loss_to_parquet` and publishes the stable
`interchange/loss_pw0.all_years.hill.parquet` name. Keeping a dashboard open while
that run is rebuilt therefore leaves the browser's old key valid.

Retained `gl_dashboard_generation_probe.cjs/.json/.log` executes the **actual
active ES module**, with actual Arrow Parquet writes and DuckDB reads at the
injected query transport. First year 2000 returns **25**. After rewriting the
same file, revisiting 2000 returns **25**, first visiting 2001 returns the new
**76**, and a fresh manager reads the new 2000 value **75**. Only two queries
occur in the original manager. No restored timestamp is necessary. This is a
confirmed file-dependency reuse gap, not just a search hit or changed variable
name. The probe does not run a live WEPP job, deployed browser, or complete
authenticated query-engine service; those acceptance steps remain outstanding.

Required next step: a bounded browser-generation contract/checkpoint deciding
how an open dashboard detects a changed source and refreshes or rejects data
before mixing it with already cached values. Preserve baseline/roads selection,
scenario isolation, query authorization and existing performance expectations.
Neither a TTL nor an unchanged run/scenario identifier proves byte equality.
This discovery does not authorize a new polling service or automatic model
rebuild. No remediation or risk acceptance is recorded here.

**B-L01 — Confirmed legacy behavior, not a current production blocker.** Actual
`controllers_js/subcatchment_delineation.js` also returns old metric values
(25 after rewrite to 75; a fresh instance reads 75). The retained
`browser_dependency_reuse_probe.cjs/.json/.log` uses its public `renderRunoff`
and real Parquet/DuckDB. However `build_controllers_js.py:GL_EXCLUDED_MODULES`
explicitly excludes this Leaflet controller and selects `subcatchments_gl.js`.
No maintained template directly loading the legacy source was found. Do not
promote this isolated reproduction to a current production finding without a
supported entrypoint. The earlier failed DuckDB prepared-DDL probe and its
source remain as `browser_dependency_reuse_probe_initial.*`; the correction
uses DuckDB's relation `create_view`, not an implementation change.

## Scope and reproducibility

Discovery revision: `57e60aae94608d20225a3c168d343e6a52a69f4f`, with the parent's
uncommitted CLI changes present. Source reads and disposable probes only; this
review changed no runtime/tests, operated no named project, and started no live
service or deployment. Existing Python raster, Omni and profile-upload findings
remain owned by `remaining_semantic_inventory.md`; this is a bounded supplement,
not a claim that the entire package is ready to close.

`remaining_nonpython_scope.json` retains exact argv, exit codes, output names and
explicit exclusions. `remaining_nonpython_discovery.py` reproduces the searches:

```text
python3 docs/work-packages/20260916_file_dependency_freshness/artifacts/remaining_nonpython_discovery.py
node docs/work-packages/20260916_file_dependency_freshness/artifacts/browser_dependency_reuse_probe.cjs
node docs/work-packages/20260916_file_dependency_freshness/artifacts/gl_dashboard_generation_probe.cjs
```

The final finite search scope contains **180** service/tool/script sources
(including eight Docker operational shell scripts) and **130** maintained
browser source files, plus the template identity scan. The manifest enumerates
files and commands; counts are navigation aids, not semantic proof. Go has ten
production source files across status2/preflight2. Vendored/minified libraries,
node_modules and test trees were not inspected for internal cache behavior.
Explicitly excluded legacy Leaflet/GeoTIFF library wrappers are listed in the
manifest and are not claimed safe. The first file list included generated
`controllers-gl.js`; the retained `_initial` lists document that exploratory
overbreadth. Final searches exclude it and inspect the maintained producer and
browser sources instead.

## Go and service dispositions

| Finite boundary | Writer → consumer and evidence | Disposition |
| --- | --- | --- |
| `services/preflight2/internal/server/server.go:pushUpdate`; `internal/checklist/checklist.go:Evaluate`, `ExtractLastModified` | Python RedisPrep writes task receipts/attributes; every keyspace notification performs `HGetAll`, evaluates task ordering and sends payload. Same-second/equal payload notifications are still delivered. `checklist.Equal` exists but is not called by this delivery path. Browser `static/js/preflight.js` projects status and last-modified display; post-fire controller calls owner freshness endpoint. | Workflow receipt ordering and display, not file-byte equality. Preserve timestamps. Actual Python file currentness remains its owner's responsibility. No additional Go metadata hash cache found. |
| `services/status2/internal/server/server.go`; `internal/payload/payload.go` | Redis PubSub task text → parsed run-status WebSocket payload. `lastSeen`, `time.Since`, ping/pong limits and retry timers manage connections. | Transport/liveness; no file-dependency reuse. |
| Both Go `internal/config/config.go:readSecretFile` | Startup configuration reads secret bytes with `os.ReadFile`; Redis connection receives startup credentials. | Process configuration snapshot, not stat-cached scientific identity. No runtime credential reload promise inferred. No secret contents read during this audit. |
| `services/cao/.../cleanup_service.py:cleanup_old_data` | Terminal/log writers → `st_mtime` cutoff based on `RETENTION_DAYS`; database timestamps similarly expire terminal/inbox rows. | Age/retention. Replacing timestamps with content hashes would change lifecycle semantics. |
| `services/cao/.../utils/agent_profiles.py`; CAO flow services | Named local/profile resource read per load, database/tmux/flow state operations. Discovery found no file-stat-keyed digest/result reuse. | Configuration/resource selection; no additional confirmed file-currentness defect. This is not a security review of CAO command execution. |
| `services/cap/server.js:currentSecret`, `validatePersistence`, asset routes; `migrate-data.js` | Secret file is reread at verification. Startup validates token-ledger type/access/JSON. Migration hashes actual ledger bytes before and after ownership/mode changes. Assets use Express `sendFile`. Production Dockerfile pins CAP source commit; selected assets live in image `/opt/cap`, with no asset-write mount in reviewed Compose service. | Secret reload and migration checks are actual reads. Proof-of-work SHA in `canary.js` is challenge computation, not file identity. Asset HTTP conditional semantics are delegated to Express; no supported mutable-asset writer or actual stale response was demonstrated. Do not claim a content-hash ETag or inspect bundled third-party code to manufacture one. |
| `services/profile_playback/app.py` and `tools/profile_playback_cli.py` | Profile/capture seed → newly allocated UUID sandbox or explicit archive/playback operation. Configuration selection is read for that operation. | Historical seed/snapshot purpose; preserve. Existing canonical-first successive upload defect remains S02 in the separate Python review, not waived by this row. |

## Tooling and operational script dispositions

| Finite boundary | Writer → consumer | Disposition |
| --- | --- | --- |
| `tools/ablation_protocol.py:build_manifest_rows`, `compute_sha256`, `write_checksums` | Incident files → manifest date from mtime and fresh streaming byte checksums. | Date is presentation; checksum is read anew, no stat-keyed hash cache. Concurrent-writer isolation is not claimed. |
| `tools/repair_forked_run_identity.py:_sha256_text`, `retry_cache_clear_from_backup` | Explicit repair records before/after text hashes → retry freshly reads each regular non-symlink NoDb, compares current content with recorded after-hash, then clears scoped cache. | Current byte/text validation, not size/mtime equality. Preserve identity/backup safeguards. |
| `tools/run_pytest_sharded.py:load_module_timing_cache`, `plan_shards` | Clean test durations → path-keyed estimate of future shard weight; fallback file size. Every selected module still executes. | Scheduling estimate, not test-result reuse. Stale timing can affect balance, not validate changed tests. |
| `tools/run_profile_coverage_batch.py:main` | Explicit `--skip-existing` option → skip a profile with an existing merged `.coverage` artifact. Default is false. | User-selected resume policy, no claim source bytes are current. Do not silently redefine the option as scientific cache admission. |
| `tools/compare_wepp_runs.py:file_hash` | Current directory files → fresh SHA, with documented `.sol` comment and `.slp` aspect normalization. | Intentional comparison semantics; no cached stat key. Do not remove format-specific normalization as a freshness fix. |
| `tools/peakflow_phase1_fixture.py`, `peakflow_phase1_1986_fixture.py`, `peakflow_phase1_instrument.py`, `peakflow_phase1_negative_control.py`, `peakflow_gate21_acceptance.py`, `peakflow_phase2a_pilot.py`, `surf14a_local_acceptance.py` | Explicit experiment input/binary/build manifests → freshly read byte hashes or serialized semantic hashes; phase2 pilot also compares run-directory hashes before/after execution. | Integrity/experiment evidence; no stat-keyed digest reuse found. `peakflow_phase1_protocol.py` defines hash-bearing schemas. `tools/peakflow_census.py` delegates to the Python census owner already traced separately. These scripts were not executed against named workloads. |
| `tools/split_d2b_taxonomy.py`, `refine_mofe_taxonomy.py`, `triage_pipeline.py` | Incident rows/rules → diagnostic family “signature” labels. | Classification vocabulary, not file identity. |
| `tools/eu_invalid_soil_search.py:_CachedRasterSampler`, `screen_manifest` | One screen invocation opens ESDAC source datasets once, samples cells repeatedly, then builds selected records. | Invocation-scoped native handle reuse. Source raster mutation during a study is not proven supported here; no cross-invocation stat cache. Shared indirect raster closure remains in the Python raster wave. |
| `tools/check_test_isolation.py`, `tools/perf/redis_nodb_cache_stress/run_harness.py` | Static test-isolation analysis, or explicit synthetic Redis stress samples. | Test tooling; not additional scientific file dependency. Do not run stress harness during discovery. |
| `scripts/deploy-production.sh` | `sha256sum` of the running script before/after authorized git pull decides restart; Compose topology is then resolved again. Build uses no-cache for selected services. | Fresh content check; Docker build-cache pruning is lifecycle policy. No deploy performed. |
| `tools/check_wepp_binary_provenance.sh`; Docker `validate-aux-image-contract.sh`, `validate-cap-runtime-contract.sh` | Fresh binary/ledger reads or pinned image digest → validation output; CAP checks before/after migration SHA. | Content/provenance validation, not metadata cache. Other Docker shell “cache” hits refer to tmpfs/package caches or explicit render request `skip_cache`. |
| `tools/wctl2/context.py`, `commands/maintenance.py`; `wctl/*.sh` | Each CLI invocation merges environment files into its own temporary environment; build-assets invokes the maintained builder. Installers/manifests select current paths. | Per-command configuration snapshot and explicit maintenance; no stat-based freshness shortcut found. |

The remaining listed tooling files contain direct analysis/read/write/generation
operations, not a reuse predicate selected by this discovery. This negative
search result does not certify arbitrary derived-result dependency completeness
inside every scientific tool or imported Python owner.

## Maintained browser dispositions and residual scope

| Boundary | Producer → reuse predicate | Disposition |
| --- | --- | --- |
| `gl-dashboard/data/wepp-data.js` | Stable model Parquet paths → year-keyed result maps, cleared on scenario transition. | B-F01 confirmed above; OPEN. |
| `gl-dashboard/graphs/graph-loaders.js` | Query-engine scientific rows → run/config/scenario/graph-option keys in `graphDataCache`, `hillLossCache`, `channelLossCache`, `outletAllYearsCache`, `hillslopeAreaCache`. Top-level `force` bypasses `graphDataCache`; lower caches can still reuse their results. | Concrete related browser result caches. Trace exists; no independent full graph failure probe. Include in the B-F01 contract's finite scope rather than declaring them verified safe or individually confirmed defects. |
| `gl-dashboard/layers/detector.js:ensureBatchGeoJson` | Each batch run's resources GeoJSON → module map keyed by batch/config/kind; promise retained, including missing/empty result. | Related geometry snapshot reuse. Batch membership/content is not in key. No supported within-page batch-membership change or actual failed refresh reproduced; candidate remains OPEN. |
| `storm-event-analyzer/data/event-data.js:fetchWarmupYear` | `MIN(year)` from climate Parquet → module caches keyed only by runid; subsequent event queries use that year in filters. | Related browser scientific dependency. Climate replacement can change this dependency; actual full event misfilter not reproduced. Include as candidate, not merely a harmless color cache. |
| `static/js/parquet_schema_preview.js:fetchSchema` | Authenticated schema endpoint → page-local promise keyed by URL, deleted on fetch failure but retained after collapse/reopen. | Schema view snapshot; path-only reuse. Changed-file behavior/UX needs explicit disposition. No producer-write or readiness admission occurs here; do not overstate this as a server cache bypass. |
| `templates/combined_ws_viewer2.htm:render` | WEPP subcatchment query rows → `dataCache[runid]`; changing variable clears the cache, range/unit restyling reuses data. | Page view memoization with explicit variable invalidation. Underlying-run regeneration while page stays open has the same unresolved view-generation question. |
| `map_gl.js:resolveLayerData`, `clearFindFlashCache`; `channel_gl.js`, `subcatchments_gl.js` | Resource geometry request → find/flash cache; successful channel/subcatchment loads clear the corresponding cache and expose fresh controller data first. Fetch adds a timestamp query parameter. | Managed refresh invalidation traced. No failure reproduced for that workflow; timestamp URL is network cache-busting, not scientific content proof. External file mutation without managed reload remains outside this narrow safe statement. |
| `disturbed.js`, `baer.js`, `omni.js` | Server has-SBS boolean → local UI availability state; upload/remove completion updates it and emits `disturbed:has_sbs_changed`; explicit refresh rereads endpoint. | UI projection. Not source-raster equivalence; backend still owns SBS freshness. |
| `http.js` | Session/token endpoint → expiry-aware token/promise caches keyed by run/config; explicit invalidation supported. | Auth TTL, not file dependency; preserve. |
| `ash.js`, `batch_runner.js`, `wepp.js`, dashboard `colors.js`, `map/raster-utils.js`, label/range caches | User form values, DOM references, color functions/legends, loader object and CSS style signatures → UI rendering reuse. | Non-file inputs or already loaded object transforms. No scientific-file equality claim at these cache entries. GeoTIFF loader-object cache does not cache source bytes. |
| `templates/controls/edit_csv.htm`, `landuse_map.htm`; disturbed lookup save route | Server's actual lookup SHA → browser baseline, stale warning and `X-If-Match-Sha256`/JSON precondition. Save holds controller lock and recomputes current lookup SHA before comparison. | Byte optimistic concurrency, not metadata. mtime in editor metadata is display. Preserve missing-token 428 and mismatch handling. |
| `project_config_update.js`, landuse upload table, `features_export.js` | Graph/structure/file hashes and cache-hit flags from server → explanatory UI. | Display of owner state; no independent browser file-hash cache. |
| `controllers_gl_stale_check.js`; maintained bundle builder | HTML expected build identifier vs actual bundle identifier → reload banner. | C10 owner/bundle identity boundary already reviewed. No additional mtime shortcut in this browser consumer. |
| Archive/diagnostics helpers, service worker | Archive/diagnostic fetches explicitly avoid HTTP storage; push service worker handles notifications, not a file-content response cache. | Transport/notification/lifecycle behavior. |

No explicit maintained-browser `ETag`, `If-Modified-Since` or `If-None-Match`
decision was found in the finite searched sources. Ordinary browser/server HTTP
caching still exists and is not certified byte-coherent by that negative result.
This review found no new confirmed Go/tool/script metadata-currentness defect;
the active GL result-generation gap and related browser candidate families must
receive an explicit package disposition before claiming exhaustive M1 coverage.
