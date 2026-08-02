# Execute Omni fork symlink retarget hardening

This ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep
Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective
current and update this plan with the package tracker at each milestone.

## Purpose / Big Picture

A fork remains an rsync-speed copy but becomes independent of source and
ancestor runs for every recognized Omni shared-input link. Users can delete or
expire an ancestor without breaking a descendant's Omni scenarios or future
archives.

## Progress

- [x] (2026-08-02 18:28 UTC) Captured production lineage and operator choice.
- [x] (2026-08-02 18:28 UTC) Scaffolded SURF-04A and initial checkpoint.
- [x] (2026-08-02 18:45 UTC) Received two independent checkpoint reviews.
- [x] (2026-08-02 18:50 UTC) Expanded producer/role inventory and no-follow
  transactional security contract in response to review.
- [x] (2026-08-02 19:05 UTC) Obtained post-fix confirmations, dispositioned
  findings, and committed checkpoint ancestor `9d437942f2c78ea54cb66e4bfd2cb454670d7995`.
- [x] (2026-08-02 19:35 UTC) Wrote initial regressions and implemented producers
  plus fork normalization.
- [x] (2026-08-02 20:15 UTC) Ratified the skip/undisturbify contrast-run
  amendment after independent contract and security approvals.
- [x] (2026-08-02 21:00 UTC) Committed amendment ancestors and completed
  adversarial regressions prompted by final review.
- [x] (2026-08-02 21:45 UTC) Validated, independently reviewed, dispositioned,
  and closed locally without deployment.
- [x] (2026-08-02 22:15 UTC) Reopened after production NFSv4.2 returned
  `EINVAL` for `renameat2(RENAME_NOREPLACE)`.
- [ ] Ratify and commit an NFS-compatible transaction checkpoint.
- [ ] Implement, exercise on NFS, repeat all gates, and re-close.

## Surprises & Discoveries

- `rsync -a` preserves dangling absolute links exactly.
- Root NoDb rewriting does not touch nested symlink targets.
- A source can already contain links to its parent or grandparent, so replacing
  only the immediate source prefix cannot repair fork chains.
- `_ensure_omni_shared_inputs` is a second producer/repairer and supports legacy
  `climate.nodir` and `watershed.nodir` entries.
- Contrast clones also link selected root NoDb files and direct entries under
  `wepp/runs`; these require explicit roles rather than heuristic rewriting.
- Lexical path checks alone do not prevent a symlinked/swapped ancestor from
  redirecting temporary-link creation or replacement outside the fork.
- Root-only skip exclusions leave copied contrast `wepp/runs` symlinks without
  their intentionally excluded targets unless normalization removes them.
- Omni collections contain canonical `build_report.ndjson` metadata alongside
  child directories, requiring one exact regular-file exception.
- `renameat2` may exist in libc and work on ext4 while the production NFSv4.2
  backing filesystem rejects `RENAME_NOREPLACE` with `EINVAL`.

## Decision Log

- Decision: Keep `rsync -a --stats` unchanged.
  Rationale: no benchmark justifies replacing the high-performance copy engine.
  Date/Author: 2026-08-02 / operator and Codex.
- Decision: Canonical links are relative and role-derived.
  Rationale: they survive arbitrary fork depth without source dependencies.
  Date/Author: 2026-08-02 / operator and Codex.
- Decision: Use descriptor-relative/no-follow inventory and replacement with
  preflight plus rollback.
  Rationale: path-string containment cannot close parent-swap races.
  Date/Author: 2026-08-02 / checkpoint security review disposition.
- Decision: Preserve links outside the exact matrix.
  Rationale: generic rewriting could corrupt intentional unrelated links.
  Date/Author: 2026-08-02 / Codex.
- Decision: Remove copied contrast-run symlinks in skip/undisturbify mode while
  retaining regular materialized files.
  Rationale: root targets are intentionally excluded, so retargeting cannot
  satisfy the completed-fork no-dangling-link invariant.
  Date/Author: 2026-08-02 / final review discovery and Codex.
- Decision: Replace `RENAME_NOREPLACE` with ordinary rename into a newly
  created private quarantine plus exclusive hard-link restoration.
  Rationale: NFS supports ordinary rename and link creation, while link creation
  fails with `EEXIST` instead of overwriting a recreated project entry.
  Date/Author: 2026-08-02 / production failure remediation.

## Outcomes & Retrospective

The first implementation was incompatible with the production NFSv4.2 backing
filesystem despite passing ext4 validation. Remediation is pending. Earlier
review improved the producer inventory, role matrix, private capture-first
transaction, rollback, metadata compatibility, and test plan, but the package
is not complete until the revised primitive passes actual-NFS evidence and all
gates. No production data was repaired.

## Context and Orientation

`wepppy/rq/project_rq_fork.py:prepare_fork_run` runs rsync, then rewrites root
NoDb payloads and removes copied identity/marker state. The new normalization
belongs immediately after rsync and before those later steps.

`wepppy/nodb/mods/omni/omni_clone_contrast_service.py` creates scenario and
contrast child workspaces with absolute links. Contrast clones additionally
link selected root NoDb files and individual parent `wepp/runs` files.
`wepppy/weppcloud/utils/helpers.py:_ensure_omni_shared_inputs` recreates missing
shared links for composite run resolution, including legacy `.nodir` files.

The exact normative role matrix and security behavior live in
`artifacts/2026-08-02_contract_decision.md`; implementation must not infer extra
roles from filename patterns.

## Milestone 1: Checkpoint Ancestor

Store both raw independent checkpoint reviews and a disposition artifact.
Obtain post-fix confirmation that every high/medium finding is resolved. Lint
all changed docs and commit the checkpoint, SURF registration, durable guide
pending note, and related archive decision notes as one standalone ancestor.
Record its revision in the tracker. Do not edit code or tests before this commit.

## Milestone 2: Failing Regressions

Extend `tests/nodb/mods/test_omni.py` and
`tests/weppcloud/utils/test_helpers_paths.py` to assert every producer's exact
relative link. Extend `tests/rq/test_project_rq_fork.py` for the matrix,
multi-generation/missing-target repair, descriptor-relative containment,
materialized entries, unrelated links, transaction rollback, no temp residue,
old-target non-access, and ordering before NoDb rewrite. Use monkeypatchable
helpers or synchronization events, never sleeps.
Exercise the exact collection metadata exception in both collections: preserve
regular `build_report.ndjson` byte-for-byte and reject other regular names plus
same-name symlink and special entries.

## Milestone 3: Implementation

Add a small relative-link helper for producer use without creating a generic
symlink framework. Update scenario clone, contrast clone, contrast `wepp/runs`,
and composite helper creation sites.

In `project_rq_fork.py`, define the fixed matrix and implement fork
normalization with root/ancestor directory descriptors opened no-follow. Scan
only immediate children, classify entries with descriptor-relative stat calls,
preflight every action and target, create exclusive temporary siblings, replace
atomically, validate, and rollback published links on failure. Publish bounded
count/duration status without per-link output. Invoke immediately after rsync.
Pass the effective removal mode `undisturbify or skip_wepp_runs_output` as the
normalizer's keyword-only `skip_wepp_runs_output` boolean. Removal candidates
must be atomically quarantined and identity-verified before deletion at commit;
never unlink a candidate directly after a check.
Use one random mode-0700 quarantine directory beneath the incomplete
destination, held by descriptor. Capture with ordinary descriptor-relative
rename and restore hardlinkable objects exclusively with
`os.link(..., follow_symlinks=False)`, followed by identity verification and
private-name unlink. Publish canonical links exclusively. A raced directory is
non-restorable in place: fail closed, retain it only inside the unpublished
failed destination, and require whole-destination cleanup.

## Concrete Steps

From `/home/workdir/wepppy`:

    wctl run-pytest tests/rq/test_project_rq_fork.py --maxfail=1
    wctl run-pytest tests/nodb/mods/test_omni.py -k "clone or contrast" --maxfail=1
    wctl run-pytest tests/weppcloud/utils/test_helpers_paths.py --maxfail=1
    wctl docker compose exec \
      -e WEPPPY_NFS_TEST_ROOT=/wc1/benchmarks/omni-fork-nfs-parity \
      weppcloud bash -lc 'cd /workdir/wepppy && \
        PYTHONPATH=/workdir/wepppy /opt/venv/bin/pytest \
        tests/rq/test_project_rq_fork_nfs.py -m integration -vv'
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20260802_omni_fork_symlink_retarget_hardening
    wctl doc-lint --path docs/ui-docs/weppcloud-project-forking.md
    git diff --check

Run `wctl check-rq-graph` only if implementation unexpectedly changes queue
wiring; the contract excludes that change.

## Validation and Acceptance

Tests must inspect generated links and a complete two-generation destination,
not only helper return values. Exact rsync argv and existing fork tests remain
green. Foreign sentinel trees must remain unchanged across every adversarial
case. All medium/high correctness, QA, and security findings must be resolved.

Track normalization count and duration. A later Forest canary should compare
fork wall time with rsync baseline and reject material p50/p95 regression before
production deployment. Deployment remains separately authorized.

The NFS parity test must first verify that `WEPPPY_NFS_TEST_ROOT` is on NFS and
refuse to count ext4/tmpfs as evidence. It must exercise cross-directory rename
of a symlink into private quarantine; symlink-object hard-link restoration;
raw-text, type, device/inode identity; `EEXIST` collision refusal without
overwrite; private cleanup; and deterministic regular-file and directory leaf
swaps. Store the mount record, command, and transcript summary in
`artifacts/2026-08-02_nfs_transaction_validation.md` and mirror the result in
the package tracker.

## Idempotence and Recovery

Normalization is idempotent: canonical relative links yield no replacement.
Preflight occurs before mutation, and any later failure rolls back in reverse
order and cleans temporary siblings. A failed fork destination is not reused;
retry allocates a fresh destination. Source and foreign trees are never written.

## Interfaces and Dependencies

No external dependency is added. Use Python `os` descriptor-relative APIs,
`stat`, `secrets` or equivalent collision-safe naming, and existing status
publication. Keep helper interfaces private and typed. The producer helper
accepts owning run root, child root, and role. The fork normalizer accepts the
destination root plus keyword-only effective `skip_wepp_runs_output: bool` mode
and returns a normalized/removal count for status/telemetry.

## Artifacts

Required artifacts are the contract decision, two raw checkpoint reviews,
checkpoint disposition, final correctness review, QA review, security review,
and validation/closeout evidence in the tracker.

Plan revision note (2026-08-02): Initial focused plan after the operator chose
rsync-preserving hardening.

Plan revision note (2026-08-02): Expanded after independent checkpoint reviews
to cover all producers/roles, no-follow ancestor safety, transactional rollback,
hardening signals, and complete ExecPlan requirements.

Plan revision note (2026-08-02): Final review exposed a skip/undisturbify
interaction. Added an explicit transactional-removal contract and adversarial
validation milestone before the implementation commit.

Plan revision note (2026-08-02): Reopened after production NFS rejected the
ext4-validated `RENAME_NOREPLACE` primitive. Added a backing-filesystem parity
gate and an NFS-compatible capture/restore checkpoint.
