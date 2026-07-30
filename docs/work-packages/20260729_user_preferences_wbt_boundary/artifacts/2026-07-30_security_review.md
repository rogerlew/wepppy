# Security Review - Account User Preferences and WBT Boundary Policy

## Metadata

- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Reviewer**: independent operations/security agent; checkpoint re-review
  pending
- **Date**: 2026-07-30
- **Scope**: authenticated preference GET/POST, SQLAlchemy/Alembic state,
  creation-time propagation, run NoDb snapshot, WBT edge policy, rq-engine
  failure, and Forest migration
- **Revision context**: starting implementation revision
  `715417f7081ea12e168e10426603445ec5140520`; checkpoint pending

## Security Triage

- **Impact**: `high`
- **Dedicated review required**: yes
- **Rationale**: the package adds authenticated account mutation,
  CSRF-sensitive input, database schema/state, an account-to-run trust
  boundary, RQ failure behavior, and a Forest database migration.

Threat assumptions are that existing Flask-Security identity, global CSRF,
rq-engine response, run authorization, and NoDb locking contracts remain
authoritative. Preference values are untrusted even when submitted by an
authenticated user. No preference value may select code, paths, commands, or
arbitrary configuration keys.

## Findings

| ID | Severity | Surface | Description | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Identity/ownership | Account lookup and ownership could fail open | Restrict identity/subject binding; atomic ownership and cleanup; generic errors | Contract-fixed; re-review pending |
| SEC-02 | High | Creation inventory | HUC-fire and other constructors were not dispositioned | Include regular/HUC-fire; explicitly exclude all others | Contract-fixed; re-review pending |
| SEC-03 | High | Async errors | Enqueue-time catch was not the worker failure/public status path | Exact jobinfo schema/redaction/diagnostic contract and canonical RQ amendment | Second re-review pending |
| OPS-04 | High | Migration | Repository has two heads; bind-mounted rollout and active workers/backup were unsafe | Fresh validated backup; quiesce enqueue; drain; graceful worker stop; post-stop registry; one-off migration | Contract review PASS |
| OPS-05 | Medium | Stale state | Worker/direct/batch invalidation and retry were incomplete | Exact raster/timestamp/preflight/retry contract | Contract-fixed; re-review pending |
| SEC-06 | Medium | Concurrency | Simultaneous insert/update behavior was ambiguous | Complete-form last-write-wins and bounded collision retry | Contract-fixed; re-review pending |

## Required Surface Checks

- [ ] GET/POST require authentication and POST preserves global CSRF and
  same-origin contracts.
- [ ] Only two exact field names and six exact enum tokens reach persistence.
- [ ] Jinja output is escaped and Pure macros do not create unsafe attributes.
- [ ] Updates are atomic, constrained in PostgreSQL, and safe under concurrent
  requests.
- [ ] Missing row is compatible; database errors are explicit rather than
  silently changing new-run defaults.
- [ ] Authenticated identity cannot read or mutate another user's preferences.
- [ ] Account defaults cannot inject arbitrary `section:name` configuration
  overrides.
- [ ] Explicit project choices, anonymous creation, shared runs, and forks
  cannot cross account boundaries.
- [ ] Failed resolution and `Ron` initialization clean up partial directories
  and do not register a usable run.
- [ ] WBT `error` cannot leave stale completion/readiness or a consumable
  clipped canonical artifact.
- [ ] Typed exception responses disclose no paths, secrets, or internal stack.
- [ ] No queue, subprocess, external egress, dependency, token, role, or secret
  scope is widened.
- [ ] Migration upgrade/downgrade, backup, rollback, revision ordering, and
  Forest least-disruption procedure are reviewed.
- [ ] No credentials, cookies, JWTs, CSRF tokens, or database secrets are
  retained in test or deployment artifacts.

## Validation Evidence

Pending implementation. Required evidence is enumerated in `package.md`,
`tracker.md`, the active ExecPlan, and the contract decision.

## Verdict

- **Gate status**: checkpoint PASS; implementation validation and final review
  remain pending
- **Unresolved findings**:
  - High: none unresolved
  - Medium: none unresolved
  - Low: none
- **Release recommendation**: implementation may begin after the standalone
  checkpoint commit; hold Forest migration until implementation, full
  validation, and final reviews pass.

## Sign-off

- **Security reviewer**: independent operations/security agent, checkpoint PASS
- **Package owner**: requesting WEPPcloud operator / Codex implementation agent
