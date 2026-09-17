# Features implementation correctness review

Independent reviewer: `freshness_correctness`, 2026-09-17 UTC.
Compared current implementation with accepted ancestor `90a8a3dc9` and the
canonical File-content cache identity amendment. Production/tests were read-only
for this review. **Scoped PASS: no unresolved major correctness finding.**
Indirect native dependency closure and full runtime acceptance remain OPEN.

## Finding and disposition

**FE-I01 — Low, resolved:** companion cache construction originally copied the
GeoPackage producer's `layer_outputs[*].format` unchanged while changing root
format and layer paths to FileGDB. `cache_rehydration` would reconstruct
inconsistent typed output metadata. Current `service.py` now sets both layer
`relpath="features_export.gdb"` and `format="geodatabase"`. The native companion
regression also exercises an actual subsequent cache hit and asserts the cache
layer formats and job-manifest GDB paths. This matches the independently reported
security finding; the original observation is retained here.

No new cache-poisoning path was found in the scoped changes after this correction.

## Correctness assessment

- `dependency_tracker` opts into the shared coherent ordinary-file digest helper
  only for regular files. It binds the digest to its own before/after device,
  inode, size, mtime and ctime observations. Identity excludes diagnostic mtime
  only for present entries with a lowercase 64-hex SHA-256 marker/value. Explicit
  metadata mode, missing entries and directory metadata remain unchanged. Digest
  failures do not fall back to a metadata key.
- `prepare_export_submission` requests SHA mode and preserves initial hash error
  causes under `changed_source` 409. `_verify_export_submission` rebuilds the
  selected plan's dependency/request identity using the same catalog, including
  the existing Unitizer preference fingerprint. It compares complete cache keys,
  not just the file portion. Expected verification failures return a verdict for
  retention before the caller raises.
- Primary materialization decides the source verdict before writing success
  README/ZIP data or a cache binding. Rejection writes matching candidate/job
  manifests and retains materialized payloads; existing cache/index/artifact bytes
  are untouched. Cache-hit manifests label verification as `cache_selection`;
  the accepted ZIP/README is not rewritten by a new observation.
- Companion creation checks the actual source artifact's cache binding against
  the corresponding current GeoPackage request key, so Unitizer/version changes
  cannot be excused by equivalent request text. It requires verified producer
  provenance, matching dependency fingerprint/request/artifact identity, and
  shared catalog resolution. This closes the retained native old-25/new-75
  attribution failure before conversion starts.
- Conversion uses a new UUID artifact directory. The post-conversion verification
  runs before reusable insertion; rejected candidates have their own manifest,
  leaving both prior companion ZIP and source GeoPackage manifest unchanged.
  Successful companions deep-copy producer lineage, update request/artifact/layer
  references, and package their own manifest and README beside the native GDB.
  Cache/result references point to that companion manifest.
- Native conversion no longer deletes partial GDB/ZIP output on subprocess or
  packaging failure. The caller retains a conversion-error manifest. Dual-profile
  publication performs conversion first, preventing an unsuccessful companion
  attempt from partially advancing the GeoPackage profile binding. Existing
  publication/cache integrity rules continue to govern later selections.
- `publish_profile_artifact` now derives identity from an actual artifact-matching,
  format-compatible cache binding. It does not rehash today's sources and label
  an older artifact with them. Historical publication/download remains available
  after source removal. Missing historical content proof rejects new companion
  conversion without invalidating old downloads.

## Retained validation reviewed

- `features_affected_tests.log`: **195 passed**, including service, dependency,
  cache/manifest/writer and rq-engine compatibility tests.
- `features_native_freshness_tests.log`: **6 passed** original native regressions;
  `features_review_regressions.log`: **10 passed** after adding request-version,
  initial digest-failure and source-removed historical retrieval cases.
- `features_affected_tests_final_revision2.log`: **199 passed**, including the
  subsequently added FE-I01 cache-hit assertions. The preceding final log retains
  **198 passed, 1 failed**: its same-size in-place mutation happened within one
  observable stat quantum. The corrected regression uses atomic replacement to
  guarantee observable inode drift, without changing production behavior. A
  completed old-byte hash remains a valid point-in-time observation under the
  ratified coherent-read contract; the original timing-sensitive assertion was
  not evidence of a mixed-generation digest.
- `features_retention_tests.log`: **13 passed** native converter/freshness cases.
  `features_native_packaging_retention_after_probe.log`: **1 passed** actual native
  packaging-failure probe. Twenty native files totaling 52,335 bytes and the
  partial ZIP remain byte-identical after the injected packaging error.
- Security's retained service probe: **5 passed** for initial denial, request/
  version/producer-proof rejection and historical publication. QA's retained
  probe additionally exercises permitted parent-root input and directory snapshot
  states; these do not establish recursive native closure.

The tests use real materialization and native GeoPackage/OpenFileGDB writers for
the principal source-change and companion cases, with catalog selection and
failure injection explicitly bounded. Earlier failed tests/probes remain retained;
this review does not overwrite or reinterpret those baselines as successes.

## Performance and residual coverage

The representative read-only submission benchmark resolves 24 dependency entries
over 14 unique files. Revision 2 records 0.2745 s for cold prepare plus final
verification, versus 0.2141 s for the measured metadata-only full preparation;
the stated two-pass budget is 0.4996 s. Settled prepare plus verification averages
0.2255 s with zero digest misses. The original failed 0.0885 s budget calculation
is retained: it measured only dependency resolution and omitted existing catalog,
planning and Unitizer preparation. The correction measures those real existing
costs rather than excluding the new hashing work. This passes the bounded measured
submission budget, not large-export or live-route throughput acceptance.

Unitizer-specific preference mutation is checked structurally by the complete
request-key path; a separate real project-units mutation regression was not found
in the new native module. Full RQ execution, browser downloads, cross-process
permissions/mounts, archive restore and large native workloads remain package
acceptance obligations. The retained initial/final observations cannot detect
arbitrary change-and-restore within materialization, as the checkpoint states.
Raster/vector sidecars, recursive VRT and directory-backed input content remain
explicit OPEN closure items. None is claimed solved by hashing catalog main files.
