# Derived main-file implementation security review

## Findings and disposition

**Final scoped disposition: PASS; DI-I01 resolved, no open scoped findings.**
The initial implementation required changes for DI-I01; that record is retained
below. Review date: 2026-09-17 UTC; original checkpoint ancestor:
`b8c63ab1e20592066365994f4225b73efd21cf5c`; directory compatibility precision:
`dbec83d30`.
Original reviewed `_derived_build.py` SHA-256:
`d057af221dc50cbc8837cb6172a64bb0d68051c25cdc787dd184057ebbf856f2`.
Corrected reviewed source SHA-256:
`423c37c144cac5f8bee3c97930c4f8c65da26f72cb39104007370f3a5cedcc2e`.
No production or test edits were made by this reviewer.

### DI-I01 — Medium: regular-file rejection narrows native raster support

`_derived_build.file_signature` initially rejected every nonregular input with
`EINVAL`. Installed GDAL can create a local directory-backed Zarr raster, and
the actual `identify_median_single_raster_key` returns `{"1": 25.0}` from it.
The old resolved-path/mtime/size signature accepts that directory. The new
signature rejects it before numerical collection. This violates the accepted
checkpoint's preservation of existing raster formats and paths.

`derived_main_security_probe.py` and the original `.log` reproduce the changed
boundary with disposable local files, no network and no numerical mocks. The
revision 2 log also retains the rejection. This is a valid-state regression,
not a hypothetical unsupported format or a security reason to reject Zarr.

Required correction: preserve directory-backed dataset behavior explicitly,
while keeping its member-content verification in the already OPEN raster
closure wave. An explicit directory result with the existing resolved path,
mtime and size plus `digest=None` can restore the checkpoint; it must not be
presented as content verification or reached through a swallowed read failure.
Canonical/checkpoint precision, corrected code and native regression evidence
were required before changing this disposition.

Resolution: `dbec83d30` records that directory-backed native datasets retain
their root path/mtime/size identity with an explicit absent digest. The corrected
helper branches on `S_ISDIR` and returns that identity plus `None`. It does not
catch a read failure or claim directory member verification. Regular-file
checks remain unchanged. The permanent native Zarr test and independent
post-correction probe both pass; directory member verification remains in the
OPEN shared raster closure wave. This restores accepted valid-state behavior.

## Other implementation boundaries reviewed

The regular-file path computes uncached SHA-256 from one opened descriptor.
It compares device, inode, size, nanosecond mtime and ctime before opening,
after opening and after reading, verifies the pathname version, and checks
resolved-path consistency. The returned equality includes only resolved path,
mtime, size and digest: ctime/inode changes outside a read do not themselves
become new transaction conflicts.

Each logical read requests at most the remaining captured size plus one byte;
growth beyond that size fails before hashing the extra byte. The byte count
must equal the captured size at completion. Observable growth, truncation,
replacement and version drift therefore raise explicit errors rather than
cache or publish a digest. This is bounded logical consumption, not a promise
about filesystem readahead, kernel I/O time or arbitrary writer isolation.

Filesystem exceptions propagate unchanged; there is no generic retry, fallback
stat identity, persistent hash store or cached transaction result. Existing
symlinks remain allowed. Only helper imports/function and caller docstrings
change in this slice; `_identity`, rollback ownership, publication, lock/token
handling, uncertain-commit recovery and numerical readers remain unchanged.

## Evidence inspected and independently exercised

Initial author logs inspected (retained historical evidence):

- `derived_main_signature_tests.log`: **5 passed**, 2 warnings, 9.17 seconds.
  Real byte changes preserve size/mtime; hard-link, chmod and identical
  replacement preserve equality; touch retains the old transaction conflict.
  Empty and missing inputs, and real growth/replacement/mtime drift are covered.
  The original directory-rejection assertion encoded DI-I01; it is corrected
  in the follow-up evidence below.
- `derived_main_focused.log`: **38 passed**, 8 warnings, 17.43 seconds.
  Both restored-time PRISM/RAP finalizers reject before publication and preserve
  NoDb bytes. The suite also covers existing publication/rollback failures,
  unrelated changes, legacy state, actual native rasters, generated parquet
  and downstream `wepp/runs/p1.cov` values. The initial restored-time cases started
  without prior output; they do not alone demonstrate preservation of an
  already published output generation; the follow-up now covers prior bytes.

Independent command:

```text
wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/derived_main_security_probe.py
```

`derived_main_security_probe_revision2.log` exits 0 and confirms unchanged
symlink equality, exact injected `PermissionError` object propagation,
real truncation during reading rejected with ESTALE, and actual replacement
between the initial stat and descriptor open rejected with ESTALE. It also
confirms valid native Zarr reading and the initial signature regression.

Follow-up author log `derived_main_review_tests_revision2.log` records
**46 passed**, 8 warnings, 17.34 seconds. The revised signature suite adds
truncation, exact read-error propagation and real native Zarr compatibility.
The actual-finalizer tests preserve preexisting PRISM output bytes and a RAP
parquet produced by a successful preceding analysis, plus the original NoDb
bytes, after a restored-time main-file rewrite. This closes the narrower
publication-evidence gap above without changing publication code.

The independent command was rerun after correction. Retained
`derived_main_security_probe_after_directory_fix.log` exits 0, records
`directory_metadata_compatibility_preserved=true`, and again returns the native
Zarr summary `{"1": 25.0}`. Symlink equality, permission-error identity,
truncation and pre-open replacement guards also pass. The original rejection
logs remain available rather than being overwritten.

The inspected `derived_inputs_benchmark.json` hashes 39 real RAP main rasters
(1986–2024; 564,058 total bytes) on the run mount in **0.536 seconds** first
pass and **0.035 seconds** second pass. Both are below the 10-second hash-work
budget for this measured set. The artifact correctly says no lock was acquired
and native processing was excluded; it does not establish full operational
input cost, held-lock occupancy or larger-raster parity.

## Remaining package gates

The prior DI-S01 indirect-dependency finding remains OPEN for nested VRT,
auxiliary, virtual and now explicit directory-backed inputs. Complete-set
RAP hash/lock timing, full sanity, restarted native workflows and archive
acceptance remain unverified here. Even a corrected scoped implementation
pass cannot close C01 in full or the repository package.
