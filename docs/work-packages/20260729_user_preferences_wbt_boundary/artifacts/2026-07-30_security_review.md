# Security Review - Account User Preferences and WBT Boundary Policy

## Metadata

- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Reviewer**: pending independent operations/security reviewer
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
| SEC-01 | Pending | Checkpoint | Independent review has not run | Complete review and disposition | Open |

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

- **Gate status**: pending
- **Unresolved findings**:
  - High: pending review
  - Medium: pending review
  - Low: pending review
- **Release recommendation**: hold implementation until the checkpoint passes;
  hold Forest migration until implementation, full validation, and final
  reviews pass.

## Sign-off

- **Security reviewer**: pending
- **Package owner**: requesting WEPPcloud operator / Codex implementation
  agent, pending
