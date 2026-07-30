# Post-Acceptance Operations and Security Review

## Metadata

- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Reviewer**: independent operations/security control agent
- **Date**: 2026-07-30 UTC
- **Base revision**: `b1f1f99c8f808528315abce001a70200ab068bc7`
- **Reviewed additions**: the real local two-user acceptance record and
  harness, the Create-page token-subject correction and regression, failed
  attempt containment, cleanup, and local worker/queue recovery
- **Forest or production mutation by this review**: none
- **Historical artifacts changed by this review**: none

This artifact is additive. It does not amend the earlier source-freeze PASS
reviews or the historical local-acceptance PASS record.

## Verdict

**FAIL / SCOPE-REDUCE — local remediation and validation only. Do not declare
the tree commit-ready and do not begin Forest preflight, migration, or canary.**

The successful two-user exercise is credible: it reached the real browser,
Create, preference, shared-run, Unitizer, rq-engine, Redis/RQ metadata, and
public-redaction boundaries. The numeric Create-token correction also fixes
the discovered normal-user failure without widening authorization.

The cleanup claim is not yet a sufficient T4 control record. Independent
inspection found a partially initialized acceptance-era run directory that
had no PostgreSQL or Redis receipt. The coordinator removed that exact
directory only after independently proving the database and Redis negatives,
and the local environment is clean now. The underlying Create failure path
and the acceptance postcondition remain unable to guarantee that the same
unreceipt-bound residue cannot recur.

In addition, the token issuer still permits a nonnumeric email fallback for a
`token_class=user` subject, and the successful exercise was performed after a
production source change that was not part of the state-specific source-freeze
reviews or final full-suite result. Final validation and renewed independent
review are therefore required.

## Findings by Severity

| ID | Severity | Status | Finding |
| --- | --- | --- | --- |
| POST-OPS-01 | High | Open | A failed create left an unreceipt-bound run directory; the current product and harness boundary cannot prove failure-atomic cleanup. |
| POST-OPS-02 | Medium | Open | The harness does not produce a durable, asserted cleanup receipt for every SQL, Redis/RQ, and filesystem postcondition. |
| POST-SEC-01 | Medium | Open | The corrected Create issuer prefers the numeric User ID but can still mint a user-class token with an email subject. |

There are no open Low findings.

### POST-OPS-01 — failed create can leave an unreceipt-bound directory

Independent inspection found:

```text
/wc1/runs/at/attainable-novitiate
```

Its project files were initialized at `2026-07-30 12:14:42-43 UTC`. Its TTL
was active with `last_touched_by` set to `create`, its README still contained
template placeholders, and it had no corresponding PostgreSQL `runs` or
`runs_users` row. Redis contained neither a matching job hash nor
`rq:subcatchment-mutation-tail:attainable-novitiate`.

The harness does not receive a run ID until a 303 response is parsed
(`tools/surf14a_local_acceptance.py:178`). Its cleanup can discover only that
returned run ID or a Run row associated with one of the disposable users
(`tools/surf14a_local_acceptance.py:265`). It therefore cannot discover a
directory created by a request that fails before its redirect and before
ownership registration. The orphan is durable evidence that this is an
executed failure path, not a hypothetical one.

The coordinator subsequently removed exactly
`/wc1/runs/at/attainable-novitiate` using depth-first deletion after separately
confirming zero database run/association rows and zero matching Redis keys. It
was not removed by scheduled garbage collection. Follow-up checks prove that
both the orphan and the passing run directory
`/wc1/runs/li/livelong-blouse` are absent.

Current cleanup resolves the local residue, but it does not close the control
defect. Closure requires the product Create boundary to provide one of these
equivalent properties:

1. every failed create leaves no run directory; or
2. any directory that cannot be removed has an exact, durable, correlated
   recovery receipt that an operator can resolve without guessing ownership.

Fault injection must exercise failure after directory creation and a cleanup
failure such as a retained file handle. It must prove the exact directory is
removed or durably recoverable, no owner/association row survives, the public
response remains sanitized, and the internal error ID/run ID identifies the
recovery target.

### POST-OPS-02 — cleanup result is not durably asserted

The current harness has two sound improvements made during this review:

- it appends each successful WBT root ID immediately, so a second submission
  failure does not lose the first receipt
  (`tools/surf14a_local_acceptance.py:221`); and
- bounded cleanup errors are accumulated and make the process fail
  (`tools/surf14a_local_acceptance.py:255`,
  `tools/surf14a_local_acceptance.py:320`).

The remaining evidence and postcondition gaps are:

- the `status: pass` payload is emitted before cleanup starts
  (`tools/surf14a_local_acceptance.py:237`);
- deleted job IDs are not checked for absence from job hashes, queues,
  registries, dependency sets, or root links;
- the run tail is deleted without asserting its absence;
- successful `rmtree` is not followed by an absence assertion;
- total row-count equality supplements, but does not replace, exact
  run/preference/role/association receipt assertions; and
- the durable acceptance artifact records neither job IDs nor a structured
  after-cleanup receipt, so the claimed Redis cleanup cannot be reconstructed
  after deletion.

Closure requires a final cleanup receipt, emitted only after cleanup, that
records secret-free exact identifiers and asserts:

- both disposable emails and User IDs, their preference rows, their exact
  User-role associations, the disposable Run row, and every `runs_users`
  association are absent;
- every recorded WBT root and known child/dependency/registry/queue reference
  is absent, and the exact run tail is absent;
- every operation-created run directory is absent or is reported as an
  operator-blocking recovery target; and
- the process exits nonzero on any unresolved postcondition.

The passing canary must be rerun after these controls are in place. At least
the second-WBT-submission failure and failed-directory-cleanup cases must also
be exercised before Forest.

### POST-SEC-01 — user token issuer does not enforce its numeric subject

The change at `wepppy/weppcloud/routes/run_0/run_0_bp.py:2266` now reads
`current_user.id` before any other identity. The focused regression proves
that User ID 42 becomes subject `"42"` even when `get_id()` returns a
Flask-Security `fs_uniquifier`
(`tests/weppcloud/routes/test_run_0_create_token.py:16`). The regression plus
the rq-engine project-route suite independently passed with 23 tests.

This fixes the observed normal-user path. The consumer also validates a
positive integer and rejects a malformed subject before directory creation
(`wepppy/weppcloud/user_preferences.py:139`,
`wepppy/weppcloud/user_preferences.py:237`), so the remaining issue is
fail-closed and is not an authorization bypass.

The issuer nevertheless falls back to email when the ID is falsey
(`wepppy/weppcloud/routes/run_0/run_0_bp.py:2270`). That can mint a
`token_class=user` token whose subject contradicts this package's canonical
positive-numeric User binding. Closure requires validating a positive numeric
`current_user.id` at issuance, removing the email-subject fallback for this
token, and adding missing, Boolean, zero, negative, and nonnumeric subject
regressions.

## Independent Recovery and Residue Evidence

After the exact orphan cleanup, the reviewer obtained:

| Boundary | Independent result |
| --- | --- |
| Exact disposable Users, IDs 284/285 | 0 rows |
| Exact preference rows | 0 rows |
| Exact User-role associations | 0 rows |
| Runs `livelong-blouse` and `attainable-novitiate` | 0 rows |
| Exact run associations | 0 rows |
| Both run directories | absent |
| Matching Redis jobs for both run IDs | none |
| Per-run mutation tails for both run IDs | absent |
| `default` queue | 0 queued, 0 executing |
| `batch` queue | 0 queued, 0 executing |
| Worker state | all registered workers idle |
| Web/rq-engine/Redis/worker containers | running; Redis healthy |

A scheduled `gc_runs_rq` briefly occupied one default worker during review. It
completed normally, was unrelated to either acceptance run, and left both
queues at zero queued/zero executing. No worker, queue, database, Redis, or
filesystem mutation was performed by this reviewer.

## Validation Status

Preliminary post-acceptance evidence is green:

| Gate | Result |
| --- | --- |
| Numeric-subject regression plus rq-engine project-route suite | **PASS — 23 tests** |
| RQ dependency graph/catalog | **PASS** |
| Changed-file broad-exception enforcement | **PASS, net -5** |
| `git diff --check HEAD --` | **PASS** |
| Local acceptance artifact documentation lint | **PASS** |

These checks do not restore the source freeze. The Create-token production
change was made after the recorded final full suite and both state-specific
source-freeze reviews. Any product-boundary cleanup remediation will add more
source drift.

## Required Release Sequence

Before a release commit or Forest action:

1. close POST-OPS-01 at the product boundary and add cleanup/recovery fault
   injection;
2. close POST-OPS-02 and produce a new secret-free acceptance/cleanup receipt;
3. close POST-SEC-01 with strict numeric issuance and negative regressions;
4. rerun the passing real two-user local canary and its required failed-attempt
   containment cases;
5. run the package's final focused, full Python, frontend, stub, isolation,
   RQ-graph, broad-exception, and whitespace gates against one frozen source
   state; and
6. obtain renewed governance and operations/security reviews for that exact
   state.

Only a new PASS artifact may authorize Forest preflight. Forest migration and
canary remain separately subject to exact-source, backup, quiescence,
migration, rollback, cleanup, and post-action evidence.
