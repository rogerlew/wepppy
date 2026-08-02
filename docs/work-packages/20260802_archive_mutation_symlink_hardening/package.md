# Run Archive Consistency and Symlink Hardening

**Status**: Open (2026-08-02)
**Timezone**: UTC
**Security impact**: `high`

## Overview

Harden run archive creation against two confirmed production defects: archives
can read a run while an RQ mutation is deleting files, and a broken run-tree
symlink currently fails late with an unhelpful `FileNotFoundError`. The package
will define a snapshot-consistency contract, coordinate archive creation with
participating mutations, and give symlinks an explicit, secure archive policy.

## Trigger and Failure Signatures

- Environment: `wepp1` production.
- Run: `mdobre-intensive-darling`.
- First archive job: `65717fb6-db0b-47e8-aa28-602dc798a18b`, running
  2026-08-02 16:39:10–16:51:45 UTC.
- Contrast deletion job: `ae0ea873-ef03-410a-9a9f-d7e6e6c791e0`, running
  2026-08-02 17:06:04–17:08:53 UTC.
- Second archive job: `b4eeaff3-f2ff-4107-a0ff-418638cb15dd`, running
  2026-08-02 17:06:21–17:09:38 UTC. It overlapped contrast deletion for about
  152 seconds.
- Exact exception:
  `FileNotFoundError: [Errno 2] No such file or directory:
  '/wc1/runs/md/mdobre-intensive-darling/_pups/omni/scenarios/prescribed_fire/climate'`.
- The failing entry was a symlink to
  `/wc1/runs/md/mdobre-facile-deviousness/climate`; that target run was absent.
- The same symlink failed the first archive before the recorded contrast
  deletion began. Concurrency and the broken link are therefore distinct
  defects even though the second failure exhibited both conditions.
- User impact: archive creation ran for several minutes and then failed; no
  usable archive was produced.

## Scope Boundary

Make archive creation either consume a contract-defined stable run snapshot or
fail before payload writing with a precise, actionable consistency error,
without redesigning Omni storage or general NoDb locking.

### Included

- Define the authoritative archive snapshot, mutation-exclusion, symlink, and
  error/cleanup contracts before implementation.
- Inventory run-tree mutation entry points that can overlap archive traversal,
  beginning with Omni contrast deletion and scenario/contrast cleanup.
- Add run-scoped coordination that covers the full filesystem mutation window,
  including deletion performed after a controller's short NoDb critical
  section.
- Add deterministic preflight and traversal behavior for valid, broken,
  dangling-during-read, internal, and run-root-crossing symlinks.
- Make newly created Omni child-run links to shared parent inputs relative to
  the child workspace, so copying the complete run retargets them naturally.
- During fork, normalize recognized legacy Omni shared-input links to canonical
  relative links within the destination run. Derive the destination from the
  link's role and location, not by replacing only the immediate source-run
  prefix, so multi-generation inherited links are repaired as well.
- Preserve atomic publication: only a complete validated archive may replace
  the final archive path, and `.tmp` files must be cleaned after failure.
- Add exact race and symlink regression tests, operator diagnostics, durable
  documentation, security review, code review, and QA review.
- Update `wepppy/rq/job-dependencies-catalog.md` and run the graph gate only if
  enqueue/dependency wiring changes.

### Explicitly Out of Scope

- Repairing or recreating `mdobre-facile-deviousness` production data.
- Automatically deleting broken links or silently omitting unknown entries.
- Broad conversion of Omni symlinks to copied data.
- Generic filesystem snapshots, NFS redesign, queue-wide serialization, or
  stack restarts.
- Archive restore redesign except where required to keep the chosen archive
  entry contract symmetric and safe.
- Parameter defaults, model formulas, thresholds, units, or fallback heuristics.

## Contract-First Gate

This work changes UI-coupled RQ terminal/error behavior and shared run mutation
semantics. Before production code is edited, create and obtain operator approval
for `artifacts/2026-08-02_contract_decision.md`, amend or add every applicable
canonical contract, complete two independent contract reviews, disposition all
findings, and commit that checkpoint as a standalone ancestor revision per
`docs/standards/contract-first-change-standard.md`.

The checkpoint must decide, rather than infer from current code:

1. Whether archive takes a shared/read lock, mutations take an exclusive/write
   lock, or an equivalent run-scoped lease protocol is used.
2. Which mutations participate and what happens when archive or mutation is
   already active: bounded wait, explicit conflict, or queue dependency.
3. The archive representation of canonical internal links and the treatment of
   non-canonical links, including containment and restore behavior. Operator
   direction already fixes the fork contract: canonical Omni shared-input links
   are location-relative and point within the destination run after a fork.
4. The canonical typed RQ/API failure payload and user/operator remediation for
   broken links and consistency conflicts.

## Objectives and Success Criteria

- [ ] Archive and participating run-tree mutations cannot execute their
  filesystem read/write phases concurrently for the same run.
- [ ] `delete_omni_contrasts_rq` holds the selected coordination boundary across
  the complete deletion, not only NoDb state updates.
- [ ] Broken symlinks are detected deterministically before ZIP payload writing
  and reported with run-relative link and target context.
- [ ] Symlinks cannot cause archive creation to read outside contract-approved
  run roots or leak unrelated run data.
- [ ] A forked Omni scenario's canonical shared-input links resolve inside the
  destination run, including when the source inherited absolute links through
  multiple prior forks.
- [ ] A target disappearing between preflight and read is handled according to
  the same explicit consistency contract, with no published partial archive.
- [ ] Exact regressions reproduce the production overlap and broken-link
  signature without timing-dependent sleeps.
- [ ] Existing successful archive, disk-headroom, archive exclusion, comment,
  cleanup, and restore behavior remains covered.
- [ ] Focused tests, full repository pytest, applicable RQ graph validation,
  documentation lint, code review, QA review, and security review pass with no
  unresolved medium/high findings.
- [ ] Forest canary validation precedes production rollout; production health
  signals are observed for 30 days.

## Compatibility and Regression Plan

- Preserve existing run layout, archive naming, final ZIP location, archive
  comments, and RQ response envelope unless the approved checkpoint explicitly
  versions a behavior.
- Keep evolution additive and fail explicitly; do not silently discard files or
  links to make an archive appear successful.
- Characterize current valid symlink behavior before choosing the new policy.
- Characterize and migrate legacy absolute Omni shared-input links without
  following arbitrary or unrecognized links during fork normalization.
- Test old runs containing valid cross-run Omni links and broken links, plus
  ordinary runs without symlinks.
- Validate resulting ZIP contents and restore behavior, not only job status.
- Verify failure cleanup leaves no final corrupt ZIP and no stale `.tmp`, lock,
  or archive-job identifier.

## Security Impact and Review Gate

- **Security impact triage**: `high`.
- **Dedicated security review required**: `yes`.
- **Rationale**: the change governs archive file/path traversal, cross-run
  symlinks, run-scoped data integrity, RQ concurrency, and downloadable output.
- **Artifact**:
  `artifacts/2026-08-02_security_review.md`.

The review must cover path containment, symlink escape and time-of-check/time-of-
use behavior, cross-run authorization/data disclosure, lock ownership/expiry,
deadlock ordering, cancellation, partial ZIP cleanup, and restore symmetry.

## Hardening Hypotheses and Signals

### H1: Snapshot coordination

If archive traversal and participating mutations share a run-scoped
coordination contract for their complete filesystem phases, no archive will
fail or silently become inconsistent because a participating mutation removed
an entry mid-read.

- Health signal: zero archive failures attributable to participating concurrent
  mutations during the 30-day production observation window.
- Guardrails: no deadlocks, stale leases, material queue starvation, or
  mutation latency regression beyond the approved bound.

### H2: Symlink policy

If archive preflight classifies every symlink under an explicit containment and
representation policy and traversal revalidates relevant assumptions, broken or
escaping links will fail early with actionable errors and cannot disclose data.

- Health signal: zero late raw `FileNotFoundError` failures from `zipfile.write`
  for symlink entries; typed diagnostics identify the relative link and reason.
- Guardrails: ordinary archives and approved legacy Omni scenarios remain
  usable, archive contents are deterministic, and no path outside approved run
  scope is read.

### Danger signals

- A second ad hoc lock that is not shared by all relevant mutations.
- A broad retry or `FileNotFoundError` catch that masks an inconsistent archive.
- Silent omission of broken or concurrently removed entries.
- Lock TTL expiry permitting overlap, lock-order inversion, or abandoned locks.
- Following symlinks into unrelated runs without an explicit authorization and
  representation contract.

### Observation window and calluses

The production observation window is 30 days after deployment. No retry,
feature flag, or delay is authorized by this package by default. Any temporary
lease timeout, compatibility mode, or operator override introduced during
implementation must be registered in `tracker.md` with an owner, review date,
rollback path, and measurable sunset criteria.

## Precedent

- `docs/standards/hardening-lifecycle-standard.md` supplies incident evidence,
  signal, review, and observation requirements.
- `docs/schemas/nodb-persistence-concurrency-contract.md` defines cooperative
  NoDb locks and explicitly notes that they do not protect out-of-band file
  mutation. This package must not misrepresent a short NoDb lock as a run-tree
  snapshot lock.
- `docs/work-packages/20260214_nodir_archives/` provides existing symlink/path
  security precedent and Omni child-run compatibility context.
- `docs/work-packages/20260428_rq_scoped_stale_cache_guard_priority2/` covers
  scoped cache guards around Omni mutation paths but intentionally preserved
  existing deletion and archive behavior.
- `docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups/` preserves
  archive-root and lock-gate ordering and is relevant to regression ordering.

Unlike NoDir extraction hardening or stale-cache guards, this package owns the
consistency boundary between whole-run archive reads and filesystem mutations.

## Stakeholders and Reviews

- **Primary**: WEPPcloud operators and users creating project archives.
- **Domain reviewers**: RQ and NoDb/Omni maintainers.
- **Required independent reviews**: two contract reviews before implementation;
  code, QA, and security reviews before closure.
- **Informed**: Mariana and the operator who reported the production failure.

## Timeline and Risk

- **Expected duration**: 3–6 focused sessions plus a 30-day production
  observation window.
- **Complexity**: high.
- **Risk**: high because incorrect locking can deadlock work and incorrect
  symlink handling can omit or expose data.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no.
- **Decision provenance captured**: contract checkpoint required instead.

## References

- `wepppy/rq/project_rq_archive.py` — archive traversal and publication.
- `wepppy/rq/omni_rq.py` — contrast deletion RQ entry point.
- `wepppy/nodb/mods/omni/omni_state_contrast_mixin.py` — contrast cleanup.
- `tests/rq/test_project_rq_archive.py` — archive regression anchor.
- `tests/rq/test_omni_rq.py` — Omni RQ regression anchor.
- `docs/schemas/rq-response-contract.md` — canonical RQ payload contract.

## Deliverables

- Approved standalone contract checkpoint and canonical contract amendment.
- Minimal run-scoped archive/mutation coordination implementation.
- Explicit secure symlink preflight/traversal implementation.
- Deterministic unit/integration regressions and generated ZIP evidence.
- Operator/developer documentation and rollout/rollback instructions.
- Code, QA, and security review artifacts with finding disposition.
