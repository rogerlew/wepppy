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
  sanitization. Protected-ref installer preserves existing LFS hooks. Twenty-two
  real-Git tests pass, including original 20-commit-loss topology and two-repo
  environment redirection and survival after copied/symlinked installation venv
  removal. Stable installed checker and system interpreter are verified locally;
  existing LFS hooks remain byte-identical. No production host
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

## Live bootstrap and canary progress

PR #657 merged as `98017d78981ec8c43ad14bd8faf9846cdb2d4928`, preserving accepted
source `2edde3e35c6f4aed62f596f6c3feb9a4cc56eebd`. The first push check correctly
rejected the PR-head-only approval; publication run 43958588430 failed eligibility
and skipped its publish job. After exact merge approval, governance run43958588392
attempt2 succeeded and live publication eligibility was read back.

Negative PR #658 replaces the behavioral workflow with a green no-op. That check
passed, but base-owned `integration-governance-policy` failed. With the proposed
rule installed on `governance-canary/20261116`, GitHub rejected both merge API
(HTTP405, failing required policy check) and direct push (GH006). See retained
`canary_protection.json` and `canary_rejections.json`.

Positive test setup initially failed: `--no-checkout` left an uninitialized index,
and non-fail-fast shell continuation created empty-tree commit `14a44dbf9` on a
disposable branch. PR #659 was closed without merging. Remote master and canary
base both remained98017d789; no production/default source was changed. The replacement
positive PR #660 was built from a fully initialized index, with exact index/HEAD
and one-file staged-diff assertions. This setup error is not counted as positive
enforcement evidence. Dependent mutation commands now fail fast.

The setup also exposed a real sparse-checkout identity gap: missing physical
wctl markers could fall back to the installed checkout. A follow-up correction
uses sanitized Git index/HEAD inspection; 16 focused cases pass and independent
security review accepts it. It will enter master through the newly enforced PR
boundary, not a bypass.

## Environmental enforcement

The positive PR #660 passed both checks. A fast-forward push of its exact green
head was accepted, and GitHub recorded the PR as merged at
`aefdbecefa8fba2ec2b3cf67f4e461151f12e996`. This is GitHub's PR-association semantics,
not a guarantee of merge-button/API-only transport. A separate harmless commit
with no PR association was rejected with GH006/"Changes must be made through a
pull request" while canary status checks were temporarily disabled; the complete
rule was restored in a finally block. See `canary_no_pr_rejection.json` and
`canary_protection_restored.json`. PR #659's accidental empty-tree candidate also
received a failing trusted policy result and remained closed/unmerged.

On 2026-11-16, the tested protection was applied to master and read back:
`master_protection_readback.json`. It requires PR association and both checks
bound to Actions app15368, strict up-to-date status, administrator enforcement,
and no force push/deletion. Squash/rebase UI/API merges are disabled; merge commits
remain enabled (`merge_settings_readback.json`). Human required approvals remain
zero as explicitly adopted; no routine bypass actor was added.

Bootstrap publication run43958588430 attempt2 passed eligibility and proceeded
through the existing publishing workflow. This is normal artifact publication,
not production deployment. Exact completion and image evidence remain to be read.
The follow-up sparse-checkout correction must now demonstrate legitimate integration
through protected master. Full repository pytest continues; no pass is claimed yet.
