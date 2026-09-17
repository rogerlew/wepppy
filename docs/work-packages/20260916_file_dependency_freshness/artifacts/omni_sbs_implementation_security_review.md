# S01 Omni SBS implementation security review

**PASS for the scoped implementation: O-I01 and O-I02 verified closed.** Review covers the initial
implementation after checkpoint `c28f81f59`, including receipt/copy helpers,
signature selection, clone/reset callback, direct/RQ admission and private-field
mutation. Reviewer: `freshness_security`. Only disposable probes and artifacts
were written; no production/test edits or named projects were mutated.

## Findings

**O-I01, medium, closed below: the child can change during the last upload observation and
still pass admission.** `SbsExecution.validate_admission` checks child physical
version, SHA and version, then reads any present replacement upload. It does
not recheck the child after that second dependency read. The actual probe
rewrites the child during that upload digest and receives successful admission
with changed child bytes. This violates the accepted whole-operation child
guard; it is a local integrity failure, not a claim of arbitrary writer isolation.

Required remediation: retain complete-set physical guards through the final
source observation and locked admission. Recheck the captured child generation
after observing the replacement source, preserving SHA verification and original
access/error behavior. Do not replace content checking with stat-only identity
or add unrelated child-directory mtime guards; native sibling creation is valid.

**O-I02, medium, closed below: replacing `shutil.copyfile` lost its same-inode protection and
can destroy the uploaded bytes on a rejected copy.** In actual
`OmniModeBuildServices.apply_scenario_mode`, a hardlinked source and expected
destination now reach `target.open('wb')` before identity rejection. Both paths
become empty, then the operation raises ESTALE. The existing `shutil.copyfile`
control raises `SameFileError` before truncation and preserves both paths.

Required remediation: preserve the existing same-file rejection before opening
the destination for truncation, including source/destination aliases referring
to the same inode. Bind the actual opened destination identity sufficiently to
avoid introducing a pathname-check/truncate gap in the replacement copy logic.
Keep the established source/output symlink and mode/write authority; a blanket
alias ban would regress valid inputs. This finding concerns data loss on an
existing safe failure path, not a claim that same-inode copying should succeed.

## Actual evidence

```text
wctl run-pytest docs/work-packages/20260916_file_dependency_freshness/artifacts/omni_sbs_implementation_security_probe.py -v -s
```

`omni_sbs_implementation_security_probe.log`: **2 failed, 6 passed in 12.82 s**.
The adjacent JSON retains the observed results. O-I01 has `error: null` after
an actual child rewrite. O-I02 records empty source bytes after the actual mode
branch fails, alongside the prior copy primitive's preserved byte control.
No native model, queue dispatch or external HTTP request runs in these probes.

Passing controls establish:

- An observed newer same-name upload is preserved and rejects copy acceptance;
  the copied prior bytes remain in the normal child target.
- Actual UID1000 denial of a0444 destination preserves prior destination and
  source bytes. A denied present upload cannot become consumed-source reuse;
  genuine later absence with accepted receipt and matching child still reuses.
- Existing source and destination symlinks remain supported, selected source
  link consumption leaves its physical target intact, and destination0640 mode
  remains unchanged.
- Changed-then-restored child bytes reject through the retained physical guard;
  ordinary sibling native outputs do not invalidate that guard.
- Actual `Omni` persistence and existing Redis lock acquisition on a unique
  disposable project refresh durable state under exactly one admission lock,
  preserving a newer unrelated field/dependency entry and appending the affected
  run state. No mocked lock, durable loader or public setter supplies that result.

## Other reviewed boundaries and remaining gates

Receipt parsing restricts exact version/path/hash shape and derives the child
from the selected scenario, rather than accepting a receipt-selected destination.
Non-SBS signature construction stays unchanged. Clone/reset invalidation is
placed before destructive reset and checks queued selection/source first.
The grouped admission uses private backing fields after in-lock refresh, without
nesting the public setters; the local lock token is outside the replaced state
dictionary. Independent correctness review covers direct/RQ ordering, legacy
association invalidation and stale local state separately.

Close O-I01/O-I02 with retained after-probes before scoped approval. Final actual
copy/admission timing, direct and RQ native work, lock residence, generated
management/soil/WEPP artifacts and browse/archive are separate acceptance gates.
The main-file receipt does not resolve inherited child world/mask/PAM or other
native companion dependencies. Conditional unlink remains explicitly bounded by
the documented absence of an atomic shared upload lock.

## Corrections and retained after-probes

The copy now opens the destination without truncation, compares the actual
opened source/destination device/inode pair, then truncates only a distinct
destination. It raises the previous single-message `SameFileError` shape. The
actual mode branch preserves both hardlinked paths, closing O-I02. An additional
probe retargets a destination symlink to the source at the real `os.open` seam;
the opened-inode check rejects before truncation, preserving source and prior
output. Ordinary distinct source/output aliases remain supported.

Admission now repeats the retained child physical guard after the final source
observation. The original real rewrite inside that observation raises ESTALE,
closing O-I01. Copy also repeats the source physical guard after its last SHA
read and before unlink. An equal-byte newer inode installed inside that read is
preserved and rejected. This covers observable change within final observation;
it does not remove the documented writer-after-final-check limitation.

The helper normalizes standard path-like inputs with `os.fspath`, preserving
the previous basename/copy support and receipt string representation. The
expanded probe exercises capture, pre-reset check, copy, admission and subsequent
consumed-source signature using a real `Path` selection. In-lock refresh now
reinitializes the logger after detached hydration; the actual one-lock probe
continues logging after admission. Independent correctness also identified
legacy association resurrection; current reuse retains the captured accepted
association and requires it to still match under the lock. That review owns
the complete direct/RQ sequencing tests.

Retained runs:

- Initial probe: **2 failed, 6 passed in 12.82 s**; real O-I01/O-I02 evidence.
- Revision2: **9 failed, 1 passed in 13.83 s**; O-I01 passed, but the first
  same-file exception used a Path-valued `errno`, causing the probe's cumulative
  JSON recorder to fail for that and subsequent cases. These are not nine
  distinct product findings. The exception construction was corrected, and the
  next diagnostic recorder stringifies unsupported diagnostic values.
- Revision3: **10 passed in 12.89 s**, including both original failures, late
  same-inode alias selection, path-like compatibility and post-refresh logging.
- `omni_sbs_implementation_security_probe_revision4.py/.json/.log`: **11 passed
  in 12.49 s**, adding the equal-byte newer source during the final observation
  and repeating every prior control against the final helper.

No unresolved medium/high security finding remains in this bounded main-file
implementation. This approval does not substitute for independent direct/RQ
correctness, measured actual performance, native output propagation, normal
browse/archive or whole-package acceptance. No production/tests were edited by
the reviewer. The documented inherited raster dependency limitation remains open.

Reviewed SHA-256 values:

```text
omni_sbs_freshness.py 6f95a6f6f3bc8836259361fb5883697578b1a2392baee5540b87b2f3961e2832
omni.py 22bd86e063d66ec94783037861b9428a30f4f2bdba6d29f1a0c816c08534e614
omni_clone_contrast_service.py f7490428128e0fb34a81e9e7404c71b9e098ec49c70f38097ac840b6dfc419e6
omni_mode_build_services.py 8d6d4590947eed0a731295f0f0ff7f5082af840372f98090f1a2db62ed9f518d
omni_station_catalog_service.py ecd08d23ab564e4065e5e9bcb3bdfca068063ea3db9c15dddb520855926139ae
omni_run_orchestration_service.py e09f1b19fe75d650b04df2d272219729964774817a7c989f44fdb986c316b134
omni_rq.py 0fca1007d49ed39ab0210ea42b90a651f752ca0bb7d828d64583e5da857924c7
```
