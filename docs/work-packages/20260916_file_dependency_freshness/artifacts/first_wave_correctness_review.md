# First-wave implementation correctness review

## Metadata and verdict

Independent reviewer: `freshness_correctness`, 2026-09-17 UTC. Compared the
working-tree first-wave implementation with checkpoint
`43317704fd046faffac39e114634bb155213c547`; verified the checkpoint is HEAD and
therefore an ancestor of the forthcoming implementation. No implementation files
were edited by this reviewer. Reviewed production.py SHA-256
`8be3d1de598131075a63c13ca8f270702ee1ef16430b7b94b0e943b9a1e680b1` and route SHA-256
`1de0d33f2f9519d3174673b2c8edf3f19d3de1ef6ba212bd2eb9fcc739e0e3c0`.

**Gate: FAIL / hold.** One reproducible high-severity correctness defect remains:
nanosecond-valued metadata does not guarantee a distinct ctime for every write
on either tested filesystem. The new digest cache can return the old hash for
changed bytes. The checkpoint's stated filesystem assumption is disproven by
direct runtime evidence and must be revised before this implementation can pass.

Canonical authority: `docs/schemas/file-dependency-freshness-contract.md`,
production M1/M3 freshness refinements, the accepted report contract and RQ
response contract. Scope: source/artifact comparison, digest cache, M1/M3 locked
publication, get-state projection and accepted-file downloads.

## Findings

| ID | Severity | Surface / evidence | Required action / disposition |
| --- | --- | --- | --- |
| FWC-01 | **High / P1, open** | `production.py:cached_digest` and `_digest_version` reuse a cached SHA based on `(dev, inode, size, mtime_ns, ctime_ns)`. Actual create/hash/equal-size rewrite/restored-mtime operations produced the same complete identity but different bytes, and `cached_digest(..., local=True)` returned the previous SHA. Retained probe reproduced on both container `/tmp` and repository bind mount. | Revise the cache-admission/coherence contract using measured supported-filesystem behavior. Do not fix this by sleeping in the regression or merely assuming nanosecond precision. A bounded recently-modified-file cache-admission policy may address the demonstrated timestamp-quantum collision, but its supported resolution/clock assumptions and warm-read budget require evidence and contract review. Keep uncached execution validation. |
| FWC-02 | **High / P1, implementation corrected during review** | Initial `execute_model` admitted same-content active dNBR artifacts but its finalizer compared their original acceptance timestamps. A harmless link/touch before starting M1 therefore advertised a usable upload and failed only after expensive computation. | Current code captures `verified_active` before uncached strong admission verification, rechecks that capture, and uses it at finalization. This separates accepted content from the run's mutation guard. `test_upload_and_model_real_artifacts` now inserts a real pre-run hard link. Require passing revised test and a complementary during-build mutation rejection test before marking fully validated. |
| FWC-03 | **Medium / P2, implementation corrected during review** | New route `rainfall_io.open_local` could raise `RainfallError`; generic `boundary_error` would map it to HTTP 503 rather than the canonical changed-file conflict. | Route now translates this expected local artifact invalidity to `WorkflowError('changed_file', ..., 409)`. Add an actual over-limit/rejected-open route regression; verify handle closure and existing error schema. |
| FWC-04 | Medium, coverage/performance follow-up | `_current_authority` calls `sources` under the finalization lock. Newly added source hashes can cause cold reads there after metadata drift/cache eviction, before strict snapshot inequality rejects the attempt. | Measure lock-held cold work and consider an initial strict-stat comparison against the captured snapshot before content revalidation. No observed wrong acceptance from this path; do not redesign the publication protocol speculatively. |

## Direct false-current evidence

Replayable evidence:

```bash
wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/first_wave_ctime_collision_probe.py
```

`first_wave_ctime_collision_probe.json` records the retained rerun. Each tested
filesystem produced a stale cache hit by iteration 3. The real old bytes were
`before`; the new bytes were `AFTER!`, both length six. The cached result was
`6db7d803e74f1ffa7d8f5adc0bf95b3e15bf4c8373fffadf546227cc6c6742cb`, while an
independent SHA-256 of the current bytes was
`a7b70603afa9575af9458adc5edccac707a5bcb8d311f62ec3fcde4dbbe3f9b7`.
There are no mocked metadata values, clocks, opens or hash functions. All files
were disposable. No existing project or accepted record was changed.

The predecessor `first_wave_focused_revision2.log` also contains a real hard-link
ctime collision: `test_source_snapshots_legacy_and_content` expected a changed
ctime but received identical timestamps. That failed assumption is evidence,
not a reason to weaken the expected true-content invalidation requirement.

This affects `sources` and `artifacts_current(strong=False)`: both now promote
cached hashes into accepted-content equality. A same-byte replacement or touch
can establish a fresh cache entry whose timestamp quantum has not elapsed;
a rapid preserved-time rewrite can then leave the stale entry reusable for
later reads. The full before/after descriptor checks see the same collision.

## Contract and valid-state review

- New source snapshots preserve stat fields and add complete hash maps. The
  comparison strips timestamps only for complete valid new maps, compares
  selections and other keys, and distinguishes absent from empty files.
- Legacy comparison removes only the additive hash map, retaining exact
  timestamp comparison. Old acceptance is not rewritten. Malformed maps have
  targeted missing/extra/null/invalid-hash tests.
- Strong artifact checks remain uncached. Locked finalizers explicitly request
  strict stat behavior; M1 now captures run-time active-artifact metadata so
  prior harmless churn does not make accepted uploads unusable.
- The route requires an accepted five-field SHA record, admits the file through
  component-wise no-follow opening, compares descriptor metadata around hashing,
  rereads accepted state, and passes that same descriptor to streaming ownership.
  This restores the already-canonical SHA requirement without fabricating hashes
  for legacy source snapshots.
- Security's no-follow improvements now apply to project hashes via `local=True`.
  Engine/tool hashing stays a separate trusted path. Final security review owns
  that distinction and containment/race proof.

## Coverage and residual risk

The initial focused suite retained **135 passed** in
`first_wave_focused.log`, before the in-review fixes. The revision-2 run stopped
at the real timestamp collision after **12 passed, 1 failed**. Neither log proves
the latest working tree passes. Regression expansion and reruns are ongoing.

Existing/new direct coverage includes real hard links and unlink, touch/chmod,
same-byte replacement, preserved-mtime changed bytes, absent/empty inputs,
hash-map corruption, descriptor mutation, read-access failure and M3 actual
get-state after WEPP `copy_input_file`. M1 pre-run churn coverage was added during
review. Remaining first-wave gaps include true-content changes through get-state,
mid-build strict-finalizer rejection with existing result retention, route
descriptor mutation/size errors, and same-quantum cache collisions.

`state_performance.json` reports 211 cached files, zero new misses over 100 warm
M3 state reads, approximately 213 ms per warm state call and 1.17 s initial state.
This validates working-set capacity only for that implementation and one project;
it predates the latest no-follow changes. Rerun after resolving FWC-01 and include
two interleaved projects, per-file cold/warm limits and ordinary metadata
revalidation. NFS behavior remains unproven.

Rebuilt/restarted services, real UI/RQ/WEPP acceptance, canonical archive/restore,
and all non-postfire open findings remain outside this interim implementation
sign-off. Project artifacts continue using existing observable attempt paths;
failure retention and archive member equality still require final acceptance.
