# Independent implementation review: checkout identity and CI trust

Date: 2026-11-16 (UTC). Reviewer: history_controls sub-agent.
Scope: M2 checkout identity and M3 governance/publication implementation; M1 code
was written by this reviewer and is excluded from independent approval here.
Initial verdict: **HOLD — M3 trust-boundary finding requires repair and canary**.
This is an in-progress review; it is not acceptance of unfinished controls.

## Findings

### H1 — High: candidate workflow can bypass its own trusted-checker selection

The initial `.github/forest_workflows/integration-governance.yml` loads a checker
from a trusted base, but its invocation is still selected by candidate-controlled
workflow YAML. Replacing that job with a same-named successful no-op prevents the
checker from executing. Listing the YAML itself in `PROTECTED` is insufficient
when no trusted actor runs the comparison. Required check name alone does not
prove the trusted workflow ran.

Fix: execute policy evaluation from a genuinely base-controlled workflow or
another independently enforced mechanism. Prove that a candidate deleting or
replacing the governance workflow cannot satisfy integration. If posting custom
check results, verify their association with the exact candidate and investigate
whether another same-repository workflow can spoof the same check name/application.
Keep candidate execution separate from any token permitted to write acceptance
results. Required-rule support and actual rejection evidence are closure gates.

Root and CI implementer have been notified; a base-owned evaluation approach is
under investigation. No fixed verdict is claimed yet.

### M1 — Medium: installed shim migration is part of checkout protection

`wctl/install.sh` now captures `WCTL_CALLER_CWD` before changing directories.
An old installed shim does not supply this information; once it changes to the
preset project, the verifier cannot reconstruct the original task worktree from
its cwd. Regeneration of installed shims is therefore part of wiring, not merely
an optional packaging detail. Root reports the current shim has been regenerated;
retain actual correct/mismatched Docker canary evidence before claiming environment
validation. Other installations must receive the same update.

## M2 static correctness assessment

The nonce probe is a narrow and appropriate way to prove the selected host checkout
is the live container mount. `requested_checkout` prioritizes explicit selection,
then caller ancestry, then installed preset. `checked_test_command` creates a random
readable marker, checks it before launching tests, and cleans it on exit. Aliased
paths can pass; separate copies at the same commit fail, including caller dirty
source. The implementation explicitly does not freeze source against concurrent
edits, so serialized validation/integration ownership remains required.

Read `tools/wctl2/tests/test_checkout_identity.py` and modified command tests.
Local subprocess tests execute the actual embedded probe but substitute the mount
path; they are useful unit evidence, not the real Docker acceptance boundary.
No independent broad tests were run concurrently with root validation.

## Bootstrap clarification

An initial concern that bootstrap expected `420e31b97` while local HEAD was
`8a159aaed` was withdrawn after root clarified the latter is the task branch and
remote master remains `420e31b97`. This is not an open defect. A newly introduced
base-owned workflow still needs a documented initial activation/bootstrap procedure
before its status can become a required check.

## Remaining acceptance evidence

- Candidate workflow deletion/replacement cannot self-approve integration.
- Acceptance is tied to exact candidate and trusted workflow execution; spoofing
  and stale-success cases cannot satisfy the required gate.
- Registry writers are downstream of verified exact-candidate acceptance.
- Current wctl shim admits the actual mounted checkout and rejects a separate
  task checkout before tests start, preserving both worktrees.
- Independent reviewer other than this author validates M1 receipt and hook code.

## M2 evidence update

The M2 implementer reports 66 wctl tests passing through the canonical wrapper,
a live installed-shim mismatch canary exiting `2` before pytest, and probe cleanup.
Invocation outside a checkout still reaches the preset and reports pytest version;
canonical mounted-checkout tests pass. This reviewer read the implementation and
tests independently but did not rerun the implementer's canaries. M1 above is
resolved for the current installation, with migration of other installed shims
remaining an explicit rollout requirement. M2 has no remaining static blocker
within the stated accidental-mismatch and serialized-validation scope.

## M3 repair review

Re-read the repaired canonical `integration-policy.yml`, behavioral workflow,
`tools/check_security_baseline.py`, publication consumers, and their tests.
The separate `pull_request_target` policy workflow checks out the trusted base,
fetches candidate objects without checking out or executing candidate code, and
compares protected blobs using the base checker. Its separate checkout-free
report job has `checks: write` and records the exact PR head; the comparison job
has only read authority. Both policy and behavioral contexts are intended to be
required. This statically repairs H1 for accidental candidate workflow deletion
or replacement; actual GitHub check association and rejection remain canary gates.

The policy now protects the newly introduced checkout-identity helper and its
tests, closing the initially identified possibility of weakening the helper
without changing its protected caller. Publication jobs depend on a hosted
read-only eligibility job that requires a successful push workflow for the exact
source SHA. Unknown, unfinished, or failed run evidence does not permit publication.

A concern about unauthenticated fetch on a private remote was withdrawn after
the CI implementer reported fresh GitHub API readback of this repository as public.
Private repository support is not claimed; a visibility change must fail closed
and receive explicit integration work rather than silently adding credentials.

Deliberate same-application check forgery by a writer allowed to run arbitrary
GitHub Actions remains outside this accident-prevention boundary. A required
check name/application is not cryptographic proof of workflow identity; retain
this residual explicitly and do not claim hostile-writer containment.

Revised verdict: **No remaining static code blocker within the stated scope;
environmental acceptance remains pending the live workflow-removal rejection,
required-check association, bootstrap, publication, and recovery evidence.**
M1 remains excluded from independent approval by this reviewer.

## CI repository-selector repair readback

Re-read the CI checker's `git_environment()` and bounded Git helper after the
root reviewer reproduced ambient Git environment redirection. Explicit `--root`
is now authoritative: inherited repository, worktree, index, object-store,
alternate, namespace, shallow-history, and config override selectors are removed;
replacement objects are disabled and Git operations have a 60-second timeout.
The implementer reports a real two-repository regression and 34 checker/deploy
tests passing. This resolves the static repository-selection concern for the
reviewed CI helper. No broader enforcement claim follows from that local result.

## Final environmental review

Independent read-only review on 2026-11-16 confirms the live master protection
and retained canary evidence. GitHub API readback requires both
`integration-governance` and `integration-governance-policy`, each bound to Actions
app `15368`, with strict up-to-date checks and administrator enforcement.
Force-push and deletion are disabled. PR association is required with zero human
approvals, as adopted; this is not independent human review. Repository readback
permits merge commits and disables squash/rebase merges. The repository is public.

Direct API readback of [PR #661](https://github.com/rogerlew/wepppy/pull/661)
confirms its merge at `d3b0effbc26f0ca04f5f11e8c14982bfbf1b3c54`, preserving
reviewed head `dff9eba283a2767c9c776cd4d12d81f9b18b91dd`. Both required checks
succeeded on that exact head under app `15368`. Remote master readback matches the
merge, and local `git merge-base --is-ancestor` confirms preservation. The retained
`enforced_integration_receipt.json` agrees with these independent observations.

For [negative PR #658](https://github.com/rogerlew/wepppy/pull/658), independent
check-run readback confirms the candidate's no-op `integration-governance` succeeded
while the base-owned policy failed on the same head `98d5aa60e11a62cb78cb741372bdde3265cf9376`.
The PR remains closed and unmerged. `canary_rejections.json` retains rejection by
both the merge API and direct push under the tested canary protection. This closes
H1's environmental gate for the stated accidental/unreviewed weakening scenario.

[Positive PR #660](https://github.com/rogerlew/wepppy/pull/660) is recorded as
merged at its exact green head `aefdbecefa8fba2ec2b3cf67f4e461151f12e996` after a
fast-forward push. The demonstrated guarantee is **PR-associated, check-gated
integration**, not merge-button/API-only transport. A separate commit without PR
association was rejected while status checks were disabled on the disposable canary
only, isolating the PR requirement; `canary_no_pr_rejection.json` and
`canary_protection_restored.json` retain the rejection and restored complete rule.

[PR #659](https://github.com/rogerlew/wepppy/pull/659), created by the empty-index
canary setup mistake, is independently confirmed closed and unmerged. It is a
retained setup failure, not positive acceptance evidence. `canary_cleanup.json`
records removal of temporary protection, remote branches, and clean disposable
worktrees. No remote writes were performed by this reviewer.

**Environmental verdict: PASS for the tested master integration controls and
history-preservation boundary.** Local/remote evidence now supports implemented,
wired, and environmentally enforced status for those controls. The receipt is an
ancestry snapshot, not a behavior or production deployment attestation. This
verdict does not claim full application regression success, completed image
publication, hostile-writer containment, other-host hook rollout, or package
closure. Full pytest is still running, and five future real integrations remain
an open operational observation obligation; bootstrap/canaries do not satisfy it.

## Final regression repair review

Independently reviewed the workflow-generator resolver repair and deployment-plan
fixture/side-effect repair. The generator now deep-copies inherited resolver maps
for both its loader and dumper before removing workflow-specific boolean rules.
This preserves the intended workflow parsing while avoiding shared PyYAML mutation.

Independent fresh-process readback reproduced the original source as
`bool-type=str shared-map-preserved=False` after importing the generator, and the
fixed source as `bool-type=bool shared-map-preserved=True`. The new regression
runs the actual generator in a fresh subprocess, outside the old isolating fixture,
and checks both parent resolver maps, normal true/false loading, default dumping,
workflow `on`/string-boolean semantics, and roundtrip. It therefore detects the
shared-state defect rather than only asserting the implementation's copy calls.
Independent `/usr/bin/python3 scripts/build_forest_workflows.py --check` exits zero
with generated output unchanged. The existing README profile-section warning is
not a generated-workflow mismatch.

The plan fixture now supplies the actual installed-preset query and records
forbidden Git/Docker/network/non-query-wctl/non-contract-Python activity, including
negative cases whose nonzero exit alone could previously hide the wrong failure.
The new wepp3 plan case exposed a real production side effect: the old
`validate_deploy_topology` started a secret-readability container during
`--print-plan`. Its retained red run failed on that exact invocation. The repair
adds only `PRINT_PLAN=false` to that preflight condition; real deployment retains
the secret check. Execution coverage verifies governance precedes the secret
probe and build, and failed governance prevents the probe for full/wepp3 variants.
Independent shell syntax and changed-file whitespace checks pass.

Static verdict: no remaining implementation blocker for these narrow repairs.
The repaired test suites' final results are recorded below once available; this
review does not convert the earlier failed full-suite attempts into passing runs.

### Final repair validation receipt

Read the completed logs independently:

- `/tmp/governance-yaml-coupled-tests.log`: **559 passed in 41.97 seconds**.
  The security/workflow tests and all affected feature-registry, pure-controls,
  and Usersum modules run in the same process in that order. This closes the
  33 downstream failures attributed to the generator's global resolver mutation.
- `/tmp/governance-deploy-plan-execution-tests.log`: **77 passed in 105.37 seconds**.
- `/tmp/governance-deploy-governance-boundary-tests.log`: **2 passed in 9.47 seconds**
  after adding the explicit assertion that failed governance invokes no secret
  readability probe for either full or wepp3 topology. These two cases overlap
  the preceding execution suite and must not be added as unique coverage.

**Final regression-repair verdict: PASS.** The reviewed generator repair preserves
workflow output and normal YAML semantics; the plan repair aligns the fixture with
current preset discovery and keeps actual `--print-plan` read-only while retaining
real-deployment preflight ordering. No remaining blocker was found in these changes.
This targeted evidence does not erase the failed broad-suite attempts or classify
unrelated baseline failures as passing; the regression-disposition artifact retains
those outcomes separately. No source, index, or installed-hook edits were made by
this independent reviewer during this review.

## Native policy reporter repair review

A later real merge refusal exposed a coverage limit in the earlier environmental
verdict: duplicate PR-target events on one head created multiple workflow suites,
but the custom Checks API reports attached to the older suite. Independent API
readback for PR #662 head `edec451e464bdcf2654b5fc696887e568d0c8f21` confirmed
custom required checks `133658322779` and `133658183168` both in suite
`119032773520`, while native reporter `133658150965` correctly belonged to newer
suite `119032828536`. All were app `15368` and successful on that same head;
therefore a green custom check was insufficient evidence of current-suite coverage.

Reviewed the canonical/generated workflow, test changes, and canonical standard.
The repaired native job is named exactly `integration-governance-policy`, depends
on the trusted evaluator, uses `if: always()`, and exits nonzero unless the evaluator
result is exactly `success`. It performs no checkout or candidate execution, has
`permissions: {}`, and removes the token, custom Checks API call, and hand-built
check association. The base-owned evaluation boundary remains unchanged. This is
a smaller and less privileged implementation than repairing custom suite selection.

The meaningful reporter test executes the actual generated workflow script for
success, failure, cancellation, skipped, and empty results; only success passes.
Wiring assertions also retain the base-only checkout, trusted dependency,
always-run condition, required native name, and absence of check-write/API paths.
Read `/tmp/governance-native-reporter-tests.log`: **40 passed in 10.16 seconds**.
Independent generated-workflow `--check` passes, with only the preexisting README
profile-section warning. No source/index/remote mutation was performed by this
reviewer.

**Static repair verdict: PASS; duplicate-event environmental proof remains open.**
Integrate the repair normally using the existing base workflow, without disabling
protection, then test a disposable protected canary whose base contains the repair.
Create one harmless draft PR and mark it ready without changing its head, producing
opened/ready events. Retain both target run IDs, suite IDs, exact head and app IDs;
require a native required check in each corresponding suite, latest-suite eligibility,
and accepted integration without settings bypass. Separately retain a candidate
workflow-weakening rejection with the native policy result failing and merge/direct
push refused. Cleanup and rule readback must follow. These canaries do not count as
real operational-observation integrations. The existing deliberate same-app forgery
residual is unchanged and is not solved by native check association.
