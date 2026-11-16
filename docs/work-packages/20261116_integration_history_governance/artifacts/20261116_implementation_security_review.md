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
