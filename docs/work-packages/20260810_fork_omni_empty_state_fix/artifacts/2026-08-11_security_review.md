# Security Review - Fork Omni Empty-State Conformance Fix

## Metadata

- **Package**: `docs/work-packages/20260810_fork_omni_empty_state_fix/`
- **Reviewer**: independent security reviewer agent
- **Date**: 2026-08-11
- **Scope reviewed**: descriptor-relative ancestor creation, Omni reset targets,
  hostile entries, retry/partial-state behavior, tests, and governance changes
- **Commit/branch context**: working tree on `master`
- **Related artifacts**: correctness and QA reviews in this directory

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: yes
- **Triage rationale**: the patch adds a directory-creation path inside a copied
  run tree and must preserve symlink/special-entry containment.
- **Valid states controls must preserve**: wholly absent `_pups`, existing real
  `_pups` with missing `omni`, empty hierarchy, populated reset targets, and an
  unready partial hierarchy from an interrupted prior attempt.

## Findings and Disposition

| ID | Severity | Description | Disposition | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | High | Path-based recursive creation could follow a copied or race-inserted symlink | Added reset-only descriptor-relative `mkdir`, followed by `O_DIRECTORY | O_NOFOLLOW` open with held parent descriptors | Resolved |
| SEC-02 | Medium | Relaxing `_open_fork_chain` would create state in unrelated strict traversal callers | Kept `_open_fork_chain` unchanged; new helper is used only by Omni reset ancestors | Resolved |
| SEC-03 | Low | Leaf replacement relies on exclusive destination ownership against concurrent real-directory substitution | Existing contract and fd-safe `rmtree` retained; no scope expansion recommended | Accepted unchanged residual assumption |

## Surface Checks

- [x] Valid absent, empty, populated, and retry states preserve their contracted
  fork outcome.
- [x] Existing ancestor symlinks, regular files, FIFOs, and Unix sockets fail
  closed.
- [x] A symlink swap after directory creation fails at the final no-follow open
  without external mutation.
- [x] Strict shared traversal helpers remain create-free.
- [x] Existing ancestor ownership and mode are preserved; no `chmod`/`chown`
  widening was added.
- [x] No rollback deletion was added; a partial real ancestor remains safe for
  idempotent retry.
- [x] Auth, secrets, request parsing, queue topology, subprocess behavior, and
  run-root resolution are unchanged.
- [x] The orchestration regression keeps `_reset_forked_omni` and the directory
  reset helper real while stubbing unrelated collaborators.

## Validation Evidence

- `wctl run-pytest tests/rq/test_project_rq_fork.py -q`: 102 passed, 4 warnings.
- `git diff --check`: passed.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`:
  passed with net delta zero.
- Scoped canonical documentation lint: zero errors and zero warnings.

## Residual Risk

Unchanged assumptions remain: Linux `O_NOFOLLOW` and `dir_fd` support,
exclusive destination ownership during reset, and Python's fd-safe `rmtree`.
No new accepted security risk was introduced.

## Verdict

- **Gate status**: pass
- **Unresolved findings**: zero high; zero medium; zero low
- **Release recommendation**: ship after correctness, QA, and full-suite gates
  pass

## Sign-off

- **Security reviewer**: independent security reviewer agent, 2026-08-11
- **Package owner**: Codex, 2026-08-11
