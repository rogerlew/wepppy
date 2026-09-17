# Features export implementation security review

Independent review by `freshness_security`, 2026-09-17 UTC, against accepted
checkpoint `90a8a3dc9`. Production/test changes were read only; this reviewer
created disposable probes and review artifacts.

## Findings and disposition

**PASS for the corrected bounded implementation. No open scoped medium/high
findings.** This is not runtime, archive/restore or package closeout approval.

- **FE-C01, High, closed in scope:** companion conversion now binds to the
  accepted source artifact's cache key and verified producer manifest. It cannot
  assign old converted payload to today's different dependency/request identity.
  Real native value tests cover same-source success, changed-source rejection
  and a later new-source cache miss.
- **FE-S02, Medium, closed in scope:** separate companion candidate directories
  preserve an accepted ZIP, source manifest and prior cache/publication bindings
  when another conversion fails or its final dependency observation changes.
  Both profile writes occur after companion verification.
- **FE-I01, Medium, found and corrected during this review:** the native helper
  initially deleted all useful partial GDB work on timeout/nonzero exit or ZIP
  packaging failure before the wrapper could retain it. Real native conversion
  followed by an injected packaging ENOSPC reproduced the loss. Failure cleanup
  is removed; the corrected independent probe retains every native file and the
  partial ZIP with the error manifest. Original failure evidence is retained.
- **Minor metadata correction:** companion cached layer outputs initially kept
  `format="geopackage"` from the source. They now use `geodatabase`, consistent
  with the actual artifact and rehydration. No stale numerical result was
  demonstrated from this metadata defect.

## Changed boundaries and valid-state behavior

`dependency_tracker._build_entry_for_relpath` hashes regular files through the
reviewed ordinary-file helper, then compares device/inode/size/mtime/ctime to
the initial observation. `_entry_identity` removes diagnostic mtime only for a
present entry with a lowercase 64-hex SHA-256 value. Missing/malformed hashes
retain metadata identity. Existing directories and absent dependencies retain
their explicit states, and low-level `none` mode remains unchanged. Existing
run/parent-run path resolution and ordinary allowed symlink semantics remain.

`prepare_export_submission` explicitly selects SHA mode and translates observed
filesystem read failures to `changed_source` 409 with the original cause.
It does not return a previous digest or silently downgrade to metadata identity.
`_verify_export_submission` rebuilds the resolved request with the same catalog
and compares the complete cache key, covering request versions and Unitizer
preferences as well as dependency content. It records rejected/error/verified
observations before primary success manifests, README, ZIP and cache publication.
Primary rejection preserves prior index/artifact bytes and writes matching
artifact/job failure manifests while retaining materialized payloads.

Cache-hit job manifests use `scope="cache_selection"` and retain the accepted
content fingerprint while the original ZIP/README stay immutable. No claim is
made that the old artifact was materialized again. The README now includes the
catalog observation verdict without inventing recursive dependency closure.

## Companion provenance, errors and publication

`co_create_post_wepp_geodatabase_artifact` resolves the current companion and
corresponding GeoPackage plans from the same catalog. Before conversion it
requires the accepted source cache entry under the complete current producer
key, matching artifact path, matching dependency fingerprint and matching
artifact ID in a verified producer manifest. That manifest's resolved request
must equal the expected GeoPackage request. Missing legacy proof or request/
version mismatch fails before creating a reusable companion; historical hashes
are not manufactured.

Conversion writes a fresh visible artifact directory. After native conversion,
the complete companion submission is verified again. Its manifest carries the
source artifact/job association, companion request, own artifact paths and
verification verdict. Successful ZIPs include that manifest and generated README;
cache/result manifest references point to the companion. Source provenance and
earlier accepted companion files are preserved. Failed conversions retain an
error manifest and useful partial files; failed final verification retains the
candidate with rejected/error provenance and does not publish it.

The native helper's failure cleanup removal is limited to retaining useful work.
It still reports timeout, subprocess diagnostics and packaging failures through
the existing writer-error contract, never treating partial output as success.
Successful redundant GDB-directory cleanup occurs only after the usable ZIP
contains the complete tree and provenance. Candidate storage remains in the
established browsable/archive layout.

`publish_profile_artifact` derives identities from the actual artifact-matching
cache entry and validates format instead of recollecting today's source files.
Missing/incompatible mappings retain `stale_publication` behavior. Dual-format
orchestration verifies conversion before either profile registry update.
Historical download resolution and route access/job-completion guards remain
unchanged. This preserves artifact selection after sources change or disappear;
it does not add current-source certification to historical retrieval.

## Independent evidence and limits

- `features_native_packaging_retention_probe.py/.log`: real first native output,
  **20 files / 52,335 bytes**, then injected `make_archive` ENOSPC; the original
  helper deleted all native files and the partial ZIP. One characterization
  test passed, recording the defect rather than acceptance.
- `features_native_packaging_retention_after_probe.py/.log`: same real native
  path after the fix; **all 20 files and the partial ZIP remain**, with one error
  manifest. **1 passed in 9.15 seconds**. The injected packaging failure is a
  bounded error seam, not a claim that the disk was actually exhausted.
- `features_service_security_probe.py/.log`: **5 passed in 9.19 seconds**.
  Under an unprivileged container identity, actual chmod read denial becomes
  409 with a `PermissionError` cause. Changed request/version or removed producer
  verification proof prevents conversion and preserves the index. Historical
  publication/resolution still returns identical ZIP bytes after both catalog
  source files are removed. Only disposable fixtures were changed.
- Parent evidence: `features_native_freshness_tests.log` initially **6 passed**;
  `features_retention_tests.log` **13 passed**; `features_affected_tests.log`
  **195 passed** across feature modules, RQ worker and export routes. Native
  tests read actual parquet/OGR ZIP values and preserve exact prior index, ZIP,
  source manifest and publication bytes under post-conversion mutation/ENOSPC.
  Earlier mock-signature/provenance fixture failures remain retained; the old
  synthetic companion test now checks explicit legacy rejection and real native
  tests cover supported generation. `features_review_regressions.log` then
  records **10 passed in 11.31 seconds**, including request-version rejection,
  initial read failure, missing-source historical retrieval and actual native
  packaging-error retention.

The shared helper's point-in-time/coherent-filesystem assumptions still apply.
Neither before/after observations nor this test set establishes arbitrary-writer
isolation, multi-file transactions or recursive vector/raster/directory closure.
Those remain separate package obligations. Follow-up
`export_submission_benchmark_revision2.json` supplies the scoped representative
performance gate: 24 entries / 14 unique files, metadata preparation 0.2141 s,
cold content preparation plus verification 0.2745 s within the 0.4996 s budget,
settled 0.2255 s with zero digest misses. The first comparison omitted existing
catalog/planner/Unitizer work; its failure and correction rationale remain
retained. This does not establish large-source or deployed-service performance.
Canonical archive/restore evidence, normal-identity browser/download acceptance
and final full runtime sanity remain required before package closeout.

Reviewed production SHA-256 values:

```text
dependency_tracker.py b8722d4b4fc224d26370bb749fb1bd2899973d2da09d1fc7f41549ce7deb4c0d
service.py 007e1d51dc1e600a36da9ff8ff5060974a5639411338fb96e6347f4d6599b747
exporters/geodatabase.py f2138126063048a06ad828d562c39e2fa885a1e47b6a795705eabc061c0a9146
readme_builder.py 68939aa79d5310299f96ba506256c3dc818a16ba9f1d25918a56566476b05fad
```
