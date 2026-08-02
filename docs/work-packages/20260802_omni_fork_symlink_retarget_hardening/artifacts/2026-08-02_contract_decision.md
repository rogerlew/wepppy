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
   directories, and non-directory child entries are rejected.
7. Destination root and every ancestor are opened descriptor-relatively with
   directory and no-follow semantics. Candidate `lstat`, temporary-link
   creation, replacement, and validation use the held child directory
   descriptor; path-string check-then-use is insufficient.
8. Before mutation, all candidates and root targets are preflighted. Root
   directory roles must be real non-symlink directories. Root `.nodb`/`.nodir`
   and `wepp/runs/<basename>` targets must be regular non-symlink files. Missing,
   dangling, external, socket/device/FIFO, or symlink root targets fail.
9. At a recognized child role, a symlink is normalized. A supported
   materialized directory/file of the role's expected type is retained. Any
   other type fails. Contrast `wepp/runs` regular files are retained; symlinks
   are normalized by safe basename.
10. Each replacement uses an exclusively named temporary sibling link created
    through the held directory descriptor and atomically published with
    descriptor-relative `os.replace`. Temporary entries are cleaned on every
    path.
11. The operation is transactional: preflight completes before the first
    replacement; original link text is recorded; a later failure rolls back
    every published replacement in reverse order. Rollback failure is reported
    with the primary error. A failed destination is not declared usable; normal
    recovery is a fresh fork destination.
12. Success follows descriptor-relative revalidation of every normalized link
    and confirmation that its canonical target exists with expected type inside
    the destination. Failures propagate through the existing exception boundary
    as a failed `fork_rq` job and `FORK_FAILED`; no response schema or queue edge
    changes.

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

Two independent read-only reviews and disposition are required before this
documentation-only checkpoint is committed as the implementation ancestor.

