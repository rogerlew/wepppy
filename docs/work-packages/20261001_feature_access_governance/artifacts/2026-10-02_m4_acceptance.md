# Milestone-four onboarding and maturity acceptance

Recorded 2026-10-02 UTC against the working tree after M3 commit `1c9ad8046`.
Production was not modified.

## Implemented behavior

The existing `multi-ofe-is-preview` registry rule is now a conservative
Preview ceiling. A matching declared Stable or Preview configuration resolves
to Preview. Experimental, Internal and Deprecated declarations remain intact.
The real loader reports both Revegetation MOFE variants as Experimental. No
scientific configuration value changed.

Profile presents the versioned PowerUser statement and exactly two required
questions. Its session/CSRF POST binds the authenticated current account and
accepts no account, role or decision-rule input. The store locks that active
account and commits the versioned acceptance, automatic decision metadata,
approval time and only the PowerUser role in one transaction. Repeats do not
duplicate either record; unrelated roles survive. Existing PowerUsers remain
active without a fabricated acceptance record.

## Database, token and transport evidence

The final focused registry/Profile/account run passed **275 tests**. Direct isolated
PostgreSQL cases cover all five maturity states, the two real Revegetation
configs, strict boolean and field validation, stale versions, cross-account and
role-field injection, missing role configuration, idempotence, legacy users,
transaction rollback and preservation of unrelated roles.

The final full repository regression passed **10,267 tests with 126 skipped and
4,013 warnings in 2,794.19 seconds (46:34)**. An earlier attempt stopped at one
unrelated postfire NoDb retained-lock failure after 3,608 passing tests. The
exact failing parameter passed immediately in isolation, and the complete rerun
then passed the same module and the entire repository. No production fix was
made for that transient test-environment lock.

Frontend validation passed standard lint, explicit `feature_access.js` lint,
and **112 Jest suites / 919 tests**. Test-stub completeness, changed-file broad
exception enforcement, Python compilation, Markdown lint, root AGENTS size and
whitespace checks passed.

A freshly approved user's real signed profile-token shape resolves to a current
PowerUser principal but remains denied for a private Batch grouped-resource
decision. No group membership or internal scope is added during onboarding.

## Full-app browser evidence

The existing isolated full application ran under the development container's
normal dependencies with real Flask-Security/Redis sessions, CSRF middleware,
templates/scripts and a disposable PostgreSQL schema. Playwright passed **1
test in 10.1 seconds**. An ordinary User completed both Profile questions,
received PowerUser, used a PowerUser-only probe, minted a real 90-day profile
JWT, and received HTTP 403 when that fresh token attempted the private Batch
probe. The existing group grant, internal acknowledgment and removal round trip
also remained green.

The test clears the JWT field before retaining visual/axe evidence. No bearer
credential, session cookie or signing material is present in the artifact bundle.

The exercised Profile and administration states have zero violations from the
bounded WCAG 2 A/AA and WCAG 2.1 AA axe scan. The helper's cookie file, Redis
sessions and PostgreSQL schema were removed after the run.

Retained evidence:

- [Round-trip observations](m4-browser/roundtrip.json)
- [PowerUser Profile screenshot](m4-browser/profile-poweruser.png) and [axe result](m4-browser/profile-poweruser-axe.json)
- [Pending internal access screenshot](m4-browser/profile-pending.png) and [axe result](m4-browser/profile-pending-axe.json)
- [Group administration screenshot](m4-browser/admin-granted.png) and [axe result](m4-browser/admin-granted-axe.json)

## Scope

This milestone adds no suspension, reinstatement or permanent-revocation state.
It changes no token lifetime/scope, group membership, private-resource rule,
queue wiring, service credential or deployment state. Final M5 reviews and an
operator-approved production rollout remain open. The deployed Culvert
credential's recorded expiry remains a separate rollout dependency.
