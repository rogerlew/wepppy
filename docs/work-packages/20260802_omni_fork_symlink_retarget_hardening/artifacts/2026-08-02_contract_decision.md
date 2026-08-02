# SURF-04A Omni Fork Symlink Retarget Contract Decision

**Date**: 2026-08-02 18:28 UTC
**Starting revision**: `82bf325d88bc8447ccd8c959e2f3e536de81da0b`
**Security impact**: high
**Implementation status**: approved contract; conformance pending

## Operator Decision

The operator directed that forks retarget symlinks, elected to retain rsync for
wall time, and asked Codex to scaffold and execute this package. Production
deployment and in-place repair remain separately authorized.

## Normative Contract

1. Fork copy continues using `rsync -a --stats` with current exclusions,
   heartbeat, bounded output, API, queue, and RQ terminal behavior.
2. All producers create the relative link forms below. This includes Omni clone
   services and `wepppy.weppcloud.utils.helpers:_ensure_omni_shared_inputs`.
3. Immediately after rsync and before root NoDb rewrite, TTL initialization, or
   success, the fork worker normalizes copied legacy links from semantic role to
   the destination root. Old targets need not exist and are never statted,
   opened, resolved, or followed.
4. Normalization is independent of the copied target string and therefore
   repairs links inherited through any fork depth.
5. Unrecognized links outside the matrix remain unchanged. The `_pups`, `omni`,
   `scenarios`/`contrasts`, and immediate child entries are security ancestors,
   not unrecognized links: each must be a real directory, never a symlink or
   special entry.
6. Inventory accepts only immediate child names returned by descriptor-relative
   directory iteration. `.`/`..`, slash, backslash, NUL, symlinked child
   directories, and non-directory child entries are rejected, except the
   canonical regular metadata file `build_report.ndjson`, which is retained
   unchanged. No other collection-level regular filename is allowed.
7. Destination root and every ancestor are opened descriptor-relatively with
   directory and no-follow semantics. Candidate `lstat`, temporary-link
   creation, replacement, and validation use the held child directory
   descriptor; path-string check-then-use is insufficient.
8. Before mutation, all candidates and root targets are preflighted. Root
   directory roles must be real non-symlink directories. Root `.nodb`/`.nodir`
   and ordinary-mode `wepp/runs/<basename>` targets must be regular non-symlink
   files. Missing,
   dangling, external, socket/device/FIFO, or symlink root targets fail.
   Removal mode is the exception: the intentionally excluded root
   `wepp/runs/<basename>` target is neither required nor accessed; preflight
   verifies the child entry is a symlink and records its exact raw link text.
9. At a recognized child role, a symlink is normalized. A supported
   materialized directory/file of the role's expected type is retained. Any
   other type fails. Contrast `wepp/runs` regular files are retained; symlinks
   are normalized by safe basename.
10. Before either replacement or removal, each inventoried link is atomically
    moved with descriptor-relative ordinary `os.rename` into a newly created
    random, mode-0700 quarantine directory beneath the destination root and
    identity-verified there. The private directory is empty at creation and
    random quarantine names are unique within it under the clause 14 threat
    boundary, so capture does not overwrite project data. Canonical publication
    uses descriptor-relative exclusive `os.symlink`. Restoration uses
    descriptor-relative `os.link(..., follow_symlinks=False)` from quarantine
    to the absent project name, verifies identical device/inode/type/raw text,
    then unlinks the private quarantine name. `EEXIST` fails closed without
    overwriting a recreated entry. Rollback captures and verifies any published
    canonical link before exclusive restoration of the original. If a covered
    project-path race substitutes a directory or another object that NFS cannot
    hard-link, normalization fails closed and retains the capture inside the
    unpublished destination for whole-destination cleanup; it does not attempt
    an overwriting rename-back or claim in-place restoration.
11. The operation is transactional: preflight completes before the first
    replacement; original link text is recorded; a later failure rolls back
    every published replacement in reverse order when exclusive restoration is
    supported. Rollback failure or a non-hardlinkable raced capture is reported
    with the primary error. A failed destination is never declared usable;
    normal recovery discards it and allocates a fresh fork destination.
12. Success follows descriptor-relative revalidation of every normalized link
    and confirmation that its canonical target exists with expected type inside
    the destination. Failures propagate through the existing exception boundary
    as a failed `fork_rq` job and `FORK_FAILED`; no response schema or queue edge
    changes.
13. When `skip_wepp_runs_output=True` or `undisturbify=True`, rsync continues to
    exclude root `wepp/runs` and `wepp/output`. Copied symlink entries below
    `_pups/omni/contrasts/<child>/wepp/runs/` are therefore removed during the
    same transaction instead of being retained as dangling links. Regular
    materialized contrast-run files remain unchanged. Removal atomically moves
    each candidate to a collision-safe quarantine name before verifying the
    quarantined device, inode, symlink type, and exact raw link text. A mismatch
    is restored without deleting the moved entry and fails the fork. Verified
    quarantines are retained through full validation, restored exactly during
    rollback, and deleted only at commit. No quarantine residue is permitted on
    successful completion or an uncontended rollback. A contested,
    non-hardlinkable capture may remain only inside the failed unpublished
    destination pending whole-destination cleanup.
14. The private quarantine directory is not a project namespace and is never
    exposed through a completed fork. The concurrent-mutation threat model
    covers destination project paths but excludes actors that bypass mode-0700
    permissions or run arbitrary code as the fork worker UID to guess and
    mutate random quarantine names. Cleanup revalidates through the held private
    directory descriptor immediately before unlink and removes the directory
    before success.
15. Fork normalization must not depend on `renameat2` flags or another primitive
    unsupported by the production NFSv4.2 export. Required parity evidence runs
    ordinary cross-directory rename of a symlink, hard-link restoration of the
    symlink object with `follow_symlinks=False`, collision refusal, raw-text and
    inode identity checks, and cleanup on an actual NFS-backed path. Local ext4
    evidence alone is insufficient.
16. Regression evidence must deterministically replace an inventoried symlink
    with both a regular file and a directory immediately before capture. The
    regular object must be exclusively restorable without byte or inode loss.
    The directory case must fail closed without overwriting a recreated name or
    mutating anything outside the fresh destination; retained quarantine makes
    the destination unusable and is reported for whole-destination cleanup.

## Exact Role Matrix

All targets are relative from `_pups/omni/<collection>/<child>/`.

| Collection | Child role | Root target | Expected type | Canonical link |
| --- | --- | --- | --- | --- |
| scenarios | `climate` | `climate` | directory | `../../../../climate` |
| scenarios | `watershed` | `watershed` | directory | `../../../../watershed` |
| scenarios | `dem` | `dem` | directory | `../../../../dem` |
| scenarios | `climate.nodb` | `climate.nodb` | regular file | `../../../../climate.nodb` |
| scenarios | `dem.nodb` | `dem.nodb` | regular file | `../../../../dem.nodb` |
| scenarios | `watershed.nodb` | `watershed.nodb` | regular file | `../../../../watershed.nodb` |
| scenarios/contrasts compatibility | `climate.nodir` | `climate.nodir` | regular file | `../../../../climate.nodir` |
| scenarios/contrasts compatibility | `watershed.nodir` | `watershed.nodir` | regular file | `../../../../watershed.nodir` |
| contrasts | `climate` | `climate` | directory | `../../../../climate` |
| contrasts | `watershed` | `watershed` | directory | `../../../../watershed` |
| contrasts | `climate.nodb` | `climate.nodb` | regular file | `../../../../climate.nodb` |
| contrasts | `watershed.nodb` | `watershed.nodb` | regular file | `../../../../watershed.nodb` |
| contrasts | `landuse.nodb` | `landuse.nodb` | regular file | `../../../../landuse.nodb` |
| contrasts | `soils.nodb` | `soils.nodb` | regular file | `../../../../soils.nodb` |
| contrasts | `unitizer.nodb` | `unitizer.nodb` | regular file | `../../../../unitizer.nodb` |
| contrasts | `treatments.nodb` | `treatments.nodb` | regular file | `../../../../treatments.nodb` |

Every direct symlink entry
`_pups/omni/contrasts/<child>/wepp/runs/<basename>` maps to root
`wepp/runs/<basename>` and canonical target `../../../../../../wepp/runs/<basename>`.
Basenames must be a single non-empty component other than `.` or `..`.
In skip/undisturbify mode, those symlink entries are removed because their root
targets are intentionally excluded; in ordinary forks they are retargeted.

## Compatibility and Rejected Alternatives

Legacy `.nodir` compatibility remains supported by the composite-run helper.
Materialized expected-type entries remain unchanged. Partial failed fork
destinations are not reused; retries allocate a fresh destination. Unrelated
and intentionally cross-run links outside the matrix remain unchanged.

Replacing rsync lacks benchmark support. `--copy-links` materializes data;
`--safe-links` can silently omit it. Source-prefix replacement misses inherited
grandparent links. Rewriting every link widens disclosure/corruption risk.

## Required Regression Evidence

- Exact new relative forms for clone and composite helper producers.
- One- and two-generation repair with missing old targets and explicit proof
  that old targets are never accessed.
- Exact unchanged rsync argv, exclusions, heartbeat, API, and terminal mapping.
- Symlinked `_pups`, `omni`, collection, child, and root-role targets; parent
  replacement race; outside sentinels remain untouched.
- Invalid child names/types, dangling/external/special root roles, supported
  materialized entries, unrelated links, temp collisions/residue, rollback,
  retry-to-fresh-destination, and ordering before NoDb rewrite.
- Skip/undisturbify removal of copied contrast-run symlinks, retention of
  regular materialized entries, no root-target access, and rollback restoring
  exact raw link text. Cover effective removal mode separately for
  `(skip=True, undisturbify=False)`, `(skip=False, undisturbify=True)`, and both
  true, plus ordinary retargeting when both are false. Deterministically swap a
  candidate symlink for a regular file immediately before quarantine; its bytes
  and original name must survive, the fork must fail closed, earlier actions
  must roll back, and no temporary/quarantine residue may remain.
- Byte-for-byte retention of regular `build_report.ndjson` under both
  collections; rejection of another regular filename and of same-name symlink
  or special entries under both collections.

Two independent read-only reviews and disposition are required before this
documentation-only checkpoint is committed as the implementation ancestor.
