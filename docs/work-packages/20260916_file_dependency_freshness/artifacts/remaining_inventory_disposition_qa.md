# Remaining maintained families: QA disposition draft

Reviewer: `freshness_qa`, 2026-09-17. This consolidates the retained finite
inventories and current source tracing without new runtime probes or production
changes. It is an explicit bounded disposition draft for the package owner,
not a claim that every repository dependency or live workflow is verified.

Evidence anchors are `remaining_semantic_inventory.md`, its exact commands in
`remaining_semantic_search_scope.json`, and
`remaining_services_tools_browser_inventory.md` with
`remaining_nonpython_scope.json`. The earlier `m1_supplemental_inventory.md`
remains historical discovery. Its output-discovery SHA shortcut is now owned
by the separately reviewed shared-digest implementation; its old OPEN label
does not supersede that later evidence.

Here **verified-safe** means the specified inspected predicate does not replace
content equality with file size/mtime. It is not certification of all concurrent
writers or indirect inputs. **Nondependency** means the timestamp/cache has a
different documented purpose. **Justified unresolved** preserves a concrete
closure/contract gap without calling an untested ordinary workflow defective.

## Roads and AgFields

| Boundary | Evidence and bounded disposition | Smallest follow-up |
| --- | --- | --- |
| Roads controlled upload/parameter admission | **Verified-safe for controlled-ingest identity.** `roads.py:set_uploaded_geojson` copies the selected upload, hashes the staged bytes freshly and persists the receipt under the controller lock; upload/parameter mutations invalidate state. `_require_prepare_state_current` compares that receipt and the normalized parameter signature. This is an ingest receipt, not an mtime-based rehash cache. | Preserve the ingestion boundary and existing parameter semantics. Do not use an arbitrary behind-the-controller file replacement as proof of an ordinary upload failure. |
| Roads upstream raster dependency closure | **Justified unresolved.** `_resolve_prepare_raster_paths` selects relief or DEM, netful and subwta; preparation consumes them. Prepared-state currentness does not bind those selected raster bytes. Run tracing also selects flovec. The retained review has no actual ordinary upstream rebuild → Roads rerun result comparison. | On a disposable project, prepare Roads, perform the maintained watershed/DEM update, then execute the normal Roads entry point and compare prepared/routed outputs with explicit fresh preparation. Record actual raster selection and completion behavior before proposing a source-proof checkpoint. The C08 Roads manifest dependency correction is separate. |
| AgFields Stage4 workflow/mapping completion | **Verified-safe for the stated receipt contract.** `AgFields._workflow_signature` freshly hashes rotation lookup; schema/upload mutations invalidate recorded state. Raw execution clears interchange completion. `mark_wepp_ag_fields_interchange_complete` requires matching current/raw workflow signatures and deep bundle validation under lock. `has_current_wepp_ag_fields_interchange` requires those signatures plus the bundle. `ag_fields_interchange.py` hashes the mapping before/after native conversion, stages six outputs under a directory flock and publishes the last-written manifest. | Keep completion markers and manifest-last publication. Size checks describe the completed inventory; they do not claim each output's current SHA. No change is justified merely because an equal-size unmanaged output edit can bypass a fast size check. |
| AgFields wider Stage4/5 and native closure | **Justified unresolved beyond that receipt contract.** README explicitly limits Stage4 staleness to boundary/schema/rotation; preflight additionally orders completion after parent WEPP/watershed/landuse/soils/climate. Stage5 hashes actual selected inputs/executables and uses isolated attempt climate-hash dictionaries, but those facts alone do not prove a coherent complete cross-stage/native set. | First exercise an actual parent-input update through its maintained writer and Stage4 readiness/Stage5 admission, including a failed producer and retained previous result. Compare real outputs with a normal rebuild. If disagreement is demonstrated, decide the smallest cross-stage contract correction; do not silently redefine Stage4 completion or replace preflight receipts with hashes. |

These are targeted source traces. No new Roads or AgFields numerical failure,
security incident, or whole-workflow pass is asserted.

## Geneva whole-HRU preparation is a separate boundary

**Justified unresolved for whole-preparation source currentness.** In
`collaborators/hru_preparation_service.py:prepare_hrus`, a request with
`force_rebuild=False` can return `hru_prepare_summary.json` before resolving
current raster references or supplied `input_refs`.
`_is_cached_summary_current` checks required output existence, expected map/legend
locations and current CN lookup SHA. It does not compare source raster content
or newly requested input bindings. The specification's CN-table invalidation
rule and its Run All normalization explicitly describe the existing boundary;
`rq_engine/geneva_routes.py:_normalize_workflow_request` forces preparation to
rebuild. This is source-traced behavior, not a new numerical runtime probe.

C05 geometry and C06 aligned-burn acceptance therefore do not establish that
every cached whole-preparation request invokes those corrected readers. Their
accepted scoped native/performance evidence remains valid. Changing the meaning
of `force_rebuild=False` or ignoring explicit current `input_refs` requires a
separate behavior/compatibility decision, not an unannounced lower-level fix.

The minimum follow-up is a disposable normal Run All operation proving the
current aligned artifact reaches the native kernel, plus a paired explicit
cached-versus-forced preparation after one maintained source change. Retain the
resolved inputs, summary/table/map outputs and emitted status. Use that evidence
to decide whether cached preparation means an accepted prepared snapshot or
current-source preparation, then specify legacy reuse and rebuild cost. No new
generation protocol or speculative full raster framework is justified here.

## Other retained Python/content families

| Finite family | Disposition and evidence limit | Smallest follow-up if stronger assurance is required |
| --- | --- | --- |
| Project config builder/preset snapshots and config reader | **Verified-safe for byte association.** Builders hash the immutable bytes they serialize; reader observations bind parsed state to those bytes. Revision/lock authority is separate. Warning-mode hash mismatch is intentional compatibility behavior. | Preserve warning versus exact-authority rejection. Do not add new rejection policy as a freshness cleanup. |
| Postfire offline replay and peakflow replay packets | **Verified-safe at replay identity.** Opened transcript bodies are rehashed against retained content with byte/request checks; peakflow verifies canonical serialized packet hashes. | Full acquisition authority and numerical parity stay with their owning reviews. No stat-cache correction is needed at these predicates. |
| PATH cost-effective sweep | **Verified-safe for ordinary sequential key construction; cross-file publication unresolved.** The sweep hashes prepared-frame bytes and selected configuration/schema after preparation. No metadata-keyed hash cache is present. | Only if concurrent frame replacement is a supported workflow, retain an actual prepared-frame/hash mismatch probe and define publication authority. No such failure is established here. |
| Omni base-loss helper and contrast receipts | **Verified-safe fresh loss hashing; broader contrast reuse justified unresolved.** `_hash_file_sha1` rereads bytes. Contrast reuse also relies on selected completion receipts/sidecar metadata. Missing/unreadable loss can yield `None`; full unavailable-source reuse behavior is not established. | Exercise supported loss removal/failed producer and contrast retry with actual output admission. Preserve completion semantics. S01 and C07 have separate explicit dispositions. |
| Geneva artifact hashes and ks-last provenance | **Verified-safe at inspected hashing calls.** Artifact hashes read bytes anew; ks-last records source/grid checks and output provenance. Neither is the whole-Geneva preparation cache above. | Additional indirect/concurrent-source assurance needs the actual native reader and maintained writer, not a generic format-capability argument. |
| Resource unroll migration | **Verified-safe byte-conflict predicate; concurrent move/publication unresolved.** Source/target hashes are fresh; differing targets fail, and creation uses no-overwrite mechanics. No migration was executed. | Characterize an authorized disposable migration under its existing quiescence/recovery contract before changing move/receipt behavior. |
| Other maintained report classes | **No additional persistent result-cache dependency identified in the finite report subtree.** Persistent `ReportCacheManager` consumers were C08/C09; those waves have their own accepted proofs. Other traced classes use current queries or instance-local data. | Catalog/renderer behavior outside that finite trace is not certified; reproduce a maintained stale result before extending the cache mechanism. |
| Generic/config profile seeds | **Nondependency as initial historical snapshots.** A copy-if-absent seed is not inherently a claim of current source equality. S02's confirmed successive SBS event defect has its separate implemented proof. | Other successive upload families (landuse/CLI/cover-transform) remain **justified unresolved event-fidelity candidates** until an actual repeated-upload replay is retained. Do not mark them fixed by the SBS change. |

## Services, tools and browser scope

The maintained service/tool/browser inventory retains exact files and paths for
the following grouped dispositions; these groupings do not extend that search.

- **Nondependencies:** status2 transport timers; preflight2 task-order receipts
  and last-modified display; startup credential snapshots; CAO/cleanup age
  cutoffs; GridMET admission configuration/leases; shard-duration scheduling
  estimates; explicit `--skip-existing` coverage resume; diagnostic taxonomy
  signatures; run-directory ordering and file-listing metadata. Preserve their
  time/order/resume semantics.
- **Verified-safe inspected content checks:** CAP secret rereads and migration
  ledger hashes; repair before/after text validation; ablation/binary/experiment
  manifests; deploy-script before/after SHA; canonical lookup editor byte
  preconditions under lock. CLI environment snapshots and analysis generators
  introduce no identified cross-invocation stat-based result shortcut. This
  does not certify each tool's native inputs or authorize execution/deployment.
- **Justified unresolved concurrent-native boundary:** the ESDAC screen sampler
  keeps native handles for one invocation. No maintained mid-study source
  mutation or cross-invocation reuse defect is proven. An actual supported
  mutation/output probe is needed before changing that lifetime.
- **No mutable-asset defect established:** CAP assets are selected from the
  pinned image with no reviewed write mount; Express owns HTTP conditional
  serving. There is no claim of content-hash ETags and no demonstrated mutable
  producer. General HTTP cache semantics are not certified by a negative grep.
- **Browser disposition already explicit:** B-F01 is a confirmed active GL
  mixed-generation result defect, justified unresolved for the documented UX
  contract gap in `browser_generation_unresolved_disposition.md`. Related graph,
  batch geometry, warmup-year, schema-preview and combined-viewer caches remain
  unconfirmed members of that finite unresolved view-generation scope. The
  legacy Leaflet reproduction lacks a maintained entry point. Managed GL
  geometry refresh invalidation is verified by tracing only for that refresh
  path; loaded-object/style caches and auth TTLs are nondependencies.

Vendored/minified code, excluded legacy wrappers, untraced imported scientific
owners and arbitrary renderer internals are outside the retained finite search;
they are not silently labeled safe. C02/C07's minimum remaining evidence is in
`features_omni_remaining_closure_qa.md`. The implemented S01/S02 and C01–C11 waves,
their explicit unresolved native boundaries, and full package runtime acceptance
continue to be tracked separately. This draft supplies dispositions and next
evidence, not permission to omit a confirmed defect or declare the package done.
