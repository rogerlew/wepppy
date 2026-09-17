# Derived input byte verification security checkpoint

## Findings and disposition

**PASS for the revised main-path-only checkpoint.** The original GDAL proposal
does not pass and must not be implemented. DI-S01 remains an explicit package
closure blocker in the later raster dependency wave; there is no risk acceptance
for it. DI-S02 is resolved by withdrawing the proposed restriction. No new
scoped blocker remains for adding uncached hashes of the existing main files.

Reviewed 2026-09-17 UTC at ancestor candidate
`984023c180f7fda01dfd0abfd9f879d01ca7dfd3`, against the revised
`derived_input_contract_decision.md` and
`docs/schemas/nodb-persistence-concurrency-contract.md`, **Derived input byte
verification**. No production code or tests were changed by this reviewer.

### DI-S01 — Medium: one-level GDAL list misses valid numerical inputs

The original proposal promised native dependency closure by snapshotting a
dataset's reported file list. Actual GDAL and native summarization show that
an explicit `outer.vrt -> inner.vrt -> source.tif` chain returns only outer and
inner from the outer dataset's `GetFileList`. The native summary is initially
`{"1": 25.0}`. Rewriting the source GeoTIFF to 75 while preserving its size and
mtime leaves every listed member's hash unchanged, yet the native summary
becomes `{"1": 75.0}`. Such a change during collection could therefore pass
the proposed finalizer while its numerical dependency had changed.

Evidence: `derived_gdal_security_probe.py` and
`derived_gdal_security_probe_revision3.log`. This is a disposable local fixture
using installed GDAL and `identify_median_single_raster_key`; no network,
mocked metadata or modified numerical implementation is involved.

Required remediation before package closure: a separately reviewed transitive
dependency design with native acceptance for nested VRT/auxiliary/virtual
sources. The revised checkpoint explicitly limits this implementation to the
existing main files and leaves C01 indirect closure OPEN alongside the other
raster consumers. That honest split permits the confirmed main-file fix, but
does not resolve this finding or supersede the general finalization contract.

### DI-S02 — Medium: blanket virtual-member rejection changes valid behavior

A real local VRT referencing a GeoTIFF inside a local ZIP returns a valid native
summary `{"1": 25.0}`. Its GDAL member name is
`/vsizip/<temporary>/source.zip/source.tif`; that namespace does not establish
that the backing bytes are remote. Rejecting all such members as “nonlocal”
would deny an existing readable local input. Main-file RAP containment does
not itself restrict the source format of the contained file.

Evidence: the same retained probe and logs, `local_zip_vrt` case. The ordinary
acquisition path in `landcover/rap/rangeland_analysis_platform.py:retrieve`
writes local GeoTIFFs, but that happy path alone cannot establish that all
existing readable VRT representations are invalid or authorize their rejection.

Disposition: resolved in the revised checkpoint by removing all new GDAL reads,
format restrictions, member traversal and nonlocal rejection from this wave.
Any subsequent closure design must preserve compatible local virtual inputs
or explicitly resolve the behavior change through the owner contract.

## Baseline and retained intermediate evidence

`derived_build_baseline_probe.py/.log` exercise the real PRISM and RAP
finalizers with real equal-size/restored-mtime source writes. Both cases publish
outputs despite changed bytes (**2 characterization tests passed**). Numerical
collection is injected, as the record states; this is publication-boundary
evidence, not a complete native scientific acceptance test.

Independent reviewer command:

```text
wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/derived_gdal_security_probe.py
```

All three retained runs exit 0. The first log remains intermediate evidence:
`gdal.Translate(VRT, VRT)` flattened the intended nested fixture, so it did not
test transitive nesting. Revision 2 explicitly constructed the nested VRT and
revealed the omitted source. Revision 3 added the actual preserved-metadata
rewrite and unchanged-list-hash comparison. Only revision 3 supports the full
DI-S01 claim; the initial flattened case is not represented as passing closure.

## Revised boundary, compatibility and noninterference

`_derived_build.file_signature` currently serves only the PRISM CLI source and
RAP time-series main raster, subwta and optional MOFE paths. Adding an uncached
digest to its transaction-local result keeps the resolved path first, so the
existing numerical callers still receive the captured source path. Retain
size/mtime in transaction equality; do not add inode/ctime to returned equality
merely because they are useful within one read's race checks. Same-byte metadata
churn between observations follows the explicit existing mtime guard, while
alias changes alone must not become a new conflict predicate.

The proposed descriptor/path checks and captured-size-plus-one bound address
observable read drift and unbounded growth. Read errors must propagate rather
than yield an empty digest or a fallback stat signature. Existing collection
failures happen before publication. Existing finalizer wrappers translate
`ValueError`, `TypeError` and `FileNotFoundError` into superseded errors;
permission and other filesystem errors must retain their explicit failure.
No broad retry, cache or historical-digest migration is authorized.

Symlink resolution, RAP main-path containment, allowed settings, years/bands,
watershed selection and numerical validation remain unchanged. Empty plain
files are hashable; their consumer owns semantic validation. No new raster
reader is needed for this first slice. Legacy persisted NoDb state has no input
signature migration because these signatures are transaction-local.

`finalize` must still lock, freshly hydrate, verify relevant inputs, publish
and dump once. `_identity`, rollback ownership, output path checks, lock-token
checks and uncertain-commit recovery are outside this equality change and must
remain intact. The checkpoint promises no isolation from an arbitrary complete
change-and-restore during native processing; before/after checks rely on the
existing cooperative publication assumptions.

## Outstanding implementation and runtime gates

Require actual restored-time PRISM/RAP rejection with old outputs preserved,
unchanged-input success, read-error/drift/growth cases and rollback regression
coverage. Observe full representative RAP finalizer hash time under its real
lock; the single-file benchmark does not establish lock occupancy. The revised
checkpoint's 10-second full-set hash budget is a shipping gate, not evidence
already collected or permission to add silent timeouts.

Final full sanity, rebuilt/restarted native workflows, archive acceptance and
the explicitly open indirect dependency wave remain required. This checkpoint
approves only the specified implementation slice and cannot close C01 in full.
