# Derived main-file implementation correctness review

Independent reviewer: `freshness_correctness`, 2026-09-17 UTC. Reviewed the
bounded implementation after standalone checkpoint `b8c63ab1e`, both callers,
`test_derived_file_signature.py`, the contention-suite diff and retained focused
logs. No production implementation or tests were edited by this reviewer.

**Current verdict: PASS for the corrected bounded implementation.** All three
scoped findings below are resolved and independently reviewed. The initial
regular-file-only assumption and native counterexample remain documented.
This does not close C01 indirect dependencies or package performance/runtime
acceptance gates.

## Findings

| ID | Severity | Finding and smallest follow-up |
| --- | --- | --- |
| DERIVED-IMPL-01 | Low, resolved | The initial restored-time finalizer tests started without prior outputs. Both now assert exact prior output bytes and NoDb bytes survive the byte conflict. RAP first performs a valid build to produce its prior parquet, preserving real fresh hydration. |
| DERIVED-IMPL-02 | Low, resolved | Drift coverage now includes real truncation and a read-error hook. The tests verify ESTALE on truncation and preservation of the original PermissionError object, with no fallback signature. |
| DERIVED-IMPL-03 | Medium, resolved | The native security probe proved a local directory-backed Zarr was previously valid but rejected by the new regular-file-only guard. Explicit directory handling now returns the original metadata identity plus absent digest. The real native Zarr regression verifies the exact tuple and numerical summary `{"1": 25.0}`. |

## Directory conformance correction

`derived_main_security_probe.py`, its original log and revision 2 retain the
real compatibility failure. The implemented correction is **PASS as a bounded
conformance repair** after canonical clarification commit `dbec83d30`.
`S_ISDIR` returns the original resolved root path, mtime and size plus an
explicit absent digest (`None`). The branch is restricted to an actual directory;
failed regular-file hashes and read errors cannot become absent-digest success.
The return annotation reflects the optional digest and the main path remains
in element zero.

This restores the already permitted input state, not a claim of directory
content freshness. Native consumers retain their validation of whether the
directory represents a valid raster. Root metadata can remain unchanged when
member bytes change; directory-member verification joins the explicit OPEN
recursive/auxiliary/VSI dependency-closure blocker. A directory-to-regular-file
change has a different digest state and cannot compare equal accidentally.

The canonical NoDb contract now records that explicit compatibility state.
It is consistent with the checkpoint's existing no-format-restriction rule;
no new general fallback policy or numerical reader is needed. The initial EINVAL
evidence remains retained, and `test_native_directory_backed_raster_remains_readable`
verifies actual GDAL-created Zarr input through the installed native summarizer.

Both low-gap follow-ups have been inspected: truncation/read-error cases now
exercise the real descriptor, and both finalizers preserve a prior output.
The intermediate `derived_main_review_tests.log` remains **44 passed, 1 failed**:
its RAP fixture seeded arbitrary text where fresh hydration expects valid
parquet. The corrected fixture generates valid prior parquet through `rap.analyze`
and retains exact bytes. Follow-up `derived_main_review_tests_revision2.log`
records **46 passed** without bypassing real hydration or weakening assertions.

## Implementation assessment

`wepppy/nodb/_derived_build.py:file_signature` preserves resolved pathname,
mtime and size as the first three tuple members and appends SHA-256. Both
numerical callers continue consuming element zero and comparing their complete
input snapshots. The only caller changes are explanatory docstrings. Required
legacy state has no persisted signature migration.

For regular files the helper reads one binary descriptor without a digest cache. It compares
device, inode, size, mtime and ctime at admission and after reading, checks the
pathname generation and resolved destination again, and rejects short or
overlong observations. Each read is limited by remaining captured size plus
one; total consumption cannot grow indefinitely with an appending writer.
Read errors remain explicit. Empty regular files have their standard empty
digest; missing and special-file inputs fail, while directories retain the
explicit compatibility state above. Numerical format validation is
unchanged and no GDAL dependency discovery or virtual-path restriction was added.

Descriptor ctime/inode checks do not enter returned transaction equality.
Real-file tests verify hard-link creation, readable chmod and same-byte atomic
replacement with restored mtime preserve equality between separate observations;
changed bytes with restored size/mtime change the digest. Mtime-only changes
still produce the existing conservative transaction conflict. Permitted symlink
resolution remains implemented through ordinary resolved-path/open behavior.

`_identity`, lock/hydration, allowlisted derived-state updates, publication,
rollback ownership and uncertain-commit recovery are unchanged. Hash comparison
occurs before `publish_files` enters, so detected main-file changes cannot
publish the staged generation. The two finalizer regressions exercise that real
comparison/publication boundary using filesystem writes and restored mtimes;
numerical work is deliberately injected and is not native workflow evidence.

## Evidence and remaining gates

`derived_main_signature_tests.log` records **5 passed** and
`derived_main_focused.log` records **38 passed**, including both actual
restored-time finalizers and existing contention, unrelated-field preservation,
failure/rollback and ownership cases. The corrected combined regression run
records **46 passed**, including all three resolved findings. These are reviewed
retained runs, not an additional independent rerun.

`derived_inputs_benchmark.json` records read-only signature passes over 39 actual
RAP annual files totaling 564,058 bytes: **0.536 seconds first pass and 0.035
seconds second pass**. The script imports before timing, rereads bytes on each
pass and takes no lock. The retained path list contains RAP rasters only, with
no watershed/MOFE inputs, and is a small cropped dataset. This supports bounded
cost for that sample; it does not establish complete operational input-set or
held-lock acceptance. Apply the checkpoint's full-set shipping budget before
claiming the finalization lock remains operationally acceptable. Native restarted
workflow, archive/restore, full applicable sanity and final security acceptance
remain open. Main-path hashing does not resolve recursive VRT, auxiliary-file
or VSI backing dependencies; the retained native 3-to-7 closure counterexample
continues to block full C01/package closure.
