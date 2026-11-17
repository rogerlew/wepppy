# Resumed vector upload correctness review

- Reviewed source: `f964831084159eb4cf68cb533dc48235cb580989`.
- Independently executed predecessor: `224184ecd778dd58844036084f272897b79f7cd7`.
- Reviewer: dedicated `reviewer` agent `provenance_review`.
- Verdict for this source: **PASS within the independent scope below; no open High or Medium findings.** Archive creation, destructive child-scope protection and copy free-space admission findings are closed. The private ZIP write bound, cleanup accounting and source-copy reconciliation gate preserve those closures.
- Converter image remains `sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`.

This independent review covers the shared retention lifecycle, profile
integration including separate storage roots and flattened archive exports,
Batch copy/reset, and Omni cleanup/reset. It excludes the fork/route production
changes, fork regression module, and session-provenance regression module this
reviewer authored. Their independent reviewers are frozen QA, security and
operations. No production source was changed during this review.

## Closed findings

### VUN-CORRECTNESS-RESUME-05: Closed High - late child upload versus public archive

The following reproduction and line references describe `224184ecd` and the
unchanged archive module in `cfd5329d`.

`wepppy/rq/project_rq_archive.py:402` takes only the parent run's retention
scope before classifying sensitivity at line 408. Its later ZIP walk writes
newly observed files at line 495 without checking whether they invalidate that
classification. A supported composite child upload takes a different scope and
can therefore create retained originals after the parent was classified public.

An independent reproduction against `224184ecd` called the real archive worker
and real `prepare_vector_upload()` with real Redis leases/reservations. A
deterministic test boundary admitted the child upload immediately after the
real sensitivity check returned false. Archive creation succeeded, and ZIP
readback found the exact complete original at
`_pups/omni/contrasts/1/ag_fields/vector_upload_attempts/<uuid>/original/late.geojson.upload`
inside ordinary `archives/<parent>.<timestamp>.zip`. The private namespace and
private archive charge were bypassed. The source uses valid real directories;
rejecting ordinary model symlinks does not establish safety for this case.

The deliberately failing reproduction is retained only in the development
container at `/tmp/vun-correctness-224/tests/rq/test_review_archive_child_race.py`.
It failed the exact-original ZIP assertion in 13.42 seconds. No user files were
used. The archive module is byte-identical in `224184ecd` and `cfd5329d` (SHA-256
`662f84d2726b971ad37ce39da8f51d8e722f3a86c232511b62101bfb307aeccd`).

The earlier sensitivity walker also pruned every directory named `archives`, while the
writer excludes only the project's top-level `archives` tree. Nested child
`archives/private` bundles therefore require consistent sensitive classification.

Closure required preventing late sensitive contents from entering a public ZIP,
including its ordinary temporary path, and retain the source original on race
failure. A bounded member check before writing plus safe failure is sufficient;
silently omitting retained evidence would violate the copy/archive contract.
The required regression introduces a real child upload after classification
and checks both final and temporary archive outputs.

Closed on `13feaac9276bd95f2341102d2683aca5a43cd3a5`:
`_assert_archive_member_visibility()` runs before both directory and file ZIP
writes. A late sensitive member fails the archive without filtering it into an
incomplete success. Independent execution verifies that no sensitive member is
written, temporary/final public ZIPs are absent, original/receipt bytes and the
child's live lease remain intact, and a retry produces a private archive with
the exact source bytes and sensitive sidecar. The nested-private-only case also
produces a private archive, with top-level archive exclusion preserved.

The `111dd982cadb499333bc6b5eba2c07f9d4923d7c` delta also closes the
security review's separate late-growth accounting finding. The private ZIP
stream rejects a write before its ending offset exceeds the already admitted
ZIP allowance. Header rewrites remain valid without counting the same bytes
twice; member data, central-directory records and comments use the same bounded
writer. The ZIP closes before its underlying buffered stream. The additional
receipt allowance and quota defaults are unchanged. Public archives retain the
member-visibility check above.

The `467e9db1b752ebd8448b569b58eede661f6e64a5` delta closes the
operations review's cleanup-accounting finding. Failure releases its reservation
only after temporary-file removal and a successful containing-directory fsync.
Failed unlink or fsync retains the reservation and writes an incomplete receipt
with the original archive actor, project identity and reservation ID. Existing
reconciliation then commits the exact surviving bytes under that actor. Receipt
persistence failure is logged and leaves the reservation intact. Independent
tests cover each failure, source preservation, receipt size and later exact
principal/total accounting. This adds no recovery store or queue behavior.

### VUN-CORRECTNESS-RESUME-03: Closed High - active child upload versus parent cleanup

The following reproduction and line references describe the earlier
`54ee356fd16845e7abf6da59d7df616f8b5fa6ce` source.

`wepppy/microservices/vector_retention_lifecycle.py:330` acquires only the
caller-supplied project scopes. Omni bulk cleanup supplies the parent scope at
`wepppy/nodb/mods/omni/omni_state_contrast_mixin.py:556`, then recursively deletes
child directories at line 566. A child upload uses a distinct scope: AgFields
passes the complete requested run ID at
`wepppy/microservices/rq_engine/ag_fields_routes.py:682`. Authorization recognizes
the parent owner for these child IDs in
`wepppy/microservices/rq_engine/auth.py:188`.

An independent reproduction on the frozen source used real Redis, the real
`prepare_vector_upload()` receiver, and real
`OmniStateContrastMixin._clean_stale_contrast_runs()`. The upload retained a
complete GeoJSON original under a contrast child's AgFields attempt directory
and continued to own `run:<parent>;;omni-contrast;;1`. Parent cleanup completed
under `run:<parent>` and erased the original. The regression assertion failed:
`parent cleanup erased complete original under active child upload lease`.
No user project or external artifact was involved.

Committed-only rebuild preserves outstanding reservations, but that does not
protect their files. Required closure is bounded discovery/acquisition of
relevant descendant reservation scopes under the global maintenance fence,
before filesystem mutation. Cover both physical attempt-path ancestry and a
descendant reservation created before its attempt path has been bound. Preserve
the existing borrowed-parent scope case. Assess the same parent/child assumption
in separate project/archive deletion and restore consumers.

The isolated reproduction is retained in the development container at
`/tmp/vun-correctness-54/tests/nodb/test_review_child_scope.py`. Its final run
failed the data-preservation assertion in 9.60 seconds.

Closed on `224184ecd`: bounded `discover_retention_scopes()` runs under global
maintenance, adds bound descendant-path scopes and hierarchical scopes for
reservations whose attempt path is not yet bound, then acquires them before the
body mutates files. Whole-run deletion, Batch deletion and whole-run restore
use the same discovery. Regressions cover completed retained source bytes,
pre-bind reservations, unchanged originals/totals on denial, and successful
retry after the active upload settles. Existing borrowed-parent behavior passes.

### VUN-CORRECTNESS-RESUME-04: Closed Medium - outstanding reservations in free-space admission

The following reproduction and line references describe `54ee356fd`.

`wepppy/microservices/vector_retention_lifecycle.py:218` reads reserved bytes and
includes them in quota ceilings. Its free-space comparison at line 229 includes
only the incoming copy allowance and protected filesystem reserve. Another
admitted upload may later consume its outstanding reservation.

A read-only reproduction against the frozen helper supplied 200 bytes of
outstanding reservations, a 200-byte incoming allowance, and free space equal to
the protected reserve plus 300 bytes. `_admit_copy()` accepted, although the two
admitted writes can reduce free space to 100 bytes below the protected reserve.
The units scale to the actual upload limit; no filesystem pressure was created.

Required closure: include outstanding reserved bytes in the free-space check and
retain a regression with sufficient space for the copy alone but insufficient
space for the copy plus existing reservations.

Closed on `224184ecd`: `_admit_copy()` includes `total_reserved` in its
free-space comparison. The regression supplies capacity for the copy alone but
not the outstanding reservations and verifies rejection before destination
creation.

## Disposition of earlier findings

- `VUN-CORRECTNESS-RESUME-01` is **closed by operator policy**, recorded in `docs/schemas/vector-upload-normalization-contract.md`, section **Sharing, copies, and existing workspace resets**, and standalone checkpoint `bbb216c0bc48674f8b24f5e69f20ec58e57b795a`. Public/team copies retain original/private evidence under existing destination ownership. The proposed source-only restriction was explicitly rejected.
- The original unaccounted-copy/reset finding `VUN-CORRECTNESS-RESUME-02` is closed within the reviewed Batch, Omni and profile consumer scope. The related successor findings are closed above; excluded fork paths require their independent reviews.

## Other reviewed behavior

- Copies preserve original actor, source identity, attempt identity and bytes. Additive `retention_actor` charges the copier; a bounded raw receipt/hash records inheritance. Automated callers use the unattributed bucket. Subsequent copying does not create a growing nested history.
- Final source `f964831084159eb4cf68cb533dc48235cb580989` rejects an explicit noncommitted source receipt or a matching noncommitted Redis reservation before destination mutation or repair-marker creation. The gate runs under maintenance and project scopes; its bounded receipt inventory and reservation-key lookups introduce no new store. Legacy receipts without accounting fields and reconciled terminal incomplete evidence remain copyable. Partial-destination cleanup/retry remains available because admission inventories the source.
- Global maintenance precedes newly acquired project scopes; borrowed scopes remain owned by their workflow. Failure retains a deterministic repair obligation, and rebuild preserves unrelated active reservations.
- Batch retry recognizes interrupted copies even when ordinary reset is disabled. It requires partial-destination removal before copying again. Deferred stale workspaces remain part of physical accounting.
- Omni normal cleanup preserves its owning retained-attempt roots. Single-child retry recognizes an absent child with a pending obligation. Deferred stale evidence remains counted without speculative deletion credit.
- Profile promotion remains a byte-preserving explicit offline export. Existing server-resolved execution destinations outside a fully configured ledger root remain on their established storage. Managed reentry/descendants are charged; missing configuration rejects evidence-bearing execution copies.
- Flattened profile archive destinations retain receipt-parent discovery. Replacing an existing `private/bundle` export with an empty result releases its charge. Config-seed playback retains its existing selected-file behavior.

## Independent validation and limits

Final exact-source execution used a separate `git archive` of
`f964831084159eb4cf68cb533dc48235cb580989` at `/tmp/vun-correctness-f964`, with
that directory as both working directory and `PYTHONPATH`, through the existing
`wctl exec` container fallback. Command target arguments were:

- `tests/microservices/test_vector_retention_lifecycle.py::test_copy_requires_source_reservation_reconciliation`
- `tests/microservices/test_vector_retention_lifecycle.py::test_copy_keeps_source_provenance_and_charges_copying_actor`
- `tests/microservices/test_vector_retention_lifecycle.py::test_partial_copy_retry_and_ordinary_model_symlink`
- `-q --maxfail=1 --basetemp=/tmp/vun-correctnessf964-testdata`

Result: **6 passed**, zero failures/skips, four dependency/deprecation warnings,
23.54 seconds; retained log `/tmp/vun-f964-review.log`. The tests reject both
pending receipts and receipts claiming committed accounting while their real
Redis reservation remains noncommitted. They verify no destination or repair
marker is created, then perform real reconciliation and verify exact source
and copying-actor charges after retry. Accepted, rejected and incomplete legacy
receipts still copy with immutable provenance, and interrupted-copy recovery
still succeeds. The helper is the sole production delta from the preceding
reviewed source; its SHA-256 matches the integration checkout:
`083acbf6a8c16eeaf98dea7c8dd9dc9c4a34c405f942308fe3b8c42503c93903`.
Earlier results below retain their original source qualification.

Earlier exact-source execution used a separate `git archive` of
`467e9db1b752ebd8448b569b58eede661f6e64a5` at `/tmp/vun-correctness-467`, with
that directory as both working directory and `PYTHONPATH`, through the existing
`wctl exec` container fallback. Command target arguments were:

- `tests/rq/test_vector_archive_recovery.py::test_private_archive_rejects_late_growth_within_existing_reservation`
- `-q --maxfail=1 --basetemp=/tmp/vun-correctness467-testdata`

Result: **4 passed**, zero failures/skips, 12 dependency/deprecation warnings,
17.10 seconds; retained log `/tmp/vun-467-review.log`. The parametrized cases
exercise successful cleanup, failed unlink, failed directory fsync, and failed
incomplete-receipt persistence. They verify the original sources are unchanged,
the reservation covers surviving bytes, failed cleanup remains charged, and
subsequent reconciliation preserves exact actor attribution when the receipt
was persisted. Receipt-write failure retains the reservation for existing
corrupt-receipt recovery; that later recovery is not exercised in this focused
case. The archive source SHA-256 remains unchanged in the final source:
`48d8f26bb2fd786f91eefa2454aa688e5a83494deb552ba6473d1c2074773be3`.
Cleanup handling is the sole production delta from the preceding reviewed
source. Earlier results below retain their original source qualification.

Earlier exact-source execution used a separate `git archive` of
`111dd982cadb499333bc6b5eba2c07f9d4923d7c` at `/tmp/vun-correctness-111`, with
that directory as both working directory and `PYTHONPATH`, through the existing
`wctl exec` container fallback. Command target arguments were:

- `tests/rq/test_project_rq_archive.py::test_private_zip_cap_allows_header_rewrites_at_exact_final_size`
- `tests/rq/test_project_rq_archive.py::test_private_zip_cap_rejects_central_directory_before_growth`
- `tests/rq/test_project_rq_archive.py::test_private_zip_cap_limits_file_extent_after_seeks`
- `tests/rq/test_vector_archive_recovery.py::test_private_archive_rejects_late_growth_within_existing_reservation`
- `-q --maxfail=1 --basetemp=/tmp/vun-correctness111-testdata`

Result: **4 passed**, zero failures/skips, six dependency/deprecation warnings,
12.83 seconds; retained log `/tmp/vun-111-review.log`. Tests cover exact final
ZIP readback, permitted backward header rewrites, rejection before seek writes
or central-directory growth exceed the cap, and real late child growth against
the existing Redis reservation. The latter verifies every observed file extent
stays within the ZIP allowance, originals remain unchanged, temporary/final
archives are absent, and reserved/inflight counters return to zero. That
archive source SHA-256 is
`13ba221c2b558d7640e4dbfd3f775008838b4272e716f0f4ee8b80b28f8bb06b`.
The bounded writer was the sole production delta from the preceding reviewed
source.

Earlier exact-source execution used a separate `git archive` of `13feaac927` at
`/tmp/vun-correctness-13f`, with that directory as both working directory and
`PYTHONPATH`, through the existing `wctl exec` container fallback. Command target
arguments were:

- `tests/rq/test_vector_archive_recovery.py::test_public_archive_aborts_before_writing_late_child_upload`
- `tests/rq/test_vector_archive_recovery.py::test_parent_archive_classifies_nested_private_archive_without_attempt_roots`
- `tests/microservices/test_vector_retention_lifecycle.py::test_copy_syncs_evidence_ancestors_before_clearing_marker`
- `-q --maxfail=1 --basetemp=/tmp/vun-correctness13f-testdata`

Result: **4 passed**, zero failures/skips, eight dependency/deprecation warnings,
15.55 seconds. The ancestor-sync test covers both absolute and relative target
paths and verifies newly created parent directories through the configured
filesystem root. That archive source SHA-256 is
`79e16cf30a038c0b66e749d633b889b1c6be591004d852e9a9958eac4d85e11e`;
the frozen integration checkout and independently selected source match.

On exact `224184ecd`, independent execution in `/tmp/vun-correctness-224` ran
the three modules below plus `tests/rq/test_vector_retention_deletion.py` and
`tests/rq/test_vector_archive_recovery.py`, using
`--basetemp=/tmp/vun-correctness224-testdata`. Result: **109 passed**, zero
failures/skips, 20 dependency/deprecation warnings, 233.16 seconds. The separate
archive-creation probe then demonstrated RESUME-05. The `cfd5329d` delta extends
ancestor fsync through the configured root, including newly created destination
parents; source and regression review found that bounded durability change
sound. Final relative-path normalization is covered by the four tests above.
The broader 109-test run is not represented as a fresh final-source run.

The earlier independent snapshot is a `git archive` of exact `54ee356fd` at
`/tmp/vun-correctness-54` inside the existing development `weppcloud` container.
The shared checkout and service mounts were unchanged. Canonical
`wctl run-pytest` rejects the task checkout's mount mismatch, so execution used
`wctl --project-dir /home/workdir/wepppy exec -T`, working directory and
`PYTHONPATH=/tmp/vun-correctness-54`, and `/opt/venv/bin/python -m pytest` with:

- `tests/microservices/test_vector_retention_lifecycle.py`
- `tests/nodb/test_vector_retention_copy_consumers.py`
- `tests/profile_recorder/test_retained_profile_lifecycle.py`
- `-q --maxfail=1 --basetemp=/tmp/vun-correctness54-testdata`

Historical `54ee356fd` result: **44 passed**, zero failures/skips, four dependency/deprecation warnings,
45.54 seconds. Those cases do not cover the newly reproduced conditions. The
child-scope probe was a separate deliberately failing test stored only in the
isolated snapshot.

Batch tests stop before subsequent controller/model preparation. Profile
HTTP/archive-job orchestration is stubbed in this lifecycle suite. The tests do
exercise actual copy/reset/Redis readback, but do not establish a full production
workflow. No full-suite result or remote-host parity is claimed here.
Publication and production deployment remain separate gates.
