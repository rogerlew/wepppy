# Resumed vector upload correctness review

- Reviewed source: `ee26389f099e9e950b5920d53790f8661548a5e3`.
- Earlier frozen candidate: `de15403aadbd7a659ef4717e77223ff4890b18c1`.
- Reviewer: dedicated `reviewer` agent `provenance_review`.
- Exact unchanged converter image:
  `sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`.
- Verdict: **HOLD: one High privacy finding and one Medium accounting finding.**

This review examines production correctness and the actual downstream methods.
The reviewer authored the new session-provenance regression module earlier in
this resumption; independent QA of that module belongs to the separate frozen QA
review, and this artifact does not independently approve those tests. No production
code was changed during this review. Neither publication nor deployment is approved.

## Findings

### VUN-CORRECTNESS-RESUME-01: High - ordinary forks copy private vector evidence to a new owner

The public-run fork route admits an ordinary non-owner through
`authorize_run_access()` (`wepppy/microservices/rq_engine/fork_archive_routes.py:960-963`;
`wepppy/microservices/rq_engine/auth.py:196-206`) and also explicitly supports
anonymous public-run forks. The destination metadata grants the requesting human
ownership (`fork_archive_routes.py:1531-1542`). Its worker calls the ordinary rsync
builder, whose exclusions omit all four `vector_upload_attempts` roots and
`archives/private` (`wepppy/rq/project_rq_fork.py:580-602`).

Consequently, a non-owner can copy a public source's private upload originals,
rejected/hostile candidates, normalization receipts and private archives into a
new destination. The sensitive-download predicate then recognizes that requester
as the destination owner (`wepppy/microservices/browse/sensitive_vectors.py:74-93`).
The public-source sensitive-read denial therefore does not protect the same bytes
across the fork boundary. This contradicts the canonical contract's explicit
owner/root evidence authority and ban on ordinary public-read access.

A harmless local reproduction invoked the real `_build_fork_rsync_cmd()` and
actual `rsync` against a temporary source containing a private `.upload`, a
private ZIP and a canonical GeoJSON. At the reviewed revision it returned:

    {"fork_copied_private_original": true,
     "fork_copied_private_archive": true,
     "fork_copied_canonical": true}

This reproduction used no user project, credential, remote service or destructive
external action. It proves the copy step; the authorization consequence follows
from the production source/ownership/download paths above.

Required closure: ratify whether ordinary copies retain private evidence only in
the source with a provenance reference, or permit explicit source-authorized
copies with accounting. In every case, a non-owner public fork must not acquire
private source evidence. Apply the rule to worker-time copy, not just browser
controls. Retain an end-to-end public non-owner fork test and inspect the copied
filesystem and destination download result; preserve the accepted canonical
GeoJSON needed to run the fork. The operator's disposition is pending as of this
review. No dependent implementation choice is made here.

### VUN-CORRECTNESS-RESUME-02: Medium - Batch cloning/reset and ordinary forks bypass retention accounting

The same fork rsync copies retained bytes without a destination reservation or
accounting commit. Batch execution has a second confirmed copy path:
`BatchRunner._run_batch_hillslopes_owned()` recursively copies `_base` to each
new leaf with `shutil.copytree(base_wd, runid_wd)`
(`wepppy/nodb/batch_runner.py:591-594`). A Roads, AgFields or Omni upload accepted
into the base is copied, including its original and receipt, into every generated
run without admission or destination provenance. Files retain the base attempt's
identity and principal while occupying additional uncharged space.

The rerun path invokes `_reset_run_workspace()` at `batch_runner.py:580-583`.
That helper renames the entire child to a stale directory and recursively removes
it (`:123-153`) without the retention scope, durable rebuild obligation or ledger
repair. A leaf upload can therefore disappear with stale charged totals; partial
removal can leave evidence moved outside its original project identity. This is
the same failure class now repaired for whole-Batch deletion, reached through a
separate established consumer. Canonical Batch input files themselves must remain
available after the chosen repair.

Required closure: apply the operator-selected copy/provenance rule consistently
to ordinary forks and Batch base-to-leaf copying. Preserve or durably reconcile
retained child evidence during automatic reset, including partial removal and
retry. Prove the global/principal totals against filesystem bytes with unrelated
active reservations, and ensure copied receipts cannot masquerade as new upload
acceptance. Do not silently discard newly retained originals or disable the
established Batch rerun workflow to close accounting.

## Closed or accepted production checks

- Run and Batch deletion validate missing/outside-root configuration before TTL,
  cache or filesystem mutations; direct deletion symlinks are rejected.
- Whole-Batch deletion acquires global maintenance before its Batch and generated
  child scopes, persists the dual obligation, fsyncs even an absent-target retry,
  rebuilds exact-root totals and rechecks owned leases before marker completion.
- Private bundle retry can repair partial deletion without requiring already
  removed provenance, but continues to validate containment and symlink ancestry.
  Private restore detects incoming sensitive members before project mutation.
- Obligation creation retains Redis authority after a possibly completed file
  replace/fsync failure, rejects existing/dangling symlink directories, and marker
  completion validates its configured root before unlinking.
- The `ee26389f0` amendment refuses a different destructive identity while either
  filesystem or Redis authority contains pending work. The identical operation
  can retry. Thus parent deletion cannot orphan a pending private repair by
  deleting its owner/target first.
- Roads preparation actually calls the monotonic segment converter with raster
  inputs; Batch's real generation method writes `dem/target_watershed.geojson`
  and registers the Ron boundary; AgFields writes rotation Parquet; both Omni
  build entry points reach the user-defined-area report/sidecar writers. The
  revised downstream tests exercise those production methods rather than
  manufacturing their asserted acceptance artifacts. The clone/reset finding
  above was identified while tracing that real Batch path.
- The conservative nonterminal recovery decision remains accepted: absent an
  authoritative workflow adapter, prepared/source-stored state stays incomplete.
  No new recovery adapter is required by this review.

## Validation boundary

Independent execution uses a `git archive` of the reviewed commit in
`/tmp/vun-correctness-de154` inside the existing development `weppcloud` container;
that directory was refreshed from `ee26389f0` before execution. The shared checkout
and running service mounts were not changed. Canonical `wctl run-pytest` cannot
select this task worktree because of the known container mount mismatch; the
explicit `wctl exec` command tests the archive instead:

    wctl --project-dir /home/workdir/wepppy exec -T \
      -w /tmp/vun-correctness-de154 \
      -e PYTHONPATH=/tmp/vun-correctness-de154 weppcloud \
      /opt/venv/bin/python -m pytest \
      tests/rq/test_vector_retention_deletion.py \
      tests/rq/test_vector_archive_recovery.py \
      -q --maxfail=1 --basetemp=/tmp/vun-correctness-testdata

Result is recorded below after completion. Root's frozen final5 downstream and
combined validation receipts remain the authority for broader acceptance; this
review does not relabel earlier aggregate runs as a fresh full-suite pass.

The two findings must close on a successor with the operator's copy-retention
contract documented and tested. Production-equivalent remote-host canaries,
publication and rollout remain separate gates even after local closure.

Independent execution completed at 2026-11-17 08:28 UTC: **52 passed**, no failures or skips, 18 pre-existing dependency/deprecation warnings, 50.11 seconds. Documentation lint validated this artifact with zero errors and zero warnings.
