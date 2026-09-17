# Remaining M1 semantic inventory

Independent correctness reviewer: `freshness_correctness`, 2026-09-17 UTC.
No production/test edits, named-run mutations, queue submissions or deployment.
This follows the retained discovery lists and extends C01–C11; it is **targeted
semantic coverage, not an exhaustive repository audit**. Exact follow-up search
commands/revision and unfiltered results are retained in
`remaining_semantic_search_scope.json` and its named text artifacts.

## Confirmed additional defects

### S01 — High: same-name Omni SBS re-upload skips the changed scenario

`omni_routes.py:_prepare_omni_scenarios` saves uploads into
`omni/_limbo/<index>/<filename>` with `overwrite=True`. Re-uploading a different
raster under the same filename is supported. `OmniInputParsingService.parse_scenarios`
keeps only scenario type/path for SBS maps and does not invalidate the stored
scenario dependency tree. `OmniStationCatalogService.scenario_signature` serializes
that mapping without observing SBS bytes. Both `OmniRunOrchestrationService.run_omni_scenarios`
and `rq/omni_rq.py:run_omni_scenarios_rq` reuse when the base loss hash and scenario
signature match. The direct service additionally checks year-set equality.

`remaining_semantic_baseline_probe.py` exercises the real route upload helper,
parser, production signature and direct run orchestration on disposable projected
GeoTIFFs. The first upload contains class 1, the same-name second upload contains
class 3. The actual saved path is unchanged and contains class 3, but statuses are
`executed`, then `skipped`; the scenario executor is called only for class 1.
The expensive executor is a recording seam, not a WEPP model run. Base loss and
year inputs are real parquet files. This proves the supported upload-to-skip
decision beyond an extracted predicate, but does not claim live RQ/UI acceptance.

Owner: Omni scenario dependency/reuse contract in the module README and RQ/domain
contracts. Regression anchors: `tests/nodb/mods/test_omni_run_orchestration_service.py`,
`tests/rq/test_omni_rq.py`, rq-engine Omni route tests. Existing direct-service test
fixtures replace the signature with a type-only stub and cannot detect this case.

Smallest proposed correction: include the actual selected SBS dependency identity
in accepted scenario provenance, with main-file versus native indirect closure
explicitly distinguished; use the same identity in direct/RQ skip decisions and
publication. Decide legacy dependency-tree entries conservatively before edits.
Do not rename every upload or clear unrelated scenarios merely to hide the issue.
Keep existing source path, parameters, base loss and year rules. End-to-end model
and UI evidence, source changes during execution, and recursive raster closure
remain required. This is separate from stream-order pruning C07.

### S02 — Medium: profile replay loses successive upload identity

`ProfileAssembler._snapshot_sbs_upload` refreshes the named seed (for example
`sbs.tif`) but creates canonical `input_upload_sbs.tif` only when absent.
`PlaybackSession._populate_sbs_form`, called by `_build_form_request`, selects that
canonical file for every SBS request without per-event source binding.

The same retained probe records two successful upload response events, first
class 1 then class 3. The named seed correctly ends at class 3; the canonical seed
remains class 1. Real multipart reconstruction selects class 1 for **both** events.
Only controller acquisition is injected for recorder discovery; copying, event
recording, selection and GDAL reads are real. No external HTTP playback or full
profile-engine workflow is claimed. Both events are retained, so this is loss of
input identity rather than a missing capture event.

Owners: `profile_recorder/PROFILE_TEST_ENGINE_SPEC.md` Assembly/Playback and nearest
AGENTS upload support. Tests: `tests/profile_recorder/test_assembler.py` and
`test_playback_session.py` cover single seeded uploads; add same-name multiple
events. Similar canonical-first behavior exists for landuse, CLI and cover
transform; those families were inspected but not separately reproduced.

Overwriting only the canonical seed is insufficient: it would replay class 3 for
both events instead. A bounded checkpoint must bind each captured upload event to
its retained bytes, preserving the legacy canonical-seed reader for old profiles.
Retain original captures; do not silently rewrite existing profile history.
This requires an additive capture/playback contract, not a generic hash-cache fix.

## C07: native stale-output mechanism, ordinary receipt path distinguished

`omni_pruning_native_probe.py` invokes installed WBT through the actual
`_prune_stream_order` and service reuse helpers on disposable projected rasters.
Changing the stream source while holding the completion receipt fixed leaves
`needs_prune=false`; the cached map retains 5 stream cells, while direct native
rebuild from current sources retains 1. JSON/log and script are retained.

This experiment deliberately omits a new completion event. It does **not** prove
that ordinary watershed rebuilding violates the completion-order assumption:

- `WatershedOperationsMixin.build_channels` removes `subwta`; Omni validates that
  required source before reusing generated maps, so an intervening normal channel
  rebuild does not silently proceed with a missing subcatchment map.
- `build_subcatchments` clears its timestamp before work and stamps completion
  on success. Successful ordinary rebuilding makes older pruning products stale.
- `symlink_channels_map` changes channel sources and stamps only build-channels;
  its observed callers are CulvertsRunner creation/repair, not a proven ordinary
  Omni contrast regeneration sequence. Shared/VRT backing source changes and
  restoration of cached outputs/receipts need a separate supported-workflow probe.
- An absent build-subcatchments receipt makes `_is_stale` return false. Missing
  generated files still rebuild, but existing products get no source proof.
  Concurrent completion/partial-generation semantics remain unresolved.

Keep C07 OPEN with stronger native mechanism evidence. Completion receipts remain
necessary orchestration state; do not replace them with byte hashes. Main rasters,
outlet, native sidecars/VRT sources and settings form a separate freshness closure.

## Other traced families and dispositions

| Family / concrete boundary | Writer and caller evidence | Disposition for this audit |
| --- | --- | --- |
| AgFields interchange `_manifest_is_current` / `has_current_wepp_ag_fields_interchange` | Stage 4 clears the completion marker before raw execution; six native outputs are staged under a directory flock, validated, then published with last-written manifest. Mapping parquet is hashed freshly before/after conversion and on currentness reads. Stage completion also requires raw/workflow/interchange signatures. Routes and features export consume the check. | Completion/schema/mapping contract, not a claim that output size is a content hash. No restored-time hash-cache shortcut found. Fast reads inspect output size; deep reads add schema/row counts. Neither proves all output bytes or raw-source identity. Preserve receipt semantics; do not call arbitrary equal-size artifact mutation a confirmed ordinary-writer defect. |
| AgFields workflow and routing provenance | `_workflow_signature` freshly hashes rotation lookup; upload/schema mutations reset state. Stage 5 integrators freshly hash input files/executables, and per-attempt climate-hash dictionaries live inside isolated execution. README explicitly limits Stage 4 staleness to boundary/schema/rotation, while preflight completion must also be newer than parent WEPP/watershed/landuse/soil/climate. | No stat-keyed hash cache found. Stage 4 currentness versus broader upstream preflight is a distinct contract boundary; do not silently expand it. Cross-file/sidecar/concurrent-parent-input closure is not proven by these hashes and remains a coverage gap. |
| Roads upload / prepare state | `set_uploaded_geojson` reads the staged target bytes for SHA-256 and saves the receipt under lock. Upload/parameter changes invalidate prepared/run state. `_require_prepare_state_current` compares stored upload receipt and normalized parameter digest. `prepare_segments` additionally consumes DEM/channel/subwta rasters; `run_roads_wepp` loads prepared features. | Stored upload digest is legitimate controlled-ingest provenance, not a stat-keyed cache. Upstream raster identity is absent from prepare freshness; an ordinary upstream-rebuild/road-rerun scientific probe is still needed before classifying that omission as a supported-flow defect. The Roads pass manifest's report dependency is already confirmed C08. |
| Project config builder / preset snapshots | `snapshot.resolve_builder_candidate` and `project_config_snapshot` hash the same immutable config byte objects they serialize. `project_config_reader._read_parser_observation` returns parser plus the exact byte observation; exact-digest checks hash those bytes. Update authority additionally uses explicit revisions/locks. | Correct byte association by inspection; no metadata-keyed reuse. Reader digest mismatch warning is intentional compatibility behavior, while exact-authority checks reject mismatch. Do not convert warning-mode reads into a new rejection policy. |
| Profile generic/config seeds | `_snapshot_candidate` and `_ensure_config_seed` keep initial seed copies; later playback creates a clean workspace and replays events. | Initial seeds are not generally a "current source" cache. The actual successive upload defect is S02, not every copy-if-absent call. Config-event fidelity beyond these traced rules remains unverified. |
| Other report families | Maintained `wepp/reports` search found persistent `ReportCacheManager` use only in C08/C09. Other report classes obtain current queries or instance-local data; query context catalog metadata resolves actual dataset paths. | C08/C09 full result probes already retained in `reports_freshness_baseline_review.md`. No additional persistent report cache defect established in this subtree; this does not audit every external report renderer or catalog refresh policy. |
| Omni base-loss and contrast metadata | `_hash_file_sha1` reads actual loss bytes each call. Scenario reuse also requires scenario signature; contrast skip uses sidecar SHA plus selected RedisPrep run-completion receipts. `_contrast_dependency_entry` records additional loss hashes. | Hash helper itself has no stale stat cache. Missing/unreadable loss yields `None`; complete source-unavailable reuse behavior needs separate review. Scenario SBS omission is S01. Contrast receipt equality assumes managed producers; full loss-content validation is not established by receipt comparison. |
| PATH cost-effective sweep | `_sweep_cache_key` freshly hashes the prepared frame and relevant configuration/schema. `run` captures one config snapshot, prepares frame, solves, then sweeps. | Ordinary sequential path is content-keyed, not mtime-keyed. Concurrent frame replacement between in-memory preparation and file hashing would need a coherent-publication probe; no confirmed supported-flow failure here. |
| Geneva artifact hashes | `artifact_io.sha256` freshly reads bytes; batch-run service stores panel/table/legend provenance in result artifacts. | Provenance hashing, not a cached digest shortcut. Separate existing HRU geometry/HSG cache defects C05/C06 remain open. |
| GridMET admission `fingerprint` | JSON of queue limit, lease, polling and compatibility settings sent to Redis admission scripts. | Configuration/lease compatibility, not file identity. Preserve timing semantics. |
| Postfire offline `ReplayTransport` | Bounded transcript initialization hashes records/bodies; each opened body is rehashed against the retained value before replay, with request/byte-count checks. | Content-pinned replay, no stat-only digest reuse. Full source-acquisition/security acceptance remains owned by the postfire review. |
| Peakflow replay packets | `tools/peakflow_phase1_replay.py` hashes canonical serialized payload and `verify_packet` compares the payload hash before numerical replay. | Semantic payload identity, not filesystem metadata. Numerical correctness is outside this inventory. |
| Resource unroll migration | `_sha256_path` reads source/target bytes; differing existing target is explicit conflict, equal content follows migration policy, create uses no-overwrite mechanics. | Content conflict detection, not a reusable digest cache. No migration was executed. Concurrent source mutation/move receipts and operator quiescence are not accepted by this read-only inventory. |

## Evidence limits and next bounded work

The two upload probes and native pruning probe exit 0; raw logs and JSON remain
browsable. These are discovery experiments, not substitute production regression
tests. No new production change is approved by this inventory alone.

S01 and S02 require contract checkpoints and scoped fixes or an explicit retained
scope disposition; they cannot disappear behind closure of the original eleven
items. C07 ordinary-source/receipt coherence, Roads upstream raster regeneration,
AgFields cross-stage currentness boundaries, native indirect dependencies and
remaining raw discovery families still need semantic coverage. Full live RQ,
profile HTTP playback, representative performance and archive/restore acceptance
were not exercised. Search hits/counts do not settle those obligations.

## Geneva whole-preparation cache boundary

`GenevaHruPreparationService.prepare_hrus(force_rebuild=False)` returns an
existing `hru_prepare_summary.json` before resolving current raster references
when its CN lookup SHA matches and HRU table/map/legend outputs exist.
`_is_cached_summary_current` does not compare source rasters or the newly supplied
`input_refs`. Thus the C06 alignment correction runs on new/forced preparation,
not on every explicitly cached preparation request. The normal RQ run-all
normalizer sets `force_rebuild=True`; its downstream acceptance must verify the
corrected aligned artifact reaches the kernel payload.

Disposition: preserve this separate existing cached-preparation contract in the
bounded C05/C06 wave. It is a semantic inventory boundary requiring a separate
decision if whole-HRU reuse is made sensitive to current source bytes. Do not
declare it fixed by lower-level alignment freshness or silently change the
meaning of `force_rebuild=False`. This entry is based on actual caller/writer
tracing; no new native preparation, model run or permission mutation was executed.
