# Features-export implementation QA

Date: 2026-09-16. Scope: implementation after accepted checkpoint `90a8a3dc9`,
including the subsequent native converter failure-retention correction.
Disposition: scoped QA PASS with non-blocking regression follow-ups below.
Complete native dependency closure, representative performance, and live runtime
acceptance remain separate open gates.

## Evidence

- `features_affected_tests.log`: 195 passed before the converter follow-up.
- `features_retention_tests.log`: 13 passed with the converter follow-up.
- `tests/nodb/mods/test_features_export_freshness.py` exercises real planning,
  DuckDB materialization, ZIP/manifests/cache, and GDAL GeoPackage/FileGDB output.
  Fixture catalog/profile selection is substituted; native processing is not.
  The synthetic legacy companion test now checks explicit unproven-source
  rejection, while native tests cover successful conversion and retention.
- Independent [probe](features_implementation_qa_probe.py),
  [results](features_implementation_qa_probe.json), and
  [log](features_implementation_qa_probe.log), executed through
  `wctl exec weppcloud python` under UID 1000/GID 993. Disposable native outputs
  are retained under `features_qa_inputs/67535796c16c/`.

| QA concern | Observed result |
| --- | --- |
| Same-byte restoration | Actual source rewrite plus changed mtime reused the GeoPackage cache; producer ZIP and manifest remained byte-identical |
| Companion from a cache-hit job | Native FileGDB contained value 25, retained the original artifact ID as source, and used producer run context even though the cache-hit job manifest lacked that context |
| Omni parent compatibility | Actual child-run export read `../../../../geometry.geojson`, hashed it, and produced a successful ZIP |
| Directory compatibility | SHA-mode dependency collection accepted the directory and retained null hash fields; this is snapshot evidence, not native directory-content freshness proof |
| Native packaging failure | Injected ENOSPC at `shutil.make_archive` after actual GDAL creation retained the candidate GDB tree and failure manifest; accepted companion bytes remained unchanged |
| Changed values and source conflicts | Native tests assert actual exported values, 409 `changed_source`, matching rejected/error manifests, and byte-for-byte preservation of prior artifacts/index |
| Companion failure after conversion | Native tests preserve both accepted profile archives, source manifest, cache index, and publication index |

## Maintainability and test quality

`dependency_tracker.py` retains a small separation between observable entry
metadata and fingerprint identity. Invalid/incomplete SHA fields retain mtime;
directory entries are not disguised as content-verified files. The existing
path resolver and parent-root rules remain in use, with the independent parent
export confirming the newly hashed path still works. The before/after stat
comparison is covered at the digest-to-entry boundary.

`service.py::_verify_export_submission` centralizes the bounded recheck and
retains a verdict before callers raise. It compares complete cache keys, so
request identity is checked as well as dependency fingerprints. Native tests
assert output values and durable retention, rather than only call counts.
Historical publication now takes the matching artifact's cache identity;
the native test proves subsequent source changes do not relabel that artifact.

Companion creation now has one clear candidate directory and one publication
point. Reading provenance from the cache-bound producer manifest avoids depending
on the more limited cache-hit job manifest. Deep copies prevent companion edits
from mutating producer dictionaries. The function has grown to roughly 180
lines: its sequential validation/conversion/publication stages remain readable,
but further companion features should extract the producer-proof validation
block before adding more nested checks. This is residual maintainability debt,
not a request to refactor the current correction.

The converter follow-up removes destructive failure cleanup. The new
`test_native_packaging_failure_retains_gdb_and_partial_zip` reaches the actual
packaging failure boundary and checks GDB bytes, partial ZIP, failure manifest,
and unchanged cache. This is stronger than only raising after conversion returns.
The independent probe confirms the same retention on current code. The existing
RQ failure path retains exception context; manifests provide browseable verdicts.

## Non-blocking follow-ups and limits

1. Promote the independent same-byte-rewrite/cache-hit-companion chain and
   SHA-mode Omni-parent case into durable regression tests. The current native
   test directly covers touch and changed-byte rewrite, but not the identical
   rewrite plus cache-hit producer-provenance sequence.
2. Add a companion rejection case driven only by Unitizer or export-version
   request identity. Existing cache-key tests verify Unitizer hashing and the
   implementation uses the complete current request key, but this specific
   conversion admission behavior is not directly asserted by the new tests.
3. Retain the scoped limitation in the README/specification: directory records
   and indirect native dependencies are not closed by regular-file SHA. The
   directory snapshot probe verifies compatibility only. No claim of directory
   content freshness or full vector/raster closure is made here.
4. The 195-test log predates the converter follow-up; its focused retention
   rerun passed 13 tests. Package-level representative performance, real
   RQ/download workflow, and archive/restore acceptance remain pending.

No production or test edits were made by this reviewer.
