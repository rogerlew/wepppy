# SURF-14A Post-Acceptance Governance and Cleanup Review

## Metadata

- **Reviewer**: independent governance/correctness control agent
- **Date**: 2026-07-30 UTC
- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Review boundary**: the local two-user acceptance artifact and harness,
  exact local PostgreSQL/filesystem/Redis cleanup state, the canary-discovered
  Create-token subject correction and regression, the approved user-context
  contract, and the source-freeze evidence
- **Production or Forest mutation by this reviewer**: none
- **Break-glass basis**: none requested or used

Historical checkpoint, final-review, source-freeze, and acceptance artifacts
remain preserved. This is a new post-acceptance control record; it does not
replace or silently revise any earlier artifact.

The initial review target was:

| Item | SHA-256 |
| --- | --- |
| Local acceptance artifact | `8ed7ead54c1d4125bc63af51ddaeaa233b830031e4c3b8549111b5ed16871df2` |
| Acceptance harness | `42c79fc99aacbd09212d74435beef8eed040d30ee6f5663a27f7c1e241517c37` |
| Create-page route source | `75b2195a30841ce5c4feace3ba85340944685e86e7e53cfd4a481ca8f02f1586` |
| Create-token regression | `5320624cba1539dc1d37c721161ba4b8f830dcc3bddb6ddf91581bbe09f8f1e7` |
| Source-freeze governance PASS | `bbbf4141f0c3214f19ff039d0430588cb922992b60cf783e0b7516b1cac32edb` |
| Source-freeze operations/security PASS | `55a4d8a99524f4b9f795a640f1d1c202c064194a19de0b0be6ae3b4860ae68c8` |

Source and harness remediation began during this review. Those later files are
not covered by the verdict for the initial fingerprint and require a fresh
review after their validation evidence is complete.

## Verdict

**FAIL — SCOPE-REDUCE. REJECT Forest and release progression.**

Only exact local residue cleanup, harness/evidence correction, strict numeric
token-subject correction, and validation reruns are authorized. The existing
Forest authority is not broadened, and production/wepp1 remains unauthorized.

**Findings against the reviewed acceptance fingerprint**: 3 High, 2 Medium.

The accepted user-context design remains legitimate: presentation follows the
authenticated viewing user, a WBT snapshot follows the authenticated
initiating user, and neither follows project ownership or mutates durable
project policy. The real canary supplied valuable evidence for two distinct
users on one project and correctly exposed `fs_uniquifier` subject drift.
However, the retained acceptance artifact overstates both its exercised scope
and its cleanup. A source change after source-freeze also invalidates the
reviewed release fingerprint until the required validation and dual review
repeat.

## Findings

### GOV-PA-01 — High: the PASS cleanup claim was false at review entry

The retained acceptance artifact says the exact run directory and credentials
were absent. Initial independent inspection instead found:

- `/wc1/runs/li/.livelong-blouse`, a 213-byte mode-`0644` access log outside
  the deleted run directory. Its three structurally valid records contained
  the disposable User A email twice and User B email once, together with IP
  and timestamp fields. No IP or full record was copied into this artifact.
- `/tmp/surf14a-cookies.txt`, a 253-byte mode-`0664` cookie jar containing one
  `session` cookie record with a 64-character secret value. The value was not
  read into review output or reproduced.
- `/wc1/runs/at/attainable-novitiate`, a directory from a failed acceptance
  attempt that was not identified in the retained transcript. The root
  orchestrator found this path while responding to the review and confirmed
  zero corresponding database and Redis state before removing it.

The harness deletes `run.wd`, but the production run view writes
`.<runid>` beside that directory. Consequently `shutil.rmtree(run_wd)` cannot
remove the access log. The harness also did not own or assert cleanup of the
temporary cookie jar.

The root orchestrator intentionally removed those three exact targets during
this review. At `2026-07-30 12:29:50 UTC`, this reviewer independently
confirmed absence of:

- `/wc1/runs/li/livelong-blouse`;
- `/wc1/runs/li/.livelong-blouse`;
- `/wc1/runs/at/attainable-novitiate`;
- `/wc1/runs/at/.attainable-novitiate`; and
- `/tmp/surf14a-cookies.txt`.

Current exact state is clean for the known acceptance identities and runs, but
the original cleanup procedure and evidence are not acceptable release
evidence. A revised harness must receipt-bind and assert all run-adjacent logs,
temporary credentials, failed-attempt paths, SQL rows, job hashes, queue
membership, and tail keys. Cleanup failure must fail the canary and remain
visible for operator completion.

### GOV-PA-02 — High: required local acceptance rows were not exercised

The harness writes each disposable user's `fs_uniquifier` directly into a
Flask test-client session and transfers the resulting signed cookie to the
live HTTP client. This proves live behavior after an authenticated session
exists, but it does not prove the contract's ordinary credential-authenticated
path or credential creation and cleanup boundary.

The canary proves:

- User A SI versus User B English on one run;
- User A presentation Auto/config;
- User A `error` versus User B `warn` WBT root snapshots;
- public job-info redaction; and
- byte-stable Unitizer and unchanged durable WBT fields.

It does not prove the locally required WBT Auto/config submissions or the
anonymous/public-session/service fallback rows. No anonymous, public-session,
service, or MCP request is made by the harness. Pre-source-freeze unit and
route coverage for those paths does not replace the explicit local canary
obligation recorded in the approved contract and active ExecPlan.

The retained artifact must therefore not be used as evidence that the full
local acceptance contract passed. The missing rows require a contained rerun
against the corrected fingerprint.

### GOV-PA-03 — High: the canary changed source after source-freeze

The source-freeze reviews approved the working tree only after the 5,721-test
Python suite and the other recorded gates passed. The real canary then changed
`wepppy/weppcloud/routes/run_0/run_0_bp.py` and added
`tests/weppcloud/routes/test_run_0_create_token.py`.

This reviewer independently reran the initial correction selection:

```text
23 passed, 6 warnings in 11.67s
```

That result supports the discovered failure mode but does not transfer the
earlier full-suite approval to the new source. The active ExecPlan correctly
leaves post-acceptance review and final validation pending. Forest requires a
new stable fingerprint, the complete prescribed validation gates, and both
independent post-acceptance approvals on that same fingerprint.

### GOV-PA-04 — Medium: the initial issuer correction retained a nonnumeric fallback

The approved contract requires a `token_class=user` token to carry a verified
positive numeric User subject. The initial correction preferred
`current_user.id` but retained `current_user.email` when the ID was missing or
falsey. It also accepted any truthy value, including a Boolean, negative
integer, or numeric-looking string. The downstream creation boundary rejected
those subjects, so this did not bypass ownership or preference controls, but
the issuer still did not satisfy the exact contract.

The initial regression proved only that ID `42` superseded
`fs_uniquifier`. During this review the root orchestrator replaced the fallback
with `type(subject) is int and subject > 0` and added negative cases for
missing, zero, negative, Boolean, and string IDs. That direction matches the
approved user-context contract. It is prospective closure only until the new
source/test fingerprint passes final validation and independent re-review.

### GOV-PA-05 — Medium: receipts and cleanup assertions were not durable or exact

The retained transcript records Users 284 and 285 and run
`livelong-blouse`, but omits:

- both exact emails in the procedure receipts;
- the `User` role ID and both exact `(user_id, role_id)` receipts;
- the Run database ID and exact `(user_id, run_id)` sharing receipt;
- both WBT root job IDs;
- all failed-attempt run IDs and paths;
- numeric before/after table counts; and
- the literal post-cleanup SQL and Redis results.

This omission prevented an independent reviewer from deriving every cleanup
target from the artifact itself. It also makes the claim that no unrelated
count changed non-reproducible after the fact.

The initial harness silently caught every exception while deleting jobs,
selected every Run associated with either disposable User rather than only
the recorded Run ID, and asserted aggregate User/preference/role/run-sharing
counts but not the exact Run row, access log, credentials, job hashes, or
tail. The artifact then asserted stronger cleanup than the harness output
demonstrated.

A superseding evidence artifact must preserve the failed artifact, publish all
nonsecret receipts and numeric before/after counts, record exact cleanup
queries/results, and identify any operator-assisted cleanup. It must not expose
passwords, session cookies, bearer tokens, client IPs, or other secrets.

## Independent Current-State Evidence

After the exact remediation described under GOV-PA-01, this reviewer obtained
the following read-only results:

- PostgreSQL returned zero rows across the exact disposable emails, User IDs
  284/285, `user_preferences`, `roles_users`, `runs_users`, `oauth_account`,
  `run`, and `run_migrations` targets for `livelong-blouse` and
  `attainable-novitiate`.
- A scan of 1,787 Redis RQ job hashes completed with zero decode/fetch errors
  and found no reference to either run ID.
- Redis contained no key name or subcatchment-mutation tail for either run ID.
- Both `default` and `batch` had zero queued and zero started/executing jobs
  when checked. Historical unrelated finished, failed, and deferred registry
  entries were not altered by this review.
- The exact known run directories, adjacent dot logs, and temporary cookie jar
  were absent.

This supports the narrow statement that no durable residue remains for the
known acceptance receipts at the end of this review. It cannot reconstruct
the missing preflight counts or prove the original cleanup assertion was true
when written.

## Contract and Authority Assessment

The canary-discovered change is within the operator-approved behavior only
when the issuer binds `token_class=user` to an exact positive numeric
`current_user.id`. It must never use project owner, email, or Flask-Security
`fs_uniquifier` as the account subject. The strict correction observed during
this review appears to restore that boundary and continues to fail closed
before run-directory creation for malformed identity.

No finding justifies weakening downstream identity validation, substituting
email identity, skipping independent review, or treating local cleanup as
authority for Forest. Revocation remains straightforward: withhold Forest,
remove only exact local receipts, and retain the last reviewed source and
artifacts until a corrected fingerprint passes.

## Required Closure Before Forest

1. Finish the receipt-bound harness correction, including exact run-adjacent
   access-log and credential cleanup, exact job/tail assertions, narrow
   exception handling, and nonsecret receipt/count output.
2. Rerun the local canary on the strict numeric-subject fingerprint through
   the ordinary authenticated path and exercise every required
   Auto/config/anonymous/public-session/service fallback row.
3. Preserve the failed acceptance artifact and create a new superseding
   redacted transcript containing exact nonsecret receipts, before/after
   counts, SQL/Redis/filesystem cleanup results, and any operator intervention.
4. Run the active ExecPlan's complete final validation set against one stable
   post-canary fingerprint. Focused token/project-route results alone are
   insufficient.
5. Obtain fresh governance/correctness and operations/security
   post-acceptance PASS artifacts for that same fingerprint.
6. Only then perform the existing Forest preflight. Stop on any target,
   revision, backup, schema, account, queue, service-health, canary, or cleanup
   mismatch. Production/wepp1 remains out of scope.

## Final Control Decision

**Forest and release remain blocked.** Current known local residue has been
removed and the strict numeric-ID remediation is directionally
contract-conformant, but the reviewed acceptance fingerprint failed its
cleanup, coverage, evidence, and source-freeze obligations. No break-glass
exception is justified.
