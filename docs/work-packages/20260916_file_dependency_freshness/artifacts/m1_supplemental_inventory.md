# Supplemental discovery disposition

Execution baseline: `adb4f9b004459fc578460a95f30ac01ae1421f36`.
See discovery_scope.json for retained commands and unfiltered outputs. Raw outputs
include bundled vendor JavaScript; the compact file lists are navigation aids,
not assertions that every omitted hit was reviewed. Exhaustive discovery remains
open until all content-hash and cache consumers are traced.

## Traced additional consumers

| Boundary | Producer/consumer and role | Disposition |
| --- | --- | --- |
| rq-engine schema_defaults_routes `_sha256_file_cached` | Features-export output discovery returns SHA-256; cache keyed by resolved path, size, mtime | Open false-current candidate: equal-size/restored-mtime replacement returns old hash. Must reproduce real function and review output discovery contract before fix. |
| SWAT `_collect_run_outputs`, `_resolve_latest_run_dir` | Binary output collection relative to invocation time; latest-attempt presentation | Completion-order metadata, not a content-equivalence claim; preserve. |
| observed `_latest_run_dir` | Most recent run-directory selection | Presentation/completion order; preserve. |
| `_context_processors` last-modified projection | Redis receipts or maximum NoDb mtime for UI label | Display metadata; no scientific-content cache, preserve. |
| run_0 route run-directory ordering | Directory mtime used to sort displayed runs | Display metadata; preserve. |
| browse listing/files_api/runtime_paths/fs/query_engine.activate | Size/mtime exposed as file listing/catalog metadata | Metadata transport; not a digest proof. Preserve listing semantics. |
| shape_converter cleanup, CAO cleanup, scheduler, fork claim aging, OSM cache TTL | Age/expiry/lease cleanup | Lifecycle timing; do not substitute content hashes. |
| disturbed `_lookup_file_snapshot`, lookup-save route | Reads SHA-256, optimistic edit compare under lock; mtime is displayed metadata | No stat-keyed hash cache; content compare governs save. Preserve. |
| Geneva CN editor and browser edit_csv | `X-If-Match-Sha256` and lookup digest compared on saves | Content optimistic-concurrency token, not file metadata; preserve. |
| landuse catalog files and lookup editor | Actual byte SHA-256/serialized mapping digest | No timestamp cache discovered in route; preserve. Landuse controller fingerprint is a separate finding. |
| ks-last raster preparation | Source/grid bytes hashed before/after processing, output hash manifest | Content provenance with change check; no stat-only shortcut discovered. |
| RedisPrep/preflight2 checklist | Task completion order, Python postfire owner projection | Workflow prerequisite receipts remain advisory; do not reinterpret as file content identity. File edits without a managed owner event must still be caught by Python postfire currentness. |
| browser built bundles | Generated vendor assets contain unrelated WebGL attribute invalidation and local timing | Retain original search lines; maintained app sources searched independently. Not file dependency consumers on that evidence. |

## Open scope

Independent correctness/security inventories retain the core seed dispositions.
Remaining broad hash consumers (ag-fields, climate admission, road manifests,
project-config snapshots, profile playback, replay/migration tools and report
cache families) must be traced before marking M1 exhaustive. Source-list counts
are not semantic coverage. Confirmed in-scope defects remain package blockers.
