# Resumed vector upload correctness review

- Reviewed source: `54ee356fd16845e7abf6da59d7df616f8b5fa6ce`.
- Reviewer: dedicated `reviewer` agent `provenance_review`.
- Verdict for this source: **HOLD: one High concurrency finding and one Medium free-space admission finding.** Proposed fixes require successor review.
- Converter image remains `sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`.

This independent review covers the shared retention lifecycle, profile
integration including separate storage roots and flattened archive exports,
Batch copy/reset, and Omni cleanup/reset. It excludes the fork/route production
changes, fork regression module, and session-provenance regression module this
reviewer authored. Their independent reviewers are frozen QA, security and
operations. No production source was changed during this review.

## Findings

### VUN-CORRECTNESS-RESUME-03: High - parent cleanup can erase an active child upload

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

### VUN-CORRECTNESS-RESUME-04: Medium - copy free-space admission omits outstanding reservations

`wepppy/microservices/vector_retention_lifecycle.py:218` reads reserved bytes and
includes them in quota ceilings. Its free-space comparison at line 229 includes
only the incoming copy allowance and protected filesystem reserve. Another
already-admitted upload may consume its outstanding reservation afterward.

A read-only reproduction against the frozen helper supplied 200 bytes of
outstanding reservations, a 200-byte incoming allowance, and free space equal to
the protected reserve plus 300 bytes. `_admit_copy()` accepted, although the two
admitted writes can reduce free space to 100 bytes below the protected reserve.
The units scale to the actual upload limit; no filesystem pressure was created.

Required closure: include outstanding reserved bytes in the free-space check and
retain a regression with sufficient space for the copy alone but insufficient
space for the copy plus existing reservations.

## Disposition of earlier findings

- `VUN-CORRECTNESS-RESUME-01` is **closed by operator policy**, recorded in `docs/schemas/vector-upload-normalization-contract.md`, section **Sharing, copies, and existing workspace resets**, and standalone checkpoint `bbb216c0bc48674f8b24f5e69f20ec58e57b795a`. Public/team copies retain original/private evidence under existing destination ownership. The proposed source-only restriction was explicitly rejected.
- The original unaccounted-copy/reset finding `VUN-CORRECTNESS-RESUME-02` has implementation coverage across the reviewed Batch, Omni and profile consumers. Closure depends on resolving the two concrete successor findings above and independent review of the excluded fork paths.

## Other reviewed behavior

- Copies preserve original actor, source identity, attempt identity and bytes. Additive `retention_actor` charges the copier; a bounded raw receipt/hash records inheritance. Automated callers use the unattributed bucket. Subsequent copying does not create a growing nested history.
- Global maintenance precedes newly acquired project scopes; borrowed scopes remain owned by their workflow. Failure retains a deterministic repair obligation, and rebuild preserves unrelated active reservations.
- Batch retry recognizes interrupted copies even when ordinary reset is disabled. It requires partial-destination removal before copying again. Deferred stale workspaces remain part of physical accounting.
- Omni normal cleanup preserves its owning retained-attempt roots. Single-child retry recognizes an absent child with a pending obligation. Deferred stale evidence remains counted without speculative deletion credit.
- Profile promotion remains a byte-preserving explicit offline export. Existing server-resolved execution destinations outside a fully configured ledger root remain on their established storage. Managed reentry/descendants are charged; missing configuration rejects evidence-bearing execution copies.
- Flattened profile archive destinations retain receipt-parent discovery. Replacing an existing `private/bundle` export with an empty result releases its charge. Config-seed playback retains its existing selected-file behavior.

## Independent validation and limits

The independent snapshot is a `git archive` of the reviewed SHA at
`/tmp/vun-correctness-54` inside the existing development `weppcloud` container.
The shared checkout and service mounts were unchanged. Canonical
`wctl run-pytest` rejects the task checkout's mount mismatch, so execution used
`wctl --project-dir /home/workdir/wepppy exec -T`, working directory and
`PYTHONPATH=/tmp/vun-correctness-54`, and `/opt/venv/bin/python -m pytest` with:

- `tests/microservices/test_vector_retention_lifecycle.py`
- `tests/nodb/test_vector_retention_copy_consumers.py`
- `tests/profile_recorder/test_retained_profile_lifecycle.py`
- `-q --maxfail=1 --basetemp=/tmp/vun-correctness54-testdata`

Result: **44 passed**, zero failures/skips, four dependency/deprecation warnings,
45.54 seconds. Those cases do not cover the newly reproduced conditions. The
child-scope probe was a separate deliberately failing test stored only in the
isolated snapshot.

Batch tests stop before subsequent controller/model preparation. Profile
HTTP/archive-job orchestration is stubbed in this lifecycle suite. The tests do
exercise actual copy/reset/Redis readback, but do not establish a full production
workflow. No full-suite result or remote-host parity is claimed here.
Publication and production deployment remain separate gates.
