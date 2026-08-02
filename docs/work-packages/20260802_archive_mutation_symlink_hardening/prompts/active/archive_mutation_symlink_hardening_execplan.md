# Harden run archives against concurrent mutation and unsafe symlinks

This ExecPlan is maintained under
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current. Update
this plan and the package `tracker.md` together at every milestone handoff.

## Purpose / Big Picture

A user can request a project archive and receive either a complete,
contract-consistent ZIP or an early, actionable failure. Same-run RQ mutations
cannot delete files during the archive's protected read phase, and symlinks are
handled by an explicit containment and representation policy rather than by
incidental `os.walk`/`zipfile` behavior.

## Progress

- [x] (2026-08-02 17:15 UTC) Captured the two archive failures, deletion job,
  exact overlap, broken link, missing target, and production service health.
- [x] (2026-08-02 17:25 UTC) Created the work package and recorded precedent,
  hypotheses, signals, compatibility constraints, and security gate.
- [ ] Inventory archive and mutation surfaces plus current symlink behavior.
- [ ] Ratify and commit the contract-first ancestor checkpoint.
- [ ] Add failing deterministic regressions for both defects.
- [ ] Implement the approved minimal hardening.
- [ ] Validate, review, canary, deploy when authorized, and observe for 30 days.

## Surprises & Discoveries

- Observation: `archive_rq` checks currently held `.nodb` locks only once before
  disk sizing and traversal. It does not hold a run-snapshot lock while walking
  and writing the ZIP.
  Evidence: `wepppy/rq/project_rq_archive.py:archive_rq`.

- Observation: `Omni.clear_contrasts()` updates controller state inside
  `self.locked()` but calls `_clean_contrast_runs()` after leaving that critical
  section. The deletion job can therefore mutate the filesystem while the
  archive sees no held `.nodb` lock.
  Evidence: `wepppy/nodb/mods/omni/omni_state_contrast_mixin.py`.

- Observation: valid directory symlinks and broken directory symlinks are
  classified differently by `os.walk`; the broken link reached `zf.write`,
  which followed it and raised during `os.stat`.
  Evidence: production traceback and the link inspection on `wepp1`.

- Observation: the broken link predates the observed deletion overlap. The
  first archive failed on it at 16:51 UTC, while the recorded deletion began at
  17:06 UTC.
  Evidence: RQ jobs `65717fb6-db0b-47e8-aa28-602dc798a18b` and
  `ae0ea873-ef03-410a-9a9f-d7e6e6c791e0`.

## Decision Log

- Decision: Keep the two confirmed defects in one package but require separate
  regressions and acceptance evidence.
  Rationale: both affect archive consistency and share traversal/coordination
  boundaries, but neither is sufficient evidence for the other's root cause.
  Date/Author: 2026-08-02 / Codex.

- Decision: Use the contract-first checkpoint to select lock and symlink
  semantics before editing implementation.
  Rationale: these choices change RQ behavior, compatibility, path safety, and
  downloadable archive contents; current incidental behavior is not normative.
  Date/Author: 2026-08-02 / Codex.

- Decision: Treat silent omission and broad retry as disallowed unless the
  operator explicitly ratifies a narrowly specified exception.
  Rationale: either behavior could publish an archive that does not represent a
  stable run and mask data loss.
  Date/Author: 2026-08-02 / Codex.

## Outcomes & Retrospective

Pending implementation and observation. At package creation, the production
incident is fully scoped, but no production data or code has been changed.

## Context and Orientation

`wepppy/rq/project_rq.py:archive_rq` delegates to
`wepppy/rq/project_rq_archive.py:archive_rq`. That helper checks NoDb lock
statuses, estimates disk usage, walks the entire run with `os.walk`, writes each
file through `zipfile.ZipFile.write`, and atomically renames a temporary ZIP on
success. Its `finally` block removes a remaining temporary ZIP and clears the
archive job identifier.

`wepppy/rq/omni_rq.py:delete_omni_contrasts_rq` hydrates `Omni` and calls
`clear_contrasts()`. In
`wepppy/nodb/mods/omni/omni_state_contrast_mixin.py`, controller fields are
cleared while the Omni NoDb lock is held, but contrast directories and sidecars
are deleted afterward. Other RQ and direct mutation entry points must be
inventoried; fixing only this one call would leave an unsupported abstraction.

The production link was under
`_pups/omni/scenarios/prescribed_fire/climate` and pointed to a different run.
Omni intentionally uses some symlinks for child-run inputs, so simply banning
all symlinks may break legacy and current workflows. Conversely, following
arbitrary links can disclose unrelated data. The contract checkpoint must
resolve that tension with exact containment, authorization, ZIP representation,
and restore rules.

## Milestone 1: Discovery and characterization

Inventory every same-run filesystem mutation that can overlap whole-run archive
creation. Start from RQ enqueue sites and worker functions, then trace helpers
that create, rename, unlink, or recursively remove run-tree entries. Record the
queue, current locks, lock duration, cancellation behavior, and whether the
mutation can be invoked outside RQ. Do not assume every NoDb writer needs the
new boundary; include only confirmed filesystem-consistency participants.

Add characterization tests or a read-only spike for how the current archive
handles ordinary files, valid file links, valid directory links, broken links,
links to another run, relative escapes, and a target removed between discovery
and `zf.write`. Inspect actual ZIP entry names and contents. Record results in
the tracker or a concise artifact.

Milestone acceptance: the participant matrix and symlink behavior matrix are
complete enough to evaluate coordination and representation alternatives.

## Milestone 2: Contract checkpoint

Create `artifacts/2026-08-02_contract_decision.md` with the starting revision,
applicable canonical contracts, observed discrepancies, alternatives, exact
normative delta, compatibility and security impact, and proposed regression
evidence. The decision must define:

- the shared/exclusive or equivalent coordination primitive, key, owner,
  acquisition order, TTL/renewal, cancellation, conflict, and recovery rules;
- the exact participant boundary and how future mutators opt in;
- allowed symlink targets and representation in ZIPs;
- preflight versus read-time revalidation and typed failure details;
- atomic publication, cleanup, and restore symmetry;
- user/operator messaging and RQ response compatibility.

Amend or create the canonical archive-consistency contract. Obtain explicit
operator approval and two independent read-only contract reviews, disposition
every finding, and commit the checkpoint and contract changes as a standalone
ancestor. Do not edit production implementation before this milestone passes.

Milestone acceptance: the tracker records the ancestor revision and review
artifacts, and the working tree contains no implementation change predating it.

## Milestone 3: Exact failing regressions

Extend `tests/rq/test_project_rq_archive.py` with deterministic synchronization
seams. One test must pause archive traversal while a participating mutation
attempts to enter its filesystem phase and prove the approved serialization or
conflict behavior. A companion test must prove cleanup and lock release on
archive failure/cancellation. Avoid wall-clock sleeps.

Add a fixture reproducing the broken `prescribed_fire/climate` link and assert
the approved typed error, relative path/target diagnostics, absence of a final
or temporary ZIP, and cleared archive job identifier. Cover valid approved
links, escape attempts, cycles if applicable, and a target disappearing after
preflight. Extend `tests/rq/test_omni_rq.py` or the closest Omni suite to prove
the deletion filesystem phase participates for its full duration.

Milestone acceptance: tests fail for the expected reasons on the checkpoint
ancestor and do not depend on scheduling luck.

## Milestone 4: Minimal implementation

Implement the approved coordination through a small shared primitive with
explicit acquisition/release boundaries and observable errors. Integrate
archive and only the inventoried participating mutations. Preserve established
NoDb/NoDir lock ordering and do not add a fallback wrapper that proceeds without
required coordination.

Implement one symlink classification path used consistently by sizing,
preflight, and ZIP traversal. Enforce approved containment before reading a
target and handle read-time invalidation according to the contract. Keep final
ZIP publication atomic and failure cleanup explicit.

Update the RQ response/error contract and operator/developer documentation as
required. Update the RQ dependency catalog only if enqueue or dependency edges
change.

Milestone acceptance: focused regressions pass, existing archive behavior is
preserved where the contract does not change it, and no silent skip or partial
publication path exists.

## Milestone 5: Validation, review, and rollout evidence

Run from `/home/workdir/wepppy`:

    wctl run-pytest tests/rq/test_project_rq_archive.py --maxfail=1
    wctl run-pytest <targeted Omni RQ and NoDb suites> --maxfail=1
    wctl check-rq-graph  # only when queue wiring changed
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20260802_archive_mutation_symlink_hardening
    wctl doc-lint --path <each affected durable document>
    git diff --check

Create code-review, QA-review, and security-review artifacts. Resolve every
medium/high finding before closure. Manually inspect generated ZIP contents and
restore behavior for ordinary and approved linked runs. Validate a Forest
canary with overlapping archive/mutation attempts and a legacy linked Omni run.
Do not deploy to production without separate operator authorization.

After deployment, record baseline and post-change signals for 30 days. Reopen
the package on any recurrence of the raw symlink `FileNotFoundError`, an archive
inconsistency attributable to a participating mutation, a deadlock/stale lock,
or cross-run archive disclosure.

## Validation and Acceptance

Acceptance requires behavioral evidence, not only successful unit tests:

- archive and a participating mutation cannot overlap their protected phases;
- broken/escaping symlinks yield the approved actionable error before final ZIP
  publication;
- disappearing targets cannot result in a successful inconsistent ZIP;
- valid approved legacy links produce the contract-defined contents;
- failures and cancellation clean temporary artifacts, job identifiers, and
  coordination state;
- restore behavior matches the chosen representation;
- security, code, and QA gates have no unresolved medium/high findings.

## Idempotence and Recovery

Package documentation steps are repeatable. Test fixtures use temporary run
trees. Archive implementation must retain timestamped final output and
temporary-path cleanup semantics. A failed archive can be retried after the
reported mutation or symlink condition is resolved; retry must not require
manual lock deletion under normal operation.

If a development attempt leaves a coordination record, use only the recovery
operation defined by the approved contract and record it in the tracker. Do not
force-clear production locks or modify production run data while executing this
plan without explicit operator authorization.

Rollback removes the new participant integrations and symlink implementation
as one compatible change while retaining the approved contract history and
incident tests as evidence. If rollout exposes deadlock or data-disclosure risk,
stop new archive submissions through the narrowest available operational
control and follow the production runbook; do not restart the entire stack by
default.

## Artifacts and Notes

Required artifacts:

- `artifacts/2026-08-02_contract_decision.md`
- two pre-implementation contract reviews and their disposition
- `artifacts/2026-08-02_security_review.md`
- final code-review and QA-review findings/disposition
- participant and symlink behavior matrices
- Forest canary and production observation evidence

## Interfaces and Dependencies

Prefer owned Redis/NoDb/RQ primitives already in the repository. No external
dependency is expected or authorized. The final interface names are selected
by the contract checkpoint, but the implementation must expose test seams for
acquisition, release, traversal classification, and target invalidation so
regressions do not depend on real Redis, NFS, or sleeps.

Plan revision note (2026-08-02): Initial plan created from the confirmed
`wepp1` incident. It deliberately defers lock and symlink representation choices
to the required contract-first checkpoint.

