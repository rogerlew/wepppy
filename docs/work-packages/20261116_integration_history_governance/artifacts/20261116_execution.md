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
  helper suite: 34 passed after final protected-input and environment coverage. These scopes overlap and should not be added as unique tests.
- Real Rust smoke verifies valid output, feature quota rejection and malformed SHX
  rejection. Generated workflows are in sync using the container Python runtime.
- Full repository pytest is running; its result is not yet claimed.
- Independent implementation reviews are retained for history/CI, correctness and
  security. All identified medium/high findings were repaired and independently
  re-reviewed; remote enforcement evidence is recorded below.

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

Canary, master activation, final merge receipt and publication results are
recorded below and in adjacent JSON artifacts. The observation window remains
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
security review accepts it. PR #661 integrated it through the newly enforced PR
boundary with both required checks passing.

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

Bootstrap publication run43958588430 attempt2 completed successfully. Registry
readback of `ghcr.io/rogerlew/wepppy:sha-98017d78981ec8c43ad14bd8faf9846cdb2d4928`
returned index digest
`sha256:94964fa14981277487f02a684fee7115f4cc724699054163f43fab81f852b707`;
its OCI revision label matches the exact merge SHA. See `publication_readback.json`.
This is normal artifact publication, not production deployment.

## Protected integration and cleanup

[PR #661](https://github.com/rogerlew/wepppy/pull/661) preserved accepted source
`dff9eba283a2767c9c776cd4d12d81f9b18b91dd` in merge
`d3b0effbc26f0ca04f5f11e8c14982bfbf1b3c54`. Both required checks passed on the
source; the merge was accepted under the live administrator-enforced rule.
`enforced_integration_receipt.json` independently fetches remote master and proves
accepted ancestry. The history reviewer independently read back checks, PR state,
settings and ancestry after integration.

The first merge-push governance attempt rejected the stale PR-head approval as
designed. After explicit approval of the reviewed merge SHA and unchanged policy
digest, run43961539583 attempt2 succeeded. Publication run43961539621 attempt2
completed successfully. Registry readback confirms source revision d3b0effbc and
index digest `sha256:3cd337199548c54ee61a0a7c8c7dd002e262e9c74531da63e5cb4dcd81200706`
(`publication_readback.json`).
Automatic transfer of a PR-head approval to an unobserved merge is not permitted.

`canary_cleanup.json` records removal of disposable remote branches/protection and
clean task worktrees. Local recovery refs and prior incident backups remain. All
preexisting unrelated WIP is excluded from implementation/audit commits. The
tracked unrelated diff (AGENTS, project tracker, three contracts and management
JSON) was byte-identical to `/tmp/governance-unrelated-wip.patch` at final audit
preparation. Generated docs index remains ignored; unrelated untracked paths remain.

## Regression scope

The full application suite started before the final narrow installed-hook and
sparse-checkout refinements. Those final paths were independently rerun through
22 real-Git and 16 checkout cases; the final policy/deployment scope passed 34.
The initial combined 152 and initial wctl 66 scopes overlap these results; counts
are not additive. The full run validates the shared working tree, including
preexisting unrelated edits, rather than an immutable clean checkout. No domain
application code was changed by the governance refinements. Final full-run result
is pending; no pass is claimed here yet.

## Recovery drill

The [independent disposable recovery drill](20261116_recovery_drill.md) passed.
It demonstrated protected-ref refusal, actual pre-ref tracked-WIP overwrite,
recovery from retained accepted refs plus external WIP backup, and legitimate
merge integration with exact tracked/untracked work restored. Fresh remote receipt
and verification succeeded. This fulfills the separate recovery drill; fixture
commits do not count toward the five-real-integration observation.

## Maintenance correction discovered during audit

Automatic Git maintenance exposed a false positive: files-backend `pack-refs`
reports pruning the redundant loose master ref as SHA-to-zero, so the original
hook refused it as logical deletion. The audit commit/push succeeded, but normal
maintenance failed. This was repaired before handoff, not waived.

The guard now permits only the verified storage transition: matching old SHA in
both loose and packed entries, a loose-ref lock, and no packed rewrite lock/new
state. Symlinks, duplicate entries and unknown layouts fail closed. Actual branch
deletion remains blocked for loose, packed and mixed refs. Independent security
review checked Git 2.43 source and real bare/linked probes. The final suite passes
37 real-Git tests, including maintenance and actual deletion/rewind coverage.

The previous owned hook/checker were backed up in
`/tmp/governance-pre-pack-refs-fix-hooks`, then the reviewed guard was installed
and checked. Installed checker SHA256:
`d9240304432c45256733c386fbc56e87071ef95bc13a7ec43a52bfb27d97a438`.
Real shared-checkout `git pack-refs --all --prune` succeeded with byte-identical
`git show-ref` output; unrelated hooks remained byte-identical. No force update,
hook bypass, or production mutation was used.
