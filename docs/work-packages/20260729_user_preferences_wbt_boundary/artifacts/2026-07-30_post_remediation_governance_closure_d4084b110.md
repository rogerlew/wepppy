# SURF-14A Post-Remediation Governance Closure Review

## Metadata

- **Reviewer**: independent governance/correctness control agent
- **Date**: 2026-07-30 UTC
- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Git base**: `b1f1f99c8f808528315abce001a70200ab068bc7`
- **Requested staged fingerprint**:
  `d4084b110a48b2ab3272f857ba6e8010511fb84aeda7eb590a64a6aadb86b186`
- **Reviewed contract/source/test fingerprint, excluding work-package
  documentation**:
  `c4d047f3baf7ad48ad924c70df1b1744192b0f641cb2b9d7ef64b86479fd88b7`
- **Forest, production, or product mutation by this reviewer**: none
- **Break-glass basis**: none requested or used

This artifact is additive. It preserves the earlier source-freeze PASS reviews
and post-acceptance FAIL reviews without revising their evidence or verdicts.
The requested full staged fingerprint was independently reproduced at review
entry. It was superseded during this review by documentation correction and
then by additional cleanup remediation; those later states are prospective and
are not approved by this artifact.

## Verdict

**FAIL — SCOPE-REDUCE. REJECT Forest and release progression for the exact
`d4084b110` fingerprint.**

**Open findings**: 2 High, 2 Medium.

The user-scoped Unitizer/WBT behavior, strict positive numeric Create subject,
and bounded filesystem cleanup implementation are directionally sound.
However, the reviewed state adds a new public failed-create recovery field
without the repository's mandatory pre-implementation contract ancestor, and
its corrected acceptance cleanup omitted working-directory cache state. The
exact fingerprint also ceased to be the frozen staged state before the
test-isolation gate became terminal.

No finding authorizes weakened identity validation, an undocumented public
error field, destructive broad cleanup, or Forest action.

## Findings

### GOV-PR-01 — High: the public recovery receipt lacks its required contract ancestor

The reviewed diff adds this public rq-engine error behavior:

```json
{
  "cleanup_required": true,
  "runid": "generated-run-id"
}
```

It adds the field to `docs/schemas/rq-response-contract.md` and implements it
in `wepppy/microservices/rq_engine/project_routes.py` in the same staged
change. Neither approved ancestor, user-context amendment `4d2ef5838` nor
atomic-admission amendment `b1f1f99c8`, defines that field.

This is an intended public error-contract change, not mere conformance to an
unchanged canonical contract. The contract-first standard covers rq-engine
errors and requires operator approval, two independent read-only reviews,
findings disposition, and a standalone documentation ancestor before
implementation files are edited. It explicitly says an implementation commit
cannot retroactively manufacture that checkpoint and requires final reviewers
to reject reversed sequencing.

The field is bounded and the correlated internal cleanup logging is useful,
but implementation quality does not cure missing authority and ancestry.
There is no urgent-restoration exception: that path may not add an error field
or RQ behavior, and no break-glass authorization exists.

Closure requires one of two contained choices:

1. remove the new public receipt and its canonical-contract amendment, retain
   the existing sanitized public error shape, and close failed-create cleanup
   through exact safe compensation plus correlated internal diagnostics; or
2. restore the implementation to its pre-receipt state, prospectively ratify
   the exact public behavior through the full checkpoint sequence, commit that
   checkpoint as an ancestor, and only then reimplement and validate it.

The in-review worktree currently follows the first scope-reduction direction.
That later unstaged state is not evidence that `d4084b110` passed.

### GOV-PR-02 — High: corrected acceptance cleanup omitted DB-11 state

The reviewed acceptance artifact claims exact SQL, Redis, filesystem, session,
job, tail, and credential cleanup for Users 312/313 and run
`inflammatory-bilberry`. The exact reviewed harness did not connect to the
working-directory cache database, delete its exact run key, or assert that key
absent.

Fresh operations inspection during this review found six exact stale
working-directory cache keys across disposable acceptance attempts. The
operator deleted only those six named DB-11 keys and verified each absent.
This reviewer independently confirmed the structural cause in the
`d4084b110` harness: its cleanup covered RQ and session Redis but not
`RedisDB.WD_CACHE`.

The exact SQL, RQ-job, tail, session, queue, directory, adjacent-log, and
temporary-cookie checks were otherwise clean. Users 312/313, Run 1394, the
four recorded WBT roots, and `inflammatory-bilberry` remain useful evidence,
but they do not make the reviewed cleanup claim complete.

Prospective harness edits now delete and assert the exact WD-cache key and
purge NoDb instances, locks, and file cache before removing a run. Closure
requires a new acceptance run and secret-free postcondition receipt on one
frozen source state; editing the harness after the canary does not
retroactively validate the earlier result.

### GOV-PR-03 — Medium: the exact fingerprint and isolation gate were not frozen

At review entry the requested staged hash was exact and staged/unstaged path
intersection was empty. The staged SURF-14A set was distinct from the
unstaged Command Bar/Pure UI work, including its route, controller, tests,
package, tracker, and generated documentation changes.

The `d4084b110` tracker nevertheless represented test isolation as complete
while the corrected-source isolation run was still pending. Correcting that
statement changed the full staged fingerprint to
`275646c42854b4a7452bce6783064dee439d942d7d2b19c18be84dea162139fc`.
Subsequent cleanup remediation created staged/unstaged overlap in SURF-14A
source, tests, harness, contract, and work-package documentation. The requested
fingerprint is therefore no longer the current release candidate.

The supplied full suite and broad gates also ran in the shared dirty worktree,
not an exported exact index. Initial path separation is good packaging
evidence, but it does not establish that globally imported application code
was identical to the proposed release state.

Closure requires:

- one final staged or committed source fingerprint with no overlapping
  unstaged paths;
- a terminal test-isolation result recorded truthfully;
- exact-state focused and release gates, preferably from a detached temporary
  worktree or CI checkout of the proposed commit; and
- renewed independent reviews of that same fingerprint.

### GOV-PR-04 — Medium: incident hardening lacks required lifecycle evidence

The failed-create cleanup and recovery work was introduced after the canary
left an unreceipt-bound directory. It is incident-driven hardening under
`docs/standards/hardening-lifecycle-standard.md`.

The active package records the failure and regression direction, but it does
not record the required hardening hypothesis, primary health signal,
guardrails, observation window, related precedent, or explicit keep/sunset
decision. It also does not distinguish permanent compensation from any
temporary defensive callus.

Before final approval, the package must add those concise lifecycle fields and
name an owner for the observation review. If the cleanup is intentionally
permanent and has no callus to sunset, state that explicitly rather than
leaving the obligation implicit.

## Positive Control Evidence

The following controls passed review for the exact staged source:

- Create binds `token_class=user` to `current_user.id` only when
  `type(id) is int and id > 0`; missing, zero, negative, Boolean, and string
  subjects fail before token issuance. No email or Flask-Security
  `fs_uniquifier` fallback remains.
- The corrected acceptance receipt identifies Users 312/313, Run 1394,
  `inflammatory-bilberry`, the exact sharing receipt, and four exact WBT root
  job IDs. It demonstrates SI versus English presentation and `error` versus
  `warn` WBT snapshots on one byte-stable project, plus Auto/config and
  service/accountless fallback behavior without durable account-derived
  policy.
- Failed-create filesystem cleanup validates the canonical run path, refuses
  the runs root and top-level symlinks, requires symlink-resistant
  file-descriptor cleanup, and has mismatch, symlink, replacement-race, and
  cleanup-failure regression coverage.
- This reviewer independently ran the strict subject, project-create, and
  preference/cleanup selection: **66 passed**. Documentation lint for the
  package and canonical RQ response contract passed with no findings.
- Supplied broad evidence reports **5,727 Python tests passed, 58 skipped**;
  **745 frontend tests passed**; frontend lint, stubs, test-stub completeness,
  documentation, RQ graph, broad-exception, and diff checks green. These
  results support the implementation direction but do not override the exact
  fingerprint and governance findings above.

The local session materialization is acceptable evidence of ordinary
authenticated route behavior in an OAuth-only local environment. It does not
claim to test the external OAuth provider itself, and the exact server-side
sessions were receipt-bound and removed.

## Authority, Release, and Revocation Decision

- **Exact `d4084b110` release candidate**: rejected.
- **Forest preflight, migration, and canary**: not authorized.
- **Production/wepp1**: outside this package's authority.
- **Allowed next work**: bounded local scope reduction, cleanup remediation,
  documentation correction, exact-state validation, and fresh review.
- **Revocation posture**: retain the last reviewed contract ancestors, do not
  merge or deploy the rejected fingerprint, preserve all FAIL artifacts, and
  remove only exact receipt-bound local residue.

No break-glass justification is proportionate. The defects are locally
remediable without accepting reversed contract sequencing or incomplete
cleanup evidence.

## Final Control Decision

The exact requested fingerprint does not satisfy the post-remediation
governance closure gate. A later source state may earn a new PASS only after
the public-receipt scope is legitimately resolved, WD-cache-aware acceptance
is rerun, hardening lifecycle evidence is recorded, all gates are terminal,
and both independent reviewers approve the same frozen fingerprint.
