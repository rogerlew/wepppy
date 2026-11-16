# Execution receipt — 2026-11-16

## Authority and decisions

The operator requested execution after reviewing the scaffold. Adopted D1–D5:
merge-preserving integration; scoped task branches with one integrator; PR/check
requirements and administrator enforcement; exact owner-configured policy approval;
separate acceptance/integration/release states and gated publication. Human approval
count starts at zero because no independent reviewer was assigned. Other write
collaborators exist; this is not a claim that the owner is the only contributor.

## Local implementation and evidence

- M1: fresh remote ancestry receipts with no-clobber output, explicit identity,
  immutable observation, shallow/offline refusal, and ambient Git environment
  sanitization. Protected-ref installer preserves existing LFS hooks. Eighteen
  real-Git tests pass, including original 20-commit-loss topology and two-repo
  environment redirection. Installed/check verified locally; no production host
  hook installation is claimed.
- M2: live mount nonce precedes pytest/sharded pytest. Sixty-six wctl tests pass;
  a real wrong-checkout invocation exits 2 before tests and the normal fallback
  invocation succeeds. Existing local shim regenerated. Other installs must
  regenerate the shim when adopting this version.
- Root combined integration/deployment/wctl suite: 152 passed. Policy and deployment
  helper suite: 29 passed before extra protected-input coverage; later checker
  suite: 28 passed. These scopes overlap and should not be added as unique tests.
- Real Rust smoke verifies valid output, feature quota rejection and malformed SHX
  rejection. Generated workflows are in sync using the container Python runtime.
- Full repository pytest is running; its result is not yet claimed.
- Independent implementation reviews are retained for history/CI, correctness and
  security. Local findings were repaired; remote enforcement canaries remain.

## Bootstrap and environmental gates

Remote master before bootstrap: `420e31b97e962dd6ea79694efe89f348c27ef83f`.
The base has no integration checker/workflow. Bootstrap therefore requires the
reviewed checker checksum and exact candidate approval in Actions variables, a
reviewed PR, then a one-time merge before requiring the new base-owned policy check.
This is an explicit bootstrap transition, not a standing bypass.

`remote_settings_before.json` records original settings;
`proposed_branch_protection.json` contains the exact proposed rule. The required
checks are bound to GitHub Actions app 15368. Check names/app identity do not isolate
a deliberately malicious writer using that same app; the documented threat model
covers accidental loss and unreviewed changes, not owner credential containment.

Canary, master activation, final merge receipt and publication results will be
recorded before claiming environmental enforcement. The observation window remains
open for the first five real subsequent integrations plus a recovery drill.

## Recovery and limitations

Local hook refusal preserves the protected ref but cannot undo index/worktree
changes already made by prohibited hard reset/rebase. Stop and recover using saved
refs/WIP; do not retry with hooks disabled. The existing unrelated WIP was backed
up before execution and excluded from task commits.

The full deployment entry point now refuses unvalidated protected source or missing
exact-source CI evidence before builds/stops. Public API access suffices; API failure
blocks deployment. No production service was changed or deployed during this work.
