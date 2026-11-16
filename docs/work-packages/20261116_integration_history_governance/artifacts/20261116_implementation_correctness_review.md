# Implementation correctness review — receipts and local history guard

## Metadata and scope

- Date: 2026-11-16, UTC.
- Reviewer: delegated correctness/QA agent, independent of M1 implementation.
- Scope: `tools/check_integration_history.py`, `tools/install_integration_hooks.py`,
  `tests/tools/test_integration_history.py`, and canonical integration policy.
- M2 evidence below is implementer validation, not independent M2 sign-off.
- Review surface: working implementation during this package, before integration.

## User outcome and acceptance evidence

The implementation refuses to certify unpushed accepted commits even when a
later ordinary fast-forward push succeeds. Receipts bind an accepted SHA to a
fresh isolated fetch of a declared remote branch, and verification requires the
saved repository/remote/branch identity. Ancestry remains explicitly distinct
from behavior and release eligibility.

Direct command: `wctl run-pytest tests/tools/test_integration_history.py -q --maxfail=1`.
Result before remediation: **16 passed**, two unrelated dependency deprecation
warnings, 16.69 seconds. The suite uses real disposable Git repositories and
bare remotes. It covers the 20-commit loss topology, published receipt readback,
dirty-state preservation during observation, no-clobber output, stale tracking
refs, remote advancement, unsupported shallow history, offline/missing objects,
wrong remote/branch, malformed receipts, rewrite detection, LFS-hook preservation,
custom-hook refusal, protected-ref loss and allowed forward updates.

## Findings

| ID | Severity | Finding | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| ICOR-01 | Medium | Ambient Git repository-selection variables override explicit `--repo`. | Two real repositories A/B with distinct sources/remotes: `receipt --repo A --accepted B_SHA` with `GIT_DIR=B/.git` exited 0 and emitted a receipt for B's origin. `git()` passes ambient environment to Git despite `-C A`. | Clear or explicitly reject repository-selection Git variables; prove `--repo A` cannot operate on B through ambient environment. Preserve legitimate hook invocation by resolving its real repository before sanitation if needed. | Resolved: repository-selection environment sanitized; two-repository and linked-worktree regressions pass |
| ICOR-02 | Medium | A ref-transaction refusal does not preserve working-tree/index state for arbitrary prohibited commands. | Real disposable repo: `git reset --hard BASE` exited 128 with `PROTECTED_MASTER`, master still pointed to accepted tip, but dirty tracked content became BASE content. | Explicitly document that the hook protects refs, not early command side effects. Prohibit destructive commands before execution; after refusal stop and inspect/recover. Do not promise WIP safety from the hook alone. | Resolved: canonical Operator commands explicitly document side effects and stop/recovery requirement |

The first issue can create a valid-looking proof for a different checkout than
the explicit caller selected. The second would cause users to rely on a stronger
safety guarantee than Git's hook boundary supplies. Neither requires new
infrastructure. Owner-controlled hook bypass remains an accepted limitation of
the stated accidental-loss threat model.

## Valid-state and consumer review

Read-only receipt operations preserve dirty tracked and untracked state and
transient observation refs are cleaned. Output uses an atomic no-clobber link
and retains its parsed semantic contents. Expected remote movement is represented
as a newer snapshot; exact consumers can require an expected SHA. Rewriting a
saved observed history is refused even when the accepted ancestor survives.
Missing or ambiguous evidence fails explicitly rather than producing a receipt.

The local hook installer leaves existing LFS pre-push content unchanged and
refuses custom hook managers or conflicting reference-transaction hooks. This is
compatible with the actual repository's multiple existing LFS hooks. The guard
allows normal forward commits and unrelated task-ref changes. It is not a
replacement for single-integrator ownership, remote protections, or behavior CI.

The artifact chain is explicit intent -> accepted object -> isolated fresh remote
object -> parsed receipt -> re-verifying consumer. GitHub enforcement and
publication wiring are outside this M1 correctness review and require their own
direct acceptance. The working-copy ref guard does not establish deployed state.

## M2 implementer validation retained for the integrator

- `wctl run-pytest tools/wctl2/tests -q --maxfail=1`: **66 passed** in 3.34 seconds.
- Live installed shim invoked from a disposable alternate checkout: exit `2`,
  `WCTL_CHECKOUT_MISMATCH`, no pytest execution, nonce removed afterward.
- Live invocation from `/tmp` outside any checkout: exit `0`, pytest `9.0.3`
  version returned using the installed project default.
- Canonical checkout test invocation passes through the real live-mount probe.
- Probe tests cover copied source mismatch, dirty/untracked source acceptance,
  alias mounts, nonce mismatch, interruption cleanup, explicit project precedence,
  caller detection and outside-checkout fallback.
- Generated dev shim was regenerated with existing system Python and confirmed
  to export caller cwd before changing directory. Initial installer attempts
  under Homebrew Python could not install absent dependencies into root-owned
  vendor storage; rerunning with `/usr/bin` first in PATH reused installed
  dependencies and succeeded. No dependency change was needed.
- Help, Compose status, npm version and three changed documentation lint checks
  passed. No container recreation or production deployment occurred.

The nonce verifies shared live source visibility, including dirty/untracked files.
It does not freeze concurrent edits or qualify ignored binaries/external inputs.
Source mutation and validation therefore remain serialized by policy.

## Remediation readback

Re-reviewed `git()` after remediation: repository, worktree, common directory,
index, object directory, alternate object directory, namespace, shallow-history,
replace-ref, discovery and environment-config overrides no longer redirect its
explicit repository. The added regression injects a second real repository into
these variables, verifies the intended remote and SHA, checks installer placement,
and preserves both indexes. A separate linked-worktree regression confirms the
installed guard still protects master with Git's normal exported hook environment.

Read back `/tmp/integration-history-env-tests.log`: **18 passed**, two unrelated
dependency deprecation warnings, 17.90 seconds. Source review and these direct
regressions close ICOR-01. The canonical standard's **Operator commands** section
now states that rejected reset/rebase operations may already mutate index/worktree,
requires stopping and deliberate recovery, and forbids retrying with the guard
disabled. This matches the direct destructive-command probe and closes ICOR-02.

## Verdict

M1 correctness: PASS for the reviewed receipt and local-reference guard scope.
Unresolved findings: zero High, zero Medium. GitHub rule enforcement, CI baseline
trust, publication gating and observation-period evidence remain separately owned
acceptance gates. The retained M2 results are not an independent implementation
review by its author.
