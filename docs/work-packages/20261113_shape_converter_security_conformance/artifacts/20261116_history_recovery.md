# Rust parser history recovery — 2026-11-16

## Cause and recovered history

The local reflog records a rebase onto `ff1740239` at 2026-11-15 17:04:45 PST.
It replayed the soils commit as `7755822d7`, but omitted the 20 commits in
`19c0dc107..4194fd43b`. Consequently master at `97e4d7600` lacked the accepted
Rust parser despite issue #656 being closed.

Merge `a5d9f0fc30f64b4ab5446dd7aee6dbb74c6d41df` restores the original history,
including implementation `a6be89141c234727bb5d89aa5a4b3c2ec51dc284` and closure
`4194fd43bf937ebe5675079acf3ddadc537d0a1e`, while retaining newer master changes.
The parser directory, shape tests, and dedicated Dockerfile match the accepted
tip byte for byte. The restored specification includes the operator decision
to use a bounded Rust CLI without adding a second sandbox.

Recovery used a detached worktree and a merge, with no history rewrite. Original
commits are additionally pinned by `refs/recovery/shape-rust-pre-rebase-20261114`
and `/tmp/wepppy-shape-rust-pre-rebase-20261114.bundle`. Unrelated tracked work
was saved and reapplied; untracked files were left in place. The workspace
snapshot remains under `refs/recovery/pre-rust-recovery-workspace-20261116` and
its stash, with a full tracked diff in
`/tmp/wepppy-pre-rust-recovery-worktree.patch`.

## Integration repair

Merge conflicts were limited to the deployment script and its execution tests.
The merge retains newer RQ control selection and restored parser build-failure
handling. Scoped tests then exposed a behavioral conflict: newer retained-image
rollback would restart the old parser, while restored fail-closed policy
requires it to remain stopped.

Recovery now explicitly selects retained services other than shape-converter,
uses `--no-deps`, and excludes the deliberately stopped parser from retained
health checks. Other workloads still require image, health, and worker
registration verification before RQ resumes. Failure to verify parser shutdown
returns `88` and retains the fence. Regression assertions cover service
exclusion, dependency suppression, recovery ordering, and no resume on failed
parser shutdown. The operator contract is in
`docs/infrastructure/shape-converter-fail-closed-recovery.md`.

## Validation

- Locked release build succeeds; all 5 Rust tests pass.
- `wctl run-pytest tests/shape_converter -q --maxfail=3`: 296 passed.
- `wctl run-pytest tests/scripts/test_deploy_production_execution.py
  tests/docker/unit/test_project_config_rollout_contract.py
  tools/wctl2/tests/test_cli_smoke.py --maxfail=1 -q`: 76 passed, 3 skipped.
- Focused parser-stop and combined rollback-failure regressions each pass.
- All four changed Markdown files pass scoped documentation lint.
- Broad-exception changed-file enforcement against `origin/master`: PASS.
- Shell syntax and Git whitespace checks pass.

The recovery preserves historical exact-image qualification evidence; it does
not claim a new production deployment or new image qualification. Production
rollout remains separately authorized and subject to the restored release gates.
