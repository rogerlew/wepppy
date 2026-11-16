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
