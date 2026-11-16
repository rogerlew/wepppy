# Recovery drill — 2026-11-16

**Result: PASS.** Completed at 2026-11-16T21:46:24.951604+00:00 by the history-controls sub-agent,
following the canonical standard's “Validation and incident recovery” and
“Operator commands” sections. This completes the separate recovery-drill obligation;
it does not count toward five real subsequent protected integrations.

## Scope and retained evidence

All Git mutations and fixture commits occurred in disposable repositories under
`/tmp/wepppy-recovery-drill-20261116-jerwa0cu`: an operator checkout, an independent peer checkout, and a local
bare remote. No shared WEPPpy refs, index, hooks, configuration, GitHub settings,
registry, running stack, or production services were changed. This artifact is
the only shared-workspace output. Full command/result transcripts, external WIP
backups, repository objects, stash, and receipt remain in that temporary directory.
No hook bypass was used.

| Identity | Full commit |
|---|---|
| Earlier remote baseline | `12408737772933b237ffe2939a29974e9ca2a57e` |
| Accepted local work / retained recovery ref | `04e91d6a5706f231f6f88506b15484631f296707` |
| Independent remote advance | `82a4d6553606c79bbe6b2ea244246901665aa94e` |
| Legitimate merge / observed remote target | `506042b3ade7ef20747b18cec6d41d2545f09d7d` |
| Retained operator WIP stash | `b70fd30327c1f537339ddbbdf32c1c32dc267568` |

The installed tooling was read from `/workdir/wepppy/tools/`:

- Checker SHA256: `5ad9ec0b8b82606c8647c51524067226258b486616a9d516f1cac5b4b559749b`.
- Installer SHA256: `eaa5e97dc7d94955e961e7ef8a83bf73c3faa1f88d56cdf2fbaac00009048279`.

## Procedure and observed results

Initialize the bare remote and two real checkouts; publish an earlier baseline,
then create accepted local work. Before the exceptional destructive-update probe,
retain `refs/recovery/pre-drill` at the accepted commit, save `git diff --binary`
outside the checkout, and back up the untracked operator note. Install the actual
stable guard with `install_integration_hooks.py --repo OPERATOR` and verify it
with `--check`.

Invoke `git reset --hard 12408737772933b237ffe2939a29974e9ca2a57e` **only in the disposable operator checkout**.
It exits `128` with `PROTECTED_MASTER`. Master and the recovery ref
still identify the accepted commit. The experiment confirms the documented limit:
Git has already overwritten the unrelated tracked WIP before the ref refusal.
The untracked note survives. Stop after refusal; do not retry or disable the hook.

Recover accepted tracked state and saved work with:

```bash
git restore --source=refs/recovery/pre-drill --staged --worktree -- .
git apply ../backups/tracked.patch
```

Readback verifies the accepted parser fixture content, the exact unrelated tracked
WIP bytes, the exact untracked note bytes, and the original `git status --porcelain`.
The accepted ref alone did not recover uncommitted work; the external WIP backup
was required and successfully consumed.

Preserve this recovered work with `git stash push --include-untracked`, retaining
the stash. Publish an independent peer change to the disposable remote; fetch it
in the operator checkout and integrate with `git merge --no-ff origin/master`.
Push the merge without force. Apply the retained stash with `git stash apply --index`.
Direct content readback and exact porcelain comparison prove unrelated tracked
and untracked work is restored. Both accepted and peer commits are ancestors of
the merged remote target. Re-check the installed guard; it remains valid.

Create and verify a fresh receipt using the real checker with the explicit expected
remote target:

```bash
python3 /workdir/wepppy/tools/check_integration_history.py receipt \
  --repo OPERATOR --accepted 04e91d6a5706f231f6f88506b15484631f296707 \
  --expected-remote-sha 506042b3ade7ef20747b18cec6d41d2545f09d7d --output RECEIPT.json
python3 /workdir/wepppy/tools/check_integration_history.py verify \
  --repo OPERATOR --receipt RECEIPT.json \
  --expected-remote-sha 506042b3ade7ef20747b18cec6d41d2545f09d7d
```

Both commands succeed and leave the recovered WIP unchanged. The receipt readback
is retained here so the proof does not depend solely on temporary files:

```json
{
  "accepted_sha": "04e91d6a5706f231f6f88506b15484631f296707",
  "branch": "master",
  "claim": "remote_integration_snapshot",
  "integration_mode": "merge-preserving",
  "observed_at": "2026-11-16T21:46:24.210563+00:00",
  "observed_remote_sha": "506042b3ade7ef20747b18cec6d41d2545f09d7d",
  "remote": "origin",
  "repository": "/tmp/wepppy-recovery-drill-20261116-jerwa0cu/remote.git",
  "schema_version": 1,
  "validation_scope": "ancestry-only; not behavioral acceptance or release approval"
}
```

## Limits

This is a local Git recovery drill, not an additional GitHub enforcement canary,
production rollback, or full application test. It deliberately exercises the
hard-reset side effect; the standing rule still prohibits routine shared-master
reset/rebase. Recovery depends on keeping accepted refs and separate WIP backups
before an exceptional operation. The ancestry receipt proves remote historical
inclusion at the observation time, not semantic validation or release eligibility.
The five-real-integration observation and full regression result remain separate
obligations and are not satisfied by these fixture commits.
