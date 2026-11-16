# Implementation security review — receipt, local guard, checkout identity, deployment consumer

## Metadata and independence

Reviewer: delegated `ci_security` agent, 2026-11-16 UTC. Scope: M1 receipt/hook
implementation, M2 wctl checkout proof, and root-authored deployment eligibility
consumer. Reviewed working implementation on `codex/integration-history-governance`.
The reviewer authored the separate CI baseline/publisher changes; those are
excluded from this independent approval and assigned to the history reviewer.
No production operation or external mutation was performed for this review.

## Verdict

**PASS for the scoped implementation review**, with zero open high/medium findings
in the independently reviewed surfaces. This is not remote-rule activation,
production validation, or approval of the reviewer-authored CI implementation.
Remote canary and final package-wide evidence remain required before closure.

## Findings and disposition

Root's subsequent review found an ambient Git-selection defect shared by the
receipt helper and the baseline/deployment helper: inherited `GIT_DIR`, worktree,
index/object, and Git configuration variables could override the explicit root.
Disposition: **resolved** by sanitizing those selectors, disabling replacement
objects, and retaining real two-repository redirection regressions. The reviewer
read back the corrected M1 implementation; baseline helper remediation remains
subject to the independent CI reviewer. This was a high source-identity finding,
not an accepted residual risk. No other high/medium defect was found in the scoped
receipt, hook, mount probe, or root deployment consumer. During cross-surface inspection, the reviewer found
that the baseline's protected paths omitted some existing shape build inputs.
That separate CI defect was repaired by adding `.dockerignore`, the shape
Dockerfile ignore file, requirements, the wepp1 Compose overlay, package imports,
and observability imports. The independently reviewing history agent also
identified the omitted checkout-identity helper; it and its tests are now
protected. Those repairs require the independent CI review's final disposition;
this artifact does not self-approve them.

## Boundary checks

### Receipt and local ref guard

`tools/check_integration_history.py` fetches an explicit branch into a unique
observation ref without replacing tracking refs or the checkout. The accepted
identity must be a complete commit ID; shallow history and failed fetches refuse
proof. Git replacement objects are disabled. The saved receipt records repository,
branch, accepted commit, remote commit, and timestamp and explicitly claims only
ancestry. Verification checks target identity and freshly observes remote history;
a stale local tracking ref is not sufficient.

Git stderr and remote command output are not echoed on failures. Credential-bearing
HTTP remote URLs are refused. Atomic receipt publication uses a complete temporary
file and no-clobber link, so retry cannot overwrite an existing receipt or follow an
existing output symlink. The parent directory is caller-controlled; no new
privilege boundary is claimed.

`tools/install_integration_hooks.py` refuses existing hook conflicts and configured
hook managers, leaving Git LFS's separate pre-push hook intact. The shared
reference-transaction hook rejects master deletion and non-ancestral replacement.
This is local accident prevention, not containment of an owner who edits hooks.
The standard correctly states that a refused hard reset/rebase may already have
changed working/index state; it does not promise those mutations are transactional.
The hook's absolute checker path must remain available; worktree retirement and
hook reinstallation belong to documented operator recovery.

### Checkout identity

`tools/wctl2/checkout_identity.py` creates a random non-secret nonce in the requested
host tree and requires the container's expected source root to read it before
pytest starts. The command is shell-quoted, the probe is readable across supported
container UIDs, and cleanup occurs on success or exception. Explicit project
selection takes precedence; otherwise caller checkout discovery prevents an
installed shim's directory change from silently selecting another checkout.

The nonce proves shared live source visibility, including dirty and untracked
changes, rather than merely equal commit IDs. It intentionally does not freeze
source against simultaneous edits. The standard requires serialized edits and
validation on the shared stack. No runtime secret, token, or user data is written
into the nonce or logs.

### Deployment consumer

`tools/check_deployment_governance.py` binds the local HEAD to eligibility for the
fixed `rogerlew/wepppy` repository and refuses staged, dirty, or untracked protected
source before querying remote evidence. It cannot borrow another repository's
successful check through CLI configuration. Existing `GH_TOKEN` is optional for
public API reads; access failure and rate limiting fail closed without printing
the token. No new production credential was introduced.

`scripts/deploy-production.sh` invokes the consumer after its existing source
fast-forward/restart handling and before builds, RQ suspension, or activation.
`--print-plan` retains its read-only behavior. Existing retained-image recovery,
source-overlay validation, targeted modes, and shape fail-closed logic remain in
their established paths. The new check does not authorize arbitrary dirty runtime
source: it verifies protected-source cleanliness and CI identity; broader runtime
and overlay contracts still depend on the existing deployment validators.

The check reads source and remote state at a point in time. It does not lock remote
master or protect a caller who intentionally edits the local checker/deployment
script itself. These limits match the adopted accidental-loss/explicit-policy-change
threat model; hostile owner credential containment would require a different
trust boundary.

## Validation evidence

Executed through the canonical mounted-checkout proof:

```text
wctl run-pytest tests/tools/test_integration_history.py \
  tools/wctl2/tests/test_checkout_identity.py \
  tests/tools/test_deployment_governance.py -q --maxfail=1
29 passed, 2 warnings in 18.32s
```

The receipt/hook cases use real disposable repositories and bare remotes, including
the original 20-commit loss with valid remote fast-forward, stale refs, shallow and
offline failure, merge-preserving success, retained WIP, wrong targets, atomic
receipt conflict, LFS coexistence, and ref-rewrite rejection. The checkout tests
execute the actual embedded verifier against real directories, including a copied
same-revision tree, aliases, tampering, and missing caller roots. Deployment tests
exercise real Git dirtiness and isolate the remote API boundary. These are not a
claim of real production deployment or remote protection enforcement.

Independent CI/security-baseline review, deployment script execution regressions,
remote rejection/positive-integration canary, and package-required broad testing
remain the root integrator's gates. No high/medium risk acceptance is inferred
from this scoped pass.

## Stable-hook follow-up review — 17d0d1e79

Independent readback of `17d0d1e79e86f6bf57395405f7d995d7a7dcca4a`
confirms that the checker is now copied into the shared Git hooks directory,
content drift and symlink destinations fail without overwrite, and installation
publishes complete files with no-clobber links. The new real-worktree test proves
checker survival after the installer worktree is removed. Root reports 21 passing
history tests and verified migration of only its owned wrapper with LFS unchanged;
this reviewer did not repeat the broader suite.

**SEC-HOOK-02 — Medium, open:** the installed shell wrapper still embeds raw
`sys.executable`. An installer invoked with a virtual environment interpreter
inside a disposable task worktree can therefore leave a missing interpreter when
that worktree is removed, despite preserving the checker itself. The current
worktree-removal test invokes the normal test interpreter and does not construct
that state. Select and validate a durable base/system interpreter, and retain a
real virtual-environment removal regression (including a copied interpreter,
where resolving a symlink alone is insufficient). No owner acceptance is implied.

Updated scoped gate: **HOLD for the worktree-lifetime claim** until SEC-HOOK-02 is
closed. The prior receipt, mount, and deployment conclusions remain unchanged.

## SEC-HOOK-02 closure — durable interpreter re-review

**Resolved; scoped security gate restored to PASS.** Independent readback of the
final installer confirms that it selects `/usr/bin/python3`, verifies Python
3.10 or newer in isolated mode, and refuses a resolved interpreter inside any
registered worktree. The wrapper invokes that durable interpreter with `-I` and
the stable checker copy under the shared Git hooks directory. It no longer
captures the installer's virtual-environment executable or imports through the
caller's Python environment.

The retained real-Git regression now installs from a virtual environment inside
a disposable worktree in both `--copies` and `--symlinks` modes. After removing
the worktree and its environment, it proves ordinary commit/push and receipt
creation still work, the rewind guard still rejects master loss, and installer
readback still matches. Reviewed `/tmp/integration-history-stable-python-tests.log`:
**22 passed, 2 warnings in 21.30s** through wctl's verified checkout. No additional
broad suite was run by this reviewer.

The source change and direct failure-class coverage close the only outstanding
medium finding from the stable-hook follow-up. No open high/medium findings remain
in this review's M1/M2/root deployment-consumer scope. Bootstrap merge may proceed
subject to the separate CI review and root integration gates. Remote enforcement,
production deployment, and operating-system interpreter administration remain
outside this source-level sign-off.

## M2 sparse-checkout follow-up review

**Scoped PASS.** Independent readback confirms the follow-up repairs the observed
sparse-worktree selection failure: absence of the two physical WEPPpy marker files
no longer automatically selects the installed checkout. At a discovered `.git`
boundary, the helper checks tracked index paths, then committed HEAD paths so a
staged deletion does not disguise a WEPPpy checkout. Unrelated and unborn Git
repositories retain the documented installed-preset fallback, while failed Git
inspection raises an explicit error before the container test command.

The new subprocess is local and read-only, removes ambient `GIT_*` selectors and
configuration, disables replacement objects and optional locks, uses argument
lists rather than shell interpolation, and has a ten-second timeout. Checkout
selection now occurs within the command wrapper's existing error-handling boundary.
The nonce probe still verifies the selected live tree before pytest starts.

Reviewed the real sparse linked-worktree regression, staged-marker deletion,
unrelated/unborn fallback, ambient selection, and broken Git-metadata cases in
`tools/wctl2/tests/test_checkout_identity.py`, and read
`/tmp/wctl-sparse-checkout-tests.log`: **16 passed in 1.22s** across checkout identity
and Python command tests. The sparse case explicitly proves that the canonical
mounted checkout is rejected when the caller requested the sparse worktree.
No additional broad suite or production operation was performed for this review.

No new high/medium finding was identified in this M2 correction. Its acceptance is
source-level and scoped; follow-up PR policy checks, exact-source integration,
and remote enforcement evidence remain root integration gates. The separate
positive-canary setup error (an empty-index deletion commit on a disposable branch)
is incident/test-setup evidence, not a successful integration or a master change,
and does not substitute for the positive-canary proof.

## Reference packing follow-up review — Git 2.43 files backend

**Scoped PASS; no new high/medium finding.** The original guard treated Git's
redundant loose-ref pruning as logical branch deletion. The repair allows only a
nonzero full old SHA that matches both the loose master contents and exactly one
committed packed master entry, while the loose master lock exists and neither
packed rewrite lock nor pending packed replacement exists. Symlinked loose,
packed, or loose-lock files and duplicate packed master entries are refused.
Missing or unreadable state does not authorize the exception.

Reviewed the actual transaction traces under
`/tmp/git-ref-transactions-0n2t4qk7/`: packing commits the packed master before a
separate old-SHA-to-zero loose prune; genuine mixed-representation deletion holds
the packed rewrite lock and prepares its replacement. This agrees with the
[Git 2.43 files-backend implementation](https://github.com/git/git/blob/v2.43.0/refs/files-backend.c):
`prune_ref` marks representation pruning, while logical deletion prepares a packed
transaction, and packing releases the packed lock before pruning loose copies.
The exception depends on that supported backend behavior, not on a caller-supplied
"maintenance" flag. It does not authorize master removal or rewind.

The normal loose-ref lock prevents another Git writer from concurrently deleting
that same logical ref while the prune is being prepared. Concurrent packed-ref
maintenance can conservatively cause refusal if a rewrite lock is observed;
that is a retryable availability outcome, not authorization to bypass the guard.
No claim is made against an owner who manually tampers with Git internals or
against unqualified future storage backends.

Reviewed `/tmp/integration-history-pack-refs-tests.log`: **36 passed, 2 warnings
in 26.16s**. The suite exercises real packing, pruning, repeated maintenance and
GC with dirty/index/untracked state preserved; logical deletion across loose,
packed, stale mixed and identical mixed representations using three deletion
forms; and packed-ref rewind refusal.

Independent disposable-repository probes additionally demonstrated that both a
linked worktree and a bare repository can pack/prune master without changing its
SHA, then reject a genuine `update-ref -d` deletion with the expected old SHA.
A separate synthetic predicate probe rejected all three symlink forms and duplicate
packed entries. These probes used only temporary repositories and did not alter
the installed guard or source. Root still owns installation, integration, and
remote enforcement evidence. No full test suite was restarted for this review.

## Native policy reporter repair — implementation author addendum

This addendum records implementation by `ci_security`; independent review of this
repair belongs to `history_controls`, rather than the author of the change.

PR #662 at `edec451e464bdcf2654b5fc696887e568d0c8f21` remained blocked with
`Required status check integration-governance-policy is expected` despite two
successful exact-head custom checks from Actions app 15368. Read-only API evidence:

- Runs `43969385574` and `43969407518` created suites `119032773520` and
  `119032828536` after synchronize and ready-for-review events.
- Both custom checks `133658183168` and `133658322779` attached to the older suite
  `119032773520`. The newer suite had successful evaluator/reporter jobs but no
  custom required check. Its native reporter `133658150965` already had the correct
  candidate SHA and PR #662 association.
- There were no commit statuses with the required name and no merge-ref check
  runs. Both protection contexts still required app 15368 and strict updates.
- Previously merged PR #661 had a single policy suite `119010693037`; its custom
  check `133629567859` belonged to that suite.

The duplicate-suite association is the strongest supported cause of the blocked
merge; GitHub's internal merge evaluation is not exposed by these API results.
The [Checks API](https://docs.github.com/en/rest/checks/runs) does not offer a
check-suite selector when creating a check run. Avoiding custom publication
removes this ambiguous association path.

The repair names the native reporter job `integration-governance-policy`, keeps
`needs: trusted-policy` and `if: always()`, and explicitly fails for every evaluator
result except `success`. The reporter has `permissions: {}`, no checkout, no
provided token, and no API publication. The base-owned evaluator and all four
trigger events remain unchanged. Local tests execute the generated reporter for
success, failure, cancellation, skipped evaluation, and an empty result; wiring
checks cover the required name, dependency, unconditional scheduling, and absence
of a publication token. GitHub suite/merge semantics still require live validation.

Rollout: root adds a new reviewed commit to already-ready PR #662, approves its
exact policy transition, and lets the old base's single synchronize run satisfy
existing protection without a bypass. After merge, a disposable protected canary
must exercise the new base workflow with duplicate events on the same SHA and
confirm native required checks attach to each suite. A deliberately weakened
candidate must fail policy evaluation and its reporter, blocking merge. No remote
settings or check results were mutated by this agent.

Local repair validation: **40 passed, 2 warnings in 10.16 seconds** for
`tests/tools/test_security_baseline.py` and
`tests/tools/test_deployment_governance.py` through `wctl run-pytest`;
`/tmp/governance-native-reporter-tests.log`. Generated workflow consistency,
scoped documentation lint, and Git whitespace checks pass. These results do not
substitute for the root-owned remote canary described above.
