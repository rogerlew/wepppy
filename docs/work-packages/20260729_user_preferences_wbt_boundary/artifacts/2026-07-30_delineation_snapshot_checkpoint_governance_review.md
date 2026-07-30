# Delineation Snapshot Amendment Checkpoint Governance Review

## Metadata

- **Reviewer**: independent governance/correctness control agent
- **Date**: 2026-07-30 UTC
- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Starting implementation revision**:
  `b593fb1d8595f6c3c9862ce773def31d372d787c`
- **Review boundary**: the uncommitted documentation-only SURF-14A
  delineation-snapshot amendment and its PostgreSQL evidence
- **Forest, production, or acceptance mutation**: none

The review excluded unrelated dirty-worktree changes. Source at the starting
revision was read only to determine whether the proposed authority, identity,
configuration, NoDb, and RQ rules were executable without policy inference.
No implementation file or authored amendment document was modified.

## Verdict

**FAIL — REJECT checkpoint ratification, standalone-ancestor disposition, and
runtime implementation.**

The amendment correctly recognizes the operator's expected result for their
owned run, chooses enqueue-time snapshotting over worker-time account lookup,
corrects the dependent state to `canceled`, and supplies adequate explicit-
target PostgreSQL graph evidence. It does not yet establish authority for the
complete cross-user delta or define a deterministic owner/session and
configuration source for every included path.

**Findings**: 2 High, 3 Medium, 0 Low.

No break-glass basis exists. Acceptance E2E and Forest must remain blocked.

## Findings

### GOV-SNAP-01 — High: recorded operator authority is narrower than the normative delta

The amendment accurately limits the later operator statement to the observable
requirement that a delineation on their owned run use their current preference
and stop with the controlled error
(`2026-07-30_contract_amendment_delineation_snapshot.md`, lines 24-29).
The normative delta then governs every `user` and `session` submission,
shared/admin initiators, forks and ownership changes, legacy/unowned failure
semantics, and new audit retention (lines 46-88).

Those broader choices are reasonable containment proposals, but they are not
covered by the quoted approval. The amended contract decision instead
attributes the complete, newly revised snapshot/fork delta to the original
2026-07-29 execution instruction
(`2026-07-30_contract_decision.md`, lines 56-60), and ADR-0033 repeats that
older provenance while presenting the revised decision as accepted
(`docs/adrs/ADR-0033-user-defaults-and-wbt-boundary-policy.md`, lines 3 and
67-85). This retroactively expands the scope of an earlier approval.

Required closure:

1. Present the exact owner/shared/admin/session/service/MCP/fork matrix to the
   decision owner and record explicit approval after the amendment exists; or
   scope-reduce the amendment to the approved owned-run behavior and govern
   later cross-user behavior separately.
2. Add the later decision venue, timestamp, participants, exact approval, and
   supersession relationship to ADR-0033 and the contract decision.
3. Keep the amendment pending until both independent reviews and the
   disposition are complete; an earlier accepted ADR must not imply that this
   later behavior is ratified.

### GOV-SNAP-02 — High: controlling owner and account-bearing session identity are not exact

The amendment requires an “active owner” and stable numeric actor/owner IDs
but does not name the authoritative relationship. The application has two
different concepts:

- singular `Run.owner_id`, used by `Run.owner`
  (`wepppy/weppcloud/app.py`, lines 167-207); and
- the many-to-many `runs_users` association returned by the existing
  “run owners” helper.

This difference is material for shared and forked runs. The current fork path
sets the authenticated forker as the destination `Run.owner_id` while adding
source-associated users to the destination association
(`wepppy/microservices/rq_engine/fork_archive_routes.py`, lines 379-412).
Selecting the first associated user instead of the singular owner would let a
non-controlling account determine safety policy.

The session rule is also internally incomplete. Session JWT issuance makes
`user_id` optional, public-run session authorization can succeed without an
account, current session authorization verifies the run/session marker rather
than the optional numeric account claim, and sanitized session actors retain a
session identifier rather than a numeric User ID. The amendment nevertheless
treats every `session` principal as account-bearing and requires a stable
numeric actor ID. The package simultaneously says run-session identities
cannot impersonate an account
(`package.md`, lines 117-120).

Required closure:

1. Name the one controlling database field or relationship. If it is
   `Run.owner_id`, say explicitly that `runs_users` membership grants existing
   mutation authority but never preference-control authority.
2. Define fork and any ownership-transfer transition for that field,
   including missing, nonnumeric, inactive, deleted, and multiply associated
   cases.
3. Define an account-bearing session as a verified numeric `user_id` claim
   bound to an active User and state how it is revalidated. Separately specify
   behavior for an existing authorized session with no account claim,
   including public runs; do not silently convert that path into either an
   account lookup or a new denial.
4. Require database-backed tests for the singular owner versus associated
   users, authenticated forker versus carried associations, admin/shared
   initiators, and session claims that are present, absent, malformed,
   mismatched, inactive, or revoked.

### GOV-SNAP-03 — Medium: “project configuration” is not a stable fallback source

The amendment says an owner value of `config` or a missing preference row uses
project configuration, but it does not identify the exact source. At creation,
a non-`config` account boundary value is inserted into the effective creation
overrides before `Ron` is initialized
(`wepppy/weppcloud/user_preferences.py`, lines 189-193;
`wepppy/microservices/rq_engine/project_routes.py`, lines 363-431).
The resulting query override is part of the run's `_config`, and the persisted
Watershed value is also an effective value. Neither is necessarily the
underlying selected configuration value.

Consequently, changing an account from `error` to `config` could resolve the
old account-derived `error` rather than the selected configuration's value.
That makes the stated source label `project_config` and later retry snapshot
non-reproducible.

Required closure:

1. Define the immutable project-config baseline precisely, excluding any
   account-derived creation override, and state how it is recovered for
   existing, legacy, restored, and forked runs.
2. Define precedence for service/MCP and direct/batch paths without using the
   ambiguous phrase `persisted/config-derived`.
3. Test `warn|error -> config`, missing-row fallback, a run created with an
   account override, legacy hydration, restore, and fork behavior. Each test
   must assert the snapshot's prior value, effective value, and source.

### GOV-SNAP-04 — Medium: failure atomicity and NoDb sequencing permit partial mutation

The amendment promises no readiness or queue mutation when preference
resolution fails. That is too narrow for the current route boundary, which
can persist submitted subcatchment options to `watershed.nodb` before clearing
timestamps and enqueueing
(`wepppy/microservices/rq_engine/watershed_routes.py`, lines 965-1018).
An implementation could therefore satisfy the written promise while returning
`preference_resolution_failed` after partially changing the project.

The worker rule also needs exact cache and lock sequencing. The policy must be
validated, the Watershed cache hydrated from current durable state, and the
snapshot persisted in a bounded canonical lock scope that ends before
`build_subcatchments()`, which requires an unlocked controller and acquires
its own lock scopes.

Required closure:

1. Require authorization, controlling-owner binding, preference lookup, and
   snapshot validation to finish before any NoDb, RedisPrep, readiness, job-ID,
   or queue mutation.
2. Specify child cache invalidation/hydration, one locked policy write, lock
   release, and only then WBT execution. A policy-write or stale-write failure
   must not begin WBT or clear prior readiness.
3. Test unchanged NoDb state on every resolver failure, lock/cache/stale-write
   failure before execution, exact root-to-child snapshot serialization, RQ
   retry reuse, and a fresh user resubmission as a distinct snapshot.

### GOV-SNAP-05 — Medium: authoritative documents still state incompatible behavior

The package overview still says later account changes do not silently change
an existing project's behavior (`package.md`, lines 15-20), while its
normative section says a WBT preference edit takes effect on the next
account-bearing delineation (lines 99-106).

ADR-0033 says legacy state preserves `warn` through forks regardless of later
configuration or account changes (lines 40-44), then says existing runs adopt
the owner's changed preference on a later delineation (lines 58-62). The ADR
is marked unqualified `Accepted` even though the contract decision and package
properly identify the delineation amendment as pending.

Required closure:

1. Reconcile the overview, ADR decision, compatibility text, package normative
   contract, and contract decision to one lifetime rule.
2. Mark the ADR's original decision and pending amendment distinctly until the
   checkpoint is approved and committed.
3. Run documentation lint and retain spelling-normalization evidence after the
   documents are reconciled.

## Accepted Portions

The following portions are acceptable and may be retained while the findings
are corrected:

- The user's owned-run expectation is recorded as an intended behavior change,
  not misclassified as an implementation-only conformance fix.
- Resolution before enqueue, a bounded primitive root/child argument, no
  worker account lookup, and retry reuse are the correct deterministic RQ
  architecture once actor, owner, and fallback sources are exact.
- Ignoring a shared initiator's personal preference and preventing
  service/MCP account impersonation are sound authority-containment rules.
- A failed subcatchment child with a never-started abstraction dependent in
  RQ's terminal `canceled` state is aligned with the amended canonical polling
  contract. This closes the prior `stopped`/`canceled` discrepancy.
- The representative-schema limitation is now explicit. The recorded
  both-parents to merge, explicit-target downgrade restoring both parents, and
  re-upgrade cycle is adequate graph-level PostgreSQL evidence. Destructive
  migration downgrade remains outside current Forest authority.
- Unitizer behavior, TOPAZ behavior, geometry, formulas, thresholds, and
  configuration defaults remain outside the amendment. Acceptance mutation
  and Forest are correctly blocked.

## Required Re-review Evidence

Before another governance checkpoint review, retain:

1. explicit decision-owner approval for the final cross-user matrix;
2. reconciled canonical documents with exact owner, session, and config
   sources;
3. a complete database-backed authority matrix and the configuration-reset
   cases listed above;
4. failure-atomic NoDb/cache/lock and immutable RQ snapshot tests;
5. the existing explicit-target PostgreSQL graph transcript and canceled-
   dependent contract; and
6. a clean documentation lint result for every amended document.

The next review remains documentation-only. Runtime implementation, local
acceptance mutation, and Forest rollout are not authorized until the corrected
checkpoint is independently approved, dispositioned, and committed as a
standalone ancestor.
