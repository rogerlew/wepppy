# M0 operations review - Dependency security gate

**Review time**: 2026-11-11 05:11 UTC  
**Reviewer**: independent wepp1 operator agent  
**Source**: `2041fb8e267de3a1572d9fb4f4a62e725b75cc91`, local dirty worktree  
**Environment**: local `forest`, `/workdir/wepppy`; no SSH or production action  
**Verdict**: design recommendation with prerequisites; not owner approval,
implementation acceptance, or production qualification.

## Confirmed control flow

`scripts/deploy-production.sh` derives build and recreation sets from rendered
Compose, refreshes them after pull, and serializes deployment with a local lock.
The future gate must inspect that resolved set and immutable local image IDs,
not assume the common image is always named `wepppy:latest` or selected through
the `weppcloud` service.

The insertion point is after the build/targeted-selection block (currently
lines 941-984), before Step 3 (line 998). Prefer placement before CAP's
`--secret-only` preparer at line 995 so a scan failure also avoids that unrelated
runtime preparation. This precedes all normal-path stop/down/recreate commands,
including worker/fork-archive warm shutdown and the later full-stack cutover.
The CAP recovery trap does not recreate CAP before `CAP_ACTIVATION_STARTED` is
set, which happens later at activation. Preserve this ordering and trap behavior.

| Deployment path | Gate implication |
| --- | --- |
| Full stack | Gate each selected common-image identity; preserve dependent fcgiwrap build ordering and separate CAP/WEPPcloudR validations. |
| Targeted web | Builds common image through `weppcloud`, recreates `weppcloud` and `rq-engine`; gate applies. |
| Targeted CAP | Builds/recreates only CAP; common-image gate must not block this unrelated repair. |
| Targeted batch overlay | `build_source_overlay.py` creates an image from an immutable baseline and retags the resolved batch image; assess the actual selected image rather than skipping on the flag alone. |
| Targeted batch rollback | Verifies a retained image ID; its policy treatment must be explicit and cannot become an implicit stale-evidence bypass. |
| Worker/fork-archive presets | Discover the common image through rendered Compose; these paths need no `weppcloud` service. Scope applicability must be explicit before enabling across presets. |

The existing `--skip-build` path rejects locally built services selected for
recreation. Do not weaken that check to accommodate scanning. The development
baseline is not equivalent to wepp1's build identity: the wepp1 overlay declares
APP_UID 1002 and APP_GID 130, while local tests currently use the dev image.

## Findings and required acceptance evidence

1. **High integration risk: retry wrappers can mask failures.** Both
   `run_wctl_with_retry` and `capture_wctl_with_retry` assign `exit_code=$?`
   after a failed `if` statement without an `else`. A harmless local Bash
   reproduction, `if false; then :; fi; rc=$?`, yielded zero. Call the new
   evidence/policy interface directly with explicit failure propagation. Record
   the existing wrapper defect separately or repair its confirmed consumers
   under the failure-class standard; do not route the gate through it unchanged.

2. **Medium design gap: image selection and rollback.** A mode-only condition
   could skip the batch-derived common image or gate unrelated CAP. Finalize
   selection by rendered image/build definitions and candidate identities, with
   explicit retained rollback treatment. Recheck the selected tag-to-ID mapping
   immediately before activation, and verify running containers consume that ID.
   The deployment lock prevents cooperating deploys, but does not prove an
   external tag writer cannot change it during a long scan.

3. **Medium qualification gap: protected evidence and resource capacity.**
   `DEPLOY_STATE_DIR` defaults to `/var/tmp`, not a private directory. Create a
   dedicated 0700 child and 0600 evidence files. Prove actual operator ownership,
   free space for image archives/database/reports, failed-run cleanup, and
   retention behavior before activation. Do not prune rollback images or unrelated
   evidence. The proposed 90/365-day retention and 24-hour freshness are pending
   owner decisions and storage validation, not operationally approved limits.

4. **Medium qualification gap: failure preserves service availability.** Extend
   `tests/scripts/test_deploy_production_execution.py` using its existing fake
   command ledger. Require nonzero exit with no stop/down/up command, no CAP
   activation, and no RQ suspension for missing tool/database, schema mismatch,
   image mismatch, stale evidence, and blocking findings. Exercise full, web,
   worker, batch-derived, rollback, and excluded CAP paths. Also retain the
   unmocked scanner/disposable-image trial; fake control flow alone cannot prove
   scanner filesystem, permissions, coverage, or database behavior.

## Recommendation and remaining authority

The proposed shared CI/deploy policy interface and archive-only scanner boundary
fit the existing host-local Compose workflow. Keep the current pull/build,
static assets, RQ fence, CAP rescue, health, and targeted scope contracts. A
failed scan should return before any cutover work and report the private receipt
location without dumping rendered environment or secrets.

Before M0 acceptance, retain green mandatory pre-change gates, completed scanner
qualification, independent correctness/security review, and owner ratification
of concrete thresholds, exceptions, retention, and rollback behavior. No policy
exception or deployment authorization is granted by this review. M3/M4 require
implementation-specific re-review and production-equivalent identity/mount
evidence; M5 remains separately authorized.

Only source inspection and the harmless Bash status reproduction were performed
for this review. No full test, scanner, deployed runtime, or production recovery
result is claimed here.
